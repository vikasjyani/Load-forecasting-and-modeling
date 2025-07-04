/**
 * ColorManagerIntegration.js
 * Enhanced color management integration for centralized chart system
 * Provides seamless integration between ColorManager and chart libraries
 */

class ColorManagerIntegration {
    constructor(colorManager) {
        this.colorManager = colorManager;
        
        // Dynamic color mappings - will be populated from backend
        this.dynamicMappings = {
            sectors: new Map(),
            models: new Map(),
            carriers: new Map(),
            pypsa: new Map()
        };
        
        // Static fallback mappings for common models
        this.staticMappings = {
            models: {
                'SLR': 'models.slr',
                'MLR': 'models.mlr',
                'ARIMA': 'models.arima',
                'SARIMA': 'models.sarima',
                'WAM': 'models.wam'
            },
            pypsa: {
                'Generator': 'pypsa.generator',
                'Load': 'pypsa.load',
                'Line': 'pypsa.line',
                'Bus': 'pypsa.bus',
                'Storage': 'pypsa.storage'
            }
        };
        
        // Cache for API responses
        this.cache = {
            sectors: null,
            carriers: null,
            lastUpdated: null
        };
        
        // Initialize dynamic mappings
        this.initializeDynamicMappings();
    }

    /**
     * Initialize dynamic mappings from backend APIs
     */
    async initializeDynamicMappings() {
        try {
            // Check cache validity (refresh every 5 minutes)
            const now = Date.now();
            if (this.cache.lastUpdated && (now - this.cache.lastUpdated) < 300000) {
                return;
            }
            
            await Promise.all([
                this.loadDynamicSectors(),
                this.loadDynamicCarriers()
            ]);
            
            this.cache.lastUpdated = now;
        } catch (error) {
            console.warn('Failed to initialize dynamic mappings:', error);
        }
    }
    
