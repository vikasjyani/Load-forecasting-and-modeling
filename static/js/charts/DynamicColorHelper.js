/**
 * Dynamic Color Helper for KSEB Energy Futures Platform
 * Provides utilities to transition from hardcoded colors to dynamic color management
 * 
 * @author KSEB Development Team
 * @version 1.0.0
 */

class DynamicColorHelper {
    constructor(colorManagerIntegration) {
        this.colorIntegration = colorManagerIntegration;
        this.migrationMap = new Map();
        this.initializeMigrationMap();
    }

    /**
     * Initialize migration mapping for common hardcoded values
     */
    initializeMigrationMap() {
        // Common sector mappings found in existing code
        this.migrationMap.set('sectors', {
            'Domestic': 'domestic',
            'Commercial': 'commercial', 
            'Industrial': 'industrial',
            'Agriculture': 'agriculture',
            'Public Lighting': 'public_lighting',
            'Traction': 'traction',
            'Others': 'others',
            'Miscellaneous': 'miscellaneous'
        });

        // Common model mappings
        this.migrationMap.set('models', {
            'SLR': 'slr',
            'MLR': 'mlr', 
            'ARIMA': 'arima',
            'SARIMA': 'sarima',
            'WAM': 'wam',
            'Simple Linear Regression': 'slr',
            'Multiple Linear Regression': 'mlr'
        });

        // Common carrier mappings
        this.migrationMap.set('carriers', {
            'electricity': 'electricity',
            'gas': 'gas',
            'oil': 'oil',
            'coal': 'coal',
            'renewable': 'renewable',
            'solar': 'solar',
            'wind': 'wind',
            'hydro': 'hydro'
        });

        // PyPSA component mappings
        this.migrationMap.set('pypsa', {
            'Generator': 'generator',
            'Load': 'load',
            'Line': 'line',
            'Bus': 'bus',
            'Storage': 'storage',
            'Link': 'link',
            'Store': 'store'
        });
    }

    /**
     * Get dynamic colors for a list of items with fallback support
     * @param {string} category - Category (sectors, models, carriers, pypsa)
     * @param {Array} items - Array of item names
     * @param {Object} fallbackColors - Optional fallback color mapping
     * @returns {Promise<Array>} Array of colors
     */
    async getDynamicColors(category, items, fallbackColors = null) {
        try {
            // Try to get colors using dynamic system
            const colors = await this.colorIntegration.getEnergyColors(category, items);
            
            // Validate that we got actual colors (not just defaults)
            const hasValidColors = colors.some(color => 
                color && color !== this.colorIntegration.colorManager.getColor('charts.default')
            );
            
            if (hasValidColors) {
                return colors;
            }
            
            // Fallback to provided colors or generate new ones
            if (fallbackColors) {
                return items.map(item => fallbackColors[item] || this.generateFallbackColor(item));
            }
            
            return this.generateColorPalette(items.length);
            
        } catch (error) {
            console.warn(`Failed to get dynamic colors for ${category}:`, error);
            
            // Use fallback colors if provided
            if (fallbackColors) {
                return items.map(item => fallbackColors[item] || this.generateFallbackColor(item));
            }
            
            // Generate basic color palette
            return this.generateColorPalette(items.length);
        }
    }

    /**
     * Synchronous version for immediate use
     * @param {string} category - Category
     * @param {Array} items - Array of item names
     * @param {Object} fallbackColors - Optional fallback color mapping
     * @returns {Array} Array of colors
     */
    getDynamicColorsSync(category, items, fallbackColors = null) {
        try {
            const colors = this.colorIntegration.getEnergyColorsSync(category, items);
            
            // Validate colors
            const hasValidColors = colors.some(color => 
                color && color !== this.colorIntegration.colorManager.getColor('charts.default')
            );
            
            if (hasValidColors) {
                return colors;
            }
            
            // Fallback
            if (fallbackColors) {
                return items.map(item => fallbackColors[item] || this.generateFallbackColor(item));
            }
            
            return this.generateColorPalette(items.length);
            
        } catch (error) {
            console.warn(`Failed to get dynamic colors for ${category}:`, error);
            
            if (fallbackColors) {
                return items.map(item => fallbackColors[item] || this.generateFallbackColor(item));
            }
            
            return this.generateColorPalette(items.length);
        }
    }

