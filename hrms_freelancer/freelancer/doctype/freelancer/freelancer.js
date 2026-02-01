// Copyright (c) 2024, HRMS Freelancer and contributors
// For license information, please see license.txt

frappe.ui.form.on('Freelancer', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Create Contract'), function() {
                frm.call({
                    method: 'create_contract',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            frappe.set_route('Form', 'Freelancer Contract', r.message);
                        }
                    }
                });
            }, __('Actions'));

            frm.add_custom_button(__('Create Payment'), function() {
                frm.call({
                    method: 'create_payment',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            frappe.set_route('Form', 'Freelancer Payment', r.message);
                        }
                    }
                });
            }, __('Actions'));

            frm.add_custom_button(__('Export GDPR Data'), function() {
                frm.call({
                    method: 'export_gdpr_data',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('GDPR data exported. Check the attachment.'));
                        }
                    }
                });
            }, __('GDPR'));

            frm.add_custom_button(__('View Contracts'), function() {
                frappe.set_route('List', 'Freelancer Contract', {
                    freelancer: frm.doc.name
                });
            }, __('View'));

            frm.add_custom_button(__('View Payments'), function() {
                frappe.set_route('List', 'Freelancer Payment', {
                    freelancer: frm.doc.name
                });
            }, __('View'));
        }

        // Show compliance dashboard
        if (!frm.is_new()) {
            render_compliance_dashboard(frm);
        }

        // Setup country change handler
        setup_country_handlers(frm);
    },

    residency_country: function(frm) {
        update_eu_status(frm);
        check_vat_requirements(frm);
    },

    tax_residency_country: function(frm) {
        update_tax_status(frm);
    },

    vat_registered: function(frm) {
        check_vat_requirements(frm);
    },

    vat_number: function(frm) {
        if (frm.doc.vat_number && frm.doc.vat_registered) {
            validate_vat_number(frm);
        }
    },

    hourly_rate: function(frm) {
        calculate_daily_equivalent(frm);
        check_minimum_wage(frm);
    },

    daily_rate: function(frm) {
        calculate_hourly_equivalent(frm);
        check_minimum_wage(frm);
    },

    gdpr_consent_obtained: function(frm) {
        if (frm.doc.gdpr_consent_obtained && !frm.doc.gdpr_consent_date) {
            frm.set_value('gdpr_consent_date', frappe.datetime.now_date());
        }
    }
});

// EU Countries list for 2026
const EU_COUNTRIES = [
    'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
    'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
    'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands',
    'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden'
];

function setup_country_handlers(frm) {
    // Auto-set tax residency to residency country if empty
    frm.set_query('tax_residency_country', function() {
        return {
            query: 'erpnext.setup.doctype.country.country.get_countries'
        };
    });
}

function update_eu_status(frm) {
    const is_eu = EU_COUNTRIES.includes(frm.doc.residency_country);
    frm.set_value('is_eu_resident', is_eu);
    
    if (is_eu) {
        frm.dashboard.set_headline(__('EU Resident - Reverse charge mechanism may apply'));
    } else {
        frm.dashboard.set_headline(__('Non-EU Resident - Check withholding tax requirements'));
    }
}

function update_tax_status(frm) {
    const is_eu = EU_COUNTRIES.includes(frm.doc.tax_residency_country);
    
    // Update tax hints based on country
    if (frm.doc.tax_residency_country === 'Netherlands') {
        frm.set_df_property('tax_identification_number', 'description', 
            'Enter your BSN (Burgerservicenummer) - 9 digits');
    } else if (frm.doc.tax_residency_country === 'Germany') {
        frm.set_df_property('tax_identification_number', 'description', 
            'Enter your Steuernummer - 10-11 digits');
    } else if (frm.doc.tax_residency_country === 'United Kingdom') {
        frm.set_df_property('tax_identification_number', 'description', 
            'Enter your UTR (Unique Taxpayer Reference) - 10 digits');
    }
}

function check_vat_requirements(frm) {
    const is_eu = EU_COUNTRIES.includes(frm.doc.residency_country);
    
    if (is_eu && !frm.doc.vat_registered) {
        frappe.show_alert({
            message: __('EU-based freelancers may need to be VAT registered. Please verify.'),
            indicator: 'orange'
        }, 5);
    }
    
    // Make VAT number mandatory if registered
    frm.toggle_reqd('vat_number', frm.doc.vat_registered);
}

