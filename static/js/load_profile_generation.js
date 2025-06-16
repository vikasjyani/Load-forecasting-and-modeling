// static/js/load_profile_generation.js
/**
 * Load Profile Generation Frontend Controller
 * Handles both Base Profile Scaling and STL decomposition methods
 *with dynamic constraint calculation and custom profile naming
 */

document.addEventListener('DOMContentLoaded', function () {
    console.log('Load Profile Generation: Initializing');

    // Application State
    const AppState = {
        selectedMethod: null,
        selectedDemandSource: null,
        selectedScenario: null,
        templateInfo: null,
        availableBaseYears: [],
        generationInProgress: false,
        currentJobId: null,
        generatedProfile: null
    };

    // API Base URL
    const API_BASE = '/load_profile/api';

    // Chart instances
    let profileChart = null;

    // Initialize application
    initialize();

    function initialize() {
        setupEventListeners();
        loadTemplateInfo();
        loadSavedProfiles();
        updateNamePreview(); // Initialize name preview
    }

    function setupEventListeners() {
        // Method selection
        document.querySelectorAll('.method-card').forEach(card => {
            card.addEventListener('click', function () {
                selectMethod(this.dataset.method);
            });
        });

        // Demand source selection
        document.querySelectorAll('.demand-source-card').forEach(card => {
            card.addEventListener('click', function () {
                selectDemandSource(this.dataset.source);
            });
        });

        // Form submission
        document.getElementById('configurationForm').addEventListener('submit', handleFormSubmission);

        // Base year preview
        document.getElementById('previewBaseYear')?.addEventListener('click', previewBaseYear);

        // Scenario selection
        document.getElementById('scenarioSelect')?.addEventListener('change', handleScenarioChange);

        // Year range validation
        document.getElementById('startFY')?.addEventListener('change', validateYearRange);
        document.getElementById('endFY')?.addEventListener('change', validateYearRange);

        // Custom name handling
        const customNameInput = document.getElementById('customProfileName');
        if (customNameInput) {
            customNameInput.addEventListener('input', function () {
                updateNamePreview();
                validateCustomName();
            });
            customNameInput.addEventListener('blur', validateCustomName);
            customNameInput.addEventListener('keyup', updateCharacterCounter);
        }

        // Saved profiles actions
        document.querySelectorAll('.view-profile').forEach(btn => {
            btn.addEventListener('click', function () {
                viewProfile(this.dataset.profileId);
            });
        });

        document.querySelectorAll('.download-profile').forEach(btn => {
            btn.addEventListener('click', function () {
                downloadProfile(this.dataset.profileId);
            });
        });

        document.querySelectorAll('.delete-profile').forEach(btn => {
            btn.addEventListener('click', function () {
                deleteProfile(this.dataset.profileId);
            });
        });

        // Results actions
        document.getElementById('downloadProfile')?.addEventListener('click', downloadGeneratedProfile);
        document.getElementById('generateAnother')?.addEventListener('click', resetForNewGeneration);

        // Cancel generation
        document.getElementById('cancelGeneration')?.addEventListener('click', cancelGeneration);
    }

    function selectMethod(method) {
        AppState.selectedMethod = method;

        // Update UI
        document.querySelectorAll('.method-card').forEach(card => {
            card.classList.remove('selected');
        });

        document.getElementById(method === 'base_profile_scaling' ? 'baseMethodCard' : 'stlMethodCard')
            .classList.add('selected');

        // Show configuration card
        document.getElementById('configurationCard').classList.remove('d-none');

        // Show/hide method-specific config
        const baseMethodConfig = document.getElementById('baseMethodConfig');
        const stlMethodConfig = document.getElementById('stlMethodConfig');
        const baseYearSelect = document.getElementById('baseYear');

        if (method === 'base_profile_scaling') {
            baseMethodConfig.classList.remove('d-none');
            stlMethodConfig.classList.add('d-none');

            // Make base year required for this method
            baseYearSelect.setAttribute('required', 'required');

            // Load available base years
            loadAvailableBaseYears();
        } else {
            baseMethodConfig.classList.add('d-none');
            stlMethodConfig.classList.remove('d-none');

            // Remove required attribute for STL method
            baseYearSelect.removeAttribute('required');
        }

        // Update name preview with new method
        updateNamePreview();

        showStatusAlert('info', `Selected method: ${method.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}`);
    }

    function selectDemandSource(source) {
        AppState.selectedDemandSource = source;

        // Update radio buttons
        document.querySelectorAll('input[name="demand_source"]').forEach(radio => {
            radio.checked = radio.value === source;
        });

        // Update card selection
        document.querySelectorAll('.demand-source-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-source="${source}"]`).classList.add('selected');

        // Show/hide scenario selection
        const scenarioSelection = document.getElementById('scenarioSelection');
        if (source === 'scenario') {
            scenarioSelection.style.display = 'block';
            document.getElementById('scenarioSelect').setAttribute('required', 'required');
        } else {
            scenarioSelection.style.display = 'none';
            document.getElementById('scenarioSelect').removeAttribute('required');
        }

        // Load source-specific information
        if (source === 'template') {
            loadTemplateInfo();
        }
    }

    // Custom Profile Naming Functions
    function updateNamePreview() {
        const customNameInput = document.getElementById('customProfileName');
        const namePreview = document.getElementById('namePreview');

        if (!customNameInput || !namePreview) return;

        const customName = customNameInput.value.trim();
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');

        if (customName) {
            // Sanitize name for preview
            const safeName = customName.replace(/[^a-zA-Z0-9\s\-_]/g, '').replace(/\s+/g, '_');
            const previewName = `${safeName}_${timestamp}`;

            namePreview.innerHTML = `
                <small class="text-success">
                    <i class="fas fa-check-circle me-1"></i>
                    <strong>${previewName}.csv</strong>
                </small>
            `;
        } else {
            // Show auto-generated name
            const method = AppState.selectedMethod || 'method';
            const autoName = `${method}_${timestamp}`;

            namePreview.innerHTML = `
                <small class="text-info">
                    <i class="fas fa-magic me-1"></i>
                    Auto: <strong>${autoName}.csv</strong>
                </small>
            `;
        }
    }

    function validateCustomName() {
        const customNameInput = document.getElementById('customProfileName');
        if (!customNameInput) return true;

        const customName = customNameInput.value.trim();

        if (customName) {
            // Check for invalid characters
            const invalidChars = /[^a-zA-Z0-9\s\-_]/g;
            if (invalidChars.test(customName)) {
                customNameInput.classList.add('is-invalid');
                customNameInput.classList.remove('is-valid');
                showStatusAlert('warning', 'Profile name contains invalid characters. Only letters, numbers, spaces, hyphens and underscores are allowed.');
                return false;
            }

            // Check length
            if (customName.length > 50) {
                customNameInput.classList.add('is-invalid');
                customNameInput.classList.remove('is-valid');
                showStatusAlert('warning', 'Profile name is too long. Maximum 50 characters allowed.');
                return false;
            }

            customNameInput.classList.remove('is-invalid');
            customNameInput.classList.add('is-valid');
        } else {
            customNameInput.classList.remove('is-invalid', 'is-valid');
        }

        return true;
    }

    function updateCharacterCounter() {
        const customNameInput = document.getElementById('customProfileName');
        if (!customNameInput) return;

        const currentLength = customNameInput.value.length;
        const maxLength = 50;

        // Remove existing counter
        const existingCounter = customNameInput.parentNode.querySelector('.char-counter');
        if (existingCounter) {
            existingCounter.remove();
        }

        // Add new counter if there's content
        if (currentLength > 0) {
            const counter = document.createElement('span');
            counter.className = 'char-counter';
            counter.textContent = `${currentLength}/${maxLength}`;

            if (currentLength > maxLength * 0.8) {
                counter.classList.add('warning');
            }
            if (currentLength > maxLength) {
                counter.classList.add('danger');
            }

            customNameInput.parentNode.style.position = 'relative';
            customNameInput.parentNode.appendChild(counter);
        }
    }

    async function loadTemplateInfo() {
        try {
            showLoading(true);
            const response = await fetch(`${API_BASE}/template_info`);
            const result = await response.json();

            if (result.status === 'success') {
                AppState.templateInfo = result.data;
                updateTemplateInfoDisplay();
                updateConstraintStatus();
            } else {
                throw new Error(result.message || 'Failed to load template info');
            }
        } catch (error) {
            console.error('Error loading template info:', error);
            showStatusAlert('danger', `Template info error: ${error.message}`);
            updateTemplateInfoDisplay(false);
        } finally {
            showLoading(false);
        }
    }

    function updateTemplateInfoDisplay(available = true) {
        const templateInfo = document.getElementById('templateInfo');

        if (available && AppState.templateInfo) {
            const info = AppState.templateInfo;
            templateInfo.innerHTML = `
                <small class="text-success">
                    <i class="fas fa-check-circle me-1"></i>
                    ${info.historical_data.records} records, 
                    ${info.historical_data.available_years.length} years available,
                    ${info.total_demand.years} demand scenarios
                </small>
            `;
        } else {
            templateInfo.innerHTML = `
                <small class="text-warning">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    Template file not found or invalid. Please upload load_curve_template.xlsx
                </small>
            `;
        }
    }

    function updateConstraintStatus() {
        if (!AppState.templateInfo) {
            // Set default disabled state
            const monthlyPeaksOption = document.getElementById('monthlyPeaksOption');
            const loadFactorsOption = document.getElementById('loadFactorsOption');

            monthlyPeaksOption.classList.add('disabled');
            loadFactorsOption.classList.add('disabled');

            document.getElementById('applyMonthlyPeaks').disabled = true;
            document.getElementById('applyLoadFactors').disabled = true;

            return;
        }

        const constraints = AppState.templateInfo.constraints_available;

        // Monthly peaks status
        const monthlyPeaksStatus = document.getElementById('monthlyPeaksStatus');
        const monthlyPeaksOption = document.getElementById('monthlyPeaksOption');
        const monthlyPeaksCheckbox = document.getElementById('applyMonthlyPeaks');

        if (constraints.monthly_peaks) {
            const source = constraints.monthly_peaks_source;
            const sourceText = source === 'template' ?
                'Available in template file' :
                'Will be calculated from historical data automatically';

            monthlyPeaksStatus.innerHTML = `
                <small class="text-success">
                    <i class="fas fa-check-circle me-1"></i>
                    ${sourceText}
                </small>
            `;
            monthlyPeaksOption.classList.remove('disabled');
            monthlyPeaksCheckbox.disabled = false;
        } else {
            monthlyPeaksStatus.innerHTML = `
                <small class="text-warning">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    No historical data available for calculation
                </small>
            `;
            monthlyPeaksOption.classList.add('disabled');
            monthlyPeaksCheckbox.disabled = true;
            monthlyPeaksCheckbox.checked = false;
        }

        // Load factors status
        const loadFactorsStatus = document.getElementById('loadFactorsStatus');
        const loadFactorsOption = document.getElementById('loadFactorsOption');
        const loadFactorsCheckbox = document.getElementById('applyLoadFactors');

        if (constraints.monthly_load_factors) {
            const source = constraints.load_factors_source;
            const sourceText = source === 'template' ?
                'Available in template file' :
                'Will be calculated from historical data automatically';

            loadFactorsStatus.innerHTML = `
                <small class="text-success">
                    <i class="fas fa-check-circle me-1"></i>
                    ${sourceText}
                </small>
            `;
            loadFactorsOption.classList.remove('disabled');
            loadFactorsCheckbox.disabled = false;
        } else {
            loadFactorsStatus.innerHTML = `
                <small class="text-warning">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    No historical data available for calculation
                </small>
            `;
            loadFactorsOption.classList.add('disabled');
            loadFactorsCheckbox.disabled = true;
            loadFactorsCheckbox.checked = false;
        }
    }

    async function loadAvailableBaseYears() {
        try {
            const response = await fetch(`${API_BASE}/available_base_years`);
            const result = await response.json();

            if (result.status === 'success') {
                AppState.availableBaseYears = result.data.available_years;
                updateBaseYearSelect();
            } else {
                throw new Error(result.message || 'Failed to load available years');
            }
        } catch (error) {
            console.error('Error loading available base years:', error);
            showStatusAlert('warning', `Could not load base years: ${error.message}`);
        }
    }

    function updateBaseYearSelect() {
        const baseYearSelect = document.getElementById('baseYear');
        baseYearSelect.innerHTML = '<option value="">Select base year...</option>';

        AppState.availableBaseYears.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `FY ${year} (${year - 1}-${year})`;
            baseYearSelect.appendChild(option);
        });

        // Pre-select most recent year
        if (AppState.availableBaseYears.length > 0) {
            baseYearSelect.value = AppState.availableBaseYears[AppState.availableBaseYears.length - 1];
        }
    }

    async function previewBaseYear() {
        const baseYear = document.getElementById('baseYear').value;
        if (!baseYear) {
            showStatusAlert('warning', 'Please select a base year first');
            return;
        }

        try {
            showLoading(true);
            const response = await fetch(`${API_BASE}/preview_base_profiles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base_year: parseInt(baseYear) })
            });

            const result = await response.json();

            if (result.status === 'success') {
                displayBaseYearPreview(result.data);
            } else {
                throw new Error(result.message || 'Failed to generate preview');
            }
        } catch (error) {
            console.error('Error previewing base year:', error);
            showStatusAlert('danger', `Preview error: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function displayBaseYearPreview(previewData) {
        const modal = new bootstrap.Modal(document.getElementById('baseYearPreviewModal'));
        const content = document.getElementById('baseYearPreviewContent');

        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Preview Summary</h6>
                    <ul class="list-group mb-3">
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Base Year:</span>
                            <strong>FY ${previewData.base_year}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Total Patterns:</span>
                            <strong>${previewData.total_patterns}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Weekday Patterns:</span>
                            <strong>${previewData.patterns_by_type.weekday_patterns}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Weekend/Holiday Patterns:</span>
                            <strong>${previewData.patterns_by_type.weekend_holiday_patterns}</strong>
                        </li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h6>Monthly Peak Fractions</h6>
                    <div class="bg-light p-3 rounded">
                        ${Object.entries(previewData.monthly_peaks).map(([month, peak]) =>
            `<div class="d-flex justify-content-between">
                                <span>Month ${month}:</span>
                                <strong>${(peak * 100).toFixed(1)}%</strong>
                            </div>`
        ).join('')}
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-12">
                    <h6>Sample Daily Patterns</h6>
                    <canvas id="previewChart" width="800" height="300"></canvas>
                </div>
            </div>
        `;

        // Create preview chart
        setTimeout(() => {
            createPreviewChart(previewData.sample_patterns);
        }, 100);

        modal.show();
    }

    function createPreviewChart(samplePatterns) {
        const canvas = document.getElementById('previewChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        const datasets = [];
        const months = ['Apr', 'Jul', 'Oct', 'Jan'];
        const colors = ['#6366f1', '#ef4444', '#10b981', '#f59e0b'];

        samplePatterns.forEach((pattern, index) => {
            if (pattern.weekday.length > 0) {
                datasets.push({
                    label: `${months[index]} Weekday`,
                    data: pattern.weekday.map(p => ({ x: p.hour, y: p.fraction })),
                    borderColor: colors[index],
                    backgroundColor: colors[index] + '20',
                    fill: false,
                    tension: 0.4
                });
            }

            if (pattern.weekend.length > 0) {
                datasets.push({
                    label: `${months[index]} Weekend`,
                    data: pattern.weekend.map(p => ({ x: p.hour, y: p.fraction })),
                    borderColor: colors[index],
                    backgroundColor: colors[index] + '20',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4
                });
            }
        });

        new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        min: 0,
                        max: 23,
                        title: { display: true, text: 'Hour of Day' }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Load Fraction' }
                    }
                },
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'Sample Load Patterns by Month and Day Type' }
                }
            }
        });
    }

    async function handleScenarioChange() {
        const scenarioName = document.getElementById('scenarioSelect').value;
        if (!scenarioName) return;

        try {
            const response = await fetch(`${API_BASE}/scenario_info/${scenarioName}`);
            const result = await response.json();

            if (result.status === 'success') {
                AppState.selectedScenario = result.data;
                showStatusAlert('success', `Scenario "${scenarioName}" loaded with ${result.data.data_summary.total_years} years of data`);
            } else {
                throw new Error(result.message || 'Failed to load scenario info');
            }
        } catch (error) {
            console.error('Error loading scenario:', error);
            showStatusAlert('danger', `Scenario error: ${error.message}`);
        }
    }

    function validateYearRange() {
        const startFY = parseInt(document.getElementById('startFY').value);
        const endFY = parseInt(document.getElementById('endFY').value);

        if (startFY && endFY && startFY >= endFY) {
            showStatusAlert('warning', 'End year must be greater than start year');
            return false;
        }

        return true;
    }

    async function handleFormSubmission(event) {
        event.preventDefault();

        if (!validateForm()) {
            return;
        }

        const formData = new FormData(event.target);
        const config = Object.fromEntries(formData.entries());

        // Add method and other state
        config.method = AppState.selectedMethod;
        config.demand_source = AppState.selectedDemandSource;

        // Add custom name if provided
        const customName = document.getElementById('customProfileName')?.value.trim();
        if (customName) {
            config.custom_name = customName;
        }

        // Only include base_year for base_profile_scaling method
        if (AppState.selectedMethod === 'base_profile_scaling') {
            const baseYear = document.getElementById('baseYear').value;
            if (baseYear) {
                config.base_year = parseInt(baseYear);
            }
        }

        // Process STL parameters only for STL method
        if (AppState.selectedMethod === 'stl_decomposition') {
            config.stl_params = {
                period: parseInt(config.stl_period) || 8760,
                seasonal: parseInt(config.stl_seasonal) || 13,
                robust: config.stl_robust === 'true'
            };

            // Remove STL parameters from main config
            delete config.stl_period;
            delete config.stl_seasonal;
            delete config.stl_robust;
        }

        // Process constraints - Convert checkbox values to booleans
        config.apply_monthly_peaks = document.getElementById('applyMonthlyPeaks')?.checked || false;
        config.apply_load_factors = document.getElementById('applyLoadFactors')?.checked || false;

        await generateProfile(config);
    }


    function validateForm() {
        if (!AppState.selectedMethod) {
            showStatusAlert('warning', 'Please select a generation method');
            return false;
        }

        if (!AppState.selectedDemandSource) {
            showStatusAlert('warning', 'Please select a demand data source');
            return false;
        }

        if (AppState.selectedDemandSource === 'scenario' && !document.getElementById('scenarioSelect').value) {
            showStatusAlert('warning', 'Please select a demand scenario');
            return false;
        }

        // Validate custom name
        if (!validateCustomName()) {
            return false;
        }

        // Fix: Only validate base year for base_profile_scaling method
        if (AppState.selectedMethod === 'base_profile_scaling') {
            const baseYearSelect = document.getElementById('baseYear');
            if (!baseYearSelect.value) {
                showStatusAlert('warning', 'Please select a base year for Base Profile Scaling method');
                // Focus on the base year select to help user
                baseYearSelect.focus();
                return false;
            }
        }

        if (!validateYearRange()) {
            return false;
        }

        return true;
    }

    async function generateProfile(config) {
        try {
            AppState.generationInProgress = true;
            showProgressSection();

            // Update progress message to include profile name
            const profileName = config.custom_name || 'Auto-generated name';
            updateProgress(0, `Initializing profile generation: "${profileName}"`);

            // Select API endpoint based on method
            const endpoint = config.method === 'base_profile_scaling' ?
                '/generate_base_profile' : '/generate_stl_profile';

            updateProgress(25, 'Sending configuration to server...');

            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.status === 'success') {
                updateProgress(100, 'Profile generated and saved successfully!');
                AppState.generatedProfile = result.data;

                // Show save information
                if (result.data.save_info) {
                    const saveInfo = result.data.save_info;
                    showStatusAlert('success',
                        `Profile saved as "${saveInfo.profile_id}.csv" (${saveInfo.file_size.toFixed(1)} MB)`,
                        8000
                    );
                }

                setTimeout(() => {
                    hideProgressSection();
                    displayResults();
                    // Refresh saved profiles table
                    loadSavedProfiles();
                }, 1000);
            } else {
                throw new Error(result.message || 'Generation failed');
            }

        } catch (error) {
            console.error('Error generating profile:', error);
            showStatusAlert('danger', `Generation failed: ${error.message}`);
            hideProgressSection();
        } finally {
            AppState.generationInProgress = false;
        }
    }

    function showProgressSection() {
        document.getElementById('progressContainer').style.display = 'block';
        document.getElementById('configurationCard').classList.add('d-none');
        document.getElementById('methodSelectionCard').classList.add('d-none');
    }

    function hideProgressSection() {
        document.getElementById('progressContainer').style.display = 'none';
        document.getElementById('configurationCard').classList.remove('d-none');
        document.getElementById('methodSelectionCard').classList.remove('d-none');
    }

    function updateProgress(percent, message) {
        const progressBar = document.getElementById('progressBar');
        const progressMessage = document.getElementById('progressMessage');

        progressBar.style.width = `${percent}%`;
        progressBar.textContent = `${percent}%`;
        progressMessage.textContent = message;

        // Update step indicators
        const steps = document.querySelectorAll('.step');
        steps.forEach((step, index) => {
            if (percent >= (index + 1) * 25) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (percent >= index * 25) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }

    function displayResults() {
        const resultsCard = document.getElementById('resultsCard');
        resultsCard.classList.remove('d-none');

        // Update statistics
        updateProfileStatistics();

        // Update validation results
        updateValidationResults();

        // Create chart
        createProfileChart();

        // Scroll to results
        resultsCard.scrollIntoView({ behavior: 'smooth' });
    }

    function updateProfileStatistics() {
        if (!AppState.generatedProfile || !AppState.generatedProfile.validation) return;

        const stats = AppState.generatedProfile.validation.general_stats;
        const metadata = AppState.generatedProfile.metadata;

        document.getElementById('profileStats').innerHTML = `
            <div class="row">
                <div class="col-6 mb-2">
                    <small class="text-muted">Total Hours:</small>
                    <div class="fw-bold">${stats.total_hours.toLocaleString()}</div>
                </div>
                <div class="col-6 mb-2">
                    <small class="text-muted">Peak Demand:</small>
                    <div class="fw-bold">${stats.peak_demand.toFixed(1)} MW</div>
                </div>
                <div class="col-6 mb-2">
                    <small class="text-muted">Min Demand:</small>
                    <div class="fw-bold">${stats.min_demand.toFixed(1)} MW</div>
                </div>
                <div class="col-6 mb-2">
                    <small class="text-muted">Avg Demand:</small>
                    <div class="fw-bold">${stats.avg_demand.toFixed(1)} MW</div>
                </div>
                <div class="col-12 mb-2">
                    <small class="text-muted">Load Factor:</small>
                    <div class="fw-bold">${(stats.overall_load_factor * 100).toFixed(1)}%</div>
                </div>
                <div class="col-12">
                    <small class="text-muted">Method:</small>
                    <div class="fw-bold">${AppState.generatedProfile.method.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                </div>
            </div>
        `;
    }

    function updateValidationResults() {
        if (!AppState.generatedProfile || !AppState.generatedProfile.validation) return;

        const validation = AppState.generatedProfile.validation;
        let validationHTML = '';

        // Annual totals validation
        if (validation.annual_totals && Object.keys(validation.annual_totals).length > 0) {
            validationHTML += '<h6 class="mb-2">Annual Total Validation</h6>';

            Object.entries(validation.annual_totals).forEach(([year, data]) => {
                const diffClass = data.difference_percent < 1 ? 'text-success' :
                    data.difference_percent < 5 ? 'text-warning' : 'text-danger';

                validationHTML += `
                    <div class="d-flex justify-content-between mb-1">
                        <small>${year}:</small>
                        <small class="${diffClass}">${data.difference_percent.toFixed(2)}% diff</small>
                    </div>
                `;
            });
        } else {
            validationHTML = '<p class="text-muted">No validation data available</p>';
        }

        document.getElementById('validationResults').innerHTML = validationHTML;
    }

    function createProfileChart() {
        if (!AppState.generatedProfile || !AppState.generatedProfile.forecast) return;

        const canvas = document.getElementById('profileChart');
        const ctx = canvas.getContext('2d');

        // Destroy existing chart
        if (profileChart) {
            profileChart.destroy();
        }

        const forecastData = AppState.generatedProfile.forecast;

        // Sample data for visualization (show first month to avoid performance issues)
        const sampleData = forecastData.slice(0, 24 * 30); // First 30 days

        const labels = sampleData.map((_, index) => {
            const date = new Date(2025, 3, 1); // Start from April 1, 2025
            date.setHours(date.getHours() + index);
            return date;
        });

        const data = sampleData.map(row => row.demand);

        profileChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Load Profile',
                    data: data,
                    borderColor: '#6366f1',
                    backgroundColor: '#6366f1' + '20',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MMM DD'
                            }
                        },
                        title: { display: true, text: 'Date' }
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Demand (MW)' }
                    }
                },
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Generated Load Profile (Sample: First 30 Days)'
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    async function downloadGeneratedProfile() {
        if (!AppState.generatedProfile || !AppState.generatedProfile.save_info) {
            showStatusAlert('warning', 'No profile to download');
            return;
        }

        const profileId = AppState.generatedProfile.save_info.profile_id;
        window.location.href = `${API_BASE}/download_profile/${profileId}`;
        showStatusAlert('success', 'Download started');
    }

    function resetForNewGeneration() {
        // Reset state
        AppState.selectedMethod = null;
        AppState.selectedDemandSource = null;
        AppState.generatedProfile = null;

        // Reset UI
        document.querySelectorAll('.method-card').forEach(card => card.classList.remove('selected'));
        document.querySelectorAll('.demand-source-card').forEach(card => card.classList.remove('selected'));
        document.getElementById('configurationCard').classList.add('d-none');
        document.getElementById('resultsCard').classList.add('d-none');
        document.getElementById('configurationForm').reset();

        // Clear custom name input and preview
        const customNameInput = document.getElementById('customProfileName');
        const namePreview = document.getElementById('namePreview');
        if (customNameInput) {
            customNameInput.value = '';
            customNameInput.classList.remove('is-valid', 'is-invalid');
        }
        if (namePreview) {
            namePreview.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-info-circle me-1"></i>
                    Preview will appear here
                </small>
            `;
        }

        // Remove character counter
        const existingCounter = document.querySelector('.char-counter');
        if (existingCounter) {
            existingCounter.remove();
        }

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function cancelGeneration() {
        if (AppState.generationInProgress) {
            AppState.generationInProgress = false;
            hideProgressSection();
            showStatusAlert('info', 'Generation cancelled');
        }
    }

    async function loadSavedProfiles() {
        try {
            const response = await fetch(`${API_BASE}/saved_profiles`);
            const result = await response.json();

            if (result.status === 'success') {
                updateSavedProfilesTable(result.data.profiles);
            }
        } catch (error) {
            console.error('Error loading saved profiles:', error);
        }
    }

    function updateSavedProfilesTable(profiles) {
        const tbody = document.querySelector('#savedProfilesTable tbody');

        if (profiles.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <i class="fas fa-info-circle me-2"></i>No saved profiles found. Generate your first load profile above.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = profiles.map(profile => {
            // Determine if this is a custom named profile
            const isCustom = profile.profile_id && !profile.profile_id.match(/^(base_profile_scaling|stl_decomposition)_\d{8}_\d{6}$/);
            const badgeColor = profile.method === 'base_profile_scaling' ? 'primary' : 'success';
            const customBadge = isCustom ? '<span class="badge bg-info ms-1">Custom</span>' : '';

            return `
                <tr class="${isCustom ? 'profile-custom' : ''}">
                    <td>
                        <strong>${profile.profile_id}</strong>${customBadge}
                        <br><small class="text-muted">${profile.method || 'Unknown'}</small>
                    </td>
                    <td>
                        <span class="badge bg-${badgeColor}">
                            ${(profile.method || 'Unknown').replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </span>
                    </td>
                    <td>${profile.generated_at ? profile.generated_at.substring(0, 10) : 'Unknown'}</td>
                    <td>${profile.start_fy || 'N/A'} - ${profile.end_fy || 'N/A'}</td>
                    <td>${(profile.file_info?.size_mb || 0).toFixed(1)} MB</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary view-profile" data-profile-id="${profile.profile_id}" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-success download-profile" data-profile-id="${profile.profile_id}" title="Download CSV">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn btn-outline-danger delete-profile" data-profile-id="${profile.profile_id}" title="Delete Profile">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        // Re-attach event listeners
        tbody.querySelectorAll('.view-profile').forEach(btn => {
            btn.addEventListener('click', function () {
                viewProfile(this.dataset.profileId);
            });
        });

        tbody.querySelectorAll('.download-profile').forEach(btn => {
            btn.addEventListener('click', function () {
                downloadProfile(this.dataset.profileId);
            });
        });

        tbody.querySelectorAll('.delete-profile').forEach(btn => {
            btn.addEventListener('click', function () {
                deleteProfile(this.dataset.profileId);
            });
        });
    }

    async function viewProfile(profileId) {
        try {
            showLoading(true);
            const response = await fetch(`${API_BASE}/profile_data/${profileId}`);
            const result = await response.json();

            if (result.status === 'success') {
                displayProfileView(result.data);
            } else {
                throw new Error(result.message || 'Failed to load profile');
            }
        } catch (error) {
            console.error('Error viewing profile:', error);
            showStatusAlert('danger', `Failed to view profile: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function displayProfileView(profileData) {
        const modal = new bootstrap.Modal(document.getElementById('profileViewModal'));
        const content = document.getElementById('profileViewContent');

        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Profile Information</h6>
                    <ul class="list-group mb-3">
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Profile ID:</span>
                            <strong>${profileData.profile_id}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Total Records:</span>
                            <strong>${profileData.data_summary.total_records.toLocaleString()}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>File Size:</span>
                            <strong>${profileData.file_info.size_mb.toFixed(1)} MB</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Date Range:</span>
                            <strong>${profileData.data_summary.date_range?.start || 'N/A'} to ${profileData.data_summary.date_range?.end || 'N/A'}</strong>
                        </li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h6>Demand Statistics</h6>
                    <ul class="list-group mb-3">
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Peak:</span>
                            <strong>${profileData.data_summary.demand_stats?.max.toFixed(1) || 'N/A'} kW</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Minimum:</span>
                            <strong>${profileData.data_summary.demand_stats?.min.toFixed(1) || 'N/A'} kW</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Average:</span>
                            <strong>${profileData.data_summary.demand_stats?.mean.toFixed(1) || 'N/A'} kW</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Load Factor:</span>
                            <strong>${profileData.data_summary.demand_stats ? (profileData.data_summary.demand_stats.mean / profileData.data_summary.demand_stats.max * 100).toFixed(1) + '%' : 'N/A'}</strong>
                        </li>
                    </ul>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <h6>Sample Data (First 50 Records)</h6>
                    <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                        <table class="table table-sm table-striped">
                            <thead class="table-dark">
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Demand (kW)</th>
                                    <th>Fiscal Year</th>
                                    <th>Hour</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${profileData.sample_data?.slice(0, 50).map(row => `
                                    <tr>
                                        <td>${row.datetime || row.ds || 'N/A'}</td>
                                        <td>${row['Demand (kW)'] ? parseFloat(row['Demand (kW)']).toFixed(2) : (row.demand ? parseFloat(row.demand).toFixed(2) : 'N/A')}</td>
                                        <td>${row.Fiscal_Year || row.financial_year || 'N/A'}</td>
                                        <td>${row.Hour || row.hour || 'N/A'}</td>
                                    </tr>
                                `).join('') || '<tr><td colspan="4">No sample data available</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        // Update the modal footer to include the Deep Analysis button
        const modalFooter = document.querySelector('#profileViewModal .modal-footer');
        if (modalFooter) {
            modalFooter.innerHTML = `
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="fas fa-times me-2"></i>Close
                </button>
                <button type="button" class="btn btn-primary" onclick="redirectToDeepAnalysis('${profileData.profile_id}')">
                    <i class="fas fa-chart-line me-2"></i>Deep Analysis
                </button>
            `;
        }

        modal.show();
    }

    // Add this function to handle the redirect to load profile visualization
    function redirectToDeepAnalysis(profileId) {
        // Store the selected profile in localStorage for the analysis page
        localStorage.setItem('selectedProfileForAnalysis', profileId);

        // Close the modal first
        const modal = bootstrap.Modal.getInstance(document.getElementById('profileViewModal'));
        if (modal) {
            modal.hide();
        }

        // Show loading indicator
        if (typeof showLoading === 'function') {
            showLoading(true);
        }

        // Redirect to load profile analysis page
        // Adjust the URL based on your routing structure
        // window.location.href = '/load_profile_analysis/';

        // Alternative: if you need to pass the profile ID as a parameter
        window.location.href = `/load_profile_analysis/?profile=${encodeURIComponent(profileId)}`;
    }


    async function downloadProfile(profileId) {
        try {
            window.location.href = `${API_BASE}/download_profile/${profileId}`;
            showStatusAlert('success', 'Download started');
        } catch (error) {
            console.error('Error downloading profile:', error);
            showStatusAlert('danger', `Download failed: ${error.message}`);
        }
    }

    async function deleteProfile(profileId) {
        if (!confirm(`Are you sure you want to delete profile "${profileId}"? This action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/delete_profile/${profileId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.status === 'success') {
                showStatusAlert('success', `Profile "${profileId}" deleted successfully`);
                loadSavedProfiles(); // Refresh the table
            } else {
                throw new Error(result.message || 'Failed to delete profile');
            }
        } catch (error) {
            console.error('Error deleting profile:', error);
            showStatusAlert('danger', `Failed to delete profile: ${error.message}`);
        }
    }

    // Utility Functions
    function showLoading(show) {
        document.body.style.cursor = show ? 'wait' : 'default';

        if (typeof window.showLoading === 'function') {
            window.showLoading(show);
        }
    }

    function showStatusAlert(type, message, duration = 5000) {
        const alert = document.getElementById('statusAlert');
        const messageSpan = document.getElementById('statusMessage');

        alert.className = `alert alert-${type} alert-dismissible fade show`;
        messageSpan.textContent = message;
        alert.classList.remove('d-none');

        if (duration > 0) {
            setTimeout(() => {
                alert.classList.add('d-none');
            }, duration);
        }

        console.log(`[LoadProfile] ${type.toUpperCase()}: ${message}`);
    }
    window.redirectToDeepAnalysis = redirectToDeepAnalysis;
});
