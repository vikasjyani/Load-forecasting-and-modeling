// static/js/demand_visualization.js
/**
 * Enhanced Demand Visualization Application
 * Complete system with working filters, sector comparison, and consolidated analysis
 */

class DemandVisualizationApp {
    constructor() {
        this.API_BASE = '/demand_visualization/api';
        
        // Application state
        this.state = {
            currentScenario: null,
            currentData: null,
            comparisonScenario: null,
            comparisonData: null,
            isComparisonMode: false,
            
            // Filters - prevent auto-reload
            filters: {
                unit: 'TWh',
                startYear: null,
                endYear: null,
                sectors: []
            },
            filtersApplied: false,
            
            // Model configuration
            modelConfig: {},
            tdLosses: [],
            consolidatedData: null,
            
            // Charts and UI
            charts: {},
            availableScenarios: [],
            
            // Loading states
            loading: {
                scenarios: false,
                data: false,
                comparison: false,
                consolidated: false
            }
        };
        
        // Chart color schemes
        
        
        this.init();
    }
    
    async init() {
        console.log('Initializing Enhanced Demand Visualization...');
        
        try {
            this.setupEventListeners();
            this.loadInitialData();
            await this.loadScenarios();
            
            console.log('App initialized successfully');
        } catch (error) {
            console.error('Initialization error:', error);
            this.showNotification('error', 'Failed to initialize application');
        }
    }
    
    loadInitialData() {
        try {
            const dataElement = document.getElementById('initialData');
            if (dataElement) {
                const data = JSON.parse(dataElement.textContent);
                this.state.availableScenarios = data.scenarios || [];
            }
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }
    
    setupEventListeners() {
        // Scenario selection
        document.getElementById('scenarioSelect')?.addEventListener('change', (e) => {
            this.handleScenarioChange(e.target.value);
        });
        
        // Filter controls - NO auto-reload
        document.getElementById('unitSelect')?.addEventListener('change', (e) => {
            this.state.filters.unit = e.target.value;
            // Don't auto-reload, wait for apply button
        });
        
        document.getElementById('startYearSelect')?.addEventListener('change', (e) => {
            this.state.filters.startYear = parseInt(e.target.value);
            // Don't auto-reload, wait for apply button
        });
        
        document.getElementById('endYearSelect')?.addEventListener('change', (e) => {
            this.state.filters.endYear = parseInt(e.target.value);
            // Don't auto-reload, wait for apply button
        });
        
        // Apply filters button - ONLY way to reload data
        document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
            this.applyFilters();
        });
        
