// Copyright (c) 2024, HRMS Freelancer and contributors
// For license information, please see license.txt

frappe.ui.form.on('Freelancer Contract', {
    refresh: function(frm) {
        // Add custom buttons based on status
        if (!frm.is_new() && frm.doc.docstatus === 1) {
            if (frm.doc.status === 'Active') {
                frm.add_custom_button(__('Create Payment'), function() {
                    create_payment_from_contract(frm);
                }, __('Actions'));

                frm.add_custom_button(__('Terminate Contract'), function() {
                    terminate_contract(frm);
                }, __('Actions'));

                frm.add_custom_button(__('Renew Contract'), function() {
                    renew_contract(frm);
                }, __('Actions'));
            }
        }

        // Show contract summary
        if (!frm.is_new()) {
            render_contract_summary(frm);
        }

        // Setup milestone handlers
        setup_milestone_handlers(frm);
    },

    freelancer: function(frm) {
        if (frm.doc.freelancer) {
            // Fetch freelancer details
            frappe.db.get_doc('Freelancer', frm.doc.freelancer).then(doc => {
                frm.set_value('freelancer_name', doc.full_name);
                frm.set_value('currency', doc.preferred_currency || 'EUR');
                frm.set_value('hourly_rate', doc.hourly_rate);
                frm.set_value('daily_rate', doc.daily_rate);
                
                // Set tax defaults
                if (doc.is_eu_resident) {
                    frm.set_value('apply_reverse_charge', 1);
                    frm.set_value('tax_notes', 'EU B2B transaction - Reverse charge applies');
                }
            });
        }
    },

    contract_type: function(frm) {
        update_contract_type_fields(frm);
    },

    start_date: function(frm) {
        validate_dates(frm);
        calculate_contract_duration(frm);
    },

    end_date: function(frm) {
        validate_dates(frm);
        calculate_contract_duration(frm);
    },

    total_contract_value: function(frm) {
        calculate_milestone_percentages(frm);
    },

    validate: function(frm) {
        validate_milestones(frm);
        validate_payment_schedule(frm);
    }
});

frappe.ui.form.on('Freelancer Contract Milestone', {
    amount: function(frm, cdt, cdn) {
        calculate_milestone_percentage(frm, cdt, cdn);
        calculate_total_from_milestones(frm);
    },

    percentage_of_contract: function(frm, cdt, cdn) {
        calculate_milestone_amount(frm, cdt, cdn);
    },

    status: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.status === 'Completed' && !row.actual_completion_date) {
            frappe.model.set_value(cdt, cdn, 'actual_completion_date', frappe.datetime.now_date());
        }
    }
});

function update_contract_type_fields(frm) {
    // Show/hide fields based on contract type
    const type = frm.doc.contract_type;
    
    frm.toggle_display('end_date', type !== 'Open-Ended');
    frm.toggle_reqd('end_date', type === 'Fixed-Term' || type === 'Project-Based');
    
    if (type === 'Retainer') {
        frm.set_df_property('payment_frequency', 'default', 'Monthly');
        frm.set_value('payment_frequency', 'Monthly');
    } else if (type === 'Project-Based') {
        frm.set_df_property('payment_frequency', 'default', 'Milestone');
        frm.set_value('payment_frequency', 'Milestone');
    }
}

function validate_dates(frm) {
    if (frm.doc.start_date && frm.doc.end_date) {
        if (frm.doc.end_date < frm.doc.start_date) {
            frappe.msgprint(__('End date cannot be before start date'));
            frm.set_value('end_date', null);
        }
    }
}

function calculate_contract_duration(frm) {
    if (frm.doc.start_date && frm.doc.end_date) {
        const start = frappe.datetime.str_to_obj(frm.doc.start_date);
        const end = frappe.datetime.str_to_obj(frm.doc.end_date);
        const diff = frappe.datetime.get_diff(end, start);
        
        const months = Math.floor(diff / 30);
        const days = diff % 30;
        
        let duration = '';
        if (months > 0) duration += months + ' month(s) ';
        if (days > 0) duration += days + ' day(s)';
        
        frm.set_df_property('end_date', 'description', __('Duration: {0}', [duration]));
    }
}

function setup_milestone_handlers(frm) {
    frm.set_query('milestone_reference', 'payment_items', function() {
        return {
            filters: {
                parent: frm.doc.name
            }
        };
    });
}

function validate_milestones(frm) {
    if (frm.doc.milestones && frm.doc.milestones.length > 0) {
        let total_percentage = 0;
        let total_amount = 0;
        
        frm.doc.milestones.forEach(m => {
            total_percentage += m.percentage_of_contract || 0;
            total_amount += m.amount || 0;
        });
        
        if (Math.abs(total_percentage - 100) > 0.01 && total_percentage > 0) {
            frappe.msgprint({
                title: __('Milestone Warning'),
                message: __('Milestone percentages total {0}%, not 100%', [total_percentage.toFixed(1)]),
                indicator: 'orange'
            });
        }
        
        if (frm.doc.total_contract_value && Math.abs(total_amount - frm.doc.total_contract_value) > 0.01) {
            frappe.msgprint({
                title: __('Milestone Warning'),
                message: __('Milestone amounts ({0}) do not match contract value ({1})', 
                    [format_currency(total_amount), format_currency(frm.doc.total_contract_value)]),
                indicator: 'orange'
            });
        }
    }
}

function validate_payment_schedule(frm) {
    if (frm.doc.payment_frequency === 'Milestone' && (!frm.doc.milestones || frm.doc.milestones.length === 0)) {
        frappe.msgprint({
            title: __('Missing Milestones'),
            message: __('Please add milestones for milestone-based payment contracts'),
            indicator: 'orange'
        });
    }
}

