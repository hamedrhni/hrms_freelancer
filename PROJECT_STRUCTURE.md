# HRMS Freelancer - Project Structure

## Overview
This is a complete Frappe HRMS extension for managing freelancers and contractors with EU and international compliance.

## Directory Structure

```
hrms_freelancer/
├── setup.py                    # Python package configuration
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
└── hrms_freelancer/
    ├── __init__.py
    ├── hooks.py               # Frappe hooks configuration
    ├── hrms_freelancer.json   # App configuration
    ├── modules.txt            # Module definitions
    │
    ├── freelancer/            # Main freelancer module
    │   ├── doctype/
    │   │   ├── freelancer/                      # Core freelancer record
    │   │   │   ├── freelancer.json
    │   │   │   ├── freelancer.py
    │   │   │   └── freelancer.js
    │   │   │
    │   │   ├── freelancer_contract/             # Contract management
    │   │   │   ├── freelancer_contract.json
    │   │   │   ├── freelancer_contract.py
    │   │   │   └── freelancer_contract.js
    │   │   │
    │   │   ├── freelancer_payment/              # Invoice-based payments
    │   │   │   ├── freelancer_payment.json
    │   │   │   ├── freelancer_payment.py
    │   │   │   └── freelancer_payment.js
    │   │   │
    │   │   ├── freelancer_skill/                # Skills child table
    │   │   │   ├── freelancer_skill.json
    │   │   │   └── freelancer_skill.py
    │   │   │
    │   │   ├── freelancer_contract_milestone/   # Milestones child table
    │   │   │   ├── freelancer_contract_milestone.json
    │   │   │   └── freelancer_contract_milestone.py
    │   │   │
    │   │   ├── freelancer_payment_item/         # Line items child table
    │   │   │   ├── freelancer_payment_item.json
    │   │   │   └── freelancer_payment_item.py
    │   │   │
    │   │   ├── freelancer_payment_expense/      # Expenses child table
    │   │   │   ├── freelancer_payment_expense.json
    │   │   │   └── freelancer_payment_expense.py
    │   │   │
    │   │   └── freelancer_document/             # Documents child table
    │   │       ├── freelancer_document.json
    │   │       └── freelancer_document.py
    │   │
    │   └── print_format/
    │       └── freelancer_payment_invoice/      # Invoice print format
    │           ├── freelancer_payment_invoice.html
    │           └── freelancer_payment_invoice.json
    │
    ├── compliance/            # Compliance module
    │   └── doctype/
    │       ├── tax_treaty/                # International tax treaties
    │       │   ├── tax_treaty.json
    │       │   └── tax_treaty.py
    │       │
    │       ├── gdpr_consent_log/          # GDPR audit log
    │       │   ├── gdpr_consent_log.json
    │       │   └── gdpr_consent_log.py
    │       │
    │       └── vat_configuration/         # VAT rates by country
    │           ├── vat_configuration.json
    │           └── vat_configuration.py
    │
    ├── utils/                 # Utility modules
    │   ├── __init__.py
    │   ├── currency.py        # Currency conversion
    │   └── tax_calculations.py # Tax calculation utilities
    │
    ├── setup/                 # Installation scripts
    │   ├── __init__.py
    │   └── install.py         # Post-install setup
    │
    ├── fixtures/              # Default data
    │   └── default_data.json  # VAT configs, treaties
    │
    ├── tests/                 # Unit tests
    │   ├── __init__.py
    │   └── test_tax_calculations.py
    │
    └── public/                # Frontend assets
        ├── css/
        │   └── hrms_freelancer.css
        └── js/
            ├── hrms_freelancer.js
            └── components/
                ├── FreelancerDashboard.vue
                ├── TaxCalculator.vue
                ├── ComplianceCard.vue
                ├── TaxInfoPanel.vue
                ├── ContractList.vue
                └── PaymentList.vue
```

## Key Features

### 1. Freelancer Management
- Complete profile with personal and professional details
- EU/non-EU residency tracking
- VAT registration and validation
- Tax ID management by country
- Skills and certifications tracking
- GDPR consent management

### 2. Contract Management
- Multiple contract types (Fixed-Term, Open-Ended, Project-Based, Retainer)
- Milestone-based payment schedules
- Contract renewal and termination workflows
- Document attachments

### 3. Payment Processing
- Invoice-based payments (not salary slips)
- Line item breakdown with quantities and rates
- Expense reimbursement tracking
- Automatic tax calculations

### 4. Tax Compliance

#### EU (2026 Standards)
- VAT reverse charge mechanism for B2B transactions
- Automatic EU country detection
- VIES VAT number validation
- Country-specific VAT rates

#### International
- Tax treaty support for reduced withholding rates
- Certificate-based rate reductions
- Automatic withholding calculation

### 5. GDPR Compliance
- Consent tracking with timestamps
- Immutable audit log
- Data export functionality
- Right to erasure support

## Installation

```bash
# Navigate to frappe-bench
cd frappe-bench

# Get the app
bench get-app hrms_freelancer [path/url]

# Install on site
bench --site [site-name] install-app hrms_freelancer

# Run migrations
bench --site [site-name] migrate
```

## Configuration

After installation:
1. VAT configurations and tax treaties are auto-created
2. Custom roles (Freelancer Manager, Freelancer Approver) are created
3. Payment approval workflow is set up

## API Methods

### Freelancer
- `create_contract()` - Create new contract
- `create_payment()` - Create new payment
- `export_gdpr_data()` - Export personal data
- `validate_vat_number_vies()` - Validate VAT with EU VIES

### Freelancer Contract
- `create_payment_from_contract()` - Create payment for milestones
- `renew_contract()` - Create renewal contract
- `terminate_contract()` - End contract early
- `get_contract_summary()` - Get financial summary

### Freelancer Payment
- `approve_payment()` - Approve for payment
- `create_purchase_invoice()` - Create linked Purchase Invoice
- `create_withholding_journal_entry()` - Record withholding tax
- `mark_as_paid()` - Record payment completion

## Scheduled Tasks

- **Daily**: Check contract expirations, update exchange rates
- **Weekly**: GDPR consent review
- **Monthly**: Generate compliance reports
- **Quarterly**: VAT reporting reminders

## Support

For issues or feature requests, please contact the development team.
