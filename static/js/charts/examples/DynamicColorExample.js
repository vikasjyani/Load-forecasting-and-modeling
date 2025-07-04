/**
 * Dynamic Color System Usage Examples
 * Demonstrates how to migrate from hardcoded colors to dynamic color management
 * 
 * @author KSEB Development Team
 * @version 1.0.0
 */

/**
 * Example 1: Basic Dynamic Color Usage
 * Shows how to replace hardcoded sector colors with dynamic colors
 */
class DynamicColorExamples {
    constructor() {
        this.colorManager = null;
        this.colorIntegration = null;
        this.dynamicHelper = null;
        this.initialized = false;
    }

    /**
     * Initialize the dynamic color system
     */
    async initialize() {
        try {
            // Initialize ColorManager (assuming it's available globally)
            this.colorManager = window.ColorManager || new ColorManager();
            
            // Initialize ColorManagerIntegration
            this.colorIntegration = new ColorManagerIntegration(this.colorManager);
            
            // Initialize DynamicColorHelper
            this.dynamicHelper = new DynamicColorHelper(this.colorIntegration);
            
            // Wait for dynamic mappings to load
            await this.colorIntegration.initializeDynamicMappings();
            
            this.initialized = true;
            console.log('Dynamic color system initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize dynamic color system:', error);
        }
    }

    /**
     * Example 1: Migrating Demand Visualization Chart Colors
     */
    async example1_DemandVisualizationMigration() {
        if (!this.initialized) await this.initialize();

        console.log('=== Example 1: Demand Visualization Migration ===');

        // OLD APPROACH (Hardcoded)
        const oldSectorColors = {
            'Domestic': '#FF6384',
            'Commercial': '#36A2EB', 
            'Industrial': '#FFCE56',
            'Agriculture': '#4BC0C0',
            'Public Lighting': '#9966FF',
            'Traction': '#FF9F40',
            'Others': '#FF6384'
        };

        const sectors = ['Domestic', 'Commercial', 'Industrial', 'Agriculture'];

        // NEW APPROACH (Dynamic)
        try {
            const dynamicColors = await this.dynamicHelper.getDynamicColors(
                'sectors', 
                sectors, 
                oldSectorColors // fallback
            );

            console.log('Old colors:', sectors.map(s => oldSectorColors[s]));
            console.log('Dynamic colors:', dynamicColors);

            // Create Chart.js configuration with dynamic colors
            const chartConfig = {
                type: 'bar',
                data: {
                    labels: sectors,
                    datasets: [{
                        label: 'Energy Consumption (MWh)',
                        data: [1200, 800, 1500, 400],
                        backgroundColor: dynamicColors,
                        borderColor: dynamicColors.map(color => this.adjustColorOpacity(color, 1.0)),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Sector-wise Energy Consumption (Dynamic Colors)'
                        }
                    }
                }
            };

            return chartConfig;

        } catch (error) {
            console.error('Failed to get dynamic colors:', error);
            // Fallback to old approach
            return this.createFallbackChart(sectors, oldSectorColors);
        }
    }

    /**
     * Example 2: PyPSA Component Color Migration
     */
    async example2_PyPSAComponentMigration() {
        if (!this.initialized) await this.initialize();

        console.log('=== Example 2: PyPSA Component Migration ===');

        // OLD APPROACH
        const oldComponentColors = {
            'Generator': '#FF6384',
            'Load': '#36A2EB',
            'Line': '#FFCE56',
            'Bus': '#4BC0C0',
            'Storage': '#9966FF'
        };

        const components = ['Generator', 'Load', 'Line', 'Bus', 'Storage'];
        const componentData = [25, 15, 30, 10, 20];

        // NEW APPROACH
        try {
            const dynamicColors = await this.dynamicHelper.getDynamicColors(
                'pypsa',
                components,
                oldComponentColors
            );

            // Create Plotly configuration
            const plotlyConfig = {
                data: [{
                    type: 'pie',
                    labels: components,
                    values: componentData,
                    marker: {
                        colors: dynamicColors
                    },
                    textinfo: 'label+percent',
                    textposition: 'outside'
                }],
                layout: {
                    title: 'PyPSA Component Distribution (Dynamic Colors)',
                    showlegend: true
                }
            };

            console.log('PyPSA dynamic colors applied:', dynamicColors);
            return plotlyConfig;

        } catch (error) {
            console.error('Failed to get PyPSA colors:', error);
            return this.createFallbackPieChart(components, componentData, oldComponentColors);
        }
    }

