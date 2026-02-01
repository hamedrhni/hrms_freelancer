"""
GDPR Consent Log DocType Controller
Immutable audit log for GDPR compliance tracking
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

if TYPE_CHECKING:
    from frappe.types import DF


class GDPRConsentLog(Document):
    """
    GDPR Consent Log for tracking data subject consent
    
    This is an immutable audit log that cannot be edited or deleted
    after creation, ensuring compliance with GDPR record-keeping requirements.
    """
    
    if TYPE_CHECKING:
        freelancer: DF.Link
        action: DF.Literal["Consent Given", "Consent Withdrawn", "Data Export", 
                          "Data Deletion Request", "Data Rectification", 
                          "Processing Objection", "Consent Updated"]
        timestamp: DF.Datetime
        user: DF.Link
        ip_address: DF.Data | None
        purposes: DF.SmallText | None
        legal_basis: DF.Data | None

    def validate(self) -> None:
        """Validate consent log entry"""
        self.validate_immutability()
        self.set_defaults()
    
    def validate_immutability(self) -> None:
        """Ensure existing records cannot be modified"""
        if not self.is_new():
            frappe.throw(
                _("GDPR Consent Logs cannot be modified after creation. "
                  "Create a new log entry instead.")
            )
    
    def set_defaults(self) -> None:
        """Set default values"""
        if not self.timestamp:
            self.timestamp = now_datetime()
        
        if not self.user:
            self.user = frappe.session.user
        
        # Capture IP address
        if not self.ip_address and hasattr(frappe.local, 'request'):
            self.ip_address = frappe.local.request.remote_addr
    
    def on_trash(self) -> None:
        """Prevent deletion of consent logs"""
        frappe.throw(
            _("GDPR Consent Logs cannot be deleted. "
              "This is required for compliance with GDPR Article 7(1).")
        )


@frappe.whitelist()
def log_consent_action(
    freelancer: str,
    action: str,
    purposes: str = None,
    legal_basis: str = None,
    data_categories: str = None,
    consent_method: str = None,
    notes: str = None
) -> str:
    """
    Create a new GDPR consent log entry
    
    Args:
        freelancer: Freelancer document name
        action: Type of consent action
        purposes: Processing purposes
        legal_basis: GDPR legal basis
        data_categories: Categories of data
        consent_method: How consent was obtained
        notes: Additional notes
        
    Returns:
        Name of created log entry
    """
    log = frappe.get_doc({
        "doctype": "GDPR Consent Log",
        "freelancer": freelancer,
        "action": action,
        "purposes": purposes,
        "legal_basis": legal_basis,
        "data_categories": data_categories,
        "consent_method": consent_method,
        "notes": notes
    })
    log.insert(ignore_permissions=True)
    
    return log.name


@frappe.whitelist()
def get_consent_history(freelancer: str) -> List[Dict[str, Any]]:
    """
    Get complete consent history for a freelancer
    
    Args:
        freelancer: Freelancer document name
        
    Returns:
        List of consent log entries
    """
    logs = frappe.get_all(
        "GDPR Consent Log",
        filters={"freelancer": freelancer},
        fields=["name", "action", "timestamp", "user", "purposes", 
                "legal_basis", "consent_method"],
        order_by="timestamp desc"
    )
    
    return logs


@frappe.whitelist()
def export_consent_data(freelancer: str) -> Dict[str, Any]:
    """
    Export all GDPR-related data for a freelancer (data portability)
    
    Args:
        freelancer: Freelancer document name
        
    Returns:
        Complete data export in portable format
    """
    from hrms_freelancer.freelancer.doctype.freelancer.freelancer import export_gdpr_data
    
    # Log the export action
    log_consent_action(
        freelancer=freelancer,
        action="Data Export",
        purposes="GDPR Article 20 - Right to data portability",
        legal_basis="Consent (Art. 6(1)(a))",
        consent_method="API/System"
    )
    
    return export_gdpr_data(freelancer, format="json")


@frappe.whitelist()
def submit_deletion_request(freelancer: str, reason: str = None) -> Dict[str, Any]:
    """
    Submit a data deletion request (right to erasure)
    
    Args:
        freelancer: Freelancer document name
        reason: Reason for deletion request
        
    Returns:
        Status of deletion request
    """
    # Log the deletion request
    log_consent_action(
        freelancer=freelancer,
        action="Data Deletion Request",
        purposes="GDPR Article 17 - Right to erasure",
        legal_basis="Consent (Art. 6(1)(a))",
        notes=reason
    )
    
    # Check if deletion is possible
    blocking_reasons = []
    
    # Check for active contracts
    active_contracts = frappe.db.count(
        "Freelancer Contract",
        {"freelancer": freelancer, "status": ["in", ["Active", "Pending Approval"]]}
    )
    if active_contracts > 0:
        blocking_reasons.append(f"Active contracts exist ({active_contracts})")
    
    # Check for pending payments
    pending_payments = frappe.db.count(
        "Freelancer Payment",
        {"freelancer": freelancer, "status": ["in", ["Draft", "Pending", "Approved", "Processing"]]}
    )
    if pending_payments > 0:
        blocking_reasons.append(f"Pending payments exist ({pending_payments})")
    
    # Tax retention requirements
    blocking_reasons.append(
        "Tax compliance: Data must be retained for 7 years per legal obligations"
    )
    
    if blocking_reasons:
        return {
            "status": "pending_review",
            "message": "Deletion request logged but cannot be immediately processed",
            "blocking_reasons": blocking_reasons,
            "recommendation": "Data will be anonymized after retention period expires"
        }
    
    return {
        "status": "approved",
        "message": "Deletion request can proceed. Manual review required.",
        "next_steps": ["Review by compliance officer", "Data anonymization", "Confirmation"]
    }
