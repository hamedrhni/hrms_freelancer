# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Setup script for HRMS Freelancer module
Run after installation to set up default data and configurations
"""

import frappe
from frappe import _


def before_install():
    """Run before the app is installed"""
    pass


def before_tests():
    """Run before tests"""
    pass


def after_install():
    """Run after the app is installed"""
    print("Setting up HRMS Freelancer module...")
    
    create_custom_roles()
    create_default_vat_configurations()
    create_default_tax_treaties()
    # Workflow setup disabled - requires manual configuration
    # setup_workflow()
    
    print("HRMS Freelancer setup complete!")


def create_custom_roles():
    """Create custom roles for freelancer management"""
    roles = [
        {
            "role_name": "Freelancer Manager",
            "desk_access": 1,
            "description": "Can manage freelancers, contracts, and payments"
        },
        {
            "role_name": "Freelancer Approver",
            "desk_access": 1,
            "description": "Can approve freelancer payments and contracts"
        },
        {
            "role_name": "Freelancer",
            "desk_access": 1,
            "description": "Self-service portal access for freelancers"
        }
    ]
    
    for role in roles:
        if not frappe.db.exists("Role", role["role_name"]):
            doc = frappe.get_doc({
                "doctype": "Role",
                "role_name": role["role_name"],
                "desk_access": role["desk_access"]
            })
            doc.insert(ignore_permissions=True)
            print(f"Created role: {role['role_name']}")


def create_default_vat_configurations():
    """Create default VAT configurations for EU countries"""
    vat_configs = [
        {"name": "Netherlands", "country": "Netherlands", "standard_rate": 21.0, "reduced_rate": 9.0},
        {"name": "Germany", "country": "Germany", "standard_rate": 19.0, "reduced_rate": 7.0},
        {"name": "France", "country": "France", "standard_rate": 20.0, "reduced_rate": 5.5},
        {"name": "Belgium", "country": "Belgium", "standard_rate": 21.0, "reduced_rate": 6.0},
        {"name": "Spain", "country": "Spain", "standard_rate": 21.0, "reduced_rate": 10.0},
        {"name": "Italy", "country": "Italy", "standard_rate": 22.0, "reduced_rate": 10.0},
        {"name": "Austria", "country": "Austria", "standard_rate": 20.0, "reduced_rate": 10.0},
        {"name": "Poland", "country": "Poland", "standard_rate": 23.0, "reduced_rate": 8.0},
        {"name": "Ireland", "country": "Ireland", "standard_rate": 23.0, "reduced_rate": 13.5},
        {"name": "Portugal", "country": "Portugal", "standard_rate": 23.0, "reduced_rate": 13.0},
        {"name": "Sweden", "country": "Sweden", "standard_rate": 25.0, "reduced_rate": 12.0},
        {"name": "Denmark", "country": "Denmark", "standard_rate": 25.0, "reduced_rate": 0.0},
        {"name": "Finland", "country": "Finland", "standard_rate": 25.5, "reduced_rate": 14.0},
        {"name": "Greece", "country": "Greece", "standard_rate": 24.0, "reduced_rate": 13.0},
        {"name": "Czech Republic", "country": "Czech Republic", "standard_rate": 21.0, "reduced_rate": 12.0},
        {"name": "Hungary", "country": "Hungary", "standard_rate": 27.0, "reduced_rate": 18.0},
        {"name": "Romania", "country": "Romania", "standard_rate": 19.0, "reduced_rate": 9.0},
        {"name": "Luxembourg", "country": "Luxembourg", "standard_rate": 17.0, "reduced_rate": 8.0},
        {"name": "United Kingdom", "country": "United Kingdom", "standard_rate": 20.0, "reduced_rate": 5.0},
        {"name": "Switzerland", "country": "Switzerland", "standard_rate": 8.1, "reduced_rate": 2.6},
    ]
    
    for config in vat_configs:
        if not frappe.db.exists("VAT Configuration", config["name"]):
            doc = frappe.get_doc({
                "doctype": "VAT Configuration",
                "name": config["name"],
                "country": config["country"],
                "standard_rate": config["standard_rate"],
                "reduced_rate": config["reduced_rate"],
                "zero_rate": 0.0,
                "reverse_charge_applicable": 1 if config["country"] not in ["United Kingdom", "Switzerland"] else 0
            })
            doc.insert(ignore_permissions=True)
            print(f"Created VAT configuration: {config['name']}")


def create_default_tax_treaties():
    """Create default tax treaty configurations"""
    treaties = [
        {
            "treaty_code": "NL-US",
            "treaty_name": "Netherlands-United States Tax Treaty",
            "country_1": "Netherlands",
            "country_2": "United States",
            "services_withholding_rate": 0.0,
            "reduced_rate": 0.0,
            "certificate_required": 1
        },
        {
            "treaty_code": "NL-UK",
            "treaty_name": "Netherlands-United Kingdom Tax Treaty",
            "country_1": "Netherlands",
            "country_2": "United Kingdom",
            "services_withholding_rate": 0.0,
            "reduced_rate": 0.0,
            "certificate_required": 1
        },
        {
            "treaty_code": "DE-US",
            "treaty_name": "Germany-United States Tax Treaty",
            "country_1": "Germany",
            "country_2": "United States",
            "services_withholding_rate": 0.0,
            "reduced_rate": 0.0,
            "certificate_required": 1
        },
        {
            "treaty_code": "NL-IN",
            "treaty_name": "Netherlands-India Tax Treaty",
            "country_1": "Netherlands",
            "country_2": "India",
            "services_withholding_rate": 10.0,
            "reduced_rate": 10.0,
            "certificate_required": 1
        },
    ]
    
    for treaty in treaties:
        if not frappe.db.exists("Tax Treaty", treaty["treaty_code"]):
            doc = frappe.get_doc({
                "doctype": "Tax Treaty",
                **treaty
            })
            doc.insert(ignore_permissions=True)
            print(f"Created tax treaty: {treaty['treaty_code']}")


def setup_workflow():
    """Setup workflow for Freelancer Payment approval"""
    workflow_name = "Freelancer Payment Approval"
    
    if frappe.db.exists("Workflow", workflow_name):
        print(f"Workflow '{workflow_name}' already exists")
        return
    
    workflow = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": "Freelancer Payment",
        "is_active": 1,
        "send_email_alert": 1,
        "states": [
            {
                "state": "Draft",
                "doc_status": "0",
                "allow_edit": "Freelancer Manager"
            },
            {
                "state": "Pending Approval",
                "doc_status": "0",
                "allow_edit": "Freelancer Approver"
            },
            {
                "state": "Approved",
                "doc_status": "1",
                "allow_edit": "Accounts Manager"
            },
            {
                "state": "Rejected",
                "doc_status": "0",
                "allow_edit": "Freelancer Manager"
            },
            {
                "state": "Paid",
                "doc_status": "1",
                "allow_edit": "Accounts Manager"
            }
        ],
        "transitions": [
            {
                "state": "Draft",
                "action": "Submit for Approval",
                "next_state": "Pending Approval",
                "allowed": "Freelancer Manager"
            },
            {
                "state": "Pending Approval",
                "action": "Approve",
                "next_state": "Approved",
                "allowed": "Freelancer Approver"
            },
            {
                "state": "Pending Approval",
                "action": "Reject",
                "next_state": "Rejected",
                "allowed": "Freelancer Approver"
            },
            {
                "state": "Rejected",
                "action": "Revise",
                "next_state": "Draft",
                "allowed": "Freelancer Manager"
            },
            {
                "state": "Approved",
                "action": "Mark Paid",
                "next_state": "Paid",
                "allowed": "Accounts Manager"
            }
        ]
    })
    
    workflow.insert(ignore_permissions=True)
    print(f"Created workflow: {workflow_name}")


def before_uninstall():
    """Run before the app is uninstalled"""
    print("Cleaning up HRMS Freelancer module...")
    
    # Optionally clean up custom data
    # Be careful with this in production!
    
    print("HRMS Freelancer cleanup complete!")
