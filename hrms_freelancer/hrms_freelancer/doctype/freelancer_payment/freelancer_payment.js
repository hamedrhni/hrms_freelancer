// Copyright (c) 2024, HRMS Freelancer and contributors
// For license information, please see license.txt

frappe.ui.form.on('Freelancer Payment', {
    refresh: function(frm) {
        // Add custom buttons based on status
        if (!frm.is_new()) {
            if (frm.doc.status === 'Draft') {
                frm.add_custom_button(__('Submit for Approval'), function() {
                    frm.set_value('status', 'Pending Approval');
                    frm.save();
                });
            }
            
            if (frm.doc.status === 'Pending Approval' && has_approval_permission(frm)) {
                frm.add_custom_button(__('Approve'), function() {
                    approve_payment(frm);
                }, __('Actions'));
                
                frm.add_custom_button(__('Reject'), function() {
                    reject_payment(frm);
                }, __('Actions'));
            }
            
            if (frm.doc.status === 'Approved') {
                frm.add_custom_button(__('Create Purchase Invoice'), function() {
                    create_purchase_invoice(frm);
                }, __('Accounting'));
                
                frm.add_custom_button(__('Mark as Paid'), function() {
                    mark_as_paid(frm);
                }, __('Actions'));
            }
            
            if (frm.doc.withholding_tax_amount > 0 && frm.doc.status === 'Paid') {
                frm.add_custom_button(__('Create Withholding Entry'), function() {
                    create_withholding_entry(frm);
                }, __('Accounting'));
            }
        }
        
        // Show tax breakdown
        if (!frm.is_new()) {
            render_tax_breakdown(frm);
        }
        
        // Setup handlers
        setup_payment_handlers(frm);
    },
    
    freelancer: function(frm) {
        if (frm.doc.freelancer) {
            frappe.db.get_doc('Freelancer', frm.doc.freelancer).then(doc => {
                frm.set_value('freelancer_name', doc.full_name);
                frm.set_value('currency', doc.preferred_currency || 'EUR');
                frm.set_value('is_eu_freelancer', doc.is_eu_resident);
                frm.set_value('vat_registered', doc.vat_registered);
                frm.set_value('vat_number', doc.vat_number);
                
                // Auto-fill bank details if available
                if (doc.bank_account_holder) {
                    frm.set_value('bank_account_name', doc.bank_account_holder);
                    frm.set_value('iban', doc.iban);
                    frm.set_value('bic_swift', doc.bic_swift);
                }
            });
        }
    },
    
    contract: function(frm) {
        if (frm.doc.contract) {
            frappe.db.get_doc('Freelancer Contract', frm.doc.contract).then(doc => {
                frm.set_value('freelancer', doc.freelancer);
                frm.set_value('currency', doc.currency);
                frm.set_value('apply_reverse_charge', doc.apply_reverse_charge);
            });
        }
    },
    
    base_amount: function(frm) {
        calculate_taxes(frm);
    },
    
    vat_rate: function(frm) {
        calculate_taxes(frm);
    },
    
    apply_reverse_charge: function(frm) {
        if (frm.doc.apply_reverse_charge) {
            frm.set_value('vat_rate', 0);
            frm.set_value('vat_amount', 0);
            frm.set_df_property('vat_rate', 'read_only', 1);
        } else {
            frm.set_df_property('vat_rate', 'read_only', 0);
        }
        calculate_taxes(frm);
    },
    
    withholding_rate: function(frm) {
        calculate_taxes(frm);
    },
    
    validate: function(frm) {
        validate_payment_items(frm);
        validate_tax_calculations(frm);
    }
});

frappe.ui.form.on('Freelancer Payment Item', {
    quantity: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    payment_items_remove: function(frm) {
        calculate_base_from_items(frm);
    }
});

frappe.ui.form.on('Freelancer Payment Expense', {
    amount: function(frm, cdt, cdn) {
        calculate_total_expenses(frm);
    },
    
    expense_reimbursements_remove: function(frm) {
        calculate_total_expenses(frm);
    }
});

function setup_payment_handlers(frm) {
    // Set query for contracts
    frm.set_query('contract', function() {
        return {
            filters: {
                freelancer: frm.doc.freelancer,
                status: 'Active',
                docstatus: 1
            }
        };
    });
}

