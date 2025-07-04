# KSEB Energy Futures Platform - Chart and Visualization Analysis

## Overview

This document provides a comprehensive analysis of all chart types, plotting libraries, and visualization components used across the KSEB Energy Futures Platform. The platform employs a multi-layered visualization architecture combining backend chart generation with frontend interactive components.

## Technology Stack

### Backend Visualization Libraries
- **Chart.js 4.4.0**: Primary charting library for web-based visualizations
- **Plotly**: Used for advanced statistical plots and heatmaps
- **Matplotlib**: Backend chart generation and export functionality
- **ECharts**: Used in Load Profile Analysis for advanced interactive charts

### Frontend Chart Management
- **Vanilla JavaScript**: Custom chart management and interaction handling
- **Chart.js Integration**: Direct Chart.js API usage for dynamic charts
- **ECharts Integration**: Advanced charting for load profile analysis
- **Plotly.js**: Frontend Plotly integration for heatmaps

---

## Module-by-Module Chart Analysis

### 1. Demand Projection Module

#### Chart Types Available:

##### 1.1 Sector Analysis Charts
- **Chart Type**: Line, Bar, Area charts
- **Library**: Chart.js 4.4.0
- **Purpose**: Display demand forecasts for individual sectors
- **Data Source**: Excel files from `results/demand_projection/`
- **Features**:
  - Multi-model comparison (SLR, MLR, WAM, Time Series)
  - Dynamic year range filtering
  - Unit conversion (kWh, MWh, GWh, TWh)
  - Interactive tooltips with model details
  - Color-coded model differentiation

**Implementation Location**: 
- Backend: `services/demand_visualization_service.py`
- Frontend: `static/js/demand_visualization.js`
- Chart Generation: `utils/plot_utils.py` - `create_sector_chart_data()`

##### 1.2 Sector Comparison Charts
- **Chart Type**: Multi-line comparison charts
- **Library**: Chart.js 4.4.0
- **Purpose**: Compare demand across multiple sectors
- **Features**:
  - Cross-sector analysis
  - Model selection per sector
  - Synchronized year ranges
  - Dynamic legend management

**Implementation**: `utils/plot_utils.py` - `create_sector_comparison_chart_data()`

##### 1.3 Consolidated Electricity Demand Charts

###### 1.3.1 Stacked Sectoral Breakdown
- **Chart Type**: Stacked Bar Chart
- **Purpose**: Show total demand composition by sector
- **Features**:
  - Sector-wise color coding
  - Yearly progression visualization
  - Hover details for individual sectors

###### 1.3.2 Gross vs Net Demand Comparison
- **Chart Type**: Dual-line Chart
- **Purpose**: Compare gross demand vs net generation requirements
- **Features**:
  - T&D losses visualization
  - Efficiency analysis
  - Trend comparison

###### 1.3.3 T&D Losses Analysis
- **Chart Type**: Combined Line and Bar Chart
- **Purpose**: Analyze transmission and distribution losses
- **Features**:
  - Loss percentage trends
  - Absolute loss values
  - Efficiency indicators

###### 1.3.4 Sector Trends Analysis
- **Chart Type**: Multi-line Chart
- **Purpose**: Long-term sector growth trends
- **Features**:
  - Growth rate visualization
  - Comparative sector analysis
  - Trend extrapolation

**Implementation**: `utils/plot_utils.py` - `create_consolidated_electricity_chart_data()`

### 2. Demand Visualization Module

#### Chart Management Features:

##### 2.1 Dynamic Chart Configuration
- **Color Management**: Centralized color scheme management
- **Theme Support**: Light/dark theme switching
- **Export Options**: PNG, SVG, PDF export capabilities
- **Responsive Design**: Mobile and desktop optimization

##### 2.2 Interactive Features
- **Zoom and Pan**: Chart.js native zoom functionality
- **Legend Toggling**: Show/hide data series
- **Tooltip Customization**: Rich tooltip content with metadata
- **Filter Integration**: Real-time filter application