    /**
     * Load dynamic sector mappings from backend
     */
    async loadDynamicSectors() {
        try {
            // Try to get sectors from current scenario data
            const response = await fetch('/demand_visualization/api/scenarios');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data.scenarios.length > 0) {
                    const allSectors = new Set();
                    data.data.scenarios.forEach(scenario => {
                        if (scenario.available_sectors) {
                            scenario.available_sectors.forEach(sector => allSectors.add(sector));
                        }
                    });
                    
                    // Create dynamic mappings for discovered sectors
                    this.dynamicMappings.sectors.clear();
                    Array.from(allSectors).forEach(sector => {
                        const normalizedKey = this.normalizeName(sector);
                        this.dynamicMappings.sectors.set(sector, `sectors.${normalizedKey}`);
                    });
                    
                    this.cache.sectors = Array.from(allSectors);
                }
            }
        } catch (error) {
            console.warn('Failed to load dynamic sectors:', error);
        }
    }
    
    /**
     * Load dynamic carrier mappings from PyPSA results
     */
    async loadDynamicCarriers() {
        try {
            // Try to get carriers from color management API
            const response = await fetch('/chart_management/colors/carriers');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.carrier_colors) {
                    this.dynamicMappings.carriers.clear();
                    Object.keys(data.carrier_colors).forEach(carrier => {
                        const normalizedKey = this.normalizeName(carrier);
                        this.dynamicMappings.carriers.set(carrier, `carriers.${normalizedKey}`);
                    });
                    
                    this.cache.carriers = Object.keys(data.carrier_colors);
                }
            }
        } catch (error) {
            console.warn('Failed to load dynamic carriers:', error);
        }
    }
    
    /**
     * Normalize name for color key generation
     * @param {string} name - Original name
     * @returns {string} Normalized name
     */
    normalizeName(name) {
        return name.toLowerCase()
                  .replace(/[^a-z0-9]/g, '_')
                  .replace(/_+/g, '_')
                  .replace(/^_|_$/g, '');
    }
    
    /**
     * Get colors for energy-specific categories with dynamic mapping
     * @param {string} category - Category type (sectors, models, carriers, pypsa)
     * @param {Array} items - Array of item names
     * @returns {Array} Array of colors
     */
    async getEnergyColors(category, items) {
        // Ensure dynamic mappings are loaded
        await this.initializeDynamicMappings();
        
        const colors = [];
        
        for (const item of items) {
            let colorKey = null;
            
            // Try dynamic mapping first
            if (this.dynamicMappings[category] && this.dynamicMappings[category].has(item)) {
                colorKey = this.dynamicMappings[category].get(item);
            }
            // Fallback to static mapping
            else if (this.staticMappings[category] && this.staticMappings[category][item]) {
                colorKey = this.staticMappings[category][item];
            }
            // Generate dynamic color key for unknown items
            else {
                const normalizedKey = this.normalizeName(item);
                colorKey = `${category}.${normalizedKey}`;
                
                // Store in dynamic mapping for future use
                if (!this.dynamicMappings[category]) {
                    this.dynamicMappings[category] = new Map();
                }
                this.dynamicMappings[category].set(item, colorKey);
            }
            
            // Get color from color manager
            const color = this.colorManager.getColor(colorKey) || this.colorManager.getColor('charts.default');
            colors.push(color);
        }
        
        return colors;
    }
    
    /**
     * Synchronous version for backward compatibility
     * @param {string} category - Category type
     * @param {Array} items - Array of item names
     * @returns {Array} Array of colors
     */
    getEnergyColorsSync(category, items) {
        const colors = [];
        
        for (const item of items) {
            let colorKey = null;
            
            // Try dynamic mapping first
            if (this.dynamicMappings[category] && this.dynamicMappings[category].has(item)) {
                colorKey = this.dynamicMappings[category].get(item);
            }
            // Fallback to static mapping
            else if (this.staticMappings[category] && this.staticMappings[category][item]) {
                colorKey = this.staticMappings[category][item];
            }
            // Generate dynamic color key for unknown items
            else {
                const normalizedKey = this.normalizeName(item);
                colorKey = `${category}.${normalizedKey}`;
            }
            
            // Get color from color manager
            const color = this.colorManager.getColor(colorKey) || this.colorManager.getColor('charts.default');
            colors.push(color);
        }
        
        return colors;
    }

    /**
     * Create Chart.js dataset with energy-aware colors (async version)
     * @param {Object} config - Dataset configuration
     * @returns {Promise<Object>} Enhanced dataset with colors
     */
    async createEnergyDataset(config) {
        const { data, labels, category, type = 'line', ...otherConfig } = config;
        
        let colors;
        if (category && labels) {
            colors = await this.getEnergyColors(category, labels);
        } else {
            colors = this.colorManager.getColorPalette(data.length);
        }

        const dataset = {
            data,
            ...otherConfig
        };

        // Apply colors based on chart type
        if (type === 'line') {
            dataset.borderColor = colors[0] || colors;
            dataset.backgroundColor = this.addAlpha(colors[0] || colors, 0.1);
        } else if (type === 'bar' || type === 'pie') {
            dataset.backgroundColor = colors;
            dataset.borderColor = colors.map(color => this.addAlpha(color, 0.8));
        }

        return dataset;
    }
    
    /**
     * Create Chart.js dataset with energy-aware colors (sync version)
     * @param {Object} config - Dataset configuration
     * @returns {Object} Enhanced dataset with colors
     */
    createEnergyDatasetSync(config) {
        const { data, labels, category, type = 'line', ...otherConfig } = config;
        
        let colors;
        if (category && labels) {
            colors = this.getEnergyColorsSync(category, labels);
        } else {
            colors = this.colorManager.getColorPalette(data.length);
        }

        const dataset = {
            data,
            ...otherConfig
        };

        // Apply colors based on chart type
        if (type === 'line') {
            dataset.borderColor = colors[0] || colors;
            dataset.backgroundColor = this.addAlpha(colors[0] || colors, 0.1);
        } else if (type === 'bar' || type === 'pie') {
            dataset.backgroundColor = colors;
            dataset.borderColor = colors.map(color => this.addAlpha(color, 0.8));
        }

        return dataset;
    }

    /**
     * Enhance Plotly configuration with energy colors (async version)
     * @param {Object} config - Plotly configuration
     * @param {string} category - Energy category
     * @returns {Promise<Object>} Enhanced configuration
     */
    async enhancePlotlyConfig(config, category = null) {
        const enhanced = { ...config };
        
        if (enhanced.data && Array.isArray(enhanced.data)) {
            const enhancedData = [];
            
            for (let index = 0; index < enhanced.data.length; index++) {
                const trace = enhanced.data[index];
                const enhancedTrace = { ...trace };
                
                if (category && trace.name) {
                    const colors = await this.getEnergyColors(category, [trace.name]);
                    enhancedTrace.marker = {
                        ...enhancedTrace.marker,
                        color: colors[0]
                    };
                } else {
                    const palette = this.colorManager.getColorPalette(enhanced.data.length);
                    enhancedTrace.marker = {
                        ...enhancedTrace.marker,
                        color: palette[index]
                    };
                }
                
                enhancedData.push(enhancedTrace);
            }
            
            enhanced.data = enhancedData;
        }

        // Apply theme-based layout colors
        enhanced.layout = {
            ...enhanced.layout,
            paper_bgcolor: this.colorManager.getColor('theme.background'),
            plot_bgcolor: this.colorManager.getColor('theme.surface'),
            font: {
                ...enhanced.layout?.font,
                color: this.colorManager.getColor('theme.text')
            }
        };

        return enhanced;
    }
    
    /**
     * Enhance Plotly configuration with energy colors (sync version)
     * @param {Object} config - Plotly configuration
     * @param {string} category - Energy category
     * @returns {Object} Enhanced configuration
     */
    enhancePlotlyConfigSync(config, category = null) {
        const enhanced = { ...config };
        
        if (enhanced.data && Array.isArray(enhanced.data)) {
            enhanced.data = enhanced.data.map((trace, index) => {
                const enhancedTrace = { ...trace };
                
                if (category && trace.name) {
                    const colors = this.getEnergyColorsSync(category, [trace.name]);
                    enhancedTrace.marker = {
                        ...enhancedTrace.marker,
                        color: colors[0]
                    };
                } else {
                    const palette = this.colorManager.getColorPalette(enhanced.data.length);
                    enhancedTrace.marker = {
                        ...enhancedTrace.marker,
                        color: palette[index]
                    };
                }
                
                return enhancedTrace;
            });
        }

        // Apply theme-based layout colors
        enhanced.layout = {
            ...enhanced.layout,
            paper_bgcolor: this.colorManager.getColor('theme.background'),
            plot_bgcolor: this.colorManager.getColor('theme.surface'),
            font: {
                ...enhanced.layout?.font,
                color: this.colorManager.getColor('theme.text')
            }
        };

        return enhanced;
    }

    /**
     * Enhance ECharts configuration with energy colors (async version)
     * @param {Object} config - ECharts configuration
     * @param {string} category - Energy category
     * @returns {Promise<Object>} Enhanced configuration
     */
    async enhanceEChartsConfig(config, category = null) {
        const enhanced = { ...config };
        
        // Apply color palette
        if (category && enhanced.series) {
            const seriesNames = enhanced.series.map(s => s.name).filter(Boolean);
            if (seriesNames.length > 0) {
                enhanced.color = await this.getEnergyColors(category, seriesNames);
            }
        } else {
            const seriesCount = enhanced.series ? enhanced.series.length : 5;
            enhanced.color = this.colorManager.getColorPalette(seriesCount);
        }

        // Apply theme colors
        enhanced.backgroundColor = this.colorManager.getColor('theme.background');
        
        if (enhanced.textStyle) {
            enhanced.textStyle.color = this.colorManager.getColor('theme.text');
        }

        return enhanced;
    }
    
    /**
     * Enhance ECharts configuration with energy colors (sync version)
     * @param {Object} config - ECharts configuration
     * @param {string} category - Energy category
     * @returns {Object} Enhanced configuration
     */
    enhanceEChartsConfigSync(config, category = null) {
        const enhanced = { ...config };
        
        // Apply color palette
        if (category && enhanced.series) {
            const seriesNames = enhanced.series.map(s => s.name).filter(Boolean);
            if (seriesNames.length > 0) {
                enhanced.color = this.getEnergyColorsSync(category, seriesNames);
            }
        } else {
            const seriesCount = enhanced.series ? enhanced.series.length : 5;
            enhanced.color = this.colorManager.getColorPalette(seriesCount);
        }

        // Apply theme colors
        enhanced.backgroundColor = this.colorManager.getColor('theme.background');
        
        if (enhanced.textStyle) {
            enhanced.textStyle.color = this.colorManager.getColor('theme.text');
        }

        return enhanced;
    }

    /**
     * Get PyPSA-specific color mapping (async version)
     * @param {string} component - PyPSA component type
     * @param {Array} items - Component items
     * @returns {Promise<Object>} Color mapping
     */
    async getPyPSAColors(component, items) {
        const colors = await this.getEnergyColors('pypsa', [component]);
        const baseColor = colors[0];
        
        const colorMap = {};
        items.forEach((item, index) => {
            colorMap[item] = this.generateVariation(baseColor, index, items.length);
        });
        
        return colorMap;
    }
    
    /**
     * Get PyPSA-specific color mapping (sync version)
     * @param {string} component - PyPSA component type
     * @param {Array} items - Component items
     * @returns {Object} Color mapping
     */
    getPyPSAColorsSync(component, items) {
        const colors = this.getEnergyColorsSync('pypsa', [component]);
        const baseColor = colors[0];
        
        const colorMap = {};
        items.forEach((item, index) => {
            colorMap[item] = this.generateVariation(baseColor, index, items.length);
        });
        
        return colorMap;
    }

    /**
     * Generate color variations for similar items
     * @param {string} baseColor - Base color
     * @param {number} index - Item index
     * @param {number} total - Total items
     * @returns {string} Varied color
     */
    generateVariation(baseColor, index, total) {
        if (total === 1) return baseColor;
        
        // Convert to HSL and vary lightness/saturation
        const hsl = this.hexToHsl(baseColor);
        const variation = (index / (total - 1)) * 0.3 - 0.15; // ±15% variation
        
        hsl.l = Math.max(0.1, Math.min(0.9, hsl.l + variation));
        
        return this.hslToHex(hsl);
    }

    /**
     * Add alpha transparency to color
     * @param {string} color - Hex color
     * @param {number} alpha - Alpha value (0-1)
     * @returns {string} RGBA color
     */
    addAlpha(color, alpha) {
        const rgb = this.hexToRgb(color);
        return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
    }

    /**
     * Convert hex to RGB
     * @param {string} hex - Hex color
     * @returns {Object} RGB object
     */
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    /**
     * Convert hex to HSL
     * @param {string} hex - Hex color
     * @returns {Object} HSL object
     */
    hexToHsl(hex) {
        const rgb = this.hexToRgb(hex);
        const r = rgb.r / 255;
        const g = rgb.g / 255;
        const b = rgb.b / 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;

        if (max === min) {
            h = s = 0;
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }

        return { h, s, l };
    }

    /**
     * Convert HSL to hex
     * @param {Object} hsl - HSL object
     * @returns {string} Hex color
     */
    hslToHex({ h, s, l }) {
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
            r = g = b = l;
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
     * Register color change listener
     * @param {Function} callback - Callback function
     */
    onColorChange(callback) {
        if (this.colorManager.addEventListener) {
            this.colorManager.addEventListener('colorChanged', callback);
        }
    }

    /**
     * Update all charts when colors change
     * @param {Array} chartInstances - Array of chart instances
     */
    updateChartsOnColorChange(chartInstances) {
        this.onColorChange(() => {
            chartInstances.forEach(chart => {
                if (chart.update) {
                    chart.update();
                } else if (chart.setOption) {
                    // ECharts
                    chart.setOption(chart.getOption(), true);
                } else if (chart.redraw) {
                    // Plotly
                    chart.redraw();
                }
            });
        });
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ColorManagerIntegration;
} else {
    window.ColorManagerIntegration = ColorManagerIntegration;
}