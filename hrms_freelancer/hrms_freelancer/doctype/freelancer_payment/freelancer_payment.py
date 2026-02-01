"""
Freelancer Payment DocType Controller
Handles invoice-based payments with tax calculations for EU and international freelancers
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import date, datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days, flt, cint, money_in_words

if TYPE_CHECKING:
    from frappe.types import DF


class FreelancerPayment(Document):
    """
    Freelancer Payment DocType
    
    Manages invoice-based payments with support for:
    - EU VAT reverse charge
    - Withholding taxes for non-EU freelancers
    - Multi-currency payments
    - ERPNext accounting integration
    """
    
    if TYPE_CHECKING:
        naming_series: DF.Literal["HR-PAY-.YYYY.-", "FRL-PAY-.YYYY.-.#####"]
        title: DF.Data | None
        freelancer: DF.Link
        freelancer_name: DF.Data | None
        company: DF.Link
        contract: DF.Link | None
        posting_date: DF.Date
        status: DF.Literal["Draft", "Pending Approval", "Approved", "Invoice Received", "Processing", "Paid", "Rejected", "Cancelled"]
        billing_type: DF.Literal["Hourly", "Daily", "Weekly", "Monthly", "Project-Based", "Milestone-Based"]
        rate: DF.Currency
        quantity: DF.Float
        currency: DF.Link
        base_amount: DF.Currency | None
        exchange_rate: DF.Float
        gross_amount: DF.Currency | None
        vat_applicable: DF.Check
        vat_rate: DF.Percent
        vat_amount: DF.Currency | None
        reverse_charge: DF.Check
        withholding_tax_applicable: DF.Check
        withholding_tax_rate: DF.Percent
        withholding_tax_amount: DF.Currency | None
        net_amount: DF.Currency | None
        total_expenses: DF.Currency | None

    def validate(self) -> None:
        """Validate payment data before save"""
        self.set_title()
        self.validate_freelancer_status()
        self.validate_contract()
        self.validate_dates()
        self.calculate_amounts()
        self.set_compliance_notes()
        self.validate_minimum_amount()
    
    def before_submit(self) -> None:
        """Actions before submitting the payment"""
        if self.status == "Draft":
            self.status = "Pending Approval"
    
    def on_submit(self) -> None:
        """Actions after payment submission"""
        self.update_contract_totals()
        self.notify_approval_required()
    
    def on_cancel(self) -> None:
        """Actions after payment cancellation"""
        self.status = "Cancelled"
        self.reverse_contract_totals()
        self.cancel_linked_documents()
    
    def set_title(self) -> None:
        """Set payment title"""
        self.title = f"{self.freelancer_name or 'Freelancer'} - {self.posting_date}"
    
    def validate_freelancer_status(self) -> None:
        """Ensure freelancer is active"""
        if self.freelancer:
            status = frappe.db.get_value("Freelancer", self.freelancer, "status")
            if status in ["Blacklisted", "Offboarding"]:
                frappe.throw(
                    _("Cannot create payment for freelancer with status: {0}").format(status)
                )
    
    def validate_contract(self) -> None:
        """Validate contract reference if provided"""
        if self.contract:
            contract_status = frappe.db.get_value(
                "Freelancer Contract", self.contract, "status"
            )
            if contract_status not in ["Active", "Completed"]:
                frappe.msgprint(
                    _("Warning: Contract status is {0}. Payments are typically "
                      "made against active contracts.").format(contract_status),
                    indicator="orange"
                )
            
            # Verify contract belongs to this freelancer
            contract_freelancer = frappe.db.get_value(
                "Freelancer Contract", self.contract, "freelancer"
            )
            if contract_freelancer != self.freelancer:
                frappe.throw(_("Contract does not belong to selected freelancer"))
    
    def validate_dates(self) -> None:
        """Validate payment period dates"""
        if self.payment_period_start and self.payment_period_end:
            if getdate(self.payment_period_end) < getdate(self.payment_period_start):
                frappe.throw(_("Period end date cannot be before start date"))
        
        # Set due date based on payment terms
        if not self.due_date and self.posting_date:
            # Default to 30 days from posting
            days = 30
            if self.contract:
                payment_terms = frappe.db.get_value(
                    "Freelancer Contract", self.contract, "payment_terms"
                )
                if payment_terms:
                    # Get days from payment terms template
                    terms_doc = frappe.get_doc("Payment Terms Template", payment_terms)
                    if terms_doc.terms:
                        days = terms_doc.terms[0].credit_days or 30
            
            self.due_date = add_days(self.posting_date, days)
    
    def calculate_amounts(self) -> None:
        """Calculate all payment amounts including taxes"""
        # Base amount
        self.base_amount = flt(self.rate) * flt(self.quantity)
        
        # Add line items if present
        if hasattr(self, 'payment_items') and self.payment_items:
            items_total = sum(flt(item.amount) for item in self.payment_items)
            if items_total > 0:
                self.base_amount = items_total
        
        # Add milestone amounts if milestone-based
        if self.billing_type == "Milestone-Based" and hasattr(self, 'milestones') and self.milestones:
            milestone_total = sum(flt(m.amount) for m in self.milestones)
            if milestone_total > 0:
                self.base_amount = milestone_total
        
        # Calculate expenses
        self.total_expenses = 0
        if hasattr(self, 'expense_reimbursements') and self.expense_reimbursements:
            self.total_expenses = sum(flt(e.amount) for e in self.expense_reimbursements)
        
        # Gross amount (base + expenses)
        self.gross_amount = flt(self.base_amount) + flt(self.total_expenses)
        
        # VAT calculation
        self.vat_amount = 0
        if self.vat_applicable and not self.reverse_charge:
            self.vat_amount = flt(self.gross_amount) * flt(self.vat_rate) / 100
        
        # Gross with VAT
        self.gross_with_vat = flt(self.gross_amount) + flt(self.vat_amount)
        
        # Withholding tax calculation
        self.withholding_tax_amount = 0
        if self.withholding_tax_applicable and self.withholding_tax_rate > 0:
            # Withholding is typically on gross amount (before VAT)
            self.withholding_tax_amount = flt(self.gross_amount) * flt(self.withholding_tax_rate) / 100
        
        # Total deductions
        self.total_deductions = flt(self.withholding_tax_amount)
        
        # Net payable amount
        # If reverse charge: Freelancer receives gross amount (company handles VAT)
        # If normal VAT: Freelancer receives gross + VAT
        # Withholding is always deducted from payment
        if self.reverse_charge:
            self.net_amount = flt(self.gross_amount) - flt(self.withholding_tax_amount)
        else:
            self.net_amount = flt(self.gross_with_vat) - flt(self.withholding_tax_amount)
        
        # Company currency amounts
        self.base_amount_company_currency = flt(self.base_amount) * flt(self.exchange_rate or 1)
        self.net_amount_company_currency = flt(self.net_amount) * flt(self.exchange_rate or 1)
    
    def set_compliance_notes(self) -> None:
        """Set compliance notes based on payment characteristics"""
        notes = []
        
        # EU reverse charge
        if self.reverse_charge:
            notes.append(
                "EU Reverse Charge Applied: VAT is 0% on invoice. "
                "The recipient (company) is responsible for VAT accounting."
            )
        
        # Withholding tax
        if self.withholding_tax_applicable and self.withholding_tax_amount > 0:
            notes.append(
                f"Withholding Tax: {self.withholding_tax_rate}% = {self.currency} {self.withholding_tax_amount:.2f} "
                f"will be remitted to tax authorities."
            )
            
            if self.tax_treaty:
                treaty_name = frappe.db.get_value("Tax Treaty", self.tax_treaty, "treaty_name")
                notes.append(f"Tax Treaty Applied: {treaty_name}")
        
        # 1099 reporting
        if self.form_1099_applicable:
            notes.append(
                "US 1099 Reporting: This payment may be reportable to the IRS. "
                "Ensure W-8BEN or W-9 is on file."
            )
        
        # Large payment warning
        if self.gross_amount and self.gross_amount > 10000:
            notes.append(
                "Large Payment: May require additional compliance checks. "
                "Verify anti-money laundering (AML) requirements."
            )
        
        self.compliance_notes = "\n".join(notes) if notes else None
    
    def validate_minimum_amount(self) -> None:
        """Validate payment meets minimum thresholds"""
        if self.net_amount and self.net_amount < 0:
            frappe.throw(_("Net payable amount cannot be negative"))
        
        # Warn about very small payments
        if self.net_amount and self.net_amount < 10:
            frappe.msgprint(
                _("Warning: Payment amount is very small ({0}). "
                  "Consider batching with other payments.").format(self.net_amount),
                indicator="orange"
            )
    
    def update_contract_totals(self) -> None:
        """Update contract totals after payment submission"""
        if self.contract:
            # Update total invoiced
            frappe.db.sql("""
                UPDATE `tabFreelancer Contract`
                SET total_invoiced = COALESCE(total_invoiced, 0) + %s
                WHERE name = %s
            """, (self.gross_amount, self.contract))
    
    def reverse_contract_totals(self) -> None:
        """Reverse contract totals on cancellation"""
        if self.contract:
            frappe.db.sql("""
                UPDATE `tabFreelancer Contract`
                SET total_invoiced = COALESCE(total_invoiced, 0) - %s
                WHERE name = %s
            """, (self.gross_amount, self.contract))
    
    def notify_approval_required(self) -> None:
        """Send notification for payment approval"""
        # Get approvers
        approvers = get_payment_approvers(self.company)
        
        for approver in approvers:
            frappe.publish_realtime(
                "payment_approval_required",
                {
                    "payment": self.name,
                    "freelancer": self.freelancer_name,
                    "amount": self.gross_amount,
                    "currency": self.currency
                },
                user=approver
            )
    
    def cancel_linked_documents(self) -> None:
        """Cancel linked accounting documents"""
        if self.erp_invoice:
            invoice = frappe.get_doc("Purchase Invoice", self.erp_invoice)
            if invoice.docstatus == 1:
                invoice.cancel()
        
        if self.journal_entry:
            je = frappe.get_doc("Journal Entry", self.journal_entry)
            if je.docstatus == 1:
                je.cancel()


# Hook functions
def validate_payment(doc: FreelancerPayment, method: str = None) -> None:
    """Hook for validate event"""
    doc.validate()


def on_submit(doc: FreelancerPayment, method: str = None) -> None:
    """Hook for on_submit event"""
    pass


def on_cancel(doc: FreelancerPayment, method: str = None) -> None:
    """Hook for on_cancel event"""
    pass


def get_payment_approvers(company: str) -> List[str]:
    """Get list of users who can approve payments"""
    # Get users with Freelancer Accountant or HR Manager role
    approvers = frappe.db.sql("""
        SELECT DISTINCT u.name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE hr.role IN ('Freelancer Accountant', 'HR Manager', 'System Manager')
        AND u.enabled = 1
    """, as_dict=True)
    
    return [a.name for a in approvers]


@frappe.whitelist()
def approve_payment(payment: str) -> None:
    """
    Approve a freelancer payment
    
    Args:
        payment: Payment document name
    """
    doc = frappe.get_doc("Freelancer Payment", payment)
    
    if doc.docstatus != 1:
        frappe.throw(_("Payment must be submitted before approval"))
    
    if doc.status not in ["Pending Approval", "Invoice Received"]:
        frappe.throw(_("Payment is not pending approval"))
    
    # Check permission
    if not frappe.has_permission("Freelancer Payment", "submit", doc):
        frappe.throw(_("You don't have permission to approve payments"))
    
    doc.db_set("status", "Approved")
    doc.db_set("approved_by", frappe.session.user)
    doc.db_set("approval_date", frappe.utils.now_datetime())
    
    # Notify freelancer
    freelancer = frappe.get_doc("Freelancer", doc.freelancer)
    if freelancer.email:
        frappe.sendmail(
            recipients=[freelancer.email],
            subject=_("Payment Approved: {0}").format(doc.name),
            template="payment_approved",
            args={
                "freelancer_name": freelancer.full_name,
                "payment_name": doc.name,
                "amount": f"{doc.currency} {doc.net_amount:,.2f}",
                "due_date": doc.due_date
            },
            delayed=True
        )
    
    frappe.msgprint(_("Payment approved"), indicator="green")


@frappe.whitelist()
def reject_payment(payment: str, reason: str = None) -> None:
    """
    Reject a freelancer payment
    
    Args:
        payment: Payment document name
        reason: Rejection reason
    """
    doc = frappe.get_doc("Freelancer Payment", payment)
    
    if doc.docstatus != 1:
        frappe.throw(_("Payment must be submitted before rejection"))
    
    if doc.status not in ["Pending Approval", "Invoice Received"]:
        frappe.throw(_("Payment is not pending approval"))
    
    doc.db_set("status", "Rejected")
    doc.db_set("rejection_reason", reason or "Not specified")
    
    frappe.msgprint(_("Payment rejected"), indicator="red")


@frappe.whitelist()
def create_purchase_invoice(payment: str) -> str:
    """
    Create ERPNext Purchase Invoice from payment
    
    Args:
        payment: Payment document name
        
    Returns:
        Name of created Purchase Invoice
    """
    doc = frappe.get_doc("Freelancer Payment", payment)
    
    if doc.docstatus != 1:
        frappe.throw(_("Payment must be submitted first"))
    
    if doc.erp_invoice:
        frappe.throw(_("Purchase Invoice already created: {0}").format(doc.erp_invoice))
    
    # Get freelancer details for supplier
    freelancer = frappe.get_doc("Freelancer", doc.freelancer)
    
    # Find or create supplier
    supplier = get_or_create_supplier(freelancer)
    
    # Get expense account
    company_doc = frappe.get_doc("Company", doc.company)
    expense_account = company_doc.default_expense_account or \
                      frappe.db.get_value("Account", 
                          {"company": doc.company, "account_type": "Expense Account"}, 
                          "name")
    
    # Build invoice items
    items = []
    
    # Main service item
    items.append({
        "item_name": f"Services - {freelancer.full_name}",
        "description": doc.description or f"Freelancer services for period {doc.payment_period_start} to {doc.payment_period_end}",
        "qty": doc.quantity,
        "rate": doc.rate,
        "amount": doc.base_amount,
        "expense_account": expense_account
    })
    
    # Add expenses
    if doc.total_expenses and doc.total_expenses > 0:
        items.append({
            "item_name": "Expense Reimbursement",
            "description": "Expense reimbursements",
            "qty": 1,
            "rate": doc.total_expenses,
            "amount": doc.total_expenses,
            "expense_account": expense_account
        })
    
    # Create Purchase Invoice
    invoice = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": supplier,
        "company": doc.company,
        "posting_date": doc.posting_date,
        "due_date": doc.due_date,
        "bill_no": doc.invoice_number,
        "bill_date": doc.invoice_date or doc.posting_date,
        "currency": doc.currency,
        "conversion_rate": doc.exchange_rate or 1,
        "buying_price_list": frappe.db.get_single_value("Buying Settings", "buying_price_list"),
        "items": items,
        "taxes": []
    })
    
    # Add VAT if applicable (and not reverse charge)
    if doc.vat_applicable and not doc.reverse_charge and doc.vat_amount > 0:
        vat_account = get_vat_account(doc.company)
        if vat_account:
            invoice.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": vat_account,
                "description": f"VAT {doc.vat_rate}%",
                "rate": doc.vat_rate
            })
    
    # Add reverse charge info
    if doc.reverse_charge:
        invoice.remarks = "EU Reverse Charge - VAT to be self-assessed by recipient"
    
    invoice.insert()
    
    # Link back to payment
    doc.db_set("erp_invoice", invoice.name)
    
    frappe.msgprint(
        _("Purchase Invoice {0} created").format(invoice.name),
        indicator="green"
    )
    
    return invoice.name


@frappe.whitelist()
def create_withholding_journal_entry(payment: str) -> str:
    """
    Create Journal Entry for withholding tax
    
    Args:
        payment: Payment document name
        
    Returns:
        Name of created Journal Entry
    """
    doc = frappe.get_doc("Freelancer Payment", payment)
    
    if not doc.withholding_tax_applicable or doc.withholding_tax_amount <= 0:
        frappe.throw(_("No withholding tax applicable"))
    
    if doc.journal_entry:
        frappe.throw(_("Journal Entry already created: {0}").format(doc.journal_entry))
    
    company_doc = frappe.get_doc("Company", doc.company)
    
    # Get withholding tax liability account
    wht_account = frappe.db.get_value("Account", {
        "company": doc.company,
        "account_name": ["like", "%Withholding Tax%"]
    }, "name")
    
    if not wht_account:
        # Create account if not exists
        wht_account = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Withholding Tax Payable",
            "parent_account": company_doc.default_payable_account,
            "company": doc.company,
            "account_type": "Payable"
        }).insert().name
    
    # Create Journal Entry
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "company": doc.company,
        "posting_date": doc.posting_date,
        "user_remark": f"Withholding tax for {doc.freelancer_name} - Payment {doc.name}",
        "accounts": [
            {
                "account": company_doc.default_payable_account,
                "party_type": "Supplier",
                "party": get_or_create_supplier(frappe.get_doc("Freelancer", doc.freelancer)),
                "debit_in_account_currency": doc.withholding_tax_amount,
                "reference_type": "Freelancer Payment",
                "reference_name": doc.name
            },
            {
                "account": wht_account,
                "credit_in_account_currency": doc.withholding_tax_amount
            }
        ]
    })
    je.insert()
    
    doc.db_set("journal_entry", je.name)
    
    frappe.msgprint(
        _("Journal Entry {0} created for withholding tax").format(je.name),
        indicator="green"
    )
    
    return je.name


@frappe.whitelist()
def mark_as_paid(
    payment: str, 
    payment_date: str = None, 
    payment_reference: str = None
) -> None:
    """
    Mark payment as paid
    
    Args:
        payment: Payment document name
        payment_date: Actual payment date
        payment_reference: Payment reference/transaction ID
    """
    doc = frappe.get_doc("Freelancer Payment", payment)
    
    if doc.docstatus != 1:
        frappe.throw(_("Payment must be submitted first"))
    
    if doc.status not in ["Approved", "Processing"]:
        frappe.throw(_("Payment must be approved before marking as paid"))
    
    doc.db_set("status", "Paid")
    doc.db_set("payment_date", payment_date or nowdate())
    if payment_reference:
        doc.db_set("payment_reference", payment_reference)
    
    # Update contract totals
    if doc.contract:
        frappe.db.sql("""
            UPDATE `tabFreelancer Contract`
            SET total_paid = COALESCE(total_paid, 0) + %s,
                outstanding_amount = COALESCE(total_invoiced, 0) - COALESCE(total_paid, 0) - %s
            WHERE name = %s
        """, (doc.net_amount, doc.net_amount, doc.contract))
    
    # Notify freelancer
    freelancer = frappe.get_doc("Freelancer", doc.freelancer)
    if freelancer.email:
        frappe.sendmail(
            recipients=[freelancer.email],
            subject=_("Payment Completed: {0}").format(doc.name),
            template="payment_completed",
            args={
                "freelancer_name": freelancer.full_name,
                "payment_name": doc.name,
                "amount": f"{doc.currency} {doc.net_amount:,.2f}",
                "payment_date": doc.payment_date,
                "reference": doc.payment_reference
            },
            delayed=True
        )
    
    frappe.msgprint(_("Payment marked as paid"), indicator="green")


@frappe.whitelist()
def export_pdf(payment: str) -> str:
    """
    Export payment as PDF invoice
    
    Args:
        payment: Payment document name
        
    Returns:
        URL to generated PDF
    """
    doc = frappe.get_doc("Freelancer Payment", payment)
    
    # Generate PDF using print format
    pdf = frappe.get_print(
        "Freelancer Payment",
        payment,
        "Freelancer Payment Invoice",
        as_pdf=True
    )
    
    # Save as file
    file_name = f"Payment_{payment}_{nowdate()}.pdf"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "attached_to_doctype": "Freelancer Payment",
        "attached_to_name": payment,
        "content": pdf,
        "is_private": 1
    })
    file_doc.save()
    
    return file_doc.file_url


def get_or_create_supplier(freelancer: Document) -> str:
    """Get or create supplier from freelancer"""
    supplier_name = f"FRL-{freelancer.name}"
    
    if frappe.db.exists("Supplier", supplier_name):
        return supplier_name
    
    # Create new supplier
    supplier = frappe.get_doc({
        "doctype": "Supplier",
        "supplier_name": supplier_name,
        "supplier_group": "Services",
        "supplier_type": "Individual",
        "tax_id": freelancer.tax_id,
        "custom_freelancer": freelancer.name
    })
    supplier.insert(ignore_permissions=True)
    
    return supplier.name


def get_vat_account(company: str) -> Optional[str]:
    """Get VAT/Input Tax account for company"""
    return frappe.db.get_value("Account", {
        "company": company,
        "account_type": "Tax",
        "account_name": ["like", "%Input%VAT%"]
    }, "name") or frappe.db.get_value("Account", {
        "company": company,
        "account_type": "Tax"
    }, "name")


@frappe.whitelist()
def calculate_payment_preview(
    freelancer: str,
    rate: float,
    quantity: float,
    billing_type: str,
    expenses: float = 0
) -> Dict[str, Any]:
    """
    Calculate payment preview without creating document
    
    Args:
        freelancer: Freelancer document name
        rate: Billing rate
        quantity: Quantity (hours/days/units)
        billing_type: Billing type
        expenses: Total expenses
        
    Returns:
        Dictionary with calculated amounts
    """
    freelancer_doc = frappe.get_doc("Freelancer", freelancer)
    
    base_amount = flt(rate) * flt(quantity)
    gross_amount = base_amount + flt(expenses)
    
    # VAT
    vat_amount = 0
    if freelancer_doc.vat_registered and not freelancer_doc.reverse_charge_applicable:
        vat_amount = gross_amount * flt(freelancer_doc.vat_rate) / 100
    
    gross_with_vat = gross_amount + vat_amount
    
    # Withholding
    withholding_amount = 0
    if freelancer_doc.withholding_tax_rate > 0:
        withholding_amount = gross_amount * flt(freelancer_doc.withholding_tax_rate) / 100
    
    # Net
    if freelancer_doc.reverse_charge_applicable:
        net_amount = gross_amount - withholding_amount
    else:
        net_amount = gross_with_vat - withholding_amount
    
    return {
        "base_amount": base_amount,
        "expenses": expenses,
        "gross_amount": gross_amount,
        "vat_applicable": freelancer_doc.vat_registered,
        "vat_rate": freelancer_doc.vat_rate if freelancer_doc.vat_registered else 0,
        "vat_amount": vat_amount,
        "reverse_charge": freelancer_doc.reverse_charge_applicable,
        "gross_with_vat": gross_with_vat,
        "withholding_applicable": freelancer_doc.withholding_tax_rate > 0,
        "withholding_rate": freelancer_doc.withholding_tax_rate,
        "withholding_amount": withholding_amount,
        "net_amount": net_amount,
        "currency": freelancer_doc.currency,
        "residency_status": freelancer_doc.residency_status,
        "is_eu": freelancer_doc.is_eu_country
    }
