/**
 * DemandVisualizationCharts.js
 * Specialized chart management for Demand Visualization module
 * Provides sector-specific visualizations with consistent color schemes
 */

class DemandVisualizationCharts {
    constructor(chartFactory, colorManager) {
        this.chartFactory = chartFactory;
        this.colorManager = colorManager;
        this.charts = new Map();
        this.module = 'demand_visualization';
        
        // Initialize color manager in factory
        if (chartFactory && chartFactory.initColorManager) {
            chartFactory.initColorManager(colorManager);
        }
        
        // Sector-specific configurations
        this.sectorConfigs = {
            'Domestic': { priority: 1, icon: '🏠' },
            'Commercial': { priority: 2, icon: '🏢' },
            'Industrial': { priority: 3, icon: '🏭' },
            'Agriculture': { priority: 4, icon: '🌾' },
            'Public Lighting': { priority: 5, icon: '💡' },
            'Traction': { priority: 6, icon: '🚊' },
            'Others': { priority: 7, icon: '📊' }
        };
        
        // Chart type configurations for demand visualization
        this.chartTypes = {
            'sector_comparison': {
                type: 'bar',
                library: 'chartjs',
                responsive: true,
                maintainAspectRatio: false
            },
            'trend_analysis': {
                type: 'line',
                library: 'chartjs',
                responsive: true,
                maintainAspectRatio: false
            },
            'sector_distribution': {
                type: 'pie',
                library: 'chartjs',
                responsive: true,
                maintainAspectRatio: false
            },
            'time_series': {
                type: 'line',
                library: 'plotly',
                responsive: true
            },
            'heatmap': {
                type: 'heatmap',
                library: 'plotly',
                responsive: true
            }
        };
    }

