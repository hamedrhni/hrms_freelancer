# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Monthly scheduled tasks for HRMS Freelancer
"""

import frappe
from frappe import _
from frappe.utils import nowdate, add_months, getdate, get_first_day, get_last_day, flt


def run_compliance_checks():
    """Run monthly compliance checks for all active freelancers"""
    try:
        active_freelancers = frappe.get_all(
            "Freelancer",
            filters={"status": "Active"},
            fields=["name", "first_name", "last_name", "email", "country", 
                   "tax_id", "vat_number", "worker_type"]
        )
        
        compliance_issues = []
        
        for freelancer in active_freelancers:
            issues = []
            
            # Check required fields based on country
            from hrms_freelancer.utils.constants import is_eu_country
            
            freelancer_country_code = get_country_code(freelancer.country)
            
            if freelancer_country_code and is_eu_country(freelancer_country_code):
                # EU freelancers need VAT number for B2B
                if not freelancer.vat_number:
                    issues.append("Missing VAT number (required for EU B2B)")
            
            if not freelancer.tax_id:
                issues.append("Missing Tax ID")
            
            # Check for expired documents
            expired_docs = frappe.get_all(
                "Freelancer Document",
                filters={
                    "parent": freelancer.name,
                    "expiry_date": ["<", nowdate()]
                },
                fields=["document_type", "expiry_date"]
            )
            
            for doc in expired_docs:
                issues.append(f"Expired document: {doc.document_type} (expired {doc.expiry_date})")
            
            # Check GDPR consent status
            gdpr_consent = frappe.get_all(
                "GDPR Consent Log",
                filters={
                    "freelancer": freelancer.name,
                    "consent_given": 1
                },
                limit=1
            )
            
            if not gdpr_consent:
                issues.append("No active GDPR consent on record")
            
            if issues:
                compliance_issues.append({
                    "freelancer": freelancer.name,
                    "name": f"{freelancer.first_name} {freelancer.last_name}",
                    "issues": issues
                })
        
        # Generate compliance report
        if compliance_issues:
            report_content = "<h3>Monthly Compliance Report</h3>"
            report_content += f"<p>Date: {nowdate()}</p>"
            report_content += f"<p>Total issues found: {len(compliance_issues)} freelancers with issues</p>"
            report_content += "<hr>"
            
            for item in compliance_issues:
                report_content += f"<h4>{item['name']} ({item['freelancer']})</h4>"
                report_content += "<ul>"
                for issue in item['issues']:
                    report_content += f"<li>{issue}</li>"
                report_content += "</ul>"
            
            # Send to compliance officers
            frappe.log_error(
                title="Monthly Compliance Report",
                message=report_content
            )
            
    except Exception as e:
        frappe.log_error(
            title="Monthly Compliance Check Failed",
            message=str(e)
        )


def archive_completed_contracts():
    """Archive contracts that have been completed for more than 90 days"""
    try:
        cutoff_date = add_months(nowdate(), -3)
        
        completed_contracts = frappe.get_all(
            "Freelancer Contract",
            filters={
                "status": "Completed",
                "end_date": ["<", cutoff_date],
                "archived": 0  # Custom field to track archived status
            },
            fields=["name", "freelancer", "end_date"]
        )
        
        archived_count = 0
        for contract in completed_contracts:
            try:
                # Add archived flag
                frappe.db.set_value(
                    "Freelancer Contract",
                    contract.name,
                    "archived",
                    1
                )
                archived_count += 1
            except Exception as e:
                frappe.log_error(
                    title=f"Failed to archive contract {contract.name}",
                    message=str(e)
                )
        
        if archived_count > 0:
            frappe.db.commit()
            frappe.log_error(
                title="Contracts Archived",
                message=f"Archived {archived_count} completed contracts"
            )
            
    except Exception as e:
        frappe.log_error(
            title="Contract Archival Failed",
            message=str(e)
        )


def send_tax_summary_reports():
    """Send monthly tax summary reports to finance team"""
    try:
        # Get last month's date range
        today = getdate(nowdate())
        first_day_last_month = get_first_day(add_months(today, -1))
        last_day_last_month = get_last_day(add_months(today, -1))
        
        # Get all payments from last month
        payments = frappe.get_all(
            "Freelancer Payment",
            filters={
                "posting_date": ["between", [first_day_last_month, last_day_last_month]],
                "docstatus": 1
            },
            fields=["name", "freelancer", "gross_amount", "net_amount", 
                   "withholding_tax", "vat_amount", "currency"]
        )
        
        if not payments:
            return
        
        # Calculate totals
        totals = {
            "count": len(payments),
            "gross": sum(flt(p.gross_amount) for p in payments),
            "net": sum(flt(p.net_amount) for p in payments),
            "withholding": sum(flt(p.withholding_tax) for p in payments),
            "vat": sum(flt(p.vat_amount) for p in payments)
        }
        
        # Group by currency
        by_currency = {}
        for payment in payments:
            currency = payment.currency or "EUR"
            if currency not in by_currency:
                by_currency[currency] = {
                    "count": 0, "gross": 0, "net": 0, "withholding": 0, "vat": 0
                }
            by_currency[currency]["count"] += 1
            by_currency[currency]["gross"] += flt(payment.gross_amount)
            by_currency[currency]["net"] += flt(payment.net_amount)
            by_currency[currency]["withholding"] += flt(payment.withholding_tax)
            by_currency[currency]["vat"] += flt(payment.vat_amount)
        
        # Generate report
        report = f"""
        <h3>Monthly Tax Summary Report</h3>
        <p>Period: {first_day_last_month} to {last_day_last_month}</p>
        
        <h4>Overall Summary</h4>
        <table border="1" cellpadding="5">
            <tr><td>Total Payments</td><td>{totals['count']}</td></tr>
            <tr><td>Gross Amount</td><td>{totals['gross']:,.2f}</td></tr>
            <tr><td>Net Amount</td><td>{totals['net']:,.2f}</td></tr>
            <tr><td>Withholding Tax</td><td>{totals['withholding']:,.2f}</td></tr>
            <tr><td>VAT</td><td>{totals['vat']:,.2f}</td></tr>
        </table>
        
        <h4>By Currency</h4>
        """
        
        for currency, data in by_currency.items():
            report += f"""
            <h5>{currency}</h5>
            <table border="1" cellpadding="5">
                <tr><td>Payments</td><td>{data['count']}</td></tr>
                <tr><td>Gross</td><td>{currency} {data['gross']:,.2f}</td></tr>
                <tr><td>Net</td><td>{currency} {data['net']:,.2f}</td></tr>
                <tr><td>Withholding</td><td>{currency} {data['withholding']:,.2f}</td></tr>
                <tr><td>VAT</td><td>{currency} {data['vat']:,.2f}</td></tr>
            </table>
            """
        
        frappe.log_error(
            title=f"Tax Summary Report - {first_day_last_month.strftime('%B %Y')}",
            message=report
        )
        
    except Exception as e:
        frappe.log_error(
            title="Tax Summary Report Failed",
            message=str(e)
        )


def get_country_code(country_name):
    """Get country code from country name"""
    if not country_name:
        return None
    
    from hrms_freelancer.utils.constants import EU_COUNTRIES
    
    for code, info in EU_COUNTRIES.items():
        if info['name'].lower() == country_name.lower():
            return code
    
    return None
