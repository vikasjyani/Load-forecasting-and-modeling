# blueprints/loadprofile_analysis_bp.py (OPTIMIZED)
"""
Optimized Load Profile Analysis Blueprint with ServiceBlueprint integration
error handling, response formatting, and performance optimization
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import request
import pandas as pd
import numpy as np
from utils.base_blueprint import ServiceBlueprint, with_service

from utils.common_decorators import (
    require_project, validate_json_request, handle_exceptions,
    api_route, track_performance, cache_route, memory_efficient_operation
)
from utils.response_utils import success_json, error_json, validation_error_json
from utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError
from utils.constants import UNIT_FACTORS, SUCCESS_MESSAGES, ERROR_MESSAGES
from services.loadprofile_analysis_service import LoadProfileAnalysisService

logger = logging.getLogger(__name__)

class LoadProfileAnalysisBlueprint(ServiceBlueprint):
    """
    Optimized Load Profile Analysis Blueprint with comprehensive analytics
    """
    
    def __init__(self):
        super().__init__(
            'loadprofile_analysis',
            __name__,
            service_class=LoadProfileAnalysisService,
            template_folder='../templates',
            static_folder='../static',
            url_prefix='/load_profile_analysis'
        )
    
    def register_routes(self):
        """Register optimized load profile analysis routes"""
        
        # Main dashboard route
        @self.blueprint.route('/')
        @require_project
        @handle_exceptions('loadprofile_analysis')
        @track_performance(threshold_ms=2000)
        def analysis_dashboard():
            return self._render_dashboard()
        
        # Profile Management APIs
        @self.blueprint.route('/api/available_profiles')
        @api_route(cache_ttl=300)
        def get_available_profiles_api():
            return self._get_available_profiles()
        
        @self.blueprint.route('/api/profile_data/<profile_id>')
        @api_route(cache_ttl=300)
        def get_profile_data_api(profile_id):
            return self._get_profile_data(profile_id)
        
        @self.blueprint.route('/api/profile_metadata/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_metadata_api(profile_id):
            return self._get_profile_metadata(profile_id)
        
        # Analysis APIs
        @self.blueprint.route('/api/profile_analysis/<profile_id>/<analysis_type>')
        @api_route(cache_ttl=600)
        def get_profile_analysis_api(profile_id, analysis_type):
            return self._get_profile_analysis(profile_id, analysis_type)
        
        @self.blueprint.route('/api/comprehensive_analysis/<profile_id>')
        @api_route(cache_ttl=1200)
        def get_comprehensive_analysis_api(profile_id):
            return self._get_comprehensive_analysis(profile_id)
        
        @self.blueprint.route('/api/statistical_summary/<profile_id>')
        @api_route(cache_ttl=600)
        def get_statistical_summary_api(profile_id):
            return self._get_statistical_summary(profile_id)
        
        # Comparison APIs
        @self.blueprint.route('/api/compare_profiles', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids'],
            max_concurrent=2
        )
        def compare_profiles_api():
            return self._compare_profiles()
        
        @self.blueprint.route('/api/benchmark_profile/<profile_id>')
        @api_route(cache_ttl=600)
        def benchmark_profile_api(profile_id):
            return self._benchmark_profile(profile_id)
        
        # Temporal Analysis APIs
        @self.blueprint.route('/api/fiscal_years/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_fiscal_years_api(profile_id):
            return self._get_profile_fiscal_years(profile_id)
        
        @self.blueprint.route('/api/seasonal_analysis/<profile_id>')
        @api_route(cache_ttl=600)
        def get_seasonal_analysis_api(profile_id):
            return self._get_seasonal_analysis(profile_id)
        
        @self.blueprint.route('/api/time_series_decomposition/<profile_id>')
        @api_route(cache_ttl=1200)
        def get_time_series_decomposition_api(profile_id):
            return self._get_time_series_decomposition(profile_id)
        
        # Quality Assessment APIs
        @self.blueprint.route('/api/profile_validation/<profile_id>')
        @api_route(cache_ttl=300)
        def validate_profile_api(profile_id):
            return self._validate_profile(profile_id)
        
        @self.blueprint.route('/api/data_quality_report/<profile_id>')
        @api_route(cache_ttl=600)
        def get_data_quality_report_api(profile_id):
            return self._get_data_quality_report(profile_id)
        
        # Export APIs
        @self.blueprint.route('/api/export_analysis/<profile_id>')
        @require_project
        @handle_exceptions('loadprofile_analysis')
        def export_analysis_api(profile_id):
            return self._export_analysis(profile_id)
        
        @self.blueprint.route('/api/export_comparison', methods=['POST'])
        @api_route(required_json_fields=['profile_ids'])
        def export_comparison_api():
            return self._export_comparison()
        
        # Batch Operations APIs
        @self.blueprint.route('/api/batch_analysis', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids', 'analysis_types'],
            max_concurrent=1
        )
        def batch_analysis_api():
            return self._batch_analysis()
        
        @self.blueprint.route('/api/generate_report', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids'],
            max_concurrent=1
        )
        def generate_report_api():
            return self._generate_comprehensive_report()
        
        # Additional Analysis APIs
        @self.blueprint.route('/api/analysis_suitability/<profile_id>/<analysis_type>')
        @api_route(cache_ttl=300)
        def check_analysis_suitability(profile_id, analysis_type):
            """Check if analysis type is suitable for profile data"""
            return self._check_analysis_suitability(profile_id, analysis_type)

        @self.blueprint.route('/api/profile_summary/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_summary(profile_id):
            """Get comprehensive profile summary"""
            return self._get_profile_summary(profile_id)

        @self.blueprint.route('/api/multi_profile_comparison', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids', 'comparison_metrics'],
            max_concurrent=1
        )
        def multi_profile_comparison():
            """Advanced multi-profile comparison with custom metrics"""
            return self._advanced_multi_profile_comparison()

        @self.blueprint.route('/api/profile_insights/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_insights(profile_id):
            """Get AI-powered insights for load profile"""
            return self._generate_profile_insights(profile_id)

        @self.blueprint.route('/api/export_heatmap/<profile_id>')
        @require_project
        @handle_exceptions('loadprofile_analysis')
        def export_heatmap_data(profile_id):
            """Export heatmap data for external visualization"""
            return self._export_heatmap_data(profile_id)

        @self.blueprint.route('/api/profile_forecast_validation/<profile_id>')
        @api_route(cache_ttl=300)
        def validate_forecast_profile(profile_id):
            """Special validation for generated forecast profiles"""
            return self._validate_forecast_profile(profile_id)
    
    def _render_dashboard(self):
        """Render the main analysis dashboard"""
        try:
            # Get cached dashboard data
            dashboard_data = self._get_cached_dashboard_data()
            
            if 'error' in dashboard_data:
                return self._render_error_page(dashboard_data['error'])
            
            return self._render_template('load_profile_analysis.html', **dashboard_data)
            
        except Exception as e:
            logger.exception(f"Error rendering dashboard: {e}")
            return self._render_error_page(str(e))
    
    @with_service
    def _get_available_profiles(self) -> Dict[str, Any]:
        """Get all available load profiles with metadata"""
        try:
            profiles = self.service.get_available_profiles()
            
            # Enhance with validation status
            for profile in profiles:
                try:
                    validation = self.service.quick_validate_profile(profile['profile_id'])
                    profile['validation_status'] = validation
                except Exception as validation_error:
                    profile['validation_status'] = {
                        'valid': False,
                        'error': str(validation_error)
                    }
            
            # Calculate summary statistics
            total_profiles = len(profiles)
            valid_profiles = sum(1 for p in profiles if p.get('validation_status', {}).get('valid', False))
            
            # Group by method
            method_groups = {}
            for profile in profiles:
                method = profile.get('method', 'Unknown')
                if method not in method_groups:
                    method_groups[method] = []
                method_groups[method].append(profile)
            
            return success_json(
                "Available profiles retrieved successfully",
                {
                    'profiles': profiles,
                    'summary': {
                        'total_profiles': total_profiles,
                        'valid_profiles': valid_profiles,
                        'invalid_profiles': total_profiles - valid_profiles,
                        'method_groups': {k: len(v) for k, v in method_groups.items()},
                        'total_size_mb': sum(p.get('file_info', {}).get('size_mb', 0) for p in profiles)
                    },
                    'method_groups': method_groups
                }
            )
            
        except Exception as e:
            logger.exception(f"Error getting available profiles: {e}")
            return error_json(f"Failed to get profiles: {str(e)}")
    
    @with_service
    def _get_profile_data(self, profile_id: str) -> Dict[str, Any]:
        """Get profile data with error handling and validation"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            # Extract filters from request
            filters = self._extract_data_filters()
            unit = filters.get('unit', 'kW')
            
            if unit not in UNIT_FACTORS:
                raise ValidationError(f"Invalid unit: {unit}")
            
            # Load and process data
            profile_data = self.service.get_profile_data(profile_id, filters)
            
            return success_json(
                f"Profile data retrieved for '{profile_id}'",
                profile_data
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except ProcessingError as e:
            return error_json(f"Data processing failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error getting profile data: {e}")
            return error_json(f"Failed to get profile data: {str(e)}")
    
    @with_service
    def _get_profile_metadata(self, profile_id: str) -> Dict[str, Any]:
        """Get profile metadata and configuration"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            metadata = self.service.get_profile_metadata(profile_id)
            
            return success_json(
                f"Profile metadata retrieved for '{profile_id}'",
                metadata
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting profile metadata: {e}")
            return error_json(f"Failed to get profile metadata: {str(e)}")
    
    @memory_efficient_operation
    def _get_profile_analysis(self, profile_id: str, analysis_type: str) -> Dict[str, Any]:
        """Get specific analysis for a profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            valid_analysis_types = [
                'overview', 'peak_analysis', 'weekday_weekend', 
                'seasonal', 'monthly', 'duration_curve', 'heatmap',
                'load_factor', 'demand_profile', 'variability'
            ]
            
            if analysis_type not in valid_analysis_types:
                raise ValidationError(f"Invalid analysis type. Must be one of: {valid_analysis_types}")
            
            # Extract analysis parameters
            params = self._extract_analysis_parameters()
            
            # Perform analysis
            analysis_result = self.service.perform_analysis(profile_id, analysis_type, params)
            
            return success_json(
                f"{analysis_type} analysis completed for '{profile_id}'",
                analysis_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except ProcessingError as e:
            return error_json(f"Analysis failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error performing analysis: {e}")
            return error_json(f"Analysis failed: {str(e)}")
    
    @memory_efficient_operation
    def _get_comprehensive_analysis(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis covering all aspects"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            comprehensive_analysis = self.service.get_comprehensive_analysis(profile_id)
            
            return success_json(
                f"Comprehensive analysis completed for '{profile_id}'",
                comprehensive_analysis
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except ProcessingError as e:
            return error_json(f"Comprehensive analysis failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error in comprehensive analysis: {e}")
            return error_json(f"Comprehensive analysis failed: {str(e)}")
    
    @with_service
    def _get_statistical_summary(self, profile_id: str) -> Dict[str, Any]:
        """Get statistical summary of profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            unit = request.args.get('unit', 'kW')
            if unit not in UNIT_FACTORS:
                raise ValidationError(f"Invalid unit: {unit}")
            
            statistical_summary = self.service.get_statistical_summary(profile_id, unit)
            
            return success_json(
                f"Statistical summary completed for '{profile_id}'",
                statistical_summary
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting statistical summary: {e}")
            return error_json(f"Failed to get statistical summary: {str(e)}")
    
    @memory_efficient_operation
    def _compare_profiles(self) -> Dict[str, Any]:
        """Compare multiple load profiles"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            comparison_type = data.get('comparison_type', 'overview')
            
            # Validation
            if len(profile_ids) < 2:
                raise ValidationError("At least 2 profiles required for comparison")
            
            if len(profile_ids) > 5:
                raise ValidationError("Maximum 5 profiles can be compared")
            
            for profile_id in profile_ids:
                if not self._validate_profile_id(profile_id):
                    raise ValidationError(f"Invalid profile ID: {profile_id}")
            
            # Extract comparison parameters
            comparison_params = {
                'unit': data.get('unit', 'kW'),
                'filters': data.get('filters', {}),
                'metrics': data.get('metrics', ['basic', 'statistical']),
                'include_charts': data.get('include_charts', True)
            }
            
            # Perform comparison
            comparison_result = self.service.compare_profiles(
                profile_ids=profile_ids,
                comparison_type=comparison_type,
                parameters=comparison_params
            )
            
            return success_json(
                "Profile comparison completed successfully",
                comparison_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ProcessingError as e:
            return error_json(f"Comparison failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error comparing profiles: {e}")
            return error_json(f"Comparison failed: {str(e)}")
    
    @with_service
    def _benchmark_profile(self, profile_id: str) -> Dict[str, Any]:
        """Benchmark profile against standard metrics"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            benchmark_type = request.args.get('type', 'industry_standard')
            unit = request.args.get('unit', 'kW')
            
            benchmark_result = self.service.benchmark_profile(profile_id, benchmark_type, unit)
            
            return success_json(
                f"Profile benchmarking completed for '{profile_id}'",
                benchmark_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error benchmarking profile: {e}")
            return error_json(f"Benchmarking failed: {str(e)}")
    
    @with_service
    def _get_profile_fiscal_years(self, profile_id: str) -> Dict[str, Any]:
        """Get available fiscal years for profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            fiscal_years = self.service.get_profile_fiscal_years(profile_id)
            
            return success_json(
                f"Fiscal years retrieved for '{profile_id}'",
                {
                    'fiscal_years': fiscal_years,
                    'total_years': len(fiscal_years),
                    'year_range': {
                        'start': min(fiscal_years) if fiscal_years else None,
                        'end': max(fiscal_years) if fiscal_years else None
                    }
                }
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting fiscal years: {e}")
            return error_json(f"Failed to get fiscal years: {str(e)}")
    
    @memory_efficient_operation
    def _get_seasonal_analysis(self, profile_id: str) -> Dict[str, Any]:
        """Get seasonal analysis for profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            analysis_params = self._extract_analysis_parameters()
            seasonal_analysis = self.service.get_seasonal_analysis(profile_id, analysis_params)
            
            return success_json(
                f"Seasonal analysis completed for '{profile_id}'",
                seasonal_analysis
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error in seasonal analysis: {e}")
            return error_json(f"Seasonal analysis failed: {str(e)}")
    
    @memory_efficient_operation
    def _get_time_series_decomposition(self, profile_id: str) -> Dict[str, Any]:
        """Get time series decomposition analysis"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            decomposition_params = {
                'method': request.args.get('method', 'STL'),
                'period': request.args.get('period', 'auto'),
                'seasonal': request.args.get('seasonal', 'additive')
            }
            
            decomposition_result = self.service.get_time_series_decomposition(
                profile_id, decomposition_params
            )
            
            return success_json(
                f"Time series decomposition completed for '{profile_id}'",
                decomposition_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error in time series decomposition: {e}")
            return error_json(f"Time series decomposition failed: {str(e)}")
    
    @with_service
    def _validate_profile(self, profile_id: str) -> Dict[str, Any]:
        """Validate profile data quality"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            validation_result = self.service.validate_profile_comprehensive(profile_id)
            
            return success_json(
                f"Profile validation completed for '{profile_id}'",
                validation_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error validating profile: {e}")
            return error_json(f"Profile validation failed: {str(e)}")
    
    @with_service
    def _get_data_quality_report(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive data quality report"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            quality_report = self.service.generate_data_quality_report(profile_id)
            
            return success_json(
                f"Data quality report generated for '{profile_id}'",
                quality_report
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error generating quality report: {e}")
            return error_json(f"Quality report generation failed: {str(e)}")
    
    @with_service
    def _export_analysis(self, profile_id: str):
        """Export analysis results"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            export_format = request.args.get('format', 'csv').lower()
            analysis_types = request.args.getlist('analysis_types')
            
            if export_format not in ['csv', 'xlsx', 'json']:
                raise ValidationError("Invalid export format. Must be csv, xlsx, or json")
            
            return self.service.export_analysis_results(
                profile_id=profile_id,
                export_format=export_format,
                analysis_types=analysis_types
            )
            
        except ValidationError as e:
            return error_json(str(e), status_code=400)
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error exporting analysis: {e}")
            return error_json(f"Export failed: {str(e)}")
    
    @with_service
    def _export_comparison(self):
        """Export comparison results"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            export_format = data.get('format', 'xlsx')
            
            if len(profile_ids) < 2:
                raise ValidationError("At least 2 profiles required for comparison export")
            
            return self.service.export_comparison_results(profile_ids, export_format)
            
        except ValidationError as e:
            return error_json(str(e), status_code=400)
        except Exception as e:
            logger.exception(f"Error exporting comparison: {e}")
            return error_json(f"Comparison export failed: {str(e)}")
    
    @memory_efficient_operation
    def _batch_analysis(self) -> Dict[str, Any]:
        """Perform batch analysis on multiple profiles"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            analysis_types = data.get('analysis_types', [])
            
            if len(profile_ids) > 10:
                raise ValidationError("Maximum 10 profiles can be processed in batch")
            
            batch_result = self.service.perform_batch_analysis(profile_ids, analysis_types)
            
            return success_json(
                "Batch analysis completed successfully",
                batch_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error in batch analysis: {e}")
            return error_json(f"Batch analysis failed: {str(e)}")
    
    @memory_efficient_operation
    def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            report_type = data.get('report_type', 'comprehensive')
            
            report_result = self.service.generate_comprehensive_report(profile_ids, report_type)
            
            return success_json(
                "Comprehensive report generated successfully",
                report_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error generating report: {e}")
            return error_json(f"Report generation failed: {str(e)}")
    
    # Helper methods
    def _validate_profile_id(self, profile_id: str) -> bool:
        """Validate profile ID format"""
        if not profile_id or '..' in profile_id or '/' in profile_id:
            return False
        return True
    
    def _extract_data_filters(self) -> Dict[str, Any]:
        """Extract data filters from request parameters"""
        from flask import request
        
        filters = {}
        
        # Optional filters
        if request.args.get('year'):
            filters['year'] = request.args.get('year')
        if request.args.get('month'):
            filters['month'] = request.args.get('month')
        if request.args.get('season'):
            filters['season'] = request.args.get('season')
        if request.args.get('day_type'):
            filters['day_type'] = request.args.get('day_type')
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        filters['unit'] = request.args.get('unit', 'kW')
        
        return filters
    
    def _extract_analysis_parameters(self) -> Dict[str, Any]:
        """Extract analysis parameters from request"""
        from flask import request
        
        return {
            'unit': request.args.get('unit', 'kW'),
            'aggregation': request.args.get('aggregation', 'hourly'),
            'include_charts': request.args.get('include_charts', 'true').lower() == 'true',
            'detailed': request.args.get('detailed', 'false').lower() == 'true',
            'filters': self._extract_data_filters()
        }
    
    @cache_route(ttl=300, key_func=lambda: "loadprofile_analysis_dashboard")
    def _get_cached_dashboard_data(self) -> Dict[str, Any]:
        """Get cached dashboard data"""
        try:
            if not self.service:
                return {'error': 'Service not available'}
            
            return self.service.get_dashboard_data()
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}
    
    def _render_template(self, template: str, **kwargs):
        """Render template with error handling"""
        try:
            from flask import render_template
            return render_template(template, **kwargs)
        except Exception as e:
            logger.exception(f"Error rendering template {template}: {e}")
            return self._render_error_page(str(e))
    
    def _render_error_page(self, error_message: str):
        """Render error page"""
        try:
            from flask import render_template
            return render_template('errors/loadprofile_analysis_error.html', error=error_message), 500
        except Exception:
            return f"<h1>Load Profile Analysis Error</h1><p>{error_message}</p>", 500




    # Implementation of new route methods

    @with_service
    def _check_analysis_suitability(self, profile_id: str, analysis_type: str) -> Dict[str, Any]:
        """Check analysis suitability"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            suitability = self.service.validate_analysis_suitability(profile_id, analysis_type)
            
            return success_json(
                f"Analysis suitability check completed for '{profile_id}'",
                suitability
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error checking analysis suitability: {e}")
            return error_json(f"Suitability check failed: {str(e)}")

    @with_service
    def _get_profile_summary(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive profile summary"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            summary = self.service.get_comprehensive_profile_summary(profile_id)
            
            return success_json(
                f"Profile summary retrieved for '{profile_id}'",
                summary
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting profile summary: {e}")
            return error_json(f"Failed to get profile summary: {str(e)}")

    @with_service
    def _advanced_multi_profile_comparison(self) -> Dict[str, Any]:
        """Advanced multi-profile comparison"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            comparison_metrics = data.get('comparison_metrics', [])
            comparison_type = data.get('comparison_type', 'statistical')
            
            if len(profile_ids) < 2:
                raise ValidationError("At least 2 profiles required for comparison")
            
            if len(profile_ids) > 10:
                raise ValidationError("Maximum 10 profiles can be compared")
            
            comparison_result = self.service.advanced_profile_comparison(
                profile_ids=profile_ids,
                metrics=comparison_metrics,
                comparison_type=comparison_type
            )
            
            return success_json(
                "Advanced profile comparison completed",
                comparison_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error in advanced comparison: {e}")
            return error_json(f"Advanced comparison failed: {str(e)}")

    @with_service
    def _generate_profile_insights(self, profile_id: str) -> Dict[str, Any]:
        """Generate AI-powered insights"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            insights = self.service.generate_intelligent_insights(profile_id)
            
            return success_json(
                f"Insights generated for '{profile_id}'",
                insights
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error generating insights: {e}")
            return error_json(f"Insight generation failed: {str(e)}")

    @with_service
    def _export_heatmap_data(self, profile_id: str):
        """Export heatmap data"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            heatmap_type = request.args.get('type', 'hour_day')
            export_format = request.args.get('format', 'json')
            
            return self.service.export_heatmap_data(profile_id, heatmap_type, export_format)
            
        except ValidationError as e:
            return error_json(str(e), status_code=400)
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error exporting heatmap: {e}")
            return error_json(f"Heatmap export failed: {str(e)}")

    @with_service
    def _validate_forecast_profile(self, profile_id: str) -> Dict[str, Any]:
        """Validate generated forecast profiles"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            validation_result = self.service.validate_forecast_profile_data(profile_id)
            
            return success_json(
                f"Forecast validation completed for '{profile_id}'",
                validation_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error validating forecast profile: {e}")
            return error_json(f"Forecast validation failed: {str(e)}")

    # Additional service methods to implement in LoadProfileAnalysisService

    def get_comprehensive_profile_summary(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive profile summary with key metrics"""
        try:
            df = self.analyzer.load_profile_data(profile_id)
            
            if df.empty:
                raise ProcessingError("No data available for profile summary")
            
            # Basic statistics
            statistics = self.analyzer.calculate_comprehensive_statistics(df, 'kW')
            
            # Multi-year analysis if applicable
            fiscal_years = df['Fiscal_Year'].unique() if 'Fiscal_Year' in df.columns else []
            is_multi_year = len(fiscal_years) > 1
            
            # Data quality assessment
            data_quality = self._assess_profile_data_quality(df)
            
            # Pattern analysis
            patterns = self._analyze_load_patterns(df)
            
            # Generate summary insights
            insights = self._generate_summary_insights(statistics, patterns, is_multi_year)
            
            summary = {
                'profile_id': profile_id,
                'basic_info': {
                    'total_records': len(df),
                    'fiscal_years': sorted(fiscal_years.tolist()) if len(fiscal_years) > 0 else [],
                    'is_multi_year': is_multi_year,
                    'date_range': {
                        'start': df['datetime'].min().isoformat() if 'datetime' in df.columns else None,
                        'end': df['datetime'].max().isoformat() if 'datetime' in df.columns else None
                    } if 'datetime' in df.columns else None
                },
                'key_metrics': {
                    'peak_demand': statistics['basic']['peak_load'] if 'basic' in statistics else 0,
                    'average_demand': statistics['basic']['average_load'] if 'basic' in statistics else 0,
                    'load_factor': statistics['basic']['load_factor'] if 'basic' in statistics else 0,
                    'total_energy': statistics['basic']['total_energy'] if 'basic' in statistics else 0,
                    'demand_variability': statistics['basic']['coefficient_of_variation'] if 'basic' in statistics else 0
                },
                'data_quality': data_quality,
                'patterns': patterns,
                'insights': insights,
                'recommended_analyses': self._get_recommended_analyses(df, is_multi_year),
                'generated_at': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.exception(f"Error getting profile summary: {e}")
            raise

    def _assess_profile_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess data quality metrics"""
        total_records = len(df)
        
        quality_metrics = {
            'completeness': 100.0,
            'missing_values': 0,
            'zero_values': 0,
            'negative_values': 0,
            'outliers': 0,
            'data_gaps': 0
        }
        
        if 'Demand (kW)' in df.columns:
            demand_col = 'Demand (kW)'
            demand_data = df[demand_col]
            
            # Missing values
            missing = demand_data.isna().sum()
            quality_metrics['missing_values'] = int(missing)
            quality_metrics['completeness'] = ((total_records - missing) / total_records * 100) if total_records > 0 else 0
            
            # Zero values
            quality_metrics['zero_values'] = int((demand_data == 0).sum())
            
            # Negative values
            quality_metrics['negative_values'] = int((demand_data < 0).sum())
            
            # Outliers (values beyond 3 standard deviations)
            if not demand_data.empty:
                mean_demand = demand_data.mean()
                std_demand = demand_data.std()
                if std_demand > 0:
                    outliers = ((demand_data - mean_demand).abs() > 3 * std_demand).sum()
                    quality_metrics['outliers'] = int(outliers)
            
            # Data gaps (consecutive missing hours)
            if 'datetime' in df.columns and total_records > 24:
                df_sorted = df.sort_values('datetime')
                time_diffs = df_sorted['datetime'].diff()
                expected_interval = pd.Timedelta(hours=1)  # Assuming hourly data
                gaps = (time_diffs > expected_interval * 1.5).sum()  # Allow 50% tolerance
                quality_metrics['data_gaps'] = int(gaps)
        
        # Quality assessment
        quality_score = 100
        if quality_metrics['completeness'] < 95:
            quality_score -= (100 - quality_metrics['completeness'])
        if quality_metrics['zero_values'] > total_records * 0.1:
            quality_score -= 10
        if quality_metrics['negative_values'] > 0:
            quality_score -= 5
        if quality_metrics['outliers'] > total_records * 0.05:
            quality_score -= 10
        if quality_metrics['data_gaps'] > 5:
            quality_score -= 15
        
        quality_metrics['overall_score'] = max(0, quality_score)
        
        # Quality rating
        if quality_score >= 90:
            quality_metrics['rating'] = 'Excellent'
        elif quality_score >= 75:
            quality_metrics['rating'] = 'Good'
        elif quality_score >= 60:
            quality_metrics['rating'] = 'Fair'
        else:
            quality_metrics['rating'] = 'Poor'
        
        return quality_metrics

    def _analyze_load_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze load patterns"""
        patterns = {
            'daily_pattern': 'Unknown',
            'weekly_pattern': 'Unknown',
            'seasonal_pattern': 'Unknown',
            'peak_hours': [],
            'off_peak_hours': [],
            'load_shape': 'Unknown'
        }
        
        try:
            if 'Hour' in df.columns and 'Demand (kW)' in df.columns:
                # Daily pattern analysis
                hourly_avg = df.groupby('Hour')['Demand (kW)'].mean()
                peak_hours = hourly_avg.nlargest(3).index.tolist()
                off_peak_hours = hourly_avg.nsmallest(3).index.tolist()
                
                patterns['peak_hours'] = peak_hours
                patterns['off_peak_hours'] = off_peak_hours
                
                # Classify daily pattern
                morning_peak = any(6 <= h <= 10 for h in peak_hours)
                evening_peak = any(17 <= h <= 21 for h in peak_hours)
                night_minimum = any(0 <= h <= 5 for h in off_peak_hours)
                
                if morning_peak and evening_peak:
                    patterns['daily_pattern'] = 'Double Peak'
                elif evening_peak and night_minimum:
                    patterns['daily_pattern'] = 'Residential'
                elif 9 <= max(peak_hours) <= 17:
                    patterns['daily_pattern'] = 'Commercial'
                else:
                    patterns['daily_pattern'] = 'Industrial'
            
            # Weekly pattern analysis
            if 'datetime' in df.columns:
                df_temp = df.copy()
                df_temp['day_of_week'] = pd.to_datetime(df_temp['datetime']).dt.day_name()
                weekly_avg = df_temp.groupby('day_of_week')['Demand (kW)'].mean()
                
                weekday_avg = weekly_avg[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']].mean()
                weekend_avg = weekly_avg[['Saturday', 'Sunday']].mean()
                
                if weekday_avg > weekend_avg * 1.2:
                    patterns['weekly_pattern'] = 'Business-focused'
                elif weekend_avg > weekday_avg * 1.1:
                    patterns['weekly_pattern'] = 'Leisure-focused'
                else:
                    patterns['weekly_pattern'] = 'Consistent'
            
            # Load shape classification
            if 'Demand (kW)' in df.columns:
                demand_data = df['Demand (kW)'].dropna()
                if not demand_data.empty:
                    cv = demand_data.std() / demand_data.mean() if demand_data.mean() > 0 else 0
                    
                    if cv < 0.2:
                        patterns['load_shape'] = 'Flat'
                    elif cv < 0.4:
                        patterns['load_shape'] = 'Moderate'
                    else:
                        patterns['load_shape'] = 'Variable'
        
        except Exception as e:
            logger.warning(f"Error analyzing load patterns: {e}")
        
        return patterns

    def _generate_summary_insights(self, statistics: Dict, patterns: Dict, is_multi_year: bool) -> List[str]:
        """Generate summary insights"""
        insights = []
        
        try:
            if 'basic' in statistics:
                basic = statistics['basic']
                
                # Load factor insights
                load_factor = basic.get('load_factor', 0)
                if load_factor > 70:
                    insights.append("Excellent load factor indicates efficient system utilization")
                elif load_factor < 40:
                    insights.append("Low load factor suggests opportunities for demand optimization")
                
                # Pattern insights
                daily_pattern = patterns.get('daily_pattern', 'Unknown')
                if daily_pattern == 'Double Peak':
                    insights.append("Double peak pattern typical of mixed commercial-residential load")
                elif daily_pattern == 'Residential':
                    insights.append("Residential load pattern with evening peak demand")
                elif daily_pattern == 'Commercial':
                    insights.append("Commercial load pattern with business hour peaks")
                
                # Multi-year insights
                if is_multi_year:
                    insights.append("Multi-year data enables comprehensive trend analysis")
                    insights.append("Consider year-over-year growth and seasonal variations")
                
                # Load shape insights
                load_shape = patterns.get('load_shape', 'Unknown')
                if load_shape == 'Flat':
                    insights.append("Flat load shape indicates stable, predictable demand")
                elif load_shape == 'Variable':
                    insights.append("Variable load shape requires flexible capacity management")
            
            if not insights:
                insights.append("Profile analysis completed - review detailed metrics for insights")
        
        except Exception as e:
            logger.warning(f"Error generating insights: {e}")
            insights.append("Basic profile analysis completed")
        
        return insights

    def _get_recommended_analyses(self, df: pd.DataFrame, is_multi_year: bool) -> List[Dict[str, str]]:
        """Get recommended analyses based on data characteristics"""
        recommendations = []
        
        data_span_days = (df['datetime'].max() - df['datetime'].min()).days if 'datetime' in df.columns else 0
        
        # Always recommend overview
        recommendations.append({
            'analysis_type': 'overview',
            'priority': 'high',
            'reason': 'Essential for understanding overall load profile characteristics'
        })
        
        # Daily patterns
        if data_span_days >= 7:
            recommendations.append({
                'analysis_type': 'heatmap_hour_day',
                'priority': 'high',
                'reason': 'Reveals daily and weekly load patterns'
            })
        
        # Seasonal analysis for long-term data
        if data_span_days >= 90:
            recommendations.append({
                'analysis_type': 'monthly',
                'priority': 'high',
                'reason': 'Monthly comparison reveals seasonal trends'
            })
        
        # Multi-year analysis
        if is_multi_year:
            recommendations.append({
                'analysis_type': 'heatmap_month_year',
                'priority': 'high',
                'reason': 'Multi-year heatmap shows long-term seasonal patterns'
            })
        
        # Peak analysis
        recommendations.append({
            'analysis_type': 'peak_analysis',
            'priority': 'medium',
            'reason': 'Critical for capacity planning and demand management'
        })
        
        # Load factor for efficiency analysis
        if data_span_days >= 30:
            recommendations.append({
                'analysis_type': 'load_factor',
                'priority': 'medium',
                'reason': 'System efficiency trends over time'
            })
        
        # Duration curve for capacity analysis
        recommendations.append({
            'analysis_type': 'duration_curve',
            'priority': 'medium',
            'reason': 'Capacity utilization and planning analysis'
        })
        
        return recommendations

    def advanced_profile_comparison(self, profile_ids: List[str], metrics: List[str], 
                                comparison_type: str = 'statistical') -> Dict[str, Any]:
        """Advanced multi-profile comparison"""
        try:
            # Load data for all profiles
            profiles_data = {}
            profiles_metadata = {}
            
            for profile_id in profile_ids:
                try:
                    df = self.analyzer.load_profile_data(profile_id)
                    if not df.empty:
                        profiles_data[profile_id] = df
                        profiles_metadata[profile_id] = self.get_profile_metadata(profile_id)
                except Exception as e:
                    logger.warning(f"Could not load profile {profile_id}: {e}")
            
            if len(profiles_data) < 2:
                raise ProcessingError("Insufficient valid profiles for comparison")
            
            # Perform comparison based on type
            if comparison_type == 'statistical':
                result = self._statistical_comparison(profiles_data, metrics)
            elif comparison_type == 'patterns':
                result = self._pattern_comparison(profiles_data, metrics)
            elif comparison_type == 'efficiency':
                result = self._efficiency_comparison(profiles_data, metrics)
            elif comparison_type == 'capacity':
                result = self._capacity_comparison(profiles_data, metrics)
            else:
                result = self._statistical_comparison(profiles_data, metrics)
            
            # Add metadata
            result['comparison_metadata'] = {
                'profile_count': len(profiles_data),
                'comparison_type': comparison_type,
                'metrics': metrics,
                'profiles_metadata': profiles_metadata,
                'generated_at': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in advanced profile comparison: {e}")
            raise

    def _statistical_comparison(self, profiles_data: Dict, metrics: List[str]) -> Dict[str, Any]:
        """Statistical comparison of profiles"""
        comparison = {
            'comparison_type': 'statistical',
            'profiles': {},
            'rankings': {},
            'correlations': {}
        }
        
        # Calculate statistics for each profile
        for profile_id, df in profiles_data.items():
            stats = self.analyzer.calculate_comprehensive_statistics(df, 'kW')
            comparison['profiles'][profile_id] = stats
        
        # Create rankings
        for metric in ['peak_load', 'average_load', 'load_factor', 'total_energy']:
            rankings = []
            for profile_id, stats in comparison['profiles'].items():
                if 'basic' in stats and metric in stats['basic']:
                    rankings.append({
                        'profile_id': profile_id,
                        'value': stats['basic'][metric]
                    })
            
            rankings.sort(key=lambda x: x['value'], reverse=True)
            comparison['rankings'][metric] = rankings
        
        return comparison

    def generate_intelligent_insights(self, profile_id: str) -> Dict[str, Any]:
        """Generate intelligent insights using pattern analysis"""
        try:
            df = self.analyzer.load_profile_data(profile_id)
            
            if df.empty:
                raise ProcessingError("No data available for insight generation")
            
            # Get comprehensive statistics
            statistics = self.analyzer.calculate_comprehensive_statistics(df, 'kW')
            
            # Analyze patterns
            patterns = self._analyze_load_patterns(df)
            
            # Data quality assessment
            quality = self._assess_profile_data_quality(df)
            
            # Generate insights
            insights = {
                'profile_id': profile_id,
                'key_findings': self._generate_key_findings(statistics, patterns, quality),
                'efficiency_insights': self._generate_efficiency_insights(statistics),
                'pattern_insights': self._generate_pattern_insights(patterns),
                'recommendations': self._generate_actionable_recommendations(statistics, patterns),
                'data_quality_insights': self._generate_quality_insights(quality),
                'generated_at': datetime.now().isoformat()
            }
            
            return insights
            
        except Exception as e:
            logger.exception(f"Error generating insights: {e}")
            raise

    def _generate_key_findings(self, statistics: Dict, patterns: Dict, quality: Dict) -> List[str]:
        """Generate key findings"""
        findings = []
        
        if 'basic' in statistics:
            basic = statistics['basic']
            
            # Peak demand finding
            peak_demand = basic.get('peak_load', 0)
            avg_demand = basic.get('average_load', 0)
            
            if peak_demand > 0 and avg_demand > 0:
                peak_ratio = peak_demand / avg_demand
                if peak_ratio > 3:
                    findings.append(f"High peak-to-average ratio ({peak_ratio:.1f}) indicates significant demand spikes")
                elif peak_ratio < 1.5:
                    findings.append(f"Low peak-to-average ratio ({peak_ratio:.1f}) shows stable demand patterns")
            
            # Load factor finding
            load_factor = basic.get('load_factor', 0)
            if load_factor > 80:
                findings.append(f"Excellent load factor ({load_factor:.1f}%) indicates optimal system utilization")
            elif load_factor < 30:
                findings.append(f"Low load factor ({load_factor:.1f}%) suggests underutilized capacity")
            
            # Energy consumption finding
            total_energy = basic.get('total_energy', 0)
            if total_energy > 0:
                findings.append(f"Total energy consumption: {total_energy:,.0f} kWh over analysis period")
        
        # Pattern findings
        daily_pattern = patterns.get('daily_pattern', 'Unknown')
        if daily_pattern != 'Unknown':
            findings.append(f"Load profile exhibits {daily_pattern.lower()} characteristics")
        
        # Quality findings
        quality_rating = quality.get('rating', 'Unknown')
        if quality_rating != 'Unknown':
            findings.append(f"Data quality assessment: {quality_rating} ({quality.get('overall_score', 0):.0f}/100)")
        
        return findings

    def _generate_actionable_recommendations(self, statistics: Dict, patterns: Dict) -> List[Dict[str, str]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if 'basic' in statistics:
            basic = statistics['basic']
            load_factor = basic.get('load_factor', 0)
            
            if load_factor < 50:
                recommendations.append({
                    'category': 'Efficiency',
                    'recommendation': 'Implement load balancing strategies to improve load factor',
                    'priority': 'high',
                    'expected_benefit': 'Reduced capacity requirements and improved system efficiency'
                })
            
            peak_ratio = basic.get('peak_to_average_ratio', 0)
            if peak_ratio > 2.5:
                recommendations.append({
                    'category': 'Peak Management',
                    'recommendation': 'Consider peak shaving measures during high demand periods',
                    'priority': 'high',
                    'expected_benefit': 'Reduced peak demand charges and infrastructure costs'
                })
        
        # Pattern-based recommendations
        daily_pattern = patterns.get('daily_pattern', 'Unknown')
        if daily_pattern == 'Residential':
            recommendations.append({
                'category': 'Demand Management',
                'recommendation': 'Implement time-of-use pricing to shift evening peak demand',
                'priority': 'medium',
                'expected_benefit': 'Improved load factor and reduced peak demand'
            })
        elif daily_pattern == 'Commercial':
            recommendations.append({
                'category': 'Energy Efficiency',
                'recommendation': 'Focus on HVAC optimization during business hours',
                'priority': 'medium',
                'expected_benefit': 'Reduced overall energy consumption and peak demand'
            })
        
        return recommendations











# Create the optimized blueprint
loadprofile_analysis_blueprint = LoadProfileAnalysisBlueprint()
loadprofile_analysis_bp = loadprofile_analysis_blueprint.blueprint

# Export for Flask app registration
def register_loadprofile_analysis_bp(app):
    """Register the load profile analysis blueprint with optimizations"""
    loadprofile_analysis_blueprint.register(app)