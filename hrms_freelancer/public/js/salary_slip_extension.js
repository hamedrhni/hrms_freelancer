/**
 * Salary Slip DocType Extension for HRMS Freelancer
 * Adds freelancer payment comparison and hybrid worker support
 */

frappe.ui.form.on('Salary Slip', {
    refresh: function(frm) {
        // Add button to view freelancer payments for hybrid workers
        if (!frm.is_new() && frm.doc.employee) {
            checkLinkedFreelancerPayments(frm);
        }

        // Add comparison dashboard for hybrid workers
        if (frm.doc.docstatus === 1) {
            addHybridWorkerComparison(frm);
        }
    },

    employee: function(frm) {
        // Check if employee has linked freelancer profile
        if (frm.doc.employee) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Employee',
                    filters: { name: frm.doc.employee },
                    fieldname: 'custom_linked_freelancer'
                },
                callback: function(r) {
                    if (r.message && r.message.custom_linked_freelancer) {
                        frm.set_intro(
                            __('This employee also has a Freelancer profile: {0}', 
                                ['<a href="/app/freelancer/' + r.message.custom_linked_freelancer + '">' + 
                                 r.message.custom_linked_freelancer + '</a>']),
                            'blue'
                        );
                    }
                }
            });
        }
    }
});

/**
 * Check for freelancer payments in the same period
 */
function checkLinkedFreelancerPayments(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Employee',
            filters: { name: frm.doc.employee },
            fieldname: 'custom_linked_freelancer'
        },
        callback: function(r) {
            if (r.message && r.message.custom_linked_freelancer) {
                // Check for freelancer payments in the same period
                frappe.call({
                    method: 'frappe.client.get_count',
                    args: {
                        doctype: 'Freelancer Payment',
                        filters: {
                            freelancer: r.message.custom_linked_freelancer,
                            posting_date: ['between', [frm.doc.start_date, frm.doc.end_date]],
                            docstatus: ['!=', 2]
                        }
                    },
                    callback: function(count_r) {
                        if (count_r.message > 0) {
                            frm.add_custom_button(
                                __('View Freelancer Payments ({0})', [count_r.message]),
                                function() {
                                    frappe.set_route('List', 'Freelancer Payment', {
                                        freelancer: r.message.custom_linked_freelancer,
                                        posting_date: ['between', [frm.doc.start_date, frm.doc.end_date]]
                                    });
                                },
                                __('Links')
                            );
                        }
                    }
                });
            }
        }
    });
}

/**
 * Add comparison dashboard for hybrid workers
 */
function addHybridWorkerComparison(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Employee',
            filters: { name: frm.doc.employee },
            fieldname: 'custom_linked_freelancer'
        },
        callback: function(r) {
            if (r.message && r.message.custom_linked_freelancer) {
                // Get freelancer payments total for the period
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Freelancer Payment',
                        filters: {
                            freelancer: r.message.custom_linked_freelancer,
                            posting_date: ['between', [frm.doc.start_date, frm.doc.end_date]],
                            docstatus: 1
                        },
                        fields: ['sum(net_amount) as total'],
                        group_by: 'freelancer'
                    },
                    callback: function(payments_r) {
                        if (payments_r.message && payments_r.message.length > 0) {
                            const freelancerTotal = payments_r.message[0].total || 0;
                            const salaryTotal = frm.doc.net_pay || 0;
                            const combinedTotal = freelancerTotal + salaryTotal;

                            // Add info to dashboard
                            frm.dashboard.add_comment(
                                __('Combined Income (Employee + Freelancer): {0}', 
                                    [format_currency(combinedTotal, frm.doc.currency)]),
                                'blue',
                                true
                            );
                        }
                    }
                });
            }
        }
    });
}
