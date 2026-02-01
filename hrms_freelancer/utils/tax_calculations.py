"""
Tax Calculation Utilities
Handles withholding tax, VAT, and treaty-based calculations
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List, Tuple
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from hrms_freelancer.compliance.doctype.tax_treaty.tax_treaty import (
    get_applicable_treaty,
    get_withholding_rate,
    get_eu_countries
)
from hrms_freelancer.compliance.doctype.vat_configuration.vat_configuration import (
    get_vat_rate,
    calculate_vat
)


class TaxCalculator:
    """
    Comprehensive tax calculator for freelancer payments
    
    Handles:
    - Withholding tax based on residency and treaties
    - VAT/BTW for EU and non-EU countries
    - Reverse charge mechanism
    - Social security considerations
    """
    
    def __init__(
        self,
        freelancer_country: str,
        company_country: str,
        is_b2b: bool = True,
        transaction_date: str = None
    ):
        """
        Initialize tax calculator
        
        Args:
            freelancer_country: Freelancer's tax residency country
            company_country: Company's country
            is_b2b: Is B2B transaction
            transaction_date: Date for rate lookups
        """
        self.freelancer_country = freelancer_country
        self.company_country = company_country
        self.is_b2b = is_b2b
        self.transaction_date = transaction_date or nowdate()
        
        self.eu_countries = get_eu_countries()
        self.is_freelancer_eu = freelancer_country in self.eu_countries
        self.is_company_eu = company_country in self.eu_countries
        self.is_cross_border = freelancer_country != company_country
    
    def calculate_all_taxes(
        self,
        gross_amount: float,
        service_type: str = "professional",
        has_tax_certificate: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate all applicable taxes for a payment
        
        Args:
            gross_amount: Base payment amount
            service_type: Type of service
            has_tax_certificate: Whether freelancer has tax residency certificate
            
        Returns:
            Complete tax breakdown
        """
        result = {
            "gross_amount": gross_amount,
            "freelancer_country": self.freelancer_country,
            "company_country": self.company_country,
            "is_eu_freelancer": self.is_freelancer_eu,
            "is_cross_border": self.is_cross_border,
            "transaction_date": self.transaction_date,
            "components": [],
            "warnings": [],
            "compliance_notes": []
        }
        
        # Calculate withholding tax
        withholding = self._calculate_withholding(gross_amount, has_tax_certificate)
        result["withholding_tax"] = withholding
        if withholding["rate"] > 0:
            result["components"].append({
                "type": "withholding_tax",
                "rate": withholding["rate"],
                "amount": withholding["amount"],
                "deductible": True
            })
        
        # Calculate VAT
        vat = self._calculate_vat(gross_amount, service_type)
        result["vat"] = vat
        if vat["amount"] > 0 or vat["reverse_charge"]:
            result["components"].append({
                "type": "vat",
                "rate": vat["rate"],
                "amount": vat["amount"],
                "reverse_charge": vat["reverse_charge"],
                "deductible": False  # VAT adds to invoice, not deducted from payment
            })
        
        # Calculate net amounts
        result["gross_with_vat"] = gross_amount + vat["amount"]
        result["total_deductions"] = withholding["amount"]
        result["net_payable"] = result["gross_with_vat"] - result["total_deductions"]
        
        # If reverse charge, net payable is just gross (no VAT added, no withholding for EU)
        if vat["reverse_charge"]:
            result["net_payable"] = gross_amount - withholding["amount"]
        
        # Add compliance notes
        result["compliance_notes"] = self._get_compliance_notes(result)
        
        return result
    
    def _calculate_withholding(
        self,
        amount: float,
        has_certificate: bool
    ) -> Dict[str, Any]:
        """Calculate withholding tax"""
        # EU to EU: No withholding
        if self.is_freelancer_eu and self.is_company_eu:
            return {
                "rate": 0,
                "amount": 0,
                "treaty_applied": False,
                "notes": "No withholding tax between EU member states"
            }
        
        # Same country: No withholding (local taxation)
        if not self.is_cross_border:
            return {
                "rate": 0,
                "amount": 0,
                "treaty_applied": False,
                "notes": "Domestic payment - no withholding"
            }
        
        # Get treaty rate
        rate_info = get_withholding_rate(
            self.freelancer_country,
            self.company_country,
            "services"
        )
        
        rate = rate_info.get("rate", 0)
        
        # If no certificate, may need to use higher rate
        if rate > 0 and not has_certificate and rate_info.get("certificate_required"):
            # Use default rate without treaty
            rate = rate_info.get("default_rate", rate)
            rate_info["notes"] = f"{rate_info.get('notes', '')} (Certificate required for reduced rate)"
        
        return {
            "rate": rate,
            "amount": round(amount * rate / 100, 2),
            "treaty_applied": rate_info.get("treaty_applied", False),
            "treaty_name": rate_info.get("treaty_name"),
            "certificate_required": rate_info.get("certificate_required", False),
            "notes": rate_info.get("notes", "")
        }
    
    def _calculate_vat(
        self,
        amount: float,
        service_type: str
    ) -> Dict[str, Any]:
        """Calculate VAT/BTW"""
        # Cross-border B2B within EU: Reverse charge
        if self.is_cross_border and self.is_freelancer_eu and self.is_company_eu and self.is_b2b:
            return {
                "rate": 0,
                "amount": 0,
                "reverse_charge": True,
                "notes": "EU B2B reverse charge mechanism - VAT accounted by recipient"
            }
        
        # Non-EU to EU: Generally no VAT on services (place of supply = customer)
        if not self.is_freelancer_eu and self.is_company_eu and self.is_b2b:
            return {
                "rate": 0,
                "amount": 0,
                "reverse_charge": True,
                "notes": "Import of services - reverse charge applies"
            }
        
        # EU to non-EU: Export of services, generally 0%
        if self.is_freelancer_eu and not self.is_company_eu:
            return {
                "rate": 0,
                "amount": 0,
                "reverse_charge": False,
                "notes": "Export of services outside EU - 0% VAT"
            }
        
        # Domestic transaction or B2C: Apply local VAT
        vat_info = get_vat_rate(
            self.freelancer_country,
            service_type,
            self.is_b2b
        )
        
        rate = vat_info.get("rate", 0)
        
        return {
            "rate": rate,
            "amount": round(amount * rate / 100, 2),
            "reverse_charge": False,
            "notes": f"Standard VAT rate for {self.freelancer_country}"
        }
    
    def _get_compliance_notes(self, result: Dict[str, Any]) -> List[str]:
        """Generate compliance notes for the calculation"""
        notes = []
        
        if result["vat"]["reverse_charge"]:
            notes.append(
                "REVERSE CHARGE: Under EU VAT Directive Article 196, "
                "the recipient is liable to account for VAT. "
                "Invoice should state 'Reverse charge' and show 0% VAT."
            )
        
        if result["withholding_tax"]["rate"] > 0:
            notes.append(
                f"WITHHOLDING TAX: {result['withholding_tax']['rate']}% will be withheld. "
                "This should be reported to tax authorities and a certificate provided to the freelancer."
            )
            
            if result["withholding_tax"]["treaty_applied"]:
                notes.append(
                    f"TAX TREATY: Reduced rate applied under {result['withholding_tax'].get('treaty_name', 'applicable treaty')}. "
                    "Ensure tax residency certificate is on file."
                )
        
        if self.is_freelancer_eu and self.is_company_eu and self.is_cross_border:
            notes.append(
                "EU INTRA-COMMUNITY: This is an intra-Community supply of services. "
                "Report in EC Sales List if required."
            )
        
        # Large payment warning
        if result["gross_amount"] > 10000:
            notes.append(
                "LARGE PAYMENT: Amounts over €10,000 may have additional reporting requirements. "
                "Verify compliance with anti-money laundering regulations."
            )
        
        return notes


