# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Weekly scheduled tasks for HRMS Freelancer
"""

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, add_months, getdate


def check_contract_expiry_notifications():
    """Check for contracts expiring within 30 days and send summary"""
    try:
        expiring_contracts = frappe.get_all(
            "Freelancer Contract",
            filters={
                "end_date": ["between", [nowdate(), add_days(nowdate(), 30)]],
                "status": "Active"
            },
            fields=["name", "freelancer", "company", "end_date", "contract_value"],
            order_by="end_date asc"
        )
        
        if not expiring_contracts:
            return
        
        # Group by company
        contracts_by_company = {}
        for contract in expiring_contracts:
            company = contract.company or "No Company"
            if company not in contracts_by_company:
                contracts_by_company[company] = []
            contracts_by_company[company].append(contract)
        
        # Send summary email to HR managers
        hr_managers = frappe.get_all(
            "Has Role",
            filters={"role": "Freelancer Manager"},
            fields=["parent"],
            distinct=True
        )
        
        if hr_managers:
            message = "<h3>Contracts Expiring in Next 30 Days</h3>"
            for company, contracts in contracts_by_company.items():
                message += f"<h4>{company}</h4><ul>"
                for c in contracts:
                    freelancer_name = frappe.get_value("Freelancer", c.freelancer, "full_name") or c.freelancer
                    message += f"<li>{c.name} - {freelancer_name} - Expires: {c.end_date}</li>"
                message += "</ul>"
            
            recipients = [frappe.get_value("User", h.parent, "email") for h in hr_managers]
            recipients = [r for r in recipients if r]
            
            if recipients:
                frappe.sendmail(
                    recipients=recipients,
                    subject=_("Weekly Contract Expiry Report - {0} Contracts Expiring").format(len(expiring_contracts)),
                    message=message,
                    now=True
                )
                
    except Exception as e:
        frappe.log_error(
            title="Contract Expiry Notification Failed",
            message=str(e)
        )


def generate_compliance_reports():
    """Generate weekly compliance summary reports"""
    try:
        # Count freelancers by compliance status
        compliance_stats = {
            "total_active": frappe.db.count("Freelancer", {"status": "Active"}),
            "missing_tax_id": frappe.db.count("Freelancer", {"status": "Active", "tax_id": ["is", "not set"]}),
            "missing_vat_id": frappe.db.count("Freelancer", {"status": "Active", "vat_number": ["is", "not set"]}),
            "expiring_documents": 0
        }
        
        # Count documents expiring within 30 days
        expiring_docs = frappe.get_all(
            "Freelancer Document",
            filters={
                "expiry_date": ["between", [nowdate(), add_days(nowdate(), 30)]]
            }
        )
        compliance_stats["expiring_documents"] = len(expiring_docs)
        
        # Count GDPR consents expiring
        gdpr_stats = {
            "total_consents": frappe.db.count("GDPR Consent Log"),
            "active_consents": frappe.db.count("GDPR Consent Log", {"consent_given": 1}),
        }
        
        # Log compliance report
        report_content = f"""
        Weekly Compliance Report - {nowdate()}
        
        Freelancer Statistics:
        - Total Active Freelancers: {compliance_stats['total_active']}
        - Missing Tax ID: {compliance_stats['missing_tax_id']}
        - Missing VAT Number: {compliance_stats['missing_vat_id']}
        - Documents Expiring Soon: {compliance_stats['expiring_documents']}
        
        GDPR Statistics:
        - Total Consent Records: {gdpr_stats['total_consents']}
        - Active Consents: {gdpr_stats['active_consents']}
        """
        
        frappe.log_error(
            title="Weekly Compliance Report",
            message=report_content
        )
        
    except Exception as e:
        frappe.log_error(
            title="Compliance Report Generation Failed",
            message=str(e)
        )


def sync_tax_treaty_updates():
    """Check for and sync any tax treaty configuration updates"""
    try:
        # Get all active tax treaties
        treaties = frappe.get_all(
            "Tax Treaty",
            filters={"enabled": 1},
            fields=["name", "country_code", "withholding_rate", "reduced_rate"]
        )
        
        # Validate treaty configurations
        issues = []
        for treaty in treaties:
            # Check for missing rates
            if treaty.withholding_rate is None:
                issues.append(f"{treaty.name}: Missing withholding rate")
            
            # Check for invalid reduced rates
            if treaty.reduced_rate and treaty.reduced_rate > treaty.withholding_rate:
                issues.append(f"{treaty.name}: Reduced rate higher than standard rate")
        
        if issues:
            frappe.log_error(
                title="Tax Treaty Configuration Issues",
                message="\n".join(issues)
            )
            
    except Exception as e:
        frappe.log_error(
            title="Tax Treaty Sync Failed",
            message=str(e)
        )


def cleanup_old_notifications():
    """Clean up notification logs older than 30 days"""
    try:
        cutoff_date = add_days(nowdate(), -30)
        
        old_notifications = frappe.get_all(
            "Notification Log",
            filters={
                "creation": ["<", cutoff_date],
                "read": 1
            },
            pluck="name"
        )
        
        for notif in old_notifications[:100]:  # Process in batches
            frappe.delete_doc("Notification Log", notif, ignore_permissions=True)
        
        if old_notifications:
            frappe.db.commit()
            
    except Exception as e:
        frappe.log_error(
            title="Notification Cleanup Failed",
            message=str(e)
        )
