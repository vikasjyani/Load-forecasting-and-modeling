/**
 * Enhanced Demand Visualization Application
 * Dynamic sector/model handling with proper Chart.js 4.4.0 integration
 * FIXED: Scenarios loading and color management
 */

class DemandVisualizationApp {
    constructor() {
        this.API_BASE = '/demand_visualization/api';
        this.NOTIFICATION_DURATION = 5000;
        
        // Dynamic application state
        this.state = {
            scenarios: [],
            currentScenario: null,
            scenarioData: null,
            availableSectors: [],
            availableModels: [],
            currentSector: null,
            currentTab: 'sector-analysis',
            filters: {
                unit: null,
                startYear: null,
                endYear: null,
                selectedSectors: [],
                selectedModels: []
            },
            charts: {},
            isLoading: false,
            isComparisonMode: false,
            comparisonScenario: null,
            modelConfiguration: {},
            tdLossesConfiguration: [],
            consolidatedData: null,
            colorManager: null,
            filterManager: null
        };

        this.chartInstances = new Map();
        this.init();
    }

    // ========== INITIALIZATION ==========

    async init() {
        try {
            this.showLoading('Initializing application...');
            
            await this.waitForDependencies();
            await this.initializeColorManager();
            await this.initializeFilterManager();
            await this.loadInitialData();
            
            this.setupEventListeners();
            this.initializeUI();
            
            this.showNotification('success', 'Application initialized successfully');
        } catch (error) {
            console.error('Failed to initialize:', error);
            this.showNotification('error', 'Failed to initialize application: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async waitForDependencies() {
        const dependencies = [
            { name: 'Chart.js', check: () => typeof Chart !== 'undefined' && Chart.register },
            { name: 'ColorManager', check: () => window.colorManager },
            { name: 'Plot Utils', check: () => true } // Plot utils are backend-generated
        ];

        for (const dep of dependencies) {
            let attempts = 0;
            const maxAttempts = 50;
            
            while (!dep.check() && attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }
            
            if (!dep.check()) {
                throw new Error(`${dep.name} failed to load`);
            }
            
            console.log(`✓ ${dep.name} loaded successfully`);
        }
    }

    async initializeColorManager() {
        try {
            // Wait for colorManager to be available
            let attempts = 0;
            const maxAttempts = 10;
            
            while (!window.colorManager && attempts < maxAttempts) {
                console.log(`Waiting for colorManager... attempt ${attempts + 1}`);
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }
            
            if (window.colorManager) {
                this.state.colorManager = window.colorManager;
                
                // Wait for initialization if method exists
                if (typeof this.state.colorManager.waitForInitialization === 'function') {
                    await this.state.colorManager.waitForInitialization();
                }
                
                // Register for color change events if method exists
                if (typeof this.state.colorManager.registerColorChangeCallback === 'function') {
                    this.state.colorManager.registerColorChangeCallback((category, item, color) => {
                        this.handleColorChange(category, item, color);
                    });
                }
                
                console.log('✓ ColorManager initialized successfully');
            } else {
                console.warn('⚠️ ColorManager not available, using fallback colors');
                this.state.colorManager = null;
            }
        } catch (error) {
            console.error('Error initializing ColorManager:', error);
            this.state.colorManager = null;
        }
    }

    async initializeFilterManager() {
        this.state.filterManager = {
            filters: { ...this.state.filters },
            callbacks: new Set(),
            
            updateFilter: (key, value) => {
                console.log(`Filter update: ${key} = ${value}`);
                this.state.filters[key] = value;
                this.state.filterManager.filters[key] = value;
                this.applyFilters();
            },
            
            registerCallback: (callback) => {
                this.state.filterManager.callbacks.add(callback);
            }
        };
    }

    async loadInitialData() {
        await this.loadScenarios();
        this.populateScenarioSelect();
    }

    // ========== SCENARIO MANAGEMENT ==========

    async loadScenarios() {
        try {
            console.log('🔍 Loading scenarios from:', `${this.API_BASE}/scenarios`);
            
            const response = await fetch(`${this.API_BASE}/scenarios`);
            const result = await response.json();
            
            console.log('📦 Full API Response:', result);
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to load scenarios');
            }
            
            // FIX: Handle both response structures
            let scenarios = [];
            if (result.data && result.data.scenarios) {
                // New structure: result.data.scenarios
                scenarios = result.data.scenarios;
                console.log('✅ Using result.data.scenarios structure');
                console.log('📊 Total scenarios in data:', result.data.total_count);
                console.log('📈 Has data:', result.data.has_data);
            } else if (result.scenarios) {
                // Old structure: result.scenarios  
                scenarios = result.scenarios;
                console.log('✅ Using result.scenarios structure');
            } else {
                console.log('❌ No scenarios found in response structure:', Object.keys(result));
                console.log('🔍 Available keys in result:', Object.keys(result));
                if (result.data) {
                    console.log('🔍 Available keys in result.data:', Object.keys(result.data));
                }
                scenarios = [];
            }
            
            this.state.scenarios = scenarios;
            console.log(`✅ Final result: Loaded ${this.state.scenarios.length} scenarios`);
            
            // Debug each scenario
            this.state.scenarios.forEach((scenario, index) => {
                console.log(`📋 Scenario ${index + 1}:`, {
                    name: scenario.name,
                    sectors_count: scenario.sectors_count,
                    has_data: scenario.has_data,
                    file_count: scenario.file_count
                });
            });
            
        } catch (error) {
            console.error('❌ Error loading scenarios:', error);
            this.state.scenarios = [];
        }
    }

    populateScenarioSelect() {
        const select = document.getElementById('scenarioSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Choose a demand forecast scenario...</option>';
        
        this.state.scenarios.forEach(scenario => {
            const option = document.createElement('option');
            option.value = scenario.name;
            option.textContent = `${scenario.name} (${scenario.sectors_count} sectors)`;
            
            // Store metadata for dynamic access
            option.dataset.sectorsCount = scenario.sectors_count;
            option.dataset.fileCount = scenario.file_count;
            option.dataset.yearMin = scenario.year_range?.min || '';
            option.dataset.yearMax = scenario.year_range?.max || '';
            
            select.appendChild(option);
        });

        console.log(`📝 Populated scenario select with ${this.state.scenarios.length} options`);
    }

    async handleScenarioChange(scenarioName) {
        if (!scenarioName) {
            this.clearScenario();
            return;
        }

        try {
            this.showLoading(`Loading scenario: ${scenarioName}...`);
            this.state.currentScenario = scenarioName;
            
            await this.loadScenarioData(scenarioName);
            this.initializeFiltersFromData();
            this.populateDynamicUI();
            this.enableControls();
            this.switchTab('sector-analysis');
            
            this.showNotification('success', `Scenario "${scenarioName}" loaded successfully`);
        } catch (error) {
            console.error('Error loading scenario:', error);
            this.showNotification('error', 'Failed to load scenario: ' + error.message);
            this.clearScenario();
        } finally {
            this.hideLoading();
        }
    }

    async loadScenarioData(scenarioName) {
        try {
            const response = await fetch(`${this.API_BASE}/scenario/${encodeURIComponent(scenarioName)}`);
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to load scenario data');
            }
            
            this.state.scenarioData = result.data;
            
            // Extract dynamic information
            this.state.availableSectors = Object.keys(this.state.scenarioData.sectors || {});
            this.state.availableModels = this.extractAllModels();
            
            console.log(`Loaded scenario data:`, {
                sectors: this.state.availableSectors.length,
                models: this.state.availableModels.length,
                yearRange: this.state.scenarioData.year_range
            });
            
            await this.loadExistingConfigurations();
        } catch (error) {
            console.error('Error loading scenario data:', error);
            throw error;
        }
    }

    extractAllModels() {
        const allModels = new Set();
        Object.values(this.state.scenarioData.sectors || {}).forEach(sectorData => {
            if (sectorData.models) {
                sectorData.models.forEach(model => allModels.add(model));
            }
        });
        return Array.from(allModels);
    }

    async loadExistingConfigurations() {
        try {
            // Load model configuration
            const modelResponse = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`);
            const modelResult = await modelResponse.json();
            
            if (modelResult.success && modelResult.config?.model_selection) {
                this.state.modelConfiguration = modelResult.config.model_selection;
            }
            
            // Load T&D losses configuration
            const tdResponse = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`);
            const tdResult = await tdResponse.json();
            
            if (tdResult.success && tdResult.config?.td_losses) {
                this.state.tdLossesConfiguration = tdResult.config.td_losses;
            }
        } catch (error) {
            console.warn('Error loading existing configurations:', error);
        }
    }

