"""
Color Management Utility for Energy Platform
Centralized color management system for consistent theming across the application
"""

import json
import os
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class ColorManager:
    """
    Centralized color management system for the entire application
    Supports sectors, models, carriers, and custom color schemes
    """
    
    def __init__(self, app=None):
        self.app = app
        self.config_file = None
        self.colors = {}
        self.default_colors = self._get_default_colors()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        static_folder = app.static_folder or 'static'
        self.config_file = os.path.join(static_folder, 'config', 'colors.json')
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Load existing colors or create default
        self.load_colors()
        
        # Register template functions
        app.jinja_env.globals['get_color'] = self.get_color
        app.jinja_env.globals['get_color_palette'] = self.get_color_palette
        app.jinja_env.globals['get_all_colors'] = self.get_all_colors
    
    def _get_default_colors(self) -> Dict:
        """Define comprehensive default color schemes"""
        return {
            "sectors": {
                "residential": "#2563EB",      # Blue
                "commercial": "#059669",       # Green
                "industrial": "#DC2626",       # Red
                "transportation": "#7C3AED",   # Purple
                "agriculture": "#16A34A",      # Dark Green
                "public": "#EA580C",           # Orange
                "mining": "#92400E",           # Brown
                "construction": "#0891B2",     # Cyan
                "services": "#BE185D",         # Pink
                "healthcare": "#0D9488",       # Teal
                "education": "#7C2D12",        # Dark Orange
                "hospitality": "#B91C1C",      # Dark Red
                "retail": "#1D4ED8",           # Dark Blue
                "finance": "#6B21A8",          # Dark Purple
                "technology": "#0F766E",       # Dark Teal
                "manufacturing": "#A16207",    # Amber
                "utilities": "#DC2626",        # Red
                "government": "#1F2937",       # Gray
                "military": "#374151",         # Dark Gray
                "other": "#6B7280"             # Medium Gray
            },
            "models": {
                "MLR": "#3B82F6",              # Blue
                "SLR": "#10B981",              # Emerald
                "WAM": "#F59E0B",              # Amber
                "TimeSeries": "#8B5CF6",       # Violet
                "ARIMA": "#EF4444",            # Red
                "Linear": "#06B6D4",           # Cyan
                "Polynomial": "#84CC16",       # Lime
                "Exponential": "#F97316",      # Orange
                "Logarithmic": "#EC4899",      # Pink
                "Power": "#14B8A6",            # Teal
                "Neural": "#A855F7",           # Purple
                "RandomForest": "#22C55E",     # Green
                "SVM": "#F43F5E",              # Rose
                "XGBoost": "#0EA5E9",          # Sky
                "LSTM": "#8B5CF6"              # Violet
            },
            "carriers": {
                "electricity": "#3B82F6",      # Blue
                "natural_gas": "#EF4444",      # Red
                "coal": "#1F2937",             # Gray
                "oil": "#92400E",              # Brown
                "biomass": "#16A34A",          # Green
                "solar": "#F59E0B",            # Amber
                "wind": "#06B6D4",             # Cyan
                "hydro": "#0891B2",            # Light Blue
                "nuclear": "#7C3AED",          # Purple
                "geothermal": "#DC2626",       # Red
                "waste": "#6B7280",            # Gray
                "hydrogen": "#8B5CF6",         # Violet
                "battery": "#10B981",          # Emerald
                "pumped_hydro": "#0D9488",     # Teal
                "compressed_air": "#84CC16",   # Lime
                "thermal": "#F97316",          # Orange
                "district_heating": "#EC4899", # Pink
                "district_cooling": "#14B8A6"  # Teal
            },
            "status": {
                "success": "#10B981",          # Emerald
                "warning": "#F59E0B",          # Amber
                "error": "#EF4444",            # Red
                "info": "#3B82F6",             # Blue
                "pending": "#6B7280",          # Gray
                "active": "#8B5CF6",           # Violet
                "inactive": "#9CA3AF",         # Light Gray
                "completed": "#059669",        # Dark Green
                "failed": "#DC2626",           # Dark Red
                "cancelled": "#F97316"         # Orange
            },
            "charts": {
                "primary": "#2563EB",          # Blue
                "secondary": "#059669",        # Green
                "tertiary": "#DC2626",         # Red
                "quaternary": "#7C3AED",       # Purple
                "quinary": "#EA580C",          # Orange
                "background": "#F8FAFC",       # Light Gray
                "grid": "#E2E8F0",             # Light Blue Gray
                "text": "#1E293B",             # Dark Gray
                "axis": "#64748B",             # Medium Gray
                "hover": "#F1F5F9"             # Very Light Gray
            },
            "gradients": {
                "primary": ["#3B82F6", "#1D4ED8"],     # Blue gradient
                "secondary": ["#10B981", "#059669"],    # Green gradient
                "tertiary": ["#EF4444", "#DC2626"],     # Red gradient
                "quaternary": ["#8B5CF6", "#7C3AED"],   # Purple gradient
                "success": ["#10B981", "#059669"],      # Green gradient
                "warning": ["#F59E0B", "#D97706"],      # Amber gradient
                "error": ["#EF4444", "#DC2626"],        # Red gradient
                "info": ["#3B82F6", "#2563EB"]          # Blue gradient
            },
            "themes": {
                "light": {
                    "background": "#FFFFFF",
                    "surface": "#F8FAFC",
                    "primary": "#2563EB",
                    "secondary": "#64748B",
                    "text": "#1E293B",
                    "border": "#E2E8F0"
                },
                "dark": {
                    "background": "#0F172A",
                    "surface": "#1E293B",
                    "primary": "#3B82F6",
                    "secondary": "#94A3B8",
                    "text": "#F1F5F9",
                    "border": "#334155"
                }
            }
        }
    
    def load_colors(self):
        """Load colors from JSON file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_colors = json.load(f)
                # Merge with defaults to ensure all categories exist
                self.colors = self._merge_colors(self.default_colors, saved_colors)
                logger.info(f"Colors loaded from {self.config_file}")
            else:
                self.colors = self.default_colors.copy()
                self.save_colors()
                logger.info("Default colors created and saved")
        except Exception as e:
            logger.error(f"Error loading colors: {e}")
            self.colors = self.default_colors.copy()
    
    def save_colors(self):
        """Save current colors to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.colors, f, indent=2)
            logger.info(f"Colors saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving colors: {e}")
            return False
    
    def _merge_colors(self, defaults: Dict, saved: Dict) -> Dict:
        """Merge saved colors with defaults to ensure completeness"""
        merged = defaults.copy()
        for category, colors in saved.items():
            if category in merged and isinstance(colors, dict):
                merged[category].update(colors)
            else:
                merged[category] = colors
        return merged
    
    def get_color(self, category: str, item: str, default: str = "#6B7280") -> str:
        """Get color for specific category and item"""
        try:
            return self.colors.get(category, {}).get(item, default)
        except Exception:
            return default
    
    def get_color_palette(self, category: str, items: List[str]) -> Dict[str, str]:
        """Get color palette for multiple items in a category"""
        palette = {}
        category_colors = self.colors.get(category, {})
        
        for item in items:
            if item in category_colors:
                palette[item] = category_colors[item]
            else:
                # Generate color if not exists
                palette[item] = self._generate_color_for_item(category, item)
                # Save the generated color
                if category not in self.colors:
                    self.colors[category] = {}
                self.colors[category][item] = palette[item]
        
        return palette
    
    def _generate_color_for_item(self, category: str, item: str) -> str:
        """Generate a consistent color for an item based on its name"""
        # Use hash of item name to generate consistent color
        import hashlib
        hash_object = hashlib.md5(f"{category}_{item}".encode())
        hex_dig = hash_object.hexdigest()
        
        # Convert to RGB values
        r = int(hex_dig[:2], 16)
        g = int(hex_dig[2:4], 16)
        b = int(hex_dig[4:6], 16)
        
        # Ensure good contrast and visibility
        # Adjust brightness to avoid too dark or too light colors
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        if brightness < 100:  # Too dark
            r, g, b = min(255, r + 100), min(255, g + 100), min(255, b + 100)
        elif brightness > 200:  # Too light
            r, g, b = max(0, r - 100), max(0, g - 100), max(0, b - 100)
        
        return f"#{r:02X}{g:02X}{b:02X}"
    
    def set_color(self, category: str, item: str, color: str) -> bool:
        """Set color for specific category and item"""
        try:
            if category not in self.colors:
                self.colors[category] = {}
            self.colors[category][item] = color
            return self.save_colors()
        except Exception as e:
            logger.error(f"Error setting color: {e}")
            return False
    
    def set_colors(self, category: str, color_dict: Dict[str, str]) -> bool:
        """Set multiple colors for a category"""
        try:
            if category not in self.colors:
                self.colors[category] = {}
            self.colors[category].update(color_dict)
            return self.save_colors()
        except Exception as e:
            logger.error(f"Error setting colors: {e}")
            return False
    
    def get_all_colors(self) -> Dict:
        """Get all colors"""
        return self.colors.copy()
    
    def get_category_colors(self, category: str) -> Dict[str, str]:
        """Get all colors for a specific category"""
        return self.colors.get(category, {}).copy()
    
    def reset_to_defaults(self, category: Optional[str] = None) -> bool:
        """Reset colors to defaults"""
        try:
            if category:
                if category in self.default_colors:
                    self.colors[category] = self.default_colors[category].copy()
            else:
                self.colors = self.default_colors.copy()
            return self.save_colors()
        except Exception as e:
            logger.error(f"Error resetting colors: {e}")
            return False
    
    def get_chart_colors(self, count: int, category: str = "charts") -> List[str]:
        """Get a list of colors for charts"""
        base_colors = [
            self.get_color(category, "primary"),
            self.get_color(category, "secondary"), 
            self.get_color(category, "tertiary"),
            self.get_color(category, "quaternary"),
            self.get_color(category, "quinary")
        ]
        
        # If we need more colors, generate them
        if count > len(base_colors):
            additional_colors = []
            for i in range(len(base_colors), count):
                color = self._generate_color_for_item("chart", f"color_{i}")
                additional_colors.append(color)
            base_colors.extend(additional_colors)
        
        return base_colors[:count]
    
    def get_sector_colors(self, sectors: List[str]) -> Dict[str, str]:
        """Get colors specifically for sectors"""
        return self.get_color_palette("sectors", sectors)
    
    def get_model_colors(self, models: List[str]) -> Dict[str, str]:
        """Get colors specifically for models"""
        return self.get_color_palette("models", models)
    
    def get_carrier_colors(self, carriers: List[str]) -> Dict[str, str]:
        """Get colors specifically for carriers"""
        return self.get_color_palette("carriers", carriers)
    
    def export_colors_for_js(self) -> str:
        """Export colors as JavaScript object"""
        try:
            return f"window.AppColors = {json.dumps(self.colors, indent=2)};"
        except Exception as e:
            logger.error(f"Error exporting colors for JS: {e}")
            return "window.AppColors = {};"
    
    def get_gradient(self, gradient_name: str) -> List[str]:
        """Get gradient colors"""
        return self.colors.get("gradients", {}).get(gradient_name, ["#3B82F6", "#1D4ED8"])
    
    def get_theme_colors(self, theme: str = "light") -> Dict[str, str]:
        """Get theme colors"""
        return self.colors.get("themes", {}).get(theme, self.colors["themes"]["light"])

# Global instance
color_manager = ColorManager()

def init_color_manager(app):
    """Initialize color manager with Flask app"""
    color_manager.init_app(app)
    return color_manager

# Utility functions for direct use
def get_color(category: str, item: str, default: str = "#6B7280") -> str:
    """Direct function to get color"""
    return color_manager.get_color(category, item, default)

def get_sector_colors(sectors: List[str]) -> Dict[str, str]:
    """Direct function to get sector colors"""
    return color_manager.get_sector_colors(sectors)

def get_model_colors(models: List[str]) -> Dict[str, str]:
    """Direct function to get model colors"""
    return color_manager.get_model_colors(models)

def get_chart_colors(count: int) -> List[str]:
    """Direct function to get chart colors"""
    return color_manager.get_chart_colors(count)