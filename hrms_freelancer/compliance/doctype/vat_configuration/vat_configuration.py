"""
VAT Configuration DocType Controller
Manages VAT rates and rules for different countries
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List

import frappe
from frappe import _
from frappe.model.document import Document

if TYPE_CHECKING:
    from frappe.types import DF


# EU countries as of 2026
EU_MEMBER_STATES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"
]


class VATConfiguration(Document):
    """
    VAT Configuration for managing country-specific VAT rates and rules
    """
    
    if TYPE_CHECKING:
        country: DF.Link
        is_eu_member: DF.Check
        standard_rate: DF.Percent
        reduced_rate_1: DF.Percent | None
        reduced_rate_2: DF.Percent | None
        reverse_charge_b2b: DF.Check
        moss_applicable: DF.Check

    def validate(self) -> None:
        """Validate VAT configuration"""
        self.set_eu_status()
        self.validate_rates()
    
    def set_eu_status(self) -> None:
        """Set EU member status based on country"""
        self.is_eu_member = self.country in EU_MEMBER_STATES
    
    def validate_rates(self) -> None:
        """Validate VAT rates are reasonable"""
        if self.standard_rate < 0 or self.standard_rate > 100:
            frappe.throw(_("Standard VAT rate must be between 0 and 100"))
        
        # Reduced rates should be less than standard
        for field in ["reduced_rate_1", "reduced_rate_2", "super_reduced_rate"]:
            rate = getattr(self, field, None)
            if rate and rate >= self.standard_rate:
                frappe.msgprint(
                    _("{0} ({1}%) is not less than standard rate ({2}%). Please verify.").format(
                        self.meta.get_field(field).label, rate, self.standard_rate
                    ),
                    indicator="orange"
                )


@frappe.whitelist()
def get_vat_rate(
    country: str,
    service_type: str = "standard",
    is_b2b: bool = True
) -> Dict[str, Any]:
    """
    Get applicable VAT rate for a country and service type
    
    Args:
        country: Country name
        service_type: Type of service (standard, reduced, digital, professional)
        is_b2b: Is this a B2B transaction?
        
    Returns:
        VAT rate information
    """
    config = frappe.db.get_value(
        "VAT Configuration",
        country,
        ["standard_rate", "reduced_rate_1", "b2b_services_rate", 
         "digital_services_rate", "professional_services_rate",
         "reverse_charge_b2b", "is_eu_member"],
        as_dict=True
    )
    
    if not config:
        # Return default for unknown countries
        return {
            "rate": 0,
            "reverse_charge": False,
            "notes": f"No VAT configuration found for {country}"
        }
    
    # B2B cross-border within EU uses reverse charge
    if is_b2b and config.reverse_charge_b2b:
        return {
            "rate": 0,
            "reverse_charge": True,
            "is_eu": config.is_eu_member,
            "notes": "Reverse charge applies - VAT shifted to recipient"
        }
    
    # Get rate based on service type
    rate_map = {
        "standard": config.standard_rate,
        "reduced": config.reduced_rate_1,
        "digital": config.digital_services_rate or config.standard_rate,
        "professional": config.professional_services_rate or config.standard_rate
    }
    
    return {
        "rate": rate_map.get(service_type, config.standard_rate),
        "reverse_charge": False,
        "is_eu": config.is_eu_member,
        "notes": f"Standard {service_type} rate for {country}"
    }


@frappe.whitelist()
def calculate_vat(
    amount: float,
    country: str,
    service_type: str = "standard",
    is_b2b: bool = True,
    is_cross_border: bool = False
) -> Dict[str, Any]:
    """
    Calculate VAT for a given amount
    
    Args:
        amount: Base amount
        country: Country for VAT calculation
        service_type: Type of service
        is_b2b: Is B2B transaction?
        is_cross_border: Is cross-border within EU?
        
    Returns:
        VAT calculation breakdown
    """
    vat_info = get_vat_rate(country, service_type, is_b2b)
    
    # Cross-border B2B within EU = reverse charge
    if is_cross_border and is_b2b and vat_info.get("is_eu"):
        return {
            "base_amount": amount,
            "vat_rate": 0,
            "vat_amount": 0,
            "total_amount": amount,
            "reverse_charge": True,
            "notes": "EU B2B reverse charge: VAT is 0%, recipient accounts for VAT"
        }
    
    vat_rate = vat_info.get("rate", 0)
    vat_amount = amount * vat_rate / 100
    
    return {
        "base_amount": amount,
        "vat_rate": vat_rate,
        "vat_amount": round(vat_amount, 2),
        "total_amount": round(amount + vat_amount, 2),
        "reverse_charge": vat_info.get("reverse_charge", False),
        "notes": vat_info.get("notes", "")
    }


def get_default_vat_configurations() -> List[Dict[str, Any]]:
    """
    Get default VAT configurations for EU countries (2026 rates)
    """
    return [
        {
            "country": "Netherlands",
            "vat_name": "BTW",
            "is_eu_member": 1,
            "standard_rate": 21,
            "reduced_rate_1": 9,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "registration_threshold": 20000,
            "threshold_currency": "EUR",
            "filing_frequency": "Quarterly",
            "tax_authority": "Belastingdienst",
            "tax_authority_url": "https://www.belastingdienst.nl",
            "vat_number_format": "NL + 9 digits + B + 2 digits"
        },
        {
            "country": "Germany",
            "vat_name": "USt/MwSt",
            "is_eu_member": 1,
            "standard_rate": 19,
            "reduced_rate_1": 7,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "registration_threshold": 22000,
            "threshold_currency": "EUR",
            "filing_frequency": "Monthly",
            "tax_authority": "Bundeszentralamt für Steuern",
            "tax_authority_url": "https://www.bzst.de",
            "vat_number_format": "DE + 9 digits"
        },
        {
            "country": "France",
            "vat_name": "TVA",
            "is_eu_member": 1,
            "standard_rate": 20,
            "reduced_rate_1": 10,
            "reduced_rate_2": 5.5,
            "super_reduced_rate": 2.1,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "registration_threshold": 34400,
            "threshold_currency": "EUR",
            "filing_frequency": "Monthly",
            "tax_authority": "Direction Générale des Finances Publiques",
            "tax_authority_url": "https://www.impots.gouv.fr",
            "vat_number_format": "FR + 2 chars + 9 digits"
        },
        {
            "country": "Belgium",
            "vat_name": "BTW/TVA",
            "is_eu_member": 1,
            "standard_rate": 21,
            "reduced_rate_1": 12,
            "reduced_rate_2": 6,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "registration_threshold": 25000,
            "threshold_currency": "EUR",
            "filing_frequency": "Monthly",
            "tax_authority": "SPF Finances",
            "tax_authority_url": "https://finances.belgium.be"
        },
        {
            "country": "Spain",
            "vat_name": "IVA",
            "is_eu_member": 1,
            "standard_rate": 21,
            "reduced_rate_1": 10,
            "super_reduced_rate": 4,
            "zero_rate_applicable": 0,
            "reverse_charge_b2b": 1,
            "filing_frequency": "Quarterly",
            "tax_authority": "Agencia Tributaria"
        },
        {
            "country": "Italy",
            "vat_name": "IVA",
            "is_eu_member": 1,
            "standard_rate": 22,
            "reduced_rate_1": 10,
            "reduced_rate_2": 5,
            "super_reduced_rate": 4,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "filing_frequency": "Monthly"
        },
        {
            "country": "Poland",
            "vat_name": "PTU/VAT",
            "is_eu_member": 1,
            "standard_rate": 23,
            "reduced_rate_1": 8,
            "reduced_rate_2": 5,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "filing_frequency": "Monthly"
        },
        {
            "country": "Ireland",
            "vat_name": "VAT",
            "is_eu_member": 1,
            "standard_rate": 23,
            "reduced_rate_1": 13.5,
            "reduced_rate_2": 9,
            "super_reduced_rate": 4.8,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "registration_threshold": 37500,
            "threshold_currency": "EUR",
            "filing_frequency": "Bi-Monthly"
        },
        {
            "country": "Sweden",
            "vat_name": "Moms",
            "is_eu_member": 1,
            "standard_rate": 25,
            "reduced_rate_1": 12,
            "reduced_rate_2": 6,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "threshold_currency": "SEK",
            "filing_frequency": "Monthly"
        },
        {
            "country": "Denmark",
            "vat_name": "Moms",
            "is_eu_member": 1,
            "standard_rate": 25,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 1,
            "registration_threshold": 50000,
            "threshold_currency": "DKK",
            "filing_frequency": "Quarterly"
        },
        {
            "country": "United Kingdom",
            "vat_name": "VAT",
            "is_eu_member": 0,
            "standard_rate": 20,
            "reduced_rate_1": 5,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 0,
            "registration_threshold": 85000,
            "threshold_currency": "GBP",
            "filing_frequency": "Quarterly",
            "tax_authority": "HMRC",
            "tax_authority_url": "https://www.gov.uk/government/organisations/hm-revenue-customs"
        },
        {
            "country": "Switzerland",
            "vat_name": "MwSt/TVA/IVA",
            "is_eu_member": 0,
            "standard_rate": 8.1,
            "reduced_rate_1": 2.6,
            "reduced_rate_2": 3.8,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 0,
            "registration_threshold": 100000,
            "threshold_currency": "CHF",
            "filing_frequency": "Quarterly"
        },
        {
            "country": "United States",
            "vat_name": "Sales Tax",
            "is_eu_member": 0,
            "standard_rate": 0,
            "zero_rate_applicable": 1,
            "reverse_charge_b2b": 0,
            "notes": "No federal VAT. State sales taxes vary by state (0-10%+). Services generally not taxed."
        }
    ]
