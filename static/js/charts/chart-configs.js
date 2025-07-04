/**
 * Chart Configurations for EnergyCharts
 * Defines chart types, default options, and library mappings
 */

const CHART_CONFIGS = {
    
    /**
     * LINE CHART CONFIGURATION
     * Best for: Trends, time series, demand forecasts
     */
    line: {
        defaultLibrary: 'chartjs',
        category: 'basic',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false,
            tension: 0.1,
            fill: false
        },
        libraryMappings: {
            chartjs: {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                font: {
                                    family: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            cornerRadius: 8,
                            titleFont: { weight: 'bold' },
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            ticks: { maxTicksLimit: 10 }
                        },
                        y: {
                            display: true,
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        }
                    },
                    animation: {
                        duration: 750,
                        easing: 'easeInOutQuart'
                    }
                }
            },
            echarts: {
                tooltip: { trigger: 'axis' },
                legend: { bottom: 0 },
                grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
                xAxis: { type: 'category', boundaryGap: false },
                yAxis: { type: 'value' },
                series: []
            }
        }
    },

    /**
     * BAR CHART CONFIGURATION
     * Best for: Comparisons, capacity analysis, generation mix
     */
    bar: {
        defaultLibrary: 'chartjs',
        category: 'basic',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false
        },
        libraryMappings: {
            chartjs: {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { usePointStyle: true }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            cornerRadius: 8
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: { display: false }
                        },
                        y: {
                            display: true,
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            },
            echarts: {
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
                legend: { bottom: 0 },
                grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
                xAxis: { type: 'category' },
                yAxis: { type: 'value' },
                series: []
            }
        }
    },

    /**
     * PIE CHART CONFIGURATION
     * Best for: Sectoral breakdown, composition analysis
     */
    pie: {
        defaultLibrary: 'chartjs',
        category: 'basic',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false
        },
        libraryMappings: {
            chartjs: {
                type: 'pie',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { usePointStyle: true }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            cornerRadius: 8,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${context.label}: ${value.toLocaleString()} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            },
            echarts: {
                tooltip: { trigger: 'item' },
                legend: { bottom: 0, orient: 'horizontal' },
                series: [{
                    type: 'pie',
                    radius: '60%',
                    center: ['50%', '40%'],
                    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
                }]
            }
        }
    },

    /**
     * DOUGHNUT CHART CONFIGURATION
     * Best for: Composition with center focus
     */
    doughnut: {
        defaultLibrary: 'chartjs',
        category: 'basic',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%'
        },
        libraryMappings: {
            chartjs: {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true } },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            cornerRadius: 8
                        }
                    }
                }
            }
        }
    },

    /**
     * AREA CHART CONFIGURATION
     * Best for: Stacked demand, cumulative data
     */
    area: {
        defaultLibrary: 'chartjs',
        category: 'basic',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false,
            fill: true,
            tension: 0.1
        },
        libraryMappings: {
            chartjs: {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { intersect: false, mode: 'index' },
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true } },
                        tooltip: { backgroundColor: 'rgba(17, 24, 39, 0.95)', cornerRadius: 8 }
                    },
                    scales: {
                        x: { display: true, grid: { color: 'rgba(0,0,0,0.1)' } },
                        y: { 
                            display: true, 
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            stacked: true
                        }
                    },
                    elements: {
                        line: { fill: true },
                        point: { radius: 0, hoverRadius: 5 }
                    }
                }
            }
        }
    },

    /**
     * TIME SERIES CONFIGURATION
     * Best for: Load profiles, high-resolution time data
     */
    timeseries: {
        defaultLibrary: 'echarts',
        category: 'advanced',
        defaultOptions: {
            responsive: true,
            zoomable: true,
            brushable: true
        },
        libraryMappings: {
            echarts: {
                title: { left: 'center' },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } }
                },
                legend: { bottom: 0 },
                toolbox: {
                    feature: {
                        dataZoom: { yAxisIndex: 'none' },
                        restore: {},
                        saveAsImage: {}
                    }
                },
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { start: 0, end: 100, handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23.1h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z' }
                ],
                grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
                xAxis: {
                    type: 'time',
                    boundaryGap: false
                },
                yAxis: { type: 'value' },
                series: []
            },
            chartjs: {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { type: 'time', time: { unit: 'hour' } },
                        y: { display: true }
                    },
                    plugins: {
                        zoom: {
                            zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' },
                            pan: { enabled: true, mode: 'x' }
                        }
                    }
                }
            }
        }
    },

    /**
     * HEATMAP CONFIGURATION
     * Best for: Load patterns, correlation matrices
     */
    heatmap: {
        defaultLibrary: 'plotly',
        category: 'specialized',
        defaultOptions: {
            responsive: true,
            colorScale: 'Viridis'
        },
        libraryMappings: {
            plotly: {
                data: [{
                    type: 'heatmap',
                    colorscale: 'Viridis',
                    showscale: true
                }],
                layout: {
                    autosize: true,
                    margin: { l: 60, r: 60, t: 60, b: 60 },
                    xaxis: { title: 'X Axis' },
                    yaxis: { title: 'Y Axis' }
                },
                config: {
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                    toImageButtonOptions: {
                        format: 'png',
                        filename: 'heatmap',
                        height: 600,
                        width: 800,
                        scale: 2
                    }
                }
            },
            echarts: {
                tooltip: { position: 'top' },
                grid: { height: '50%', top: '10%' },
                xAxis: { type: 'category', splitArea: { show: true } },
                yAxis: { type: 'category', splitArea: { show: true } },
                visualMap: {
                    min: 0,
                    max: 100,
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '15%'
                },
                series: [{
                    type: 'heatmap',
                    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
                }]
            }
        }
    },

    /**
     * SCATTER PLOT CONFIGURATION
     * Best for: Correlation analysis, data points
     */
    scatter: {
        defaultLibrary: 'chartjs',
        category: 'basic',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false
        },
        libraryMappings: {
            chartjs: {
                type: 'scatter',
                data: { datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { type: 'linear', position: 'bottom' },
                        y: { type: 'linear' }
                    },
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: { backgroundColor: 'rgba(17, 24, 39, 0.95)', cornerRadius: 8 }
                    }
                }
            },
            plotly: {
                data: [{
                    type: 'scatter',
                    mode: 'markers'
                }],
                layout: {
                    autosize: true,
                    hovermode: 'closest'
                }
            }
        }
    },

    /**
     * RADAR CHART CONFIGURATION
     * Best for: Performance metrics, multi-dimensional analysis
     */
    radar: {
        defaultLibrary: 'chartjs',
        category: 'specialized',
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false
        },
        libraryMappings: {
            chartjs: {
                type: 'radar',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0,0,0,0.1)' },
                            pointLabels: { font: { size: 12 } }
                        }
                    },
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            }
        }
    },

    /**
     * GAUGE CHART CONFIGURATION
     * Best for: KPIs, single value indicators
     */
    gauge: {
        defaultLibrary: 'echarts',
        category: 'specialized',
        defaultOptions: {
            responsive: true,
            min: 0,
            max: 100
        },
        libraryMappings: {
            echarts: {
                series: [{
                    type: 'gauge',
                    center: ['50%', '60%'],
                    radius: '75%',
                    min: 0,
                    max: 100,
                    splitNumber: 10,
                    axisLine: {
                        lineStyle: {
                            width: 10,
                            color: [
                                [0.3, '#67e0e3'],
                                [0.7, '#37a2da'],
                                [1, '#fd666d']
                            ]
                        }
                    },
                    pointer: {
                        itemStyle: { color: 'auto' }
                    },
                    axisTick: { distance: -30, length: 8 },
                    splitLine: { distance: -30, length: 30 },
                    axisLabel: { distance: -60, fontSize: 14 },
                    detail: {
                        valueAnimation: true,
                        formatter: '{value}%',
                        fontSize: 20
                    }
                }]
            }
        }
    },

    /**
     * SANKEY DIAGRAM CONFIGURATION
     * Best for: Energy flow, process visualization
     */
    sankey: {
        defaultLibrary: 'echarts',
        category: 'specialized',
        defaultOptions: {
            responsive: true,
            oriented: 'horizontal'
        },
        libraryMappings: {
            echarts: {
                series: [{
                    type: 'sankey',
                    layout: 'none',
                    emphasis: { focus: 'adjacency' },
                    data: [],
                    links: [],
                    lineStyle: { color: 'gradient', curveness: 0.5 }
                }]
            },
            plotly: {
                data: [{
                    type: 'sankey',
                    orientation: 'h',
                    node: {
                        pad: 15,
                        thickness: 30,
                        line: { color: "black", width: 0.5 }
                    },
                    link: { source: [], target: [], value: [] }
                }],
                layout: { font: { size: 12 } }
            }
        }
    },

    /**
     * FUNNEL CHART CONFIGURATION
     * Best for: Process stages, conversion analysis
     */
    funnel: {
        defaultLibrary: 'echarts',
        category: 'specialized',
        defaultOptions: {
            responsive: true,
            sort: 'descending'
        },
        libraryMappings: {
            echarts: {
                tooltip: { trigger: 'item', formatter: '{a} <br/>{b} : {c}%' },
                legend: { bottom: 0 },
                series: [{
                    type: 'funnel',
                    left: '10%',
                    top: 60,
                    width: '80%',
                    minSize: '0%',
                    maxSize: '100%',
                    sort: 'descending',
                    gap: 2,
                    label: { show: true, position: 'inside' },
                    labelLine: { length: 10, lineStyle: { width: 1, type: 'solid' } },
                    itemStyle: { borderColor: '#fff', borderWidth: 1 },
                    emphasis: { label: { fontSize: 20 } }
                }]
            }
        }
    }
};

