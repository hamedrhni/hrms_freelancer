"""
Tax Treaty DocType Controller
Manages international tax treaty configurations for freelancer payments
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

if TYPE_CHECKING:
    from frappe.types import DF


class TaxTreaty(Document):
    """
    Tax Treaty DocType for managing double taxation agreements
    and withholding tax configurations for international freelancers.
    """
    
    if TYPE_CHECKING:
        treaty_code: DF.Data
        treaty_name: DF.Data
        country_1: DF.Link
        country_2: DF.Link
        effective_date: DF.Date | None
        expiry_date: DF.Date | None
        status: DF.Literal["Active", "Superseded", "Terminated", "Pending"]
        standard_rate: DF.Percent
        reduced_rate: DF.Percent
        service_fee_rate: DF.Percent | None
        independent_services_rate: DF.Percent | None

    def validate(self) -> None:
        """Validate tax treaty data"""
        self.validate_countries()
        self.validate_dates()
        self.validate_rates()
        self.set_treaty_code()
    
    def validate_countries(self) -> None:
        """Ensure different countries are selected"""
        if self.country_1 == self.country_2:
            frappe.throw(_("Country 1 and Country 2 must be different"))
    
    def validate_dates(self) -> None:
        """Validate effective and expiry dates"""
        if self.effective_date and self.expiry_date:
            if getdate(self.expiry_date) < getdate(self.effective_date):
                frappe.throw(_("Expiry date cannot be before effective date"))
        
        # Check if expired
        if self.expiry_date and getdate(self.expiry_date) < getdate(nowdate()):
            if self.status == "Active":
                frappe.msgprint(
                    _("Treaty expiry date has passed. Consider updating status."),
                    indicator="orange"
                )
    
    def validate_rates(self) -> None:
        """Validate tax rates are reasonable"""
        for field in ["standard_rate", "reduced_rate", "dividend_rate", 
                      "interest_rate", "royalty_rate", "service_fee_rate",
                      "independent_services_rate"]:
            rate = getattr(self, field, None)
            if rate is not None:
                if rate < 0 or rate > 100:
                    frappe.throw(
                        _("{0} must be between 0 and 100").format(
                            self.meta.get_field(field).label
                        )
                    )
        
        # Reduced rate should typically be less than standard
        if self.reduced_rate and self.standard_rate:
            if self.reduced_rate > self.standard_rate:
                frappe.msgprint(
                    _("Reduced rate ({0}%) is higher than standard rate ({1}%). "
                      "Please verify.").format(self.reduced_rate, self.standard_rate),
                    indicator="orange"
                )
    
    def set_treaty_code(self) -> None:
        """Auto-generate treaty code if not set"""
        if not self.treaty_code:
            # Get country codes
            c1_code = frappe.db.get_value("Country", self.country_1, "code") or self.country_1[:2]
            c2_code = frappe.db.get_value("Country", self.country_2, "code") or self.country_2[:2]
            
            # Sort alphabetically
            codes = sorted([c1_code.upper(), c2_code.upper()])
            self.treaty_code = f"{codes[0]}-{codes[1]}"


@frappe.whitelist()
def get_applicable_treaty(
    source_country: str,
    target_country: str
) -> Optional[Dict[str, Any]]:
    """
    Find applicable tax treaty between two countries
    
    Args:
        source_country: Freelancer's tax residency country
        target_country: Company/work country
        
    Returns:
        Treaty details if found, None otherwise
    """
    # Look for active treaty between the two countries
    treaty = frappe.db.sql("""
        SELECT 
            name, treaty_name, treaty_code,
            reduced_rate, service_fee_rate, independent_services_rate,
            certificate_required, form_required,
            minimum_stay_days, permanent_establishment_threshold
        FROM `tabTax Treaty`
        WHERE status = 'Active'
        AND (
            (country_1 = %s AND country_2 = %s)
            OR (country_1 = %s AND country_2 = %s)
        )
        AND (expiry_date IS NULL OR expiry_date >= %s)
        ORDER BY effective_date DESC
        LIMIT 1
    """, (source_country, target_country, target_country, source_country, nowdate()), as_dict=True)
    
    if treaty:
        return treaty[0]
    
    return None


@frappe.whitelist()
def get_withholding_rate(
    freelancer_country: str,
    company_country: str,
    income_type: str = "services"
) -> Dict[str, Any]:
    """
    Get applicable withholding tax rate
    
    Args:
        freelancer_country: Freelancer's tax residency country
        company_country: Company's country
        income_type: Type of income (services, dividends, interest, royalties)
        
    Returns:
        Dictionary with rate and treaty information
    """
    # Check for EU countries (no withholding within EU)
    eu_countries = get_eu_countries()
    
    if freelancer_country in eu_countries and company_country in eu_countries:
        return {
            "rate": 0,
            "treaty_applied": False,
            "eu_member": True,
            "notes": "No withholding tax within EU member states"
        }
    
    # Look for applicable treaty
    treaty = get_applicable_treaty(freelancer_country, company_country)
    
    if treaty:
        # Determine applicable rate based on income type
        rate_fields = {
            "services": ["independent_services_rate", "service_fee_rate", "reduced_rate"],
            "dividends": ["dividend_rate", "reduced_rate"],
            "interest": ["interest_rate", "reduced_rate"],
            "royalties": ["royalty_rate", "reduced_rate"]
        }
        
        rate = None
        for field in rate_fields.get(income_type, ["reduced_rate"]):
            rate = treaty.get(field)
            if rate is not None:
                break
        
        return {
            "rate": rate or 0,
            "treaty_applied": True,
            "treaty_name": treaty.treaty_name,
            "treaty_code": treaty.treaty_code,
            "certificate_required": treaty.certificate_required,
            "form_required": treaty.form_required,
            "notes": f"Rate under {treaty.treaty_name}"
        }
    
    # Default rates by country (without treaty)
    default_rates = {
        "United States": 30,
        "United Kingdom": 20,
        "India": 10,
        "China": 10,
        "Brazil": 15,
        "Australia": 30,
        "Canada": 25,
        "Japan": 20,
        "South Korea": 20,
        "Russia": 20,
    }
    
    return {
        "rate": default_rates.get(freelancer_country, 30),
        "treaty_applied": False,
        "notes": "No applicable treaty found. Default withholding rate applied."
    }


def get_eu_countries() -> List[str]:
    """Get list of EU member states"""
    return [
        "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
        "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
        "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
        "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"
    ]


@frappe.whitelist()
def get_treaty_countries() -> List[Dict[str, str]]:
    """Get all countries with active tax treaties"""
    countries = frappe.db.sql("""
        SELECT DISTINCT country_1 as country FROM `tabTax Treaty` WHERE status = 'Active'
        UNION
        SELECT DISTINCT country_2 as country FROM `tabTax Treaty` WHERE status = 'Active'
        ORDER BY country
    """, as_dict=True)
    
    return countries


# Fixtures: Common tax treaties (2026 estimates)
def get_default_tax_treaties() -> List[Dict[str, Any]]:
    """
    Get default tax treaty configurations
    These are estimates and should be verified with official sources
    """
    return [
        {
            "treaty_code": "NL-US",
            "treaty_name": "Netherlands-United States Income Tax Treaty",
            "country_1": "Netherlands",
            "country_2": "United States",
            "status": "Active",
            "treaty_type": "Double Taxation Agreement (DTA)",
            "standard_rate": 30,
            "reduced_rate": 15,
            "dividend_rate": 15,
            "interest_rate": 0,
            "royalty_rate": 0,
            "service_fee_rate": 0,
            "independent_services_rate": 0,
            "certificate_required": 1,
            "form_required": "W-8BEN",
            "minimum_stay_days": 183,
            "permanent_establishment_threshold": 183,
            "official_source_url": "https://www.irs.gov/businesses/international-businesses/netherlands-tax-treaty-documents"
        },
        {
            "treaty_code": "NL-UK",
            "treaty_name": "Netherlands-United Kingdom Double Taxation Convention",
            "country_1": "Netherlands",
            "country_2": "United Kingdom",
            "status": "Active",
            "treaty_type": "Double Taxation Agreement (DTA)",
            "standard_rate": 20,
            "reduced_rate": 0,
            "dividend_rate": 10,
            "interest_rate": 0,
            "royalty_rate": 0,
            "service_fee_rate": 0,
            "independent_services_rate": 0,
            "certificate_required": 1,
            "minimum_stay_days": 183
        },
        {
            "treaty_code": "DE-US",
            "treaty_name": "Germany-United States Income Tax Treaty",
            "country_1": "Germany",
            "country_2": "United States",
            "status": "Active",
            "treaty_type": "Double Taxation Agreement (DTA)",
            "standard_rate": 30,
            "reduced_rate": 15,
            "dividend_rate": 15,
            "interest_rate": 0,
            "royalty_rate": 0,
            "service_fee_rate": 0,
            "certificate_required": 1,
            "form_required": "W-8BEN",
            "minimum_stay_days": 183
        },
        {
            "treaty_code": "NL-IN",
            "treaty_name": "Netherlands-India Double Taxation Avoidance Agreement",
            "country_1": "Netherlands",
            "country_2": "India",
            "status": "Active",
            "treaty_type": "Double Taxation Agreement (DTA)",
            "standard_rate": 40,
            "reduced_rate": 10,
            "dividend_rate": 10,
            "interest_rate": 10,
            "royalty_rate": 10,
            "service_fee_rate": 10,
            "certificate_required": 1,
            "minimum_stay_days": 183
        },
        {
            "treaty_code": "DE-UK",
            "treaty_name": "Germany-United Kingdom Double Taxation Convention",
            "country_1": "Germany",
            "country_2": "United Kingdom",
            "status": "Active",
            "treaty_type": "Double Taxation Agreement (DTA)",
            "standard_rate": 20,
            "reduced_rate": 0,
            "dividend_rate": 10,
            "interest_rate": 0,
            "royalty_rate": 0,
            "certificate_required": 1,
            "minimum_stay_days": 183
        }
    ]
