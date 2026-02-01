<template>
  <div class="tax-calculator">
    <h3>Tax Calculator</h3>
    <p class="description">Calculate taxes for payments based on your residency and the company's location.</p>
    
    <div class="calculator-form">
      <div class="form-row">
        <div class="form-group">
          <label>Gross Amount</label>
          <div class="input-group">
            <span class="currency-symbol">{{ currencySymbol }}</span>
            <input 
              v-model.number="grossAmount" 
              type="number" 
              step="0.01"
              min="0"
              placeholder="1000.00"
              @input="calculate"
            />
          </div>
        </div>
        
        <div class="form-group">
          <label>Service Type</label>
          <select v-model="serviceType" @change="calculate">
            <option value="professional">Professional Services</option>
            <option value="consulting">Consulting</option>
            <option value="development">Software Development</option>
            <option value="design">Design</option>
            <option value="technical">Technical Services</option>
          </select>
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>Freelancer Country</label>
          <select v-model="fromCountry" @change="calculate">
            <option v-for="country in countries" :key="country" :value="country">
              {{ country }}
            </option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Company Country</label>
          <select v-model="toCountry" @change="calculate">
            <option v-for="country in countries" :key="country" :value="country">
              {{ country }}
            </option>
          </select>
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group checkbox-group">
          <label>
            <input type="checkbox" v-model="hasTaxCertificate" @change="calculate" />
            Has Tax Residency Certificate
          </label>
        </div>
        
        <div class="form-group checkbox-group">
          <label>
            <input type="checkbox" v-model="isB2B" @change="calculate" />
            B2B Transaction
          </label>
        </div>
      </div>
    </div>
    
    <!-- Results -->
    <div v-if="result" class="calculation-results">
      <h4>Tax Breakdown</h4>
      
      <!-- Visual Breakdown -->
      <div class="breakdown-visual">
        <div class="breakdown-bar">
          <div 
            class="bar-segment gross"
            :style="{ width: '100%' }"
          >
            <span class="segment-label">Gross: {{ formatCurrency(result.gross_amount) }}</span>
          </div>
        </div>
        
        <div class="breakdown-details">
          <!-- VAT -->
          <div class="detail-row" :class="{ 'reverse-charge': result.vat?.reverse_charge }">
            <div class="detail-icon">
              <i :class="result.vat?.reverse_charge ? 'fa fa-exchange' : 'fa fa-percent'"></i>
            </div>
            <div class="detail-info">
              <span class="detail-label">VAT ({{ result.vat?.rate || 0 }}%)</span>
              <span class="detail-note" v-if="result.vat?.reverse_charge">
                Reverse Charge - Recipient accounts for VAT
              </span>
            </div>
            <div class="detail-value">
              {{ result.vat?.reverse_charge ? 'RC' : formatCurrency(result.vat?.amount) }}
            </div>
          </div>
          
          <!-- Withholding -->
          <div class="detail-row" :class="{ 'has-withholding': result.withholding_tax?.rate > 0 }">
            <div class="detail-icon">
              <i class="fa fa-minus-circle"></i>
            </div>
            <div class="detail-info">
              <span class="detail-label">Withholding Tax ({{ result.withholding_tax?.rate || 0 }}%)</span>
              <span class="detail-note" v-if="result.withholding_tax?.treaty_applied">
                Treaty rate applied
              </span>
            </div>
            <div class="detail-value negative">
              -{{ formatCurrency(result.withholding_tax?.amount) }}
            </div>
          </div>
        </div>
      </div>
      
      <!-- Net Payable -->
      <div class="net-payable">
        <span class="label">Net Payable</span>
        <span class="value">{{ formatCurrency(result.net_payable) }}</span>
      </div>
      
      <!-- Compliance Notes -->
      <div v-if="result.compliance_notes?.length" class="compliance-notes">
        <h5><i class="fa fa-info-circle"></i> Compliance Notes</h5>
        <ul>
          <li v-for="(note, index) in result.compliance_notes" :key="index">
            {{ note }}
          </li>
        </ul>
      </div>
      
      <!-- Country Info -->
      <div class="country-info">
        <div class="info-badge" :class="{ 'eu': result.is_eu_freelancer }">
          <i :class="result.is_eu_freelancer ? 'fa fa-flag' : 'fa fa-globe'"></i>
          {{ result.is_eu_freelancer ? 'EU Resident' : 'Non-EU Resident' }}
        </div>
        <div class="info-badge" v-if="result.is_cross_border">
          <i class="fa fa-exchange"></i>
          Cross-Border Transaction
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';