/**
 * Chart categories for easy filtering and organization
 */
const CHART_CATEGORIES = {
    basic: ['line', 'bar', 'pie', 'doughnut', 'area', 'scatter'],
    advanced: ['timeseries'],
    specialized: ['heatmap', 'radar', 'gauge', 'sankey', 'funnel']
};

/**
 * Library capabilities matrix
 */
const LIBRARY_CAPABILITIES = {
    chartjs: {
        strength: 'Simple, responsive charts with good performance',
        best_for: ['line', 'bar', 'pie', 'doughnut', 'area', 'scatter', 'radar'],
        features: ['responsive', 'animations', 'interactions', 'plugins'],
        limitations: ['limited_3d', 'no_heatmaps']
    },
    echarts: {
        strength: 'Rich interactions and advanced chart types',
        best_for: ['timeseries', 'gauge', 'sankey', 'funnel', 'heatmap'],
        features: ['brush_selection', 'data_zoom', 'rich_interactions', '3d_support'],
        limitations: ['larger_bundle_size']
    },
    plotly: {
        strength: 'Statistical and scientific visualizations',
        best_for: ['heatmap', 'scatter', 'sankey', '3d_plots'],
        features: ['statistical_charts', '3d_support', 'crossfilter', 'scientific'],
        limitations: ['performance_with_large_data']
    }
};