**Implementation**: 
- Frontend: `static/js/demand_visualization.js`
- Color Management: `static/js/color_manager.js`
- Chart Export: `services/chart_export_service.py`

### 3. Load Profile Generation Module

#### Chart Types Available:

##### 3.1 Load Profile Time Series
- **Chart Type**: Line Charts
- **Library**: ECharts
- **Purpose**: Display hourly/sub-hourly load profiles
- **Features**:
  - High-resolution time series
  - Peak and minimum point highlighting
  - Seasonal pattern visualization
  - Interactive time range selection

##### 3.2 Load Profile Heatmaps
- **Chart Type**: Heatmap
- **Library**: Plotly.js
- **Purpose**: Visualize load patterns across time dimensions
- **Features**:
  - Hour vs Day heatmaps
  - Month vs Hour patterns
  - Color intensity mapping
  - Interactive hover details

##### 3.3 Weekly Pattern Analysis
- **Chart Type**: Multi-line Chart
- **Library**: ECharts
- **Purpose**: Analyze weekly load patterns
- **Features**:
  - Day-of-week comparison
  - Seasonal variations
  - Workday vs weekend analysis

##### 3.4 Seasonal Comparison Charts
- **Chart Type**: Grouped Line Charts
- **Library**: ECharts
- **Purpose**: Compare load profiles across seasons
- **Features**:
  - Season-wise color coding
  - Temperature correlation
  - Holiday impact analysis

**Implementation**:
- Backend: `services/loadprofile_analysis_service.py`
- Frontend: `static/js/load_profile_analysis.js`
- Chart Generation: `services/loadprofile_visualization_service.py`

### 4. Load Profile Analysis Module

#### Advanced Chart Features:

##### 4.1 Enhanced Time Series Charts
- **Chart Type**: Advanced Line Charts with ECharts
- **Features**:
  - Data zoom functionality
  - Brush selection
  - Animation effects
  - Custom styling

```javascript
// Example from load_profile_analysis.js
function createTimeSeriesLineOption(data, title, unit, peak_point, min_point) {
    return {
        title: { text: title },
        tooltip: { trigger: 'axis' },
        dataZoom: [{ type: 'inside' }, { type: 'slider' }],
        series: [{
            type: 'line',
            data: data,
            smooth: true,
            markPoint: {
                data: [peak_point, min_point]
            }
        }]
    };
}
```

##### 4.2 Comparison Charts
- **Chart Type**: Multi-bar Charts
- **Purpose**: Compare multiple load profiles
- **Features**:
  - Side-by-side comparison
  - Statistical metrics overlay
  - Profile metadata display

##### 4.3 Chart Export and Download
- **Formats**: PNG, SVG
- **Features**:
  - High-resolution export
  - Custom filename generation
  - Batch export capabilities

**Implementation**: `static/js/load_profile_analysis.js`

### 5. PyPSA Modeling Module

#### Chart Types Available:

##### 5.1 Daily Profile Charts
- **Chart Type**: Line Charts
- **Library**: Plotly
- **Purpose**: Display daily load/generation profiles
- **Features**:
  - Component-wise breakdown
  - Interactive legends
  - Time-based filtering

##### 5.2 Load Duration Curves
- **Chart Type**: Sorted Line Charts
- **Purpose**: Analyze load duration characteristics
- **Features**:
  - Percentile analysis
  - Capacity factor visualization
  - Peak load identification

##### 5.3 Generation Mix Charts
- **Chart Type**: Stacked Area Charts
- **Purpose**: Show generation technology mix over time
- **Features**:
  - Technology-wise color coding
  - Renewable vs conventional breakdown
  - Capacity utilization analysis

##### 5.4 Capacity Charts
- **Chart Type**: Bar Charts
- **Purpose**: Display installed capacity by technology
- **Features**:
  - Technology comparison
  - Capacity additions tracking
  - Investment analysis

