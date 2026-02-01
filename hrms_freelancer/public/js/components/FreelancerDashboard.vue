<template>
  <div class="freelancer-dashboard">
    <!-- Header with Summary -->
    <div class="dashboard-header">
      <div class="header-content">
        <h1>{{ freelancer?.full_name || 'Freelancer Dashboard' }}</h1>
        <div class="status-badge" :class="statusClass">
          {{ freelancer?.status || 'Loading...' }}
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary" @click="createPayment">
          <i class="fa fa-plus"></i> New Payment
        </button>
        <button class="btn btn-secondary" @click="createContract">
          <i class="fa fa-file-text"></i> New Contract
        </button>
      </div>
    </div>

    <!-- Compliance Status Cards -->
    <div class="compliance-cards">
      <ComplianceCard
        title="GDPR Consent"
        :status="freelancer?.gdpr_consent_obtained ? 'compliant' : 'non-compliant'"
        :description="gdprDescription"
        icon="fa-shield"
      />
      <ComplianceCard
        title="Tax Certificate"
        :status="freelancer?.tax_certificate ? 'compliant' : 'pending'"
        :description="taxCertDescription"
        icon="fa-file-text-o"
      />
      <ComplianceCard
        title="VAT Registration"
        :status="vatStatus"
        :description="vatDescription"
        icon="fa-building"
      />
      <ComplianceCard
        title="Contract Status"
        :status="hasActiveContract ? 'compliant' : 'pending'"
        :description="contractDescription"
        icon="fa-handshake-o"
      />
    </div>

    <!-- Main Content Tabs -->
    <div class="dashboard-tabs">
      <div class="tab-headers">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab-btn', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          <i :class="['fa', tab.icon]"></i>
          {{ tab.label }}
          <span v-if="tab.count" class="tab-count">{{ tab.count }}</span>
        </button>
      </div>

      <div class="tab-content">
        <!-- Overview Tab -->
        <div v-show="activeTab === 'overview'" class="tab-pane">
          <div class="overview-grid">
            <!-- Financial Summary -->
            <div class="summary-card">
              <h3>Financial Summary</h3>
              <div class="summary-stats">
                <div class="stat">
                  <span class="stat-value">{{ formatCurrency(totalEarnings) }}</span>
                  <span class="stat-label">Total Earnings</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ formatCurrency(pendingPayments) }}</span>
                  <span class="stat-label">Pending Payments</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ formatCurrency(taxWithheld) }}</span>
                  <span class="stat-label">Tax Withheld</span>
                </div>
              </div>
            </div>

            <!-- Rate Information -->
            <div class="summary-card">
              <h3>Rate Information</h3>
              <div class="rate-info">
                <div class="rate-item">
                  <span class="rate-label">Hourly Rate</span>
                  <span class="rate-value">{{ formatCurrency(freelancer?.hourly_rate) }}/hr</span>
                </div>
                <div class="rate-item">
                  <span class="rate-label">Daily Rate</span>
                  <span class="rate-value">{{ formatCurrency(freelancer?.daily_rate) }}/day</span>
                </div>
                <div class="rate-item">
                  <span class="rate-label">Currency</span>
                  <span class="rate-value">{{ freelancer?.preferred_currency || 'EUR' }}</span>
                </div>
              </div>
            </div>

            <!-- Tax Information -->
            <div class="summary-card full-width">
              <h3>Tax & Residency Information</h3>
              <TaxInfoPanel
                :country="freelancer?.tax_residency_country"
                :is-eu="freelancer?.is_eu_resident"
                :vat-registered="freelancer?.vat_registered"
                :vat-number="freelancer?.vat_number"
              />
            </div>
          </div>
        </div>

        <!-- Contracts Tab -->
        <div v-show="activeTab === 'contracts'" class="tab-pane">
          <ContractList
            :contracts="contracts"
            :currency="freelancer?.preferred_currency"
            @view="viewContract"
            @create-payment="createPaymentFromContract"
          />
        </div>

        <!-- Payments Tab -->
        <div v-show="activeTab === 'payments'" class="tab-pane">
          <PaymentList
            :payments="payments"
            :currency="freelancer?.preferred_currency"
            @view="viewPayment"
            @download-invoice="downloadInvoice"
          />
        </div>

        <!-- Tax Calculator Tab -->
        <div v-show="activeTab === 'tax-calculator'" class="tab-pane">
          <TaxCalculator
            :freelancer-country="freelancer?.tax_residency_country"
            :company-country="companyCountry"
            :is-eu="freelancer?.is_eu_resident"
            :vat-registered="freelancer?.vat_registered"
            :currency="freelancer?.preferred_currency"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import ComplianceCard from './ComplianceCard.vue';
