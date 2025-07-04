# blueprints/demand_visualization_bp.py
"""
Demand Visualization Blueprint - ENHANCED WITH GLOBAL FILTER DEBUGGING
Dynamic API endpoints with comprehensive filter logging and validation
"""
import os
import logging
from flask import Blueprint, request, jsonify, render_template, send_file, current_app
from datetime import datetime
from typing import Dict, Any, Optional

from services.demand_visualization_service import (
    DemandVisualizationService, 
    FilterConfig,
    create_filter_config_from_args
)
from utils.common_decorators import require_project
from utils.color_manager import color_manager

logger = logging.getLogger(__name__)

demand_visualization_bp = Blueprint(
    'demand_visualization',
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

def get_service() -> DemandVisualizationService:
    """Get demand visualization service instance"""
    project_path = current_app.config.get('CURRENT_PROJECT_PATH')
    if not project_path:
        raise ValueError("No project selected")
    return DemandVisualizationService(project_path)

def create_error_response(error: str, status_code: int = 500) -> tuple:
    """Create standardized error response"""
    return jsonify({
        'success': False,
        'error': error,
        'timestamp': datetime.now().isoformat()
    }), status_code

def create_success_response(data: Any, message: str = None) -> Dict:
    """Create standardized success response"""
    response = {
        'success': True,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    if message:
        response['message'] = message
    return jsonify(response)

# ===== MAIN PAGE ROUTE =====

@demand_visualization_bp.route('/')
@require_project
def demand_visualization_route():
    """main demand visualization page"""
    try:
        service = get_service()
        scenarios = service.get_available_scenarios()
        
        # Prepare scenario data for frontend
        scenarios_data = []
        for scenario in scenarios:
            scenario_data = {
                'name': scenario.name,
                'sectors_count': scenario.sectors_count,
                'year_range': scenario.year_range,
                'file_count': scenario.file_count,
                'last_modified': scenario.last_modified,
                'available_sectors': scenario.available_sectors or [],
                'available_models': scenario.available_models or [],
                'has_data': scenario.has_data
            }
            scenarios_data.append(scenario_data)
        
        context = {
            'page_title': 'Demand Visualization & Analysis',
            'scenarios': scenarios_data,
            'has_scenarios': len(scenarios_data) > 0,
            'current_project': current_app.config.get('CURRENT_PROJECT'),
            'color_manager': color_manager,
            'available_units': ['TWh', 'GWh', 'MWh', 'kWh'],
            'chart_types': ['line', 'bar', 'area', 'stacked_bar']
        }
        
        return render_template('demand_visualization.html', **context)
        
    except Exception as e:
        logger.exception(f"Error loading demand visualization page: {e}")
        return render_template('errors/500.html', error=str(e)), 500

# ===== CORE API ENDPOINTS WITH ENHANCED FILTER DEBUGGING =====

@demand_visualization_bp.route('/api/scenarios')
def api_get_scenarios():
    """Get available scenarios with comprehensive metadata"""
    try:
        service = get_service()
        scenarios = service.get_available_scenarios()
        
        scenarios_data = []
        for scenario in scenarios:
            scenario_data = {
                'name': scenario.name,
                'sectors_count': scenario.sectors_count,
                'year_range': scenario.year_range,
                'file_count': scenario.file_count,
                'has_data': scenario.has_data,
                'last_modified': scenario.last_modified,
                'available_sectors': scenario.available_sectors or [],
                'available_models': scenario.available_models or [],
                'metadata': {
                    'path': scenario.path,
                    'analysis_timestamp': datetime.now().isoformat()
                }
            }
            scenarios_data.append(scenario_data)
        
        return create_success_response({
            'scenarios': scenarios_data,
            'total_count': len(scenarios_data),
            'has_data': len(scenarios_data) > 0
        })
        
    except Exception as e:
        logger.exception(f"Error getting scenarios: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/scenario/<scenario_name>')
def api_get_scenario_data(scenario_name: str):
    """
    ENHANCED: Get scenario data with comprehensive filter debugging
    """
    try:
        service = get_service()
        
        # Create filter configuration from request args
        filters = create_filter_config_from_args(request.args)
        
        # COMPREHENSIVE FILTER DEBUGGING
        logger.info(f"API CALL - SCENARIO DATA REQUEST")
        logger.info(f"Scenario: {scenario_name}")
        logger.info(f"Raw Request Args: {dict(request.args)}")
        logger.info(f"Parsed Filters Object: {filters}")
        logger.info(f"Filter Details:")
        logger.info(f"  - Unit: {filters.unit}")
        logger.info(f"  - Start Year: {filters.start_year}")
        logger.info(f"  - End Year: {filters.end_year}")
        logger.info(f"  - Selected Sectors: {filters.selected_sectors}")
        logger.info(f"  - Selected Models: {filters.selected_models}")
        
        # Get scenario data with comprehensive filter application
        data = service.get_scenario_data(scenario_name, filters)
        
        if 'error' in data:
            logger.error(f"Scenario data loading failed: {data['error']}")
            return create_error_response(data['error'], 404)
        
        # ENHANCED: Add comprehensive filter metadata to response
        data['request_metadata'] = {
            'scenario_name': scenario_name,
            'request_timestamp': datetime.now().isoformat(),
            'request_url': request.url,
            'request_args_raw': dict(request.args),
            'filters_applied': {
                'unit': filters.unit,
                'start_year': filters.start_year,
                'end_year': filters.end_year,
                'selected_sectors_count': len(filters.selected_sectors) if filters.selected_sectors else 0,
                'selected_models_count': len(filters.selected_models) if filters.selected_models else 0,
                'filter_parsing_success': True
            },
            'data_summary': {
                'sectors_loaded': len(data.get('sectors', {})),
                'total_sectors_available': data.get('total_sectors', 0),
                'year_range_effective': data.get('year_range', {}),
                'unit_effective': data.get('unit', 'Unknown')
            }
        }
        
        # Log successful data loading
        logger.info(f"✅ SCENARIO DATA LOADED SUCCESSFULLY")
        logger.info(f"  - Sectors loaded: {len(data.get('sectors', {}))}")
        logger.info(f"  - Unit applied: {data.get('unit', 'Unknown')}")
        logger.info(f"  - Year range: {data.get('year_range', {})}")
        if 'applied_filters' in data:
            logger.info(f"  - Filter metadata: {data['applied_filters']}")
        
        return create_success_response(data)
        
    except Exception as e:
        logger.exception(f"Error getting scenario data for {scenario_name}: {e}")
        logger.error(f"Request args were: {dict(request.args)}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/scenario/<scenario_name>/analysis')
def api_get_scenario_analysis(scenario_name: str):
    """Get comprehensive scenario analysis with filter awareness"""
    try:
        service = get_service()
        filters = create_filter_config_from_args(request.args)
        
        logger.info(f"Generating analysis for {scenario_name} with filters: {filters}")
        
        analysis = service.get_analysis_summary(scenario_name, filters)
        
        if 'error' in analysis:
            return create_error_response(analysis['error'], 404)
        
        return create_success_response(analysis)
        
    except Exception as e:
        logger.exception(f"Error getting scenario analysis: {e}")
        return create_error_response(str(e))

# ===== ENHANCED CHART GENERATION ENDPOINTS =====

@demand_visualization_bp.route('/api/chart/sector/<scenario_name>/<sector_name>')
def api_generate_sector_chart(scenario_name: str, sector_name: str):
    """
    ENHANCED: Generate sector chart with comprehensive filter debugging
    """
    try:
        service = get_service()
        
        # Get chart parameters
        chart_type = request.args.get('chart_type', 'line')
        filters = create_filter_config_from_args(request.args)
        
        # COMPREHENSIVE CHART GENERATION LOGGING
        logger.info(f"CHART GENERATION REQUEST")
        logger.info(f"Scenario: {scenario_name}")
        logger.info(f"Sector: {sector_name}")
        logger.info(f"Chart Type: {chart_type}")
        logger.info(f"Filters Applied:")
        logger.info(f"  - Unit: {filters.unit}")
        logger.info(f"  - Start Year: {filters.start_year}")
        logger.info(f"  - End Year: {filters.end_year}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Raw Args: {dict(request.args)}")
        
        # Generate chart data with filters
        chart_result = service.generate_sector_chart_data(
            scenario_name=scenario_name,
            sector_name=sector_name,
            chart_type=chart_type,
            filters=filters
        )
        
        if not chart_result.get('success'):
            error_msg = chart_result.get('error', 'Chart generation failed')
            logger.error(f"Chart generation failed: {error_msg}")
            return create_error_response(error_msg)
        
        # Add request metadata to chart result
        chart_result['request_metadata'] = {
            'scenario_name': scenario_name,
            'sector_name': sector_name,
            'chart_type': chart_type,
            'filters_used': {
                'unit': filters.unit,
                'start_year': filters.start_year,
                'end_year': filters.end_year
            },
            'generation_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ CHART GENERATED SUCCESSFULLY: {chart_type} for {sector_name}")
        
        return create_success_response(chart_result)
        
    except Exception as e:
        logger.exception(f"Error generating sector chart: {e}")
        logger.error(f"Chart request details - Scenario: {scenario_name}, Sector: {sector_name}, Args: {dict(request.args)}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/chart/sector-comparison/<scenario_name>', methods=['POST'])
def api_generate_sector_comparison_chart(scenario_name: str):
    """
    ENHANCED: Generate sector comparison chart with filter debugging
    """
    try:
        service = get_service()
        
        if not request.is_json:
            return create_error_response('JSON data required', 400)
        
        data = request.get_json()
        
        # Extract parameters
        sectors = data.get('sectors', [])
        selected_models = data.get('selected_models', {})
        chart_type = data.get('chart_type', 'line')
        filter_data = data.get('filters', {})
        
        if not sectors:
            return create_error_response('No sectors specified for comparison', 400)
        
        # Create filter config
        filters = FilterConfig(
            unit=filter_data.get('unit', 'TWh'),
            start_year=filter_data.get('start_year'),
            end_year=filter_data.get('end_year'),
            selected_sectors=sectors,
            selected_models=list(selected_models.values())
        )
        
        # COMPREHENSIVE COMPARISON LOGGING
        logger.info(f"SECTOR COMPARISON CHART REQUEST")
        logger.info(f"Scenario: {scenario_name}")
        logger.info(f"Sectors: {sectors}")
        logger.info(f"Selected Models: {selected_models}")
        logger.info(f"Chart Type: {chart_type}")
        logger.info(f"Filters: {filters}")
        
        # Generate chart data
        chart_result = service.generate_sector_comparison_chart_data(
            scenario_name=scenario_name,
            sectors=sectors,
            selected_models=selected_models,
            chart_type=chart_type,
            filters=filters
        )
        
        if not chart_result.get('success'):
            error_msg = chart_result.get('error', 'Chart generation failed')
            logger.error(f"Sector comparison chart failed: {error_msg}")
            return create_error_response(error_msg)
        
        logger.info(f"✅ SECTOR COMPARISON CHART GENERATED: {len(sectors)} sectors")
        
        return create_success_response(chart_result)
        
    except Exception as e:
        logger.exception(f"Error generating sector comparison chart: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/chart/consolidated/<scenario_name>')
def api_generate_consolidated_chart(scenario_name: str):
    """
    ENHANCED: Generate consolidated chart with filter awareness
    """
    try:
        service = get_service()
        
        # Get chart parameters
        chart_type = request.args.get('chart_type', 'stacked_bar')
        filters = create_filter_config_from_args(request.args)
        
        logger.info(f"CONSOLIDATED CHART REQUEST")
        logger.info(f"Scenario: {scenario_name}")
        logger.info(f"Chart Type: {chart_type}")
        logger.info(f"Filters: {filters}")
        
        # Generate chart data
        chart_result = service.generate_consolidated_chart_data(
            scenario_name=scenario_name,
            chart_type=chart_type,
            filters=filters
        )
        
        if not chart_result.get('success'):
            error_msg = chart_result.get('error', 'Chart generation failed')
            logger.error(f"Consolidated chart generation failed: {error_msg}")
            return create_error_response(error_msg)
        
        logger.info(f"✅ CONSOLIDATED CHART GENERATED: {chart_type}")
        
        return create_success_response(chart_result)
        
    except Exception as e:
        logger.exception(f"Error generating consolidated chart: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/chart/td-losses/<scenario_name>')
def api_generate_td_losses_chart(scenario_name: str):
    """Generate T&D losses chart"""
    try:
        service = get_service()
        
        logger.info(f"T&D LOSSES CHART REQUEST for {scenario_name}")
        
        # Generate chart data
        chart_result = service.generate_td_losses_chart_data(scenario_name)
        
        if not chart_result.get('success'):
            error_msg = chart_result.get('error', 'Chart generation failed')
            logger.error(f"T&D losses chart failed: {error_msg}")
            return create_error_response(error_msg)
        
        logger.info(f"✅ T&D LOSSES CHART GENERATED")
        
        return create_success_response(chart_result)
        
    except Exception as e:
        logger.exception(f"Error generating T&D losses chart: {e}")
        return create_error_response(str(e))

# ===== CONFIGURATION MANAGEMENT ENDPOINTS =====

@demand_visualization_bp.route('/api/model-selection/<scenario_name>', methods=['GET', 'POST'])
def api_model_selection(scenario_name: str):
    """model selection management"""
    try:
        service = get_service()
        
        if request.method == 'GET':
            config = service.get_model_selection(scenario_name)
            return create_success_response({
                'config': config,
                'scenario_name': scenario_name
            })
        
        elif request.method == 'POST':
            if not request.is_json:
                return create_error_response('JSON data required', 400)
            
            data = request.get_json()
            model_selection = data.get('model_selection', {})
            
            if not model_selection:
                return create_error_response('Model selection data required', 400)
            
            # Validate model selection against current scenario
            filters = FilterConfig()  # Use default filters for validation
            validation_result = service.get_scenario_data(scenario_name, filters)
            if 'error' in validation_result:
                return create_error_response(f"Scenario validation failed: {validation_result['error']}")
            
            available_sectors = validation_result.get('sector_list', [])
            invalid_sectors = [s for s in model_selection.keys() if s not in available_sectors]
            
            if invalid_sectors:
                return create_error_response(f"Invalid sectors: {', '.join(invalid_sectors)}", 400)
            
            # Save model selection
            result = service.save_model_selection(scenario_name, model_selection)
            
            if 'error' in result:
                return create_error_response(result['error'])
            
            logger.info(f"Model selection saved for {scenario_name}: {len(model_selection)} sectors")
            
            return create_success_response(result, 'Model selection saved successfully')
            
    except Exception as e:
        logger.exception(f"Error with model selection: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/td-losses/<scenario_name>', methods=['GET', 'POST'])
def api_td_losses(scenario_name: str):
    """T&D losses management"""
    try:
        service = get_service()
        
        if request.method == 'GET':
            config = service.get_td_losses_configuration(scenario_name)
            return create_success_response({
                'config': config,
                'scenario_name': scenario_name
            })
        
        elif request.method == 'POST':
            if not request.is_json:
                return create_error_response('JSON data required', 400)
            
            data = request.get_json()
            td_losses = data.get('td_losses', [])
            
            if not td_losses:
                return create_error_response('T&D losses data required', 400)
            
            # Validate T&D losses data
            for i, loss in enumerate(td_losses):
                if not isinstance(loss, dict):
                    return create_error_response(f'Invalid T&D loss entry at index {i}', 400)
                
                try:
                    year = int(loss.get('year', 0))
                    loss_pct = float(loss.get('loss_percentage', 0))
                    
                    if year <= 0 or not (0 <= loss_pct <= 100):
                        return create_error_response(f'Invalid values in T&D loss entry at index {i}', 400)
                        
                except (ValueError, TypeError):
                    return create_error_response(f'Invalid data types in T&D loss entry at index {i}', 400)
            
            # Save T&D losses
            result = service.save_td_losses_configuration(scenario_name, td_losses)
            
            if 'error' in result:
                return create_error_response(result['error'])
            
            logger.info(f"T&D losses saved for {scenario_name}: {len(td_losses)} points")
            
            return create_success_response(result, 'T&D losses saved successfully')
            
    except Exception as e:
        logger.exception(f"Error with T&D losses: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/consolidated/<scenario_name>', methods=['POST'])
def api_generate_consolidated(scenario_name: str):
    """
    ENHANCED: Generate consolidated results with global filter support
    """
    try:
        if not request.is_json:
            return create_error_response('JSON data required', 400)
        
        data = request.get_json()
        model_selection = data.get('model_selection', {})
        td_losses = data.get('td_losses', [])
        filter_data = data.get('filters', {})
        
        if not model_selection:
            return create_error_response('Model selection required', 400)
        
        if not td_losses:
            return create_error_response('T&D losses configuration required', 400)
        
        # Create filter config from request
        filters = FilterConfig(
            unit=filter_data.get('unit', 'TWh'),
            start_year=filter_data.get('start_year'),
            end_year=filter_data.get('end_year')
        )
        
        service = get_service()
        
        # COMPREHENSIVE CONSOLIDATED GENERATION LOGGING
        logger.info(f"CONSOLIDATED RESULTS GENERATION")
        logger.info(f"Scenario: {scenario_name}")
        logger.info(f"Model Selection: {len(model_selection)} sectors")
        logger.info(f"T&D Losses: {len(td_losses)} points")
        logger.info(f"Global Filters Applied:")
        logger.info(f"  - Unit: {filters.unit}")
        logger.info(f"  - Start Year: {filters.start_year}")
        logger.info(f"  - End Year: {filters.end_year}")
        
        # Generate consolidated results with filters
        result = service.generate_consolidated_results(
            scenario_name=scenario_name,
            model_selection=model_selection,
            td_losses=td_losses,
            filters=filters
        )
        
        if 'error' in result:
            logger.error(f"Consolidated generation failed: {result['error']}")
            return create_error_response(result['error'])
        
        logger.info(f"✅ CONSOLIDATED RESULTS GENERATED with filters")
        logger.info(f"  - Data points: {len(result.get('consolidated_data', []))}")
        logger.info(f"  - Unit: {filters.unit}")
        
        return create_success_response(result, 'Consolidated results generated successfully')
        
    except Exception as e:
        logger.exception(f"Error generating consolidated results: {e}")
        return create_error_response(str(e))

# ===== ENHANCED EXPORT ENDPOINTS =====

@demand_visualization_bp.route('/api/export/<scenario_name>')
def api_export_data(scenario_name: str):
    """
    ENHANCED: Export data with comprehensive filter support
    """
    try:
        service = get_service()
        
        export_type = request.args.get('type', 'scenario')  # 'scenario' or 'consolidated'
        
        if export_type == 'scenario':
            # Apply filters to export
            filters = create_filter_config_from_args(request.args)
            
            logger.info(f"EXPORTING SCENARIO DATA with filters")
            logger.info(f"Scenario: {scenario_name}")
            logger.info(f"Filters: {filters}")
            
            file_path = service.export_scenario_data(scenario_name, filters)
            
        elif export_type == 'consolidated':
            logger.info(f"EXPORTING CONSOLIDATED DATA for {scenario_name}")
            file_path = service.export_consolidated_data(scenario_name)
        else:
            return create_error_response(f'Invalid export type: {export_type}', 400)
        
        if not os.path.exists(file_path):
            return create_error_response('Export file not found', 404)
        
        # Generate download filename with filter information
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if export_type == 'scenario':
            filters = create_filter_config_from_args(request.args)
            filter_suffix = service._create_filter_suffix(filters)
            download_name = f"{scenario_name}_{export_type}_export{filter_suffix}_{timestamp}.csv"
        else:
            download_name = f"{scenario_name}_{export_type}_export_{timestamp}.csv"
        
        logger.info(f"✅ EXPORT READY: {download_name}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.exception(f"Error exporting data: {e}")
        return create_error_response(str(e))

# ===== VALIDATION ENDPOINTS =====

@demand_visualization_bp.route('/api/validate/<scenario_name>')
def api_validate_scenario(scenario_name: str):
    """Comprehensive scenario validation with filter awareness"""
    try:
        service = get_service()
        
        # Get scenario info
        scenarios = service.get_available_scenarios()
        scenario_info = next((s for s in scenarios if s.name == scenario_name), None)
        
        if not scenario_info:
            return create_error_response(f"Scenario '{scenario_name}' not found", 404)
        
        # Load scenario data for validation with default filters
        filters = FilterConfig()  # Use defaults for validation
        scenario_data = service.get_scenario_data(scenario_name, filters)
        
        # Check configurations
        model_config = service.get_model_selection(scenario_name)
        td_losses_config = service.get_td_losses_configuration(scenario_name)
        
        # Comprehensive validation
        validation_result = {
            'valid': 'error' not in scenario_data,
            'scenario_info': {
                'name': scenario_info.name,
                'sectors_count': scenario_info.sectors_count,
                'year_range': scenario_info.year_range,
                'has_data': scenario_info.has_data,
                'available_sectors': scenario_info.available_sectors or [],
                'available_models': scenario_info.available_models or []
            },
            'configurations': {
                'has_model_selection': bool(model_config.get('model_selection')),
                'has_td_losses': bool(td_losses_config.get('td_losses')),
                'model_selection_count': len(model_config.get('model_selection', {})),
                'td_losses_count': len(td_losses_config.get('td_losses', []))
            },
            'data_validation': {
                'has_sector_data': 'error' not in scenario_data,
                'sectors_with_data': len(scenario_data.get('sectors', {})) if 'error' not in scenario_data else 0,
                'total_data_points': 0,
                'data_quality_score': 0,
                'filter_support': True
            }
        }
        
        # Calculate data quality metrics
        if 'error' not in scenario_data:
            total_points = 0
            quality_scores = []
            
            for sector_data in scenario_data['sectors'].values():
                sector_points = len(sector_data.get('years', [])) * len(sector_data.get('models', []))
                total_points += sector_points
                
                # Simple quality score based on data completeness
                if sector_points > 0:
                    non_zero_count = 0
                    total_values = 0
                    
                    for model in sector_data.get('models', []):
                        if model in sector_data:
                            values = sector_data[model]
                            total_values += len(values)
                            non_zero_count += len([v for v in values if v > 0])
                    
                    if total_values > 0:
                        quality_scores.append(non_zero_count / total_values * 100)
            
            validation_result['data_validation']['total_data_points'] = total_points
            validation_result['data_validation']['data_quality_score'] = round(
                sum(quality_scores) / len(quality_scores) if quality_scores else 0, 1
            )
        
        return create_success_response({'validation': validation_result})
        
    except Exception as e:
        logger.exception(f"Error validating scenario: {e}")
        return create_error_response(str(e))

# ===== COLOR MANAGEMENT ENDPOINTS (UNCHANGED) =====

@demand_visualization_bp.route('/api/colors/get-all')
def api_get_all_colors():
    """Get all colors with scenario-specific"""
    try:
        colors = color_manager.get_all_colors()
        
        # Add current theme information
        colors = {
            **colors,
            'current_theme': color_manager.get_current_theme(),
            'available_themes': color_manager.get_available_themes(),
            'theme_colors': color_manager.get_theme_colors()
        }
        
        return create_success_response(colors)
        
    except Exception as e:
        logger.exception(f"Error getting colors: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/colors/scenario/<scenario_name>')
def api_get_scenario_specific_colors(scenario_name: str):
    """Get colors specific to a scenario's sectors and models"""
    try:
        service = get_service()
        
        # Get scenario data to determine available sectors and models
        scenario_data = service.get_scenario_data(scenario_name)
        
        if 'error' in scenario_data:
            return create_error_response(scenario_data['error'], 404)
        
        # Get colors for available sectors and models
        available_sectors = scenario_data.get('sector_list', [])
        available_models = scenario_data.get('available_models', [])
        
        scenario_colors = {
            'sectors': color_manager.get_sector_colors(available_sectors),
            'models': color_manager.get_model_colors(available_models),
            'chart_colors': color_manager.get_chart_colors(max(len(available_sectors), len(available_models))),
            'available_sectors': available_sectors,
            'available_models': available_models
        }
        
        return create_success_response(scenario_colors)
        
    except Exception as e:
        logger.exception(f"Error getting scenario-specific colors: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/colors/set', methods=['POST'])
def api_set_color():
    """Set color with validation"""
    try:
        if not request.is_json:
            return create_error_response('JSON data required', 400)
        
        data = request.get_json()
        category = data.get('category')
        item = data.get('item')
        color = data.get('color')
        
        if not all([category, item, color]):
            return create_error_response('Category, item, and color are required', 400)
        
        # Validate color format
        if not color.startswith('#') or len(color) != 7:
            return create_error_response('Color must be in hex format (#RRGGBB)', 400)
        
        # Validate hex characters
        try:
            int(color[1:], 16)
        except ValueError:
            return create_error_response('Invalid hex color format', 400)
        
        success = color_manager.set_color(category, item, color)
        
        if success:
            return create_success_response({
                'category': category,
                'item': item,
                'color': color,
                'updated_at': datetime.now().isoformat()
            }, f'Color updated for {category}.{item}')
        else:
            return create_error_response('Failed to save color')
            
    except Exception as e:
        logger.exception(f"Error setting color: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/colors/reset', methods=['POST'])
def api_reset_colors():
    """Reset colors with options"""
    try:
        data = request.get_json() if request.is_json else {}
        category = data.get('category') if data else None
        
        success = color_manager.reset_to_defaults(category)
        
        if success:
            message = f'Colors reset for {category}' if category else 'All colors reset to defaults'
            return create_success_response({
                'reset_category': category,
                'reset_at': datetime.now().isoformat()
            }, message)
        else:
            return create_error_response('Failed to reset colors')
            
    except Exception as e:
        logger.exception(f"Error resetting colors: {e}")
        return create_error_response(str(e))

# ===== PERFORMANCE AND MONITORING ENDPOINTS =====

@demand_visualization_bp.route('/api/health')
def api_health_check():
    """Health check endpoint with filter support verification"""
    try:
        service = get_service()
        scenarios = service.get_available_scenarios()
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service_info': {
                'scenarios_available': len(scenarios),
                'results_path_exists': os.path.exists(service.results_path),
                'config_path_exists': os.path.exists(service.config_path),
                'global_filter_support': True,
                'enhanced_logging': True
            },
            'color_manager': {
                'initialized': color_manager is not None,
                'current_theme': color_manager.get_current_theme() if color_manager else None
            }
        }
        
        return create_success_response(health_data)
        
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return create_error_response(str(e))

@demand_visualization_bp.route('/api/system-info')
def api_system_info():
    """Get system information for debugging with filter details"""
    try:
        service = get_service()
        
        system_info = {
            'project_path': service.project_path,
            'results_path': service.results_path,
            'config_path': service.config_path,
            'available_units': list(service.unit_factors.keys()),
            'color_manager_info': {
                'themes': color_manager.get_available_themes(),
                'current_theme': color_manager.get_current_theme()
            },
            'filter_support': {
                'units_supported': list(service.unit_factors.keys()),
                'filter_debugging_enabled': True,
                'comprehensive_logging': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return create_success_response(system_info)
        
    except Exception as e:
        logger.exception(f"Error getting system info: {e}")
        return create_error_response(str(e))

# ===== ERROR HANDLERS =====

@demand_visualization_bp.errorhandler(404)
def not_found(error):
    return create_error_response('Resource not found', 404)

@demand_visualization_bp.errorhandler(500)
def internal_error(error):
    return create_error_response('Internal server error', 500)

@demand_visualization_bp.errorhandler(400)
def bad_request(error):
    return create_error_response('Bad request', 400)

def register_demand_visualization_bp(app):
    """Register the demand visualization blueprint"""
    try:
        app.register_blueprint(
            demand_visualization_bp, 
            url_prefix='/demand_visualization'
        )
        logger.info("Enhanced Demand Visualization Blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register Enhanced Demand Visualization Blueprint: {e}")
        raise