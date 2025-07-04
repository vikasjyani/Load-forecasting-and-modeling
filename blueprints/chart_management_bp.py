#!/usr/bin/env python3
"""
Chart Management Blueprint
API endpoints for chart creation, export, and theme management
"""

from flask import Blueprint, request, jsonify, send_file
import pandas as pd
import json
import io
import base64
from typing import Dict, List, Optional
import logging
from pathlib import Path
import sys
import tempfile
import os

# Add services to path
sys.path.append(str(Path(__file__).parent.parent / 'services'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

from pypsa_visualization_service import pypsa_viz_service
from loadprofile_visualization_service import loadprofile_viz_service
from chart_export_service import chart_export_service
from color_manager import color_manager
from plot_utils import plot_utils

logger = logging.getLogger(__name__)

# Create blueprint
chart_management_bp = Blueprint('chart_management', __name__, url_prefix='/api/charts')

# PyPSA Chart Endpoints
@chart_management_bp.route('/pypsa/daily-profile', methods=['POST'])
def create_pypsa_daily_profile():
    """
    Create PyPSA daily profile chart
    """
    try:
        data = request.get_json()
        
        # Convert data to DataFrame
        if 'data' in data:
            df = pd.DataFrame(data['data'])
        else:
            return jsonify({'error': 'No data provided'}), 400
        
        component_name = data.get('component_name', 'Load')
        title = data.get('title')
        
        chart_data = pypsa_viz_service.create_daily_profile_chart(
            df, component_name, title
        )
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating PyPSA daily profile: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/pypsa/load-duration-curve', methods=['POST'])
def create_pypsa_load_duration_curve():
    """
    Create PyPSA load duration curve
    """
    try:
        data = request.get_json()
        
        load_data = data.get('data', [])
        component_name = data.get('component_name', 'Load')
        title = data.get('title')
        
        chart_data = pypsa_viz_service.create_load_duration_curve(
            load_data, component_name, title
        )
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating PyPSA load duration curve: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/pypsa/generation-mix', methods=['POST'])
def create_pypsa_generation_mix():
    """
    Create PyPSA generation mix chart
    """
    try:
        data = request.get_json()
        
        if 'data' in data:
            df = pd.DataFrame(data['data'])
        else:
            return jsonify({'error': 'No data provided'}), 400
        
        title = data.get('title', 'Generation Mix')
        
        chart_data = pypsa_viz_service.create_generation_mix_chart(df, title)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating PyPSA generation mix: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/pypsa/capacity', methods=['POST'])
def create_pypsa_capacity():
    """
    Create PyPSA capacity chart
    """
    try:
        data = request.get_json()
        
        capacity_data = data.get('data', {})
        title = data.get('title', 'Installed Capacity')
        
        chart_data = pypsa_viz_service.create_capacity_chart(capacity_data, title)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating PyPSA capacity chart: {e}")
        return jsonify({'error': str(e)}), 500

# Load Profile Chart Endpoints
@chart_management_bp.route('/loadprofile/heatmap', methods=['POST'])
def create_loadprofile_heatmap():
    """
    Create load profile heatmap
    """
    try:
        data = request.get_json()
        
        if 'data' in data:
            df = pd.DataFrame(data['data'])
            # Convert timestamp column if present
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
        else:
            return jsonify({'error': 'No data provided'}), 400
        
        title = data.get('title', 'Load Pattern Heatmap')
        x_label = data.get('x_label', 'Hour of Day')
        y_label = data.get('y_label', 'Month')
        
        chart_data = loadprofile_viz_service.create_load_heatmap(
            df, title, x_label, y_label
        )
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating load profile heatmap: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/loadprofile/weekly-pattern', methods=['POST'])
def create_loadprofile_weekly_pattern():
    """
    Create weekly load pattern chart
    """
    try:
        data = request.get_json()
        
        if 'data' in data:
            df = pd.DataFrame(data['data'])
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
        else:
            return jsonify({'error': 'No data provided'}), 400
        
        title = data.get('title', 'Weekly Load Pattern')
        
        chart_data = loadprofile_viz_service.create_weekly_pattern_chart(df, title)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating weekly pattern chart: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/loadprofile/seasonal-comparison', methods=['POST'])
def create_loadprofile_seasonal_comparison():
    """
    Create seasonal load comparison chart
    """
    try:
        data = request.get_json()
        
        if 'data' in data:
            df = pd.DataFrame(data['data'])
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
        else:
            return jsonify({'error': 'No data provided'}), 400
        
        title = data.get('title', 'Seasonal Load Comparison')
        
        chart_data = loadprofile_viz_service.create_seasonal_comparison_chart(df, title)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"Error creating seasonal comparison chart: {e}")
        return jsonify({'error': str(e)}), 500

# Theme Management Endpoints
@chart_management_bp.route('/themes', methods=['GET'])
def get_available_themes():
    """
    Get list of available themes
    """
    try:
        themes = color_manager.get_available_themes()
        current_theme = color_manager.get_current_theme()
        
        return jsonify({
            'success': True,
            'themes': themes,
            'current_theme': current_theme
        })
        
    except Exception as e:
        logger.error(f"Error getting themes: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/themes/<theme_name>', methods=['POST'])
def set_theme(theme_name):
    """
    Set the current theme
    """
    try:
        success = color_manager.set_theme(theme_name)
        
        if success:
            return jsonify({
                'success': True,
                'theme': theme_name,
                'message': f'Theme changed to {theme_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Theme {theme_name} not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error setting theme: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/themes/custom', methods=['POST'])
def create_custom_theme():
    """
    Create a custom theme
    """
    try:
        data = request.get_json()
        
        theme_name = data.get('name')
        theme_colors = data.get('colors', {})
        
        if not theme_name:
            return jsonify({'error': 'Theme name is required'}), 400
        
        success = color_manager.create_custom_theme(theme_name, theme_colors)
        
        if success:
            return jsonify({
                'success': True,
                'theme': theme_name,
                'message': f'Custom theme {theme_name} created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create custom theme'
            }), 400
            
    except Exception as e:
        logger.error(f"Error creating custom theme: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/themes/<theme_name>/colors', methods=['GET'])
def get_theme_colors(theme_name):
    """
    Get colors for a specific theme
    """
    try:
        theme_colors = color_manager.get_theme_colors(theme_name)
        chart_colors = color_manager.get_chart_colors_themed(10, theme_name)
        
        return jsonify({
            'success': True,
            'theme': theme_name,
            'theme_colors': theme_colors,
            'chart_colors': chart_colors
        })
        
    except Exception as e:
        logger.error(f"Error getting theme colors: {e}")
        return jsonify({'error': str(e)}), 500

# Export Endpoints
@chart_management_bp.route('/export/summary', methods=['POST'])
def get_export_summary():
    """
    Get export summary for chart data
    """
    try:
        chart_data = request.get_json()
        
        summary = chart_export_service.create_export_summary(chart_data)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error creating export summary: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/export/<format_type>', methods=['POST'])
def export_chart(format_type):
    """
    Export chart data in specified format
    """
    try:
        chart_data = request.get_json()
        filename = request.args.get('filename')
        
        if format_type == 'json':
            result = chart_export_service.export_to_json(chart_data, filename)
        elif format_type == 'csv':
            result = chart_export_service.export_to_csv(chart_data, filename)
        elif format_type == 'excel':
            result = chart_export_service.export_to_excel(chart_data, filename)
        elif format_type == 'config':
            result = chart_export_service.export_chart_config(chart_data, filename)
        else:
            return jsonify({'error': f'Unsupported format: {format_type}'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error exporting chart: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/export/multiple', methods=['POST'])
def export_multiple_formats():
    """
    Export chart data in multiple formats
    """
    try:
        data = request.get_json()
        chart_data = data.get('chart_data', {})
        formats = data.get('formats', ['json', 'csv'])
        base_filename = data.get('filename')
        
        result = chart_export_service.export_multiple_formats(
            chart_data, formats, base_filename
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error exporting multiple formats: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    Download exported file
    """
    try:
        # This is a placeholder - in a real implementation,
        # you would store the exported files temporarily and serve them
        return jsonify({
            'message': 'File download endpoint - implementation depends on file storage strategy',
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({'error': str(e)}), 500

# Utility Endpoints
@chart_management_bp.route('/colors/sectors', methods=['GET'])
def get_sector_colors():
    """
    Get sector color mappings
    """
    try:
        sectors = request.args.getlist('sectors')
        if not sectors:
            # Return all sector colors
            all_colors = color_manager.get_all_colors()
            sector_colors = all_colors.get('sectors', {})
        else:
            sector_colors = color_manager.get_sector_colors(sectors)
        
        return jsonify({
            'success': True,
            'sector_colors': sector_colors
        })
        
    except Exception as e:
        logger.error(f"Error getting sector colors: {e}")
        return jsonify({'error': str(e)}), 500

@chart_management_bp.route('/colors/chart', methods=['GET'])
def get_chart_colors():
    """
    Get chart color palette
    """
    try:
        count = request.args.get('count', 10, type=int)
        theme = request.args.get('theme')
        
        if theme:
            colors = color_manager.get_chart_colors_themed(count, theme)
        else:
            colors = color_manager.get_chart_colors(count)
        
        return jsonify({
            'success': True,
            'colors': colors,
            'count': len(colors)
        })
        
    except Exception as e:
        logger.error(f"Error getting chart colors: {e}")
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@chart_management_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check for chart management service
    """
    return jsonify({
        'status': 'healthy',
        'services': {
            'pypsa_visualization': 'available',
            'loadprofile_visualization': 'available',
            'chart_export': 'available',
            'color_manager': 'available'
        },
        'current_theme': color_manager.get_current_theme()
    })