export default {
  name: 'TaxCalculator',
  
  props: {
    freelancerCountry: {
      type: String,
      default: 'Netherlands'
    },
    companyCountry: {
      type: String,
      default: 'Netherlands'
    },
    isEu: {
      type: Boolean,
      default: true
    },
    vatRegistered: {
      type: Boolean,
      default: false
    },
    currency: {
      type: String,
      default: 'EUR'
    }
  },
  
  setup(props) {
    const grossAmount = ref(1000);
    const serviceType = ref('professional');
    const fromCountry = ref(props.freelancerCountry);
    const toCountry = ref(props.companyCountry);
    const hasTaxCertificate = ref(false);
    const isB2B = ref(true);
    const result = ref(null);
    
    const countries = [
      'Netherlands', 'Germany', 'France', 'Belgium', 'Spain', 'Italy',
      'Austria', 'Poland', 'Ireland', 'Portugal', 'Sweden', 'Denmark',
      'Finland', 'Greece', 'Czech Republic', 'Hungary', 'Romania',
      'Luxembourg', 'United Kingdom', 'Switzerland', 'United States',
      'India', 'Canada', 'Australia'
    ];
    
    const euCountries = [
      'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
      'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
      'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands',
      'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden'
    ];
    
    const currencySymbol = computed(() => {
      const symbols = { EUR: '€', USD: '$', GBP: '£', CHF: 'CHF' };
      return symbols[props.currency] || props.currency;
    });
    
    const formatCurrency = (amount) => {
      if (amount === undefined || amount === null) return '€0.00';
      return new Intl.NumberFormat('en-EU', {
        style: 'currency',
        currency: props.currency || 'EUR'
      }).format(amount);
    };
    
    const calculate = async () => {
      if (!grossAmount.value || grossAmount.value <= 0) {
        result.value = null;
        return;
      }
      
      // Client-side calculation for immediate feedback
      const isFreelancerEU = euCountries.includes(fromCountry.value);
      const isCompanyEU = euCountries.includes(toCountry.value);
      const isCrossBorder = fromCountry.value !== toCountry.value;
      
      // Calculate VAT
      let vatRate = 0;
      let vatAmount = 0;
      let reverseCharge = false;
      
      if (isCrossBorder && isFreelancerEU && isCompanyEU && isB2B.value) {
        // EU B2B reverse charge
        reverseCharge = true;
      } else if (!isFreelancerEU && isCompanyEU && isB2B.value) {
        // Non-EU to EU reverse charge
        reverseCharge = true;
      } else if (isFreelancerEU && !isCompanyEU) {
        // Export - 0% VAT
        vatRate = 0;
      } else {
        // Standard VAT
        const vatRates = {
          'Netherlands': 21, 'Germany': 19, 'France': 20, 'Belgium': 21,
          'Spain': 21, 'Italy': 22, 'Austria': 20, 'Poland': 23,
          'Ireland': 23, 'United Kingdom': 20
        };
        vatRate = vatRates[fromCountry.value] || 21;
        vatAmount = grossAmount.value * vatRate / 100;
      }
      
      // Calculate withholding
      let withholdingRate = 0;
      let withholdingAmount = 0;
      let treatyApplied = false;
      
      if (isCrossBorder && !(isFreelancerEU && isCompanyEU)) {
        // Check for treaty (simplified)
        const treaties = {
          'Netherlands-United States': 0,
          'Germany-United States': 0,
          'Netherlands-India': 10,
          'Germany-India': 10,
          'Netherlands-United Kingdom': 0,
        };
        
        const treatyKey1 = `${fromCountry.value}-${toCountry.value}`;
        const treatyKey2 = `${toCountry.value}-${fromCountry.value}`;
        
        if (treaties[treatyKey1] !== undefined) {
          withholdingRate = treaties[treatyKey1];
          treatyApplied = true;
        } else if (treaties[treatyKey2] !== undefined) {
          withholdingRate = treaties[treatyKey2];
          treatyApplied = true;
        } else if (!isFreelancerEU) {
          // Default withholding for non-treaty countries
          withholdingRate = hasTaxCertificate.value ? 15 : 30;
        }
        
        withholdingAmount = grossAmount.value * withholdingRate / 100;
      }
      
      // Calculate net
      let netPayable = grossAmount.value;
      if (!reverseCharge) {
        netPayable += vatAmount;
      }
      netPayable -= withholdingAmount;
      
      // Compliance notes
      const complianceNotes = [];
      if (reverseCharge) {
        complianceNotes.push('REVERSE CHARGE: Under EU VAT Directive Article 196, the recipient is liable to account for VAT.');
      }
      if (withholdingRate > 0) {
        complianceNotes.push(`WITHHOLDING TAX: ${withholdingRate}% will be withheld and should be reported to tax authorities.`);
        if (treatyApplied) {
          complianceNotes.push('TAX TREATY: Reduced rate applied. Ensure tax residency certificate is on file.');
        }
      }
      if (grossAmount.value > 10000) {
        complianceNotes.push('LARGE PAYMENT: Amounts over €10,000 may have additional reporting requirements.');
      }
      
      result.value = {
        gross_amount: grossAmount.value,
        freelancer_country: fromCountry.value,
        company_country: toCountry.value,
        is_eu_freelancer: isFreelancerEU,
        is_cross_border: isCrossBorder,
        vat: {
          rate: vatRate,
          amount: vatAmount,
          reverse_charge: reverseCharge
        },
        withholding_tax: {
          rate: withholdingRate,
          amount: withholdingAmount,
          treaty_applied: treatyApplied
        },
        net_payable: netPayable,
        compliance_notes: complianceNotes
      };
    };
    
    // Watch for prop changes
    watch(() => props.freelancerCountry, (newVal) => {
      fromCountry.value = newVal;
      calculate();
    });
    
    watch(() => props.companyCountry, (newVal) => {
      toCountry.value = newVal;
      calculate();
    });
    
    onMounted(() => {
      calculate();
    });
    
    return {
      grossAmount,
      serviceType,
      fromCountry,
      toCountry,
      hasTaxCertificate,
      isB2B,
      result,
      countries,
      currencySymbol,
      formatCurrency,
      calculate
    };
  }
};
</script>

