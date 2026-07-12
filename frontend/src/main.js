import './style.css';

const API_BASE_URL = 'http://localhost:8000';
let activeModule = 'sales';
let activeFile = null;
let primaryChart = null;
let secondaryChart = null;

// DOM Elements
const backendStatus = document.getElementById('backend-status');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const loadingPanel = document.getElementById('loading-panel');
const errorPanel = document.getElementById('error-panel');
const errorTitle = document.getElementById('error-title');
const errorMessage = document.getElementById('error-message');
const errorDismiss = document.getElementById('error-dismiss');
const resultsPanel = document.getElementById('results-panel');
const moduleBtns = document.querySelectorAll('.module-btn');
const uploadTrigger = document.querySelector('.upload-trigger');
const sampleLinksGrid = document.getElementById('sample-links-grid');

// Sample Data Configuration
const SAMPLES_DATA = {
  sales: [
    { name: 'sales_format1.csv', type: 'CSV', url: '/samples/sales/sales_format1.csv' },
    { name: 'sales_format2.xlsx', type: 'XLSX', url: '/samples/sales/sales_format2.xlsx' },
    { name: 'sales_format3.csv', type: 'CSV (Dirty)', url: '/samples/sales/sales_format3.csv' }
  ],
  inventory: [
    { name: 'inventory_format1.csv', type: 'CSV', url: '/samples/inventory/inventory_format1.csv' },
    { name: 'inventory_format2.xlsx', type: 'XLSX', url: '/samples/inventory/inventory_format2.xlsx' },
    { name: 'inventory_format3.csv', type: 'CSV', url: '/samples/inventory/inventory_format3.csv' }
  ],
  purchases: [
    { name: 'purchases_format1.csv', type: 'CSV', url: '/samples/purchases/purchases_format1.csv' },
    { name: 'purchases_format2.xlsx', type: 'XLSX', url: '/samples/purchases/purchases_format2.xlsx' },
    { name: 'purchases_format3.csv', type: 'CSV', url: '/samples/purchases/purchases_format3.csv' }
  ]
};

function updateSampleDownloads() {
  if (!sampleLinksGrid) return;
  const items = SAMPLES_DATA[activeModule] || [];
  const cacheBust = Date.now();
  sampleLinksGrid.innerHTML = items.map(item => {
    const badgeClass = item.type.includes('XLSX') ? 'sample-type-xlsx' : 'sample-type-csv';
    return `
      <a href="${item.url}?v=${cacheBust}" download="${item.name}" class="sample-download-link">
        <span>${escapeHtml(item.name)}</span>
        <span class="sample-type-badge ${badgeClass}">${item.type}</span>
      </a>
    `;
  }).join('');
}


// 1. Backend Health Check
function checkBackendHealth() {
  const dot = backendStatus.querySelector('.status-dot');
  const label = backendStatus.querySelector('.status-label');
  
  dot.className = 'status-dot checking';
  label.textContent = 'Checking...';

  fetch(`${API_BASE_URL}/health`)
    .then(res => {
      if (res.ok) {
        dot.className = 'status-dot online';
        label.textContent = 'Backend Online';
      } else {
        throw new Error('Health check returned non-200');
      }
    })
    .catch(() => {
      dot.className = 'status-dot offline';
      label.textContent = 'Backend Offline';
    });
}

// Check on load and set up polling every 10 seconds
checkBackendHealth();
updateSampleDownloads();
setInterval(checkBackendHealth, 10000);

// 2. Module Selector Tabs
moduleBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    moduleBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeModule = btn.dataset.module;
    resetUI();
    updateSampleDownloads();
  });
});

// 3. File Upload Trigger and Drag/Drop Handlers
uploadTrigger.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFile(e.target.files[0]);
  }
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    handleFile(e.dataTransfer.files[0]);
  }
});

dropZone.addEventListener('click', () => {
  fileInput.click();
});