function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = (row.quantity || 0) * (row.rate || 0);
    frm.refresh_field('payment_items');
    calculate_base_from_items(frm);
}

function calculate_base_from_items(frm) {
    let total = 0;
    (frm.doc.payment_items || []).forEach(item => {
        total += item.amount || 0;
    });
    
    if (total > 0) {
        frm.set_value('base_amount', total);
    }
}

function calculate_total_expenses(frm) {
    let total = 0;
    (frm.doc.expense_reimbursements || []).forEach(exp => {
        if (exp.approved) {
            total += exp.amount || 0;
        }
    });
    
    frm.set_value('total_expenses', total);
    calculate_taxes(frm);
}

function calculate_taxes(frm) {
    const base = flt(frm.doc.base_amount) || 0;
    const expenses = flt(frm.doc.total_expenses) || 0;
    const gross = base + expenses;
    
    // VAT calculation
    let vat = 0;
    if (!frm.doc.apply_reverse_charge && frm.doc.vat_rate > 0) {
        vat = gross * (frm.doc.vat_rate / 100);
    }
    frm.set_value('vat_amount', vat);
    
    // Withholding tax (on gross, before VAT)
    let withholding = 0;
    if (frm.doc.withholding_rate > 0) {
        withholding = gross * (frm.doc.withholding_rate / 100);
    }
    frm.set_value('withholding_tax_amount', withholding);
    
    // Net payable
    const net = gross + vat - withholding;
    frm.set_value('net_payable', net);
    
    // Update display
    update_tax_display(frm, {
        base: base,
        expenses: expenses,
        gross: gross,
        vat: vat,
        withholding: withholding,
        net: net
    });
}

function update_tax_display(frm, amounts) {
    // This updates a visual breakdown shown in the form
    frm.set_df_property('base_amount', 'description', 
        __('Services total: {0}', [format_currency(amounts.base, frm.doc.currency)]));
}

function validate_payment_items(frm) {
    if (!frm.doc.payment_items || frm.doc.payment_items.length === 0) {
        if (!frm.doc.base_amount || frm.doc.base_amount <= 0) {
            frappe.throw(__('Please add payment items or enter a base amount'));
        }
    }
}

function validate_tax_calculations(frm) {
    // Verify calculations are correct
    const base = flt(frm.doc.base_amount) || 0;
    const expenses = flt(frm.doc.total_expenses) || 0;
    const gross = base + expenses;
    
    let expected_vat = 0;
    if (!frm.doc.apply_reverse_charge && frm.doc.vat_rate > 0) {
        expected_vat = gross * (frm.doc.vat_rate / 100);
    }
    
    let expected_withholding = 0;
    if (frm.doc.withholding_rate > 0) {
        expected_withholding = gross * (frm.doc.withholding_rate / 100);
    }
    
    const expected_net = gross + expected_vat - expected_withholding;
    
    if (Math.abs(frm.doc.net_payable - expected_net) > 0.01) {
        frappe.show_alert({
            message: __('Tax calculations have been recalculated'),
            indicator: 'blue'
        });
        frm.set_value('vat_amount', expected_vat);
        frm.set_value('withholding_tax_amount', expected_withholding);
        frm.set_value('net_payable', expected_net);
    }
}

function has_approval_permission(frm) {
    // Check if current user can approve
    return frappe.user.has_role('HR Manager') || 
           frappe.user.has_role('Accounts Manager') ||
           frappe.user.has_role('System Manager');
}

function approve_payment(frm) {
    frm.call({
        method: 'approve_payment',
        doc: frm.doc,
        callback: function(r) {
            if (!r.exc) {
                frm.reload_doc();
            }
        }
    });
}

function reject_payment(frm) {
    frappe.prompt({
        fieldname: 'reason',
        fieldtype: 'Small Text',
        label: __('Rejection Reason'),
        reqd: 1
    }, function(values) {
        frm.set_value('status', 'Rejected');
        frm.set_value('notes', (frm.doc.notes || '') + '\n\nRejected: ' + values.reason);
        frm.save();
    }, __('Reject Payment'), __('Reject'));
}