    /**
     * Create sector comparison chart
     * @param {string} containerId - Container element ID
     * @param {Object} data - Sector data
     * @param {Object} options - Chart options
     * @returns {Object} Chart instance
     */
    createSectorComparison(containerId, data, options = {}) {
        const config = this.chartTypes.sector_comparison;
        
        // Sort sectors by priority
        const sortedData = this.sortSectorData(data);
        
        const chartData = {
            labels: sortedData.labels,
            datasets: [{
                label: options.datasetLabel || 'Demand (MU)',
                data: sortedData.values,
                borderWidth: 2,
                borderRadius: 4
            }]
        };
        
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: options.title || 'Sector-wise Demand Comparison',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    display: options.showLegend !== false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const sector = context.label;
                            const value = context.parsed.y;
                            const icon = this.sectorConfigs[sector]?.icon || '📊';
                            return `${icon} ${sector}: ${value.toFixed(2)} MU`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: options.yAxisLabel || 'Demand (MU)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: options.xAxisLabel || 'Sectors'
                    }
                }
            },
            ...options.chartOptions
        };
        
        const chart = this.chartFactory.createChart(
            containerId,
            config.type,
            chartData,
            chartOptions,
            {
                module: this.module,
                category: 'sectors',
                library: config.library
            }
        );
        
        this.charts.set(`${containerId}_sector_comparison`, chart);
        return chart;
    }

    /**
     * Create trend analysis chart
     * @param {string} containerId - Container element ID
     * @param {Object} data - Time series data
     * @param {Object} options - Chart options
     * @returns {Object} Chart instance
     */
    createTrendAnalysis(containerId, data, options = {}) {
        const config = this.chartTypes.trend_analysis;
        
        const chartData = {
            labels: data.years || data.labels,
            datasets: data.sectors.map(sector => ({
                label: sector.name,
                data: sector.values,
                borderWidth: 3,
                fill: false,
                tension: 0.1
            }))
        };
        
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: options.title || 'Demand Trend Analysis',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: (tooltipItems) => {
                            return `Year: ${tooltipItems[0].label}`;
                        },
                        label: (context) => {
                            const sector = context.dataset.label;
                            const value = context.parsed.y;
                            const icon = this.sectorConfigs[sector]?.icon || '📊';
                            return `${icon} ${sector}: ${value.toFixed(2)} MU`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: options.yAxisLabel || 'Demand (MU)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: options.xAxisLabel || 'Year'
                    }
                }
            },
            ...options.chartOptions
        };
        
        const chart = this.chartFactory.createChart(
            containerId,
            config.type,
            chartData,
            chartOptions,
            {
                module: this.module,
                category: 'sectors',
                library: config.library
            }
        );
        
        this.charts.set(`${containerId}_trend_analysis`, chart);
        return chart;
    }

    /**
     * Create sector distribution pie chart
     * @param {string} containerId - Container element ID
     * @param {Object} data - Sector distribution data
     * @param {Object} options - Chart options
     * @returns {Object} Chart instance
     */
    createSectorDistribution(containerId, data, options = {}) {
        const config = this.chartTypes.sector_distribution;
        
        // Sort and calculate percentages
        const sortedData = this.sortSectorData(data);
        const total = sortedData.values.reduce((sum, val) => sum + val, 0);
        const percentages = sortedData.values.map(val => (val / total * 100));
        
        const chartData = {
            labels: sortedData.labels.map(label => {
                const icon = this.sectorConfigs[label]?.icon || '📊';
                return `${icon} ${label}`;
            }),
            datasets: [{
                data: sortedData.values,
                borderWidth: 2
            }]
        };
        
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: options.title || 'Sector Distribution',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    display: true,
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const sector = context.label.replace(/^[^\s]+ /, ''); // Remove icon
                            const value = context.parsed;
                            const percentage = percentages[context.dataIndex];
                            return `${sector}: ${value.toFixed(2)} MU (${percentage.toFixed(1)}%)`;
                        }
                    }
                }
            },
            ...options.chartOptions
        };
        
        const chart = this.chartFactory.createChart(
            containerId,
            config.type,
            chartData,
            chartOptions,
            {
                module: this.module,
                category: 'sectors',
                library: config.library
            }
        );
        
        this.charts.set(`${containerId}_sector_distribution`, chart);
        return chart;
    }

    /**
     * Create interactive time series chart using Plotly
     * @param {string} containerId - Container element ID
     * @param {Object} data - Time series data
     * @param {Object} options - Chart options
     * @returns {Object} Chart instance
     */
    createInteractiveTimeSeries(containerId, data, options = {}) {
        const config = this.chartTypes.time_series;
        
        const traces = data.sectors.map(sector => ({
            x: data.dates || data.years,
            y: sector.values,
            name: sector.name,
            type: 'scatter',
            mode: 'lines+markers',
            line: { width: 3 },
            marker: { size: 6 }
        }));
        
        const layout = {
            title: {
                text: options.title || 'Interactive Demand Time Series',
                font: { size: 18 }
            },
            xaxis: {
                title: options.xAxisLabel || 'Time',
                showgrid: true
            },
            yaxis: {
                title: options.yAxisLabel || 'Demand (MU)',
                showgrid: true
            },
            hovermode: 'x unified',
            showlegend: true,
            legend: {
                orientation: 'h',
                y: -0.2
            }
        };
        
        const chart = this.chartFactory.createChart(
            containerId,
            config.type,
            traces,
            { layout },
            {
                module: this.module,
                category: 'sectors',
                library: config.library
            }
        );
        
        this.charts.set(`${containerId}_time_series`, chart);
        return chart;
    }

    /**
     * Sort sector data by priority
     * @param {Object} data - Sector data
     * @returns {Object} Sorted data
     */
    sortSectorData(data) {
        const sectors = data.labels || Object.keys(data);
        const values = data.values || Object.values(data);
        
        const combined = sectors.map((sector, index) => ({
            label: sector,
            value: values[index],
            priority: this.sectorConfigs[sector]?.priority || 999
        }));
        
        combined.sort((a, b) => a.priority - b.priority);
        
        return {
            labels: combined.map(item => item.label),
            values: combined.map(item => item.value)
        };
    }

    /**
     * Update chart data
     * @param {string} chartKey - Chart key
     * @param {Object} newData - New data
     * @param {Object} newOptions - New options
     */
    updateChart(chartKey, newData, newOptions = {}) {
        const chart = this.charts.get(chartKey);
        if (chart && chart.update) {
            chart.update(newData, newOptions);
        }
    }

    /**
     * Destroy chart
     * @param {string} chartKey - Chart key
     */
    destroyChart(chartKey) {
        const chart = this.charts.get(chartKey);
        if (chart && chart.destroy) {
            chart.destroy();
            this.charts.delete(chartKey);
        }
    }

    /**
     * Destroy all charts
     */
    destroyAll() {
        this.charts.forEach((chart, key) => {
            if (chart.destroy) {
                chart.destroy();
            }
        });
        this.charts.clear();
    }

    /**
     * Export chart
     * @param {string} chartKey - Chart key
     * @param {string} format - Export format
     * @returns {Promise} Export promise
     */
    exportChart(chartKey, format = 'png') {
        const chart = this.charts.get(chartKey);
        if (chart && chart.export) {
            return chart.export(format);
        }
        return Promise.reject(new Error('Chart not found or export not supported'));
    }

    /**
     * Get all chart instances
     * @returns {Map} Chart instances
     */
    getAllCharts() {
        return this.charts;
    }

    /**
     * Refresh all charts with current color scheme
     */
    refreshAllCharts() {
        this.charts.forEach(chart => {
            if (chart.refresh) {
                chart.refresh();
            }
        });
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DemandVisualizationCharts;
} else {
    window.DemandVisualizationCharts = DemandVisualizationCharts;
}