    /**
     * Migrate existing hardcoded color configuration to dynamic system
     * @param {Object} existingConfig - Existing chart configuration with hardcoded colors
     * @param {string} category - Color category
     * @param {Array} items - Items to color
     * @returns {Promise<Object>} Updated configuration
     */
    async migrateChartConfig(existingConfig, category, items) {
        const config = { ...existingConfig };
        
        try {
            // Extract existing colors as fallback
            const fallbackColors = this.extractExistingColors(config);
            
            // Get dynamic colors
            const dynamicColors = await this.getDynamicColors(category, items, fallbackColors);
            
            // Apply colors based on chart library
            if (config.type === 'chartjs' || config.datasets) {
                config.datasets = config.datasets?.map((dataset, index) => ({
                    ...dataset,
                    backgroundColor: dynamicColors[index] || dynamicColors[0],
                    borderColor: dynamicColors[index] || dynamicColors[0]
                }));
            } else if (config.data && Array.isArray(config.data)) {
                // Plotly format
                config.data = config.data.map((trace, index) => ({
                    ...trace,
                    marker: {
                        ...trace.marker,
                        color: dynamicColors[index] || dynamicColors[0]
                    }
                }));
            } else if (config.series) {
                // ECharts format
                config.color = dynamicColors;
            }
            
            return config;
            
        } catch (error) {
            console.warn('Failed to migrate chart config:', error);
            return existingConfig;
        }
    }

    /**
     * Extract existing colors from chart configuration
     * @param {Object} config - Chart configuration
     * @returns {Object} Extracted color mapping
     */
    extractExistingColors(config) {
        const colors = {};
        
        if (config.datasets) {
            config.datasets.forEach((dataset, index) => {
                if (dataset.label && dataset.backgroundColor) {
                    colors[dataset.label] = dataset.backgroundColor;
                }
            });
        } else if (config.data && Array.isArray(config.data)) {
            config.data.forEach((trace, index) => {
                if (trace.name && trace.marker?.color) {
                    colors[trace.name] = trace.marker.color;
                }
            });
        }
        
        return colors;
    }

    /**
     * Generate a fallback color based on item name
     * @param {string} item - Item name
     * @returns {string} Generated color
     */
    generateFallbackColor(item) {
        // Simple hash-based color generation
        let hash = 0;
        for (let i = 0; i < item.length; i++) {
            hash = item.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        const hue = Math.abs(hash) % 360;
        return `hsl(${hue}, 70%, 50%)`;
    }

    /**
     * Generate a color palette
     * @param {number} count - Number of colors needed
     * @returns {Array} Array of colors
     */
    generateColorPalette(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const hue = (i * 360 / count) % 360;
            colors.push(`hsl(${hue}, 70%, 50%)`);
        }
        return colors;
    }

    /**
     * Check if dynamic colors are available for a category
     * @param {string} category - Category to check
     * @returns {Promise<boolean>} True if dynamic colors are available
     */
    async isDynamicColorAvailable(category) {
        try {
            await this.colorIntegration.initializeDynamicMappings();
            return this.colorIntegration.dynamicMappings[category] && 
                   this.colorIntegration.dynamicMappings[category].size > 0;
        } catch (error) {
            return false;
        }
    }

    /**
     * Get available sectors from dynamic system
     * @returns {Promise<Array>} Array of available sectors
     */
    async getAvailableSectors() {
        try {
            await this.colorIntegration.initializeDynamicMappings();
            return this.colorIntegration.cache.sectors || [];
        } catch (error) {
            console.warn('Failed to get available sectors:', error);
            return [];
        }
    }

    /**
     * Get available carriers from dynamic system
     * @returns {Promise<Array>} Array of available carriers
     */
    async getAvailableCarriers() {
        try {
            await this.colorIntegration.initializeDynamicMappings();
            return this.colorIntegration.cache.carriers || [];
        } catch (error) {
            console.warn('Failed to get available carriers:', error);
            return [];
        }
    }

    /**
     * Create a migration guide for existing code
     * @param {string} category - Category to migrate
     * @returns {Object} Migration guide
     */
    createMigrationGuide(category) {
        const guide = {
            category,
            oldApproach: 'Hardcoded color mappings',
            newApproach: 'Dynamic color system with backend integration',
            steps: [
                '1. Replace hardcoded color objects with DynamicColorHelper calls',
                '2. Use async/await for color retrieval',
                '3. Provide fallback colors for offline scenarios',
                '4. Test with different sector/carrier combinations'
            ],
            codeExample: {
                old: `const colors = {
    'Domestic': '#FF6384',
    'Commercial': '#36A2EB',
    'Industrial': '#FFCE56'
};`,
                new: `const colors = await dynamicColorHelper.getDynamicColors(
    '${category}', 
    ['Domestic', 'Commercial', 'Industrial'],
    fallbackColors // optional
);`
            }
        };
        
        return guide;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamicColorHelper;
} else if (typeof window !== 'undefined') {
    window.DynamicColorHelper = DynamicColorHelper;
}