import TaxInfoPanel from './TaxInfoPanel.vue';
import ContractList from './ContractList.vue';
import PaymentList from './PaymentList.vue';
import TaxCalculator from './TaxCalculator.vue';

export default {
  name: 'FreelancerDashboard',
  
  components: {
    ComplianceCard,
    TaxInfoPanel,
    ContractList,
    PaymentList,
    TaxCalculator
  },
  
  props: {
    freelancerId: {
      type: String,
      required: true
    }
  },
  
  setup(props) {
    const freelancer = ref(null);
    const contracts = ref([]);
    const payments = ref([]);
    const activeTab = ref('overview');
    const companyCountry = ref('Netherlands');
    
    const tabs = computed(() => [
      { id: 'overview', label: 'Overview', icon: 'fa-dashboard' },
      { id: 'contracts', label: 'Contracts', icon: 'fa-file-text', count: contracts.value.length },
      { id: 'payments', label: 'Payments', icon: 'fa-money', count: payments.value.length },
      { id: 'tax-calculator', label: 'Tax Calculator', icon: 'fa-calculator' }
    ]);
    
    const statusClass = computed(() => {
      const status = freelancer.value?.status?.toLowerCase();
      return {
        'status-active': status === 'active',
        'status-inactive': status === 'inactive',
        'status-onboarding': status === 'onboarding'
      };
    });
    
    const gdprDescription = computed(() => {
      if (freelancer.value?.gdpr_consent_obtained) {
        return `Consent obtained on ${formatDate(freelancer.value.gdpr_consent_date)}`;
      }
      return 'GDPR consent required before processing personal data';
    });
    
    const taxCertDescription = computed(() => {
      if (freelancer.value?.tax_certificate) {
        return 'Tax residency certificate on file';
      }
      return 'Upload tax certificate for reduced withholding rates';
    });
    
    const vatStatus = computed(() => {
      if (!freelancer.value?.vat_registered) return 'na';
      return freelancer.value?.vat_number ? 'compliant' : 'non-compliant';
    });
    
    const vatDescription = computed(() => {
      if (!freelancer.value?.vat_registered) {
        return 'Not VAT registered';
      }
      if (freelancer.value?.vat_number) {
        return `VAT: ${freelancer.value.vat_number}`;
      }
      return 'VAT number required';
    });
    
    const hasActiveContract = computed(() => {
      return contracts.value.some(c => c.status === 'Active');
    });
    
    const contractDescription = computed(() => {
      const active = contracts.value.filter(c => c.status === 'Active');
      if (active.length === 0) return 'No active contracts';
      return `${active.length} active contract(s)`;
    });
    
    const totalEarnings = computed(() => {
      return payments.value
        .filter(p => p.status === 'Paid')
        .reduce((sum, p) => sum + (p.net_payable || 0), 0);
    });
    
    const pendingPayments = computed(() => {
      return payments.value
        .filter(p => ['Draft', 'Pending Approval', 'Approved'].includes(p.status))
        .reduce((sum, p) => sum + (p.net_payable || 0), 0);
    });
    
    const taxWithheld = computed(() => {
      return payments.value
        .filter(p => p.status === 'Paid')
        .reduce((sum, p) => sum + (p.withholding_tax_amount || 0), 0);
    });
    
    const formatCurrency = (amount, currency = 'EUR') => {
      if (!amount) return '€0.00';
      return new Intl.NumberFormat('en-EU', {
        style: 'currency',
        currency: freelancer.value?.preferred_currency || currency
      }).format(amount);
    };
    
    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      return new Date(dateStr).toLocaleDateString('en-EU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    };
    
    const fetchFreelancer = async () => {
      try {
        const response = await frappe.call({
          method: 'frappe.client.get',
          args: {
            doctype: 'Freelancer',
            name: props.freelancerId
          }
        });
        freelancer.value = response.message;
      } catch (error) {
        console.error('Error fetching freelancer:', error);
      }
    };
    
    const fetchContracts = async () => {
      try {
        const response = await frappe.call({
          method: 'frappe.client.get_list',
          args: {
            doctype: 'Freelancer Contract',
            filters: { freelancer: props.freelancerId },
            fields: ['*'],
            order_by: 'creation desc'
          }
        });
        contracts.value = response.message || [];
      } catch (error) {
        console.error('Error fetching contracts:', error);
      }
    };
    
    const fetchPayments = async () => {
      try {
        const response = await frappe.call({
          method: 'frappe.client.get_list',
          args: {
            doctype: 'Freelancer Payment',
            filters: { freelancer: props.freelancerId },
            fields: ['*'],
            order_by: 'creation desc'
          }
        });
        payments.value = response.message || [];
      } catch (error) {
        console.error('Error fetching payments:', error);
      }
    };
    
    const createPayment = () => {
      frappe.new_doc('Freelancer Payment', {
        freelancer: props.freelancerId
      });
    };
    
    const createContract = () => {
      frappe.new_doc('Freelancer Contract', {
        freelancer: props.freelancerId
      });
    };
    
    const viewContract = (contractName) => {
      frappe.set_route('Form', 'Freelancer Contract', contractName);
    };
    
    const viewPayment = (paymentName) => {
      frappe.set_route('Form', 'Freelancer Payment', paymentName);
    };
    
    const createPaymentFromContract = (contractName) => {
      frappe.new_doc('Freelancer Payment', {
        freelancer: props.freelancerId,
        contract: contractName
      });
    };
    
    const downloadInvoice = async (paymentName) => {
      window.open(`/api/method/frappe.utils.print_format.download_pdf?doctype=Freelancer%20Payment&name=${paymentName}&format=Freelancer%20Payment%20Invoice`);
    };
    
    onMounted(() => {
      fetchFreelancer();
      fetchContracts();
      fetchPayments();
    });
    
    return {
      freelancer,
      contracts,
      payments,
      activeTab,
      tabs,
      companyCountry,
      statusClass,
      gdprDescription,
      taxCertDescription,
      vatStatus,
      vatDescription,
      hasActiveContract,
      contractDescription,
      totalEarnings,
      pendingPayments,
      taxWithheld,
      formatCurrency,
      formatDate,
      createPayment,
      createContract,
      viewContract,
      viewPayment,
      createPaymentFromContract,
      downloadInvoice
    };
  }
};
</script>

<style scoped>
.freelancer-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-content h1 {
  margin: 0;
  font-size: 28px;
}

.status-badge {
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.status-active {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.status-inactive {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.status-onboarding {
  background: rgba(255, 193, 7, 0.1);
  color: #ffc107;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.compliance-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.dashboard-tabs {
  background: var(--card-bg);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.tab-headers {
  display: flex;
  background: var(--bg-color);
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  padding: 15px 25px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.tab-btn.active {
  color: var(--primary);
  border-bottom: 2px solid var(--primary);
  background: var(--card-bg);
}

.tab-count {
  background: var(--primary);
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.tab-content {
  padding: 20px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.summary-card {
  background: var(--bg-color);
  padding: 20px;
  border-radius: 10px;
}

.summary-card.full-width {
  grid-column: 1 / -1;
}

.summary-card h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: var(--text-muted);
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.stat {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: var(--primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.rate-info {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.rate-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.rate-item:last-child {
  border-bottom: none;
}

.rate-label {
  color: var(--text-muted);
}

.rate-value {
  font-weight: bold;
}

.btn {
  padding: 10px 20px;
  border-radius: 5px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-secondary {
  background: var(--bg-color);
  color: var(--text-color);
  border: 1px solid var(--border-color);
}

.btn:hover {
  opacity: 0.9;
}
</style>