    initializeFiltersFromData() {
        if (!this.state.scenarioData) return;

        const yearRange = this.state.scenarioData.year_range;
        
        // Set dynamic filter ranges
        this.state.filters.startYear = yearRange?.min;
        this.state.filters.endYear = yearRange?.max;
        this.state.filters.unit = this.state.scenarioData.unit || 'TWh';
        
        this.updateFilterUI();
    }

    updateFilterUI() {
        // Update unit selector
        const unitSelect = document.getElementById('unitSelect');
        if (unitSelect && this.state.filters.unit) {
            unitSelect.value = this.state.filters.unit;
        }

        // Update year selectors with dynamic ranges
        this.populateYearSelectors();
    }

    populateYearSelectors() {
        const startSelect = document.getElementById('startYearSelect');
        const endSelect = document.getElementById('endYearSelect');
        
        if (!startSelect || !endSelect || !this.state.scenarioData?.year_range) return;

        const { min, max } = this.state.scenarioData.year_range;
        const years = Array.from({ length: max - min + 1 }, (_, i) => min + i);

        [startSelect, endSelect].forEach(select => {
            select.innerHTML = '';
            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                select.appendChild(option);
            });
        });

        startSelect.value = this.state.filters.startYear;
        endSelect.value = this.state.filters.endYear;
    }

    populateDynamicUI() {
        this.populateSectorNavigation();
        this.populateColorSettings();
    }

    populateSectorNavigation() {
        const navbar = document.getElementById('sectorNavbar');
        const tabs = document.getElementById('sectorTabs');
        
        if (!navbar || !tabs || !this.state.availableSectors.length) return;

        tabs.innerHTML = '';
        
        this.state.availableSectors.forEach((sector, index) => {
            const tab = document.createElement('button');
            tab.className = `sector-tab ${index === 0 ? 'active' : ''}`;
            tab.dataset.sector = sector;
            tab.textContent = this.formatSectorName(sector);
            tab.addEventListener('click', () => this.switchSector(sector));
            tabs.appendChild(tab);
        });

        navbar.style.display = 'block';
        
        if (this.state.availableSectors.length > 0) {
            this.switchSector(this.state.availableSectors[0]);
        }
    }

    formatSectorName(sector) {
        return sector.replace(/_/g, ' ')
                    .replace(/([A-Z])/g, ' $1')
                    .trim()
                    .replace(/\b\w/g, l => l.toUpperCase());
    }

    // ========== SECTOR ANALYSIS ==========

    switchSector(sectorName) {
        this.state.currentSector = sectorName;
        
        // Update active tab
        document.querySelectorAll('.sector-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.sector === sectorName);
        });

        if (this.state.currentTab === 'sector-analysis') {
            this.updateSectorAnalysis();
        }
    }

    async updateSectorAnalysis() {
        if (!this.state.scenarioData || !this.state.currentSector) {
            this.showEmptyState();
            return;
        }

        try {
            this.showLoading('Loading sector analysis...');
            
            const sectorData = this.state.scenarioData.sectors[this.state.currentSector];
            if (!sectorData) {
                throw new Error(`Sector ${this.state.currentSector} not found`);
            }

            this.createSectorAnalysisLayout(sectorData);
            await this.createSectorChart(sectorData);
            
        } catch (error) {
            console.error('Error updating sector analysis:', error);
            this.showNotification('error', 'Failed to load sector analysis: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    createSectorAnalysisLayout(sectorData) {
        const content = document.getElementById('sectorContentArea');
        if (!content) return;

        const availableModels = sectorData.models || [];
        const yearRange = sectorData.years ? 
            `${Math.min(...sectorData.years)}-${Math.max(...sectorData.years)}` : 'N/A';

        content.innerHTML = `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">
                                <i class="fas fa-chart-line me-2"></i>
                                ${this.formatSectorName(this.state.currentSector)} Sector Analysis
                            </h6>
                            <div class="btn-group" role="group">
                                ${this.createChartTypeButtons()}
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="chart-wrapper">
                                <canvas id="sector-chart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                ${this.createMetricCards(sectorData, yearRange)}
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="fas fa-table me-2"></i>
                                Data Table
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="table-wrapper">
                                ${this.createSectorDataTable(sectorData)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    createChartTypeButtons() {
        const chartTypes = [
            { type: 'line', icon: 'fa-chart-line', label: 'Line' },
            { type: 'bar', icon: 'fa-chart-bar', label: 'Bar' },
            { type: 'area', icon: 'fa-chart-area', label: 'Area' }
        ];

        return chartTypes.map(({ type, icon, label }) => `
            <button type="button" class="btn btn-sm btn-outline-primary chart-type-btn" 
                    data-chart-type="${type}" onclick="demandVizApp.changeChartType('${type}')">
                <i class="fas ${icon} me-1"></i>${label}
            </button>
        `).join('');
    }

    createMetricCards(sectorData, yearRange) {
        return `
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">${sectorData.models?.length || 0}</div>
                    <div class="metric-label">Models Available</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">${sectorData.years?.length || 0}</div>
                    <div class="metric-label">Data Points</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">${yearRange}</div>
                    <div class="metric-label">Year Range</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">${this.state.filters.unit}</div>
                    <div class="metric-label">Unit</div>
                </div>
            </div>
        `;
    }

    createSectorDataTable(sectorData) {
        if (!sectorData.years || !sectorData.models) {
            return '<p class="text-muted">No data available</p>';
        }

        const filteredData = this.applyFiltersToSectorData(sectorData);
        
        if (!filteredData.years.length) {
            return '<p class="text-muted">No data available for selected filters</p>';
        }

        let html = `
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Year</th>
                        ${filteredData.models.map(model => `<th>${model}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
        `;

        filteredData.years.forEach((year, index) => {
            html += `<tr><td><strong>${year}</strong></td>`;
            filteredData.models.forEach(model => {
                const value = filteredData[model] && filteredData[model][index] !== undefined
                    ? filteredData[model][index].toFixed(3)
                    : '0.000';
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    }

    applyFiltersToSectorData(sectorData) {
        let filteredData = JSON.parse(JSON.stringify(sectorData));
        
        // Apply year filters
        if (this.state.filters.startYear || this.state.filters.endYear) {
            const filteredIndices = [];
            const filteredYears = [];
            
            sectorData.years.forEach((year, index) => {
                const yearNum = parseInt(year);
                const passesStart = !this.state.filters.startYear || yearNum >= this.state.filters.startYear;
                const passesEnd = !this.state.filters.endYear || yearNum <= this.state.filters.endYear;
                
                if (passesStart && passesEnd) {
                    filteredIndices.push(index);
                    filteredYears.push(year);
                }
            });
            
            filteredData.years = filteredYears;
            
            // Filter model data
            filteredData.models.forEach(model => {
                if (sectorData[model]) {
                    filteredData[model] = filteredIndices.map(i => sectorData[model][i]);
                }
            });
        }

        return filteredData;
    }

    async createSectorChart(sectorData, chartType = 'line') {
        const canvasId = 'sector-chart';
        
        try {
            // Validate required parameters
            if (!this.state.currentScenario) {
                throw new Error('No scenario selected');
            }
            if (!this.state.currentSector) {
                throw new Error('No sector selected');
            }
            
            // Get chart data from backend using plot_utils
            const params = new URLSearchParams({
                chart_type: chartType,
                unit: this.state.filters.unit || 'MW',
                ...(this.state.filters.startYear && { start_year: this.state.filters.startYear }),
                ...(this.state.filters.endYear && { end_year: this.state.filters.endYear })
            });

            console.log(`Creating chart for ${this.state.currentSector} with params:`, Object.fromEntries(params));

            const response = await fetch(
                `${this.API_BASE}/chart/sector/${this.state.currentScenario}/${this.state.currentSector}?${params}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();

            if (result.success && result.chart_data) {
                this.renderChart(canvasId, result.chart_data);
                console.log(`✓ Chart created for ${this.state.currentSector} (${chartType})`);
            } else {
                throw new Error(result.error || result.message || 'Failed to generate chart data');
            }
            
        } catch (error) {
            console.error('Error creating sector chart:', error);
            this.renderErrorChart(canvasId, `Chart Error: ${error.message}`);
            this.showNotification('error', `Failed to create chart: ${error.message}`);
        }
    }

    changeChartType(chartType) {
        // Update active button
        document.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.chartType === chartType);
        });
        
        if (this.state.currentSector && this.state.scenarioData?.sectors[this.state.currentSector]) {
            this.createSectorChart(this.state.scenarioData.sectors[this.state.currentSector], chartType);
        }
    }

    // ========== CHART MANAGEMENT ==========

    renderChart(canvasId, chartConfig) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas element '${canvasId}' not found`);
            return;
        }

        // Destroy existing chart
        this.destroyChart(canvasId);

        try {
            // Ensure Chart.js is available
            if (typeof Chart === 'undefined') {
                throw new Error('Chart.js is not loaded');
            }

            // Validate chart configuration
            if (!chartConfig || !chartConfig.type || !chartConfig.data) {
                throw new Error('Invalid chart configuration');
            }

            // Enhance configuration with dynamic colors
            this.enhanceChartConfigWithColors(chartConfig);

            // Create new chart
            this.chartInstances.set(canvasId, new Chart(canvas, chartConfig));
            console.log(`✓ Chart '${canvasId}' created successfully`);
            
        } catch (error) {
            console.error(`Error creating chart '${canvasId}':`, error);
            this.renderErrorChart(canvasId, error.message);
        }
    }

    enhanceChartConfigWithColors(chartConfig) {
        if (!chartConfig.data?.datasets) return;

        // Fallback colors if colorManager is not available
        const fallbackColors = [
            '#2563EB', '#059669', '#DC2626', '#7C3AED', 
            '#EA580C', '#16A34A', '#6B7280', '#F59E0B'
        ];

        chartConfig.data.datasets.forEach((dataset, index) => {
            const label = dataset.label || '';
            let color;

            // Try to get color from colorManager with proper error handling
            if (this.state.colorManager && 
                typeof this.state.colorManager.getModelColor === 'function') {
                try {
                    color = this.state.colorManager.getModelColor(label) ||
                           this.state.colorManager.getSectorColor(label.toLowerCase()) ||
                           (typeof this.state.colorManager.getChartColors === 'function' ? 
                            this.state.colorManager.getChartColors(1)[0] : null);
                } catch (error) {
                    console.warn('ColorManager error, using fallback:', error);
                    color = null;
                }
            }

            // Use fallback color if colorManager failed or is unavailable
            if (!color) {
                color = fallbackColors[index % fallbackColors.length];
            }

            // Apply colors based on chart type
            dataset.borderColor = color;
            dataset.backgroundColor = this.addTransparency(color, 
                chartConfig.type === 'bar' ? 0.8 : 
                chartConfig.type === 'area' ? 0.3 : 0.1);

            // Additional styling for different chart types
            if (chartConfig.type === 'line') {
                dataset.pointBackgroundColor = color;
                dataset.pointBorderColor = '#FFFFFF';
                dataset.pointBorderWidth = 2;
                dataset.pointRadius = 4;
                dataset.pointHoverRadius = 6;
            } else if (chartConfig.type === 'bar') {
                dataset.borderRadius = 4;
                dataset.borderSkipped = false;
            }
        });
    }

    destroyChart(canvasId) {
        if (this.chartInstances.has(canvasId)) {
            try {
                this.chartInstances.get(canvasId).destroy();
            } catch (error) {
                console.warn(`Error destroying chart ${canvasId}:`, error);
            }
            this.chartInstances.delete(canvasId);
        }
    }

    renderErrorChart(canvasId, errorMessage) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#EF4444';
        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Chart Error', canvas.width / 2, canvas.height / 2 - 10);
        ctx.fillStyle = '#6B7280';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText(errorMessage, canvas.width / 2, canvas.height / 2 + 10);
    }

    // ========== FILTER MANAGEMENT ==========

    async applyFilters() {
        if (!this.state.currentScenario) return;

        console.log('Applying filters:', this.state.filters);

        try {
            this.showLoading('Applying filters...');

            // Update current view based on active tab
            switch (this.state.currentTab) {
                case 'sector-analysis':
                    if (this.state.currentSector) {
                        await this.updateSectorAnalysis();
                    }
                    break;
                case 'consolidated-results':
                    await this.updateConsolidatedResults();
                    break;
                case 'comparison':
                    if (this.state.isComparisonMode) {
                        await this.updateComparison();
                    }
                    break;
            }

            // Notify filter callbacks
            this.state.filterManager.callbacks.forEach(callback => {
                try {
                    callback(this.state.filters);
                } catch (error) {
                    console.warn('Filter callback error:', error);
                }
            });

        } catch (error) {
            console.error('Error applying filters:', error);
            this.showNotification('error', 'Failed to apply filters');
        } finally {
            this.hideLoading();
        }
    }

    handleFilterChange(filterId, value) {
        switch (filterId) {
            case 'unitSelect':
                this.state.filterManager.updateFilter('unit', value);
                break;
            case 'startYearSelect':
                this.state.filterManager.updateFilter('startYear', parseInt(value));
                break;
            case 'endYearSelect':
                this.state.filterManager.updateFilter('endYear', parseInt(value));
                break;
        }
    }

    // ========== TAB MANAGEMENT ==========

    switchTab(tabId) {
        this.state.currentTab = tabId;
        
        // Update active tab
        document.querySelectorAll('.analysis-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });

        // Show/hide content sections
        this.updateContentVisibility(tabId);
        
        // Update content based on tab
        switch (tabId) {
            case 'sector-analysis':
                this.updateSectorAnalysis();
                break;
            case 'td-losses':
                this.updateTdLosses();
                break;
            case 'consolidated-results':
                this.updateConsolidatedResults();
                break;
            case 'comparison':
                this.updateComparison();
                break;
        }
    }

    updateContentVisibility(activeTab) {
        const sections = {
            'sector-analysis': 'sectorAnalysisContent',
            'td-losses': 'tdLossesContent',
            'consolidated-results': 'consolidatedResultsContent',
            'comparison': 'comparisonContent'
        };

        // Show sector navbar only for sector analysis
        const navbar = document.getElementById('sectorNavbar');
        if (navbar) {
            navbar.style.display = activeTab === 'sector-analysis' ? 'block' : 'none';
        }

        // Show/hide content sections
        Object.entries(sections).forEach(([tabId, sectionId]) => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = tabId === activeTab ? 'block' : 'none';
            }
        });
    }

    // ========== T&D LOSSES MANAGEMENT ==========

    async updateTdLosses() {
        try {
            if (!this.state.currentScenario) {
                console.warn('No current scenario selected for T&D losses');
                return;
            }
            
            this.showLoading('Loading T&D losses configuration...');
            
            const response = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Backend returns result.config.td_losses (wrapped in config object)
            const tdLosses = result.success ? (result.config?.td_losses || []) : [];
            this.state.tdLossesConfiguration = tdLosses;
            this.renderTdLossesForm(tdLosses);
            
        } catch (error) {
            console.error('Error loading T&D losses:', error);
            this.showNotification('error', 'Failed to load T&D losses configuration');
            // Initialize with default data on error
            this.state.tdLossesConfiguration = [{ year: 2025, loss_percentage: 10.0 }];
            this.renderTdLossesForm(this.state.tdLossesConfiguration);
        } finally {
            this.hideLoading();
        }
    }

    renderTdLossesForm(tdLosses) {
        const formContainer = document.getElementById('tdLossesForm');
        if (!formContainer) return;

        const validatedLosses = Array.isArray(tdLosses) && tdLosses.length > 0 ? 
            tdLosses : [{ year: 2025, loss_percentage: 10.0 }];

        formContainer.innerHTML = validatedLosses.map((loss, index) => `
            <div class="td-loss-entry mb-3" data-index="${index}">
                <div class="row">
                    <div class="col-4">
                        <label class="form-label">Year</label>
                        <input type="number" class="form-control" value="${loss.year}" 
                               onchange="demandVizApp.updateTdLoss(${index}, 'year', this.value)">
                    </div>
                    <div class="col-4">
                        <label class="form-label">Loss %</label>
                        <input type="number" class="form-control" value="${loss.loss_percentage}" 
                               step="0.1" onchange="demandVizApp.updateTdLoss(${index}, 'loss_percentage', this.value)">
                    </div>
                    <div class="col-4">
                        <label class="form-label">&nbsp;</label>
                        <div>
                            <button type="button" class="btn btn-outline-danger" 
                                    onclick="demandVizApp.removeTdLoss(${index})" 
                                    ${validatedLosses.length <= 1 ? 'disabled' : ''}>
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        this.createTdLossesChart(validatedLosses);
    }

    async createTdLossesChart(tdLosses) {
        if (!Array.isArray(tdLosses) || tdLosses.length === 0) return;

        try {
            // Get chart data from backend using plot_utils
            const response = await fetch(`${this.API_BASE}/chart/td-losses/${this.state.currentScenario}`);
            const result = await response.json();

            if (result.success && result.chart_data) {
                this.renderChart('tdLossesChart', result.chart_data);
            } else {
                // Fallback to client-side rendering
                this.createClientSideTdLossesChart(tdLosses);
            }
        } catch (error) {
            console.warn('Backend T&D chart failed, using client-side:', error);
            this.createClientSideTdLossesChart(tdLosses);
        }
    }

    createClientSideTdLossesChart(tdLosses) {
        const sortedLosses = [...tdLosses].sort((a, b) => a.year - b.year);
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: sortedLosses.map(l => l.year),
                datasets: [{
                    label: 'T&D Losses (%)',
                    data: sortedLosses.map(l => l.loss_percentage),
                    borderColor: '#dc2626',
                    backgroundColor: this.addTransparency('#dc2626', 0.1),
                    borderWidth: 2,
                    tension: 0.2,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#FFFFFF',
                    pointBorderColor: '#dc2626',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'T&D Losses Configuration'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Loss Percentage (%)'
                        }
                    }
                }
            }
        };

        this.renderChart('tdLossesChart', chartConfig);
    }

    updateTdLoss(index, field, value) {
        if (!this.state.tdLossesConfiguration[index]) return;

        this.state.tdLossesConfiguration[index][field] = 
            field === 'year' ? parseInt(value) : parseFloat(value);
        
        this.createTdLossesChart(this.state.tdLossesConfiguration);
    }

    addTdLossEntry() {
        const currentEntries = this.state.tdLossesConfiguration || [];
        const newYear = currentEntries.length > 0 ? 
            Math.max(...currentEntries.map(e => e.year)) + 5 : 2025;
        
        this.state.tdLossesConfiguration.push({
            year: newYear,
            loss_percentage: 10.0
        });
        
        this.renderTdLossesForm(this.state.tdLossesConfiguration);
    }

    removeTdLoss(index) {
        if (this.state.tdLossesConfiguration.length <= 1) {
            this.showNotification('warning', 'At least one T&D loss entry is required');
            return;
        }

        this.state.tdLossesConfiguration.splice(index, 1);
        this.renderTdLossesForm(this.state.tdLossesConfiguration);
    }

    async saveTdLosses() {
        try {
            if (!this.state.tdLossesConfiguration || this.state.tdLossesConfiguration.length === 0) {
                this.showNotification('warning', 'Please add at least one T&D loss entry');
                return;
            }

            this.showLoading('Saving T&D losses...');

            const response = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ td_losses: this.state.tdLossesConfiguration })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('success', 'T&D losses saved successfully');
            } else {
                throw new Error(result.error || 'Failed to save T&D losses');
            }
        } catch (error) {
            console.error('Error saving T&D losses:', error);
            this.showNotification('error', 'Failed to save T&D losses');
        } finally {
            this.hideLoading();
        }
    }

    // ========== CONSOLIDATED RESULTS ==========

    async updateConsolidatedResults() {
        try {
            this.showLoading('Loading consolidated configuration...');
            
            // Check configurations
            const [modelResponse, tdResponse] = await Promise.all([
                fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`),
                fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`)
            ]);

            const modelResult = await modelResponse.json();
            const tdResult = await tdResponse.json();

            this.renderConsolidatedStatus(modelResult, tdResult);
            
        } catch (error) {
            console.error('Error loading consolidated status:', error);
            this.showNotification('error', 'Failed to load consolidated configuration');
        } finally {
            this.hideLoading();
        }
    }

    renderConsolidatedStatus(modelResult, tdResult) {
        const summaryContainer = document.getElementById('consolidatedSummary');
        if (!summaryContainer) return;

        const hasModelSelection = modelResult.success && modelResult.config && 
            Object.keys(modelResult.config.model_selection || {}).length > 0;
        const hasTdLosses = tdResult.success && tdResult.config && 
            Array.isArray(tdResult.config.td_losses) && tdResult.config.td_losses.length > 0;
        const canGenerate = hasModelSelection && hasTdLosses;

        summaryContainer.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card ${hasModelSelection ? 'border-success' : 'border-warning'}">
                        <div class="card-header">
                            <h6>
                                <i class="fas ${hasModelSelection ? 'fa-check-circle text-success' : 'fa-exclamation-triangle text-warning'} me-2"></i>
                                Model Selection
                            </h6>
                        </div>
                        <div class="card-body">
                            <p>Status: <span class="badge ${hasModelSelection ? 'bg-success' : 'bg-warning'}">${hasModelSelection ? 'Complete' : 'Incomplete'}</span></p>
                            ${hasModelSelection ? `<p class="text-muted small">Models configured for ${Object.keys(modelResult.config.model_selection).length} sectors</p>` : ''}
                            <button class="btn btn-outline-primary btn-sm" onclick="demandVizApp.openModelSelectionModal()">
                                <i class="fas fa-cogs me-1"></i>Configure
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card ${hasTdLosses ? 'border-success' : 'border-warning'}">
                        <div class="card-header">
                            <h6>
                                <i class="fas ${hasTdLosses ? 'fa-check-circle text-success' : 'fa-exclamation-triangle text-warning'} me-2"></i>
                                T&D Losses
                            </h6>
                        </div>
                        <div class="card-body">
                            <p>Status: <span class="badge ${hasTdLosses ? 'bg-success' : 'bg-warning'}">${hasTdLosses ? 'Complete' : 'Incomplete'}</span></p>
                            ${hasTdLosses ? `<p class="text-muted small">${tdResult.config.td_losses.length} loss points configured</p>` : ''}
                            <button class="btn btn-outline-primary btn-sm" onclick="demandVizApp.switchTab('td-losses')">
                                <i class="fas fa-chart-line me-1"></i>Configure
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="text-center">
                <button class="btn ${canGenerate ? 'btn-success' : 'btn-secondary'} btn-lg" 
                        ${canGenerate ? '' : 'disabled'} 
                        onclick="demandVizApp.generateConsolidated()">
                    <i class="fas fa-calculator me-2"></i>Generate Consolidated Results
                </button>
                ${!canGenerate ? '<p class="text-muted mt-2">Complete model selection and T&D losses configuration first</p>' : ''}
            </div>
        `;
    }

    async generateConsolidated() {
        try {
            this.showLoading('Generating consolidated results...');
            
            if (!this.state.modelConfiguration || Object.keys(this.state.modelConfiguration).length === 0) {
                throw new Error('Model selection configuration required');
            }
            
            if (!this.state.tdLossesConfiguration || this.state.tdLossesConfiguration.length === 0) {
                throw new Error('T&D losses configuration required');
            }
            
            const backendFilters = {
                unit: this.state.filters.unit,
                start_year: this.state.filters.startYear,
                end_year: this.state.filters.endYear
            };
            
            const response = await fetch(`${this.API_BASE}/consolidated/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_selection: this.state.modelConfiguration,
                    td_losses: this.state.tdLossesConfiguration,
                    filters: backendFilters
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.state.consolidatedData = result.data;
                this.showNotification('success', 'Consolidated results generated successfully');
                this.displayConsolidatedResults(result.data);
            } else {
                throw new Error(result.error || 'Failed to generate results');
            }
        } catch (error) {
            console.error('Error generating consolidated results:', error);
            this.showNotification('error', 'Error generating consolidated results: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayConsolidatedResults(data) {
        const resultsDiv = document.getElementById('consolidatedResults');
        if (!resultsDiv || !data) return;

        // Create comprehensive electricity industry layout
        resultsDiv.innerHTML = this.createConsolidatedResultsLayout();
        resultsDiv.style.display = 'block';
        
        // Generate all charts using backend plot_utils
        this.createAllConsolidatedCharts(data);
    }

    createConsolidatedResultsLayout() {
        return `
            <div class="mt-4">
                <!-- Primary Stacked Chart for Sectoral Breakdown -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-chart-area me-2"></i>
                            Sectoral Electricity Demand Breakdown
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="chart-wrapper">
                            <canvas id="stackedDemandChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Secondary Charts Grid -->
                <div class="content-grid two-col mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="fas fa-chart-line me-2"></i>
                                Gross vs Net Demand
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="chart-wrapper">
                                <canvas id="grossNetChart"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="fas fa-chart-bar me-2"></i>
                                T&D Losses Analysis
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="chart-wrapper">
                                <canvas id="tdLossesAnalysisChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Individual Sector Trends -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-chart-line me-2"></i>
                            Individual Sector Growth Trends
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="chart-wrapper">
                            <canvas id="sectorTrendsChart"></canvas>
                        </div>
                    </div>
                </div>
                
                <!-- Consolidated Data Table -->
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-table me-2"></i>
                            Consolidated Electricity Data
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="table-wrapper">
                            <div id="consolidatedDataTable"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async createAllConsolidatedCharts(consolidatedData) {
        if (!consolidatedData?.consolidated_data) return;

        try {
            // Get all consolidated charts from backend using plot_utils
            const chartRequests = [
                { id: 'stackedDemandChart', type: 'stacked_bar' },
                { id: 'grossNetChart', type: 'gross_net_comparison' },
                { id: 'tdLossesAnalysisChart', type: 'td_losses_analysis' },
                { id: 'sectorTrendsChart', type: 'sector_trends' }
            ];

            for (const { id, type } of chartRequests) {
                try {
                    const response = await fetch(`${this.API_BASE}/chart/consolidated/${this.state.currentScenario}?chart_type=${type}&unit=${this.state.filters.unit}`);
                    const result = await response.json();
                    
                    if (result.success && result.chart_data) {
                        this.renderChart(id, result.chart_data);
                    } else {
                        console.warn(`Failed to load ${type} chart:`, result.error);
                    }
                } catch (error) {
                    console.warn(`Error loading ${type} chart:`, error);
                }
            }

            // Create data table
            this.createConsolidatedDataTable(consolidatedData.consolidated_data);

        } catch (error) {
            console.error('Error creating consolidated charts:', error);
        }
    }

    createConsolidatedDataTable(data) {
        const tableContainer = document.getElementById('consolidatedDataTable');
        if (!tableContainer || !Array.isArray(data) || data.length === 0) return;

        // Define column order for electricity industry standard
        const yearColumn = 'Year';
        const sectorColumns = Object.keys(data[0]).filter(key => 
            !['Year', 'Total_Gross_Demand', 'Total_Net_Demand', 'TD_Losses', 'Loss_Percentage'].includes(key)
        );
        const summaryColumns = ['Total_Gross_Demand', 'TD_Losses', 'Total_Net_Demand', 'Loss_Percentage'];
        const orderedColumns = [yearColumn, ...sectorColumns, ...summaryColumns];

        let html = `
            <table class="table table-striped table-hover table-sm">
                <thead class="table-dark">
                    <tr>
                        ${orderedColumns.map(key => {
                            let displayName = this.formatColumnName(key);
                            return `<th class="${key === 'Year' ? 'fw-bold' : ''}">${displayName}</th>`;
                        }).join('')}
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach(row => {
            html += '<tr>';
            orderedColumns.forEach(key => {
                const value = row[key];
                let formattedValue = this.formatTableValue(key, value);
                html += `<td class="${key === 'Year' ? 'fw-bold' : ''}">${formattedValue}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        tableContainer.innerHTML = html;
    }

    formatColumnName(key) {
        const columnNames = {
            'Total_Gross_Demand': 'Total Gross',
            'Total_Net_Demand': 'Total Net',
            'TD_Losses': 'T&D Losses',
            'Loss_Percentage': 'Loss %'
        };

        return columnNames[key] || key.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim();
    }

    formatTableValue(key, value) {
        if (key === 'Year') {
            return `<strong>${value}</strong>`;
        } else if (key === 'Loss_Percentage') {
            return typeof value === 'string' ? value : `${parseFloat(value || 0).toFixed(2)}%`;
        } else if (typeof value === 'number') {
            return value.toFixed(3);
        } else {
            return value || '0.000';
        }
    }

    // ========== MODAL MANAGEMENT ==========

    openModelSelectionModal() {
        if (!this.state.scenarioData) {
            this.showNotification('warning', 'Please load a scenario first');
            return;
        }
        
        this.populateModelSelectionModal();
        this.showModal('modelSelectionModal');
    }

    populateModelSelectionModal() {
        const content = document.getElementById('modelSelectionContent');
        if (!content || !this.state.availableSectors.length) return;

        let html = '';

        this.state.availableSectors.forEach(sector => {
            const sectorData = this.state.scenarioData.sectors[sector];
            const currentSelection = this.state.modelConfiguration[sector] || '';

            html += `
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0">${this.formatSectorName(sector)}</h6>
                    </div>
                    <div class="card-body">
                        <select class="form-select" data-sector="${sector}">
                            <option value="">Select model...</option>
                            ${sectorData.models.map(model => 
                                `<option value="${model}" ${model === currentSelection ? 'selected' : ''}>${model}</option>`
                            ).join('')}
                        </select>
                        ${currentSelection ? `<small class="text-muted">Currently selected: ${currentSelection}</small>` : ''}
                    </div>
                </div>
            `;
        });

        content.innerHTML = html;

        // Add event listeners
        content.querySelectorAll('select').forEach(select => {
            select.addEventListener('change', (e) => {
                const sector = e.target.dataset.sector;
                const model = e.target.value;
                if (model) {
                    this.state.modelConfiguration[sector] = model;
                } else {
                    delete this.state.modelConfiguration[sector];
                }
            });
        });
    }

    async saveModelConfiguration() {
        try {
            const hasAllModels = this.state.availableSectors.every(sector => 
                this.state.modelConfiguration[sector]
            );

            if (!hasAllModels) {
                this.showNotification('warning', 'Please select models for all sectors');
                return;
            }

            this.showLoading('Saving model configuration...');

            const response = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_selection: this.state.modelConfiguration })
            });

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Failed to save model configuration');
            }

            this.hideModal('modelSelectionModal');
            this.showNotification('success', 'Model configuration saved successfully');

        } catch (error) {
            console.error('Error saving model configuration:', error);
            this.showNotification('error', 'Failed to save model configuration: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    // ========== COLOR MANAGEMENT ==========

    handleColorChange(category, item, color) {
        console.log(`Color changed: ${category}.${item} = ${color}`);
        // Refresh charts with new colors
        this.refreshChartsWithNewColors();
    }

    async refreshChartsWithNewColors() {
        console.log('Refreshing charts with new colors...');
        
        // Get all active chart IDs
        const activeCharts = Array.from(this.chartInstances.keys());
        
        for (const chartId of activeCharts) {
            await this.recreateChartWithNewColors(chartId);
        }
    }

    async recreateChartWithNewColors(chartId) {
        const existingChart = this.chartInstances.get(chartId);
        if (!existingChart) return;

        try {
            // Get current configuration
            const currentConfig = {
                type: existingChart.config.type,
                data: JSON.parse(JSON.stringify(existingChart.data)),
                options: JSON.parse(JSON.stringify(existingChart.options))
            };

            // Update colors in datasets
            this.enhanceChartConfigWithColors(currentConfig);

            // Recreate chart
            this.renderChart(chartId, currentConfig);
        } catch (error) {
            console.warn(`Failed to recreate chart ${chartId} with new colors:`, error);
        }
    }

    populateColorSettings() {
        // Populate sector colors
        const sectorGrid = document.getElementById('sectorColorsGrid');
        if (sectorGrid && this.state.availableSectors.length && this.state.colorManager) {
            const sectorColors = this.state.colorManager.getSectorColors(this.state.availableSectors);
            
            sectorGrid.innerHTML = this.state.availableSectors.map(sector => `
                <div class="color-config-item">
                    <label class="form-label">${this.formatSectorName(sector)}</label>
                    <input type="color" class="form-control form-control-color" 
                           value="${sectorColors[sector] || '#2563eb'}" 
                           onchange="demandVizApp.updateSectorColor('${sector}', this.value)">
                </div>
            `).join('');
        }

        // Populate model colors
        const modelGrid = document.getElementById('modelColorsGrid');
        if (modelGrid && this.state.availableModels.length && this.state.colorManager) {
            const modelColors = this.state.colorManager.getModelColors(this.state.availableModels);
            
            modelGrid.innerHTML = this.state.availableModels.map(model => `
                <div class="color-config-item">
                    <label class="form-label">${model}</label>
                    <input type="color" class="form-control form-control-color" 
                           value="${modelColors[model] || '#2563eb'}" 
                           onchange="demandVizApp.updateModelColor('${model}', this.value)">
                </div>
            `).join('');
        }
    }

    async updateSectorColor(sector, color) {
        try {
            await this.state.colorManager.updateColor('sectors', sector, color);
            this.showNotification('success', `Updated color for ${this.formatSectorName(sector)}`);
        } catch (error) {
            console.error('Error updating sector color:', error);
            this.showNotification('error', 'Failed to update sector color');
        }
    }

    async updateModelColor(model, color) {
        try {
            await this.state.colorManager.updateColor('models', model, color);
            this.showNotification('success', `Updated color for ${model} model`);
        } catch (error) {
            console.error('Error updating model color:', error);
            this.showNotification('error', 'Failed to update model color');
        }
    }

    openColorSettingsModal() {
        if (!this.state.colorManager) {
            this.showNotification('warning', 'Color manager not available');
            return;
        }
        
        this.populateColorSettings();
        this.showModal('colorSettingsModal');
    }

    // ========== UTILITY FUNCTIONS ==========

    addTransparency(color, alpha) {
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return color;
    }

    showEmptyState() {
        const content = document.getElementById('sectorContentArea');
        if (content) {
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-line fa-4x text-muted mb-4"></i>
                    <h5>Select a Scenario to Begin Analysis</h5>
                    <p>Choose a demand forecast scenario from the dropdown above to start exploring sector-wise
                        demand data and forecasting models.</p>
                </div>
            `;
        }
    }

    clearScenario() {
        this.state.currentScenario = null;
        this.state.scenarioData = null;
        this.state.availableSectors = [];
        this.state.availableModels = [];
        this.state.currentSector = null;
        this.state.modelConfiguration = {};
        this.state.tdLossesConfiguration = [];
        this.state.consolidatedData = null;
        
        // Destroy all charts
        this.chartInstances.forEach((chart, id) => {
            this.destroyChart(id);
        });

        // Hide sections and disable controls
        ['sectorNavbar', 'tdLossesContent', 'consolidatedResultsContent', 'comparisonContent'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });

        ['modelSelectionBtn', 'compareScenarioBtn', 'colorSettingsBtn', 'exportDataBtn', 'exportChartBtn'].forEach(id => {
            const button = document.getElementById(id);
            if (button) button.disabled = true;
        });

        this.showEmptyState();
    }

    enableControls() {
        ['modelSelectionBtn', 'compareScenarioBtn', 'colorSettingsBtn', 'exportDataBtn', 'exportChartBtn'].forEach(id => {
            const button = document.getElementById(id);
            if (button) button.disabled = false;
        });
    }

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            modal.style.display = 'flex';
        }
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
    }

    showLoading(message = 'Loading...') {
        let overlay = document.getElementById('loadingOverlay');
        if (!overlay) {
            overlay = this.createLoadingOverlay();
        }
        
        const spinner = overlay.querySelector('.loading-spinner div');
        if (spinner) spinner.textContent = message;
        overlay.style.display = 'flex';
    }

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.style.display = 'none';
    }

    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.5); display: flex; justify-content: center;
            align-items: center; z-index: 9999;
        `;
        overlay.innerHTML = `
            <div class="loading-spinner" style="text-align: center; color: white;">
                <i class="fas fa-spinner fa-spin fa-3x mb-3"></i>
                <div>Loading...</div>
            </div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }

    showNotification(type, message, duration = this.NOTIFICATION_DURATION) {
        document.querySelectorAll('.notification').forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; padding: 12px 20px;
            border-radius: 6px; color: white; z-index: 10000; max-width: 400px;
            font-size: 14px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transform: translateX(100%); transition: transform 0.3s ease;
            ${this.getNotificationStyle(type)}
        `;
        
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span><i class="fas ${this.getNotificationIcon(type)} me-2"></i>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; color: inherit; font-size: 1.2rem; cursor: pointer; margin-left: 1rem;">&times;</button>
            </div>
        `;

        document.body.appendChild(notification);
        setTimeout(() => notification.style.transform = 'translateX(0)', 100);
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    getNotificationStyle(type) {
        const styles = {
            success: 'background: #10B981;',
            error: 'background: #EF4444;',
            warning: 'background: #F59E0B;',
            info: 'background: #3B82F6;'
        };
        return styles[type] || styles.info;
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-triangle',
            warning: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    // ========== EVENT SETUP ==========

    setupEventListeners() {
        // Scenario selection
        const scenarioSelect = document.getElementById('scenarioSelect');
        if (scenarioSelect) {
            scenarioSelect.addEventListener('change', (e) => this.handleScenarioChange(e.target.value));
        }

        // Filters
        ['unitSelect', 'startYearSelect', 'endYearSelect'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', (e) => this.handleFilterChange(id, e.target.value));
            }
        });

        // Analysis tabs
        document.querySelectorAll('.analysis-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabId = e.target.dataset.tab || e.target.closest('.analysis-tab').dataset.tab;
                if (tabId) this.switchTab(tabId);
            });
        });

        // Action buttons
        this.setupActionButtons();
        
        // Modal handlers
        this.setupModalHandlers();
        
        // Window resize
        window.addEventListener('resize', () => this.handleResize());
    }

    setupActionButtons() {
        const buttons = {
            'modelSelectionBtn': () => this.openModelSelectionModal(),
            'colorSettingsBtn': () => this.openColorSettingsModal(),
            'saveTdLossesBtn': () => this.saveTdLosses(),
            'addTdLossBtn': () => this.addTdLossEntry(),
            'saveModelSelection': () => this.saveModelConfiguration(),
            'generateConsolidatedBtn': () => this.generateConsolidated()
        };

        Object.entries(buttons).forEach(([id, handler]) => {
            const button = document.getElementById(id);
            if (button) {
                button.removeEventListener('click', handler);
                button.addEventListener('click', handler);
            }
        });
    }

    setupModalHandlers() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                this.hideModal(e.target.id);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal-overlay.show');
                if (openModal) this.hideModal(openModal.id);
            }
        });
    }

    handleResize() {
        this.chartInstances.forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }

    initializeUI() {
        // Hide sections initially
        ['sectorNavbar', 'tdLossesContent', 'consolidatedResultsContent', 'comparisonContent'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });

        // Disable buttons initially  
        ['modelSelectionBtn', 'compareScenarioBtn', 'colorSettingsBtn', 'exportDataBtn', 'exportChartBtn'].forEach(id => {
            const button = document.getElementById(id);
            if (button) button.disabled = true;
        });

        this.showEmptyState();
    }

    // ========== COMPARISON (Placeholder) ==========
    
    updateComparison() {
        const content = document.getElementById('comparisonContainer');
        if (content) {
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-balance-scale fa-4x text-muted mb-4"></i>
                    <h5>Comparison Mode</h5>
                    <p>Scenario comparison functionality will be implemented here.</p>
                </div>
            `;
        }
    }

    // ========== DEBUG METHODS ==========
    
    async debugApiCall() {
        try {
            console.log('🔍 Direct API test...');
            const response = await fetch('/demand_visualization/api/scenarios');
            const text = await response.text();
            console.log('📄 Raw response text:', text);
            
            try {
                const json = JSON.parse(text);
                console.log('📦 Parsed JSON:', json);
            } catch (parseError) {
                console.error('❌ JSON parse error:', parseError);
            }
        } catch (fetchError) {
            console.error('❌ Fetch error:', fetchError);
        }
    }
}

// Initialize the application
window.demandVizApp = new DemandVisualizationApp();