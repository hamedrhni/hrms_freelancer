/**
 * Employee DocType Extension for HRMS Freelancer
 * Adds freelancer-related fields and actions to Employee form
 */

frappe.ui.form.on('Employee', {
    refresh: function(frm) {
        // Add button to convert employee to freelancer
        if (!frm.is_new() && frm.doc.status === 'Active') {
            frm.add_custom_button(__('Create Freelancer Profile'), function() {
                createFreelancerFromEmployee(frm);
            }, __('Actions'));
        }

        // Show linked freelancer profile if exists
        if (frm.doc.custom_linked_freelancer) {
            frm.add_custom_button(__('View Freelancer Profile'), function() {
                frappe.set_route('Form', 'Freelancer', frm.doc.custom_linked_freelancer);
            }, __('Links'));
        }

        // Add indicator for hybrid workers (both employee and freelancer)
        checkHybridWorkerStatus(frm);
    },

    onload: function(frm) {
        // Set up filters for freelancer-related fields
        setupFreelancerFilters(frm);
    }
});

/**
 * Create a Freelancer profile from an existing Employee
 */
function createFreelancerFromEmployee(frm) {
    frappe.confirm(
        __('This will create a Freelancer profile linked to this employee. Continue?'),
        function() {
            frappe.call({
                method: 'frappe.client.insert',
                args: {
                    doc: {
                        doctype: 'Freelancer',
                        first_name: frm.doc.first_name,
                        middle_name: frm.doc.middle_name,
                        last_name: frm.doc.last_name,
                        email: frm.doc.personal_email || frm.doc.company_email,
                        phone: frm.doc.cell_number,
                        country: frm.doc.country,
                        company: frm.doc.company,
                        linked_employee: frm.doc.name,
                        worker_type: 'Freelancer',
                        status: 'Onboarding',
                        currency: frappe.defaults.get_default('currency') || 'EUR'
                    }
                },
                callback: function(r) {
                    if (r.message) {
                        // Update employee with linked freelancer
                        frm.set_value('custom_linked_freelancer', r.message.name);
                        frm.save();
                        
                        frappe.show_alert({
                            message: __('Freelancer profile {0} created', [r.message.name]),
                            indicator: 'green'
                        });
                        
                        // Navigate to the new freelancer
                        frappe.set_route('Form', 'Freelancer', r.message.name);
                    }
                }
            });
        }
    );
}

/**
 * Check if employee is also a freelancer (hybrid worker)
 */
function checkHybridWorkerStatus(frm) {
    if (frm.doc.custom_linked_freelancer) {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Freelancer',
                filters: { name: frm.doc.custom_linked_freelancer },
                fieldname: ['status', 'worker_type']
            },
            callback: function(r) {
                if (r.message && r.message.status === 'Active') {
                    frm.dashboard.add_indicator(
                        __('Hybrid Worker (Employee + {0})', [r.message.worker_type]),
                        'blue'
                    );
                }
            }
        });
    }
}

/**
 * Set up field filters for freelancer integration
 */
function setupFreelancerFilters(frm) {
    // Filter linked freelancer by company
    frm.set_query('custom_linked_freelancer', function() {
        return {
            filters: {
                company: frm.doc.company,
                status: ['not in', ['Blacklisted']]
            }
        };
    });
}
