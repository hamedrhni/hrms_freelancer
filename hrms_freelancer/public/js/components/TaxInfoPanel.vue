<template>
  <div class="tax-info-panel">
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">Tax Residency</span>
        <span class="info-value">
          <i :class="isEu ? 'fa fa-flag text-primary' : 'fa fa-globe'"></i>
          {{ country }}
        </span>
      </div>
      
      <div class="info-item">
        <span class="info-label">Tax Status</span>
        <span class="info-value">
          <span class="badge" :class="isEu ? 'badge-eu' : 'badge-non-eu'">
            {{ isEu ? 'EU Resident' : 'Non-EU Resident' }}
          </span>
        </span>
      </div>
      
      <div class="info-item">
        <span class="info-label">VAT Status</span>
        <span class="info-value">
          <span class="badge" :class="vatRegistered ? 'badge-success' : 'badge-muted'">
            {{ vatRegistered ? 'VAT Registered' : 'Not Registered' }}
          </span>
        </span>
      </div>
      
      <div class="info-item" v-if="vatNumber">
        <span class="info-label">VAT Number</span>
        <span class="info-value">{{ vatNumber }}</span>
      </div>
    </div>
    
    <div class="tax-implications">
      <h5>Tax Implications</h5>
      <ul>
        <li v-if="isEu">
          <i class="fa fa-check-circle text-success"></i>
          Eligible for EU reverse charge on B2B services
        </li>
        <li v-if="isEu">
          <i class="fa fa-check-circle text-success"></i>
          No withholding tax on EU intra-Community payments
        </li>
        <li v-if="!isEu">
          <i class="fa fa-exclamation-circle text-warning"></i>
          May be subject to withholding tax (check treaty)
        </li>
        <li v-if="vatRegistered">
          <i class="fa fa-info-circle text-info"></i>
          Must charge VAT on applicable services
        </li>
        <li v-if="!vatRegistered && isEu">
          <i class="fa fa-exclamation-circle text-warning"></i>
          Consider VAT registration if turnover exceeds threshold
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TaxInfoPanel',
  
  props: {
    country: {
      type: String,
      default: ''
    },
    isEu: {
      type: Boolean,
      default: false
    },
    vatRegistered: {
      type: Boolean,
      default: false
    },
    vatNumber: {
      type: String,
      default: ''
    }
  }
};
</script>

<style scoped>
.tax-info-panel {
  padding: 15px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 5px;
}

.info-value {
  font-size: 16px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  padding: 4px 12px;
  border-radius: 15px;
  font-size: 12px;
  font-weight: 500;
}

.badge-eu {
  background: rgba(0, 102, 204, 0.1);
  color: #0066cc;
}

.badge-non-eu {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.badge-success {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.badge-muted {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.tax-implications {
  background: rgba(0, 0, 0, 0.02);
  padding: 15px;
  border-radius: 8px;
}

.tax-implications h5 {
  margin: 0 0 10px 0;
  font-size: 14px;
}

.tax-implications ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tax-implications li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border-color);
}

.tax-implications li:last-child {
  border-bottom: none;
}

.text-success {
  color: #28a745;
}

.text-warning {
  color: #ffc107;
}

.text-info {
  color: #17a2b8;
}

.text-primary {
  color: #0066cc;
}
</style>