function calculate_milestone_percentages(frm) {
    if (!frm.doc.total_contract_value || !frm.doc.milestones) return;
    
    frm.doc.milestones.forEach((m, idx) => {
        if (m.amount && !m.__percentage_set) {
            m.percentage_of_contract = (m.amount / frm.doc.total_contract_value) * 100;
        }
    });
    frm.refresh_field('milestones');
}

function calculate_milestone_percentage(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.amount && frm.doc.total_contract_value) {
        row.__percentage_set = false;
        row.percentage_of_contract = (row.amount / frm.doc.total_contract_value) * 100;
        frm.refresh_field('milestones');
    }
}

function calculate_milestone_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.percentage_of_contract && frm.doc.total_contract_value) {
        row.__percentage_set = true;
        row.amount = (row.percentage_of_contract / 100) * frm.doc.total_contract_value;
        frm.refresh_field('milestones');
    }
}

function calculate_total_from_milestones(frm) {
    if (!frm.doc.milestones) return;
    
    let total = 0;
    frm.doc.milestones.forEach(m => {
        total += m.amount || 0;
    });
    
    if (!frm.doc.total_contract_value || frm.doc.total_contract_value === 0) {
        frm.set_value('total_contract_value', total);
    }
}

function create_payment_from_contract(frm) {
    // Show dialog to select milestones
    let milestones = (frm.doc.milestones || []).filter(m => 
        m.status === 'Completed' || m.status === 'Approved'
    );
    
    if (milestones.length === 0) {
        frappe.msgprint(__('No completed milestones available for payment'));
        return;
    }
    
    let d = new frappe.ui.Dialog({
        title: __('Create Payment'),
        fields: [
            {
                fieldname: 'milestones',
                fieldtype: 'MultiSelectList',
                label: __('Select Milestones'),
                options: milestones.map(m => ({
                    value: m.milestone_name,
                    description: format_currency(m.amount)
                }))
            },
            {
                fieldname: 'payment_date',
                fieldtype: 'Date',
                label: __('Payment Date'),
                default: frappe.datetime.nowdate()
            }
        ],
        primary_action_label: __('Create'),
        primary_action: function(values) {
            frm.call({
                method: 'create_payment_from_contract',
                doc: frm.doc,
                args: {
                    milestones: values.milestones,
                    payment_date: values.payment_date
                },
                callback: function(r) {
                    if (r.message) {
                        d.hide();
                        frappe.set_route('Form', 'Freelancer Payment', r.message);
                    }
                }
            });
        }
    });
    d.show();
}

function terminate_contract(frm) {
    frappe.prompt([
        {
            fieldname: 'termination_date',
            fieldtype: 'Date',
            label: __('Termination Date'),
            default: frappe.datetime.nowdate(),
            reqd: 1
        },
        {
            fieldname: 'reason',
            fieldtype: 'Small Text',
            label: __('Reason for Termination'),
            reqd: 1
        }
    ], function(values) {
        frm.call({
            method: 'terminate_contract',
            doc: frm.doc,
            args: {
                termination_date: values.termination_date,
                reason: values.reason
            },
            callback: function(r) {
                if (r.message) {
                    frm.reload_doc();
                }
            }
        });
    }, __('Terminate Contract'), __('Terminate'));
}

function renew_contract(frm) {
    frappe.prompt([
        {
            fieldname: 'new_end_date',
            fieldtype: 'Date',
            label: __('New End Date'),
            reqd: 1
        },
        {
            fieldname: 'new_value',
            fieldtype: 'Currency',
            label: __('New Contract Value'),
            default: frm.doc.total_contract_value
        }
    ], function(values) {
        frm.call({
            method: 'renew_contract',
            doc: frm.doc,
            args: {
                new_end_date: values.new_end_date,
                new_value: values.new_value
            },
            callback: function(r) {
                if (r.message) {
                    frappe.set_route('Form', 'Freelancer Contract', r.message);
                }
            }
        });
    }, __('Renew Contract'), __('Create Renewal'));
}

function render_contract_summary(frm) {
    frm.call({
        method: 'get_contract_summary',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                let summary = r.message;
                let html = `
                    <div class="contract-summary-dashboard">
                        <div class="row">
                            <div class="col-sm-3">
                                <div class="summary-card">
                                    <h6>${__('Contract Value')}</h6>
                                    <span class="value">${format_currency(summary.total_value, frm.doc.currency)}</span>
                                </div>
                            </div>
                            <div class="col-sm-3">
                                <div class="summary-card">
                                    <h6>${__('Paid to Date')}</h6>
                                    <span class="value">${format_currency(summary.paid_amount, frm.doc.currency)}</span>
                                </div>
                            </div>
                            <div class="col-sm-3">
                                <div class="summary-card">
                                    <h6>${__('Remaining')}</h6>
                                    <span class="value">${format_currency(summary.remaining, frm.doc.currency)}</span>
                                </div>
                            </div>
                            <div class="col-sm-3">
                                <div class="summary-card">
                                    <h6>${__('Milestones')}</h6>
                                    <span class="value">${summary.completed_milestones}/${summary.total_milestones}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <style>
                        .contract-summary-dashboard {
                            padding: 15px;
                            background: var(--bg-color);
                            border-radius: 8px;
                            margin-bottom: 15px;
                        }
                        .summary-card {
                            text-align: center;
                            padding: 15px;
                            background: var(--card-bg);
                            border-radius: 8px;
                        }
                        .summary-card h6 {
                            color: var(--text-muted);
                            margin-bottom: 5px;
                        }
                        .summary-card .value {
                            font-size: 18px;
                            font-weight: bold;
                            color: var(--text-color);
                        }
                    </style>
                `;
                frm.set_intro(html, true);
            }
        }
    });
}
