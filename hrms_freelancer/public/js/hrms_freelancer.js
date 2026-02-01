/**
 * HRMS Freelancer - Main JavaScript Bundle
 * Entry point for all client-side functionality
 */

// Register Vue components when DOM is ready
frappe.ready(function() {
    console.log('HRMS Freelancer module loaded');
    
    // Initialize any global handlers
    initializeFreelancerModule();
});

function initializeFreelancerModule() {
    // Add custom list view actions
    if (frappe.listview_settings) {
        setupListViewSettings();
    }
    
    // Register keyboard shortcuts
    registerKeyboardShortcuts();
    
    // Initialize tooltips for compliance indicators
    initializeComplianceTooltips();
}

function setupListViewSettings() {
    // Freelancer list view
    frappe.listview_settings['Freelancer'] = {
        add_fields: ['status', 'is_eu_resident', 'residency_country', 'vat_registered'],
        get_indicator: function(doc) {
            if (doc.status === 'Active') {
                return [__('Active'), 'green', 'status,=,Active'];
            } else if (doc.status === 'Inactive') {
                return [__('Inactive'), 'gray', 'status,=,Inactive'];
            } else if (doc.status === 'Onboarding') {
                return [__('Onboarding'), 'orange', 'status,=,Onboarding'];
            }
        },
        formatters: {
            residency_country: function(value) {
                const euCountries = [
                    'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
                    'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
                    'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands',
                    'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden'
                ];
                const isEU = euCountries.includes(value);
                const badge = isEU ? 
                    '<span class="eu-status-badge eu-resident"><i class="fa fa-flag"></i> EU</span>' :
                    '<span class="eu-status-badge non-eu-resident"><i class="fa fa-globe"></i> Non-EU</span>';
                return value + ' ' + badge;
            }
        }
    };
    
    // Freelancer Payment list view
    frappe.listview_settings['Freelancer Payment'] = {
        add_fields: ['status', 'net_payable', 'currency', 'apply_reverse_charge'],
        get_indicator: function(doc) {
            const indicators = {
                'Draft': ['Draft', 'gray'],
                'Pending Approval': ['Pending Approval', 'orange'],
                'Approved': ['Approved', 'blue'],
                'Paid': ['Paid', 'green'],
                'Rejected': ['Rejected', 'red']
            };
            const ind = indicators[doc.status] || ['Unknown', 'gray'];
            return [__(ind[0]), ind[1], 'status,=,' + doc.status];
        },
        formatters: {
            net_payable: function(value, df, doc) {
                return format_currency(value, doc.currency || 'EUR');
            }
        }
    };
    
    // Freelancer Contract list view
    frappe.listview_settings['Freelancer Contract'] = {
        add_fields: ['status', 'total_contract_value', 'currency', 'start_date', 'end_date'],
        get_indicator: function(doc) {
            const indicators = {
                'Active': ['Active', 'green'],
                'Draft': ['Draft', 'gray'],
                'Expired': ['Expired', 'red'],
                'Terminated': ['Terminated', 'orange']
            };
            const ind = indicators[doc.status] || ['Unknown', 'gray'];
            return [__(ind[0]), ind[1], 'status,=,' + doc.status];
        }
    };
}

function registerKeyboardShortcuts() {
    // Ctrl+Shift+F: Quick search freelancers
    frappe.ui.keys.add_shortcut({
        shortcut: 'ctrl+shift+f',
        action: function() {
            frappe.set_route('List', 'Freelancer');
        },
        description: __('Go to Freelancer List'),
        page: '*'
    });
    
    // Ctrl+Shift+P: Quick search payments
    frappe.ui.keys.add_shortcut({
        shortcut: 'ctrl+shift+p',
        action: function() {
            frappe.set_route('List', 'Freelancer Payment');
        },
        description: __('Go to Freelancer Payments'),
        page: '*'
    });
}

function initializeComplianceTooltips() {
    // Will be called when compliance indicators are rendered
    $(document).on('mouseover', '.compliance-item', function() {
        const $item = $(this);
        if (!$item.data('tooltip-initialized')) {
            const status = $item.hasClass('compliant') ? 'Compliant' :
                          $item.hasClass('non-compliant') ? 'Action Required' :
                          $item.hasClass('pending') ? 'Pending' : 'Not Applicable';
            $item.tooltip({
                title: status,
                placement: 'top'
            });
            $item.data('tooltip-initialized', true);
        }
    });
}

// Utility functions
window.hrms_freelancer = {
    // Calculate tax breakdown
    calculate_taxes: function(base_amount, vat_rate, withholding_rate, reverse_charge) {
        let vat = reverse_charge ? 0 : base_amount * (vat_rate / 100);
        let withholding = base_amount * (withholding_rate / 100);
        let net = base_amount + vat - withholding;
        
        return {
            base_amount: base_amount,
            vat_amount: vat,
            withholding_amount: withholding,
            net_payable: net,
            reverse_charge: reverse_charge
        };
    },
    
    // Format currency
    format_currency: function(amount, currency) {
        return new Intl.NumberFormat('en-EU', {
            style: 'currency',
            currency: currency || 'EUR'
        }).format(amount || 0);
    },
    
    // Check if country is EU
    is_eu_country: function(country) {
        const eu_countries = [
            'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
            'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
            'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands',
            'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden'
        ];
        return eu_countries.includes(country);
    },
    
    // Validate VAT number format
    validate_vat_format: function(vat_number, country) {
        const patterns = {
            'Netherlands': /^NL[0-9]{9}B[0-9]{2}$/,
            'Germany': /^DE[0-9]{9}$/,
            'France': /^FR[A-Z0-9]{2}[0-9]{9}$/,
            'Belgium': /^BE[0-9]{10}$/,
            'Italy': /^IT[0-9]{11}$/,
            'Spain': /^ES[A-Z0-9][0-9]{7}[A-Z0-9]$/,
            'United Kingdom': /^GB([0-9]{9}|[0-9]{12}|GD[0-9]{3}|HA[0-9]{3})$/
        };
        
        const pattern = patterns[country];
        if (!pattern) return { valid: true, message: 'No pattern for this country' };
        
        const clean_vat = vat_number.replace(/[^A-Z0-9]/gi, '').toUpperCase();
        return {
            valid: pattern.test(clean_vat),
            message: pattern.test(clean_vat) ? 'Valid format' : 'Invalid format'
        };
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.hrms_freelancer;
}
