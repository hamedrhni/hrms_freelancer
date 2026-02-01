# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class FreelancerPaymentItem(Document):
    """Child table for payment line items"""
    
    def before_save(self):
        """Calculate amount from quantity and rate"""
        self.amount = flt(self.quantity) * flt(self.rate)