##### 5.5 Energy Balance Charts
- **Chart Type**: Sankey Diagrams / Flow Charts
- **Purpose**: Visualize energy flow in the system
- **Features**:
  - Source to sink mapping
  - Loss visualization
  - Efficiency analysis

##### 5.6 Network Flow Charts
- **Chart Type**: Network Diagrams
- **Purpose**: Show power flow between network nodes
- **Features**:
  - Geographic mapping
  - Flow direction indicators
  - Congestion visualization

##### 5.7 Cost Breakdown Charts
- **Chart Type**: Pie Charts / Stacked Bars
- **Purpose**: Analyze system costs by component
- **Features**:
  - CAPEX vs OPEX breakdown
  - Technology-wise costs
  - Marginal cost analysis

##### 5.8 Emissions Charts
- **Chart Type**: Line and Bar Charts
- **Purpose**: Track CO2 emissions over time
- **Features**:
  - Emissions by technology
  - Reduction targets tracking
  - Carbon intensity analysis

##### 5.9 Storage Charts
- **Chart Type**: Area Charts with State of Charge
- **Purpose**: Analyze energy storage operation
- **Features**:
  - SOC visualization
  - Charge/discharge cycles
  - Storage utilization metrics

##### 5.10 Price Analysis Charts
- **Chart Type**: Line Charts and Heatmaps
- **Purpose**: Electricity price analysis
- **Features**:
  - Nodal price differences
  - Price duration curves
  - Market clearing visualization

**Implementation**:
- Backend: `services/pypsa_visualization_service.py`
- Frontend: `static/js/pypsa_results.js`
- Chart Generation: `utils/pypsa_analysis_utils.py`

### 6. Chart Management System

#### Centralized Chart Management

##### 6.1 Chart Management Blueprint
- **File**: `blueprints/chart_management_bp.py`
- **Purpose**: RESTful API for chart operations
- **Endpoints**:
  - `/api/charts/pypsa/daily-profile`
  - `/api/charts/pypsa/load-duration-curve`
  - `/api/charts/pypsa/generation-mix`
  - `/api/charts/loadprofile/heatmap`
  - `/api/charts/loadprofile/weekly-pattern`
  - `/api/charts/export/{format_type}`

##### 6.2 Theme Management
- **Endpoints**:
  - `GET /api/charts/themes` - Get available themes
  - `POST /api/charts/themes/{theme_name}` - Set theme
  - `POST /api/charts/themes/custom` - Create custom theme
  - `GET /api/charts/colors/chart` - Get chart colors

##### 6.3 Export Functionality
- **Formats**: PNG, SVG, PDF, CSV, Excel
- **Features**:
  - Single chart export
  - Batch export
  - Custom resolution
  - Metadata inclusion

**Implementation**: `blueprints/chart_management_bp.py`

---

## Color Management System

### Centralized Color Management
- **File**: `utils/color_manager.py`
- **Frontend**: `static/js/color_manager.js`
- **Features**:
  - Consistent color schemes across modules
  - Theme-based color palettes
  - Dynamic color updates
  - Accessibility compliance

### Color Categories:
1. **Sector Colors**: Predefined colors for energy sectors
2. **Model Colors**: Colors for forecasting models
3. **Technology Colors**: Colors for generation technologies
4. **Chart Colors**: General chart color palettes
5. **Theme Colors**: Light/dark theme variations

---

## Chart Configuration Standards

### Chart.js 4.4.0 Configuration
```javascript
// Standard configuration from plot_utils.py
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        intersect: false,
        mode: "index"
    },
    animation: {
        duration: 750,
        easing: "easeInOutQuart"
    },
    plugins: {
        legend: {
            position: "bottom",
            labels: {
                usePointStyle: true,
                font: {
                    family: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
                }
            }
        },
        tooltip: {
            backgroundColor: "rgba(17, 24, 39, 0.95)",
            cornerRadius: 12
        }
    }
};
```