    /**
     * Example 3: Model Comparison with Dynamic Colors
     */
    async example3_ModelComparisonMigration() {
        if (!this.initialized) await this.initialize();

        console.log('=== Example 3: Model Comparison Migration ===');

        const models = ['SLR', 'MLR', 'ARIMA', 'SARIMA', 'WAM'];
        const accuracyData = [85.2, 89.7, 92.1, 94.3, 87.8];

        // OLD APPROACH
        const oldModelColors = {
            'SLR': '#FF6384',
            'MLR': '#36A2EB',
            'ARIMA': '#FFCE56', 
            'SARIMA': '#4BC0C0',
            'WAM': '#9966FF'
        };

        // NEW APPROACH
        try {
            const dynamicColors = await this.dynamicHelper.getDynamicColors(
                'models',
                models,
                oldModelColors
            );

            // Create line chart configuration
            const lineChartConfig = {
                type: 'line',
                data: {
                    labels: models,
                    datasets: [{
                        label: 'Model Accuracy (%)',
                        data: accuracyData,
                        borderColor: dynamicColors[0] || '#36A2EB',
                        backgroundColor: this.adjustColorOpacity(dynamicColors[0] || '#36A2EB', 0.1),
                        pointBackgroundColor: dynamicColors,
                        pointBorderColor: dynamicColors,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Forecasting Model Accuracy Comparison'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: 80,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Accuracy (%)'
                            }
                        }
                    }
                }
            };

            console.log('Model comparison colors:', dynamicColors);
            return lineChartConfig;

        } catch (error) {
            console.error('Failed to get model colors:', error);
            return this.createFallbackLineChart(models, accuracyData, oldModelColors);
        }
    }

    /**
     * Example 4: Real-time Color Updates
     */
    async example4_RealTimeColorUpdates() {
        if (!this.initialized) await this.initialize();

        console.log('=== Example 4: Real-time Color Updates ===');

        // Simulate scenario change
        const scenarios = [
            { name: 'Base Case', sectors: ['Domestic', 'Commercial', 'Industrial'] },
            { name: 'High Growth', sectors: ['Domestic', 'Commercial', 'Industrial', 'Agriculture', 'Traction'] },
            { name: 'Green Transition', sectors: ['Domestic', 'Commercial', 'Industrial', 'Agriculture', 'Public Lighting', 'EV Charging'] }
        ];

        const results = [];

        for (const scenario of scenarios) {
            try {
                // Force refresh of dynamic mappings
                await this.colorIntegration.initializeDynamicMappings();
                
                const colors = await this.dynamicHelper.getDynamicColors('sectors', scenario.sectors);
                
                results.push({
                    scenario: scenario.name,
                    sectors: scenario.sectors,
                    colors: colors
                });

                console.log(`${scenario.name}:`, {
                    sectors: scenario.sectors,
                    colors: colors
                });

            } catch (error) {
                console.error(`Failed to get colors for ${scenario.name}:`, error);
            }
        }

        return results;
    }

    /**
     * Example 5: Synchronous vs Asynchronous Usage
     */
    async example5_SyncVsAsync() {
        if (!this.initialized) await this.initialize();

        console.log('=== Example 5: Sync vs Async Usage ===');

        const testSectors = ['Domestic', 'Commercial', 'Industrial'];

        // Asynchronous approach (recommended)
        console.time('Async Color Retrieval');
        const asyncColors = await this.dynamicHelper.getDynamicColors('sectors', testSectors);
        console.timeEnd('Async Color Retrieval');
        console.log('Async colors:', asyncColors);

        // Synchronous approach (for immediate use)
        console.time('Sync Color Retrieval');
        const syncColors = this.dynamicHelper.getDynamicColorsSync('sectors', testSectors);
        console.timeEnd('Sync Color Retrieval');
        console.log('Sync colors:', syncColors);

        // Compare results
        const colorsMatch = JSON.stringify(asyncColors) === JSON.stringify(syncColors);
        console.log('Colors match:', colorsMatch);

        return { asyncColors, syncColors, colorsMatch };
    }

    /**
     * Example 6: Migration Guide Generation
     */
    example6_MigrationGuide() {
        console.log('=== Example 6: Migration Guide ===');

        const categories = ['sectors', 'models', 'carriers', 'pypsa'];
        const guides = {};

        categories.forEach(category => {
            guides[category] = this.dynamicHelper.createMigrationGuide(category);
            console.log(`\n${category.toUpperCase()} Migration Guide:`);
            console.log(guides[category]);
        });

        return guides;
    }

    /**
     * Utility: Adjust color opacity
     */
    adjustColorOpacity(color, opacity) {
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${opacity})`;
        }
        return color;
    }

    /**
     * Fallback chart creation
     */
    createFallbackChart(sectors, colors) {
        return {
            type: 'bar',
            data: {
                labels: sectors,
                datasets: [{
                    label: 'Fallback Data',
                    data: sectors.map(() => Math.random() * 1000),
                    backgroundColor: sectors.map(s => colors[s] || '#999999')
                }]
            }
        };
    }

    /**
     * Fallback pie chart creation
     */
    createFallbackPieChart(labels, data, colors) {
        return {
            data: [{
                type: 'pie',
                labels: labels,
                values: data,
                marker: {
                    colors: labels.map(l => colors[l] || '#999999')
                }
            }],
            layout: {
                title: 'Fallback Pie Chart'
            }
        };
    }

    /**
     * Fallback line chart creation
     */
    createFallbackLineChart(labels, data, colors) {
        return {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Fallback Line',
                    data: data,
                    borderColor: '#36A2EB',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)'
                }]
            }
        };
    }

    /**
     * Run all examples
     */
    async runAllExamples() {
        console.log('Running all Dynamic Color System examples...');
        
        try {
            await this.initialize();
            
            const results = {
                example1: await this.example1_DemandVisualizationMigration(),
                example2: await this.example2_PyPSAComponentMigration(),
                example3: await this.example3_ModelComparisonMigration(),
                example4: await this.example4_RealTimeColorUpdates(),
                example5: await this.example5_SyncVsAsync(),
                example6: this.example6_MigrationGuide()
            };
            
            console.log('All examples completed successfully!');
            return results;
            
        } catch (error) {
            console.error('Failed to run examples:', error);
            return null;
        }
    }
}

// Usage instructions
const USAGE_INSTRUCTIONS = `
=== Dynamic Color System Usage Instructions ===

1. Initialize the system:
   const examples = new DynamicColorExamples();
   await examples.initialize();

2. Run individual examples:
   const demandChart = await examples.example1_DemandVisualizationMigration();
   const pypsaChart = await examples.example2_PyPSAComponentMigration();

3. Run all examples:
   const results = await examples.runAllExamples();

4. Integration in existing code:
   // Replace hardcoded colors
   const oldColors = { 'Domestic': '#FF6384', 'Commercial': '#36A2EB' };
   
   // With dynamic colors
   const dynamicColors = await dynamicHelper.getDynamicColors(
       'sectors', 
       ['Domestic', 'Commercial'], 
       oldColors
   );

5. For immediate/synchronous use:
   const colors = dynamicHelper.getDynamicColorsSync('sectors', sectorList);

Note: Always provide fallback colors for offline scenarios!
`;

console.log(USAGE_INSTRUCTIONS);

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DynamicColorExamples, USAGE_INSTRUCTIONS };
} else if (typeof window !== 'undefined') {
    window.DynamicColorExamples = DynamicColorExamples;
    window.DYNAMIC_COLOR_USAGE_INSTRUCTIONS = USAGE_INSTRUCTIONS;
}