"""
Freelancer DocType Controller
Handles freelancer/contractor profile management with EU and international compliance
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import date, datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days, flt, cint

if TYPE_CHECKING:
    from frappe.types import DF

# List of EU member states (as of 2026)
EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"
]

# Default withholding tax rates by country (2026 estimates)
DEFAULT_WITHHOLDING_RATES = {
    "United States": 30,  # Can be reduced to 15% under treaty
    "United Kingdom": 20,
    "India": 10,  # Under DTAA
    "China": 10,
    "Brazil": 15,
    "Australia": 30,
    "Canada": 25,
    "Japan": 20,
    "South Korea": 20,
    "Singapore": 0,  # No withholding on services
    "Switzerland": 0,  # Under treaty with most EU countries
}


class Freelancer(Document):
    """
    Freelancer/Contractor profile DocType
    
    Manages independent workers with support for:
    - EU residents (VAT reverse charge, no withholding)
    - Non-EU residents (withholding taxes, treaty benefits)
    - Posted workers (Directive 96/71/EC compliance)
    - Hybrid workers (part employee, part freelancer)
    """
    
    # Type hints for DocType fields
    if TYPE_CHECKING:
        naming_series: DF.Literal["HR-FRL-.YYYY.-", "FRL-.YYYY.-.#####"]
        first_name: DF.Data
        middle_name: DF.Data | None
        last_name: DF.Data
        full_name: DF.Data | None
        contractor_name: DF.Data | None
        email: DF.Data
        phone: DF.Data | None
        mobile: DF.Data | None
        country: DF.Link
        residency_status: DF.Literal["EU Resident", "Non-EU Resident", "EU Posted Worker", "Digital Nomad", "Expat"]
        tax_residency_country: DF.Link
        is_eu_country: DF.Check
        tax_treaty_applicable: DF.Link | None
        withholding_tax_rate: DF.Percent
        vat_registered: DF.Check
        vat_number: DF.Data | None
        vat_rate: DF.Percent
        reverse_charge_applicable: DF.Check
        worker_type: DF.Literal["Freelancer", "Independent Contractor", "Self-Employed", "Consultant", "Agency Contractor"]
        company: DF.Link
        status: DF.Literal["Active", "Inactive", "Onboarding", "Offboarding", "Blacklisted"]
        billing_type: DF.Literal["Hourly", "Daily", "Weekly", "Monthly", "Project-Based", "Milestone-Based"]
        rate: DF.Currency
        currency: DF.Link
        gdpr_consent_given: DF.Check
        gdpr_consent_date: DF.Datetime | None
        user_id: DF.Link | None
        linked_employee: DF.Link | None

    def validate(self) -> None:
        """Validate freelancer data before save"""
        self.set_full_name()
        self.validate_email_unique()
        self.set_eu_country_status()
        self.validate_vat_number()
        self.calculate_withholding_rate()
        self.validate_eu_compliance()
        self.validate_rates()
        self.validate_gdpr_consent()
        self.check_minimum_wage_compliance()
    
    def before_save(self) -> None:
        """Actions before saving the document"""
        if self.gdpr_consent_given and not self.gdpr_consent_date:
            self.gdpr_consent_date = frappe.utils.now_datetime()
    
    def on_update(self) -> None:
        """Actions after document update"""
        self.create_gdpr_consent_log()
        self.sync_with_linked_employee()
        self.update_compliance_status()
    
    def after_insert(self) -> None:
        """Actions after document creation"""
        self.create_user_if_needed()
        self.send_welcome_email()
        self.log_onboarding()
    
    def set_full_name(self) -> None:
        """Construct full name from name components"""
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        self.full_name = " ".join(name_parts)
    
    def validate_email_unique(self) -> None:
        """Ensure email is unique across freelancers"""
        if self.email:
            existing = frappe.db.exists(
                "Freelancer",
                {"email": self.email, "name": ("!=", self.name)}
            )
            if existing:
                frappe.throw(
                    _("A freelancer with email {0} already exists").format(self.email)
                )
    
    def set_eu_country_status(self) -> None:
        """Determine if tax residency country is in EU"""
        if self.tax_residency_country:
            self.is_eu_country = self.tax_residency_country in EU_COUNTRIES
        else:
            self.is_eu_country = 0
    
    def validate_vat_number(self) -> None:
        """Validate VAT number format for EU countries"""
        if self.vat_registered and self.vat_number:
            if self.is_eu_country:
                # Basic EU VAT number validation
                vat = self.vat_number.upper().replace(" ", "")
                
                # VAT number should start with country code
                country_codes = {
                    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG",
                    "Croatia": "HR", "Cyprus": "CY", "Czech Republic": "CZ",
                    "Denmark": "DK", "Estonia": "EE", "Finland": "FI",
                    "France": "FR", "Germany": "DE", "Greece": "EL",
                    "Hungary": "HU", "Ireland": "IE", "Italy": "IT",
                    "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU",
                    "Malta": "MT", "Netherlands": "NL", "Poland": "PL",
                    "Portugal": "PT", "Romania": "RO", "Slovakia": "SK",
                    "Slovenia": "SI", "Spain": "ES", "Sweden": "SE"
                }
                
                expected_prefix = country_codes.get(self.tax_residency_country)
                if expected_prefix and not vat.startswith(expected_prefix):
                    frappe.msgprint(
                        _("VAT number should start with country code {0} for {1}").format(
                            expected_prefix, self.tax_residency_country
                        ),
                        indicator="orange",
                        alert=True
                    )
    
    def calculate_withholding_rate(self) -> None:
        """Calculate applicable withholding tax rate based on residency and treaties"""
        # EU residents: No withholding under EU treaties
        if self.is_eu_country:
            self.withholding_tax_rate = 0
            self.reverse_charge_applicable = self.vat_registered
            return
        
        # Check for applicable tax treaty
        if self.tax_treaty_applicable:
            treaty = frappe.get_doc("Tax Treaty", self.tax_treaty_applicable)
            self.withholding_tax_rate = treaty.reduced_rate or treaty.standard_rate
            return
        
        # Use default rate for country
        default_rate = DEFAULT_WITHHOLDING_RATES.get(
            self.tax_residency_country, 30  # Default to 30% if no treaty
        )
        self.withholding_tax_rate = default_rate
    
    def validate_eu_compliance(self) -> None:
        """Validate EU-specific compliance requirements"""
        if self.residency_status == "EU Posted Worker":
            if not self.posting_country:
                frappe.throw(_("Posting country is required for EU Posted Workers"))
            
            if not self.a1_certificate:
                frappe.msgprint(
                    _("A1 Certificate is required for EU Posted Workers under Regulation (EC) No 883/2004. "
                      "Please upload the certificate."),
                    indicator="orange",
                    title=_("Compliance Warning")
                )
            
            # Validate posting duration
            if self.posting_start_date and self.posting_end_date:
                posting_days = (getdate(self.posting_end_date) - getdate(self.posting_start_date)).days
                if posting_days > 365:
                    frappe.msgprint(
                        _("Posting duration exceeds 12 months. Long-term posting rules under "
                          "Directive 2018/957 may apply. Consider reviewing compliance requirements."),
                        indicator="orange",
                        title=_("Long-term Posting Alert")
                    )
    
    def validate_rates(self) -> None:
        """Validate billing rates"""
        if self.rate and self.rate < 0:
            frappe.throw(_("Rate cannot be negative"))
        
        if not self.rate:
            frappe.throw(_("Please specify a billing rate"))
    
    def validate_gdpr_consent(self) -> None:
        """Validate GDPR consent for EU data subjects"""
        if self.is_eu_country and not self.gdpr_consent_given:
            frappe.msgprint(
                _("GDPR consent is recommended for EU-resident freelancers. "
                  "Please ensure proper consent is obtained for data processing."),
                indicator="orange",
                title=_("GDPR Notice")
            )
    
    def check_minimum_wage_compliance(self) -> None:
        """Check if rate meets minimum wage requirements"""
        if not self.rate or not self.billing_type:
            return
        
        # Get minimum wage for the working country
        company_doc = frappe.get_doc("Company", self.company)
        work_country = company_doc.country if company_doc else None
        
        if not work_country:
            return
        
        # EU Minimum Wages 2026 (estimated, EUR/month)
        eu_minimum_wages = {
            "Netherlands": 2100,
            "Germany": 2050,
            "France": 1900,
            "Belgium": 2000,
            "Luxembourg": 2700,
            "Ireland": 2200,
            "Spain": 1450,
            "Italy": 1300,  # No statutory minimum, sectoral
            "Portugal": 1000,
            "Greece": 950,
            "Poland": 850,
            "Czech Republic": 750,
            "Romania": 650,
            "Bulgaria": 500,
        }
        
        min_wage = eu_minimum_wages.get(work_country)
        if not min_wage:
            return
        
        # Convert rate to monthly equivalent
        monthly_rate = self._convert_to_monthly_rate()
        
        if monthly_rate and monthly_rate < min_wage:
            frappe.msgprint(
                _("Warning: The effective monthly rate (€{0}) may be below the minimum wage "
                  "in {1} (€{2}/month). Please verify compliance with local labor laws.").format(
                    flt(monthly_rate, 2), work_country, min_wage
                ),
                indicator="red",
                title=_("Minimum Wage Alert")
            )
        else:
            self.minimum_wage_compliance = 1
    
    def _convert_to_monthly_rate(self) -> float:
        """Convert billing rate to monthly equivalent"""
        if not self.rate:
            return 0
        
        # Assuming standard working hours
        conversions = {
            "Hourly": self.rate * 160,  # 40 hours/week * 4 weeks
            "Daily": self.rate * 22,     # ~22 working days/month
            "Weekly": self.rate * 4.33,  # Weeks per month
            "Monthly": self.rate,
            "Project-Based": self.rate,  # Cannot convert, use as-is
            "Milestone-Based": self.rate
        }
        
        return conversions.get(self.billing_type, self.rate)
    
    def create_gdpr_consent_log(self) -> None:
        """Log GDPR consent changes"""
        if self.has_value_changed("gdpr_consent_given"):
            frappe.get_doc({
                "doctype": "GDPR Consent Log",
                "freelancer": self.name,
                "user": frappe.session.user,
                "action": "Consent Given" if self.gdpr_consent_given else "Consent Withdrawn",
                "timestamp": frappe.utils.now_datetime(),
                "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None,
                "purposes": self.data_processing_purposes
            }).insert(ignore_permissions=True)
    
    def sync_with_linked_employee(self) -> None:
        """Sync data with linked employee for hybrid workers"""
        if self.linked_employee:
            # Update employee with freelancer status
            frappe.db.set_value(
                "Employee",
                self.linked_employee,
                "custom_is_hybrid_worker",
                1,
                update_modified=False
            )
    
    def update_compliance_status(self) -> None:
        """Update overall compliance status"""
        compliance_issues = []
        
        if self.is_eu_country and not self.gdpr_consent_given:
            compliance_issues.append("GDPR consent missing")
        
        if self.residency_status == "EU Posted Worker" and not self.a1_certificate:
            compliance_issues.append("A1 certificate missing")
        
        if self.vat_registered and not self.vat_number:
            compliance_issues.append("VAT number missing")
        
        if compliance_issues:
            frappe.db.set_value(
                "Freelancer",
                self.name,
                "compliance_notes",
                ", ".join(compliance_issues),
                update_modified=False
            )
    
    def create_user_if_needed(self) -> None:
        """Create portal user for freelancer self-service"""
        if self.user_id:
            return
        
        # Check if user creation is enabled in settings
        settings = frappe.get_single("HR Settings")
        if not getattr(settings, "auto_create_freelancer_user", False):
            return
        
        if not frappe.db.exists("User", self.email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": self.email,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "send_welcome_email": 0,
                "user_type": "Website User",
                "roles": [{"role": "Freelancer"}]
            })
            user.insert(ignore_permissions=True)
            self.user_id = user.name
            frappe.db.set_value("Freelancer", self.name, "user_id", user.name)
    
    def send_welcome_email(self) -> None:
        """Send welcome email to new freelancer"""
        if not self.email:
            return
        
        try:
            frappe.sendmail(
                recipients=[self.email],
                subject=_("Welcome to {0}").format(self.company),
                template="freelancer_welcome",
                args={
                    "freelancer_name": self.full_name,
                    "company": self.company,
                    "onboarding_date": self.onboarding_date or nowdate()
                },
                delayed=True
            )
        except Exception as e:
            frappe.log_error(f"Failed to send welcome email: {str(e)}")
    
    def log_onboarding(self) -> None:
        """Create onboarding log entry"""
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Freelancer",
            "reference_name": self.name,
            "content": _("Freelancer profile created. Status: {0}").format(self.status)
        }).insert(ignore_permissions=True)


# Standalone functions for hooks and API
def validate_freelancer(doc: Freelancer, method: str = None) -> None:
    """Hook for validate event"""
    doc.validate()


def on_update(doc: Freelancer, method: str = None) -> None:
    """Hook for on_update event"""
    pass  # Main logic in document class


def after_insert(doc: Freelancer, method: str = None) -> None:
    """Hook for after_insert event"""
    pass  # Main logic in document class


@frappe.whitelist()
def create_contract(freelancer: str) -> str:
    """
    Create a new contract for a freelancer
    
    Args:
        freelancer: Freelancer document name
        
    Returns:
        Name of created contract
    """
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    
    contract = frappe.get_doc({
        "doctype": "Freelancer Contract",
        "freelancer": freelancer,
        "freelancer_name": freelancer_doc.full_name,
        "company": freelancer_doc.company,
        "currency": freelancer_doc.currency,
        "billing_type": freelancer_doc.billing_type,
        "rate": freelancer_doc.rate,
        "status": "Draft"
    })
    contract.insert()
    
    return contract.name


@frappe.whitelist()
def create_payment(freelancer: str, contract: str = None) -> str:
    """
    Create a new payment for a freelancer
    
    Args:
        freelancer: Freelancer document name
        contract: Optional contract reference
        
    Returns:
        Name of created payment
    """
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    
    payment = frappe.get_doc({
        "doctype": "Freelancer Payment",
        "freelancer": freelancer,
        "freelancer_name": freelancer_doc.full_name,
        "company": freelancer_doc.company,
        "contract": contract,
        "currency": freelancer_doc.currency,
        "billing_type": freelancer_doc.billing_type,
        "rate": freelancer_doc.rate,
        "withholding_tax_rate": freelancer_doc.withholding_tax_rate,
        "vat_rate": freelancer_doc.vat_rate if freelancer_doc.vat_registered else 0,
        "reverse_charge": freelancer_doc.reverse_charge_applicable,
        "status": "Draft"
    })
    payment.insert()
    
    return payment.name


@frappe.whitelist()
def export_gdpr_data(freelancer: str, format: str = "json") -> Dict[str, Any]:
    """
    Export all freelancer data for GDPR data portability
    
    Args:
        freelancer: Freelancer document name
        format: Export format (json or csv)
        
    Returns:
        Dictionary containing all freelancer data
    """
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    
    # Check permission
    if not frappe.has_permission("Freelancer", "read", freelancer_doc):
        frappe.throw(_("You don't have permission to export this data"))
    
    # Gather all related data
    data = {
        "personal_information": {
            "name": freelancer_doc.full_name,
            "email": freelancer_doc.email,
            "phone": freelancer_doc.phone,
            "mobile": freelancer_doc.mobile,
            "address": freelancer_doc.address,
            "city": freelancer_doc.city,
            "country": freelancer_doc.country,
            "date_of_birth": str(freelancer_doc.date_of_birth) if freelancer_doc.date_of_birth else None
        },
        "professional_information": {
            "worker_type": freelancer_doc.worker_type,
            "specialization": freelancer_doc.specialization,
            "company": freelancer_doc.company,
            "status": freelancer_doc.status
        },
        "tax_information": {
            "tax_residency_country": freelancer_doc.tax_residency_country,
            "vat_registered": freelancer_doc.vat_registered,
            "vat_number": freelancer_doc.vat_number
        },
        "contracts": [],
        "payments": [],
        "consent_log": [],
        "export_metadata": {
            "exported_at": frappe.utils.now_datetime(),
            "exported_by": frappe.session.user,
            "format": format
        }
    }
    
    # Get contracts
    contracts = frappe.get_all(
        "Freelancer Contract",
        filters={"freelancer": freelancer},
        fields=["name", "title", "start_date", "end_date", "status", "total_value"]
    )
    data["contracts"] = contracts
    
    # Get payments
    payments = frappe.get_all(
        "Freelancer Payment",
        filters={"freelancer": freelancer},
        fields=["name", "posting_date", "gross_amount", "net_amount", "status"]
    )
    data["payments"] = payments
    
    # Get consent log
    consent_logs = frappe.get_all(
        "GDPR Consent Log",
        filters={"freelancer": freelancer},
        fields=["action", "timestamp", "purposes"]
    )
    data["consent_log"] = consent_logs
    
    # Log the export
    frappe.get_doc({
        "doctype": "GDPR Consent Log",
        "freelancer": freelancer,
        "user": frappe.session.user,
        "action": "Data Export",
        "timestamp": frappe.utils.now_datetime(),
        "purposes": f"GDPR data portability export in {format} format"
    }).insert(ignore_permissions=True)
    
    return data


@frappe.whitelist()
def get_freelancer_summary(freelancer: str) -> Dict[str, Any]:
    """
    Get summary statistics for a freelancer
    
    Args:
        freelancer: Freelancer document name
        
    Returns:
        Dictionary with summary statistics
    """
    # Total contracts
    total_contracts = frappe.db.count(
        "Freelancer Contract",
        {"freelancer": freelancer}
    )
    
    active_contracts = frappe.db.count(
        "Freelancer Contract",
        {"freelancer": freelancer, "status": "Active"}
    )
    
    # Total payments
    total_paid = frappe.db.sql("""
        SELECT COALESCE(SUM(net_amount), 0) as total
        FROM `tabFreelancer Payment`
        WHERE freelancer = %s AND docstatus = 1
    """, freelancer, as_dict=True)[0].total
    
    pending_payments = frappe.db.count(
        "Freelancer Payment",
        {"freelancer": freelancer, "status": "Pending"}
    )
    
    # Compliance status
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    
    return {
        "total_contracts": total_contracts,
        "active_contracts": active_contracts,
        "total_paid": total_paid,
        "pending_payments": pending_payments,
        "residency_status": freelancer_doc.residency_status,
        "is_eu": freelancer_doc.is_eu_country,
        "gdpr_consent": freelancer_doc.gdpr_consent_given,
        "vat_registered": freelancer_doc.vat_registered
    }


@frappe.whitelist()
def validate_vat_number_vies(vat_number: str, country_code: str) -> Dict[str, Any]:
    """
    Validate EU VAT number using VIES API
    
    Args:
        vat_number: VAT number to validate
        country_code: Two-letter country code
        
    Returns:
        Validation result
    """
    # Note: This is a mock implementation
    # In production, integrate with actual VIES API
    # https://ec.europa.eu/taxation_customs/vies/
    
    try:
        # Mock validation
        vat_clean = vat_number.upper().replace(" ", "").replace("-", "")
        
        # Basic format check
        if not vat_clean.startswith(country_code):
            return {
                "valid": False,
                "error": f"VAT number should start with country code {country_code}"
            }
        
        # Mock: Consider valid if proper length
        min_lengths = {"NL": 12, "DE": 11, "FR": 13, "BE": 12}
        min_len = min_lengths.get(country_code, 8)
        
        if len(vat_clean) < min_len:
            return {
                "valid": False,
                "error": f"VAT number too short for {country_code}"
            }
        
        return {
            "valid": True,
            "country_code": country_code,
            "vat_number": vat_clean,
            "message": "VAT number format is valid (VIES verification recommended)",
            "disclaimer": "This is a format check only. For official validation, use the EU VIES service."
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }
