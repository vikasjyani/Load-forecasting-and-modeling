#!/usr/bin/env python3
"""
Load Profile Visualization Service
Consolidates load profile visualizations to use centralized plot_utils
Replaces matplotlib/seaborn usage with standardized chart generation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
import logging
from pathlib import Path
import sys
from datetime import datetime, timedelta

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from plot_utils import PlotUtils
from color_manager import ColorManager

logger = logging.getLogger(__name__)

class LoadProfileVisualizationService:
    """
    Service for creating load profile visualizations using centralized plot_utils
    Replaces matplotlib/seaborn usage with standardized chart generation
    """
    
    def __init__(self):
        self.plot_utils = PlotUtils()
        self.color_manager = ColorManager()
        
    def create_load_heatmap(self, data: pd.DataFrame,
                          title: str = "Load Pattern Heatmap",
                          x_label: str = "Hour of Day",
                          y_label: str = "Month") -> Dict:
        """
        Create load pattern heatmap
        Replaces seaborn heatmap usage in load_profile_pdf.py
        """
        # Prepare data for heatmap
        if isinstance(data.index, pd.DatetimeIndex):
            # Extract hour and month from datetime index
            data_copy = data.copy()
            data_copy['hour'] = data_copy.index.hour
            data_copy['month'] = data_copy.index.month
            
            # Pivot to create heatmap matrix
            heatmap_data = data_copy.groupby(['month', 'hour']).mean()
            
            # Get the first numeric column for heatmap
            value_col = None
            for col in data_copy.columns:
                if col not in ['hour', 'month'] and pd.api.types.is_numeric_dtype(data_copy[col]):
                    value_col = col
                    break
            
            if value_col:
                pivot_data = data_copy.pivot_table(
                    values=value_col, 
                    index='month', 
                    columns='hour', 
                    aggfunc='mean'
                )
            else:
                # Use first numeric column
                numeric_cols = data_copy.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    pivot_data = data_copy.pivot_table(
                        values=numeric_cols[0], 
                        index='month', 
                        columns='hour', 
                        aggfunc='mean'
                    )
                else:
                    # Create dummy data
                    pivot_data = pd.DataFrame(
                        np.random.rand(12, 24),
                        index=range(1, 13),
                        columns=range(24)
                    )
        else:
            # Assume data is already in matrix format
            pivot_data = data
        
        # Fill NaN values
        pivot_data = pivot_data.fillna(0)
        
        # Create labels
        x_labels = [f"{h:02d}:00" for h in range(24)]
        y_labels = [f"Month {m}" for m in range(1, 13)]
        
        # Ensure we have the right dimensions
        if pivot_data.shape[1] != 24:
            x_labels = [str(col) for col in pivot_data.columns]
        if pivot_data.shape[0] != 12:
            y_labels = [str(idx) for idx in pivot_data.index]
        
        return self.plot_utils.create_heatmap_chart_data(
            pivot_data.values.tolist(),
            x_labels, y_labels, title
        )
    
    def create_weekly_pattern_chart(self, data: pd.DataFrame,
                                  title: str = "Weekly Load Pattern") -> Dict:
        """
        Create weekly load pattern chart
        """
        if isinstance(data.index, pd.DatetimeIndex):
            data_copy = data.copy()
            data_copy['weekday'] = data_copy.index.day_name()
            data_copy['hour'] = data_copy.index.hour
            
            # Get numeric columns
            numeric_cols = data_copy.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
                # Group by weekday and hour
                weekly_pattern = data_copy.groupby(['weekday', 'hour'])[value_col].mean().reset_index()
                
                # Pivot for better visualization
                pivot_weekly = weekly_pattern.pivot(index='weekday', columns='hour', values=value_col)
                
                # Reorder weekdays
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                pivot_weekly = pivot_weekly.reindex(weekday_order)
                
                x_labels = [f"{h:02d}:00" for h in range(24)]
                y_labels = weekday_order
                
                return self.plot_utils.create_heatmap_chart_data(
                    pivot_weekly.fillna(0).values.tolist(),
                    x_labels, y_labels, title
                )
        
        # Fallback for non-datetime data
        return self.create_load_heatmap(data, title)
    
    def create_seasonal_comparison_chart(self, data: pd.DataFrame,
                                       title: str = "Seasonal Load Comparison") -> Dict:
        """
        Create seasonal load comparison chart
        """
        if isinstance(data.index, pd.DatetimeIndex):
            data_copy = data.copy()
            data_copy['season'] = data_copy.index.month.map({
                12: 'Winter', 1: 'Winter', 2: 'Winter',
                3: 'Spring', 4: 'Spring', 5: 'Spring',
                6: 'Summer', 7: 'Summer', 8: 'Summer',
                9: 'Autumn', 10: 'Autumn', 11: 'Autumn'
            })
            
            # Get numeric columns
            numeric_cols = data_copy.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
                # Create box plot data
                box_data = {}
                for season in ['Spring', 'Summer', 'Autumn', 'Winter']:
                    season_data = data_copy[data_copy['season'] == season][value_col].dropna()
                    box_data[season] = season_data.tolist()
                
                return self.plot_utils.create_box_plot_data(box_data, title)
        
        # Fallback: create time series
        time_col = data.columns[0] if not isinstance(data.index, pd.DatetimeIndex) else 'timestamp'
        if time_col == 'timestamp':
            data = data.reset_index()
            data.columns = ['timestamp'] + list(data.columns[1:])
        
        numeric_cols = [col for col in data.columns if col != time_col and pd.api.types.is_numeric_dtype(data[col])]
        
        return self.plot_utils.create_time_series_chart_data(
            data, time_col, numeric_cols, title=title
        )
    
    def create_load_duration_curve(self, data: pd.Series,
                                 title: str = "Load Duration Curve") -> Dict:
        """
        Create load duration curve
        """
        # Sort data in descending order
        sorted_data = data.sort_values(ascending=False).reset_index(drop=True)
        
        # Create duration percentages
        duration_percent = [(i / len(sorted_data)) * 100 for i in range(len(sorted_data))]
        
        # Create DataFrame
        df = pd.DataFrame({
            'duration_percent': duration_percent,
            'load': sorted_data.values
        })
        
        return self.plot_utils.create_area_chart_data(
            df, 'duration_percent', 'load',
            title=title, fill_mode='tozeroy'
        )
    
    def create_monthly_statistics_chart(self, data: pd.DataFrame,
                                      title: str = "Monthly Load Statistics") -> Dict:
        """
        Create monthly statistics chart (min, max, avg)
        """
        if isinstance(data.index, pd.DatetimeIndex):
            data_copy = data.copy()
            data_copy['month'] = data_copy.index.month
            
            # Get numeric columns
            numeric_cols = data_copy.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col != 'month']
            
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
                # Calculate monthly statistics
                monthly_stats = data_copy.groupby('month')[value_col].agg([
                    ('min', 'min'),
                    ('max', 'max'),
                    ('avg', 'mean')
                ]).reset_index()
                
                monthly_stats['month_name'] = monthly_stats['month'].map({
                    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                    7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
                })
                
                return self.plot_utils.create_time_series_chart_data(
                    monthly_stats, 'month_name', ['min', 'max', 'avg'],
                    chart_type='line', title=title
                )
        
        # Fallback
        return self.create_load_heatmap(data, title)
    
    def create_hourly_average_chart(self, data: pd.DataFrame,
                                  title: str = "Average Hourly Load Profile") -> Dict:
        """
        Create average hourly load profile
        """
        if isinstance(data.index, pd.DatetimeIndex):
            data_copy = data.copy()
            data_copy['hour'] = data_copy.index.hour
            
            # Get numeric columns
            numeric_cols = data_copy.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col != 'hour']
            
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
                # Calculate hourly averages
                hourly_avg = data_copy.groupby('hour')[value_col].mean().reset_index()
                hourly_avg['hour_label'] = hourly_avg['hour'].apply(lambda x: f"{x:02d}:00")
                
                return self.plot_utils.create_time_series_chart_data(
                    hourly_avg, 'hour_label', [value_col],
                    chart_type='line', title=title
                )
        
        # Fallback
        time_col = data.columns[0]
        numeric_cols = [col for col in data.columns if col != time_col and pd.api.types.is_numeric_dtype(data[col])]
        
        return self.plot_utils.create_time_series_chart_data(
            data, time_col, numeric_cols, title=title
        )
    
    def create_load_histogram(self, data: pd.Series,
                            bins: int = 30,
                            title: str = "Load Distribution") -> Dict:
        """
        Create load distribution histogram
        """
        return self.plot_utils.create_histogram_chart_data(
            data.dropna().tolist(), bins, title,
            x_label="Load (MW)", y_label="Frequency"
        )
    
    def create_correlation_heatmap(self, data: pd.DataFrame,
                                 title: str = "Load Correlation Matrix") -> Dict:
        """
        Create correlation heatmap for multiple load profiles
        """
        # Calculate correlation matrix
        numeric_data = data.select_dtypes(include=[np.number])
        corr_matrix = numeric_data.corr()
        
        # Create labels
        labels = list(corr_matrix.columns)
        
        return self.plot_utils.create_heatmap_chart_data(
            corr_matrix.values.tolist(),
            labels, labels, title, colorscale="RdBu"
        )
    
    def create_peak_analysis_chart(self, data: pd.DataFrame,
                                 percentile: float = 95,
                                 title: str = "Peak Load Analysis") -> Dict:
        """
        Create peak load analysis chart
        """
        if isinstance(data.index, pd.DatetimeIndex):
            # Get numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
                # Calculate percentile threshold
                threshold = data[value_col].quantile(percentile / 100)
                
                # Create time series with peak highlighting
                data_copy = data.reset_index()
                data_copy['timestamp'] = data_copy['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
                data_copy['is_peak'] = data_copy[value_col] >= threshold
                data_copy['peak_load'] = data_copy[value_col].where(data_copy['is_peak'])
                
                return self.plot_utils.create_time_series_chart_data(
                    data_copy, 'timestamp', [value_col, 'peak_load'],
                    title=f"{title} ({percentile}th Percentile)"
                )
        
        # Fallback
        return self.create_load_heatmap(data, title)
    
    def export_chart_data(self, chart_data: Dict, 
                         format_type: str = "json",
                         filename: str = None) -> Dict:
        """
        Export chart data in specified format
        """
        return self.plot_utils.export_chart_data(chart_data, format_type, filename)

# Global instance
loadprofile_viz_service = LoadProfileVisualizationService()

# Utility functions for direct use
def create_load_heatmap(data: pd.DataFrame,
                      title: str = "Load Pattern Heatmap",
                      x_label: str = "Hour of Day",
                      y_label: str = "Month") -> Dict:
    """Direct function to create load heatmap"""
    return loadprofile_viz_service.create_load_heatmap(data, title, x_label, y_label)

def create_weekly_pattern_chart(data: pd.DataFrame,
                              title: str = "Weekly Load Pattern") -> Dict:
    """Direct function to create weekly pattern chart"""
    return loadprofile_viz_service.create_weekly_pattern_chart(data, title)

def create_seasonal_comparison_chart(data: pd.DataFrame,
                                   title: str = "Seasonal Load Comparison") -> Dict:
    """Direct function to create seasonal comparison chart"""
    return loadprofile_viz_service.create_seasonal_comparison_chart(data, title)

def create_load_duration_curve(data: pd.Series,
                             title: str = "Load Duration Curve") -> Dict:
    """Direct function to create load duration curve"""
    return loadprofile_viz_service.create_load_duration_curve(data, title)

def create_monthly_statistics_chart(data: pd.DataFrame,
                                  title: str = "Monthly Load Statistics") -> Dict:
    """Direct function to create monthly statistics chart"""
    return loadprofile_viz_service.create_monthly_statistics_chart(data, title)

def create_hourly_average_chart(data: pd.DataFrame,
                              title: str = "Average Hourly Load Profile") -> Dict:
    """Direct function to create hourly average chart"""
    return loadprofile_viz_service.create_hourly_average_chart(data, title)

def create_load_histogram(data: pd.Series,
                        bins: int = 30,
                        title: str = "Load Distribution") -> Dict:
    """Direct function to create load histogram"""
    return loadprofile_viz_service.create_load_histogram(data, bins, title)

def create_correlation_heatmap(data: pd.DataFrame,
                             title: str = "Load Correlation Matrix") -> Dict:
    """Direct function to create correlation heatmap"""
    return loadprofile_viz_service.create_correlation_heatmap(data, title)

def create_peak_analysis_chart(data: pd.DataFrame,
                             percentile: float = 95,
                             title: str = "Peak Load Analysis") -> Dict:
    """Direct function to create peak analysis chart"""
    return loadprofile_viz_service.create_peak_analysis_chart(data, percentile, title)