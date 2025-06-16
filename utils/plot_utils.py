"""
Plotting Utilities for Energy Platform
Reusable plotting functions with consistent styling and color management
"""

import json
import logging
from typing import Dict, List, Optional, Union, Any
import pandas as pd
from utils.color_manager import color_manager

logger = logging.getLogger(__name__)

class PlotUtils:
    """
    Centralized plotting utilities for consistent chart creation across the application
    """
    
    def __init__(self):
        self.default_config = self._get_default_chart_config()
    
    def _get_default_chart_config(self) -> Dict:
        """Get default chart configuration"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "position": "bottom",
                    "labels": {
                        "usePointStyle": True,
                        "padding": 15,
                        "font": {
                            "size": 12,
                            "family": "'Inter', sans-serif"
                        }
                    }
                },
                "tooltip": {
                    "backgroundColor": "rgba(0, 0, 0, 0.8)",
                    "titleColor": "#ffffff",
                    "bodyColor": "#ffffff",
                    "borderColor": "#374151",
                    "borderWidth": 1,
                    "cornerRadius": 8,
                    "displayColors": True,
                    "font": {
                        "size": 12,
                        "family": "'Inter', sans-serif"
                    }
                }
            },
            "scales": {
                "x": {
                    "grid": {
                        "color": "#E5E7EB",
                        "drawBorder": False
                    },
                    "ticks": {
                        "color": "#6B7280",
                        "font": {
                            "size": 11,
                            "family": "'Inter', sans-serif"
                        }
                    }
                },
                "y": {
                    "grid": {
                        "color": "#E5E7EB",
                        "drawBorder": False
                    },
                    "ticks": {
                        "color": "#6B7280",
                        "font": {
                            "size": 11,
                            "family": "'Inter', sans-serif"
                        }
                    }
                }
            },
            "elements": {
                "point": {
                    "radius": 4,
                    "hoverRadius": 6,
                    "borderWidth": 2
                },
                "line": {
                    "borderWidth": 2,
                    "tension": 0.1
                }
            }
        }
    
    def create_time_series_chart_data(self, 
                                    df: pd.DataFrame, 
                                    x_column: str, 
                                    y_columns: Union[str, List[str]], 
                                    chart_type: str = "line",
                                    title: str = "",
                                    colors: Optional[Dict[str, str]] = None) -> Dict:
        """
        Create chart data for time series visualization
        
        Args:
            df: DataFrame with data
            x_column: Column name for x-axis (usually time/year)
            y_columns: Column name(s) for y-axis data
            chart_type: Type of chart (line, area, bar)
            title: Chart title
            colors: Custom colors for series
        
        Returns:
            Dictionary with Chart.js compatible data structure
        """
        try:
            if isinstance(y_columns, str):
                y_columns = [y_columns]
            
            # Prepare labels (x-axis values)
            labels = df[x_column].tolist()
            
            # Get colors for datasets
            if not colors:
                colors = color_manager.get_chart_colors(len(y_columns))
                color_dict = {col: colors[i] for i, col in enumerate(y_columns)}
            else:
                color_dict = colors
            
            # Create datasets
            datasets = []
            for i, column in enumerate(y_columns):
                if column not in df.columns:
                    logger.warning(f"Column '{column}' not found in DataFrame")
                    continue
                
                color = color_dict.get(column, color_manager.get_chart_colors(1)[0])
                
                dataset = {
                    "label": column.replace('_', ' ').title(),
                    "data": df[column].fillna(0).tolist(),
                    "borderColor": color,
                    "backgroundColor": self._add_transparency(color, 0.1),
                    "fill": chart_type == "area",
                    "tension": 0.1 if chart_type in ["line", "area"] else 0
                }
                
                # Chart type specific styling
                if chart_type == "area":
                    dataset["backgroundColor"] = self._add_transparency(color, 0.3)
                elif chart_type == "bar":
                    dataset["backgroundColor"] = color
                    dataset["borderWidth"] = 1
                
                datasets.append(dataset)
            
            # Create chart configuration
            config = self._create_chart_config(chart_type, title, labels, datasets)
            
            return {
                "type": chart_type,
                "data": {
                    "labels": labels,
                    "datasets": datasets
                },
                "options": config["options"],
                "title": title,
                "chart_id": f"chart_{hash(str(labels))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating time series chart data: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_sector_comparison_chart_data(self, 
                                          df: pd.DataFrame, 
                                          sectors: List[str], 
                                          year_column: str = "Year",
                                          chart_type: str = "line",
                                          title: str = "Sector Comparison") -> Dict:
        """
        Create chart data for sector comparison
        
        Args:
            df: DataFrame with sector data
            sectors: List of sector names (column names in df)
            year_column: Column name for years
            chart_type: Type of chart
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            # Get sector colors
            sector_colors = color_manager.get_sector_colors(sectors)
            
            return self.create_time_series_chart_data(
                df=df,
                x_column=year_column,
                y_columns=sectors,
                chart_type=chart_type,
                title=title,
                colors=sector_colors
            )
            
        except Exception as e:
            logger.error(f"Error creating sector comparison chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_model_comparison_chart_data(self, 
                                         results_dict: Dict[str, List], 
                                         years: List[int],
                                         models: List[str],
                                         title: str = "Model Comparison") -> Dict:
        """
        Create chart data for model comparison
        
        Args:
            results_dict: Dictionary with model names as keys and results as values
            years: List of years for x-axis
            models: List of model names
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            # Get model colors
            model_colors = color_manager.get_model_colors(models)
            
            datasets = []
            for model in models:
                if model not in results_dict:
                    continue
                
                color = model_colors.get(model, color_manager.get_chart_colors(1)[0])
                
                dataset = {
                    "label": model,
                    "data": results_dict[model],
                    "borderColor": color,
                    "backgroundColor": self._add_transparency(color, 0.1),
                    "borderWidth": 2,
                    "tension": 0.1,
                    "pointRadius": 3,
                    "pointHoverRadius": 5
                }
                
                datasets.append(dataset)
            
            config = self._create_chart_config("line", title, years, datasets)
            
            return {
                "type": "line",
                "data": {
                    "labels": years,
                    "datasets": datasets
                },
                "options": config["options"],
                "title": title,
                "chart_id": f"model_comparison_{hash(str(years))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating model comparison chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_stacked_bar_chart_data(self, 
                                    df: pd.DataFrame, 
                                    x_column: str, 
                                    y_columns: List[str],
                                    title: str = "Stacked Bar Chart",
                                    colors: Optional[Dict[str, str]] = None) -> Dict:
        """
        Create stacked bar chart data
        
        Args:
            df: DataFrame with data
            x_column: Column for x-axis
            y_columns: Columns for stacking
            title: Chart title
            colors: Custom colors
        
        Returns:
            Chart data dictionary
        """
        try:
            labels = df[x_column].tolist()
            
            if not colors:
                colors = color_manager.get_chart_colors(len(y_columns))
                color_dict = {col: colors[i] for i, col in enumerate(y_columns)}
            else:
                color_dict = colors
            
            datasets = []
            for column in y_columns:
                if column not in df.columns:
                    continue
                
                color = color_dict.get(column, color_manager.get_chart_colors(1)[0])
                
                dataset = {
                    "label": column.replace('_', ' ').title(),
                    "data": df[column].fillna(0).tolist(),
                    "backgroundColor": color,
                    "borderColor": self._darken_color(color, 0.2),
                    "borderWidth": 1
                }
                
                datasets.append(dataset)
            
            # Stacked bar configuration
            options = self.default_config.copy()
            options["scales"]["x"]["stacked"] = True
            options["scales"]["y"]["stacked"] = True
            options["scales"]["y"]["beginAtZero"] = True
            
            return {
                "type": "bar",
                "data": {
                    "labels": labels,
                    "datasets": datasets
                },
                "options": options,
                "title": title,
                "chart_id": f"stacked_bar_{hash(str(labels))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating stacked bar chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_pie_chart_data(self, 
                            data: Dict[str, float], 
                            title: str = "Pie Chart",
                            colors: Optional[List[str]] = None) -> Dict:
        """
        Create pie chart data
        
        Args:
            data: Dictionary with labels and values
            title: Chart title
            colors: Custom colors
        
        Returns:
            Chart data dictionary
        """
        try:
            labels = list(data.keys())
            values = list(data.values())
            
            if not colors:
                colors = color_manager.get_chart_colors(len(labels))
            
            dataset = {
                "data": values,
                "backgroundColor": colors[:len(labels)],
                "borderColor": "#FFFFFF",
                "borderWidth": 2
            }
            
            options = {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "position": "right",
                        "labels": {
                            "usePointStyle": True,
                            "padding": 15,
                            "font": {
                                "size": 12,
                                "family": "'Inter', sans-serif"
                            }
                        }
                    },
                    "tooltip": {
                        "callbacks": {
                            "label": "function(context) { return context.label + ': ' + context.parsed.toLocaleString(); }"
                        }
                    }
                }
            }
            
            return {
                "type": "pie",
                "data": {
                    "labels": labels,
                    "datasets": [dataset]
                },
                "options": options,
                "title": title,
                "chart_id": f"pie_{hash(str(labels))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_correlation_heatmap_data(self, 
                                      correlation_matrix: pd.DataFrame,
                                      title: str = "Correlation Matrix") -> Dict:
        """
        Create correlation heatmap data (for use with Chart.js Matrix chart or similar)
        
        Args:
            correlation_matrix: Pandas DataFrame with correlation values
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            # Convert correlation matrix to format suitable for heatmap
            data = []
            variables = correlation_matrix.columns.tolist()
            
            for i, var1 in enumerate(variables):
                for j, var2 in enumerate(variables):
                    correlation = correlation_matrix.loc[var1, var2]
                    
                    # Color based on correlation strength
                    if correlation >= 0.7:
                        color = color_manager.get_color("status", "success")
                    elif correlation >= 0.4:
                        color = color_manager.get_color("charts", "primary")
                    elif correlation >= -0.4:
                        color = color_manager.get_color("status", "warning")
                    else:
                        color = color_manager.get_color("status", "error")
                    
                    data.append({
                        "x": j,
                        "y": i,
                        "v": round(correlation, 3),
                        "variable1": var1,
                        "variable2": var2,
                        "color": color
                    })
            
            return {
                "type": "heatmap",
                "data": data,
                "variables": variables,
                "title": title,
                "chart_id": f"heatmap_{hash(str(variables))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {e}")
            return self._create_error_chart_data(str(e))
    
    def _create_chart_config(self, chart_type: str, title: str, labels: List, datasets: List) -> Dict:
        """Create chart configuration based on type"""
        config = self.default_config.copy()
        
        # Add title if provided
        if title:
            config["plugins"]["title"] = {
                "display": True,
                "text": title,
                "font": {
                    "size": 16,
                    "weight": "bold",
                    "family": "'Inter', sans-serif"
                },
                "padding": 20,
                "color": "#1F2937"
            }
        
        # Chart type specific configurations
        if chart_type in ["area", "line"]:
            config["scales"]["y"]["beginAtZero"] = True
            if chart_type == "area":
                config["elements"]["line"]["fill"] = True
        
        elif chart_type == "bar":
            config["scales"]["y"]["beginAtZero"] = True
            config["plugins"]["legend"]["display"] = len(datasets) > 1
        
        # Add custom formatting for tooltips
        config["plugins"]["tooltip"]["callbacks"] = {
            "label": "function(context) { return context.dataset.label + ': ' + context.parsed.y.toLocaleString(); }"
        }
        
        return {"options": config}
    
    def _add_transparency(self, hex_color: str, alpha: float) -> str:
        """Add transparency to hex color"""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            return f"rgba({r}, {g}, {b}, {alpha})"
        except Exception:
            return f"rgba(59, 130, 246, {alpha})"  # Default blue with transparency
    
    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor"""
        try:
            hex_color = hex_color.lstrip('#')
            
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return "#1D4ED8"  # Default dark blue
    
    def _create_error_chart_data(self, error_message: str) -> Dict:
        """Create error chart data for display"""
        return {
            "type": "error",
            "error": True,
            "message": error_message,
            "data": {},
            "options": {},
            "title": "Chart Error",
            "chart_id": "error_chart"
        }
    
    def get_responsive_chart_config(self, container_width: int = 800) -> Dict:
        """Get responsive chart configuration based on container width"""
        config = self.default_config.copy()
        
        if container_width < 480:  # Mobile
            config["plugins"]["legend"]["position"] = "bottom"
            config["plugins"]["legend"]["labels"]["font"]["size"] = 10
            config["plugins"]["title"]["font"]["size"] = 14
            config["scales"]["x"]["ticks"]["font"]["size"] = 9
            config["scales"]["y"]["ticks"]["font"]["size"] = 9
            config["elements"]["point"]["radius"] = 2
            config["elements"]["point"]["hoverRadius"] = 4
        elif container_width < 768:  # Tablet
            config["plugins"]["legend"]["labels"]["font"]["size"] = 11
            config["plugins"]["title"]["font"]["size"] = 15
            config["scales"]["x"]["ticks"]["font"]["size"] = 10
            config["scales"]["y"]["ticks"]["font"]["size"] = 10
            config["elements"]["point"]["radius"] = 3
            config["elements"]["point"]["hoverRadius"] = 5
        
        return config

# Global instance
plot_utils = PlotUtils()

# Direct utility functions
def create_time_series_chart(df: pd.DataFrame, 
                           x_column: str, 
                           y_columns: Union[str, List[str]], 
                           chart_type: str = "line",
                           title: str = "",
                           colors: Optional[Dict[str, str]] = None) -> Dict:
    """Direct function to create time series chart"""
    return plot_utils.create_time_series_chart_data(df, x_column, y_columns, chart_type, title, colors)

def create_sector_comparison_chart(df: pd.DataFrame, 
                                 sectors: List[str], 
                                 year_column: str = "Year",
                                 chart_type: str = "line",
                                 title: str = "Sector Comparison") -> Dict:
    """Direct function to create sector comparison chart"""
    return plot_utils.create_sector_comparison_chart_data(df, sectors, year_column, chart_type, title)

def create_model_comparison_chart(results_dict: Dict[str, List], 
                                years: List[int],
                                models: List[str],
                                title: str = "Model Comparison") -> Dict:
    """Direct function to create model comparison chart"""
    return plot_utils.create_model_comparison_chart_data(results_dict, years, models, title)