@frappe.whitelist()
def calculate_freelancer_taxes(
    freelancer: str,
    amount: float,
    service_type: str = "professional"
) -> Dict[str, Any]:
    """
    Calculate taxes for a specific freelancer
    
    Args:
        freelancer: Freelancer document name
        amount: Payment amount
        service_type: Type of service
        
    Returns:
        Tax calculation breakdown
    """
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    company_doc = frappe.get_doc("Company", freelancer_doc.company)
    
    calculator = TaxCalculator(
        freelancer_country=freelancer_doc.tax_residency_country,
        company_country=company_doc.country,
        is_b2b=True
    )
    
    result = calculator.calculate_all_taxes(
        gross_amount=flt(amount),
        service_type=service_type,
        has_tax_certificate=bool(freelancer_doc.tax_certificate)
    )
    
    # Add freelancer-specific info
    result["freelancer"] = freelancer
    result["freelancer_name"] = freelancer_doc.full_name
    result["vat_registered"] = freelancer_doc.vat_registered
    result["vat_number"] = freelancer_doc.vat_number if freelancer_doc.vat_registered else None
    
    return result


@frappe.whitelist()
def estimate_annual_tax_burden(
    freelancer: str,
    estimated_annual_income: float
) -> Dict[str, Any]:
    """
    Estimate annual tax burden for a freelancer
    
    This is a rough estimate for planning purposes.
    
    Args:
        freelancer: Freelancer document name
        estimated_annual_income: Estimated annual income
        
    Returns:
        Estimated tax breakdown
    """
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    
    # Base estimates by country (2026 approximations)
    income_tax_rates = {
        "Netherlands": {"marginal": 49.5, "effective_estimate": 35},
        "Germany": {"marginal": 45, "effective_estimate": 32},
        "France": {"marginal": 45, "effective_estimate": 30},
        "United Kingdom": {"marginal": 45, "effective_estimate": 28},
        "United States": {"marginal": 37, "effective_estimate": 25},
        "Belgium": {"marginal": 50, "effective_estimate": 35},
        "Spain": {"marginal": 47, "effective_estimate": 30},
        "Italy": {"marginal": 43, "effective_estimate": 32},
        "Poland": {"marginal": 32, "effective_estimate": 20},
        "Ireland": {"marginal": 40, "effective_estimate": 28},
    }
    
    social_security_rates = {
        "Netherlands": 27.65,  # Zelfstandigen premie
        "Germany": 18.6,      # Selbständige
        "France": 22,         # Cotisations sociales
        "United Kingdom": 9,   # Class 4 NI
        "Belgium": 20.5,
        "Spain": 30,
        "Italy": 24,
        "Poland": 19.52,
        "Ireland": 4,
    }
    
    country = freelancer_doc.tax_residency_country
    income_rate = income_tax_rates.get(country, {"effective_estimate": 30})
    social_rate = social_security_rates.get(country, 15)
    
    income = flt(estimated_annual_income)
    
    # Calculations
    estimated_income_tax = income * income_rate["effective_estimate"] / 100
    estimated_social_security = income * social_rate / 100
    
    # VAT (if registered, need to charge and remit)
    vat_rate = 0
    if freelancer_doc.vat_registered:
        vat_config = frappe.db.get_value(
            "VAT Configuration", country, "standard_rate"
        )
        vat_rate = vat_config or 21
    
    return {
        "freelancer": freelancer,
        "country": country,
        "estimated_annual_income": income,
        "income_tax": {
            "marginal_rate": income_rate.get("marginal", 40),
            "effective_rate": income_rate["effective_estimate"],
            "estimated_amount": round(estimated_income_tax, 2)
        },
        "social_security": {
            "rate": social_rate,
            "estimated_amount": round(estimated_social_security, 2)
        },
        "vat": {
            "registered": freelancer_doc.vat_registered,
            "rate": vat_rate,
            "note": "VAT is collected and remitted, not a personal cost"
        },
        "total_estimated_tax_burden": round(
            estimated_income_tax + estimated_social_security, 2
        ),
        "effective_total_rate": round(
            (estimated_income_tax + estimated_social_security) / income * 100, 1
        ),
        "net_after_tax_estimate": round(
            income - estimated_income_tax - estimated_social_security, 2
        ),
        "disclaimer": (
            "This is a rough estimate for planning purposes only. "
            "Actual tax liability depends on many factors including deductions, "
            "allowances, other income, and individual circumstances. "
            "Consult a qualified tax professional for accurate advice."
        )
    }


