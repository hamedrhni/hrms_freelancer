<template>
  <div class="payment-list">
    <div class="list-header">
      <h4>Payments</h4>
      <div class="header-controls">
        <select v-model="statusFilter" class="filter-select">
          <option value="">All Statuses</option>
          <option value="Draft">Draft</option>
          <option value="Pending Approval">Pending Approval</option>
          <option value="Approved">Approved</option>
          <option value="Paid">Paid</option>
          <option value="Rejected">Rejected</option>
        </select>
        <input 
          v-model="search" 
          type="text" 
          placeholder="Search..."
          class="search-input"
        />
      </div>
    </div>
    
    <div v-if="filteredPayments.length === 0" class="empty-state">
      <i class="fa fa-money"></i>
      <p>No payments found</p>
    </div>
    
    <table v-else class="payments-table">
      <thead>
        <tr>
          <th>Invoice #</th>
          <th>Date</th>
          <th>Description</th>
          <th>Base Amount</th>
          <th>VAT</th>
          <th>Withholding</th>
          <th>Net Payable</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="payment in filteredPayments" :key="payment.name">
          <td class="invoice-number">{{ payment.name }}</td>
          <td>{{ formatDate(payment.invoice_date || payment.creation) }}</td>
          <td>
            {{ payment.description || 'Services' }}
            <span v-if="payment.contract" class="contract-ref">
              <i class="fa fa-file-text-o"></i> {{ payment.contract }}
            </span>
          </td>
          <td class="amount">{{ formatCurrency(payment.base_amount) }}</td>
          <td class="amount">
            <span v-if="payment.apply_reverse_charge" class="reverse-charge-badge">RC</span>
            <span v-else>{{ formatCurrency(payment.vat_amount) }}</span>
          </td>
          <td class="amount negative">
            {{ payment.withholding_tax_amount ? '-' + formatCurrency(payment.withholding_tax_amount) : '—' }}
          </td>
          <td class="amount total">{{ formatCurrency(payment.net_payable) }}</td>
          <td>
            <span class="status-badge" :class="'status-' + payment.status?.toLowerCase().replace(' ', '-')">
              {{ payment.status }}
            </span>
          </td>
          <td class="actions">
            <button class="btn-icon" @click="$emit('view', payment.name)" title="View">
              <i class="fa fa-eye"></i>
            </button>
            <button 
              v-if="payment.status === 'Paid'"
              class="btn-icon" 
              @click="$emit('download-invoice', payment.name)"
              title="Download Invoice"
            >
              <i class="fa fa-download"></i>
            </button>
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="3"><strong>Totals</strong></td>
          <td class="amount"><strong>{{ formatCurrency(totals.base) }}</strong></td>
          <td class="amount"><strong>{{ formatCurrency(totals.vat) }}</strong></td>
          <td class="amount negative"><strong>{{ formatCurrency(totals.withholding) }}</strong></td>
          <td class="amount total"><strong>{{ formatCurrency(totals.net) }}</strong></td>
          <td colspan="2"></td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<script>
import { ref, computed } from 'vue';

export default {
  name: 'PaymentList',
  
  props: {
    payments: {
      type: Array,
      default: () => []
    },
    currency: {
      type: String,
      default: 'EUR'
    }
  },
  
  emits: ['view', 'download-invoice'],
  
  setup(props) {
    const search = ref('');
    const statusFilter = ref('');
    
    const filteredPayments = computed(() => {
      let result = props.payments;
      
      if (statusFilter.value) {
        result = result.filter(p => p.status === statusFilter.value);
      }
      
      if (search.value) {
        const searchLower = search.value.toLowerCase();
        result = result.filter(p => 
          p.name?.toLowerCase().includes(searchLower) ||
          p.description?.toLowerCase().includes(searchLower) ||
          p.contract?.toLowerCase().includes(searchLower)
        );
      }
      
      return result;
    });
    
    const totals = computed(() => {
      return filteredPayments.value.reduce((acc, p) => ({
        base: acc.base + (p.base_amount || 0),
        vat: acc.vat + (p.vat_amount || 0),
        withholding: acc.withholding + (p.withholding_tax_amount || 0),
        net: acc.net + (p.net_payable || 0)
      }), { base: 0, vat: 0, withholding: 0, net: 0 });
    });
    
    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      return new Date(dateStr).toLocaleDateString('en-EU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    };
    
    const formatCurrency = (amount) => {
      if (!amount && amount !== 0) return '—';
      return new Intl.NumberFormat('en-EU', {
        style: 'currency',
        currency: props.currency
      }).format(amount);
    };
    
    return {
      search,
      statusFilter,
      filteredPayments,
      totals,
      formatDate,
      formatCurrency
    };
  }
};
</script>

<style scoped>
.payment-list {
  padding: 10px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.list-header h4 {
  margin: 0;
}

.header-controls {
  display: flex;
  gap: 10px;
}

.filter-select {
  padding: 8px 15px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  background: white;
}

.search-input {
  padding: 8px 15px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  width: 200px;
}

.empty-state {
  text-align: center;
  padding: 50px;
  color: var(--text-muted);
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 15px;
}

.payments-table {
  width: 100%;
  border-collapse: collapse;
}

.payments-table th {
  text-align: left;
  padding: 12px;
  background: var(--bg-color);
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-muted);
  border-bottom: 2px solid var(--border-color);
}

.payments-table td {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  font-size: 14px;
}

.payments-table tbody tr:hover {
  background: var(--bg-color);
}

.invoice-number {
  font-weight: 500;
  font-family: monospace;
}

.contract-ref {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
}

.amount {
  text-align: right;
  font-family: monospace;
}

.amount.negative {
  color: #dc3545;
}

.amount.total {
  font-weight: bold;
}

.reverse-charge-badge {
  background: rgba(23, 162, 184, 0.1);
  color: #17a2b8;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 15px;
  font-size: 12px;
  white-space: nowrap;
}

.status-draft {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.status-pending-approval {
  background: rgba(255, 193, 7, 0.1);
  color: #ffc107;
}

.status-approved {
  background: rgba(0, 102, 204, 0.1);
  color: #0066cc;
}

.status-paid {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.status-rejected {
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
}

.actions {
  white-space: nowrap;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px 10px;
  color: var(--text-muted);
  font-size: 14px;
}

.btn-icon:hover {
  color: var(--primary);
}

.payments-table tfoot td {
  background: var(--bg-color);
  border-top: 2px solid var(--border-color);
}
</style>
