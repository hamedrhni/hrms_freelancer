<template>
  <div class="compliance-card" :class="statusClass">
    <div class="card-icon">
      <i :class="['fa', icon]"></i>
    </div>
    <div class="card-content">
      <h4>{{ title }}</h4>
      <p>{{ description }}</p>
    </div>
    <div class="card-status">
      <i :class="statusIcon"></i>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'ComplianceCard',
  
  props: {
    title: {
      type: String,
      required: true
    },
    status: {
      type: String,
      default: 'pending',
      validator: (value) => ['compliant', 'non-compliant', 'pending', 'na'].includes(value)
    },
    description: {
      type: String,
      default: ''
    },
    icon: {
      type: String,
      default: 'fa-check'
    }
  },
  
  setup(props) {
    const statusClass = computed(() => `status-${props.status}`);
    
    const statusIcon = computed(() => {
      const icons = {
        'compliant': 'fa fa-check-circle',
        'non-compliant': 'fa fa-exclamation-circle',
        'pending': 'fa fa-clock-o',
        'na': 'fa fa-minus-circle'
      };
      return icons[props.status];
    });
    
    return {
      statusClass,
      statusIcon
    };
  }
};
</script>

<style scoped>
.compliance-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: var(--card-bg);
  border-radius: 10px;
  border-left: 4px solid transparent;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s, box-shadow 0.2s;
}

.compliance-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.compliance-card.status-compliant {
  border-left-color: #28a745;
}

.compliance-card.status-non-compliant {
  border-left-color: #dc3545;
}

.compliance-card.status-pending {
  border-left-color: #ffc107;
}

.compliance-card.status-na {
  border-left-color: #6c757d;
}

.card-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  font-size: 20px;
}

.status-compliant .card-icon {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.status-non-compliant .card-icon {
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
}

.status-pending .card-icon {
  background: rgba(255, 193, 7, 0.1);
  color: #ffc107;
}

.status-na .card-icon {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.card-content {
  flex: 1;
}

.card-content h4 {
  margin: 0 0 5px 0;
  font-size: 14px;
  font-weight: 600;
}

.card-content p {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}

.card-status {
  font-size: 24px;
}

.status-compliant .card-status {
  color: #28a745;
}

.status-non-compliant .card-status {
  color: #dc3545;
}

.status-pending .card-status {
  color: #ffc107;
}

.status-na .card-status {
  color: #6c757d;
}
</style>
