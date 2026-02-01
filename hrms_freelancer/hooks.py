"""
Frappe Hooks Configuration
Defines app behavior, doctypes, fixtures, and integrations
"""

app_name = "hrms_freelancer"
app_title = "HRMS Freelancer Extension"
app_publisher = "HR Platform Team"
app_description = "Freelancer and Contractor Management Extension for Frappe HRMS"
app_email = "support@hrplatform.example.com"
app_license = "MIT"
app_version = "1.0.0"

# Required Apps
# Note: hrms is optional - works with just frappe and erpnext for basic functionality
required_apps = ["frappe", "erpnext"]

# Includes in <head>
# ------------------

app_include_css = [
    "/assets/hrms_freelancer/css/hrms_freelancer.css"
]

app_include_js = [
    "/assets/hrms_freelancer/js/hrms_freelancer.js"
]

# Include js in doctype views
doctype_js = {
    "Employee": "public/js/employee_extension.js",
    "Salary Slip": "public/js/salary_slip_extension.js"
}

# Include js in page
# page_js = {
#     "page_name": "public/js/file.js"
# }

# Include js in portal pages
# portal_js = {
#     "portal_page": "public/js/file.js"
# }

# Website routes
website_route_rules = [
    {"from_route": "/freelancer-portal", "to_route": "Freelancer Portal"},
    {"from_route": "/freelancer-portal/<path:app_path>", "to_route": "Freelancer Portal"},
]

# DocTypes to be created
# ----------------------

# Home Pages
# ----------
role_home_page = {
    "Freelancer": "freelancer-portal",
    "Contractor Manager": "freelancer-management"
}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------
# add methods and filters to jinja environment
jinja = {
    "methods": [
        "hrms_freelancer.utils.jinja_methods.format_currency_with_symbol",
        "hrms_freelancer.utils.jinja_methods.get_vat_display_text",
        "hrms_freelancer.utils.jinja_methods.format_tax_treaty_info"
    ],
    "filters": [
        "hrms_freelancer.utils.jinja_filters.currency_filter",
        "hrms_freelancer.utils.jinja_filters.date_locale_filter"
    ]
}

# Installation
# ------------

before_install = "hrms_freelancer.setup.install.before_install"
after_install = "hrms_freelancer.setup.install.after_install"

# Uninstallation
# ------------

before_uninstall = "hrms_freelancer.setup.uninstall.before_uninstall"
after_uninstall = "hrms_freelancer.setup.uninstall.after_uninstall"

# Fixtures
# --------

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "HRMS Freelancer"]
        ]
    },
    {
        "dt": "Property Setter",
        "filters": [
            ["module", "=", "HRMS Freelancer"]
        ]
    },
    {
        "dt": "Role",
        "filters": [
            ["name", "in", [
                "Freelancer",
                "Contractor Manager",
                "Freelancer Accountant",
                "Compliance Officer"
            ]]
        ]
    },
    {
        "dt": "Workflow",
        "filters": [
            ["name", "in", [
                "Freelancer Payment Approval",
                "Contract Approval",
                "Freelancer Onboarding"
            ]]
        ]
    },
    "Tax Treaty",
    "VAT Rate",
    "Compliance Requirement"
]

# Document Events
# ---------------

doc_events = {
    "Employee": {
        "validate": "hrms_freelancer.overrides.employee.validate_worker_type",
        "on_update": "hrms_freelancer.overrides.employee.on_update_worker_type",
        "after_insert": "hrms_freelancer.overrides.employee.after_insert_freelancer_check"
    },
    "Salary Slip": {
        "validate": "hrms_freelancer.overrides.salary_slip.validate_freelancer_payment",
        "before_submit": "hrms_freelancer.overrides.salary_slip.before_submit_freelancer"
    },
    "Sales Invoice": {
        "on_submit": "hrms_freelancer.integrations.erpnext.on_freelancer_invoice_submit",
        "on_cancel": "hrms_freelancer.integrations.erpnext.on_freelancer_invoice_cancel"
    },
    "Freelancer": {
        "validate": "hrms_freelancer.freelancer.doctype.freelancer.freelancer.validate_freelancer",
        "on_update": "hrms_freelancer.freelancer.doctype.freelancer.freelancer.on_update",
        "after_insert": "hrms_freelancer.freelancer.doctype.freelancer.freelancer.after_insert"
    },
    "Freelancer Contract": {
        "validate": "hrms_freelancer.freelancer.doctype.freelancer_contract.freelancer_contract.validate_contract",
        "on_submit": "hrms_freelancer.freelancer.doctype.freelancer_contract.freelancer_contract.on_submit",
        "before_cancel": "hrms_freelancer.freelancer.doctype.freelancer_contract.freelancer_contract.before_cancel"
    },
    "Freelancer Payment": {
        "validate": "hrms_freelancer.freelancer.doctype.freelancer_payment.freelancer_payment.validate_payment",
        "on_submit": "hrms_freelancer.freelancer.doctype.freelancer_payment.freelancer_payment.on_submit",
        "on_cancel": "hrms_freelancer.freelancer.doctype.freelancer_payment.freelancer_payment.on_cancel"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        # Update exchange rates daily at 6 AM
        "0 6 * * *": [
            "hrms_freelancer.tasks.daily.update_exchange_rates"
        ],
        # Check contract expiry weekly on Monday at 9 AM
        "0 9 * * 1": [
            "hrms_freelancer.tasks.weekly.check_contract_expiry_notifications"
        ],
        # Monthly compliance check on 1st at 8 AM
        "0 8 1 * *": [
            "hrms_freelancer.tasks.monthly.run_compliance_checks"
        ],
        # Quarterly VAT summary generation
        "0 10 1 1,4,7,10 *": [
            "hrms_freelancer.tasks.quarterly.generate_vat_summaries"
        ]
    },
    "daily": [
        "hrms_freelancer.tasks.daily.process_pending_milestone_reminders",
        "hrms_freelancer.tasks.daily.check_payment_due_dates"
    ],
    "weekly": [
        "hrms_freelancer.tasks.weekly.generate_compliance_reports",
        "hrms_freelancer.tasks.weekly.sync_tax_treaty_updates"
    ],
    "monthly": [
        "hrms_freelancer.tasks.monthly.archive_completed_contracts",
        "hrms_freelancer.tasks.monthly.send_tax_summary_reports"
    ]
}