def get_tax_year_dates(country: str, year: int = None) -> Tuple[date, date]:
    """
    Get tax year start and end dates for a country
    
    Args:
        country: Country name
        year: Calendar year (defaults to current)
        
    Returns:
        Tuple of (start_date, end_date)
    """
    from datetime import date
    
    if year is None:
        year = date.today().year
    
    # Most countries use calendar year
    # UK uses April 6 - April 5
    if country == "United Kingdom":
        return (date(year, 4, 6), date(year + 1, 4, 5))
    
    # Australia uses July 1 - June 30
    if country == "Australia":
        return (date(year, 7, 1), date(year + 1, 6, 30))
    
    # India uses April 1 - March 31
    if country == "India":
        return (date(year, 4, 1), date(year + 1, 3, 31))
    
    # Default: Calendar year
    return (date(year, 1, 1), date(year, 12, 31))


def validate_tax_id(tax_id: str, country: str) -> Dict[str, Any]:
    """
    Validate tax ID format for a country
    
    Args:
        tax_id: Tax identification number
        country: Country name
        
    Returns:
        Validation result
    """
    import re
    
    patterns = {
        "Netherlands": {
            "name": "BSN",
            "pattern": r"^\d{9}$",
            "example": "123456789"
        },
        "Germany": {
            "name": "Steuernummer",
            "pattern": r"^\d{10,11}$",
            "example": "12345678901"
        },
        "United Kingdom": {
            "name": "UTR",
            "pattern": r"^\d{10}$",
            "example": "1234567890"
        },
        "United States": {
            "name": "SSN/EIN",
            "pattern": r"^(\d{9}|\d{3}-\d{2}-\d{4}|\d{2}-\d{7})$",
            "example": "123-45-6789 or 12-3456789"
        },
        "France": {
            "name": "Numéro fiscal",
            "pattern": r"^\d{13}$",
            "example": "1234567890123"
        },
        "Belgium": {
            "name": "Numéro national",
            "pattern": r"^\d{11}$",
            "example": "12345678901"
        }
    }
    
    config = patterns.get(country)
    if not config:
        return {
            "valid": True,
            "message": f"No validation pattern for {country}",
            "validated": False
        }
    
    # Clean the ID
    clean_id = tax_id.replace(" ", "").replace("-", "").replace(".", "")
    
    if re.match(config["pattern"], clean_id) or re.match(config["pattern"], tax_id):
        return {
            "valid": True,
            "message": f"Valid {config['name']} format",
            "validated": True
        }
    
    return {
        "valid": False,
        "message": f"Invalid {config['name']} format. Expected format like: {config['example']}",
        "validated": True
    }
