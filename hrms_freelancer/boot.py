# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Boot session configuration for HRMS Freelancer
"""

import frappe
from frappe import _


def boot_session(bootinfo):
    """Add data to the boot session"""
    if frappe.session.user != "Guest":
        bootinfo.hrms_freelancer = {
            "version": "1.0.0",
            "features": {
                "vat_management": True,
                "tax_treaties": True,
                "multi_currency": True,
                "gdpr_compliance": True
            }
        }