        document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
            this.resetFilters();
        });
        
        // View tabs
        document.querySelectorAll('.view-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchView(e.target.dataset.view);
            });
        });
        
        // Action buttons
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.loadScenarios();
        });
        
        document.getElementById('comparisonBtn')?.addEventListener('click', () => {
            this.toggleComparisonMode();
        });
        
        document.getElementById('configureBtn')?.addEventListener('click', () => {
            this.showConfigurationModal();
        });
        
        document.getElementById('exportBtn')?.addEventListener('click', () => {
            this.showExportOptions();
        });
        
        // Modal handlers
        this.setupModalHandlers();
    }
    
    setupModalHandlers() {
        // Configuration modal
        document.getElementById('closeModelModal')?.addEventListener('click', () => {
            this.hideModal('modelConfigModal');
        });
        
        document.getElementById('cancelConfigBtn')?.addEventListener('click', () => {
            this.hideModal('modelConfigModal');
        });
        
        document.getElementById('saveConfigBtn')?.addEventListener('click', () => {
            this.saveConfiguration();
        });
        
        document.getElementById('addTdLossBtn')?.addEventListener('click', () => {
            this.addTdLossEntry();
        });
        
        // Comparison modal
        document.getElementById('closeComparisonModal')?.addEventListener('click', () => {
            this.hideModal('comparisonModal');
        });
        
        document.getElementById('cancelComparisonBtn')?.addEventListener('click', () => {
            this.hideModal('comparisonModal');
        });
        
        document.getElementById('startComparisonBtn')?.addEventListener('click', () => {
            this.startComparison();
        });
        
        document.getElementById('comparisonScenarioSelect')?.addEventListener('change', (e) => {
            document.getElementById('startComparisonBtn').disabled = !e.target.value;
        });
        
        // Click outside modal to close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                this.hideModal(e.target.id);
            }
        });
    }
    
    async loadScenarios() {
        try {
            this.state.loading.scenarios = true;
            this.showLoading('Loading scenarios...');
            
            const response = await fetch(`${this.API_BASE}/scenarios`);
            const data = await response.json();
            
            if (data.success) {
                this.state.availableScenarios = data.scenarios;
                this.updateScenarioSelect();
                
                if (data.scenarios.length === 0) {
                    this.showNotification('warning', 'No scenarios found. Please run demand projection first.');
                }
            } else {
                throw new Error(data.error || 'Failed to load scenarios');
            }
        } catch (error) {
            console.error('Error loading scenarios:', error);
            this.showNotification('error', 'Failed to load scenarios: ' + error.message);
        } finally {
            this.state.loading.scenarios = false;
            this.hideLoading();
        }
    }
    
    updateScenarioSelect() {
        const select = document.getElementById('scenarioSelect');
        if (!select) return;
        
        // Clear existing options (except first)
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        // Add scenario options
        this.state.availableScenarios.forEach(scenario => {
            const option = document.createElement('option');
            option.value = scenario.name;
            option.textContent = `${scenario.name} (${scenario.sectors_count} sectors)`;
            option.dataset.sectors = scenario.sectors_count;
            option.dataset.files = scenario.file_count || scenario.sectors_count;
            option.dataset.yearMin = scenario.year_range.min;
            option.dataset.yearMax = scenario.year_range.max;
            select.appendChild(option);
        });
    }
    
    async handleScenarioChange(scenarioName) {
        if (!scenarioName) {
            this.clearScenario();
            return;
        }
        
        try {
            this.state.currentScenario = scenarioName;
            this.updateScenarioInfo(scenarioName);
            this.showFiltersSection();
            this.initializeFilters(scenarioName);
            
            // Enable comparison button
            document.getElementById('comparisonBtn').disabled = false;
            
            // Load initial scenario data
            await this.loadScenarioData();
            
        } catch (error) {
            console.error('Error handling scenario change:', error);
            this.showNotification('error', 'Failed to load scenario: ' + error.message);
        }
    }
    
    updateScenarioInfo(scenarioName) {
        const scenario = this.state.availableScenarios.find(s => s.name === scenarioName);
        if (!scenario) return;
        
        const infoDiv = document.getElementById('scenarioInfo');
        const sectorsCount = document.getElementById('sectorsCount');
        const filesCount = document.getElementById('filesCount');
        const yearRange = document.getElementById('yearRange');
        const dataStatus = document.getElementById('dataStatus');
        
        if (sectorsCount) sectorsCount.textContent = scenario.sectors_count;
        if (filesCount) filesCount.textContent = scenario.file_count || scenario.sectors_count;
        if (yearRange) yearRange.textContent = `${scenario.year_range.min}-${scenario.year_range.max}`;
        if (dataStatus) dataStatus.textContent = 'Loading...';
        
        if (infoDiv) {
            infoDiv.classList.add('show');
        }
    }
    
    showFiltersSection() {
        const section = document.getElementById('filtersSection');
        if (section) {
            section.style.display = 'block';
        }
    }
    
    initializeFilters(scenarioName) {
        const scenario = this.state.availableScenarios.find(s => s.name === scenarioName);
        if (!scenario) return;
        
        // Initialize year range filters
        const startYearSelect = document.getElementById('startYearSelect');
        const endYearSelect = document.getElementById('endYearSelect');
        
        if (startYearSelect && endYearSelect) {
            // Clear existing options
            startYearSelect.innerHTML = '';
            endYearSelect.innerHTML = '';
            
            // Populate year options
            for (let year = scenario.year_range.min; year <= scenario.year_range.max; year++) {
                const startOption = document.createElement('option');
                startOption.value = year;
                startOption.textContent = year;
                startYearSelect.appendChild(startOption);
                
                const endOption = document.createElement('option');
                endOption.value = year;
                endOption.textContent = year;
                endYearSelect.appendChild(endOption);
            }
            
            // Set default values
            startYearSelect.value = scenario.year_range.min;
            endYearSelect.value = scenario.year_range.max;
            
            // Update state (but don't reload data)
            this.state.filters.startYear = scenario.year_range.min;
            this.state.filters.endYear = scenario.year_range.max;
        }
    }
    
    async applyFilters() {
        if (!this.state.currentScenario) {
            this.showNotification('warning', 'Please select a scenario first');
            return;
        }
        
        // Validate year range
        if (this.state.filters.startYear > this.state.filters.endYear) {
            this.showNotification('error', 'Start year cannot be greater than end year');
            return;
        }
        
        this.state.filtersApplied = true;
        await this.loadScenarioData();
        this.showNotification('success', 'Filters applied successfully');
    }
    
    resetFilters() {
        // Reset filter controls to defaults
        document.getElementById('unitSelect').value = 'TWh';
        this.state.filters.unit = 'TWh';
        
        if (this.state.currentScenario) {
            this.initializeFilters(this.state.currentScenario);
        }
        
        this.state.filtersApplied = false;
        this.showNotification('info', 'Filters reset to defaults');
    }
    
    async loadScenarioData() {
        if (!this.state.currentScenario) return;
        
        try {
            this.state.loading.data = true;
            this.showLoading('Loading scenario data...');
            
            // Build query parameters with current filters
            const params = new URLSearchParams();
            if (this.state.filters.unit) params.set('unit', this.state.filters.unit);
            if (this.state.filters.startYear) params.set('start_year', this.state.filters.startYear);
            if (this.state.filters.endYear) params.set('end_year', this.state.filters.endYear);
            
            const response = await fetch(`${this.API_BASE}/scenario/${this.state.currentScenario}?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.state.currentData = result.data;
                this.showAnalysisPanel();
                this.updateAllViews();
                
                // Update status
                document.getElementById('dataStatus').textContent = 'Ready';
                document.getElementById('panelTitle').textContent = `${this.state.currentScenario} Analysis`;
                
            } else {
                throw new Error(result.error || 'Failed to load scenario data');
            }
            
        } catch (error) {
            console.error('Error loading scenario data:', error);
            this.showNotification('error', 'Failed to load scenario data: ' + error.message);
        } finally {
            this.state.loading.data = false;
            this.hideLoading();
        }
    }
    
    showAnalysisPanel() {
        const panel = document.getElementById('analysisPanel');
        if (panel) {
            panel.style.display = 'block';
        }
    }
    
    updateAllViews() {
        this.updateOverviewContent();
        this.updateSectorContent();
        if (this.state.isComparisonMode) {
            this.updateComparisonContent();
        }
    }
    
    updateOverviewContent() {
        const container = document.getElementById('overviewContent');
        if (!container || !this.state.currentData) return;
        
        const data = this.state.currentData;
        
        let html = `
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-label">Total Sectors</div>
                        <div class="metric-value">${data.total_sectors}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-label">Available Models</div>
                        <div class="metric-value">${data.available_models.length}</div>
                        <div class="metric-detail">${data.available_models.join(', ')}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-label">Year Range</div>
                        <div class="metric-value">${data.year_range.max - data.year_range.min + 1}</div>
                        <div class="metric-detail">years (${data.year_range.min}-${data.year_range.max})</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-label">Current Unit</div>
                        <div class="metric-value">${data.unit}</div>
                        <div class="metric-detail">Applied filters: ${this.state.filtersApplied ? 'Yes' : 'Default'}</div>
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
                <h6 class="mb-3">Sector Overview - Total Demand by First Available Model</h6>
                <canvas id="overviewChart" class="chart-canvas"></canvas>
            </div>
        `;
        
        container.innerHTML = html;
        this.createOverviewChart();
    }
    
    createOverviewChart() {
        const canvas = document.getElementById('overviewChart');
        if (!canvas || !this.state.currentData) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.state.currentData;
        
        // Destroy existing chart
        if (this.state.charts.overview) {
            this.state.charts.overview.destroy();
        }
        
        // Calculate total demand by sector using first available model
        const sectors = Object.keys(data.sectors);
        const sectorTotals = sectors.map(sector => {
            const sectorData = data.sectors[sector];
            if (sectorData.models.length > 0) {
                const firstModel = sectorData.models[0];
                if (sectorData[firstModel]) {
                    return sectorData[firstModel].reduce((sum, val) => sum + (val || 0), 0);
                }
            }
            return 0;
        });
        
        this.state.charts.overview = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sectors,
                datasets: [{
                    label: `Total Demand (${data.unit})`,
                    data: sectorTotals,
                    backgroundColor: sectors.map(sectorName => {
                        const color = window.colorManager?.getColor('sectors', sectorName) ||
                                      window.colorManager?.getChartColors(1)[0] ||
                                      '#CCCCCC'; // Fallback grey
                        return color + '80'; // Apply alpha
                    }),
                    borderColor: sectors.map(sectorName => {
                        return window.colorManager?.getColor('sectors', sectorName) ||
                               window.colorManager?.getChartColors(1)[0] ||
                               '#CCCCCC'; // Fallback grey
                    }),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Sector-wise Total Demand (${data.unit})`
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: `Demand (${data.unit})`
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Sectors'
                        }
                    }
                }
            }
        });
    }
    
    updateSectorContent() {
        const container = document.getElementById('sectorContent');
        if (!container || !this.state.currentData) return;
        
        const data = this.state.currentData;
        const sectors = Object.keys(data.sectors);
        
        if (sectors.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-table"></i>
                    <h5>No sector data available</h5>
                    <p>No sector data found for the current filters.</p>
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Select Sector for Analysis:</label>
                    <select id="sectorSelect" class="form-select">
                        ${sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('')}
                    </select>
                </div>
                <div class="col-md-6">
                    <div class="d-flex gap-2 align-items-end">
                        <button class="btn btn-primary btn-sm" id="downloadSectorChart">
                            <i class="fas fa-image me-1"></i>Chart PNG
                        </button>
                        <button class="btn btn-outline-primary btn-sm" id="downloadSectorData">
                            <i class="fas fa-table me-1"></i>Data CSV
                        </button>
                    </div>
                </div>
            </div>
            
            <div id="sectorDetails">
                <!-- Sector details will be populated here -->
            </div>
        `;
        
        container.innerHTML = html;
        
        // Setup event listeners
        document.getElementById('sectorSelect')?.addEventListener('change', (e) => {
            this.updateSectorDetails(e.target.value);
        });
        
        document.getElementById('downloadSectorChart')?.addEventListener('click', () => {
            this.downloadChart('sectorChart');
        });
        
        document.getElementById('downloadSectorData')?.addEventListener('click', () => {
            this.downloadSectorCSV();
        });
        
        // Show first sector by default
        if (sectors.length > 0) {
            this.updateSectorDetails(sectors[0]);
        }
    }
    
    updateSectorDetails(sectorName) {
        const container = document.getElementById('sectorDetails');
        if (!container || !this.state.currentData) return;
        
        const sectorData = this.state.currentData.sectors[sectorName];
        if (!sectorData) return;
        
        let html = `
            <div class="row">
                <div class="col-md-12 mb-3">
                    <h6>${sectorName} - All Models Comparison</h6>
                    <div class="chart-container">
                        <canvas id="sectorChart" class="chart-canvas"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-12">
                    <h6>${sectorName} - Data Table</h6>
                    <div class="data-table-container">
                        <table class="data-table" id="sectorDataTable">
                            <thead>
                                <tr>
                                    <th>Year</th>
                                    ${sectorData.models.map(model => `<th>${model}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        sectorData.years.forEach((year, index) => {
            html += `<tr><td>${year}</td>`;
            sectorData.models.forEach(model => {
                const value = sectorData[model] && sectorData[model][index] !== undefined 
                    ? sectorData[model][index].toFixed(3) 
                    : '0.000';
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Create sector chart showing ALL models as line charts
        this.createSectorChart(sectorName, sectorData);
    }
    
    createSectorChart(sectorName, sectorData) {
        const canvas = document.getElementById('sectorChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.state.charts.sector) {
            this.state.charts.sector.destroy();
        }
        
        // Create datasets for each model - ALL MODELS AS LINE CHARTS
        const datasets = sectorData.models.map((model, index) => {
            return {
                label: model,
                data: sectorData[model] || [],
                borderColor: window.colorManager?.getColor('models', model) ||
                             window.colorManager?.getChartColors(1)[0] ||
                             this.generateRandomColor(index), // Existing fallback if others fail
                backgroundColor: (window.colorManager?.getColor('models', model) ||
                                  window.colorManager?.getChartColors(1)[0] ||
                                  this.generateRandomColor(index)) + '20', // Apply alpha
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.1,
                fill: false
            };
        });
        
        this.state.charts.sector = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sectorData.years,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${sectorName} - All Models Demand Forecast (${this.state.currentData.unit})`
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: `Demand (${this.state.currentData.unit})`
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Year'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }
    
    switchView(viewName) {
        // Update tab active state
        document.querySelectorAll('.view-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.view === viewName);
        });
        
        // Update content visibility
        document.querySelectorAll('.view-content').forEach(content => {
            content.classList.toggle('active', content.dataset.view === viewName);
        });
        
        // Load view-specific content
        if (viewName === 'consolidated') {
            this.loadConsolidatedView();
        } else if (viewName === 'comparison' && this.state.isComparisonMode) {
            this.updateComparisonContent();
        }
    }
    
    loadConsolidatedView() {
        const container = document.getElementById('consolidatedContent');
        if (!container) return;
        
        if (this.state.consolidatedData) {
            this.displayConsolidatedResults();
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-area"></i>
                    <h5>Consolidated Results</h5>
                    <p>Configure model selection and T&D losses to generate consolidated analysis.</p>
                    <button class="btn btn-primary mt-3" onclick="demandVizApp.showConfigurationModal()">
                        <i class="fas fa-cogs me-1"></i>Start Configuration
                    </button>
                </div>
            `;
        }
    }
    
    toggleComparisonMode() {
        if (!this.state.currentScenario) {
            this.showNotification('warning', 'Please select a scenario first');
            return;
        }
        
        if (this.state.isComparisonMode) {
            this.exitComparisonMode();
        } else {
            this.showComparisonModal();
        }
    }
    
    showComparisonModal() {
        // Populate comparison scenario options (exclude current scenario)
        const select = document.getElementById('comparisonScenarioSelect');
        if (select) {
            // Clear existing options (except first)
            while (select.children.length > 1) {
                select.removeChild(select.lastChild);
            }
            
            this.state.availableScenarios
                .filter(s => s.name !== this.state.currentScenario)
                .forEach(scenario => {
                    const option = document.createElement('option');
                    option.value = scenario.name;
                    option.textContent = `${scenario.name} (${scenario.sectors_count} sectors)`;
                    select.appendChild(option);
                });
        }
        
        this.showModal('comparisonModal');
    }
    
    async startComparison() {
        const comparisonScenario = document.getElementById('comparisonScenarioSelect')?.value;
        if (!comparisonScenario) {
            this.showNotification('warning', 'Please select a scenario to compare');
            return;
        }
        
        try {
            this.state.loading.comparison = true;
            this.showLoading('Loading comparison data...');
            
            // Build query parameters with current filters
            const params = new URLSearchParams();
            params.set('scenario1', this.state.currentScenario);
            params.set('scenario2', comparisonScenario);
            if (this.state.filters.unit) params.set('unit', this.state.filters.unit);
            if (this.state.filters.startYear) params.set('start_year', this.state.filters.startYear);
            if (this.state.filters.endYear) params.set('end_year', this.state.filters.endYear);
            
            const response = await fetch(`${this.API_BASE}/comparison?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.state.comparisonData = result.comparison;
                this.state.comparisonScenario = comparisonScenario;
                this.state.isComparisonMode = true;
                
                this.enableComparisonMode();
                this.updateComparisonContent();
                this.switchView('comparison');
                this.hideModal('comparisonModal');
                
                this.showNotification('success', 'Comparison mode activated successfully');
            } else {
                throw new Error(result.error || 'Failed to load comparison data');
            }
            
        } catch (error) {
            console.error('Error starting comparison:', error);
            this.showNotification('error', 'Failed to load comparison data: ' + error.message);
        } finally {
            this.state.loading.comparison = false;
            this.hideLoading();
        }
    }
    
    enableComparisonMode() {
        // Show comparison tab
        const comparisonTab = document.getElementById('comparisonTab');
        if (comparisonTab) {
            comparisonTab.style.display = 'block';
        }
        
        // Update comparison button
        const comparisonBtn = document.getElementById('comparisonBtn');
        if (comparisonBtn) {
            comparisonBtn.innerHTML = '<i class="fas fa-times me-1"></i>Exit Compare';
            comparisonBtn.className = 'btn btn-outline-warning';
        }
    }
    
    exitComparisonMode() {
        this.state.isComparisonMode = false;
        this.state.comparisonScenario = null;
        this.state.comparisonData = null;
        
        // Hide comparison tab
        const comparisonTab = document.getElementById('comparisonTab');
        if (comparisonTab) {
            comparisonTab.style.display = 'none';
        }
        
        // Reset comparison button
        const comparisonBtn = document.getElementById('comparisonBtn');
        if (comparisonBtn) {
            comparisonBtn.innerHTML = '<i class="fas fa-balance-scale me-1"></i>Compare';
            comparisonBtn.className = 'btn btn-warning';
        }
        
        // Switch to overview if currently on comparison
        const activeTab = document.querySelector('.view-tab.active');
        if (activeTab && activeTab.dataset.view === 'comparison') {
            this.switchView('overview');
        }
        
        this.showNotification('info', 'Comparison mode disabled');
    }
    
    updateComparisonContent() {
        const container = document.getElementById('comparisonContent');
        if (!container || !this.state.comparisonData) return;
        
        const data = this.state.comparisonData;
        const commonSectors = data.common_sectors;
        
        if (commonSectors.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h5>No Common Sectors</h5>
                    <p>The selected scenarios have no sectors in common for comparison.</p>
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="mb-3">
                <h6>Scenario Comparison: ${data.scenario1.name} vs ${data.scenario2.name}</h6>
                <p class="text-muted">Comparing ${commonSectors.length} common sectors with current filters applied</p>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Select Sector for Comparison:</label>
                    <select id="comparisonSectorSelect" class="form-select">
                        ${commonSectors.map(sector => `<option value="${sector}">${sector}</option>`).join('')}
                    </select>
                </div>
                <div class="col-md-6">
                    <div class="d-flex gap-2 align-items-end">
                        <button class="btn btn-primary btn-sm" id="downloadComparisonChart">
                            <i class="fas fa-image me-1"></i>Chart PNG
                        </button>
                        <button class="btn btn-outline-primary btn-sm" id="compareConsolidatedBtn">
                            <i class="fas fa-chart-area me-1"></i>Compare Consolidated
                        </button>
                    </div>
                </div>
            </div>
            
            <div id="comparisonDetails">
                <!-- Comparison details will be populated here -->
            </div>
        `;
        
        container.innerHTML = html;
        
        // Setup event listeners
        document.getElementById('comparisonSectorSelect')?.addEventListener('change', (e) => {
            this.updateComparisonDetails(e.target.value);
        });
        
        document.getElementById('downloadComparisonChart')?.addEventListener('click', () => {
            this.downloadChart('comparisonChart');
        });
        
        document.getElementById('compareConsolidatedBtn')?.addEventListener('click', () => {
            this.compareConsolidatedResults();
        });
        
        // Show first sector by default
        if (commonSectors.length > 0) {
            this.updateComparisonDetails(commonSectors[0]);
        }
    }
    
    updateComparisonDetails(sectorName) {
        const container = document.getElementById('comparisonDetails');
        if (!container || !this.state.comparisonData) return;
        
        const data = this.state.comparisonData;
        const sector1Data = data.scenario1.sectors[sectorName];
        const sector2Data = data.scenario2.sectors[sectorName];
        
        if (!sector1Data || !sector2Data) return;
        
        let html = `
            <div class="row">
                <div class="col-md-12 mb-3">
                    <h6>${sectorName} - Sector Comparison (All Models)</h6>
                    <div class="chart-container">
                        <canvas id="comparisonChart" class="chart-canvas"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <h6>${data.scenario1.name} - ${sectorName}</h6>
                    <div class="data-table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Year</th>
                                    ${sector1Data.models.map(model => `<th>${model}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        sector1Data.years.forEach((year, index) => {
            html += `<tr><td>${year}</td>`;
            sector1Data.models.forEach(model => {
                const value = sector1Data[model] && sector1Data[model][index] !== undefined 
                    ? sector1Data[model][index].toFixed(3) 
                    : '0.000';
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>${data.scenario2.name} - ${sectorName}</h6>
                    <div class="data-table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Year</th>
                                    ${sector2Data.models.map(model => `<th>${model}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        sector2Data.years.forEach((year, index) => {
            html += `<tr><td>${year}</td>`;
            sector2Data.models.forEach(model => {
                const value = sector2Data[model] && sector2Data[model][index] !== undefined 
                    ? sector2Data[model][index].toFixed(3) 
                    : '0.000';
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Create comparison chart showing ALL models from BOTH scenarios
        this.createComparisonChart(sectorName, sector1Data, sector2Data);
    }
    
    createComparisonChart(sectorName, sector1Data, sector2Data) {
        const canvas = document.getElementById('comparisonChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.state.charts.comparison) {
            this.state.charts.comparison.destroy();
        }
        
        const datasets = [];
        
        // Add datasets for scenario 1 - solid lines
        sector1Data.models.forEach((model, index) => {
            datasets.push({
                label: `${this.state.comparisonData.scenario1.name} - ${model}`,
                data: sector1Data[model] || [],
                borderColor: this.modelColors[model] || this.generateRandomColor(index),
                backgroundColor: (this.modelColors[model] || this.generateRandomColor(index)) + '20',
                borderWidth: 3,
                pointRadius: 5,
                pointHoverRadius: 7,
                tension: 0.1,
                fill: false,
                borderDash: [] // Solid line
            });
        });
        
        // Add datasets for scenario 2 - dashed lines
        sector2Data.models.forEach((model, index) => {
            datasets.push({
                label: `${this.state.comparisonData.scenario2.name} - ${model}`,
                data: sector2Data[model] || [],
                borderColor: window.colorManager?.getColor('models', model) ||
                             window.colorManager?.getChartColors(1)[0] ||
                             this.generateRandomColor(index),
                backgroundColor: (window.colorManager?.getColor('models', model) ||
                                  window.colorManager?.getChartColors(1)[0] ||
                                  this.generateRandomColor(index)) + '10', // Corrected alpha to '10'
                borderWidth: 3,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.1,
                fill: false,
                borderDash: [5, 5] // Dashed line
            });
        });
        
        this.state.charts.comparison = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.getCommonYears(sector1Data.years, sector2Data.years),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${sectorName} - Scenario Comparison (${this.state.filters.unit})`
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                return `Year: ${context[0].label}`;
                            },
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(3)} ${demandVizApp.state.filters.unit}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: `Demand (${this.state.filters.unit})`
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Year'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }
    
    async compareConsolidatedResults() {
        if (!this.state.comparisonScenario) {
            this.showNotification('warning', 'No comparison scenario selected');
            return;
        }
        
        try {
            this.showLoading('Checking consolidated results...');
            
            // Check if comparison scenario has consolidated results
            const response = await fetch(`${this.API_BASE}/validate/${this.state.comparisonScenario}`);
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to validate comparison scenario');
            }
            
            const validation = result.validation;
            
            // Check if consolidated results exist
            if (!validation.configurations.has_model_selection || !validation.configurations.has_td_losses) {
                this.showNotification('warning', 
                    `Scenario "${this.state.comparisonScenario}" needs to complete model selection and T&D losses configuration first.`);
                return;
            }
            
            // Try to load consolidated results
            const consolidatedResponse = await fetch(`${this.API_BASE}/export/${this.state.comparisonScenario}?type=consolidated`);
            
            if (!consolidatedResponse.ok) {
                this.showNotification('warning', 
                    `Please generate consolidated results for scenario "${this.state.comparisonScenario}" first.`);
                return;
            }
            
            // If we get here, both scenarios have consolidated results
            this.loadConsolidatedComparison();
            
        } catch (error) {
            console.error('Error comparing consolidated results:', error);
            this.showNotification('error', 'Failed to compare consolidated results: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async loadConsolidatedComparison() {
        // Implementation for side-by-side consolidated results comparison
        this.showNotification('info', 'Consolidated comparison feature - implementation in progress');
        // This would load both consolidated CSVs and create side-by-side charts
    }
    
    // Configuration Modal Functions
    showConfigurationModal() {
        if (!this.state.currentData) {
            this.showNotification('warning', 'Please load scenario data first');
            return;
        }
        
        this.populateModelConfiguration();
        this.populateTdLossesConfiguration();
        this.showModal('modelConfigModal');
    }
    
    populateModelConfiguration() {
        const container = document.getElementById('modelConfigContent');
        if (!container || !this.state.currentData) return;
        
        const sectors = Object.keys(this.state.currentData.sectors);
        let html = '';
        
        sectors.forEach(sector => {
            const sectorData = this.state.currentData.sectors[sector];
            html += `
                <div class="model-config-item">
                    <div class="sector-name">${sector}</div>
                    <select class="form-select" data-sector="${sector}">
                        <option value="">Select model...</option>
                        ${sectorData.models.map(model => 
                            `<option value="${model}">${model}</option>`
                        ).join('')}
                    </select>
                    <small class="text-muted">Available: ${sectorData.models.join(', ')}</small>
                </div>
            `;
        });
        
        container.innerHTML = html;
        this.loadExistingModelConfiguration();
    }
    
    async loadExistingModelConfiguration() {
        try {
            const response = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`);
            const result = await response.json();
            
            if (result.success && result.config.model_selection) {
                const modelSelection = result.config.model_selection;
                this.state.modelConfig = modelSelection;
                
                Object.keys(modelSelection).forEach(sector => {
                    const select = document.querySelector(`select[data-sector="${sector}"]`);
                    if (select) {
                        select.value = modelSelection[sector];
                    }
                });
            }
        } catch (error) {
            console.error('Error loading existing model config:', error);
        }
    }
    
    populateTdLossesConfiguration() {
        this.loadExistingTdLosses();
    }
    
    async loadExistingTdLosses() {
        try {
            const response = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`);
            const result = await response.json();
            
            if (result.success && result.config.td_losses) {
                this.state.tdLosses = result.config.td_losses;
            } else {
                // Default T&D losses
                this.state.tdLosses = [
                    { year: this.state.filters.startYear || 2025, loss_percentage: 12.0 },
                    { year: Math.floor((this.state.filters.startYear + this.state.filters.endYear) / 2) || 2030, loss_percentage: 8.0 },
                    { year: this.state.filters.endYear || 2037, loss_percentage: 6.0 }
                ];
            }
            
            this.updateTdLossesDisplay();
        } catch (error) {
            console.error('Error loading existing T&D losses:', error);
            this.state.tdLosses = [
                           min="0" max="100" step="0.1">
                    <button class="btn btn-sm btn-outline-danger" onclick="demandVizApp.removeTdLossEntry(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
        // Add event listeners for input changes
        container.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.index);
                const field = e.target.dataset.field;
                const value = field === 'year' ? parseInt(e.target.value) : parseFloat(e.target.value);
                
                if (this.state.tdLosses[index] && !isNaN(value)) {
                    this.state.tdLosses[index][field] = value;
                }
            });
        });
    }
    
    addTdLossEntry() {
        const newYear = this.state.filters.startYear || 2025;
        this.state.tdLosses.push({ year: newYear, loss_percentage: 10.0 });
        this.updateTdLossesDisplay();
    }
    
    removeTdLossEntry(index) {
        if (this.state.tdLosses.length > 1) {
            this.state.tdLosses.splice(index, 1);
            this.updateTdLossesDisplay();
        } else {
            this.showNotification('warning', 'At least one T&D loss entry is required');
        }
    }
    
    async saveConfiguration() {
        try {
            // Collect model selection
            const modelSelection = {};
            let hasAllModels = true;
            
            document.querySelectorAll('#modelConfigContent select').forEach(select => {
                if (select.value) {
                    modelSelection[select.dataset.sector] = select.value;
                } else {
                    hasAllModels = false;
                }
            });
            
            if (!hasAllModels) {
                this.showNotification('warning', 'Please select models for all sectors');
                return;
            }
            
            // Validate T&D losses
            const validTdLosses = this.state.tdLosses.filter(loss => 
                loss.year > 0 && loss.loss_percentage >= 0 && loss.loss_percentage <= 100
            );
            
            if (validTdLosses.length === 0) {
                this.showNotification('warning', 'Please add valid T&D losses data');
                return;
            }
            
            this.showLoading('Saving configuration and generating results...');
            
            // Save model selection
            const modelResponse = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_selection: modelSelection })
            });
            
            const modelResult = await modelResponse.json();
            if (!modelResult.success) {
                throw new Error(modelResult.error || 'Failed to save model selection');
            }
            
            // Save T&D losses
            const tdResponse = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ td_losses: validTdLosses })
            });
            
            const tdResult = await tdResponse.json();
            if (!tdResult.success) {
                throw new Error(tdResult.error || 'Failed to save T&D losses');
            }
            
            // Generate consolidated results
            const consolidatedResponse = await fetch(`${this.API_BASE}/consolidated/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_selection: modelSelection,
                    td_losses: validTdLosses,
                    filters: this.state.filters
                })
            });
            
            const consolidatedResult = await consolidatedResponse.json();
            if (consolidatedResult.success) {
                this.state.consolidatedData = consolidatedResult.data;
            }
            
            this.hideModal('modelConfigModal');
            this.switchView('consolidated');
            this.displayConsolidatedResults();
            this.showNotification('success', 'Configuration saved and consolidated results generated');
            
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showNotification('error', 'Failed to save configuration: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    displayConsolidatedResults() {
        const container = document.getElementById('consolidatedContent');
        if (!container || !this.state.consolidatedData) return;
        
        const data = this.state.consolidatedData.consolidated_data;
        if (!data || data.length === 0) return;
        
        let html = `
            <div class="row mb-4">
                <div class="col-md-12">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6>Consolidated Demand Analysis</h6>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary active" data-chart-type="line">Line Chart</button>
                            <button class="btn btn-outline-primary" data-chart-type="bar">Bar Chart</button>
                            <button class="btn btn-outline-primary" data-chart-type="area">Area Chart</button>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="consolidatedChart" class="chart-canvas"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-12">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6>Consolidated Data Table</h6>
                        <button class="btn btn-sm btn-outline-primary" id="downloadConsolidatedCSV">
                            <i class="fas fa-download me-1"></i>Download CSV
                        </button>
                    </div>
                    <div class="data-table-container">
                        <table class="data-table" id="consolidatedTable">
                            <thead>
                                <tr>
                                    <th>Year</th>
        `;
        
        // Add sector columns
        const firstRow = data[0];
        const sectorColumns = Object.keys(firstRow).filter(key => 
            !['Year', 'Total_Gross_Demand', 'TD_Losses', 'Total_Net_Demand', 'Loss_Percentage'].includes(key)
        );
        
        sectorColumns.forEach(sector => {
            html += `<th>${sector}</th>`;
        });
        
        html += `
                                    <th>Total Gross</th>
                                    <th>T&D Losses</th>
                                    <th>Total Net</th>
                                    <th>Loss %</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        data.forEach(row => {
            html += `<tr><td>${row.Year}</td>`;
            
            sectorColumns.forEach(sector => {
                html += `<td>${(row[sector] || 0).toFixed(3)}</td>`;
            });
            
            html += `
                <td>${(row.Total_Gross_Demand || 0).toFixed(3)}</td>
                <td>${(row.TD_Losses || 0).toFixed(3)}</td>
                <td>${(row.Total_Net_Demand || 0).toFixed(3)}</td>
                <td>${(row.Loss_Percentage || 0).toFixed(2)}%</td>
            </tr>`;
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Setup event listeners
        document.querySelectorAll('[data-chart-type]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-chart-type]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.updateConsolidatedChart(e.target.dataset.chartType);
            });
        });
        
        document.getElementById('downloadConsolidatedCSV')?.addEventListener('click', () => {
            this.downloadConsolidatedCSV();
        });
        
        // Create initial chart
        this.createConsolidatedChart('line');
    }
    
    createConsolidatedChart(chartType = 'line') {
        const canvas = document.getElementById('consolidatedChart');
        if (!canvas || !this.state.consolidatedData) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.state.consolidatedData.consolidated_data;
        
        // Destroy existing chart
        if (this.state.charts.consolidated) {
            this.state.charts.consolidated.destroy();
        }
        
        // Extract sector data
        const years = data.map(row => row.Year);
        const firstRow = data[0];
        const sectorColumns = Object.keys(firstRow).filter(key => 
            !['Year', 'Total_Gross_Demand', 'TD_Losses', 'Total_Net_Demand', 'Loss_Percentage'].includes(key)
        );
        
        // Create datasets for sectors
        const datasets = sectorColumns.map((sectorName, index) => {
            const sectorColor = window.colorManager?.getColor('sectors', sectorName) ||
                                window.colorManager?.getChartColors(1)[0] ||
                                '#A9A9A9'; // Fallback dark grey
            return {
                label: sectorName,
                data: data.map(row => row[sectorName] || 0),
                backgroundColor: sectorColor + (chartType === 'area' ? '60' : '80'), // Apply alpha
                borderColor: sectorColor,
                borderWidth: 2,
                fill: chartType === 'area',
            };
        }));

        // Add T&D losses dataset
        const tdLossesColor = window.colorManager?.getColor('status', 'error') ||
                              window.colorManager?.getColor('charts', 'tertiary') ||
                              '#FF0000'; // Fallback red
        datasets.push({
            label: 'T&D Losses',
            data: data.map(row => row.TD_Losses || 0),
            backgroundColor: tdLossesColor + (chartType === 'area' ? '60' : '80'), // Apply alpha
            borderColor: tdLossesColor,
            borderWidth: 2,
            fill: chartType === 'area',
            tension: 0.1
        }));
        
        // Add T&D losses dataset
        datasets.push({
            label: 'T&D Losses',
            data: data.map(row => row.TD_Losses || 0),
            backgroundColor: '#ef444460',
            borderColor: '#ef4444',
            borderWidth: 2,
            fill: chartType === 'area',
            tension: 0.1
        });
        
        this.state.charts.consolidated = new Chart(ctx, {
            type: chartType === 'area' ? 'line' : chartType,
            data: {
                labels: years,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Consolidated Electricity Demand (${this.state.filters.unit})`
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Year'
                        },
                        stacked: chartType === 'bar'
                    },
                    y: {
                        title: {
                            display: true,
                            text: `Demand (${this.state.filters.unit})`
                        },
                        stacked: chartType === 'bar',
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    updateConsolidatedChart(chartType) {
        this.createConsolidatedChart(chartType);
    }
    
    // Export and Download Functions
    async downloadSectorCSV() {
        const sectorSelect = document.getElementById('sectorSelect');
        const selectedSector = sectorSelect ? sectorSelect.value : null;
        
        if (!selectedSector) {
            this.showNotification('warning', 'Please select a sector first');
            return;
        }
        
        try {
            const params = new URLSearchParams();
            params.set('type', 'scenario');
            if (this.state.filters.unit) params.set('unit', this.state.filters.unit);
            if (this.state.filters.startYear) params.set('start_year', this.state.filters.startYear);
            if (this.state.filters.endYear) params.set('end_year', this.state.filters.endYear);
            
            const response = await fetch(`${this.API_BASE}/export/${this.state.currentScenario}?${params}`);
            
            if (response.ok) {
                const blob = await response.blob();
                this.downloadBlob(blob, `${selectedSector}_${this.state.currentScenario}.csv`);
                this.showNotification('success', 'Sector data downloaded successfully');
            } else {
                throw new Error('Download failed');
            }
        } catch (error) {
            console.error('Error downloading sector CSV:', error);
            this.showNotification('error', 'Failed to download sector data');
        }
    }
    
    async downloadConsolidatedCSV() {
        try {
            const response = await fetch(`${this.API_BASE}/export/${this.state.currentScenario}?type=consolidated`);
            
            if (response.ok) {
                const blob = await response.blob();
                this.downloadBlob(blob, `consolidated_${this.state.currentScenario}.csv`);
                this.showNotification('success', 'Consolidated data downloaded successfully');
            } else {
                throw new Error('Download failed');
            }
        } catch (error) {
            console.error('Error downloading consolidated CSV:', error);
            this.showNotification('error', 'Failed to download consolidated data');
        }
    }
    
    downloadChart(chartId) {
        const chart = this.state.charts[chartId];
        if (!chart) {
            this.showNotification('warning', 'Chart not found');
            return;
        }
        
        const canvas = chart.canvas;
        const url = canvas.toDataURL('image/png');
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chartId}_${new Date().toISOString().split('T')[0]}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        this.showNotification('success', 'Chart downloaded successfully');
    }
    
    downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    showExportOptions() {
        // Simple export options - could be enhanced with a modal
        const options = [
            'Current Sector Data (CSV)',
            'All Scenario Data (CSV)', 
            'Consolidated Results (CSV)',
            'Current Chart (PNG)'
        ];
        
        // For now, just show info notification
        this.showNotification('info', 'Use individual download buttons on each section for exports');
    }
    
    // Utility Functions
    generateSectorColors() {
        const colors = [
            '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
            '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6366f1',
            '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981'
        ];
        return colors;
    }
    
    getSectorColor(sector) {
        const hash = this.hashCode(sector);
        const index = Math.abs(hash) % this.sectorColors.length;
        return this.sectorColors[index];
    }
    
    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return hash;
    }
    
    generateRandomColor(index) {
        const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
        return colors[index % colors.length];
    }
    
    getCommonYears(years1, years2) {
        return years1.filter(year => years2.includes(year));
    }
    
    clearScenario() {
        this.state.currentScenario = null;
        this.state.currentData = null;
        this.exitComparisonMode();
        
        // Hide sections
        document.getElementById('filtersSection').style.display = 'none';
        document.getElementById('analysisPanel').style.display = 'none';
        document.getElementById('scenarioInfo').classList.remove('show');
        
        // Disable buttons
        document.getElementById('comparisonBtn').disabled = true;
        
        // Destroy charts
        Object.values(this.state.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.state.charts = {};
    }
    
    // Modal Management
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
        }
    }
    
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    // Loading and Notification Management
    showLoading(message = 'Loading...') {
        const existingLoader = document.getElementById('loadingOverlay');
        if (existingLoader) return;
        
        const loader = document.createElement('div');
        loader.id = 'loadingOverlay';
        loader.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            color: white;
            font-size: 1.2rem;
        `;
        loader.innerHTML = `
            <div class="text-center">
                <div class="loading-spinner">
                    <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                </div>
                <div>${message}</div>
            </div>
        `;
        document.body.appendChild(loader);
    }
    
    hideLoading() {
        const loader = document.getElementById('loadingOverlay');
        if (loader) {
            loader.remove();
        }
    }
    
    showNotification(type, message, duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            max-width: 400px;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            color: white;
            font-weight: 500;
        `;
        
        // Set background color based on type
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; color: white; font-size: 1.2rem; cursor: pointer; margin-left: 1rem;">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => notification.style.transform = 'translateX(0)', 100);
        
        // Auto remove
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.parentElement.removeChild(notification);
                }
            }, 300);
        }, duration);
    }
}

// Initialize the application
window.demandVizApp = new DemandVisualizationApp();

// Global functions for template access
window.showNotification = function(type, message, duration) {
    return window.demandVizApp.showNotification(type, message, duration);
};

window.downloadChart = function(chartId) {
    return window.demandVizApp.downloadChart(chartId);
};

window.downloadTableAsCSV = function(tableId, filename) {
    return window.demandVizApp.downloadTableAsCSV(tableId, filename);
};