# Testing
# -------

before_tests = "hrms_freelancer.setup.install.before_tests"

# Overriding Methods
# ------------------

override_whitelisted_methods = {
    # Override HRMS employee methods for freelancer support
    "hrms.hr.doctype.employee.employee.get_timeline_data": 
        "hrms_freelancer.overrides.employee.get_timeline_data_with_freelancer"
}

override_doctype_dashboards = {
    "Employee": "hrms_freelancer.overrides.employee_dashboard.get_dashboard_data"
}

# Permission Query Conditions
# ---------------------------

permission_query_conditions = {
    "Freelancer": "hrms_freelancer.permissions.freelancer_permission_query",
    "Freelancer Contract": "hrms_freelancer.permissions.contract_permission_query",
    "Freelancer Payment": "hrms_freelancer.permissions.payment_permission_query"
}

has_permission = {
    "Freelancer": "hrms_freelancer.permissions.has_freelancer_permission",
    "Freelancer Contract": "hrms_freelancer.permissions.has_contract_permission",
    "Freelancer Payment": "hrms_freelancer.permissions.has_payment_permission"
}

# DocType Class Overrides
# -----------------------

# override_doctype_class = {
#     "Employee": "hrms_freelancer.overrides.custom_employee.CustomEmployee"
# }

# Document Links
# --------------

# Additional document links for doctypes

# Bootinfo
# --------

boot_session = "hrms_freelancer.boot.boot_session"

# User Data Protection
# --------------------

user_data_fields = [
    {
        "doctype": "Freelancer",
        "filter_by": "user_id",
        "redact_fields": ["bank_account", "tax_id", "social_security_number"],
        "partial": 1,
    },
    {
        "doctype": "Freelancer Contract",
        "filter_by": "freelancer",
        "redact_fields": ["rate", "total_value"],
        "partial": 1,
    },
    {
        "doctype": "Freelancer Payment",
        "filter_by": "freelancer",
        "redact_fields": ["gross_amount", "net_amount", "bank_details"],
        "partial": 1,
    },
    {
        "doctype": "GDPR Consent Log",
        "filter_by": "user",
        "strict": True,
    }
]

# Authentication and Authorization
# --------------------------------

# auth_hooks = [
#     "hrms_freelancer.auth.validate_freelancer_session"
# ]

# Automatically update python controller files 
# with type hints based on DocType json files

# export_python_type_annotations = True

# Translation
# -----------

# Make link fields searchable based on their dependencies
# These will be translated for searching

translated_search_doctypes = [
    {
        "doctype": "Freelancer",
        "search_fields": ["full_name", "contractor_name"]
    }
]

# Desk Pages
# ----------

# desk_pages = [
#     {
#         "name": "Freelancer Management",
#         "label": "Freelancer Management",
#         "icon": "octicon octicon-briefcase",
#         "module": "HRMS Freelancer"
#     }
# ]

# Workspaces
# ----------

# workspace_icons = {
#     "Freelancer Management": "briefcase"
# }

# Regional Overrides
# ------------------

regional_overrides = {
    "Netherlands": {
        "hrms_freelancer.regional.netherlands.validate_bsn": "",
        "hrms_freelancer.regional.netherlands.calculate_btw": ""
    },
    "Germany": {
        "hrms_freelancer.regional.germany.validate_steuernummer": "",
        "hrms_freelancer.regional.germany.calculate_ust": ""
    },
    "France": {
        "hrms_freelancer.regional.france.validate_siret": "",
        "hrms_freelancer.regional.france.calculate_tva": ""
    },
    "United States": {
        "hrms_freelancer.regional.usa.validate_ein_ssn": "",
        "hrms_freelancer.regional.usa.generate_1099": ""
    }
}

# Global Search
# -------------

global_search_doctypes = {
    "Default": [
        {"doctype": "Freelancer", "index": 10},
        {"doctype": "Freelancer Contract", "index": 8},
        {"doctype": "Freelancer Payment", "index": 6}
    ]
}

# Website Configuration
# ---------------------

website_context = {
    "favicon": "/assets/hrms_freelancer/images/favicon.ico",
    "splash_image": "/assets/hrms_freelancer/images/splash.svg"
}

# Notification Configuration
# --------------------------

notification_config = "hrms_freelancer.notifications.get_notification_config"

# Email Brand Styling
# -------------------

email_brand_image = "/assets/hrms_freelancer/images/email-header.png"

# Default Print Formats
# ---------------------

default_print_format = "Freelancer Payment Print"

# PDF Generation
# --------------

pdf_header_html = "hrms_freelancer/templates/pdf/header.html"
pdf_body_html = "hrms_freelancer/templates/pdf/body.html"
pdf_footer_html = "hrms_freelancer/templates/pdf/footer.html"

# Currency
# --------

default_currency = "EUR"

# Accounting
# ----------

accounting_dimension_doctypes = [
    "Freelancer Payment",
    "Freelancer Expense"
]
