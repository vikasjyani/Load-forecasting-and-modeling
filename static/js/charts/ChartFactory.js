/**
 * EnergyCharts - Enhanced Universal Chart Factory for KSEB Energy Futures Platform
 * Supports Chart.js, ECharts, and Plotly with unified API and color management integration
 */

window.EnergyCharts = (function() {
    'use strict';

    // Private variables
    let chartInstances = new Map();
    let defaultTheme = 'energy-default';
    let chartCounter = 0;
    let colorManager = null;
    let colorIntegration = null;

    // Library availability check
    const libraryAvailable = {
        chartjs: typeof Chart !== 'undefined',
        echarts: typeof echarts !== 'undefined',
        plotly: typeof Plotly !== 'undefined'
    };

    // Module-specific chart configurations
    const moduleConfigs = {
        'demand_projection': {
            defaultColors: 'models',
            preferredLibrary: 'chartjs'
        },
        'demand_visualization': {
            defaultColors: 'sectors',
            preferredLibrary: 'chartjs'
        },
        'load_profile': {
            defaultColors: 'carriers',
            preferredLibrary: 'plotly'
        },
        'pypsa': {
            defaultColors: 'pypsa',
            preferredLibrary: 'plotly'
        }
    };

    // Initialize color manager integration
     function initializeColorManager(manager) {
         colorManager = manager;
         if (manager && typeof ColorManagerIntegration !== 'undefined') {
             colorIntegration = new ColorManagerIntegration(manager);
         }
     }

     /**
      * Apply color management to chart data (async version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @param {string} library - Chart library
      * @param {string} type - Chart type
      * @returns {Promise<Object>} Enhanced data with colors
      */
     async function applyColorManagement(data, category, library, type) {
         if (!colorIntegration) return data;
         
         switch (library) {
             case 'chartjs':
                 return await applyChartJSColors(data, category, type);
             case 'plotly':
                 return await applyPlotlyColors(data, category);
             case 'echarts':
                 return await applyEChartsColors(data, category);
             default:
                 return data;
         }
     }

     /**
      * Apply color management to chart data (sync version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @param {string} library - Chart library
      * @param {string} type - Chart type
      * @returns {Object} Enhanced data with colors
      */
     function applyColorManagementSync(data, category, library, type) {
         if (!colorIntegration) return data;
         
         switch (library) {
             case 'chartjs':
                 return applyChartJSColorsSync(data, category, type);
             case 'plotly':
                 return applyPlotlyColorsSync(data, category);
             case 'echarts':
                 return applyEChartsColorsSync(data, category);
             default:
                 return data;
         }
     }

     /**
      * Apply Chart.js specific colors (async version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @param {string} type - Chart type
      * @returns {Promise<Object>} Enhanced data
      */
     async function applyChartJSColors(data, category, type) {
         if (!data.datasets) return data;
         
         const enhancedData = { ...data };
         enhancedData.datasets = [];
         
         for (const dataset of data.datasets) {
             const labels = dataset.label ? [dataset.label] : data.labels || [];
             const enhancedDataset = await colorIntegration.createEnergyDataset({
                 ...dataset,
                 labels: labels,
                 category: category,
                 type: type
             });
             enhancedData.datasets.push(enhancedDataset);
         }
         
         return enhancedData;
     }

     /**
      * Apply Chart.js specific colors (sync version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @param {string} type - Chart type
      * @returns {Object} Enhanced data
      */
     function applyChartJSColorsSync(data, category, type) {
         if (!data.datasets) return data;
         
         const enhancedData = { ...data };
         enhancedData.datasets = data.datasets.map((dataset, index) => {
             const labels = dataset.label ? [dataset.label] : data.labels || [];
             return colorIntegration.createEnergyDatasetSync({
                 ...dataset,
                 labels: labels,
                 category: category,
                 type: type
             });
         });
         
         return enhancedData;
     }

     /**
      * Apply Plotly specific colors (async version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @returns {Promise<Object>} Enhanced data
      */
     async function applyPlotlyColors(data, category) {
         if (!Array.isArray(data)) return data;
         
         const enhancedData = [];
         for (const trace of data) {
             const enhancedTrace = { ...trace };
             if (trace.name && category) {
                 const colors = await colorIntegration.getEnergyColors(category, [trace.name]);
                 enhancedTrace.marker = {
                     ...enhancedTrace.marker,
                     color: colors[0]
                 };
             }
             enhancedData.push(enhancedTrace);
         }
         
         return enhancedData;
     }

     /**
      * Apply Plotly specific colors (sync version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @returns {Object} Enhanced data
      */
     function applyPlotlyColorsSync(data, category) {
         if (!Array.isArray(data)) return data;
         
         return data.map(trace => {
             const enhancedTrace = { ...trace };
             if (trace.name && category) {
                 const colors = colorIntegration.getEnergyColorsSync(category, [trace.name]);
                 enhancedTrace.marker = {
                     ...enhancedTrace.marker,
                     color: colors[0]
                 };
             }
             return enhancedTrace;
         });
     }

     /**
      * Apply ECharts specific colors (async version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @returns {Promise<Object>} Enhanced data
      */
     async function applyEChartsColors(data, category) {
         // ECharts colors are typically applied at the option level
         return data;
     }

     /**
      * Apply ECharts specific colors (sync version)
      * @param {Object} data - Chart data
      * @param {string} category - Color category
      * @returns {Object} Enhanced data
      */
     function applyEChartsColorsSync(data, category) {
         // ECharts colors are typically applied at the option level
         return data;
     }

     /**
      * Apply theme-specific options
      * @param {Object} options - Chart options
      * @param {string} library - Chart library
      * @returns {Object} Enhanced options
      */
     function applyThemeOptions(options, library) {
         if (!colorIntegration) return options;
         
         const enhanced = { ...options };
         
         switch (library) {
             case 'chartjs':
                 enhanced.plugins = {
                     ...enhanced.plugins,
                     legend: {
                         ...enhanced.plugins?.legend,
                         labels: {
                             ...enhanced.plugins?.legend?.labels,
                             color: colorManager?.getColor('theme.text')
                         }
                     }
                 };
                 break;
             case 'plotly':
                 enhanced.layout = {
                     ...enhanced.layout,
                     paper_bgcolor: colorManager?.getColor('theme.background'),
                     plot_bgcolor: colorManager?.getColor('theme.surface'),
                     font: {
                         ...enhanced.layout?.font,
                         color: colorManager?.getColor('theme.text')
                     }
                 };
                 break;
             case 'echarts':
                 enhanced.backgroundColor = colorManager?.getColor('theme.background');
                 enhanced.textStyle = {
                     ...enhanced.textStyle,
                     color: colorManager?.getColor('theme.text')
                 };
                 break;
         }
         
         return enhanced;
     }

     /**
      * Get preferred library for chart type and module
      * @param {string} type - Chart type
      * @param {string} module - Module name
      * @returns {string} Preferred library
      */
     function getPreferredLibrary(type, module = null) {
         // Check module preference first
         if (module && moduleConfigs[module]) {
             const moduleConfig = moduleConfigs[module];
             if (moduleConfig.preferredLibrary) {
                 return moduleConfig.preferredLibrary;
             }
         }
         
         // Fall back to type preference
         return libraryPreferences[type] || defaultLibrary;
     }

     /**
      * Refresh chart with current color scheme
      * @param {string} chartId - Chart ID
      */
     function refreshChart(chartId) {
         const chartData = chartInstances.get(chartId);
         if (!chartData) return;
         
         const { data, options, config, module, category } = chartData;
         
         // Reapply color management
         if (colorIntegration && module && category) {
             const enhancedData = applyColorManagement(data, category, chartData.library, chartData.type);
             const enhancedOptions = applyThemeOptions(options, chartData.library);
             
             updateChart(chartId, enhancedData, enhancedOptions);
         }
     }

    /**
     * Enhanced chart creation function with color management integration
     * @param {string} containerId - DOM element ID for chart container
     * @param {Object} config - Chart configuration object
     * @returns {Object} Chart instance with methods
     */
    function create(containerId, config) {
        try {
            // Validate inputs
            if (!containerId || !config) {
                throw new Error('Container ID and config are required');
            }

            const container = document.getElementById(containerId);
            if (!container) {
                throw new Error(`Container with ID '${containerId}' not found`);
            }

            // Process and validate configuration
            const processedConfig = ChartUtils.validateConfig(config);
            const chartType = processedConfig.type;
            
            // Get chart configuration template
            const chartConfig = CHART_CONFIGS[chartType];
            if (!chartConfig) {
                throw new Error(`Unsupported chart type: ${chartType}`);
            }

            // Determine best library for this chart type
            const library = processedConfig.library || 
                           chartConfig.defaultLibrary || 
                           detectBestLibrary(chartType);

            if (!libraryAvailable[library]) {
                throw new Error(`Library '${library}' is not available`);
            }

            // Generate unique chart ID
            const chartId = processedConfig.id || `chart_${++chartCounter}`;

            // Process data
            const processedData = ChartUtils.processData(processedConfig.data, chartType, library);

            // Build library-specific configuration
            const finalConfig = buildLibraryConfig(chartType, library, processedData, processedConfig);

            // Create chart instance
            const chartInstance = createChartInstance(container, library, finalConfig, chartId);

            // Store instance for management
            chartInstances.set(chartId, {
                instance: chartInstance,
                library: library,
                type: chartType,
                container: container,
                config: processedConfig
            });

            // Return chart wrapper with methods
            return createChartWrapper(chartId, chartInstance, library);

        } catch (error) {
            console.error('EnergyCharts Creation Error:', error);
            throw error;
        }
    }

    /**
     * Update existing chart with new data
     * @param {string} chartId - Chart instance ID
     * @param {Object} newData - New data object
     * @param {Object} options - Update options
     */
    function update(chartId, newData, options = {}) {
        const chartData = chartInstances.get(chartId);
        if (!chartData) {
            throw new Error(`Chart with ID '${chartId}' not found`);
        }

        const { instance, library, type } = chartData;
        const processedData = ChartUtils.processData(newData, type, library);

        switch (library) {
            case 'chartjs':
                updateChartJS(instance, processedData, options);
                break;
            case 'echarts':
                updateECharts(instance, processedData, options);
                break;
            case 'plotly':
                updatePlotly(instance, processedData, options);
                break;
        }
    }

    /**
     * Destroy chart instance and cleanup
     * @param {string} chartId - Chart instance ID
     */
    function destroy(chartId) {
        const chartData = chartInstances.get(chartId);
        if (!chartData) {
            return false;
        }

        const { instance, library } = chartData;

        switch (library) {
            case 'chartjs':
                if (instance && typeof instance.destroy === 'function') {
                    instance.destroy();
                }
                break;
            case 'echarts':
                if (instance && typeof instance.dispose === 'function') {
                    instance.dispose();
                }
                break;
            case 'plotly':
                if (instance && typeof Plotly.purge === 'function') {
                    Plotly.purge(chartData.container);
                }
                break;
        }

        chartInstances.delete(chartId);
        return true;
    }

    /**
     * Get chart instance by ID
     * @param {string} chartId - Chart instance ID
     * @returns {Object} Chart instance data
     */
    function getInstance(chartId) {
        return chartInstances.get(chartId);
    }

    /**
     * Detect best library for chart type
     * @param {string} chartType - Type of chart
     * @returns {string} Library name
     */
    function detectBestLibrary(chartType) {
        const preferences = {
            'line': 'chartjs',
            'bar': 'chartjs',
            'pie': 'chartjs',
            'doughnut': 'chartjs',
            'area': 'chartjs',
            'timeseries': 'echarts',
            'heatmap': 'plotly',
            'scatter': 'chartjs',
            'radar': 'chartjs',
            'sankey': 'echarts',
            'gauge': 'echarts',
            'funnel': 'echarts'
        };

        const preferred = preferences[chartType] || 'chartjs';
        
        // Return first available library, preferring the optimal one
        if (libraryAvailable[preferred]) return preferred;
        if (libraryAvailable.chartjs) return 'chartjs';
        if (libraryAvailable.echarts) return 'echarts';
        if (libraryAvailable.plotly) return 'plotly';
        
        throw new Error('No chart libraries available');
    }

    /**
     * Build library-specific configuration
     * @param {string} chartType - Chart type
     * @param {string} library - Target library
     * @param {Object} data - Processed data
     * @param {Object} config - User configuration
     * @returns {Object} Library-specific configuration
     */
    function buildLibraryConfig(chartType, library, data, config) {
        const baseConfig = CHART_CONFIGS[chartType];
        const libraryConfig = baseConfig.libraryMappings[library];
        
        if (!libraryConfig) {
            throw new Error(`No configuration mapping for ${chartType} with ${library}`);
        }

        // Deep merge configurations
        let finalConfig = ChartUtils.deepMerge(libraryConfig, baseConfig.defaultOptions);
        
        // Apply user customizations
        if (config.title) {
            setConfigTitle(finalConfig, config.title, library);
        }
        
        if (config.colors && config.colors.length > 0) {
            applyCustomColors(finalConfig, data, config.colors, library);
        } else {
            applyDefaultColors(finalConfig, data, config.theme || defaultTheme, library);
        }

        // Apply responsive settings
        if (config.responsive !== false) {
            applyResponsiveConfig(finalConfig, library);
        }

        // Apply export settings
        if (config.export) {
            applyExportConfig(finalConfig, config.export, library);
        }

        // Set data
        setConfigData(finalConfig, data, library);

        return finalConfig;
    }

    /**
     * Create chart instance based on library
     * @param {HTMLElement} container - DOM container
     * @param {string} library - Chart library
     * @param {Object} config - Final configuration
     * @param {string} chartId - Chart ID
     * @returns {Object} Chart instance
     */
    function createChartInstance(container, library, config, chartId) {
        switch (library) {
            case 'chartjs':
                return createChartJSInstance(container, config);
            case 'echarts':
                return createEChartsInstance(container, config);
            case 'plotly':
                return createPlotlyInstance(container, config);
            default:
                throw new Error(`Unsupported library: ${library}`);
        }
    }

    /**
     * Create Chart.js instance
     */
    function createChartJSInstance(container, config) {
        // Ensure canvas exists
        let canvas = container.querySelector('canvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            container.appendChild(canvas);
        }
        
        return new Chart(canvas.getContext('2d'), config);
    }

    /**
     * Create ECharts instance
     */
    function createEChartsInstance(container, config) {
        const chart = echarts.init(container);
        chart.setOption(config);
        
        // Add resize listener
        window.addEventListener('resize', () => chart.resize());
        
        return chart;
    }

    /**
     * Create Plotly instance
     */
    function createPlotlyInstance(container, config) {
        Plotly.newPlot(container, config.data, config.layout, config.config);
        return container;
    }

    /**
     * Update Chart.js instance
     */
    function updateChartJS(instance, newData, options) {
        if (newData.labels) {
            instance.data.labels = newData.labels;
        }
        if (newData.datasets) {
            instance.data.datasets = newData.datasets;
        }
        instance.update(options.animation !== false ? 'active' : 'none');
    }

    /**
     * Update ECharts instance
     */
    function updateECharts(instance, newData, options) {
        const updateOptions = {
            series: newData.series || newData.datasets,
            ...options
        };
        instance.setOption(updateOptions, options.merge !== false);
    }

    /**
     * Update Plotly instance
     */
    function updatePlotly(container, newData, options) {
        if (newData.data) {
            Plotly.react(container, newData.data, newData.layout);
        }
    }

    /**
     * Set chart title based on library
     */
    function setConfigTitle(config, title, library) {
        switch (library) {
            case 'chartjs':
                if (!config.plugins) config.plugins = {};
                if (!config.plugins.title) config.plugins.title = {};
                config.plugins.title.display = true;
                config.plugins.title.text = title;
                break;
            case 'echarts':
                if (!config.title) config.title = {};
                config.title.text = title;
                break;
            case 'plotly':
                if (!config.layout) config.layout = {};
                config.layout.title = title;
                break;
        }
    }

    /**
     * Apply custom colors to chart with ColorManager integration
     */
    function applyCustomColors(config, data, colors, library) {
        // If colors are provided as strings with category info, resolve them
        const resolvedColors = colors.map((color, index) => {
            if (typeof color === 'string' && color.includes(':')) {
                // Format: "category:item" (e.g., "sectors:residential")
                const [category, item] = color.split(':');
                return ChartUtils.getCategoryColors(category, [item])[0];
            }
            return color;
        });

        switch (library) {
            case 'chartjs':
                if (config.data && config.data.datasets) {
                    config.data.datasets.forEach((dataset, index) => {
                        const color = resolvedColors[index % resolvedColors.length];
                        dataset.backgroundColor = color;
                        dataset.borderColor = color;
                    });
                }
                break;
            case 'echarts':
                config.color = resolvedColors;
                break;
            case 'plotly':
                if (config.data) {
                    config.data.forEach((trace, index) => {
                        if (resolvedColors[index]) {
                            trace.marker = trace.marker || {};
                            trace.marker.color = resolvedColors[index];
                        }
                    });
                }
                break;
        }
    }

    /**
     * Apply default theme colors with ColorManager integration
     */
    function applyDefaultColors(config, data, theme, library) {
        // Try to detect if data has category information for smarter color assignment
        let categoryColors = null;
        
        if (data.datasets && typeof window.colorManager !== 'undefined') {
            // Check if dataset labels match known categories
            const labels = data.datasets.map(d => d.label || '');
            
            // Try sectors first
            if (labels.some(label => isSectorName(label))) {
                categoryColors = ChartUtils.getCategoryColors('sectors', labels);
            }
            // Try models
            else if (labels.some(label => isModelName(label))) {
                categoryColors = ChartUtils.getCategoryColors('models', labels);
            }
            // Try carriers
            else if (labels.some(label => isCarrierName(label))) {
                categoryColors = ChartUtils.getCategoryColors('carriers', labels);
            }
        }
        
        // Use category colors if detected, otherwise use theme colors
        const colors = categoryColors || ChartUtils.getThemeColors(theme, data.datasets?.length || 10);
        
        applyCustomColors(config, data, colors, library);
    }

    /**
     * Helper functions to detect category types
     */
    function isSectorName(name) {
        const sectorKeywords = ['residential', 'commercial', 'industrial', 'agriculture', 'transport', 'public', 'sector'];
        return sectorKeywords.some(keyword => name.toLowerCase().includes(keyword));
    }

    function isModelName(name) {
        const modelKeywords = ['mlr', 'slr', 'wam', 'timeseries', 'arima', 'linear', 'model'];
        return modelKeywords.some(keyword => name.toLowerCase().includes(keyword));
    }

    function isCarrierName(name) {
        const carrierKeywords = ['electricity', 'gas', 'coal', 'oil', 'renewable', 'solar', 'wind', 'hydro'];
        return carrierKeywords.some(keyword => name.toLowerCase().includes(keyword));
    }

    /**
     * Apply responsive configuration
     */
    function applyResponsiveConfig(config, library) {
        switch (library) {
            case 'chartjs':
                config.responsive = true;
                config.maintainAspectRatio = false;
                break;
            case 'echarts':
                // ECharts handles responsive automatically
                break;
            case 'plotly':
                if (!config.layout) config.layout = {};
                config.layout.autosize = true;
                break;
        }
    }

    /**
     * Apply export configuration
     */
    function applyExportConfig(config, exportOptions, library) {
        // Export functionality will be handled by chart wrapper methods
        // This function can be used to set library-specific export settings
    }

    /**
     * Set data in library-specific format
     */
    function setConfigData(config, data, library) {
        switch (library) {
            case 'chartjs':
                config.data = data;
                break;
            case 'echarts':
                if (data.series) config.series = data.series;
                if (data.xAxis) config.xAxis = data.xAxis;
                if (data.yAxis) config.yAxis = data.yAxis;
                break;
            case 'plotly':
                config.data = data.traces || data.data;
                break;
        }
    }

    /**
     * Create chart wrapper with utility methods
     */
    function createChartWrapper(chartId, instance, library) {
        return {
            id: chartId,
            instance: instance,
            library: library,
            
            update: function(newData, options) {
                return update(chartId, newData, options);
            },
            
            destroy: function() {
                return destroy(chartId);
            },
            
            export: function(format = 'png', filename) {
                return exportChart(chartId, format, filename);
            },
            
            resize: function() {
                return resizeChart(chartId);
            },
            
            getImage: function(format = 'png') {
                return getChartImage(chartId, format);
            }
        };
    }

    /**
     * Export chart functionality
     */
    function exportChart(chartId, format, filename) {
        const chartData = chartInstances.get(chartId);
        if (!chartData) {
            throw new Error(`Chart with ID '${chartId}' not found`);
        }

        const { instance, library, type } = chartData;
        const defaultFilename = filename || `${type}_chart_${Date.now()}`;

        switch (library) {
            case 'chartjs':
                return exportChartJS(instance, format, defaultFilename);
            case 'echarts':
                return exportECharts(instance, format, defaultFilename);
            case 'plotly':
                return exportPlotly(chartData.container, format, defaultFilename);
        }
    }

    /**
     * Export Chart.js as image
     */
    function exportChartJS(instance, format, filename) {
        const url = instance.toBase64Image();
        ChartUtils.downloadImage(url, `${filename}.${format}`);
        return url;
    }

    /**
     * Export ECharts as image
     */
    function exportECharts(instance, format, filename) {
        const url = instance.getDataURL({
            pixelRatio: 2,
            backgroundColor: '#fff'
        });
        ChartUtils.downloadImage(url, `${filename}.${format}`);
        return url;
    }

    /**
     * Export Plotly as image
     */
    function exportPlotly(container, format, filename) {
        Plotly.toImage(container, {format: format, width: 1200, height: 800})
            .then(url => ChartUtils.downloadImage(url, `${filename}.${format}`));
    }

    /**
     * Resize chart
     */
    function resizeChart(chartId) {
        const chartData = chartInstances.get(chartId);
        if (!chartData) return false;

        const { instance, library } = chartData;

        switch (library) {
            case 'chartjs':
                instance.resize();
                break;
            case 'echarts':
                instance.resize();
                break;
            case 'plotly':
                Plotly.Plots.resize(chartData.container);
                break;
        }
        return true;
    }

    /**
     * Get chart as image data URL
     */
    function getChartImage(chartId, format) {
        const chartData = chartInstances.get(chartId);
        if (!chartData) return null;

        const { instance, library } = chartData;

        switch (library) {
            case 'chartjs':
                return instance.toBase64Image();
            case 'echarts':
                return instance.getDataURL({pixelRatio: 2, backgroundColor: '#fff'});
            case 'plotly':
                // Plotly requires async operation
                return Plotly.toImage(chartData.container, {format: format});
        }
    }

    /**
     * Set global theme
     */
    function setTheme(theme) {
        defaultTheme = theme;
    }

    /**
     * Get all chart instances
     */
    function getAllCharts() {
        return Array.from(chartInstances.keys());
    }

    /**
     * Destroy all charts
     */
    function destroyAll() {
        const chartIds = Array.from(chartInstances.keys());
        chartIds.forEach(id => destroy(id));
    }

    /**
     * Legacy createChart function for backward compatibility
     * @param {string} containerId - ID of the container element
     * @param {string} type - Chart type
     * @param {Object} data - Chart data
     * @param {Object} options - Chart options
     * @param {Object} config - Additional configuration
     * @returns {Object} Chart instance
     */
    function createChart(containerId, type, data, options = {}, config = {}) {
        const chartConfig = {
            type: type,
            data: data,
            ...options,
            ...config
        };
        return create(containerId, chartConfig);
    }

    /**
     * Enhanced createChart function with color management (async version)
     * @param {string} containerId - ID of the container element
     * @param {string} type - Chart type
     * @param {Object} data - Chart data
     * @param {Object} options - Chart options
     * @param {string} module - Module name for color configuration
     * @param {string} category - Color category
     * @returns {Promise<Object>} Chart instance with metadata
     */
    async function createChartWithColors(containerId, type, data, options = {}, module = null, category = null) {
        const library = getPreferredLibrary(type, module);
        const moduleConfig = moduleConfigs[module];
        const effectiveCategory = category || moduleConfig?.defaultColors || 'default';
        
        // Apply color management
        const enhancedData = await applyColorManagement(data, effectiveCategory, library, type);
        
        const chartConfig = {
            type: type,
            data: enhancedData,
            module: module,
            category: effectiveCategory,
            ...options
        };
        
        const chart = create(containerId, chartConfig);
        
        // Add metadata
        chart.metadata = {
            type,
            library,
            module,
            category: effectiveCategory,
            createdAt: new Date().toISOString()
        };
        
        return chart;
    }

    /**
     * Enhanced createChart function with color management (sync version)
     * @param {string} containerId - ID of the container element
     * @param {string} type - Chart type
     * @param {Object} data - Chart data
     * @param {Object} options - Chart options
     * @param {string} module - Module name for color configuration
     * @param {string} category - Color category
     * @returns {Object} Chart instance with metadata
     */
    function createChartWithColorsSync(containerId, type, data, options = {}, module = null, category = null) {
        const library = getPreferredLibrary(type, module);
        const moduleConfig = moduleConfigs[module];
        const effectiveCategory = category || moduleConfig?.defaultColors || 'default';
        
        // Apply color management
        const enhancedData = applyColorManagementSync(data, effectiveCategory, library, type);
        
        const chartConfig = {
            type: type,
            data: enhancedData,
            module: module,
            category: effectiveCategory,
            ...options
        };
        
        const chart = create(containerId, chartConfig);
        
        // Add metadata
        chart.metadata = {
            type,
            library,
            module,
            category: effectiveCategory,
            createdAt: new Date().toISOString()
        };
        
        return chart;
    }

    /**
     * Initialize color manager integration
     * @param {Object} manager - Color manager instance
     */
    function initColorManager(manager) {
        initializeColorManager(manager);
    }

    // Public API
    return {
        create: create,
        createChart: createChart,
        createChartWithColors: createChartWithColors,
        createChartWithColorsSync: createChartWithColorsSync,
        update: update,
        destroy: destroy,
        getInstance: getInstance,
        setTheme: setTheme,
        getAllCharts: getAllCharts,
        destroyAll: destroyAll,
        initColorManager: initColorManager,
        refreshChart: refreshChart,
        version: '1.0.0'
    };

})();