/**
 * Color Manager for Energy Platform
 * Dynamic color management with Chart.js 4.4.0 integration and real-time updates
 */

class ColorManager {
    constructor() {
        this.colors = {};
        this.initialized = false;
        this.apiBase = '/demand_visualization/api/colors';
        this.changeCallbacks = new Set();
        this.currentTheme = 'light';
        this.availableThemes = ['light', 'dark'];
        this.isUpdating = false;
        
        this.init();
    }

    async init() {
        try {
            await this.loadColors();
            await this.loadThemeInfo();
            this.setupEventListeners();
            this.initialized = true;
            console.log('✅ Color Manager initialized successfully');
        } catch (error) {
            console.error('❌ Color Manager initialization failed:', error);
            this.loadFallbackColors();
        }
    }

    async loadColors() {
        try {
            // Try to get colors from window.AppColors first (set by template)
            if (window.AppColors && typeof window.AppColors === 'object') {
                this.colors = JSON.parse(JSON.stringify(window.AppColors));
                console.log('🎨 Colors loaded from window.AppColors');
                return;
            }

            // Fallback to API
            const response = await fetch(`${this.apiBase}/get-all`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    this.colors = result.data;
                    this.currentTheme = result.data.current_theme || 'light';
                    this.availableThemes = result.data.available_themes || ['light', 'dark'];
                    console.log('🎨 Colors loaded from API');
                } else {
                    throw new Error(result.error || 'API returned no data');
                }
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.warn('⚠️ Color loading failed, using fallback:', error);
            this.loadFallbackColors();
        }
    }

