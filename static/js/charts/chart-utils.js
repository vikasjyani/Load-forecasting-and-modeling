/**
 * Chart Utilities for EnergyCharts
 * Helper functions for data processing, validation, and chart management
 */

window.ChartUtils = (function() {
    'use strict';

    /**
     * Validate chart configuration
     * @param {Object} config - Chart configuration object
     * @returns {Object} Validated and processed configuration
     */
    function validateConfig(config) {
        if (!config || typeof config !== 'object') {
            throw new Error('Configuration object is required');
        }

        // Required fields
        if (!config.type) {
            throw new Error('Chart type is required');
        }

        if (!config.data) {
            throw new Error('Data is required');
        }

        // Set defaults
        const validatedConfig = {
            type: config.type.toLowerCase(),
            data: config.data,
            library: config.library || 'auto',
            id: config.id || null,
            title: config.title || '',
            colors: config.colors || null,
            theme: config.theme || 'energy-default',
            responsive: config.responsive !== false,
            export: config.export || false,
            ...config
        };

        // Validate chart type
        if (!CHART_CONFIGS[validatedConfig.type]) {
            throw new Error(`Unsupported chart type: ${validatedConfig.type}`);
        }

        // Validate library if specified
        if (validatedConfig.library !== 'auto' && 
            !['chartjs', 'echarts', 'plotly'].includes(validatedConfig.library)) {
            throw new Error(`Unsupported library: ${validatedConfig.library}`);
        }

        return validatedConfig;
    }

    /**
     * Process data for specific chart type and library
     * @param {Object|Array} data - Raw data
     * @param {string} chartType - Chart type
     * @param {string} library - Target library
     * @returns {Object} Processed data in library format
     */
    function processData(data, chartType, library) {
        if (!data) {
            throw new Error('Data is required');
        }

        // Handle different input data formats
        let processedData;

        if (Array.isArray(data)) {
            processedData = processArrayData(data, chartType, library);
        } else if (data.labels && data.datasets) {
            processedData = processStandardData(data, chartType, library);
        } else if (data.x && data.y) {
            processedData = processXYData(data, chartType, library);
        } else if (data.nodes && data.links) {
            processedData = processSankeyData(data, chartType, library);
        } else {
            processedData = processObjectData(data, chartType, library);
        }

        return processedData;
    }

    /**
     * Process array data (simple array of values)
     */
    function processArrayData(data, chartType, library) {
        switch (library) {
            case 'chartjs':
                return {
                    labels: data.map((_, index) => `Item ${index + 1}`),
                    datasets: [{
                        label: 'Data',
                        data: data,
                        backgroundColor: getDefaultColors(1)[0],
                        borderColor: getDefaultColors(1)[0]
                    }]
                };
            case 'echarts':
                if (chartType === 'pie') {
                    return {
                        series: [{
                            data: data.map((value, index) => ({
                                value: value,
                                name: `Item ${index + 1}`
                            }))
                        }]
                    };
                } else {
                    return {
                        xAxis: { data: data.map((_, index) => `Item ${index + 1}`) },
                        series: [{ data: data }]
                    };
                }
            case 'plotly':
                return {
                    data: [{
                        y: data,
                        type: getPlotlyType(chartType)
                    }]
                };
            default:
                return data;
        }
    }

    /**
     * Process standard chart data format (labels + datasets)
     */
    function processStandardData(data, chartType, library) {
        switch (library) {
            case 'chartjs':
                return formatForChartJS(data, chartType);
            case 'echarts':
                return formatForECharts(data, chartType);
            case 'plotly':
                return formatForPlotly(data, chartType);
            default:
                return data;
        }
    }

    /**
     * Process X-Y coordinate data
     */
    function processXYData(data, chartType, library) {
        switch (library) {
            case 'chartjs':
                return {
                    datasets: [{
                        label: data.label || 'Data',
                        data: data.x.map((x, i) => ({ x: x, y: data.y[i] })),
                        backgroundColor: getDefaultColors(1)[0],
                        borderColor: getDefaultColors(1)[0]
                    }]
                };
            case 'echarts':
                return {
                    series: [{
                        data: data.x.map((x, i) => [x, data.y[i]]),
                        type: getEChartsType(chartType)
                    }]
                };
            case 'plotly':
                return {
                    data: [{
                        x: data.x,
                        y: data.y,
                        type: getPlotlyType(chartType),
                        mode: chartType === 'scatter' ? 'markers' : 'lines'
                    }]
                };
            default:
                return data;
        }
    }

    /**
     * Process Sankey diagram data
     */
    function processSankeyData(data, chartType, library) {
        switch (library) {
            case 'echarts':
                return {
                    series: [{
                        type: 'sankey',
                        data: data.nodes,
                        links: data.links
                    }]
                };
            case 'plotly':
                return {
                    data: [{
                        type: 'sankey',
                        node: {
                            label: data.nodes.map(n => n.name),
                            color: data.nodes.map(n => n.color)
                        },
                        link: {
                            source: data.links.map(l => l.source),
                            target: data.links.map(l => l.target),
                            value: data.links.map(l => l.value)
                        }
                    }]
                };
            default:
                return data;
        }
    }

    /**
     * Process generic object data
     */
    function processObjectData(data, chartType, library) {
        // Try to extract meaningful data structure
        const keys = Object.keys(data);
        const values = Object.values(data);

        switch (library) {
            case 'chartjs':
                return {
                    labels: keys,
                    datasets: [{
                        label: 'Data',
                        data: values,
                        backgroundColor: getDefaultColors(values.length),
                        borderColor: getDefaultColors(values.length)
                    }]
                };
            case 'echarts':
                if (chartType === 'pie') {
                    return {
                        series: [{
                            data: keys.map((key, index) => ({
                                name: key,
                                value: values[index]
                            }))
                        }]
                    };
                } else {
                    return {
                        xAxis: { data: keys },
                        series: [{ data: values }]
                    };
                }
            case 'plotly':
                return {
                    data: [{
                        x: keys,
                        y: values,
                        type: getPlotlyType(chartType)
                    }]
                };
            default:
                return data;
        }
    }

    /**
     * Format data for Chart.js
     */
    function formatForChartJS(data, chartType) {
        const formatted = {
            labels: data.labels || [],
            datasets: []
        };

        if (data.datasets && Array.isArray(data.datasets)) {
            formatted.datasets = data.datasets.map((dataset, index) => {
                const colors = getDefaultColors(data.datasets.length);
                return {
                    label: dataset.label || `Dataset ${index + 1}`,
                    data: dataset.data || [],
                    backgroundColor: dataset.backgroundColor || colors[index],
                    borderColor: dataset.borderColor || colors[index],
                    borderWidth: dataset.borderWidth || 2,
                    fill: chartType === 'area' ? true : (dataset.fill || false),
                    tension: dataset.tension || 0.1,
                    ...dataset
                };
            });
        }

        return formatted;
    }

    /**
     * Format data for ECharts
     */
    function formatForECharts(data, chartType) {
        const formatted = {};

        if (data.labels) {
            formatted.xAxis = { data: data.labels };
        }

        if (data.datasets && Array.isArray(data.datasets)) {
            formatted.series = data.datasets.map((dataset, index) => ({
                name: dataset.label || `Dataset ${index + 1}`,
                type: getEChartsType(chartType),
                data: dataset.data || [],
                ...dataset
            }));
        }

        return formatted;
    }

    /**
     * Format data for Plotly
     */
    function formatForPlotly(data, chartType) {
        const formatted = { data: [] };

        if (data.datasets && Array.isArray(data.datasets)) {
            formatted.data = data.datasets.map((dataset, index) => ({
                name: dataset.label || `Dataset ${index + 1}`,
                x: data.labels || dataset.x,
                y: dataset.data || dataset.y,
                type: getPlotlyType(chartType),
                ...dataset
            }));
        }

        return formatted;
    }

    /**
     * Get ECharts chart type mapping
     */
    function getEChartsType(chartType) {
        const typeMap = {
            'line': 'line',
            'bar': 'bar',
            'pie': 'pie',
            'scatter': 'scatter',
            'area': 'line',
            'timeseries': 'line'
        };
        return typeMap[chartType] || 'line';
    }

    /**
     * Get Plotly chart type mapping
     */
    function getPlotlyType(chartType) {
        const typeMap = {
            'line': 'scatter',
            'bar': 'bar',
            'pie': 'pie',
            'scatter': 'scatter',
            'area': 'scatter',
            'heatmap': 'heatmap',
            'timeseries': 'scatter'
        };
        return typeMap[chartType] || 'scatter';
    }

    /**
     * Get theme colors with ColorManager integration
     * @param {string} theme - Theme name
     * @param {number} count - Number of colors needed
     * @returns {Array} Array of color strings
     */
    function getThemeColors(theme = 'energy-default', count = 10) {
        // Priority 1: Use existing ColorManager if available
        if (typeof window.colorManager !== 'undefined' && window.colorManager.initialized) {
            try {
                // Try to get chart colors from ColorManager
                const chartColors = window.colorManager.getChartColors(count);
                if (chartColors && chartColors.length >= count) {
                    return chartColors;
                }
            } catch (e) {
                console.warn('ColorManager chart colors failed, trying theme approach');
            }
            
            // Fallback: try to get theme-specific colors
            try {
                if (theme === 'energy-default' || theme === 'light') {
                    return [
                        window.colorManager.getColor('charts', 'primary'),
                        window.colorManager.getColor('charts', 'secondary'),
                        window.colorManager.getColor('charts', 'tertiary'),
                        window.colorManager.getColor('charts', 'quaternary'),
                        window.colorManager.getColor('charts', 'quinary')
                    ].concat(window.colorManager.getChartColors(count - 5, 5));
                }
            } catch (e) {
                console.warn('ColorManager theme colors failed, using fallback');
            }
        }

        // Priority 2: Use built-in theme colors
        if (CHART_THEMES && CHART_THEMES[theme]) {
            return CHART_THEMES[theme].colors.slice(0, count);
        }

        // Priority 3: Default fallback colors
        return getDefaultColors(count);
    }

    /**
     * Get default color palette
     * @param {number} count - Number of colors needed
     * @returns {Array} Array of color strings
     */
    function getDefaultColors(count = 10) {
        const defaultPalette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
        ];

        if (count <= defaultPalette.length) {
            return defaultPalette.slice(0, count);
        }

        // Generate additional colors if needed
        const colors = [...defaultPalette];
        while (colors.length < count) {
            colors.push(generateRandomColor());
        }

        return colors.slice(0, count);
    }

    /**
     * Get colors from ColorManager by category or generate unique colors
     * @param {string} category - Color category (sectors, models, charts, etc.)
     * @param {Array} items - Array of item names
     * @returns {Array} Array of color strings
     */
    function getCategoryColors(category, items) {
        if (!Array.isArray(items)) {
            console.warn('getCategoryColors expects items to be an array');
            return getDefaultColors(1);
        }

        // Priority 1: Use ColorManager if available
        if (typeof window.colorManager !== 'undefined' && window.colorManager.initialized) {
            try {
                const colors = [];
                items.forEach(item => {
                    // Get color from ColorManager, it will generate unique if not found
                    const color = window.colorManager.getColor(category, item);
                    colors.push(color);
                });
                return colors;
            } catch (e) {
                console.warn('ColorManager failed for category colors, using fallback:', e);
            }
        }

        // Priority 2: Generate unique colors for each item
        return items.map((item, index) => {
            return generateUniqueColor(category, item, index);
        });
    }

    /**
     * Generate unique color for specific category and item
     * @param {string} category - Category name
     * @param {string} item - Item name
     * @param {number} index - Index for fallback color selection
     * @returns {string} Generated color
     */
    function generateUniqueColor(category, item, index = 0) {
        // Try to use ColorManager's generation first
        if (typeof window.colorManager !== 'undefined' && 
            window.colorManager.generateColorForItem) {
            try {
                return window.colorManager.generateColorForItem(category, item);
            } catch (e) {
                console.warn('ColorManager color generation failed, using built-in');
            }
        }

        // Fallback to built-in generation
        const str = `${category}_${item}`;
        let hash = 0;
        
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash + str.charCodeAt(i)) & 0xffffffff;
        }

        hash = Math.abs(hash);

        // Use HSL for better color control
        const hue = hash % 360;
        const saturation = 60 + (hash % 30); // 60-90%
        const lightness = 45 + (hash % 25);  // 45-70%

        return hslToHex(hue, saturation, lightness);
    }

    /**
     * Convert HSL to Hex (helper function)
     */
    function hslToHex(h, s, l) {
        h = h / 360;
        s = s / 100; 
        l = l / 100;

        const hue2rgb = (p, q, t) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1/6) return p + (q - p) * 6 * t;
            if (t < 1/2) return q;
            if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
            return p;
        };

        let r, g, b;

        if (s === 0) {
            r = g = b = l; // achromatic
        } else {
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }

        const toHex = (c) => {
            const hex = Math.round(c * 255).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        };

        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }

    /**
     * Deep merge objects
     * @param {Object} target - Target object
     * @param {Object} source - Source object
     * @returns {Object} Merged object
     */
    function deepMerge(target, source) {
        if (!source) return target;
        if (!target) return source;

        const result = JSON.parse(JSON.stringify(target));

        function mergeRecursive(target, source) {
            for (const key in source) {
                if (source.hasOwnProperty(key)) {
                    if (source[key] && typeof source[key] === 'object' && 
                        !Array.isArray(source[key]) && target[key]) {
                        target[key] = target[key] || {};
                        mergeRecursive(target[key], source[key]);
                    } else {
                        target[key] = source[key];
                    }
                }
            }
        }

        mergeRecursive(result, source);
        return result;
    }

    /**
     * Download image from data URL
     * @param {string} dataURL - Data URL of image
     * @param {string} filename - Download filename
     */
    function downloadImage(dataURL, filename) {
        const link = document.createElement('a');
        link.download = filename;
        link.href = dataURL;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * Convert data to CSV format
     * @param {Object} data - Chart data
     * @param {string} chartType - Chart type
     * @returns {string} CSV string
     */
    function dataToCSV(data, chartType) {
        let csvContent = '';

        if (chartType === 'pie' || chartType === 'doughnut') {
            // Handle pie chart data
            csvContent = 'Label,Value\n';
            if (data.labels && data.datasets && data.datasets[0]) {
                data.labels.forEach((label, index) => {
                    const value = data.datasets[0].data[index] || 0;
                    csvContent += `"${label}",${value}\n`;
                });
            }
        } else {
            // Handle other chart types
            if (data.labels) {
                csvContent = 'Label';
                if (data.datasets) {
                    data.datasets.forEach(dataset => {
                        csvContent += `,"${dataset.label || 'Data'}"`;
                    });
                }
                csvContent += '\n';

                data.labels.forEach((label, index) => {
                    csvContent += `"${label}"`;
                    if (data.datasets) {
                        data.datasets.forEach(dataset => {
                            const value = dataset.data[index] || 0;
                            csvContent += `,${value}`;
                        });
                    }
                    csvContent += '\n';
                });
            }
        }

        return csvContent;
    }

    /**
     * Download data as CSV
     * @param {Object} data - Chart data
     * @param {string} chartType - Chart type
     * @param {string} filename - Download filename
     */
    function downloadCSV(data, chartType, filename = 'chart_data.csv') {
        const csvContent = dataToCSV(data, chartType);
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    /**
     * Format number with appropriate units
     * @param {number} value - Number to format
     * @param {string} unit - Unit type (energy, power, etc.)
     * @returns {string} Formatted string
     */
    function formatValue(value, unit = '') {
        if (typeof value !== 'number') return value;

        // Energy units conversion
        if (unit.toLowerCase().includes('wh')) {
            if (value >= 1e12) return (value / 1e12).toFixed(2) + ' TWh';
            if (value >= 1e9) return (value / 1e9).toFixed(2) + ' GWh';
            if (value >= 1e6) return (value / 1e6).toFixed(2) + ' MWh';
            if (value >= 1e3) return (value / 1e3).toFixed(2) + ' kWh';
            return value.toFixed(2) + ' Wh';
        }

        // Power units conversion
        if (unit.toLowerCase().includes('w') && !unit.toLowerCase().includes('wh')) {
            if (value >= 1e9) return (value / 1e9).toFixed(2) + ' GW';
            if (value >= 1e6) return (value / 1e6).toFixed(2) + ' MW';
            if (value >= 1e3) return (value / 1e3).toFixed(2) + ' kW';
            return value.toFixed(2) + ' W';
        }

        // General number formatting
        if (value >= 1e9) return (value / 1e9).toFixed(2) + 'B';
        if (value >= 1e6) return (value / 1e6).toFixed(2) + 'M';
        if (value >= 1e3) return (value / 1e3).toFixed(2) + 'K';
        
        return value.toLocaleString();
    }

    /**
     * Debounce function for performance optimization
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Check if data is valid for chart type
     * @param {Object} data - Data to validate
     * @param {string} chartType - Chart type
     * @returns {boolean} Validation result
     */
    function isValidData(data, chartType) {
        if (!data) return false;

        switch (chartType) {
            case 'pie':
            case 'doughnut':
                return (data.labels && data.datasets && 
                       data.datasets[0] && data.datasets[0].data &&
                       data.labels.length === data.datasets[0].data.length);
            
            case 'line':
            case 'bar':
            case 'area':
                return (data.labels && data.datasets &&
                       Array.isArray(data.datasets) && data.datasets.length > 0);
            
            case 'scatter':
                return (data.datasets && Array.isArray(data.datasets) &&
                       data.datasets.every(d => Array.isArray(d.data)));
            
            case 'heatmap':
                return (data.z && Array.isArray(data.z) && 
                       data.z.every(row => Array.isArray(row)));
            
            default:
                return true; // Basic validation passed
        }
    }

    // Public API
    return {
        validateConfig: validateConfig,
        processData: processData,
        getThemeColors: getThemeColors,
        getCategoryColors: getCategoryColors,
        generateUniqueColor: generateUniqueColor,
        getDefaultColors: getDefaultColors,
        deepMerge: deepMerge,
        downloadImage: downloadImage,
        downloadCSV: downloadCSV,
        formatValue: formatValue,
        debounce: debounce,
        isValidData: isValidData,
        dataToCSV: dataToCSV
    };

})();