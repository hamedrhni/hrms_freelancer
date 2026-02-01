# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Jinja template filters for HRMS Freelancer
"""

import frappe
from frappe.utils import fmt_money, format_date


def currency_filter(amount, currency="EUR"):
    """Currency formatting filter"""
    return fmt_money(amount, currency=currency)


def date_locale_filter(date_str, format_type="medium"):
    """Date formatting with locale support"""
    return format_date(date_str)
