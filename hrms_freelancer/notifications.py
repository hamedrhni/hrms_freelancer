# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Notification configuration for HRMS Freelancer
"""

import frappe
from frappe import _


def get_notification_config():
    """Returns notification config for HRMS Freelancer doctypes"""
    return {
        "for_doctype": {
            "Freelancer": {"status": "Active"},
            "Freelancer Contract": {"status": ("in", ("Draft", "Pending Approval"))},
            "Freelancer Payment": {"docstatus": 0},
        },
        "for_module_doctypes": {
            "HRMS Freelancer": ["Freelancer", "Freelancer Contract", "Freelancer Payment"]
        }
    }
