# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Jinja template methods for HRMS Freelancer
"""

import frappe
from frappe.utils import fmt_money


def format_currency_with_symbol(amount, currency="EUR"):
    """Format amount with currency symbol"""
    return fmt_money(amount, currency=currency)


def get_vat_display_text(vat_rate, reverse_charge=False):
    """Get VAT display text for invoices"""
    if reverse_charge:
        return "VAT Reverse Charge - Customer to account for VAT"
    elif vat_rate == 0:
        return "VAT Exempt (0%)"
    else:
        return f"VAT {vat_rate}%"


def format_tax_treaty_info(treaty_name, reduced_rate):
    """Format tax treaty information for display"""
    if treaty_name:
        return f"Tax Treaty Applied: {treaty_name} (Rate: {reduced_rate}%)"
    return ""