<style scoped>
.tax-calculator {
  padding: 20px;
  background: var(--card-bg);
  border-radius: 10px;
}

.tax-calculator h3 {
  margin: 0 0 5px 0;
}

.description {
  color: var(--text-muted);
  margin-bottom: 20px;
}

.calculator-form {
  background: var(--bg-color);
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 5px;
  font-weight: 500;
  font-size: 14px;
}

.input-group {
  display: flex;
  align-items: center;
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  overflow: hidden;
}

.currency-symbol {
  padding: 10px 15px;
  background: var(--bg-color);
  color: var(--text-muted);
  font-weight: bold;
}

.input-group input {
  flex: 1;
  padding: 10px;
  border: none;
  font-size: 16px;
}

.form-group select {
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  background: white;
  font-size: 14px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
}

.calculation-results {
  background: var(--bg-color);
  padding: 20px;
  border-radius: 8px;
}

.calculation-results h4 {
  margin: 0 0 20px 0;
}

.breakdown-visual {
  margin-bottom: 20px;
}

.breakdown-bar {
  height: 40px;
  background: var(--primary);
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  margin-bottom: 15px;
}

.breakdown-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-row {
  display: flex;
  align-items: center;
  padding: 15px;
  background: white;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.detail-row.reverse-charge {
  border-color: #17a2b8;
  background: rgba(23, 162, 184, 0.05);
}

.detail-row.has-withholding {
  border-color: #dc3545;
  background: rgba(220, 53, 69, 0.05);
}

.detail-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.detail-icon i {
  font-size: 16px;
}

.detail-info {
  flex: 1;
}

.detail-label {
  display: block;
  font-weight: 500;
}

.detail-note {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
}

.detail-value {
  font-weight: bold;
  font-size: 18px;
}

.detail-value.negative {
  color: #dc3545;
}

.net-payable {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: var(--primary);
  color: white;
  border-radius: 8px;
  margin: 20px 0;
}

.net-payable .label {
  font-size: 18px;
  font-weight: 500;
}

.net-payable .value {
  font-size: 28px;
  font-weight: bold;
}

.compliance-notes {
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 15px;
  margin-top: 15px;
}

.compliance-notes h5 {
  margin: 0 0 10px 0;
  color: #856404;
}

.compliance-notes ul {
  margin: 0;
  padding-left: 20px;
}

.compliance-notes li {
  margin-bottom: 5px;
  font-size: 13px;
  color: #856404;
}

.country-info {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.info-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 15px;
  background: var(--bg-color);
  border-radius: 20px;
  font-size: 13px;
}

.info-badge.eu {
  background: rgba(0, 102, 204, 0.1);
  color: #0066cc;
}

.info-badge i {
  font-size: 14px;
}
</style>
