# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Quarterly scheduled tasks for HRMS Freelancer
"""

import frappe
from frappe import _
from frappe.utils import nowdate, add_months, getdate, get_first_day, get_last_day, flt


def generate_vat_summaries():
    """Generate quarterly VAT summaries for EU reporting"""
    try:
        # Calculate quarter dates
        today = getdate(nowdate())
        current_month = today.month
        current_quarter = (current_month - 1) // 3 + 1
        
        # Get previous quarter
        prev_quarter = current_quarter - 1 if current_quarter > 1 else 4
        year = today.year if current_quarter > 1 else today.year - 1
        
        # Quarter start and end dates
        quarter_start_month = (prev_quarter - 1) * 3 + 1
        quarter_start = getdate(f"{year}-{quarter_start_month:02d}-01")
        quarter_end = get_last_day(add_months(quarter_start, 2))
        
        quarter_label = f"Q{prev_quarter} {year}"
        
        # Get all submitted payments in the quarter
        payments = frappe.get_all(
            "Freelancer Payment",
            filters={
                "posting_date": ["between", [quarter_start, quarter_end]],
                "docstatus": 1
            },
            fields=[
                "name", "freelancer", "company", "gross_amount", "net_amount",
                "vat_amount", "vat_rate", "withholding_tax", "currency",
                "vat_treatment", "posting_date"
            ]
        )
        
        if not payments:
            frappe.log_error(
                title=f"VAT Summary {quarter_label}",
                message="No payments found for the quarter"
            )
            return
        
        # Group by VAT treatment
        vat_summary = {
            "standard": {"count": 0, "gross": 0, "vat": 0},
            "reverse_charge": {"count": 0, "gross": 0, "vat": 0},
            "exempt": {"count": 0, "gross": 0, "vat": 0},
            "export": {"count": 0, "gross": 0, "vat": 0}
        }
        
        # Group by country for EC Sales List
        ec_sales = {}
        
        for payment in payments:
            treatment = payment.vat_treatment or "standard"
            if treatment not in vat_summary:
                treatment = "standard"
            
            vat_summary[treatment]["count"] += 1
            vat_summary[treatment]["gross"] += flt(payment.gross_amount)
            vat_summary[treatment]["vat"] += flt(payment.vat_amount)
            
            # Get freelancer country for EC Sales
            if payment.freelancer:
                freelancer = frappe.get_value(
                    "Freelancer", 
                    payment.freelancer, 
                    ["country", "vat_number"],
                    as_dict=True
                )
                
                if freelancer and freelancer.country:
                    country = freelancer.country
                    if country not in ec_sales:
                        ec_sales[country] = {
                            "count": 0, 
                            "value": 0,
                            "vat_numbers": set()
                        }
                    ec_sales[country]["count"] += 1
                    ec_sales[country]["value"] += flt(payment.gross_amount)
                    if freelancer.vat_number:
                        ec_sales[country]["vat_numbers"].add(freelancer.vat_number)
        
        # Generate report
        report = f"""
        <h2>Quarterly VAT Summary - {quarter_label}</h2>
        <p>Period: {quarter_start} to {quarter_end}</p>
        <p>Total Payments: {len(payments)}</p>
        
        <h3>VAT Treatment Summary</h3>
        <table border="1" cellpadding="5">
            <tr>
                <th>Treatment</th>
                <th>Count</th>
                <th>Gross Amount</th>
                <th>VAT Amount</th>
            </tr>
        """
        
        for treatment, data in vat_summary.items():
            if data["count"] > 0:
                report += f"""
                <tr>
                    <td>{treatment.replace('_', ' ').title()}</td>
                    <td>{data['count']}</td>
                    <td>{data['gross']:,.2f}</td>
                    <td>{data['vat']:,.2f}</td>
                </tr>
                """
        
        report += "</table>"
        
        # EC Sales List section
        if ec_sales:
            report += """
            <h3>EC Sales List (Cross-Border B2B)</h3>
            <table border="1" cellpadding="5">
                <tr>
                    <th>Country</th>
                    <th>Transactions</th>
                    <th>Value</th>
                    <th>VAT Numbers</th>
                </tr>
            """
            
            for country, data in sorted(ec_sales.items()):
                vat_nums = ", ".join(list(data["vat_numbers"])[:5])
                if len(data["vat_numbers"]) > 5:
                    vat_nums += f" (+{len(data['vat_numbers']) - 5} more)"
                
                report += f"""
                <tr>
                    <td>{country}</td>
                    <td>{data['count']}</td>
                    <td>{data['value']:,.2f}</td>
                    <td>{vat_nums or 'N/A'}</td>
                </tr>
                """
            
            report += "</table>"
        
        # Save report
        frappe.log_error(
            title=f"Quarterly VAT Summary - {quarter_label}",
            message=report
        )
        
        # Create a note for record keeping
        try:
            frappe.get_doc({
                "doctype": "Note",
                "title": f"VAT Summary {quarter_label}",
                "public": 0,
                "content": report
            }).insert(ignore_permissions=True)
        except Exception:
            pass  # Note doctype might not exist
            
    except Exception as e:
        frappe.log_error(
            title="Quarterly VAT Summary Failed",
            message=str(e)
        )


def review_tax_treaty_effectiveness():
    """Review tax treaty usage and effectiveness"""
    try:
        today = getdate(nowdate())
        year_start = getdate(f"{today.year}-01-01")
        
        # Get payments with treaty benefits
        treaty_payments = frappe.get_all(
            "Freelancer Payment",
            filters={
                "posting_date": [">=", year_start],
                "docstatus": 1,
                "treaty_applied": 1  # Assuming this field exists
            },
            fields=["name", "freelancer", "withholding_tax", "gross_amount"]
        )
        
        # Get payments without treaty
        non_treaty_payments = frappe.get_all(
            "Freelancer Payment",
            filters={
                "posting_date": [">=", year_start],
                "docstatus": 1,
                "treaty_applied": 0
            },
            fields=["name", "freelancer", "withholding_tax", "gross_amount"]
        )
        
        treaty_savings = sum(flt(p.gross_amount) * 0.15 - flt(p.withholding_tax) 
                           for p in treaty_payments if flt(p.withholding_tax) < flt(p.gross_amount) * 0.15)
        
        report = f"""
        <h3>Tax Treaty Effectiveness Review - YTD {today.year}</h3>
        
        <p>Payments with Treaty Benefits: {len(treaty_payments)}</p>
        <p>Payments without Treaty: {len(non_treaty_payments)}</p>
        <p>Estimated Tax Savings from Treaties: {treaty_savings:,.2f}</p>
        """
        
        frappe.log_error(
            title=f"Treaty Effectiveness Review - {today.year}",
            message=report
        )
        
    except Exception as e:
        frappe.log_error(
            title="Treaty Review Failed",
            message=str(e)
        )


def gdpr_data_retention_cleanup():
    """Clean up data according to GDPR retention policies"""
    try:
        from hrms_freelancer.utils.constants import GDPR_DATA_RETENTION_PERIODS
        
        cleaned_records = {
            "communications": 0,
            "old_consents": 0
        }
        
        # Clean old communication records (beyond retention period)
        comm_retention_years = GDPR_DATA_RETENTION_PERIODS.get("communication", 2)
        comm_cutoff = add_months(nowdate(), -comm_retention_years * 12)
        
        old_communications = frappe.get_all(
            "Communication",
            filters={
                "reference_doctype": ["in", ["Freelancer", "Freelancer Payment", "Freelancer Contract"]],
                "creation": ["<", comm_cutoff]
            },
            pluck="name",
            limit=100
        )
        
        for comm in old_communications:
            try:
                frappe.delete_doc("Communication", comm, ignore_permissions=True)
                cleaned_records["communications"] += 1
            except Exception:
                pass
        
        # Log cleanup results
        if any(cleaned_records.values()):
            frappe.db.commit()
            frappe.log_error(
                title="GDPR Data Retention Cleanup",
                message=f"Cleaned: {cleaned_records}"
            )
            
    except Exception as e:
        frappe.log_error(
            title="GDPR Cleanup Failed",
            message=str(e)
        )