### ECharts Configuration
```javascript
// Standard ECharts setup from load_profile_analysis.js
function initializeCharts() {
    const mainChartElement = document.getElementById('mainChart');
    if (mainChartElement) {
        AppState.charts.main = echarts.init(mainChartElement);
        AppState.charts.main.on('click', handleChartClick);
        AppState.charts.main.on('datazoom', handleChartZoom);
    }
}
```

---

## Performance Optimizations

### Chart Rendering Optimizations
1. **Lazy Loading**: Charts loaded on demand
2. **Data Chunking**: Large datasets processed in chunks
3. **Canvas Optimization**: Hardware acceleration utilization
4. **Memory Management**: Chart instance cleanup

### Data Processing Optimizations
1. **Backend Preprocessing**: Data aggregation on server
2. **Caching**: Chart data caching for repeated requests
3. **Compression**: Data compression for large datasets
4. **Streaming**: Real-time data streaming for live updates

---

## Accessibility Features

### Chart Accessibility
1. **Color Blind Support**: Accessible color palettes
2. **Keyboard Navigation**: Chart navigation via keyboard
3. **Screen Reader Support**: ARIA labels and descriptions
4. **High Contrast**: High contrast theme options

### Interactive Features
1. **Zoom Controls**: Keyboard and mouse zoom
2. **Focus Management**: Proper focus handling
3. **Alternative Text**: Descriptive alt text for charts
4. **Data Tables**: Tabular data alternatives

---

## Export and Integration

### Export Formats
1. **Image Formats**: PNG, SVG, PDF
2. **Data Formats**: CSV, Excel, JSON
3. **Interactive Formats**: HTML with embedded charts
4. **Print Formats**: Print-optimized layouts

### Integration Points
1. **API Endpoints**: RESTful chart generation APIs
2. **Webhook Support**: Real-time chart updates
3. **Embedding**: Chart embedding in external applications
4. **Data Feeds**: Live data integration

---

## File Structure Summary

```
project/
├── utils/
│   ├── plot_utils.py              # Chart.js chart generation
│   ├── color_manager.py           # Centralized color management
│   └── pypsa_analysis_utils.py    # PyPSA-specific chart utilities
├── services/
│   ├── demand_visualization_service.py      # Demand chart service
│   ├── loadprofile_analysis_service.py     # Load profile chart service
│   ├── loadprofile_visualization_service.py # Load profile viz service
│   ├── pypsa_visualization_service.py      # PyPSA chart service
│   └── chart_export_service.py             # Export functionality
├── blueprints/
│   ├── chart_management_bp.py      # Chart management API
│   ├── demand_visualization_bp.py   # Demand visualization routes
│   ├── loadprofile_analysis_bp.py  # Load profile routes
│   └── pypsa_bp.py                 # PyPSA routes
├── static/js/
│   ├── demand_visualization.js     # Demand charts frontend
│   ├── load_profile_analysis.js    # Load profile charts frontend
│   ├── pypsa_results.js           # PyPSA charts frontend
│   └── color_manager.js           # Color management frontend
└── templates/
    ├── demand_visualization.html   # Demand visualization page
    ├── load_profile_analysis.html  # Load profile analysis page
    └── pypsa_results.html         # PyPSA results page
```

---

## Summary

The KSEB Energy Futures Platform employs a sophisticated multi-library charting system that provides:

1. **Comprehensive Coverage**: Charts for all aspects of energy analysis
2. **Technology Diversity**: Multiple charting libraries for optimal functionality
3. **Consistent Design**: Unified styling and color management
4. **Interactive Features**: Rich user interaction capabilities
5. **Export Flexibility**: Multiple export formats and options
6. **Performance Optimization**: Efficient rendering and data handling
7. **Accessibility Compliance**: Full accessibility support
8. **Modular Architecture**: Clean separation of concerns

This architecture ensures that the platform can handle complex energy analysis visualizations while maintaining performance, usability, and maintainability.