"""
Freelancer Contract DocType Controller
Handles contract management, milestones, and renewals
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days, add_months, flt, cint, date_diff

if TYPE_CHECKING:
    from frappe.types import DF


class FreelancerContract(Document):
    """
    Freelancer Contract DocType
    
    Manages contract terms, milestones, and billing for freelancers.
    Supports EU compliance features like reverse charge VAT.
    """
    
    if TYPE_CHECKING:
        naming_series: DF.Literal["HR-CTR-.YYYY.-", "CTR-.YYYY.-.#####"]
        title: DF.Data
        freelancer: DF.Link
        freelancer_name: DF.Data | None
        company: DF.Link
        status: DF.Literal["Draft", "Pending Approval", "Active", "On Hold", "Completed", "Terminated", "Expired", "Cancelled"]
        contract_type: DF.Literal["Fixed-Term", "Open-Ended", "Project-Based", "Retainer", "Call-Off"]
        start_date: DF.Date
        end_date: DF.Date | None
        billing_type: DF.Literal["Hourly", "Daily", "Weekly", "Monthly", "Project-Based", "Milestone-Based"]
        rate: DF.Currency
        currency: DF.Link
        total_value: DF.Currency | None
        withholding_tax_applicable: DF.Check
        withholding_tax_rate: DF.Percent
        vat_applicable: DF.Check
        vat_rate: DF.Percent
        reverse_charge: DF.Check

    def validate(self) -> None:
        """Validate contract data before save"""
        self.validate_dates()
        self.validate_rates()
        self.calculate_total_value()
        self.validate_milestones()
        self.check_overlapping_contracts()
        self.validate_expense_limits()
        self.set_compliance_notes()
    
    def before_submit(self) -> None:
        """Actions before submitting the contract"""
        self.validate_required_documents()
        self.status = "Active"
    
    def on_submit(self) -> None:
        """Actions after contract submission"""
        self.notify_parties()
        self.create_calendar_events()
        self.update_freelancer_status()
    
    def before_cancel(self) -> None:
        """Actions before cancelling the contract"""
        self.check_pending_payments()
        self.status = "Cancelled"
    
    def on_cancel(self) -> None:
        """Actions after contract cancellation"""
        self.cancel_pending_milestones()
        self.notify_cancellation()
    
    def validate_dates(self) -> None:
        """Validate contract date logic"""
        if self.start_date and self.end_date:
            if getdate(self.end_date) < getdate(self.start_date):
                frappe.throw(_("End date cannot be before start date"))
            
            # Check contract duration
            duration_days = date_diff(self.end_date, self.start_date)
            if duration_days > 1095:  # 3 years
                frappe.msgprint(
                    _("Contract duration exceeds 3 years ({0} days). "
                      "Consider reviewing for long-term contractor classification.").format(duration_days),
                    indicator="orange",
                    title=_("Duration Warning")
                )
        
        # Fixed-term contracts must have end date
        if self.contract_type == "Fixed-Term" and not self.end_date:
            frappe.throw(_("End date is required for fixed-term contracts"))
        
        # Project-based contracts should have end date
        if self.contract_type == "Project-Based" and not self.end_date:
            frappe.msgprint(
                _("Consider setting an expected end date for project-based contracts"),
                indicator="blue"
            )
    
    def validate_rates(self) -> None:
        """Validate billing rates"""
        if self.rate <= 0:
            frappe.throw(_("Rate must be greater than zero"))
        
        # Warn about unusually low or high rates
        if self.billing_type == "Hourly":
            if self.rate < 10:
                frappe.msgprint(
                    _("Hourly rate of {0} seems unusually low. Please verify.").format(self.rate),
                    indicator="orange"
                )
            elif self.rate > 500:
                frappe.msgprint(
                    _("Hourly rate of {0} is high. Ensure this is correct.").format(self.rate),
                    indicator="blue"
                )
    
    def calculate_total_value(self) -> None:
        """Calculate total contract value based on billing type and estimates"""
        if self.billing_type == "Hourly" and self.estimated_hours:
            self.total_value = flt(self.rate) * flt(self.estimated_hours)
        elif self.billing_type == "Daily" and self.estimated_days:
            self.total_value = flt(self.rate) * flt(self.estimated_days)
        elif self.billing_type == "Monthly" and self.start_date and self.end_date:
            months = date_diff(self.end_date, self.start_date) / 30
            self.total_value = flt(self.rate) * flt(months)
        elif self.billing_type == "Project-Based":
            self.total_value = flt(self.rate)  # Rate is total project value
        elif self.billing_type == "Milestone-Based":
            # Calculate from milestones
            if hasattr(self, 'milestones') and self.milestones:
                self.total_value = sum(flt(m.amount) for m in self.milestones)
        else:
            # Keep existing value or set to rate
            self.total_value = self.total_value or self.rate
    
    def validate_milestones(self) -> None:
        """Validate milestone amounts and dates"""
        if not hasattr(self, 'milestones') or not self.milestones:
            return
        
        total_milestone_value = sum(flt(m.amount) for m in self.milestones)
        
        # Check if milestones match contract value
        if self.billing_type == "Milestone-Based":
            if self.total_value and abs(total_milestone_value - self.total_value) > 0.01:
                frappe.msgprint(
                    _("Total milestone value ({0}) differs from contract value ({1})").format(
                        total_milestone_value, self.total_value
                    ),
                    indicator="orange"
                )
        
        # Validate milestone dates
        for milestone in self.milestones:
            if milestone.due_date:
                if self.start_date and getdate(milestone.due_date) < getdate(self.start_date):
                    frappe.throw(
                        _("Milestone '{0}' due date cannot be before contract start date").format(
                            milestone.title
                        )
                    )
                if self.end_date and getdate(milestone.due_date) > getdate(self.end_date):
                    frappe.throw(
                        _("Milestone '{0}' due date cannot be after contract end date").format(
                            milestone.title
                        )
                    )
    
    def check_overlapping_contracts(self) -> None:
        """Check for overlapping active contracts with same freelancer"""
        if self.status in ["Draft", "Cancelled", "Terminated", "Expired"]:
            return
        
        overlapping = frappe.db.sql("""
            SELECT name, title, start_date, end_date
            FROM `tabFreelancer Contract`
            WHERE freelancer = %s
            AND name != %s
            AND docstatus = 1
            AND status IN ('Active', 'Pending Approval')
            AND (
                (start_date <= %s AND (end_date IS NULL OR end_date >= %s))
                OR (start_date <= %s AND (end_date IS NULL OR end_date >= %s))
                OR (start_date >= %s AND (end_date IS NULL OR end_date <= %s))
            )
        """, (
            self.freelancer, self.name or "",
            self.start_date, self.start_date,
            self.end_date or "9999-12-31", self.end_date or "9999-12-31",
            self.start_date, self.end_date or "9999-12-31"
        ), as_dict=True)
        
        if overlapping:
            contracts = ", ".join([c.title for c in overlapping])
            frappe.msgprint(
                _("This freelancer has overlapping contracts: {0}. "
                  "Please verify this is intentional.").format(contracts),
                indicator="orange",
                title=_("Overlapping Contracts")
            )
    
    def validate_expense_limits(self) -> None:
        """Validate expense reimbursement settings"""
        if self.expense_reimbursement and self.expense_limit:
            if self.expense_limit <= 0:
                frappe.throw(_("Expense limit must be greater than zero"))
            
            # Warn if limit seems high
            if self.billing_type == "Monthly" and self.expense_limit > self.rate:
                frappe.msgprint(
                    _("Monthly expense limit ({0}) exceeds monthly rate ({1}). Please verify.").format(
                        self.expense_limit, self.rate
                    ),
                    indicator="orange"
                )
    
    def set_compliance_notes(self) -> None:
        """Set compliance notes based on contract terms"""
        notes = []
        
        if self.reverse_charge:
            notes.append("EU Reverse Charge: VAT shifted to recipient (0% on invoice)")
        
        if self.withholding_tax_applicable and self.withholding_tax_rate > 0:
            notes.append(f"Withholding Tax: {self.withholding_tax_rate}% will be deducted from payments")
        
        if self.tax_treaty:
            treaty_name = frappe.db.get_value("Tax Treaty", self.tax_treaty, "treaty_name")
            notes.append(f"Tax Treaty: {treaty_name}")
        
        # Contract duration warning for EU
        if self.start_date and self.end_date:
            duration_days = date_diff(self.end_date, self.start_date)
            if duration_days > 183:  # 6 months
                notes.append("Duration >6 months: May trigger permanent establishment considerations")
        
        self.compliance_notes = "\n".join(notes) if notes else None
    
    def validate_required_documents(self) -> None:
        """Validate required documents are attached before submission"""
        missing = []
        
        if not self.contract_document:
            missing.append("Signed Contract")
        
        if self.confidentiality_clause and not self.nda_document:
            frappe.msgprint(
                _("NDA document is recommended when confidentiality clause is enabled"),
                indicator="blue"
            )
        
        if missing:
            frappe.throw(
                _("Please attach required documents: {0}").format(", ".join(missing))
            )
    
    def notify_parties(self) -> None:
        """Send notification to relevant parties"""
        # Notify freelancer
        freelancer = frappe.get_doc("Freelancer", self.freelancer)
        if freelancer.email:
            try:
                frappe.sendmail(
                    recipients=[freelancer.email],
                    subject=_("Contract Activated: {0}").format(self.title),
                    template="contract_activated",
                    args={
                        "freelancer_name": freelancer.full_name,
                        "contract_title": self.title,
                        "company": self.company,
                        "start_date": self.start_date,
                        "end_date": self.end_date
                    },
                    delayed=True
                )
            except Exception as e:
                frappe.log_error(f"Failed to send contract notification: {str(e)}")
        
        # Notify contract manager
        if self.contract_manager:
            manager_email = frappe.db.get_value("Employee", self.contract_manager, "user_id")
            if manager_email:
                frappe.publish_realtime(
                    "contract_activated",
                    {"contract": self.name, "title": self.title},
                    user=manager_email
                )
    
    def create_calendar_events(self) -> None:
        """Create calendar events for key dates"""
        events = []
        
        # Contract end date reminder (2 weeks before)
        if self.end_date:
            reminder_date = add_days(self.end_date, -14)
            if getdate(reminder_date) > getdate(nowdate()):
                events.append({
                    "subject": _("Contract Ending: {0}").format(self.title),
                    "starts_on": reminder_date,
                    "ends_on": reminder_date,
                    "event_type": "Private",
                    "description": _("Contract {0} with {1} ends on {2}").format(
                        self.title, self.freelancer_name, self.end_date
                    )
                })
        
        # Milestone due dates
        if hasattr(self, 'milestones') and self.milestones:
            for milestone in self.milestones:
                if milestone.due_date and getdate(milestone.due_date) > getdate(nowdate()):
                    events.append({
                        "subject": _("Milestone Due: {0}").format(milestone.title),
                        "starts_on": milestone.due_date,
                        "ends_on": milestone.due_date,
                        "event_type": "Private",
                        "description": _("Milestone '{0}' for contract {1}").format(
                            milestone.title, self.title
                        )
                    })
        
        # Create events
        for event_data in events:
            event = frappe.get_doc({
                "doctype": "Event",
                "ref_doctype": "Freelancer Contract",
                "ref_docname": self.name,
                **event_data
            })
            event.insert(ignore_permissions=True)
    
    def update_freelancer_status(self) -> None:
        """Update freelancer status when contract becomes active"""
        freelancer = frappe.get_doc("Freelancer", self.freelancer)
        if freelancer.status in ["Onboarding", "Inactive"]:
            freelancer.status = "Active"
            freelancer.save(ignore_permissions=True)
    
    def check_pending_payments(self) -> None:
        """Check for pending payments before cancellation"""
        pending = frappe.db.count(
            "Freelancer Payment",
            {"contract": self.name, "status": ["in", ["Draft", "Pending", "Approved"]]}
        )
        
        if pending > 0:
            frappe.throw(
                _("Cannot cancel contract with {0} pending payments. "
                  "Please process or cancel payments first.").format(pending)
            )
    
    def cancel_pending_milestones(self) -> None:
        """Cancel any pending milestones"""
        if hasattr(self, 'milestones') and self.milestones:
            for milestone in self.milestones:
                if milestone.status in ["Pending", "In Progress"]:
                    milestone.status = "Cancelled"
    
    def notify_cancellation(self) -> None:
        """Notify parties of contract cancellation"""
        freelancer = frappe.get_doc("Freelancer", self.freelancer)
        if freelancer.email:
            try:
                frappe.sendmail(
                    recipients=[freelancer.email],
                    subject=_("Contract Cancelled: {0}").format(self.title),
                    template="contract_cancelled",
                    args={
                        "freelancer_name": freelancer.full_name,
                        "contract_title": self.title,
                        "company": self.company
                    },
                    delayed=True
                )
            except Exception as e:
                frappe.log_error(f"Failed to send cancellation notification: {str(e)}")


# Hook functions
def validate_contract(doc: FreelancerContract, method: str = None) -> None:
    """Hook for validate event"""
    doc.validate()


def on_submit(doc: FreelancerContract, method: str = None) -> None:
    """Hook for on_submit event"""
    pass  # Main logic in document class


def before_cancel(doc: FreelancerContract, method: str = None) -> None:
    """Hook for before_cancel event"""
    pass  # Main logic in document class


@frappe.whitelist()
def create_payment_from_contract(contract: str) -> str:
    """
    Create a payment record from contract
    
    Args:
        contract: Contract document name
        
    Returns:
        Name of created payment
    """
    contract_doc = frappe.get_doc("Freelancer Contract", contract)
    freelancer_doc = frappe.get_doc("Freelancer", contract_doc.freelancer)
    
    payment = frappe.get_doc({
        "doctype": "Freelancer Payment",
        "freelancer": contract_doc.freelancer,
        "freelancer_name": contract_doc.freelancer_name,
        "contract": contract,
        "company": contract_doc.company,
        "currency": contract_doc.currency,
        "billing_type": contract_doc.billing_type,
        "rate": contract_doc.rate,
        "withholding_tax_rate": contract_doc.withholding_tax_rate if contract_doc.withholding_tax_applicable else 0,
        "vat_rate": contract_doc.vat_rate if contract_doc.vat_applicable else 0,
        "reverse_charge": contract_doc.reverse_charge,
        "status": "Draft"
    })
    payment.insert()
    
    frappe.msgprint(
        _("Payment {0} created").format(payment.name),
        indicator="green"
    )
    
    return payment.name


@frappe.whitelist()
def renew_contract(contract: str, extension_months: int = 12) -> str:
    """
    Renew/extend a contract
    
    Args:
        contract: Contract document name
        extension_months: Number of months to extend
        
    Returns:
        Name of renewed contract
    """
    old_contract = frappe.get_doc("Freelancer Contract", contract)
    
    if old_contract.docstatus != 1:
        frappe.throw(_("Can only renew submitted contracts"))
    
    if old_contract.status not in ["Active", "Expired"]:
        frappe.throw(_("Can only renew active or expired contracts"))
    
    # Calculate new dates
    new_start = add_days(old_contract.end_date, 1) if old_contract.end_date else nowdate()
    new_end = add_months(new_start, extension_months)
    
    # Create new contract (amended)
    new_contract = frappe.copy_doc(old_contract)
    new_contract.start_date = new_start
    new_contract.end_date = new_end
    new_contract.status = "Draft"
    new_contract.amended_from = contract
    new_contract.total_invoiced = 0
    new_contract.total_paid = 0
    new_contract.outstanding_amount = 0
    new_contract.hours_logged = 0
    new_contract.milestones_completed = 0
    new_contract.completion_percentage = 0
    
    # Clear milestones (will be re-created)
    new_contract.milestones = []
    
    new_contract.insert()
    
    # Mark old contract as expired if it was active
    if old_contract.status == "Active":
        old_contract.db_set("status", "Expired")
    
    frappe.msgprint(
        _("Contract renewed. New contract: {0}").format(new_contract.name),
        indicator="green"
    )
    
    return new_contract.name


@frappe.whitelist()
def terminate_contract(
    contract: str,
    termination_reason: str = None,
    termination_date: str = None
) -> None:
    """
    Terminate a contract
    
    Args:
        contract: Contract document name
        termination_reason: Reason for termination
        termination_date: Effective termination date
    """
    contract_doc = frappe.get_doc("Freelancer Contract", contract)
    
    if contract_doc.docstatus != 1:
        frappe.throw(_("Can only terminate submitted contracts"))
    
    if contract_doc.status not in ["Active", "On Hold"]:
        frappe.throw(_("Can only terminate active or on-hold contracts"))
    
    # Set termination date
    term_date = getdate(termination_date) if termination_date else getdate(nowdate())
    
    # Check notice period
    if contract_doc.notice_period_days:
        min_term_date = add_days(nowdate(), contract_doc.notice_period_days)
        if term_date < getdate(min_term_date):
            frappe.msgprint(
                _("Notice period of {0} days applies. Minimum termination date: {1}").format(
                    contract_doc.notice_period_days, min_term_date
                ),
                indicator="orange"
            )
    
    # Update contract
    contract_doc.db_set("status", "Terminated")
    contract_doc.db_set("termination_date", term_date)
    
    # Add comment
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Freelancer Contract",
        "reference_name": contract,
        "content": _("Contract terminated. Reason: {0}").format(
            termination_reason or "Not specified"
        )
    }).insert(ignore_permissions=True)
    
    # Notify freelancer
    contract_doc.notify_cancellation()
    
    frappe.msgprint(
        _("Contract terminated effective {0}").format(term_date),
        indicator="orange"
    )


@frappe.whitelist()
def get_contract_summary(contract: str) -> Dict[str, Any]:
    """
    Get summary statistics for a contract
    
    Args:
        contract: Contract document name
        
    Returns:
        Dictionary with summary data
    """
    contract_doc = frappe.get_doc("Freelancer Contract", contract)
    
    # Payment statistics
    payments = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(CASE WHEN docstatus = 1 THEN gross_amount ELSE 0 END), 0) as total_invoiced,
            COALESCE(SUM(CASE WHEN docstatus = 1 AND status = 'Paid' THEN net_amount ELSE 0 END), 0) as total_paid,
            COUNT(CASE WHEN status IN ('Draft', 'Pending', 'Approved') THEN 1 END) as pending_count
        FROM `tabFreelancer Payment`
        WHERE contract = %s
    """, contract, as_dict=True)[0]
    
    # Milestone statistics
    milestones = frappe.db.sql("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed
        FROM `tabFreelancer Milestone`
        WHERE contract = %s
    """, contract, as_dict=True)[0]
    
    # Calculate remaining value
    remaining = flt(contract_doc.total_value or 0) - flt(payments.total_invoiced)
    
    # Days until expiry
    days_remaining = None
    if contract_doc.end_date:
        days_remaining = date_diff(contract_doc.end_date, nowdate())
    
    return {
        "contract_value": contract_doc.total_value,
        "total_invoiced": payments.total_invoiced,
        "total_paid": payments.total_paid,
        "outstanding": flt(payments.total_invoiced) - flt(payments.total_paid),
        "remaining_value": remaining,
        "pending_payments": payments.pending_count,
        "total_milestones": milestones.total,
        "completed_milestones": milestones.completed,
        "completion_pct": (milestones.completed / milestones.total * 100) if milestones.total else 0,
        "days_remaining": days_remaining,
        "status": contract_doc.status
    }


@frappe.whitelist()
def get_expiring_contracts(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get contracts expiring within specified days
    
    Args:
        days: Number of days to look ahead
        
    Returns:
        List of expiring contracts
    """
    expiry_date = add_days(nowdate(), days)
    
    contracts = frappe.db.sql("""
        SELECT 
            name, title, freelancer, freelancer_name, 
            company, end_date, status, total_value
        FROM `tabFreelancer Contract`
        WHERE docstatus = 1
        AND status = 'Active'
        AND end_date IS NOT NULL
        AND end_date <= %s
        AND end_date >= %s
        ORDER BY end_date ASC
    """, (expiry_date, nowdate()), as_dict=True)
    
    return contracts
