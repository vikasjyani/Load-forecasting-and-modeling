

document.addEventListener('DOMContentLoaded', function() {
    // Current state
    const state = {
        currentNetworkPath: null,
        isMultiPeriod: false,
        currentPeriod: null, 
        periods: [],         
        networkInfo: {},
        startDate: null,
        endDate: null,
        resolution: '1H',
        dispatchData: null,
        capacityData: null,
        newCapacityAdditionsData: null,
        metricsData: null,
        storageData: null,
        emissionsData: null,
        pricesData: null,
        networkFlowData: null,
        colorPalette: {}, 
        extractedNetworkPath: null,
        allNcFiles: [] 
    };

    // Initialize UI elements
    const scenarioSelect = document.getElementById('scenarioSelect');
    const networkFileSelect = document.getElementById('networkFileSelect');
    const networkInfoContainer = document.getElementById('networkInfoContainer');
    const networkUploadForm = document.getElementById('networkUploadForm');
    const analysisDashboard = document.getElementById('analysisDashboard');
    const periodControlContainer = document.getElementById('periodControlContainer');
    const periodSelect = document.getElementById('periodSelect');
    const extractPeriodBtn = document.getElementById('extractPeriodBtn');
    const dateFilterContainer = document.getElementById('dateFilterContainer');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const resolutionSelectEl = document.getElementById('resolutionSelect'); 
    const applyFilterBtn = document.getElementById('applyFilterBtn');
    const backToSelectionBtn = document.getElementById('backToSelectionBtn');
    const newCapacityMethodSelect = document.getElementById('newCapacityMethodSelect');
    const downloadComparisonSecondaryBtn = document.getElementById('downloadComparisonSecondaryBtn');


    const initialNcFilesOptions = Array.from(document.querySelectorAll('#networkFileSelect option'));
    if (initialNcFilesOptions.length > 1) { 
        state.allNcFiles = initialNcFilesOptions
            .filter(opt => opt.value)
            .map(opt => ({
                path: opt.value,
                filename: opt.textContent,
                scenario: opt.dataset.scenario
            }));
    }
    
    // =====================
    // Event Listeners
    // =====================
    
    scenarioSelect.addEventListener('change', function() {
        const selectedScenario = this.value;
        networkFileSelect.innerHTML = '<option value="">Select a network file...</option>';
        if (selectedScenario) {
            networkFileSelect.disabled = false;
            populateNetworkFiles(selectedScenario);
        } else {
            networkFileSelect.disabled = true;
        }
        networkInfoContainer.style.display = 'none';
    });
    
    networkFileSelect.addEventListener('change', function() {
        const selectedNetworkPath = this.value;
        if (selectedNetworkPath) {
            fetchNetworkInfo(selectedNetworkPath);
        } else {
            networkInfoContainer.style.display = 'none';
        }
    });
    
    networkUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const uploadBtn = document.getElementById('uploadBtn');
        const originalBtnText = uploadBtn.innerHTML;
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Uploading...';
        
        fetch('/pypsa/api/upload_network', { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = originalBtnText;
                if (data.status === 'success') {
                    showGlobalAlert(`Network file '${data.file_info.filename}' uploaded to scenario '${data.file_info.scenario}'!`, 'success');
                    refreshNetworkFiles(); 
                    networkUploadForm.reset();
                } else {
                    showGlobalAlert(`Error: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = originalBtnText;
                showGlobalAlert(`Upload Error: ${error.message}`, 'danger');
            });
    });
        
    backToSelectionBtn.addEventListener('click', function() {
        analysisDashboard.style.display = 'none';
        document.getElementById('networkSelectionSection').style.display = 'block';
        document.getElementById('networkComparisonSection').style.display = 'none';
        state.currentNetworkPath = null; 
        state.networkInfo = {};
    });
    
    extractPeriodBtn.addEventListener('click', function() {
        if (state.currentNetworkPath && state.isMultiPeriod && state.currentPeriod) {
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Extracting...';
            extractPeriod(state.currentNetworkPath, state.currentPeriod);
        }
    });
    
    applyFilterBtn.addEventListener('click', function() {
        const startDateVal = startDateInput.value ? new Date(startDateInput.value) : null;
        const endDateVal = endDateInput.value ? new Date(endDateInput.value) : null;
        const resolutionVal = resolutionSelectEl.value;
        
        if (startDateVal && endDateVal && startDateVal > endDateVal) {
            showGlobalAlert('Start date must be before end date.', 'warning');
            return;
        }
        
        state.startDate = startDateVal ? startDateVal.toISOString().split('T')[0] : null;
        state.endDate = endDateVal ? endDateVal.toISOString().split('T')[0] : null;
        state.resolution = resolutionVal;
        
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Applying...';
        
        showLoadingIndicators(['dispatchStackPlot', 'dailyProfilePlot', 'loadDurationPlot', 'socPlot', 'avgPriceByBusPlot', 'priceDurationPlot']);

        Promise.all([
            fetchDispatchData(state.currentNetworkPath), 
            fetchStorageData(state.currentNetworkPath),
            fetchPricesData(state.currentNetworkPath)    
        ])
        .then(() => {
            updateDispatchTab(); 
            updateStorageTab();
            updatePricesTab();   
            showGlobalAlert('Filters applied successfully.', 'success');
        })
        .catch(error => {
            showGlobalAlert(`Error applying filters: ${error.message}`, 'danger');
        })
        .finally(() => {
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-filter me-1"></i> Apply Filters';
            hideLoadingIndicators(['dispatchStackPlot', 'dailyProfilePlot', 'loadDurationPlot', 'socPlot', 'avgPriceByBusPlot', 'priceDurationPlot']);
        });
    });
    
    periodSelect.addEventListener('change', function() {
        state.currentPeriod = this.value;
        showLoadingIndicatorsForDashboard();
        reloadAllData(state.currentNetworkPath) // networkInfo is already in state
         .catch(error => {
            showGlobalAlert(`Error reloading data for period ${state.currentPeriod}: ${error.message}`, 'danger');
        })
        .finally(() => {
            hideLoadingIndicatorsForDashboard();
        });
    });
    
    document.getElementById('capacityAttributeSelect').addEventListener('change', function() {
        showLoadingIndicators(['capacityByCarrierPlot', 'capacityByRegionPlot']);
        fetchCapacityData(state.currentNetworkPath, this.value)
            .then(updateCapacityTab)
            .catch(error => showGlobalAlert(`Error fetching total capacity data: ${error.message}`, 'danger'))
            .finally(() => hideLoadingIndicators(['capacityByCarrierPlot', 'capacityByRegionPlot']));
    });
    
    newCapacityMethodSelect.addEventListener('change', function() {
        showLoadingIndicators(['newCapacityAdditionsPlot']);
        fetchNewCapacityAdditionsData(state.currentNetworkPath, this.value)
            .then(updateNewCapacityAdditionsVisuals)
            .catch(error => showGlobalAlert(`Error fetching new capacity additions: ${error.message}`, 'danger'))
            .finally(() => hideLoadingIndicators(['newCapacityAdditionsPlot']));
    });
    
    document.getElementById('loadExtractedPeriodBtn').addEventListener('click', function() {
        const modalEl = document.getElementById('periodExtractionModal');
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.hide();
        
        if (state.extractedNetworkPath) {
            fetchNetworkInfo(state.extractedNetworkPath, true); 
        }
    });
    
    initializeComparison();
    
    const analysisTabs = document.querySelectorAll('#analysisTabs .nav-link');
    analysisTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const targetPaneId = e.target.getAttribute('data-bs-target');
            if (targetPaneId) {
                const plotContainers = document.querySelector(targetPaneId).querySelectorAll('.plot-container > div:not(.loading-indicator)');
                plotContainers.forEach(pc => {
                    if (pc.id && typeof Plotly !== 'undefined' && pc.data) { 
                         setTimeout(() => Plotly.Plots.resize(pc.id), 50);
                    }
                });
            }
            setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
        });
    });

    document.querySelectorAll('.download-btn').forEach(button => {
        button.addEventListener('click', function() {
            const chartId = this.dataset.chart;
            const plotContainerId = getPlotContainerIdForChart(chartId); 
            if (plotContainerId) {
                const plotEl = document.getElementById(plotContainerId);
                if (plotEl && typeof Plotly !== 'undefined' && plotEl.data) { 
                    Plotly.downloadImage(plotEl, {format: 'png', filename: chartId});
                } else {
                    showGlobalAlert(`Chart '${chartId}' (plot ID '${plotContainerId}') not found or not ready for download.`, 'warning');
                }
            } else {
                 showGlobalAlert(`No plot container defined for chart ID '${chartId}'.`, 'warning');
            }
        });
    });
    
    // =====================
    // Helper Functions
    // =====================

    function getPlotContainerIdForChart(chartId) {
        const map = { 
            'dispatchStack': 'dispatchStackPlot',
            'dailyProfile': 'dailyProfilePlot',
            'loadDuration': 'loadDurationPlot',
            'capacityByCarrier': 'capacityByCarrierPlot',
            'capacityByRegion': 'capacityByRegionPlot',
            'newCapacityAdditions': 'newCapacityAdditionsPlot',
            'cufPlot': 'cufPlot',
            'curtailmentPlot': 'curtailmentPlot',
            'socPlot': 'socPlot',
            'storageUtilizationPlot': 'storageUtilizationPlot',
            'emissionsByCarrier': 'emissionsByCarrierPlot',
            'avgPriceByBus': 'avgPriceByBusPlot',
            'priceDuration': 'priceDurationPlot',
            'lineLoading': 'lineLoadingPlot',
            'comparisonMain': 'comparisonMainPlot',
            'comparisonSecondary': 'comparisonSecondaryPlot'
        };
        return map[chartId];
    }

    function showLoadingIndicators(plotIds) {
        plotIds.forEach(id => {
            const plotContainer = document.getElementById(id);
            if (plotContainer) {
                if (!plotContainer.querySelector('.loading-indicator')) {
                    plotContainer.innerHTML = '<div class="loading-indicator" style="display: flex;"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
                } else {
                     plotContainer.querySelector('.loading-indicator').style.display = 'flex';
                }
            }
        });
    }
    function hideLoadingIndicators(plotIds) {
         plotIds.forEach(id => {
            const plotContainer = document.getElementById(id);
            if (plotContainer) {
                const loader = plotContainer.querySelector('.loading-indicator');
                if(loader) loader.style.display = 'none';
            }
         });
    }
    function showLoadingIndicatorsForDashboard() {
        document.querySelectorAll('.plot-container').forEach(pc => {
            if (!pc.querySelector('.loading-indicator')) {
                pc.innerHTML = '<div class="loading-indicator" style="display: flex;"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
            } else {
                pc.querySelector('.loading-indicator').style.display = 'flex';
            }
        });
        document.querySelectorAll('.stats-value').forEach(el => el.textContent = '-');
        document.querySelectorAll('.table-responsive tbody').forEach(el => el.innerHTML = '<tr><td colspan="100%" class="text-center">Loading...</td></tr>');
    }
    function hideLoadingIndicatorsForDashboard() {
         document.querySelectorAll('.plot-container .loading-indicator').forEach(el => {
            if (el.parentElement.childElementCount > 1 || el.style.display !== 'none') {
                 el.style.display = 'none';
            }
         });
    }

    function populateNetworkFiles(scenario) {
        const filesForScenario = state.allNcFiles.filter(file => file.scenario === scenario);
        networkFileSelect.innerHTML = '<option value="">Select a network file...</option>'; 
        filesForScenario.forEach(file => {
            const option = document.createElement('option');
            option.value = file.path;
            option.textContent = file.filename;
            option.dataset.scenario = file.scenario;
            networkFileSelect.appendChild(option);
        });
    }
    
    function fetchNetworkInfo(networkPath, autoLoadAfterFetch = false) {
        networkInfoContainer.style.display = 'block';
        networkInfoContainer.innerHTML = `<div class="card"><div class="card-body text-center py-4"><i class="fas fa-spinner fa-spin me-2"></i> Loading network information...</div></div>`;
        
        fetch(`/pypsa/api/network_info/${networkPath}`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    networkInfoContainer.innerHTML = `
                        <div class="card">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h5 class="mb-0">Network Information</h5>
                                <button type="button" class="btn btn-sm btn-primary" id="loadNetworkBtnInner">
                                    <i class="fas fa-chart-line me-1"></i> Load Network for Analysis
                                </button>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p><strong>Name:</strong> <span id="networkNameInner"></span></p>
                                        <p><strong>Components:</strong> <span id="networkComponentsInner"></span></p>
                                        <p><strong>Carriers:</strong> <span id="networkCarriersInner"></span></p>
                                    </div>
                                    <div class="col-md-6">
                                        <p><strong>Snapshots:</strong> <span id="networkSnapshotsInner"></span></p>
                                        <p><strong>Period Type:</strong> <span id="networkPeriodTypeInner"></span></p>
                                        <p><strong>Optimization Status:</strong> <span id="networkOptStatusInner"></span></p>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                    
                    document.getElementById('loadNetworkBtnInner').addEventListener('click', function() {
                        this.disabled = true;
                        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';
                        loadNetworkForAnalysis(networkPath, data.network_info);
                    });

                    displayNetworkInfo(data.network_info, 'Inner');
                    state.networkInfo = data.network_info;

                    if (autoLoadAfterFetch) {
                        const btn = document.getElementById('loadNetworkBtnInner');
                        if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';}
                        loadNetworkForAnalysis(networkPath, data.network_info);
                    }
                } else {
                    networkInfoContainer.innerHTML = `<div class="alert alert-danger">Error: ${data.message}</div>`;
                }
            })
            .catch(error => {
                console.error("Error fetching network info:", error);
                networkInfoContainer.innerHTML = `<div class="alert alert-danger">Error fetching network info: ${error.message}</div>`;
            });
    }
    
    function displayNetworkInfo(info, suffix = '') {
        document.getElementById('networkName' + suffix).textContent = info.name || 'N/A';
        const componentsText = info.components && Object.keys(info.components).length > 0 
            ? Object.entries(info.components).map(([comp, count]) => `${comp}: ${count}`).join(', ') 
            : 'N/A';
        document.getElementById('networkComponents' + suffix).textContent = componentsText;
        document.getElementById('networkCarriers' + suffix).textContent = (info.carriers && info.carriers.length > 0) ? info.carriers.join(', ') : 'N/A';

        const snapshots = info.snapshots || {};
        document.getElementById('networkSnapshots' + suffix).textContent = snapshots.count ? `${snapshots.count} (From: ${snapshots.start || 'N/A'} To: ${snapshots.end || 'N/A'})` : 'N/A';
        document.getElementById('networkPeriodType' + suffix).textContent = snapshots.is_multi_period ? 'Multi-period' : 'Single period';
        document.getElementById('networkOptStatus' + suffix).textContent = info.optimization_status || 'N/A';
    }
    
    function refreshNetworkFiles() {
        scenarioSelect.disabled = true;
        networkFileSelect.disabled = true;
        
        fetch('/pypsa/api/scan_files')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    state.allNcFiles = data.files; 
                    updateScenariosDropdown(data.scenarios);
                    
                    scenarioSelect.disabled = false;
                    const currentScenarioVal = scenarioSelect.value; 
                    if (currentScenarioVal) {
                        populateNetworkFiles(currentScenarioVal);
                        networkFileSelect.disabled = false;
                    } else {
                        networkFileSelect.disabled = true;
                        networkFileSelect.innerHTML = '<option value="">Select a network file...</option>';
                    }
                    if (document.getElementById('networkComparisonSection').style.display === 'block') {
                        loadNetworksForComparison();
                    }
                } else {
                    showGlobalAlert(`Error refreshing files: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                showGlobalAlert(`Error refreshing files: ${error.message}`, 'danger');
                scenarioSelect.disabled = false;
                networkFileSelect.disabled = !(!scenarioSelect.value);
            });
    }
    
    function updateScenariosDropdown(scenarios) {
        const currentScenario = scenarioSelect.value;
        scenarioSelect.innerHTML = '<option value="">Select a scenario...</option>';
        scenarios.forEach(scenario => {
            const option = document.createElement('option');
            option.value = scenario;
            option.textContent = scenario;
            scenarioSelect.appendChild(option);
        });
        if (currentScenario && scenarios.includes(currentScenario)) {
            scenarioSelect.value = currentScenario;
        } else {
             scenarioSelect.value = ""; 
        }
    }
        
    function loadNetworkForAnalysis(networkPath, networkInfoFull) {
        state.currentNetworkPath = networkPath;
        state.networkInfo = networkInfoFull; 

        document.getElementById('currentNetworkName').textContent = networkInfoFull.name;
        analysisDashboard.style.display = 'block';
        document.getElementById('networkSelectionSection').style.display = 'none';
        document.getElementById('networkComparisonSection').style.display = 'none';

        const loadBtnInner = document.getElementById('loadNetworkBtnInner');
        if (loadBtnInner) { 
            loadBtnInner.disabled = false;
            loadBtnInner.innerHTML = '<i class="fas fa-chart-line me-1"></i> Load Network for Analysis';
        }
        
        setupPeriodControls(networkInfoFull);
        setupDateFilter(networkInfoFull); 
        
        showLoadingIndicatorsForDashboard();
        reloadAllData(networkPath)
            .then(() => {
                showGlobalAlert('Network loaded successfully.', 'success');
            })
            .catch(error => {
                showGlobalAlert(`Error loading network data: ${error.message}`, 'danger');
            })
            .finally(() => {
                 hideLoadingIndicatorsForDashboard();
            });
    }
    
    function setupPeriodControls(networkInfoFull) {
        state.isMultiPeriod = networkInfoFull.snapshots.is_multi_period;
        state.periods = networkInfoFull.periods || [];
        
        if (state.isMultiPeriod && state.periods.length > 0) {
            periodControlContainer.style.display = 'flex'; 
            periodSelect.innerHTML = '';
            state.periods.forEach(periodVal => { 
                const option = document.createElement('option');
                option.value = periodVal;
                option.textContent = `Period ${periodVal}`;
                periodSelect.appendChild(option);
            });
            state.currentPeriod = state.periods[0]; 
            periodSelect.value = state.currentPeriod;
            extractPeriodBtn.style.display = 'inline-block';
        } else {
            periodControlContainer.style.display = 'none';
            state.currentPeriod = null; 
            extractPeriodBtn.style.display = 'none';
        }
    }
    
    function setupDateFilter(networkInfoFull) {
        const snapshotsInfo = networkInfoFull.snapshots;
        if (snapshotsInfo && snapshotsInfo.start && snapshotsInfo.end && 
            (String(snapshotsInfo.start).includes('T') || String(snapshotsInfo.start).includes(' ') || String(snapshotsInfo.start).match(/^\d{4}-\d{2}-\d{2}$/))) {
            
            dateFilterContainer.style.display = 'flex'; 

            const startDateStr = String(snapshotsInfo.start).split(/[T ]/)[0];
            const endDateStr = String(snapshotsInfo.end).split(/[T ]/)[0];
            
            startDateInput.min = startDateStr;
            startDateInput.max = endDateStr;
            endDateInput.min = startDateStr;
            endDateInput.max = endDateStr;
            
            startDateInput.value = startDateStr;
            endDateInput.value = endDateStr;
            state.startDate = startDateStr;
            state.endDate = endDateStr;
        } else {
            dateFilterContainer.style.display = 'none';
            state.startDate = null;
            state.endDate = null;
        }
        resolutionSelectEl.value = '1H'; 
        state.resolution = '1H';
    }
    
    function extractPeriod(networkPath, periodToExtract) {
        fetch(`/pypsa/api/extract_period/${networkPath}/${periodToExtract}`)
            .then(response => response.json())
            .then(data => {
                extractPeriodBtn.disabled = false;
                extractPeriodBtn.innerHTML = '<i class="fas fa-file-export me-1"></i> Extract Period';
                if (data.status === 'success') {
                    state.extractedNetworkPath = data.file_info.path;
                    document.getElementById('extractedPeriodFilePath').textContent = data.file_info.filename;
                    const modalEl = document.getElementById('periodExtractionModal');
                    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                    modal.show();
                    refreshNetworkFiles(); 
                } else {
                    showGlobalAlert(`Error extracting period: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                extractPeriodBtn.disabled = false;
                extractPeriodBtn.innerHTML = '<i class="fas fa-file-export me-1"></i> Extract Period';
                showGlobalAlert(`Error extracting period: ${error.message}`, 'danger');
            });
    }
    
    async function reloadAllData(networkPath) { 
        try {
            state.dispatchData = null; state.capacityData = null; state.newCapacityAdditionsData = null; state.metricsData = null;
            state.storageData = null; state.emissionsData = null; state.pricesData = null;
            state.networkFlowData = null; 

            await Promise.all([
                fetchDispatchData(networkPath),
                fetchCapacityData(networkPath, document.getElementById('capacityAttributeSelect').value),
                fetchNewCapacityAdditionsData(networkPath, newCapacityMethodSelect.value),
                fetchMetricsData(networkPath),
                fetchStorageData(networkPath),
                fetchEmissionsData(networkPath),
                fetchPricesData(networkPath),
                fetchNetworkFlowData(networkPath)
            ]);
            
            updateAllTabs(); 
            return true;
        } catch (error) {
            console.error("Error in reloadAllData:", error);
            showGlobalAlert(`Error loading data: ${error.message}`, 'danger');
            throw error; 
        }
    }

    function updateAllTabs() {
        updateDispatchTab();
        updateCapacityTab(); // Will also trigger updateNewCapacityAdditionsVisuals
        updateMetricsTab();
        updateStorageTab();
        updateEmissionsTab();
        updatePricesTab();
        updateNetworkFlowTab();
    }

    function buildApiUrl(basePath, queryParams = {}) {
        let url = basePath;
        const params = new URLSearchParams();

        if (state.currentPeriod) {
            params.append('period', state.currentPeriod);
        }
        
        if (queryParams.hasOwnProperty('start_date') && state.startDate) {
            params.append('start_date', state.startDate);
        }
        if (queryParams.hasOwnProperty('end_date') && state.endDate) {
            params.append('end_date', state.endDate);
        }
        if (queryParams.hasOwnProperty('resolution') && state.resolution) {
            params.append('resolution', state.resolution);
        }

        for (const key in queryParams) {
            if (key === 'start_date' || key === 'end_date' || key === 'resolution') continue;
            if (queryParams[key] !== null && queryParams[key] !== undefined && String(queryParams[key]).trim() !== "") {
                params.append(key, queryParams[key]);
            }
        }
        
        const queryString = params.toString();
        if (queryString) {
            url += `?${queryString}`;
        }
        return url;
    }
    
    async function fetchData(endpoint, processDataCallback) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) { 
                 const errorData = await response.json().catch(() => ({ message: `HTTP error! status: ${response.status}` }));
                 throw new Error(errorData.details || errorData.message || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.status === 'success') {
                if (data.colors) { 
                    Object.assign(state.colorPalette, data.colors);
                }
                processDataCallback(data); 
                return data; 
            } else {
                throw new Error(data.details || data.message || 'API returned non-success status without a message.');
            }
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            throw error; 
        }
    }

    // --- Specific data fetching functions ---
    async function fetchDispatchData(networkPath) {
        const queryParams = { start_date: true, end_date: true, resolution: true };
        const url = buildApiUrl(`/pypsa/api/dispatch_data/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.dispatchData = data.dispatch_data_data; 
            if (data.colors) Object.assign(state.colorPalette, data.colors);
        });
    }

    async function fetchCapacityData(networkPath, attribute = 'p_nom_opt') {
        const url = buildApiUrl(`/pypsa/api/capacity_data/${networkPath}`, { attribute });
        return fetchData(url, (data) => {
            state.capacityData = data.carrier_capacity_data; 
            if (data.colors) Object.assign(state.colorPalette, data.colors);
        });
    }

    async function fetchNewCapacityAdditionsData(networkPath, method = 'optimization_diff') {
        const queryParams = { method: method };
        const url = buildApiUrl(`/pypsa/api/new_capacity_additions/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.newCapacityAdditionsData = data.new_capacity_additions_data;
        });
    }

    async function fetchMetricsData(networkPath) {
        const queryParams = { start_date: true, end_date: true };
        const url = buildApiUrl(`/pypsa/api/metrics_data/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.metricsData = data.combined_metrics_extractor_data; 
            if (data.colors) Object.assign(state.colorPalette, data.colors);
        });
    }

    async function fetchStorageData(networkPath) {
        const queryParams = { start_date: true, end_date: true, resolution: true };
        const url = buildApiUrl(`/pypsa/api/storage_data/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.storageData = data.extract_api_storage_data_data;
            if (data.colors) Object.assign(state.colorPalette, data.colors);
        });
    }

    async function fetchEmissionsData(networkPath) {
        const queryParams = { start_date: true, end_date: true };
        const url = buildApiUrl(`/pypsa/api/emissions_data/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.emissionsData = data.emissions_data;
            if (data.colors) Object.assign(state.colorPalette, data.colors);
        });
    }

    async function fetchPricesData(networkPath) {
        const queryParams = { start_date: true, end_date: true, resolution: true };
        const url = buildApiUrl(`/pypsa/api/prices_data/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.pricesData = data.extract_api_prices_data_data; 
        });
    }

    async function fetchNetworkFlowData(networkPath) {
        const queryParams = { start_date: true, end_date: true }; 
        const url = buildApiUrl(`/pypsa/api/network_flow/${networkPath}`, queryParams);
        return fetchData(url, (data) => {
            state.networkFlowData = data.extract_api_network_flow_data;
        });
    }


    // =====================
    // Update Tab Functions
    // =====================
    
    function updateDispatchTab() {
        const plotContainer = document.getElementById('dispatchStackPlot');
        hideLoadingIndicators(['dispatchStackPlot', 'dailyProfilePlot', 'loadDurationPlot']); 

        if (!state.dispatchData || !state.dispatchData.timestamps || state.dispatchData.timestamps.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No dispatch data available for selected criteria.</div>';
            clearPlot('dailyProfilePlot');
            clearPlot('loadDurationPlot');
            clearTable('generationSummaryTable');
            document.getElementById('totalLoadValue').textContent = '-';
            document.getElementById('peakLoadValue').textContent = '-';
            document.getElementById('minLoadValue').textContent = '-';
            return;
        }
        
        createDispatchStackPlot();
        createDailyProfilePlot();
        createLoadDurationCurve();
        updateGenerationSummaryTable();
        updateLoadStatistics();
    }
    
    function updateCapacityTab() {
        const plotContainerCarrier = document.getElementById('capacityByCarrierPlot');
        const plotContainerRegion = document.getElementById('capacityByRegionPlot');
        hideLoadingIndicators(['capacityByCarrierPlot', 'capacityByRegionPlot']);

        let hasTotalCapacityData = state.capacityData && 
                                   ((state.capacityData.by_carrier && state.capacityData.by_carrier.length > 0) ||
                                    (state.capacityData.by_region && state.capacityData.by_region.length > 0));

        if (!hasTotalCapacityData) {
            plotContainerCarrier.innerHTML = '<div class="alert alert-warning m-3">No total capacity data available.</div>';
            plotContainerRegion.innerHTML = '<div class="alert alert-warning m-3">No regional capacity data available.</div>';
            clearTable('capacityTable');
        } else {
            createCapacityByCarrierPlot();
            createCapacityByRegionPlot();
            updateCapacityTable();
        }
        
        updateNewCapacityAdditionsVisuals();
    }
    
    function updateNewCapacityAdditionsVisuals() {
        const plotContainerNewAdditions = document.getElementById('newCapacityAdditionsPlot');
        hideLoadingIndicators(['newCapacityAdditionsPlot']);

        if (!state.newCapacityAdditionsData || !state.newCapacityAdditionsData.new_additions || state.newCapacityAdditionsData.new_additions.length === 0) {
            plotContainerNewAdditions.innerHTML = '<div class="alert alert-info m-3">No new capacity addition data for selected criteria.</div>';
            clearTable('newCapacityAdditionsTable');
        } else {
            createNewCapacityAdditionsPlot();
            updateNewCapacityAdditionsTable();
        }
    }

    function updateMetricsTab() {
        hideLoadingIndicators(['cufPlot', 'curtailmentPlot']);

        if (!state.metricsData || ((!state.metricsData.cuf || state.metricsData.cuf.length === 0) && (!state.metricsData.curtailment || state.metricsData.curtailment.length === 0)) ) {
            document.getElementById('cufPlot').innerHTML = '<div class="alert alert-warning m-3">No CUF data available.</div>';
            document.getElementById('curtailmentPlot').innerHTML = '<div class="alert alert-warning m-3">No curtailment data available.</div>';
            clearTable('cufTable');
            clearTable('curtailmentTable');
            return;
        }
        
        createCUFPlot();
        createCurtailmentPlot();
        updateCUFTable();
        updateCurtailmentTable();
    }
    
    function updateStorageTab() {
        hideLoadingIndicators(['socPlot', 'storageUtilizationPlot']);

        if (!state.storageData || ((!state.storageData.soc || state.storageData.soc.length === 0) && (!state.storageData.stats || state.storageData.stats.length === 0))) {
            document.getElementById('socPlot').innerHTML = '<div class="alert alert-warning m-3">No storage SoC data available.</div>';
            document.getElementById('storageUtilizationPlot').innerHTML = '<div class="alert alert-warning m-3">No storage utilization data.</div>';
            clearTable('storageUtilizationTable');
            return;
        }
        
        createSOCPlot();
        createStorageUtilizationPlot();
        updateStorageUtilizationTable();
    }
    
    function updateEmissionsTab() {
        hideLoadingIndicators(['emissionsByCarrierPlot']);
        const totalValEl =  document.getElementById('totalEmissionsValue');
        const totalConvEl = document.getElementById('totalEmissionsConverted');

        if (!state.emissionsData || ((!state.emissionsData.total || state.emissionsData.total.length === 0) && (!state.emissionsData.by_carrier || state.emissionsData.by_carrier.length === 0))) {
            totalValEl.textContent = '-';
            totalConvEl.textContent = '-';
            document.getElementById('emissionsByCarrierPlot').innerHTML = '<div class="alert alert-warning m-3">No emissions data available.</div>';
            clearTable('emissionsTable');
            return;
        }
        
        updateEmissionsValues();
        createEmissionsByCarrierPlot();
        updateEmissionsTable();
    }
    
    function updatePricesTab() {
        const priceDataContainer = document.getElementById('priceDataContainer');
        const noPriceDataContainer = document.getElementById('noPriceDataContainer');
        hideLoadingIndicators(['avgPriceByBusPlot', 'priceDurationPlot']);

        if (!state.pricesData || !state.pricesData.available) {
            priceDataContainer.style.display = 'none';
            noPriceDataContainer.style.display = 'block';
            clearTable('priceTable');
            return;
        }
        priceDataContainer.style.display = 'block';
        noPriceDataContainer.style.display = 'none';
        
        createAvgPriceByBusPlot();
        createPriceDurationCurve();
        updatePriceTable();
    }
    
    function updateNetworkFlowTab() {
        hideLoadingIndicators(['lineLoadingPlot']);
        if (!state.networkFlowData || ((!state.networkFlowData.losses || state.networkFlowData.losses.length === 0) && (!state.networkFlowData.line_loading || state.networkFlowData.line_loading.length === 0))) {
            document.getElementById('totalLossesValue').textContent = '-';
            document.getElementById('totalLossesGWh').textContent = '-';
            document.getElementById('lineLoadingPlot').innerHTML = '<div class="alert alert-warning m-3">No network flow data available.</div>';
            clearTable('lineLoadingTable');
            return;
        }
        
        updateLossesValues();
        createLineLoadingPlot();
        updateLineLoadingTable();
    }

    function clearPlot(plotId) {
        const plotContainer = document.getElementById(plotId);
        if (plotContainer) {
            plotContainer.innerHTML = `<div class="loading-indicator" style="display: none;"><i class="fas fa-spinner fa-spin"></i> Loading...</div>`;
        }
    }
    function clearTable(tableId) {
        const table = document.getElementById(tableId);
        if (table) {
            const tbody = table.querySelector('tbody');
            if (tbody) tbody.innerHTML = '<tr><td colspan="100%" class="text-center">No data available.</td></tr>';
        }
    }

    // =====================
    // Chart Creation Functions
    // =====================
    
    function createDispatchStackPlot() {
        const plotContainerId = 'dispatchStackPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = ''; 
    
        const { generation, load, storage, store, timestamps } = state.dispatchData;
    
        if (!timestamps || timestamps.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No timestamp data available for dispatch.</div>';
            return;
        }
    
        const traces = [];
        const xValues = timestamps.map(ts => new Date(ts)); 
    
        if (generation && generation.length > 0) {
            const firstGenRecord = generation[0];
            const carriers = Object.keys(firstGenRecord).filter(key => key !== 'index' && key !== 'timestamp' && key !== 'level_0' && !key.startsWith('level_') && key !== 'Snapshot'); 
            
            carriers.forEach(carrier => {
                const yValues = generation.map(item => item[carrier] || 0);
                if (yValues.some(v => Math.abs(v) > 1e-6)) { 
                    traces.push({
                        x: xValues, y: yValues, name: carrier, stackgroup: 'positive_generation',
                        fillcolor: window.colorManager.getColor('carriers', carrier) || window.colorManager.getChartColors(1)[0] || '#CFD8DC',
                        line: { width: 0 }, fill: 'tonexty',
                        hovertemplate: `%{x|%Y-%m-%d %H:%M}<br>${carrier}: %{y:,.1f} MW<extra></extra>`
                    });
                }
            });
        }
    
        const combinedStorageData = [];
        if (storage && storage.length > 0) {
            storage.forEach(s => combinedStorageData.push({...s, _source: 'storage'}));
        }
        if (store && store.length > 0) {
            store.forEach(s => combinedStorageData.push({...s, _source: 'store'}));
        }

        if (combinedStorageData.length > 0) {
            const firstStorageRecord = combinedStorageData[0];
            const componentKeys = Object.keys(firstStorageRecord).filter(key => key !== 'index' && key !== 'timestamp' && key !== 'level_0' && !key.startsWith('level_') && key !== '_source' && key !== 'Snapshot');
            const dischargeCols = componentKeys.filter(key => key.includes('Discharge'));
            const chargeCols = componentKeys.filter(key => key.includes('Charge'));

            dischargeCols.forEach(col => {
                const yValues = combinedStorageData.map(item => item[col] || 0);
                 if (yValues.some(v => v > 1e-6)) {
                    traces.push({
                        x: xValues, y: yValues, name: col, stackgroup: 'positive_storage', 
                        fillcolor: window.colorManager.getColor('carriers', col.replace(' Discharge', '')) || window.colorManager.getColor('storage', col.replace(' Discharge', '')) || window.colorManager.getChartColors(1)[0] || '#CFD8DC',
                        line: { width: 0 }, fill: 'tonexty',
                        hovertemplate: `%{x|%Y-%m-%d %H:%M}<br>${col}: %{y:,.1f} MW<extra></extra>`
                    });
                }
            });
            chargeCols.forEach(col => {
                const yValues = combinedStorageData.map(item => item[col] || 0); 
                 if (yValues.some(v => v < -1e-6)) { 
                    traces.push({
                        x: xValues, y: yValues, name: col, stackgroup: 'negative_storage', 
                        fillcolor: window.colorManager.getColor('carriers', col.replace(' Charge', '')) || window.colorManager.getColor('storage', col.replace(' Charge', '')) || window.colorManager.getChartColors(1)[0] || '#CFD8DC',
                        line: { width: 0 }, fill: 'tonexty', 
                        hovertemplate: `%{x|%Y-%m-%d %H:%M}<br>${col}: %{y:,.1f} MW<extra></extra>`
                    });
                }
            });
        }
    
        if (load && load.length > 0) {
            const loadValues = load.map(item => item.load);
            traces.push({
                x: xValues, y: loadValues, name: 'Load', mode: 'lines',
                line: { color: window.colorManager.getColor('text', 'dark') || window.colorManager.getColor('charts', 'axis') || 'black', width: 2.5 },
                hovertemplate: `%{x|%Y-%m-%d %H:%M}<br>Load: %{y:,.1f} MW<extra></extra>`
            });
        }
    
        const layout = {
            title: `Generation Dispatch${state.resolution ? ` (${state.resolution} resolution)` : ''}`,
            xaxis: { title: 'Time', automargin: true }, 
            yaxis: { title: 'Power (MW)', zeroline: true, zerolinecolor: 'grey', zerolinewidth: 1},
            hovermode: 'x unified', 
            legend: { orientation: 'h', y: -0.3, yanchor: 'bottom', x:0.5, xanchor:'center', traceorder: 'reversed' },
            height: 600, 
            margin: { l: 70, r: 30, t: 50, b: 150 },
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, traces, layout, { responsive: true });
    }

    function createDailyProfilePlot() {
        const plotContainerId = 'dailyProfilePlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
    
        if (!state.dispatchData || !state.dispatchData.timestamps || state.dispatchData.timestamps.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No data for daily profile.</div>';
            return;
        }
    
        const { generation, load, storage, store, timestamps } = state.dispatchData;
        const hourlyAverages = Array.from({ length: 24 }, () => ({ counts: 0 })); 
    
        const allComponentNames = new Set();
        if (generation && generation.length > 0) Object.keys(generation[0]).filter(k => k !=='timestamp' && k !=='index' && k !== 'level_0' && !k.startsWith('level_') && k !== 'Snapshot').forEach(k => allComponentNames.add(k));
        if (load && load.length > 0) allComponentNames.add('Load');
        [storage, store].forEach(s_data => {
            if (s_data && s_data.length > 0) Object.keys(s_data[0]).filter(k => k !=='timestamp' && k !=='index' && k !== 'level_0' && !k.startsWith('level_') && k !== 'Snapshot').forEach(k => allComponentNames.add(k));
        });
    
        allComponentNames.forEach(name => hourlyAverages.forEach(h => h[name] = 0));

        timestamps.forEach((ts, i) => {
            const date = new Date(ts);
            const hour = date.getHours();
            hourlyAverages[hour].counts++;

            if (generation && generation[i]) {
                Object.keys(generation[i]).filter(k => k !=='timestamp' && k !=='index' && k !== 'level_0' && !k.startsWith('level_') && k !== 'Snapshot').forEach(carrier => {
                    hourlyAverages[hour][carrier] += (generation[i][carrier] || 0);
                });
            }
            if (load && load[i]) {
                hourlyAverages[hour]['Load'] += (load[i].load || 0);
            }
            [storage, store].forEach(sourceData => {
                if (sourceData && sourceData[i]) {
                    Object.keys(sourceData[i]).filter(k => k !=='timestamp' && k !=='index' && k !== 'level_0' && !k.startsWith('level_') && k !== 'Snapshot').forEach(key => {
                        hourlyAverages[hour][key] += (sourceData[i][key] || 0); 
                    });
                }
            });
        });
    
        const traces = [];
        const xHours = Array.from({ length: 24 }, (_, i) => i);
    
        allComponentNames.forEach(compName => {
            const yValues = xHours.map(hour => hourlyAverages[hour][compName] / (hourlyAverages[hour].counts || 1));
            const isLoad = compName === 'Load';
            const isCharge = compName.includes('Charge');

            if (yValues.some(v => Math.abs(v) > 1e-3)) {
                if (isLoad) {
                     traces.push({
                        x: xHours, y: yValues, name: 'Load', mode: 'lines',
                        line: { color: window.colorManager.getColor('text', 'dark') || window.colorManager.getColor('charts', 'axis') || 'black', width: 2.5 },
                        hovertemplate: `Hour %{x}<br>Avg Load: %{y:,.1f} MW<extra></extra>`
                    });
                } else {
                    traces.push({
                        x: xHours, y: yValues, name: compName, 
                        stackgroup: isCharge ? 'negative_components_daily' : 'positive_components_daily', 
                        fillcolor: window.colorManager.getColor('carriers', compName.replace(' Charge','').replace(' Discharge','')) || window.colorManager.getColor('storage', compName.replace(' Charge','').replace(' Discharge','')) || window.colorManager.getChartColors(1)[0] || '#CFD8DC',
                        line: { width: 0 }, fill: 'tonexty',
                        hovertemplate: `Hour %{x}<br>Avg ${compName}: %{y:,.1f} MW<extra></extra>`
                    });
                }
            }
        });
            
        const layout = {
            title: 'Average Daily Profile',
            xaxis: { title: 'Hour of Day', tickmode: 'linear', tick0: 0, dtick: 2, automargin: true },
            yaxis: { title: 'Average Power (MW)', zeroline: true, zerolinecolor: 'grey', zerolinewidth: 1 },
            hovermode: 'x unified', legend: { orientation: 'h', y: -0.3, yanchor: 'bottom', x:0.5, xanchor:'center', traceorder: 'reversed' },
            height: 450, margin: { l: 70, r: 30, t: 50, b: 150 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, traces, layout, { responsive: true });
    }

    function createLoadDurationCurve() {
        const plotContainerId = 'loadDurationPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
    
        if (!state.dispatchData || !state.dispatchData.load || state.dispatchData.load.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No load data for duration curve.</div>';
            return;
        }
    
        const loadValues = state.dispatchData.load.map(item => item.load).filter(val => val !== null && !isNaN(val));
        if (loadValues.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">Load data is empty or invalid.</div>';
            return;
        }
        loadValues.sort((a, b) => b - a); 
        const xValues = loadValues.map((_, i) => (i / (loadValues.length -1 + 1e-9)) * 100); 
    
        const trace = {
            x: xValues, y: loadValues, type: 'scatter', fill: 'tozeroy',
            fillcolor: (window.colorManager.getColor('charts', 'primary') || '#007bff') + '33', line: { color: window.colorManager.getColor('charts', 'primary') || '#007bff' },
            hovertemplate: 'Duration: %{x:.1f}%<br>Load: %{y:,.1f} MW<extra></extra>'
        };
        const layout = {
            title: 'Load Duration Curve',
            xaxis: { title: 'Duration (%)', range: [0, 100], automargin: true }, yaxis: { title: 'Load (MW)' },
            height: 450, margin: { l: 70, r: 30, t: 50, b: 60 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updateGenerationSummaryTable() {
        const tbody = document.getElementById('generationSummaryTable').querySelector('tbody');
        tbody.innerHTML = ''; 
    
        if (!state.dispatchData || !state.dispatchData.generation || state.dispatchData.generation.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center">No generation data.</td></tr>';
            return;
        }
    
        const generationEnergyByCarrier = {};
        const generationData = state.dispatchData.generation; 
        const firstGenRecord = generationData[0];
        const carriers = Object.keys(firstGenRecord).filter(key => key !== 'index' && key !== 'timestamp' && key !== 'level_0' && !key.startsWith('level_') && key !== 'Snapshot');
        
        let intervalHours = 1; 
        if (state.resolution) {
            if (state.resolution.includes('H')) intervalHours = parseFloat(state.resolution.replace('H',''));
            else if (state.resolution === '1D') intervalHours = 24;
            else if (state.resolution === '1W') intervalHours = 24 * 7;
        }

        carriers.forEach(carrier => {
            generationEnergyByCarrier[carrier] = generationData.reduce((sum, item) => sum + (item[carrier] || 0), 0) * intervalHours;
        });
    
        const sortedCarriers = Object.entries(generationEnergyByCarrier)
            .filter(([_, energy]) => Math.abs(energy) > 1e-3) // Include negative generation if any (e.g. some storage models)
            .sort(([, a], [, b]) => b - a);
    
        const totalGenerationEnergy = sortedCarriers.reduce((sum, [, energy]) => sum + energy, 0);
    
        sortedCarriers.forEach(([carrier, energy]) => {
            const percentage = totalGenerationEnergy !== 0 ? (energy / totalGenerationEnergy) * 100 : 0;
            const row = tbody.insertRow();
            row.insertCell().textContent = carrier;
            row.insertCell().textContent = energy.toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = percentage.toLocaleString(undefined, { maximumFractionDigits: 1 }) + '%';
            row.cells[2].className = 'text-end';
        });
    
        if (Math.abs(totalGenerationEnergy) > 1e-3) {
            const totalRow = tbody.insertRow();
            totalRow.classList.add('table-active', 'fw-bold');
            totalRow.insertCell().textContent = 'Total';
            totalRow.insertCell().textContent = totalGenerationEnergy.toLocaleString(undefined, { maximumFractionDigits: 1 });
            totalRow.cells[1].className = 'text-end';
            totalRow.insertCell().textContent = '100.0%';
            totalRow.cells[2].className = 'text-end';
        }
    }

    function updateLoadStatistics() {
        if (!state.dispatchData || !state.dispatchData.load || state.dispatchData.load.length === 0) {
            document.getElementById('totalLoadValue').textContent = '-';
            document.getElementById('peakLoadValue').textContent = '-';
            document.getElementById('minLoadValue').textContent = '-';
            return;
        }
        const loadPowerValues = state.dispatchData.load.map(item => item.load); 
        let intervalHours = 1;
        if (state.resolution) {
            if (state.resolution.includes('H')) intervalHours = parseFloat(state.resolution.replace('H',''));
            else if (state.resolution === '1D') intervalHours = 24;
            else if (state.resolution === '1W') intervalHours = 24 * 7;
        }

        const totalLoadEnergy = loadPowerValues.reduce((sum, loadP) => sum + (loadP * intervalHours), 0); 
        const peakLoadPower = Math.max(...loadPowerValues); 
        const minLoadPower = Math.min(...loadPowerValues); 
    
        document.getElementById('totalLoadValue').textContent = totalLoadEnergy.toLocaleString(undefined, { maximumFractionDigits: 1 });
        document.getElementById('peakLoadValue').textContent = peakLoadPower.toLocaleString(undefined, { maximumFractionDigits: 1 });
        document.getElementById('minLoadValue').textContent = minLoadPower.toLocaleString(undefined, { maximumFractionDigits: 1 });
    }

    function createCapacityByCarrierPlot() {
        const plotContainerId = 'capacityByCarrierPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
    
        if (!state.capacityData || !state.capacityData.by_carrier || state.capacityData.by_carrier.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No capacity by carrier data.</div>';
            return;
        }
    
        const capacityData = [...state.capacityData.by_carrier].sort((a, b) => b.Capacity - a.Capacity);
        const attribute = document.getElementById('capacityAttributeSelect').value;
        const unit = capacityData.length > 0 && capacityData[0].Unit ? capacityData[0].Unit : (attribute.startsWith('e_nom') ? 'MWh' : 'MW');

        const trace = {
            x: capacityData.map(item => item.Carrier),
            y: capacityData.map(item => item.Capacity),
            type: 'bar',
            marker: { color: capacityData.map(item => window.colorManager.getColor('carriers', item.Carrier) || window.colorManager.getChartColors(1)[0] || '#CFD8DC') },
            hovertemplate: `%{x}<br>Capacity: %{y:,.1f} ${unit}<extra></extra>`
        };
        const layout = {
            title: `Installed Capacity by Carrier (${attribute})`,
            xaxis: { title: 'Carrier', automargin: true },
            yaxis: { title: `Capacity (${unit})` },
            height: 400, margin: { l: 70, r: 30, t: 50, b: 100 },
            legend: {traceorder: 'reversed'}
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function createCapacityByRegionPlot() {
        const plotContainerId = 'capacityByRegionPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
    
        if (!state.capacityData || !state.capacityData.by_region || state.capacityData.by_region.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No capacity by region data.</div>';
            return;
        }
    
        const capacityData = [...state.capacityData.by_region].sort((a, b) => b.Capacity - a.Capacity);
        const attribute = document.getElementById('capacityAttributeSelect').value;
        const unit = capacityData.length > 0 && capacityData[0].Unit ? capacityData[0].Unit : (attribute.startsWith('e_nom') ? 'MWh' : 'MW');


        const trace = {
            x: capacityData.map(item => item.Region),
            y: capacityData.map(item => item.Capacity),
            type: 'bar',
            marker: { color: window.colorManager.getColor('charts', 'primary') || 'rgb(158,202,225)', line: { color: window.colorManager.getColor('charts', 'axis') || 'rgb(8,48,107)', width: 1.5 } },
            hovertemplate: `%{x}<br>Capacity: %{y:,.1f} ${unit}<extra></extra>`
        };
        const layout = {
            title: `Capacity by Region (${attribute})`,
            xaxis: { title: 'Region', tickangle: -45, automargin: true },
            yaxis: { title: `Capacity (${unit})` },
            height: 450, margin: { l: 70, r: 30, t: 50, b: 120 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updateCapacityTable() {
        const tbody = document.getElementById('capacityTable').querySelector('tbody');
        tbody.innerHTML = '';
        const attribute = document.getElementById('capacityAttributeSelect').value;
        let defaultUnit = attribute.startsWith('e_nom') ? 'MWh' : 'MW';

        if (!state.capacityData || !state.capacityData.by_carrier || state.capacityData.by_carrier.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center">No capacity data.</td></tr>';
            return;
        }
        const capacityData = [...state.capacityData.by_carrier].sort((a, b) => b.Capacity - a.Capacity);
        let totalCapacity = 0;
    
        capacityData.forEach(item => {
            const unit = item.Unit || defaultUnit; 
            const row = tbody.insertRow();
            row.insertCell().textContent = item.Carrier;
            row.insertCell().textContent = item.Capacity.toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = unit; 
            totalCapacity += item.Capacity;
        });
    
        if (totalCapacity > 0 && capacityData.length > 0) {
            const overallUnit = capacityData[0].Unit || defaultUnit; 
            const totalRow = tbody.insertRow();
            totalRow.classList.add('table-active', 'fw-bold');
            totalRow.insertCell().textContent = 'Total';
            totalRow.insertCell().textContent = totalCapacity.toLocaleString(undefined, { maximumFractionDigits: 1 });
            totalRow.cells[1].className = 'text-end';
            totalRow.insertCell().textContent = overallUnit;
        }
    }

    function createNewCapacityAdditionsPlot() {
        const plotContainerId = 'newCapacityAdditionsPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
    
        if (!state.newCapacityAdditionsData || !state.newCapacityAdditionsData.new_additions || state.newCapacityAdditionsData.new_additions.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-info m-3">No new capacity addition data to plot.</div>';
            return;
        }
    
        const additionsData = [...state.newCapacityAdditionsData.new_additions].sort((a, b) => b.New_Capacity - a.New_Capacity);
        const method = newCapacityMethodSelect.options[newCapacityMethodSelect.selectedIndex].text; // Get text of selected option
        const unit = additionsData.length > 0 && additionsData[0].Unit ? additionsData[0].Unit : 'MW/MWh';

        const trace = {
            x: additionsData.map(item => item.Carrier),
            y: additionsData.map(item => item.New_Capacity),
            type: 'bar',
            marker: { color: additionsData.map(item => window.colorManager.getColor('carriers', item.Carrier) || window.colorManager.getChartColors(1)[0] || '#CFD8DC') },
            hovertemplate: `%{x}<br>New Capacity: %{y:,.1f} ${unit}<extra></extra>`
        };
        const layout = {
            title: `New Capacity Additions by Carrier <br><span style="font-size:0.8em; color:grey;">(Method: ${method})</span>`,
            xaxis: { title: 'Carrier', automargin: true },
            yaxis: { title: `New Capacity (${unit})` },
            height: 400, margin: { l: 70, r: 30, t: 60, b: 100 }, // Increased top margin for subtitle
            legend: {traceorder: 'reversed'}
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updateNewCapacityAdditionsTable() {
        const tbody = document.getElementById('newCapacityAdditionsTable').querySelector('tbody');
        tbody.innerHTML = '';
        
        if (!state.newCapacityAdditionsData || !state.newCapacityAdditionsData.new_additions || state.newCapacityAdditionsData.new_additions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center">No new capacity addition data.</td></tr>';
            return;
        }
        const additionsData = [...state.newCapacityAdditionsData.new_additions].sort((a, b) => b.New_Capacity - a.New_Capacity);
        let totalNewCapacity = 0;
        const defaultUnit = 'MW/MWh';
    
        additionsData.forEach(item => {
            const unit = item.Unit || defaultUnit;
            const row = tbody.insertRow();
            row.insertCell().textContent = item.Carrier;
            row.insertCell().textContent = item.New_Capacity.toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = unit;
            totalNewCapacity += item.New_Capacity;
        });
    
        if (totalNewCapacity > 0 && additionsData.length > 0) {
            const overallUnit = additionsData[0].Unit || defaultUnit;
            const totalRow = tbody.insertRow();
            totalRow.classList.add('table-active', 'fw-bold');
            totalRow.insertCell().textContent = 'Total New Additions';
            totalRow.insertCell().textContent = totalNewCapacity.toLocaleString(undefined, { maximumFractionDigits: 1 });
            totalRow.cells[1].className = 'text-end';
            totalRow.insertCell().textContent = overallUnit;
        }
    }


    function createCUFPlot() {
        const plotContainerId = 'cufPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.metricsData || !state.metricsData.cuf || state.metricsData.cuf.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No CUF data.</div>';
            return;
        }
        const cufData = [...state.metricsData.cuf].sort((a, b) => b.CUF - a.CUF);
        const trace = {
            x: cufData.map(item => item.Carrier),
            y: cufData.map(item => item.CUF * 100), 
            type: 'bar',
            marker: { color: cufData.map(item => window.colorManager.getColor('carriers', item.Carrier) || window.colorManager.getChartColors(1)[0] || '#CFD8DC') },
            hovertemplate: `%{x}<br>CUF: %{y:.1f}%<extra></extra>`
        };
        const layout = {
            title: 'Capacity Utilization Factor (CUF)',
            xaxis: { title: 'Carrier', automargin: true }, yaxis: { title: 'CUF (%)', tickformat: '.1f' },
            height: 350, margin: { l: 60, r: 20, t: 40, b: 100 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updateCUFTable() {
        const tbody = document.getElementById('cufTable').querySelector('tbody');
        tbody.innerHTML = '';
        if (!state.metricsData || !state.metricsData.cuf || state.metricsData.cuf.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="text-center">No CUF data.</td></tr>';
            return;
        }
        const cufData = [...state.metricsData.cuf].sort((a, b) => b.CUF - a.CUF);
        cufData.forEach(item => {
            const row = tbody.insertRow();
            row.insertCell().textContent = item.Carrier;
            row.insertCell().textContent = (item.CUF * 100).toLocaleString(undefined, { maximumFractionDigits: 1 }) + '%';
            row.cells[1].className = 'text-end';
        });
    }

    function createCurtailmentPlot() {
        const plotContainerId = 'curtailmentPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.metricsData || !state.metricsData.curtailment || state.metricsData.curtailment.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No curtailment data.</div>';
            return;
        }
        const curtailmentData = [...state.metricsData.curtailment].sort((a, b) => b['Curtailment (%)'] - a['Curtailment (%)']);
        const trace = {
            x: curtailmentData.map(item => item.Carrier),
            y: curtailmentData.map(item => item['Curtailment (%)']),
            type: 'bar',
            marker: { color: curtailmentData.map(item => window.colorManager.getColor('carriers', item.Carrier) || window.colorManager.getChartColors(1)[0] || '#CFD8DC') },
            hovertemplate: `%{x}<br>Curtailment: %{y:.1f}%<extra></extra>`
        };
        const layout = {
            title: 'Renewable Curtailment',
            xaxis: { title: 'Carrier', automargin: true }, yaxis: { title: 'Curtailment (%)' },
            height: 350, margin: { l: 60, r: 20, t: 40, b: 100 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updateCurtailmentTable() {
        const tbody = document.getElementById('curtailmentTable').querySelector('tbody');
        tbody.innerHTML = '';
        if (!state.metricsData || !state.metricsData.curtailment || state.metricsData.curtailment.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No curtailment data.</td></tr>';
            return;
        }
        const curtailmentData = [...state.metricsData.curtailment].sort((a, b) => b['Curtailment (%)'] - a['Curtailment (%)']);
        curtailmentData.forEach(item => {
            const row = tbody.insertRow();
            row.insertCell().textContent = item.Carrier;
            row.insertCell().textContent = (item['Curtailment (MWh)'] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = (item['Potential (MWh)'] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[2].className = 'text-end';
            row.insertCell().textContent = (item['Curtailment (%)'] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 }) + '%';
            row.cells[3].className = 'text-end';
        });
    }

    function createSOCPlot() {
        const plotContainerId = 'socPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.storageData || !state.storageData.soc || state.storageData.soc.length === 0 || !state.storageData.timestamps || state.storageData.timestamps.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No SoC data.</div>';
            return;
        }
        const socDataRecords = state.storageData.soc; 
        const timestamps = state.storageData.timestamps.map(ts => new Date(ts));
        const storageTypes = state.storageData.storage_types || []; 
        const traces = [];

        storageTypes.forEach(type => {
            const yValues = socDataRecords.map(item => item[type] || 0);
            if (yValues.some(v => Math.abs(v) > 1e-3)) {
                // Attempt to get a base carrier name for color (e.g., "Battery" from "Battery (StorageUnit)")
                const baseColorKey = type.includes('(') ? type.substring(0, type.indexOf('(')).trim() : type;
                traces.push({
                    x: timestamps, y: yValues, name: type, mode: 'lines',
                    line: { color: window.colorManager.getColor('carriers', baseColorKey) || window.colorManager.getColor('storage', baseColorKey) || window.colorManager.getColor('carriers', type) || window.colorManager.getChartColors(1)[0] || '#CFD8DC', width: 2 },
                    hovertemplate: `%{x|%Y-%m-%d %H:%M}<br>${type} SoC: %{y:,.1f} MWh<extra></extra>`
                });
            }
        });

        const layout = {
            title: `Storage State of Charge (SoC)${state.resolution ? ` (${state.resolution} resolution)` : ''}`,
            xaxis: { title: 'Time', automargin: true }, yaxis: { title: 'Energy (MWh)' },
            hovermode: 'x unified', legend: { orientation: 'h', y: -0.3, yanchor: 'bottom', x:0.5, xanchor:'center', traceorder: 'reversed' },
            height: 400, margin: { l: 70, r: 30, t: 50, b: 150 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, traces, layout, { responsive: true });
    }

    function createStorageUtilizationPlot() {
        const plotContainerId = 'storageUtilizationPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.storageData || !state.storageData.stats || state.storageData.stats.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No storage utilization data.</div>';
            return;
        }
        const storageStats = [...state.storageData.stats].sort((a,b) => a.Storage_Type.localeCompare(b.Storage_Type));
        const trace1 = {
            x: storageStats.map(item => item.Storage_Type),
            y: storageStats.map(item => item.Charge_MWh),
            name: 'Charge (MWh)', type: 'bar', 
            marker: { color: window.colorManager.getColor('status', 'warning') || 'rgba(255,165,0,0.8)' }
        };
        const trace2 = {
            x: storageStats.map(item => item.Storage_Type),
            y: storageStats.map(item => item.Discharge_MWh),
            name: 'Discharge (MWh)', type: 'bar', 
            marker: { color: window.colorManager.getColor('status', 'success') || 'rgba(50,205,50,0.8)' }
        };
        const layout = {
            title: 'Storage Energy Throughput',
            xaxis: { title: 'Storage Type', automargin: true, tickangle: -30 }, yaxis: { title: 'Energy (MWh)' },
            barmode: 'group', bargap: 0.15, bargroupgap: 0.1,
            height: 350, margin: { l: 70, r: 30, t: 50, b: 120 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace1, trace2], layout, { responsive: true });
    }

    function updateStorageUtilizationTable() {
        const tbody = document.getElementById('storageUtilizationTable').querySelector('tbody');
        tbody.innerHTML = '';
        if (!state.storageData || !state.storageData.stats || state.storageData.stats.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No storage utilization data.</td></tr>';
            return;
        }
        const storageStats = [...state.storageData.stats].sort((a,b) => a.Storage_Type.localeCompare(b.Storage_Type));
        storageStats.forEach(item => {
            const row = tbody.insertRow();
            row.insertCell().textContent = item.Storage_Type;
            row.insertCell().textContent = (item.Charge_MWh || 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = (item.Discharge_MWh || 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
            row.cells[2].className = 'text-end';
            row.insertCell().textContent = item.Efficiency_Percent !== null && !isNaN(item.Efficiency_Percent) ? item.Efficiency_Percent.toLocaleString(undefined, { maximumFractionDigits: 1 }) + '%' : '-';
            row.cells[3].className = 'text-end';
        });
    }

    function updateEmissionsValues() {
        const totalValEl =  document.getElementById('totalEmissionsValue');
        const totalConvEl = document.getElementById('totalEmissionsConverted');
        if (!state.emissionsData || !state.emissionsData.total || state.emissionsData.total.length === 0) {
            totalValEl.textContent = '-';
            totalConvEl.textContent = '-';
            return;
        }
        const totalEmissionsItem = state.emissionsData.total.find(item => item.Period === state.currentPeriod || item.Period === 'Overall') || state.emissionsData.total[0];
        const totalEmissions = totalEmissionsItem ? totalEmissionsItem['Total CO2 Emissions (Tonnes)'] : 0;

        totalValEl.textContent = totalEmissions.toLocaleString(undefined, { maximumFractionDigits: 0 });
        totalConvEl.textContent = (totalEmissions / 1e6).toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    function createEmissionsByCarrierPlot() {
        const plotContainerId = 'emissionsByCarrierPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.emissionsData || !state.emissionsData.by_carrier || state.emissionsData.by_carrier.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No emissions by carrier data.</div>';
            return;
        }
        const emissionsDataPeriod = state.emissionsData.by_carrier.filter(item => item.Period === state.currentPeriod || item.Period === 'Overall');
        const emissionsData = [...emissionsDataPeriod]
            .filter(item => item['Emissions (Tonnes)'] > 1)
            .sort((a, b) => b['Emissions (Tonnes)'] - a['Emissions (Tonnes)']);

        const trace = {
            x: emissionsData.map(item => item.Carrier),
            y: emissionsData.map(item => item['Emissions (Tonnes)']),
            type: 'bar',
            marker: { color: emissionsData.map(item => window.colorManager.getColor('carriers', item.Carrier) || window.colorManager.getChartColors(1)[0] || '#CFD8DC') },
            hovertemplate: `%{x}<br>Emissions: %{y:,.0f} tonnes CO₂<extra></extra>`
        };
        const layout = {
            title: 'CO₂ Emissions by Carrier',
            xaxis: { title: 'Carrier', automargin: true }, yaxis: { title: 'Emissions (Tonnes CO₂)' },
            height: 350, margin: { l: 70, r: 30, t: 50, b: 100 },
            legend: {traceorder: 'reversed'}
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updateEmissionsTable() {
        const tbody = document.getElementById('emissionsTable').querySelector('tbody');
        tbody.innerHTML = '';
        if (!state.emissionsData || !state.emissionsData.by_carrier || state.emissionsData.by_carrier.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center">No emissions data.</td></tr>';
            return;
        }
        const emissionsDataPeriod = state.emissionsData.by_carrier.filter(item => item.Period === state.currentPeriod || item.Period === 'Overall');
        const emissionsData = [...emissionsDataPeriod]
            .filter(item => item['Emissions (Tonnes)'] > 1)
            .sort((a, b) => b['Emissions (Tonnes)'] - a['Emissions (Tonnes)']);
        const totalEmissions = emissionsData.reduce((sum, item) => sum + item['Emissions (Tonnes)'], 0);

        emissionsData.forEach(item => {
            const percentage = totalEmissions > 0 ? (item['Emissions (Tonnes)'] / totalEmissions) * 100 : 0;
            const row = tbody.insertRow();
            row.insertCell().textContent = item.Carrier;
            row.insertCell().textContent = (item['Emissions (Tonnes)'] || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = percentage.toLocaleString(undefined, { maximumFractionDigits: 1 }) + '%';
            row.cells[2].className = 'text-end';
        });
        if (totalEmissions > 0) {
            const totalRow = tbody.insertRow();
            totalRow.classList.add('table-active', 'fw-bold');
            totalRow.insertCell().textContent = 'Total';
            totalRow.insertCell().textContent = totalEmissions.toLocaleString(undefined, { maximumFractionDigits: 0 });
            totalRow.cells[1].className = 'text-end';
            totalRow.insertCell().textContent = '100.0%';
            totalRow.cells[2].className = 'text-end';
        }
    }

    function createAvgPriceByBusPlot() {
        const plotContainerId = 'avgPriceByBusPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.pricesData || !state.pricesData.avg_by_bus || state.pricesData.avg_by_bus.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No average price data by bus.</div>';
            return;
        }
        const priceData = [...state.pricesData.avg_by_bus].sort((a, b) => b.price - a.price);
        const unit = state.pricesData.unit || 'currency/MWh';
        const trace = {
            x: priceData.map(item => item.bus), y: priceData.map(item => item.price),
            type: 'bar', marker: { color: window.colorManager.getColor('charts', 'primary') || 'rgba(158,202,225,0.8)', line: { color: window.colorManager.getColor('charts', 'axis') || 'rgb(8,48,107)', width: 1.5 } },
            hovertemplate: `%{x}<br>Price: %{y:,.2f} ${unit}<extra></extra>`
        };
        const layout = {
            title: `Average Marginal Price by Bus${state.resolution ? ` (${state.resolution} resolution)` : ''}`,
            xaxis: { title: 'Bus', tickangle: -45, automargin: true }, yaxis: { title: `Price (${unit})` },
            height: 350, margin: { l: 70, r: 30, t: 50, b: 120 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function createPriceDurationCurve() {
        const plotContainerId = 'priceDurationPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.pricesData || !state.pricesData.duration_curve || state.pricesData.duration_curve.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No price duration data.</div>';
            return;
        }
        const durationCurve = state.pricesData.duration_curve; 
        const unit = state.pricesData.unit || 'currency/MWh';
        const xValues = durationCurve.map((_, i) => (i / (durationCurve.length -1 + 1e-9)) * 100);
        const trace = {
            x: xValues, y: durationCurve, type: 'scatter', fill: 'tozeroy',
            fillcolor: (window.colorManager.getColor('charts', 'secondary') || '#FF0000') + '33', line: { color: window.colorManager.getColor('charts', 'secondary') || '#FF0000' },
            hovertemplate: `Duration: %{x:.1f}%<br>Price: %{y:,.2f} ${unit}<extra></extra>`
        };
        const layout = {
            title: `Price Duration Curve${state.resolution ? ` (${state.resolution} resolution)` : ''}`,
            xaxis: { title: 'Duration (%)', range: [0, 100], automargin: true }, yaxis: { title: `Price (${unit})` },
            height: 350, margin: { l: 70, r: 30, t: 50, b: 60 }
        };
        if (typeof Plotly !== 'undefined') Plotly.newPlot(plotContainerId, [trace], layout, { responsive: true });
    }

    function updatePriceTable() {
        const tbody = document.getElementById('priceTable').querySelector('tbody');
        tbody.innerHTML = '';
        if (!state.pricesData || !state.pricesData.avg_by_bus || state.pricesData.avg_by_bus.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No price data.</td></tr>';
            return;
        }
        const priceData = [...state.pricesData.avg_by_bus].sort((a, b) => b.price - a.price); 
        const unit = state.pricesData.unit || 'currency/MWh';

        priceData.forEach(item => {
            const row = tbody.insertRow();
            row.insertCell().textContent = item.bus;
            row.insertCell().textContent = (item.price !== null && item.price !== undefined) ? item.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-';
            row.cells[1].className = 'text-end';
            row.insertCell().textContent = (item.min_price !== null && item.min_price !== undefined) ? item.min_price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-';
            row.cells[2].className = 'text-end';
            row.insertCell().textContent = (item.max_price !== null && item.max_price !== undefined) ? item.max_price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-';
            row.cells[3].className = 'text-end';
            row.insertCell().textContent = unit;
        });
    }

    function updateLossesValues() {
        const totalValEl = document.getElementById('totalLossesValue');
        const totalGwhEl = document.getElementById('totalLossesGWh');
        if (!state.networkFlowData || !state.networkFlowData.losses || state.networkFlowData.losses.length === 0) {
            totalValEl.textContent = '-';
            totalGwhEl.textContent = '-';
            return;
        }
        const totalLossesItem = state.networkFlowData.losses.find(item => item.Period === state.currentPeriod || item.Period === 'Overall') || state.networkFlowData.losses[0];
        const totalLossesMWh = totalLossesItem ? (totalLossesItem['Losses (MWh)'] || 0) : 0;

        totalValEl.textContent = totalLossesMWh.toLocaleString(undefined, { maximumFractionDigits: 1 });
        totalGwhEl.textContent = (totalLossesMWh / 1000).toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    function createLineLoadingPlot() {
        const plotContainerId = 'lineLoadingPlot';
        const plotContainer = document.getElementById(plotContainerId);
        plotContainer.innerHTML = '';
        if (!state.networkFlowData || !state.networkFlowData.line_loading || state.networkFlowData.line_loading.length === 0) {
            plotContainer.innerHTML = '<div class="alert alert-warning m-3">No line loading data.</div>';
            return;
        }
        const lineLoadingData = [...state.networkFlowData.line_loading].sort((a, b) => b.loading - a.loading).slice(0, 20); // Top 20
        const trace = {
            x: lineLoadingData.map(item => item.line),
            y: lineLoadingData.map(item => item.loading),
            type: 'bar',
            marker: {
                color: lineLoadingData.map(item => {
                    if (item.loading > 90) return window.colorManager.getColor('status', 'error') || 'rgba(220,53,69,0.8)';
                    if (item.loading > 70) return window.colorManager.getColor('status', 'warning') || 'rgba(255,193,7,0.8)';
                    return window.colorManager.getColor('status', 'success') || 'rgba(25,135,84,0.8)';
// PyPSA Color Settings Modal Functions
    async function showPypsaColorModal() {
        if (!window.colorManager) {
            console.warn('ColorManager not available for PyPSA color configurations.');
            showGlobalAlert('Color management system is not initialized.', 'danger');
            return;
        }
        if (!state.currentNetworkPath) {
            showGlobalAlert('Please load a PyPSA network first to configure its colors.', 'warning');
            return;
        }

        const carrierColorsContainer = document.getElementById('carrierColorsConfigContent');
        const techColorsContainer = document.getElementById('technologyColorsConfigContent'); // Optional for now

        carrierColorsContainer.innerHTML = '<div class="loading-indicator" style="display: flex;"><i class="fas fa-spinner fa-spin"></i> Loading colors...</div>';
        if (techColorsContainer) techColorsContainer.innerHTML = '<p class="text-muted">Technology-specific colors can be configured here if applicable.</p>';


        try {
            // Fetch current carrier colors from manager
            const currentCarrierColors = await window.colorManager.getCategoryColors('carriers') || {};

            // Determine unique carriers from network info or existing palette
            let uniqueCarriers = new Set();
            if (state.networkInfo && state.networkInfo.carriers && state.networkInfo.carriers.length > 0) {
                state.networkInfo.carriers.forEach(c => uniqueCarriers.add(c));
            }
            // Add carriers from the state.colorPalette as it might contain dynamically added ones from plots
            Object.keys(state.colorPalette).forEach(c => {
                // Heuristic: if a key doesn't include "Charge" or "Discharge" and is not a known special key, it might be a carrier
                if (!c.includes("Charge") && !c.includes("Discharge") && !['Load', 'Losses', 'Curtailment'].includes(c)) {
                     uniqueCarriers.add(c);
                }
            });


            if (uniqueCarriers.size === 0) {
                carrierColorsContainer.innerHTML = '<p class="text-muted">No carriers identified in the current network or existing palette. Load a network and its data first.</p>';
            } else {
                carrierColorsContainer.innerHTML = ''; // Clear loading/previous
                Array.from(uniqueCarriers).sort().forEach(carrier => {
                    // Ensure colorManager has a color for this carrier (it will generate if not present)
                    const initialColor = currentCarrierColors[carrier] || window.colorManager.getColor('carriers', carrier);
                    const itemHtml = `
                        <div class="color-config-item">
                            <label for="color-pypsa-carrier-${carrier}" title="${carrier}">${carrier}</label>
                            <input type="color" id="color-pypsa-carrier-${carrier}" data-category="carriers" data-item="${carrier}" value="${initialColor}">
                        </div>
                    `;
                    carrierColorsContainer.insertAdjacentHTML('beforeend', itemHtml);
                });
            }

            // Placeholder for technology/component colors - can be expanded later
            if (techColorsContainer) {
                 // Example: techColorsContainer.innerHTML = '<p>Specific component color settings would go here.</p>';
            }

            const modal = new bootstrap.Modal(document.getElementById('pypsaColorConfigModal'));
            modal.show();

        } catch (error) {
            console.error("Error populating PyPSA color settings modal:", error);
            showGlobalAlert(`Error loading color settings: ${error.message}`, 'danger');
            carrierColorsContainer.innerHTML = '<p class="text-danger">Error loading carrier colors.</p>';
        }
    }

    const pypsaColorSettingsBtn = document.getElementById('pypsaColorSettingsBtn');
    if (pypsaColorSettingsBtn) {
        pypsaColorSettingsBtn.addEventListener('click', showPypsaColorModal);
    }

    const savePypsaColorsBtn = document.getElementById('savePypsaColorsBtn');
    if (savePypsaColorsBtn) {
        savePypsaColorsBtn.addEventListener('click', async function() {
            if (!window.colorManager) {
                showGlobalAlert('Color management system is not initialized.', 'danger');
                return;
            }
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';

            const colorSavePromises = [];
            document.querySelectorAll('#carrierColorsConfigContent input[type="color"], #technologyColorsConfigContent input[type="color"]').forEach(input => {
                const category = input.dataset.category;
                const item = input.dataset.item;
                const newColor = input.value;
                colorSavePromises.push(window.colorManager.setColor(category, item, newColor));
            });

            try {
                await Promise.all(colorSavePromises);
                // await window.colorManager.loadColors(); // Ensure local cache is updated
                showGlobalAlert('PyPSA color configurations saved successfully.', 'success');

                const modalEl = document.getElementById('pypsaColorConfigModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                // Refresh charts to reflect new colors
                if (state.currentNetworkPath && analysisDashboard.style.display === 'block') {
                    showLoadingIndicatorsForDashboard();
                    reloadAllData(state.currentNetworkPath)
                        .catch(error => {
                            showGlobalAlert(`Error reloading data after color save: ${error.message}`, 'danger');
                        })
                        .finally(() => {
                            hideLoadingIndicatorsForDashboard();
                        });
                }
            } catch (error) {
                console.error('Error saving PyPSA color configurations:', error);
                showGlobalAlert(`Error saving colors: ${error.message}`, 'danger');
            } finally {
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-save me-1"></i> Save Colors';
            }
        });
    }
// Ensure this is placed before the closing }); of DOMContentLoaded or in a similar scope

});