function validate_vat_number(frm) {
    if (!frm.doc.vat_number) return;
    
    // Clean VAT number
    let vat = frm.doc.vat_number.replace(/[^A-Z0-9]/gi, '').toUpperCase();
    
    // Basic format validation
    const vat_patterns = {
        'Netherlands': /^NL[0-9]{9}B[0-9]{2}$/,
        'Germany': /^DE[0-9]{9}$/,
        'France': /^FR[A-Z0-9]{2}[0-9]{9}$/,
        'Belgium': /^BE[0-9]{10}$/,
        'Italy': /^IT[0-9]{11}$/,
        'Spain': /^ES[A-Z0-9][0-9]{7}[A-Z0-9]$/,
        'United Kingdom': /^GB([0-9]{9}|[0-9]{12}|GD[0-9]{3}|HA[0-9]{3})$/
    };
    
    const pattern = vat_patterns[frm.doc.residency_country];
    if (pattern && !pattern.test(vat)) {
        frappe.show_alert({
            message: __('VAT number format may be incorrect for {0}', [frm.doc.residency_country]),
            indicator: 'orange'
        }, 5);
    }
    
    // If EU, offer VIES validation
    if (EU_COUNTRIES.includes(frm.doc.residency_country)) {
        frappe.confirm(
            __('Would you like to validate this VAT number with VIES?'),
            function() {
                frm.call({
                    method: 'validate_vat_number_vies',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message && r.message.valid) {
                            frappe.show_alert({
                                message: __('VAT number validated successfully'),
                                indicator: 'green'
                            }, 5);
                        } else {
                            frappe.show_alert({
                                message: __('VAT validation failed: {0}', [r.message.error || 'Unknown error']),
                                indicator: 'red'
                            }, 5);
                        }
                    }
                });
            }
        );
    }
}

function calculate_daily_equivalent(frm) {
    if (frm.doc.hourly_rate && !frm.doc.__daily_changed) {
        frm.__hourly_changed = true;
        // Assuming 8 hours per day
        frm.set_value('daily_rate', frm.doc.hourly_rate * 8);
        frm.__hourly_changed = false;
    }
}

function calculate_hourly_equivalent(frm) {
    if (frm.doc.daily_rate && !frm.__hourly_changed) {
        frm.__daily_changed = true;
        frm.set_value('hourly_rate', frm.doc.daily_rate / 8);
        frm.__daily_changed = false;
    }
}

function check_minimum_wage(frm) {
    // 2026 minimum wages (approximate hourly rates)
    const minimum_wages = {
        'Netherlands': 14.50,
        'Germany': 14.00,
        'France': 13.00,
        'Belgium': 13.50,
        'Luxembourg': 15.50,
        'Ireland': 13.50,
        'Spain': 10.00,
        'Italy': 10.00,
        'Portugal': 5.50
    };
    
    const min_wage = minimum_wages[frm.doc.residency_country];
    if (min_wage && frm.doc.hourly_rate && frm.doc.hourly_rate < min_wage) {
        frappe.show_alert({
            message: __('Warning: Rate of {0} is below minimum wage of {1} EUR/hour in {2}', 
                [frm.doc.hourly_rate, min_wage, frm.doc.residency_country]),
            indicator: 'orange'
        }, 7);
    }
}

function render_compliance_dashboard(frm) {
    let html = `
        <div class="freelancer-compliance-dashboard">
            <h5>${__('Compliance Status')}</h5>
            <div class="row">
                <div class="col-sm-4">
                    <div class="compliance-item ${frm.doc.gdpr_consent_obtained ? 'compliant' : 'non-compliant'}">
                        <i class="fa ${frm.doc.gdpr_consent_obtained ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                        <span>${__('GDPR Consent')}</span>
                    </div>
                </div>
                <div class="col-sm-4">
                    <div class="compliance-item ${frm.doc.tax_certificate ? 'compliant' : 'pending'}">
                        <i class="fa ${frm.doc.tax_certificate ? 'fa-check-circle' : 'fa-clock-o'}"></i>
                        <span>${__('Tax Certificate')}</span>
                    </div>
                </div>
                <div class="col-sm-4">
                    <div class="compliance-item ${frm.doc.vat_registered ? (frm.doc.vat_number ? 'compliant' : 'non-compliant') : 'na'}">
                        <i class="fa ${frm.doc.vat_registered ? (frm.doc.vat_number ? 'fa-check-circle' : 'fa-exclamation-circle') : 'fa-minus-circle'}"></i>
                        <span>${__('VAT Registration')}</span>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .freelancer-compliance-dashboard {
                padding: 15px;
                background: var(--bg-color);
                border-radius: 8px;
                margin-bottom: 15px;
            }
            .compliance-item {
                display: flex;
                align-items: center;
                padding: 10px;
                border-radius: 5px;
                margin: 5px 0;
            }
            .compliance-item i {
                margin-right: 10px;
                font-size: 18px;
            }
            .compliance-item.compliant {
                background: rgba(40, 167, 69, 0.1);
                color: #28a745;
            }
            .compliance-item.non-compliant {
                background: rgba(220, 53, 69, 0.1);
                color: #dc3545;
            }
            .compliance-item.pending {
                background: rgba(255, 193, 7, 0.1);
                color: #ffc107;
            }
            .compliance-item.na {
                background: rgba(108, 117, 125, 0.1);
                color: #6c757d;
            }
        </style>
    `;
    
    frm.set_intro(html, true);
}