/**
 * Default themes and color palettes
 */
const CHART_THEMES = {
    'energy-default': {
        name: 'Energy Default',
        colors: [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ],
        background: '#ffffff',
        grid: 'rgba(0,0,0,0.1)',
        text: '#333333'
    },
    'energy-dark': {
        name: 'Energy Dark',
        colors: [
            '#5ba3cf', '#ff9f40', '#4bc0c0', '#ff6384', '#c9cbcf',
            '#ff9f40', '#4bc0c0', '#ff6384', '#36a2eb', '#c9cbcf'
        ],
        background: '#2d3748',
        grid: 'rgba(255,255,255,0.1)',
        text: '#e2e8f0'
    },
    'renewable': {
        name: 'Renewable Energy',
        colors: [
            '#2e7d32', '#388e3c', '#43a047', '#4caf50', '#66bb6a',
            '#81c784', '#a5d6a7', '#c8e6c9', '#e8f5e8', '#f1f8e9'
        ],
        background: '#ffffff',
        grid: 'rgba(0,0,0,0.1)',
        text: '#1b5e20'
    },
    'thermal': {
        name: 'Thermal Energy',
        colors: [
            '#d32f2f', '#f44336', '#ff5722', '#ff7043', '#ff8a65',
            '#ffab91', '#ffccbc', '#fbe9e7', '#fff3e0', '#fff8f5'
        ],
        background: '#ffffff',
        grid: 'rgba(0,0,0,0.1)',
        text: '#b71c1c'
    }
};

/**
 * Export configurations for use in ChartFactory
 */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CHART_CONFIGS,
        CHART_CATEGORIES,
        LIBRARY_CAPABILITIES,
        CHART_THEMES
    };
} else if (typeof window !== 'undefined') {
    window.CHART_CONFIGS = CHART_CONFIGS;
    window.CHART_CATEGORIES = CHART_CATEGORIES;
    window.LIBRARY_CAPABILITIES = LIBRARY_CAPABILITIES;
    window.CHART_THEMES = CHART_THEMES;
}