function create_purchase_invoice(frm) {
    frm.call({
        method: 'create_purchase_invoice',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                frappe.set_route('Form', 'Purchase Invoice', r.message);
            }
        }
    });
}

function mark_as_paid(frm) {
    frappe.prompt([
        {
            fieldname: 'payment_date',
            fieldtype: 'Date',
            label: __('Payment Date'),
            default: frappe.datetime.nowdate(),
            reqd: 1
        },
        {
            fieldname: 'payment_reference',
            fieldtype: 'Data',
            label: __('Payment Reference')
        }
    ], function(values) {
        frm.call({
            method: 'mark_as_paid',
            doc: frm.doc,
            args: {
                payment_date: values.payment_date,
                reference: values.payment_reference
            },
            callback: function(r) {
                if (!r.exc) {
                    frm.reload_doc();
                }
            }
        });
    }, __('Mark as Paid'), __('Confirm'));
}

function create_withholding_entry(frm) {
    frm.call({
        method: 'create_withholding_journal_entry',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                frappe.set_route('Form', 'Journal Entry', r.message);
            }
        }
    });
}

function render_tax_breakdown(frm) {
    if (!frm.doc.base_amount) return;
    
    const base = flt(frm.doc.base_amount);
    const expenses = flt(frm.doc.total_expenses);
    const vat = flt(frm.doc.vat_amount);
    const withholding = flt(frm.doc.withholding_tax_amount);
    const net = flt(frm.doc.net_payable);
    const currency = frm.doc.currency || 'EUR';
    
    let reverseChargeNote = '';
    if (frm.doc.apply_reverse_charge) {
        reverseChargeNote = `
            <div class="reverse-charge-notice">
                <i class="fa fa-info-circle"></i>
                ${__('EU Reverse Charge: VAT to be accounted for by recipient')}
            </div>
        `;
    }
    
    let html = `
        <div class="payment-tax-breakdown">
            <h5>${__('Payment Breakdown')}</h5>
            <table class="table table-bordered">
                <tbody>
                    <tr>
                        <td>${__('Services')}</td>
                        <td class="text-right">${format_currency(base, currency)}</td>
                    </tr>
                    ${expenses > 0 ? `
                    <tr>
                        <td>${__('Expenses')}</td>
                        <td class="text-right">${format_currency(expenses, currency)}</td>
                    </tr>
                    ` : ''}
                    <tr class="subtotal">
                        <td><strong>${__('Subtotal')}</strong></td>
                        <td class="text-right"><strong>${format_currency(base + expenses, currency)}</strong></td>
                    </tr>
                    ${vat > 0 ? `
                    <tr>
                        <td>${__('VAT')} (${frm.doc.vat_rate}%)</td>
                        <td class="text-right">+ ${format_currency(vat, currency)}</td>
                    </tr>
                    ` : ''}
                    ${withholding > 0 ? `
                    <tr class="withholding">
                        <td>${__('Withholding Tax')} (${frm.doc.withholding_rate}%)</td>
                        <td class="text-right text-danger">- ${format_currency(withholding, currency)}</td>
                    </tr>
                    ` : ''}
                    <tr class="total">
                        <td><strong>${__('Net Payable')}</strong></td>
                        <td class="text-right"><strong>${format_currency(net, currency)}</strong></td>
                    </tr>
                </tbody>
            </table>
            ${reverseChargeNote}
        </div>
        <style>
            .payment-tax-breakdown {
                padding: 15px;
                background: var(--bg-color);
                border-radius: 8px;
                margin-bottom: 15px;
            }
            .payment-tax-breakdown table {
                margin-bottom: 0;
            }
            .payment-tax-breakdown .subtotal td {
                background: var(--subtle-fg);
            }
            .payment-tax-breakdown .total td {
                background: var(--primary);
                color: white;
            }
            .payment-tax-breakdown .withholding td {
                background: rgba(220, 53, 69, 0.1);
            }
            .reverse-charge-notice {
                margin-top: 10px;
                padding: 10px;
                background: rgba(23, 162, 184, 0.1);
                border-radius: 5px;
                color: #17a2b8;
            }
            .reverse-charge-notice i {
                margin-right: 5px;
            }
        </style>
    `;
    
    frm.set_intro(html, true);
}
