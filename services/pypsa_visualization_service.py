#!/usr/bin/env python3
"""
PyPSA Visualization Service
Migrates PyPSA results visualization to use centralized plot_utils
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
import logging
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from plot_utils import PlotUtils
from color_manager import ColorManager

logger = logging.getLogger(__name__)

class PyPSAVisualizationService:
    """
    Service for creating PyPSA visualizations using centralized plot_utils
    Replaces direct Plotly calls with standardized chart generation
    """
    
    def __init__(self):
        self.plot_utils = PlotUtils()
        self.color_manager = ColorManager()
        
    def create_daily_profile_chart(self, data: pd.DataFrame, 
                                 component_name: str = "Load",
                                 title: str = None) -> Dict:
        """
        Create daily profile chart data for PyPSA results
        Replaces createDailyProfilePlot from pypsa_results.js
        """
        if title is None:
            title = f"Daily Profile - {component_name}"
            
        # Handle empty data
        if data.empty:
            return {
                'type': 'line',
                'data': {
                    'labels': [],
                    'datasets': [{
                        'label': 'No Data Available',
                        'data': [],
                        'borderColor': self.color_manager.get_color('status', 'info'),
                        'backgroundColor': 'transparent'
                    }]
                },
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': title
                        }
                    }
                }
            }
        
        # Prepare data for time series chart
        if isinstance(data.index, pd.DatetimeIndex):
            x_column = 'timestamp'
            data = data.reset_index()
            data['timestamp'] = data['timestamp'].dt.strftime('%H:%M')
        else:
            x_column = data.columns[0]
            
        y_columns = [col for col in data.columns if col != x_column]
        
        return self.plot_utils.create_time_series_chart_data(
            data, x_column, y_columns, 
            chart_type='line', title=title
        )
    
    def create_load_duration_curve(self, data: Union[List, pd.Series],
                                 component_name: str = "Load",
                                 title: str = None) -> Dict:
        """
        Create load duration curve chart data
        Replaces createLoadDurationCurve from pypsa_results.js
        """
        if title is None:
            title = f"Load Duration Curve - {component_name}"
            
        # Convert to list if pandas Series
        if isinstance(data, pd.Series):
            data = data.tolist()
            
        # Sort data in descending order for duration curve
        sorted_data = sorted(data, reverse=True)
        
        # Create duration percentages
        duration_hours = list(range(len(sorted_data)))
        duration_percent = [h / len(sorted_data) * 100 for h in duration_hours]
        
        # Create DataFrame for area chart
        df = pd.DataFrame({
            'duration_percent': duration_percent,
            component_name: sorted_data
        })
        
        return self.plot_utils.create_area_chart_data(
            df, 'duration_percent', component_name,
            title=title, fill_mode='tozeroy'
        )
    
    def create_generation_mix_chart(self, data: pd.DataFrame,
                                  title: str = "Generation Mix") -> Dict:
        """
        Create generation mix stacked area chart
        """
        # Ensure data has time index
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
            else:
                data.index = pd.date_range(start='2024-01-01', periods=len(data), freq='H')
        
        # Reset index to use as x-axis
        data_reset = data.reset_index()
        time_col = data_reset.columns[0]
        
        # Format time for display
        if pd.api.types.is_datetime64_any_dtype(data_reset[time_col]):
            data_reset[time_col] = data_reset[time_col].dt.strftime('%Y-%m-%d %H:%M')
        
        # Get generation columns
        gen_columns = [col for col in data_reset.columns if col != time_col]
        
        return self.plot_utils.create_area_chart_data(
            data_reset, time_col, gen_columns,
            title=title, fill_mode='tonexty'
        )
    
    def create_capacity_chart(self, data: Dict[str, float],
                            title: str = "Installed Capacity") -> Dict:
        """
        Create capacity comparison chart
        """
        # Convert to DataFrame
        df = pd.DataFrame({
            'technology': list(data.keys()),
            'capacity': list(data.values())
        })
        
        return self.plot_utils.create_sector_comparison_chart_data(
            df, 'technology', 'capacity', title=title
        )
    
    def create_energy_balance_chart(self, data: pd.DataFrame,
                                  title: str = "Energy Balance") -> Dict:
        """
        Create energy balance chart with positive/negative values
        """
        # Separate positive and negative values
        positive_cols = []
        negative_cols = []
        
        for col in data.columns:
            if col not in ['timestamp', 'time', 'hour']:
                if data[col].sum() >= 0:
                    positive_cols.append(col)
                else:
                    negative_cols.append(col)
        
        # Create time column
        time_col = 'timestamp'
        if time_col not in data.columns:
            time_col = data.columns[0] if data.columns[0] in ['time', 'hour'] else 'time'
            if time_col not in data.columns:
                data[time_col] = range(len(data))
        
        all_cols = positive_cols + negative_cols
        
        return self.plot_utils.create_time_series_chart_data(
            data, time_col, all_cols,
            chart_type='bar', title=title
        )
    
    def create_network_flow_chart(self, data: pd.DataFrame,
                                title: str = "Network Flows") -> Dict:
        """
        Create network flow visualization
        """
        # For network flows, use multi-axis chart if we have different units
        time_col = data.columns[0] if pd.api.types.is_datetime64_any_dtype(data.iloc[:, 0]) else 'time'
        
        if time_col not in data.columns:
            data[time_col] = pd.date_range(start='2024-01-01', periods=len(data), freq='H')
        
        flow_cols = [col for col in data.columns if col != time_col]
        
        # Split into left and right axis based on magnitude
        left_cols = []
        right_cols = []
        
        for col in flow_cols:
            if abs(data[col].max()) > 1000:  # Large values go to right axis
                right_cols.append(col)
            else:
                left_cols.append(col)
        
        if not right_cols:  # If no large values, use regular time series
            return self.plot_utils.create_time_series_chart_data(
                data, time_col, flow_cols, title=title
            )
        
        return self.plot_utils.create_multi_axis_chart_data(
            data, time_col, left_cols, right_cols, title=title
        )
    
    def create_cost_breakdown_chart(self, data: Dict[str, float],
                                  title: str = "Cost Breakdown") -> Dict:
        """
        Create cost breakdown pie chart
        """
        return self.plot_utils.create_pie_chart_data(
            data, title=title
        )
    
    def create_emissions_chart(self, data: pd.DataFrame,
                             title: str = "Emissions Over Time") -> Dict:
        """
        Create emissions time series chart
        """
        time_col = 'timestamp'
        if time_col not in data.columns:
            time_col = data.columns[0]
        
        emission_cols = [col for col in data.columns if col != time_col]
        
        return self.plot_utils.create_time_series_chart_data(
            data, time_col, emission_cols,
            chart_type='line', title=title
        )
    
    def create_storage_chart(self, data: pd.DataFrame,
                           title: str = "Storage Levels") -> Dict:
        """
        Create storage level chart with area fill
        """
        time_col = 'timestamp'
        if time_col not in data.columns:
            time_col = data.columns[0]
        
        storage_cols = [col for col in data.columns if col != time_col]
        
        return self.plot_utils.create_area_chart_data(
            data, time_col, storage_cols,
            title=title, fill_mode='tonexty'
        )
    
    def create_comparison_chart(self, scenarios: Dict[str, pd.DataFrame],
                              metric: str = "total_cost",
                              title: str = "Scenario Comparison") -> Dict:
        """
        Create scenario comparison chart
        """
        # Extract metric values for each scenario
        comparison_data = {}
        for scenario_name, scenario_data in scenarios.items():
            if metric in scenario_data.columns:
                comparison_data[scenario_name] = scenario_data[metric].sum()
            else:
                comparison_data[scenario_name] = scenario_data.sum().sum()
        
        return self.plot_utils.create_sector_comparison_chart_data(
            pd.DataFrame({
                'scenario': list(comparison_data.keys()),
                'value': list(comparison_data.values())
            }),
            'scenario', 'value', title=title
        )
    
    def export_chart_data(self, chart_data: Dict, 
                         format_type: str = "json",
                         filename: str = None) -> Dict:
        """
        Export chart data in specified format
        """
        return self.plot_utils.export_chart_data(chart_data, format_type, filename)

# Global instance
pypsa_viz_service = PyPSAVisualizationService()

# Utility functions for direct use
def create_daily_profile_chart(data: pd.DataFrame, 
                             component_name: str = "Load",
                             title: str = None) -> Dict:
    """Direct function to create daily profile chart"""
    return pypsa_viz_service.create_daily_profile_chart(data, component_name, title)

def create_load_duration_curve(data: Union[List, pd.Series],
                             component_name: str = "Load",
                             title: str = None) -> Dict:
    """Direct function to create load duration curve"""
    return pypsa_viz_service.create_load_duration_curve(data, component_name, title)

def create_generation_mix_chart(data: pd.DataFrame,
                              title: str = "Generation Mix") -> Dict:
    """Direct function to create generation mix chart"""
    return pypsa_viz_service.create_generation_mix_chart(data, title)

def create_capacity_chart(data: Dict[str, float],
                        title: str = "Installed Capacity") -> Dict:
    """Direct function to create capacity chart"""
    return pypsa_viz_service.create_capacity_chart(data, title)

def create_energy_balance_chart(data: pd.DataFrame,
                              title: str = "Energy Balance") -> Dict:
    """Direct function to create energy balance chart"""
    return pypsa_viz_service.create_energy_balance_chart(data, title)

def create_network_flow_chart(data: pd.DataFrame,
                            title: str = "Network Flows") -> Dict:
    """Direct function to create network flow chart"""
    return pypsa_viz_service.create_network_flow_chart(data, title)

def create_cost_breakdown_chart(data: Dict[str, float],
                              title: str = "Cost Breakdown") -> Dict:
    """Direct function to create cost breakdown chart"""
    return pypsa_viz_service.create_cost_breakdown_chart(data, title)

def create_emissions_chart(data: pd.DataFrame,
                         title: str = "Emissions Over Time") -> Dict:
    """Direct function to create emissions chart"""
    return pypsa_viz_service.create_emissions_chart(data, title)

def create_storage_chart(data: pd.DataFrame,
                       title: str = "Storage Levels") -> Dict:
    """Direct function to create storage chart"""
    return pypsa_viz_service.create_storage_chart(data, title)

def create_comparison_chart(scenarios: Dict[str, pd.DataFrame],
                          metric: str = "total_cost",
                          title: str = "Scenario Comparison") -> Dict:
    """Direct function to create scenario comparison chart"""
    return pypsa_viz_service.create_comparison_chart(scenarios, metric, title)