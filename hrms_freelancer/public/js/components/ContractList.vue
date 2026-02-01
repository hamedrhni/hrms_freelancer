<template>
  <div class="contract-list">
    <div class="list-header">
      <h4>Contracts</h4>
      <input 
        v-model="search" 
        type="text" 
        placeholder="Search contracts..."
        class="search-input"
      />
    </div>
    
    <div v-if="filteredContracts.length === 0" class="empty-state">
      <i class="fa fa-file-text-o"></i>
      <p>No contracts found</p>
    </div>
    
    <div v-else class="contracts-grid">
      <div 
        v-for="contract in filteredContracts" 
        :key="contract.name"
        class="contract-card"
        :class="'status-' + contract.status?.toLowerCase().replace(' ', '-')"
      >
        <div class="contract-header">
          <span class="contract-type">{{ contract.contract_type }}</span>
          <span class="contract-status">{{ contract.status }}</span>
        </div>
        
        <h5 class="contract-title">{{ contract.title || contract.name }}</h5>
        
        <div class="contract-details">
          <div class="detail">
            <i class="fa fa-calendar"></i>
            {{ formatDate(contract.start_date) }} - {{ formatDate(contract.end_date) || 'Ongoing' }}
          </div>
          <div class="detail">
            <i class="fa fa-money"></i>
            {{ formatCurrency(contract.total_contract_value) }}
          </div>
        </div>
        
        <div class="contract-progress" v-if="contract.milestones?.length">
          <div class="progress-bar">
            <div 
              class="progress-fill"
              :style="{ width: getProgress(contract) + '%' }"
            ></div>
          </div>
          <span class="progress-text">
            {{ getCompletedMilestones(contract) }}/{{ contract.milestones.length }} milestones
          </span>
        </div>
        
        <div class="contract-actions">
          <button class="btn-link" @click="$emit('view', contract.name)">
            <i class="fa fa-eye"></i> View
          </button>
          <button 
            v-if="contract.status === 'Active'"
            class="btn-link primary" 
            @click="$emit('create-payment', contract.name)"
          >
            <i class="fa fa-plus"></i> Create Payment
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue';

export default {
  name: 'ContractList',
  
  props: {
    contracts: {
      type: Array,
      default: () => []
    },
    currency: {
      type: String,
      default: 'EUR'
    }
  },
  
  emits: ['view', 'create-payment'],
  
  setup(props) {
    const search = ref('');
    
    const filteredContracts = computed(() => {
      if (!search.value) return props.contracts;
      const searchLower = search.value.toLowerCase();
      return props.contracts.filter(c => 
        c.name?.toLowerCase().includes(searchLower) ||
        c.title?.toLowerCase().includes(searchLower) ||
        c.contract_type?.toLowerCase().includes(searchLower)
      );
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
      if (!amount) return '—';
      return new Intl.NumberFormat('en-EU', {
        style: 'currency',
        currency: props.currency
      }).format(amount);
    };
    
    const getProgress = (contract) => {
      if (!contract.milestones?.length) return 0;
      const completed = contract.milestones.filter(m => 
        m.status === 'Completed' || m.status === 'Approved'
      ).length;
      return Math.round((completed / contract.milestones.length) * 100);
    };
    
    const getCompletedMilestones = (contract) => {
      if (!contract.milestones?.length) return 0;
      return contract.milestones.filter(m => 
        m.status === 'Completed' || m.status === 'Approved'
      ).length;
    };
    
    return {
      search,
      filteredContracts,
      formatDate,
      formatCurrency,
      getProgress,
      getCompletedMilestones
    };
  }
};
</script>

<style scoped>
.contract-list {
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

.search-input {
  padding: 8px 15px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  width: 250px;
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

.contracts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.contract-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  transition: box-shadow 0.2s;
}

.contract-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.contract-card.status-active {
  border-left: 4px solid #28a745;
}

.contract-card.status-draft {
  border-left: 4px solid #6c757d;
}

.contract-card.status-expired {
  border-left: 4px solid #dc3545;
}

.contract-card.status-terminated {
  border-left: 4px solid #ffc107;
}

.contract-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.contract-type {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
}

.contract-status {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 10px;
  background: var(--bg-color);
}

.status-active .contract-status {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.contract-title {
  margin: 0 0 15px 0;
  font-size: 16px;
}

.contract-details {
  margin-bottom: 15px;
}

.detail {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 5px;
}

.contract-progress {
  margin-bottom: 15px;
}

.progress-bar {
  height: 6px;
  background: var(--bg-color);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 5px;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: var(--text-muted);
}

.contract-actions {
  display: flex;
  gap: 15px;
  padding-top: 15px;
  border-top: 1px solid var(--border-color);
}

.btn-link {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.btn-link:hover {
  color: var(--primary);
}

.btn-link.primary {
  color: var(--primary);
}
</style>
