# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Daily scheduled tasks for HRMS Freelancer
"""

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, getdate


def update_exchange_rates():
    """Update currency exchange rates from ECB API"""
    try:
        from hrms_freelancer.utils.currency import update_exchange_rates_from_api
        
        result = update_exchange_rates_from_api()
        
        if result.get("updated", 0) > 0:
            frappe.log_error(
                title="Exchange Rates Updated",
                message=f"Updated {result['updated']} exchange rates from {result['source']}"
            )
        
        if result.get("errors"):
            frappe.log_error(
                title="Exchange Rate Update Errors",
                message="\n".join(result["errors"])
            )
            
    except Exception as e:
        frappe.log_error(
            title="Exchange Rate Update Failed",
            message=str(e)
        )


def process_pending_milestone_reminders():
    """Send reminders for milestones due within 3 days"""
    try:
        # Get milestones that are due within the next 3 days and not completed
        upcoming_milestones = frappe.get_all(
            "Freelancer Contract Milestone",
            filters={
                "due_date": ["between", [nowdate(), add_days(nowdate(), 3)]],
                "status": ["not in", ["Completed", "Cancelled"]]
            },
            fields=["name", "parent", "milestone_name", "due_date", "amount"]
        )
        
        for milestone in upcoming_milestones:
            # Get contract details
            contract = frappe.get_doc("Freelancer Contract", milestone.parent)
            
            # Send notification to freelancer
            if contract.freelancer:
                freelancer = frappe.get_doc("Freelancer", contract.freelancer)
                if freelancer.email:
                    frappe.sendmail(
                        recipients=[freelancer.email],
                        subject=_("Milestone Due Reminder: {0}").format(milestone.milestone_name),
                        message=_("""
                            <p>Dear {0},</p>
                            <p>This is a reminder that the milestone <strong>{1}</strong> is due on <strong>{2}</strong>.</p>
                            <p>Contract: {3}</p>
                            <p>Amount: {4}</p>
                            <p>Please ensure timely completion.</p>
                        """).format(
                            freelancer.first_name,
                            milestone.milestone_name,
                            milestone.due_date,
                            contract.name,
                            frappe.format_value(milestone.amount, {"fieldtype": "Currency"})
                        ),
                        now=True
                    )
                    
    except Exception as e:
        frappe.log_error(
            title="Milestone Reminder Failed",
            message=str(e)
        )


def check_contract_expirations():
    """Check for contracts expiring within 7 days and send notifications"""
    try:
        expiring_contracts = frappe.get_all(
            "Freelancer Contract",
            filters={
                "end_date": ["between", [nowdate(), add_days(nowdate(), 7)]],
                "status": "Active"
            },
            fields=["name", "freelancer", "company", "end_date", "contract_value"]
        )
        
        for contract in expiring_contracts:
            # Get company users to notify
            company_users = frappe.get_all(
                "User",
                filters={
                    "enabled": 1
                },
                fields=["name", "email"],
                limit=5  # Limit to avoid spamming
            )
            
            # Create a notification
            for user in company_users:
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": _("Contract Expiring: {0}").format(contract.name),
                    "for_user": user.name,
                    "type": "Alert",
                    "document_type": "Freelancer Contract",
                    "document_name": contract.name,
                    "email_content": _("Contract {0} expires on {1}").format(
                        contract.name, contract.end_date
                    )
                }).insert(ignore_permissions=True)
                
    except Exception as e:
        frappe.log_error(
            title="Contract Expiration Check Failed",
            message=str(e)
        )


def process_overdue_payments():
    """Flag payments that are overdue and send reminders"""
    try:
        overdue_payments = frappe.get_all(
            "Freelancer Payment",
            filters={
                "due_date": ["<", nowdate()],
                "status": ["in", ["Draft", "Pending Approval", "Approved"]],
                "docstatus": ["<", 2]
            },
            fields=["name", "freelancer", "net_amount", "currency", "due_date"]
        )
        
        for payment in overdue_payments:
            days_overdue = (getdate(nowdate()) - getdate(payment.due_date)).days
            
            # Add comment to payment
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Freelancer Payment",
                "reference_name": payment.name,
                "content": _("Payment is {0} days overdue").format(days_overdue)
            }).insert(ignore_permissions=True)
            
    except Exception as e:
        frappe.log_error(
            title="Overdue Payment Check Failed",
            message=str(e)
        )


def check_payment_due_dates():
    """Check and notify about upcoming payment due dates"""
    pass