    async loadThemeInfo() {
        try {
            const response = await fetch('/api/charts/themes');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.currentTheme = result.current_theme;
                    this.availableThemes = result.available_themes;
                }
            }
        } catch (error) {
            console.warn('Theme info loading failed:', error);
        }
    }

    loadFallbackColors() {
        this.colors = {
            sectors: {
                residential: "#2563EB",
                commercial: "#059669", 
                industrial: "#DC2626",
                transportation: "#7C3AED",
                agriculture: "#16A34A",
                public: "#EA580C",
                mining: "#92400E",
                construction: "#0891B2",
                services: "#BE185D",
                healthcare: "#0D9488",
                education: "#7C2D12",
                other: "#6B7280"
            },
            models: {
                MLR: "#3B82F6",
                SLR: "#10B981", 
                WAM: "#F59E0B",
                TimeSeries: "#8B5CF6",
                ARIMA: "#EF4444",
                Linear: "#06B6D4",
                Polynomial: "#84CC16",
                Exponential: "#F97316",
                Logarithmic: "#EC4899",
                Neural: "#A855F7",
                Custom: "#6B7280"
            },
            charts: {
                primary: "#2563EB",
                secondary: "#059669",
                tertiary: "#DC2626", 
                quaternary: "#7C3AED",
                quinary: "#EA580C"
            },
            status: {
                success: "#10B981",
                warning: "#F59E0B",
                error: "#EF4444",
                info: "#3B82F6"
            }
        };
        this.initialized = true;
        console.log('🔧 Fallback colors loaded');
    }

    setupEventListeners() {
        // Listen for theme changes
        document.addEventListener('themeChanged', (event) => {
            this.handleThemeChange(event.detail.theme);
        });

        // Listen for scenario changes to load scenario-specific colors
        document.addEventListener('scenarioChanged', (event) => {
            this.loadScenarioColors(event.detail.scenarioName);
        });
    }

    // ========== COLOR RETRIEVAL METHODS ==========

    getColor(category, item, defaultColor = "#6B7280") {
        if (!this.initialized) {
            console.warn('⚠️ Color Manager not initialized, using default');
            return defaultColor;
        }

        try {
            const categoryColors = this.colors[category];
            if (categoryColors && categoryColors[item]) {
                return categoryColors[item];
            }

            // Generate color if not exists and add to colors
            if (categoryColors) {
                const generatedColor = this.generateColorForItem(category, item);
                categoryColors[item] = generatedColor;
                return generatedColor;
            }

            return defaultColor;
        } catch (error) {
            console.error(`❌ Error getting color for ${category}.${item}:`, error);
            return defaultColor;
        }
    }

    getColorPalette(category, items) {
        const palette = {};
        items.forEach(item => {
            palette[item] = this.getColor(category, item);
        });
        return palette;
    }

    getSectorColors(sectors) {
        if (!Array.isArray(sectors)) {
            console.warn('getSectorColors expects an array');
            return {};
        }
        return this.getColorPalette('sectors', sectors);
    }

    getModelColors(models) {
        if (!Array.isArray(models)) {
            console.warn('getModelColors expects an array');
            return {};
        }
        return this.getColorPalette('models', models);
    }

    getChartColors(count, startIndex = 0) {
        const baseColors = [
            this.getColor('charts', 'primary'),
            this.getColor('charts', 'secondary'),
            this.getColor('charts', 'tertiary'),
            this.getColor('charts', 'quaternary'), 
            this.getColor('charts', 'quinary')
        ];

        const colors = [];
        for (let i = 0; i < count; i++) {
            const colorIndex = (startIndex + i) % baseColors.length;
            if (colorIndex < baseColors.length) {
                colors.push(baseColors[colorIndex]);
            } else {
                // Generate additional colors
                colors.push(this.generateColorForItem('chart', `generated_${i}`));
            }
        }

        return colors;
    }

    getStatusColor(status) {
        return this.getColor('status', status);
    }

    getThemeColor(colorKey) {
        return this.getColor('themes', `${this.currentTheme}_${colorKey}`);
    }

    // ========== COLOR GENERATION ==========

    generateColorForItem(category, item) {
        // color generation with better distribution
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

        return this.hslToHex(hue, saturation, lightness);
    }

    hslToHex(h, s, l) {
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

    // ========== COLOR MODIFICATION ==========

    async updateColor(category, item, color) {
        if (this.isUpdating) {
            console.warn('Color update already in progress');
            return false;
        }

        this.isUpdating = true;

        try {
            // Validate color format
            if (!this.isValidHexColor(color)) {
                throw new Error('Invalid color format');
            }

            // Update locally first
            if (!this.colors[category]) {
                this.colors[category] = {};
            }
            
            const oldColor = this.colors[category][item];
            this.colors[category][item] = color;

            // Try to save to backend
            try {
                await this.saveColorToBackend(category, item, color);
                console.log(`✅ Color updated: ${category}.${item} = ${color}`);
            } catch (error) {
                console.warn('⚠️ Backend save failed, keeping local change:', error);
            }

            // Notify all callbacks
            this.notifyColorChange(category, item, color, oldColor);

            return true;
        } catch (error) {
            console.error('❌ Color update failed:', error);
            return false;
        } finally {
            this.isUpdating = false;
        }
    }

    async updateMultipleColors(category, colorDict) {
        const updates = [];
        
        for (const [item, color] of Object.entries(colorDict)) {
            updates.push(this.updateColor(category, item, color));
        }

        const results = await Promise.all(updates);
        return results.every(result => result === true);
    }

    async saveColorToBackend(category, item, color) {
        const response = await fetch(`${this.apiBase}/set`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, item, color })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Backend reported failure');
        }
    }

    isValidHexColor(color) {
        return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color);
    }

    // ========== SCENARIO-SPECIFIC COLORS ==========

    async loadScenarioColors(scenarioName) {
        if (!scenarioName) return;

        try {
            const response = await fetch(`${this.apiBase}/scenario/${scenarioName}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    // Merge scenario-specific colors
                    if (result.data.sectors) {
                        this.colors.sectors = { ...this.colors.sectors, ...result.data.sectors };
                    }
                    if (result.data.models) {
                        this.colors.models = { ...this.colors.models, ...result.data.models };
                    }
                    
                    console.log(`🎨 Loaded colors for scenario: ${scenarioName}`);
                    this.notifyColorsReloaded(scenarioName);
                }
            }
        } catch (error) {
            console.warn(`Failed to load scenario colors for ${scenarioName}:`, error);
        }
    }

    // ========== THEME MANAGEMENT ==========

    async setTheme(themeName) {
        if (!this.availableThemes.includes(themeName)) {
            console.error(`Theme '${themeName}' not available`);
            return false;
        }

        try {
            const response = await fetch('/chart_management/themes/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: themeName })
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.currentTheme = themeName;
                    await this.loadColors(); // Reload colors for new theme
                    this.notifyThemeChange(themeName);
                    return true;
                }
            }
            return false;
        } catch (error) {
            console.error('Theme change failed:', error);
            return false;
        }
    }

    getCurrentTheme() {
        return this.currentTheme;
    }

    getAvailableThemes() {
        return [...this.availableThemes];
    }

    // ========== COLOR UTILITIES ==========

    addTransparency(hexColor, alpha) {
        try {
            const hex = hexColor.replace('#', '');
            const r = parseInt(hex.substr(0, 2), 16);
            const g = parseInt(hex.substr(2, 2), 16);
            const b = parseInt(hex.substr(4, 2), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        } catch (error) {
            console.warn('Failed to add transparency:', error);
            return `rgba(99, 102, 241, ${alpha})`;
        }
    }

    darkenColor(hexColor, factor) {
        try {
            const hex = hexColor.replace('#', '');
            let r = parseInt(hex.substr(0, 2), 16);
            let g = parseInt(hex.substr(2, 2), 16);
            let b = parseInt(hex.substr(4, 2), 16);

            r = Math.max(0, Math.floor(r * (1 - factor)));
            g = Math.max(0, Math.floor(g * (1 - factor)));
            b = Math.max(0, Math.floor(b * (1 - factor)));

            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        } catch (error) {
            console.warn('Failed to darken color:', error);
            return '#1D4ED8';
        }
    }

    lightenColor(hexColor, factor) {
        try {
            const hex = hexColor.replace('#', '');
            let r = parseInt(hex.substr(0, 2), 16);
            let g = parseInt(hex.substr(2, 2), 16);
            let b = parseInt(hex.substr(4, 2), 16);

            r = Math.min(255, Math.floor(r + (255 - r) * factor));
            g = Math.min(255, Math.floor(g + (255 - g) * factor));
            b = Math.min(255, Math.floor(b + (255 - b) * factor));

            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        } catch (error) {
            console.warn('Failed to lighten color:', error);
            return '#93C5FD';
        }
    }

    getContrastColor(hexColor) {
        try {
            const hex = hexColor.replace('#', '');
            const r = parseInt(hex.substr(0, 2), 16);
            const g = parseInt(hex.substr(2, 2), 16);
            const b = parseInt(hex.substr(4, 2), 16);

            // Calculate relative luminance
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            
            return luminance > 0.5 ? '#000000' : '#FFFFFF';
        } catch (error) {
            return '#000000';
        }
    }

    // ========== CHART.JS INTEGRATION ==========

    createChartDataset(label, data, options = {}) {
        const {
            category = 'charts',
            item = 'primary',
            chartType = 'line',
            fill = false,
            tension = 0.2,
            pointRadius = 4,
            borderWidth = 2
        } = options;

        const color = this.getColor(category, item);

        const dataset = {
            label: label,
            data: data,
            borderColor: color,
            backgroundColor: fill ? this.addTransparency(color, 0.3) : this.addTransparency(color, 0.1),
            fill: fill,
            tension: tension,
            borderWidth: borderWidth,
            pointRadius: pointRadius,
            pointHoverRadius: pointRadius + 2,
            pointBackgroundColor: '#FFFFFF',
            pointBorderColor: color,
            pointBorderWidth: 2
        };

        // Chart type specific styling
        if (chartType === 'bar') {
            dataset.backgroundColor = this.addTransparency(color, 0.8);
            dataset.borderRadius = 4;
            dataset.borderSkipped = false;
            // Remove point styling for bars
            delete dataset.pointRadius;
            delete dataset.pointHoverRadius;
            delete dataset.pointBackgroundColor;
            delete dataset.pointBorderColor;
            delete dataset.pointBorderWidth;
        } else if (chartType === 'area') {
            dataset.fill = true;
            dataset.backgroundColor = this.addTransparency(color, 0.3);
        }

        return dataset;
    }

    enhanceChartConfig(chartConfig, colorMapping = {}) {
        if (!chartConfig.data?.datasets) return chartConfig;

        chartConfig.data.datasets.forEach((dataset, index) => {
            const label = dataset.label || '';
            
            // Try to get appropriate color based on mapping or label
            let color;
            if (colorMapping[label]) {
                color = colorMapping[label];
            } else if (this.colors.sectors && this.colors.sectors[label.toLowerCase()]) {
                color = this.colors.sectors[label.toLowerCase()];
            } else if (this.colors.models && this.colors.models[label]) {
                color = this.colors.models[label];
            } else {
                color = this.getChartColors(1, index)[0];
            }

            // Apply colors
            dataset.borderColor = color;
            
            if (chartConfig.type === 'bar') {
                dataset.backgroundColor = this.addTransparency(color, 0.8);
                dataset.borderColor = this.darkenColor(color, 0.1);
            } else if (chartConfig.type === 'line' || chartConfig.type === 'area') {
                dataset.backgroundColor = this.addTransparency(color, 
                    chartConfig.type === 'area' ? 0.3 : 0.1);
                dataset.pointBackgroundColor = '#FFFFFF';
                dataset.pointBorderColor = color;
            }
        });

        return chartConfig;
    }

    // ========== EVENT MANAGEMENT ==========

    registerColorChangeCallback(callback) {
        if (typeof callback === 'function') {
            this.changeCallbacks.add(callback);
        }
    }

    unregisterColorChangeCallback(callback) {
        this.changeCallbacks.delete(callback);
    }

    notifyColorChange(category, item, newColor, oldColor) {
        const changeEvent = {
            category,
            item,
            newColor,
            oldColor,
            timestamp: Date.now()
        };

        this.changeCallbacks.forEach(callback => {
            try {
                callback(changeEvent);
            } catch (error) {
                console.error('Color change callback error:', error);
            }
        });

        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('colorChanged', {
            detail: changeEvent
        }));
    }

    notifyColorsReloaded(scenarioName) {
        document.dispatchEvent(new CustomEvent('colorsReloaded', {
            detail: { scenarioName, timestamp: Date.now() }
        }));
    }

    notifyThemeChange(themeName) {
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, timestamp: Date.now() }
        }));
    }

    // ========== PERSISTENCE AND RESET ==========

    async resetToDefaults(category = null) {
        try {
            const response = await fetch(`${this.apiBase}/reset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category })
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    await this.loadColors(); // Reload colors
                    console.log(`✅ Colors reset: ${category || 'all'}`);
                    
                    // Notify about reset
                    document.dispatchEvent(new CustomEvent('colorsReset', {
                        detail: { category, timestamp: Date.now() }
                    }));
                    
                    return true;
                }
            }
            return false;
        } catch (error) {
            console.error('Reset failed:', error);
            return false;
        }
    }

    async saveAllColors() {
        try {
            const response = await fetch(`${this.apiBase}/save-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.colors)
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    console.log('✅ All colors saved successfully');
                    return true;
                }
            }
            return false;
        } catch (error) {
            console.error('Save all colors failed:', error);
            return false;
        }
    }

    // ========== UTILITY METHODS ==========

    getAllColors() {
        return JSON.parse(JSON.stringify(this.colors));
    }

    getCategoryColors(category) {
        return { ...(this.colors[category] || {}) };
    }

    async waitForInitialization() {
        if (this.initialized) return;

        let attempts = 0;
        const maxAttempts = 100;

        while (!this.initialized && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (!this.initialized) {
            console.warn('⚠️ Color Manager initialization timeout');
            this.loadFallbackColors();
        }
    }

    getColorInfo() {
        return {
            initialized: this.initialized,
            currentTheme: this.currentTheme,
            availableThemes: this.availableThemes,
            totalColors: Object.keys(this.colors).reduce((sum, category) => {
                return sum + Object.keys(this.colors[category] || {}).length;
            }, 0),
            categories: Object.keys(this.colors)
        };
    }
}

// ========== GLOBAL INITIALIZATION ==========

// Create global instance
window.ColorManager = ColorManager;
window.colorManager = new ColorManager();

// Global utility functions for backward compatibility
window.getColor = (category, item, defaultColor) => {
    return window.colorManager.getColor(category, item, defaultColor);
};

window.getSectorColors = (sectors) => {
    return window.colorManager.getSectorColors(sectors);
};

window.getModelColors = (models) => {
    return window.colorManager.getModelColors(models);
};

window.getChartColors = (count, startIndex = 0) => {
    return window.colorManager.getChartColors(count, startIndex);
};

window.updateColor = async (category, item, color) => {
    return window.colorManager.updateColor(category, item, color);
};

// global functions
window.enhanceChartConfig = (chartConfig, colorMapping) => {
    return window.colorManager.enhanceChartConfig(chartConfig, colorMapping);
};

window.createChartDataset = (label, data, options) => {
    return window.colorManager.createChartDataset(label, data, options);
};

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ColorManager;
}

console.log('🎨 Color Manager loaded successfully');