errorDismiss.addEventListener('click', () => {
  resetUI();
});

function resetUI() {
  errorPanel.style.display = 'none';
  resultsPanel.style.display = 'none';
  loadingPanel.style.display = 'none';
  dropZone.style.display = 'flex';
  activeFile = null;
  fileInput.value = '';
}

// 4. Ingestion and Validation
function handleFile(file) {
  // Extension check
  const ext = file.name.split('.').pop().toLowerCase();
  if (ext !== 'csv' && ext !== 'xlsx') {
    showError('UnsupportedFormatError', 'Invalid file type. Only CSV and XLSX exports are supported.');
    return;
  }

  // Size check
  const sizeMB = file.size / (1024 * 1024);
  if (sizeMB > 100) {
    showError('FileTooLargeError', `File size (${sizeMB.toFixed(2)}MB) exceeds the 100MB limit.`);
    return;
  }

  activeFile = file;
  uploadAndProcess();
}

function showError(title, message) {
  dropZone.style.display = 'none';
  loadingPanel.style.display = 'none';
  resultsPanel.style.display = 'none';
  
  errorPanel.style.display = 'flex';
  errorTitle.textContent = title;
  errorMessage.textContent = message;
}

// 5. Ingestion Request
function uploadAndProcess() {
  dropZone.style.display = 'none';
  errorPanel.style.display = 'none';
  resultsPanel.style.display = 'none';
  
  loadingPanel.style.display = 'flex';
  const stateText = document.getElementById('loading-state-text');
  stateText.textContent = `Processing ${activeFile.name}...`;

  const formData = new FormData();
  formData.append('file', activeFile);

  fetch(`${API_BASE_URL}/analyze/${activeModule}`, {
    method: 'POST',
    body: formData
  })
    .then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw {
          error: data.error || 'ProcessingError',
          message: data.message || data.detail || 'An unknown error occurred during ETL execution.'
        };
      }
      return data;
    })
    .then((data) => {
      loadingPanel.style.display = 'none';
      renderResults(data);
    })
    .catch((err) => {
      loadingPanel.style.display = 'none';
      showError(err.error || 'Server Connection Failed', err.message || 'Could not connect to the backend server. Please verify it is running on port 8000.');
    });
}

// 6. Result Ingestion & Rendering
function renderResults(data) {
  resultsPanel.style.display = 'block';

  // Render Data Quality Panel
  const processed = data.data_quality.processed_rows;
  const uploaded = data.data_quality.uploaded_rows;
  const dropped = data.data_quality.dropped_rows;
  const duplicates = data.data_quality.duplicate_rows;
  
  document.getElementById('stat-uploaded').textContent = uploaded.toLocaleString();
  document.getElementById('stat-processed').textContent = processed.toLocaleString();
  document.getElementById('stat-dropped').textContent = dropped.toLocaleString();
  document.getElementById('stat-duplicates').textContent = duplicates.toLocaleString();

  const completeness = uploaded > 0 ? (processed / uploaded) * 100 : 0;
  const completenessBadge = document.getElementById('completeness-score');
  completenessBadge.textContent = `${completeness.toFixed(1)}% Completeness`;
  if (completeness > 95) {
    completenessBadge.style.color = 'var(--success)';
    completenessBadge.style.borderColor = 'rgba(16, 185, 129, 0.2)';
    completenessBadge.style.background = 'var(--success-glow)';
  } else if (completeness > 80) {
    completenessBadge.style.color = 'var(--warning)';
    completenessBadge.style.borderColor = 'rgba(245, 158, 11, 0.2)';
    completenessBadge.style.background = 'var(--warning-glow)';
  } else {
    completenessBadge.style.color = 'var(--danger)';
    completenessBadge.style.borderColor = 'rgba(239, 68, 68, 0.2)';
    completenessBadge.style.background = 'var(--danger-glow)';
  }

  // Warnings list
  const warningsList = document.getElementById('warnings-list');
  const warnings = data.data_quality.quality_metrics.warnings || [];
  if (warnings.length > 0) {
    warningsList.style.display = 'flex';
    warningsList.innerHTML = warnings.map(w => `<div class="warning-item">${w}</div>`).join('');
  } else {
    warningsList.style.display = 'none';
  }

  // Render Column Mapping
  const coverage = data.column_mapping.coverage * 100;
  const coverageBadge = document.getElementById('mapping-coverage');
  coverageBadge.textContent = `${coverage.toFixed(0)}% Mapped`;
  
  const mappingTbody = document.getElementById('mapping-tbody');
  const mappingEntries = Object.entries(data.column_mapping.mapping);
  
  if (mappingEntries.length > 0) {
    mappingTbody.innerHTML = mappingEntries.map(([source, target]) => {
      const conf = data.column_mapping.confidence[target] || 1.0;
      const confPct = (conf * 100).toFixed(0);
      let confClass = 'confidence-high';
      if (conf < 0.8) confClass = 'confidence-low';
      else if (conf < 0.9) confClass = 'confidence-medium';

      return `
        <tr>
          <td><code>${escapeHtml(source)}</code></td>
          <td><span class="coverage-badge">${escapeHtml(target)}</span></td>
          <td><span class="confidence-cell ${confClass}">${confPct}%</span></td>
        </tr>
      `;
    }).join('');
  } else {
    mappingTbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No columns mapped</td></tr>`;
  }

  // Render KPIs Grid
  const kpisGrid = document.getElementById('kpis-grid');
  kpisGrid.innerHTML = '';
  
  const kpis = data.kpis;
  const overview = kpis.overview || {};

  let kpiCardsHtml = '';
  if (activeModule === 'sales') {
    kpiCardsHtml += createKpiCard('Total Revenue', formatMoney(overview.total_revenue));
    kpiCardsHtml += createKpiCard('Total Invoices', (overview.invoice_count || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Unique Customers', (overview.customer_count || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Unique Products', (overview.product_count || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Avg Invoice Value', formatMoney(overview.avg_order_value));
    kpiCardsHtml += createKpiCard('Avg Items / Order', (overview.avg_items_per_order || 0).toFixed(1));
  } else if (activeModule === 'inventory') {
    kpiCardsHtml += createKpiCard('Total Products', (overview.total_products || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Total Stock Units', (overview.total_stock_units || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Total Warehouses', (overview.total_warehouses || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Total Categories', (overview.total_categories || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Out-of-Stock Items', (overview.out_of_stock_count || 0).toLocaleString(), overview.out_of_stock_count > 0 ? 'text-danger' : '');
    kpiCardsHtml += createKpiCard('Low-Stock Items', (overview.low_stock_count || 0).toLocaleString(), overview.low_stock_count > 0 ? 'text-warning' : '');
  } else if (activeModule === 'purchases') {
    kpiCardsHtml += createKpiCard('Total Spend', formatMoney(overview.total_purchase_cost));
    kpiCardsHtml += createKpiCard('Purchase Orders', (overview.purchase_order_count || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Unique Suppliers', (overview.supplier_count || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Products Purchased', (overview.products_purchased_count || 0).toLocaleString());
    kpiCardsHtml += createKpiCard('Avg Purchase Order', formatMoney(overview.avg_purchase_value));
    kpiCardsHtml += createKpiCard('Avg Items / PO', (overview.avg_items_per_purchase || 0).toFixed(1));
  }
  kpisGrid.innerHTML = kpiCardsHtml;

  // Render Charts
  renderModuleCharts(kpis);

  // Render Anomalies Table (Sales/Inventory only)
  const anomaliesSection = document.getElementById('anomalies-section');
  const anomaliesThead = document.getElementById('anomalies-thead');
  const anomaliesTbody = document.getElementById('anomalies-tbody');
  
  let anomaliesList = [];
  if (activeModule === 'sales' && kpis.anomalies && kpis.anomalies.high_value_orders) {
    anomaliesList = kpis.anomalies.high_value_orders;
    anomaliesThead.innerHTML = `
      <tr>
        <th>Invoice ID</th>
        <th>Customer</th>
        <th>Invoice Date</th>
        <th style="text-align: right;">Total Amount</th>
      </tr>
    `;
    anomaliesTbody.innerHTML = anomaliesList.map(item => `
      <tr>
        <td><code>${escapeHtml(item.invoice_id || 'N/A')}</code></td>
        <td>${escapeHtml(item.customer_name || 'N/A')}</td>
        <td>${item.invoice_date || 'N/A'}</td>
        <td style="text-align: right; font-weight: 600;" class="text-warning">${formatMoney(item.total_amount)}</td>
      </tr>
    `).join('');
  } else if (activeModule === 'inventory' && kpis.recommendations && kpis.recommendations.overstock) {
    anomaliesList = kpis.recommendations.overstock;
    anomaliesThead.innerHTML = `
      <tr>
        <th>Product ID</th>
        <th>Product Name</th>
        <th style="text-align: right;">Stock Quantity</th>
      </tr>
    `;
    anomaliesTbody.innerHTML = anomaliesList.map(item => `
      <tr>
        <td><code>${escapeHtml(item.product_id || 'N/A')}</code></td>
        <td>${escapeHtml(item.product_name || 'N/A')}</td>
        <td style="text-align: right; font-weight: 600;" class="text-warning">${(item.stock_quantity || 0).toLocaleString()}</td>
      </tr>
    `).join('');
  }

  if (anomaliesList.length > 0) {
    anomaliesSection.style.display = 'block';
  } else {
    anomaliesSection.style.display = 'none';
  }
}

// 7. Visual Charts Configuration
function renderModuleCharts(kpis) {
  if (primaryChart) primaryChart.destroy();
  if (secondaryChart) secondaryChart.destroy();

  const primaryCtx = document.getElementById('chart-primary').getContext('2d');
  const secondaryCtx = document.getElementById('chart-secondary').getContext('2d');

  const pTitle = document.getElementById('chart-primary-title');
  const sTitle = document.getElementById('chart-secondary-title');

  // Colors
  const blue = '#3b82f6';
  const purple = '#8b5cf6';
  const green = '#10b981';
  const yellow = '#f59e0b';
  const red = '#ef4444';

  if (activeModule === 'sales') {
    pTitle.textContent = 'Revenue Growth Trends by Month';
    sTitle.textContent = 'Customer Value Segmentation';

    // Sales charts: Monthly revenue
    const monthlyData = kpis.revenue_by_month || [];
    monthlyData.sort((a, b) => (a.year - b.year) || (a.month - b.month));
    const labels = monthlyData.map(d => `${d.year}-${String(d.month).padStart(2, '0')}`);
    const values = monthlyData.map(d => d.revenue);

    primaryChart = new Chart(primaryCtx, {
      type: 'line',
      data: {
        labels: labels.length > 0 ? labels : ['No Data'],
        datasets: [{
          label: 'Revenue',
          data: values.length > 0 ? values : [0],
          borderColor: blue,
          backgroundColor: 'rgba(59, 130, 246, 0.15)',
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointBackgroundColor: blue
        }]
      },
      options: getChartOptions('Total Revenue ($)')
    });

    // Customer segmentation pie chart
    const segment = kpis.customer_segmentation || { high_value: 0, medium_value: 0, low_value: 0 };
    secondaryChart = new Chart(secondaryCtx, {
      type: 'doughnut',
      data: {
        labels: ['High Value', 'Medium Value', 'Low Value'],
        datasets: [{
          data: [segment.high_value, segment.medium_value, segment.low_value],
          backgroundColor: [purple, blue, 'rgba(255, 255, 255, 0.1)'],
          borderColor: 'transparent'
        }]
      },
      options: getDoughnutOptions()
    });

  } else if (activeModule === 'inventory') {
    pTitle.textContent = 'Stock Quantity by Category';
    sTitle.textContent = 'Stock Quantity by Warehouse';

    const catData = kpis.stock_by_category || [];
    const catLabels = catData.map(d => d.category || 'Unknown');
    const catValues = catData.map(d => d.total_stock);

    primaryChart = new Chart(primaryCtx, {
      type: 'bar',
      data: {
        labels: catLabels.length > 0 ? catLabels : ['No Category'],
        datasets: [{
          label: 'Stock Quantity',
          data: catValues.length > 0 ? catValues : [0],
          backgroundColor: blue,
          borderRadius: 6
        }]
      },
      options: getChartOptions('Units')
    });

    const whData = kpis.stock_by_warehouse || [];
    const whLabels = whData.map(d => d.warehouse || 'Unknown');
    const whValues = whData.map(d => d.total_stock);

    secondaryChart = new Chart(secondaryCtx, {
      type: 'doughnut',
      data: {
        labels: whLabels.length > 0 ? whLabels : ['No Warehouse'],
        datasets: [{
          data: whValues.length > 0 ? whValues : [0],
          backgroundColor: [purple, blue, green, yellow, red],
          borderColor: 'transparent'
        }]
      },
      options: getDoughnutOptions()
    });

  } else if (activeModule === 'purchases') {
    pTitle.textContent = 'Monthly Purchase Spend';
    sTitle.textContent = 'Top Suppliers by Total Spend';

    const costData = kpis.cost_by_month || [];
    costData.sort((a, b) => (a.year - b.year) || (a.month - b.month));
    const labels = costData.map(d => `${d.year}-${String(d.month).padStart(2, '0')}`);
    const values = costData.map(d => d.total_cost);

    primaryChart = new Chart(primaryCtx, {
      type: 'bar',
      data: {
        labels: labels.length > 0 ? labels : ['No Data'],
        datasets: [{
          label: 'Total Cost',
          data: values.length > 0 ? values : [0],
          backgroundColor: purple,
          borderRadius: 6
        }]
      },
      options: getChartOptions('Spend ($)')
    });

    const supData = (kpis.supplier_intelligence && kpis.supplier_intelligence.top_suppliers_by_spend) || [];
    const supLabels = supData.map(d => d.supplier_name || d.supplier_id || 'Unknown');
    const supValues = supData.map(d => d.total_spend);

    secondaryChart = new Chart(secondaryCtx, {
      type: 'bar',
      data: {
        labels: supLabels.slice(0, 5),
        datasets: [{
          label: 'Spend',
          data: supValues.slice(0, 5),
          backgroundColor: blue,
          borderRadius: 6
        }]
      },
      options: {
        ...getChartOptions('Spend ($)'),
        indexAxis: 'y' // Horizontal bar chart
      }
    });
  }
}

// Chart Helpers
function getChartOptions(yAxisLabel) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#9ca3af', font: { family: "'Inter', sans-serif", size: 10 } }
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        title: {
          display: true,
          text: yAxisLabel,
          color: '#6b7280',
          font: { family: "'Inter', sans-serif", size: 10 }
        },
        ticks: { color: '#9ca3af', font: { family: "'Inter', sans-serif", size: 10 } }
      }
    }
  };
}

function getDoughnutOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#9ca3af',
          font: { family: "'Inter', sans-serif", size: 10 },
          padding: 12
        }
      }
    },
    cutout: '70%'
  };
}

// General Utilities
function createKpiCard(label, value, valueClass = '') {
  return `
    <div class="kpi-card">
      <h4>${escapeHtml(label)}</h4>
      <div class="kpi-value ${valueClass}">${escapeHtml(value)}</div>
    </div>
  `;
}

function formatMoney(amount) {
  if (amount === undefined || amount === null) return '$0.00';
  return '$' + Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str || '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
