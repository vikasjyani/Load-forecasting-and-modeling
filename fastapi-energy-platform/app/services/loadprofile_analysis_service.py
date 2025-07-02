# fastapi-energy-platform/app/services/loadprofile_analysis_service.py
"""
Load Profile Analysis Service Layer for FastAPI
Handles all business logic for load profile analysis, comparison, and reporting.
"""
import os
import json
import pandas as pd
import numpy as np
import logging
import tempfile # For creating temporary files for downloads
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Assuming utilities and models are adapted and available in the new structure
from app.utils.load_profile_analyzer import LoadProfileAnalyzer # Needs to be Path-aware
from app.utils.constants import UNIT_FACTORS, VALIDATION_RULES # Check if these are still relevant as is
from app.utils.helpers import get_file_info, ensure_directory # Path-aware
from app.utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError # Custom exceptions

# FastAPI specific imports (if needed, e.g., for background tasks or specific response types)
# from fastapi import File, UploadFile # If handling uploads directly in service, though usually in router
# from fastapi.responses import FileResponse # For serving files

logger = logging.getLogger(__name__)

class LoadProfileAnalysisService:
    """
    Service layer for load profile analysis operations.
    Project paths should be injected or come from a central configuration.
    """

    def __init__(self, project_data_root: Path):
        # project_data_root is the base directory like 'user_projects_data/'
        self.project_data_root = project_data_root
        # LoadProfileAnalyzer needs to be initialized with a Path object for the specific project
        # This means analyzer might be better instantiated per-request or per-project context.
        # For now, this service will assume it's operating in the context of ONE project,
        # or the analyzer needs to be passed a project_name/project_path for each call.
        # Let's assume methods will take project_name as an argument.

        # Cache for expensive operations (in-memory, consider Redis for distributed setups)
        self._analysis_cache: Dict[str, Any] = {} # Key: project_name:profile_id:analysis_type:params_hash
        self._profile_cache: Dict[str, Any] = {}  # Key: project_name:profile_id
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl_seconds = 300  # 5 minutes

        self.supported_analysis_types = [
            'overview', 'peak_analysis', 'weekday_weekend', 'seasonal', 'monthly',
            'duration_curve', 'heatmap', 'load_factor', 'demand_profile', 'variability'
        ]
        self.export_formats = ['csv', 'xlsx', 'json'] # For exporting analysis results

    async def _get_project_specific_analyzer(self, project_name: str) -> LoadProfileAnalyzer:
        """Helper to get an analyzer instance for a specific project. (Async version)"""
        import asyncio # Ensure asyncio is imported
        project_path = self.project_data_root / project_name
        is_dir = await asyncio.to_thread(project_path.is_dir)
        if not is_dir:
            raise ResourceNotFoundError(f"Project '{project_name}' path not found or is not a directory: {project_path}")
        # Assuming LoadProfileAnalyzer constructor is lightweight or handles its own async I/O if any.
        # If its constructor does blocking I/O, it should also be wrapped:
        # return await asyncio.to_thread(LoadProfileAnalyzer, project_path)
        return LoadProfileAnalyzer(project_path)

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache_timestamps: return False
        return (datetime.now().timestamp() - self._cache_timestamps[cache_key]) < self._cache_ttl_seconds

    async def get_dashboard_data(self, project_name: str) -> Dict[str, Any]:
        """Get all data needed for the load profile analysis dashboard for a specific project."""
        try:
            analyzer = await self._get_project_specific_analyzer(project_name) # Added await
            profiles = await self.get_available_profiles(project_name) # now async

            total_profiles = len(profiles)
            total_size_mb = sum(p.get('file_info', {}).get('size_mb', 0.0) for p in profiles)
            # ... (other summary calculations from original method) ...

            return {
                'project_name': project_name,
                'available_profiles': profiles,
                'total_profiles': total_profiles,
                'total_size_mb': round(total_size_mb, 2),
                # ... (rest of the dashboard data structure)
                'available_units': list(UNIT_FACTORS.keys()),
                'analysis_types': self.supported_analysis_types, # Simplified for now
            }
        except Exception as e:
            logger.exception(f"Error getting dashboard data for project '{project_name}': {e}")
            # Consider raising a service-specific exception or returning an error structure
            raise ProcessingError(f"Failed to get dashboard data: {str(e)}")


    async def get_available_profiles(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all available load profiles with metadata for a specific project."""
        cache_key = f"profiles:{project_name}"
        if self._is_cache_valid(cache_key) and cache_key in self._profile_cache:
            return self._profile_cache[cache_key]

        import asyncio # Ensure asyncio is imported
        try:
            analyzer = await self._get_project_specific_analyzer(project_name) # Added await
            # Assuming analyzer.get_available_profiles() is synchronous. If it does I/O, use to_thread.
            profiles_raw = await asyncio.to_thread(analyzer.get_available_profiles)
            # profiles_raw = analyzer.get_available_profiles() # Old version

            enhanced_profiles = []
            # Create tasks for async operations within the loop
            validation_tasks = []
            profile_refs_for_tasks = []

            for profile_dict in profiles_raw:
                profile_id = profile_dict['profile_id']
                validation_tasks.append(self._quick_validate_profile_async(project_name, profile_id))
                profile_refs_for_tasks.append(profile_dict) # Keep ref to original dict

            validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)

            file_info_tasks = []
            profile_refs_for_file_info = []

            for i, profile_dict_ref in enumerate(profile_refs_for_tasks):
                profile_dict_ref['validation'] = validation_results[i] if not isinstance(validation_results[i], Exception) else {'valid': False, 'error': str(validation_results[i])}

                profile_id = profile_dict_ref['profile_id']
                # Path construction is sync and quick
                csv_path = analyzer.results_load_profiles_path / f"{profile_id}.csv"

                # Check existence and then get file info
                exists = await asyncio.to_thread(csv_path.exists)
                if exists:
                    file_info_tasks.append(get_file_info(csv_path)) # get_file_info is async
                    profile_refs_for_file_info.append(profile_dict_ref)
                else:
                    profile_dict_ref['file_info'] = {'exists': False, 'message': 'CSV file not found.'}

                enhanced_profiles.append(profile_dict_ref) # Add profile even if file info task is not run

            if file_info_tasks:
                 file_info_results = await asyncio.gather(*file_info_tasks, return_exceptions=True)
                 for i, profile_dict_fi_ref in enumerate(profile_refs_for_file_info):
                     profile_dict_fi_ref['file_info'] = file_info_results[i] if not isinstance(file_info_results[i], Exception) else {'exists': False, 'error': str(file_info_results[i])}

            # Sorting based on 'created_at' which might be in profile_dict or file_info
            # For now, assuming 'created_at' is part of the profile_dict from analyzer.get_available_profiles()
            enhanced_profiles.sort(key=lambda x: x.get('created_at', datetime.min.isoformat()), reverse=True)
            self._profile_cache[cache_key] = enhanced_profiles
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            return enhanced_profiles
        except Exception as e:
            logger.exception(f"Error getting available profiles for project '{project_name}': {e}")
            return [] # Or raise

    async def _quick_validate_profile_async(self, project_name: str, profile_id: str) -> Dict[str, Any]:
        """Asynchronously quick validation of a profile file."""
        import asyncio # Ensure asyncio is imported
        analyzer = await self._get_project_specific_analyzer(project_name) # await here
        csv_path = analyzer.results_load_profiles_path / f"{profile_id}.csv"

        exists = await asyncio.to_thread(csv_path.exists)
        if not exists:
            return {'valid': False, 'error': 'Profile CSV file not found.'}
        try:
            # Run pd.read_csv in a thread
            df_sample = await asyncio.to_thread(pd.read_csv, csv_path, nrows=10)
            # ... (rest of validation logic from original)
            has_demand = 'demand' in df_sample.columns
            has_datetime = any('time' in col.lower() or 'date' in col.lower() for col in df_sample.columns)
            valid = has_demand and has_datetime
            return {
                'valid': valid,
                'error': None if valid else "Missing essential columns (demand/datetime).",
                'has_data': not df_sample.empty,
                'has_demand_column': has_demand,
                'has_datetime_column': has_datetime
            }
        except Exception as e:
            return {'valid': False, 'error': f"Validation read error: {str(e)}"}

    async def get_profile_data(self, project_name: str, profile_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get profile data with filtering and processing for a specific project."""
        import asyncio # Ensure asyncio is imported
        try:
            analyzer = await self._get_project_specific_analyzer(project_name) # await
            df = await asyncio.to_thread(analyzer.load_profile_data, profile_id, filters) # Wrap blocking call

            if df.empty: raise ProcessingError("No data available after applying filters.")

            unit = filters.get('unit', 'kW') if filters else 'kW'
            # Assuming calculate_comprehensive_statistics is CPU-bound and potentially heavy
            statistics = await asyncio.to_thread(analyzer.calculate_comprehensive_statistics, df, unit)

            sample_df = df.head(min(1000, len(df)))
            # to_dict can be CPU intensive for large dataframes, but sample_df is limited.
            # If sample_df could still be very wide, this might be considered for to_thread.
            sample_data_records = sample_df.to_dict('records')

            # Convert Timestamps to ISO format strings for JSON serialization
            for record in sample_data_records:
                for key, value in record.items():
                    if isinstance(value, pd.Timestamp):
                        record[key] = value.isoformat()
                    elif pd.isna(value): # Handle NaN for JSON
                        record[key] = None


            return {
                'project_name': project_name,
                'profile_id': profile_id,
                'statistics': statistics,
                'data_sample': sample_data_records, # Renamed from 'data' for clarity
                'metadata': {
                    'total_records_after_filter': len(df),
                    'sample_records_count': len(sample_data_records),
                    'unit': unit,
                    'filters_applied': filters or {},
                    'columns': df.columns.tolist(),
                    'date_range': { # Ensure 'ds' column exists and is datetime
                        'start': df['ds'].min().isoformat() if 'ds' in df.columns and not df.empty else None,
                        'end': df['ds'].max().isoformat() if 'ds' in df.columns and not df.empty else None,
                    } if 'ds' in df.columns and pd.api.types.is_datetime64_any_dtype(df['ds']) else None,
                }
            }
        except Exception as e:
            logger.exception(f"Error getting profile data for '{profile_id}' in project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get profile data: {str(e)}")


    async def perform_analysis(self, project_name: str, profile_id: str, analysis_type: str,
                               parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a specific analysis on a profile for a given project."""
        # Caching key needs to include project_name
        params_hash = hash(json.dumps(parameters, sort_keys=True)) if parameters else "no_params"
        cache_key = f"analysis:{project_name}:{profile_id}:{analysis_type}:{params_hash}"

        if self._is_cache_valid(cache_key) and cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]

        if analysis_type not in self.supported_analysis_types:
            raise ValidationError(f"Unsupported analysis type: {analysis_type}")

        import asyncio # Ensure asyncio is imported
        try:
            analyzer = await self._get_project_specific_analyzer(project_name) # await
            filters = parameters.get('filters', {}) if parameters else {}
            df = await asyncio.to_thread(analyzer.load_profile_data, profile_id, filters) # Wrap blocking call

            if df.empty: raise ProcessingError("No data for analysis after filters.")

            unit = parameters.get('unit', 'kW') if parameters else 'kW'

            # Assuming generate_analysis_data is CPU-bound and potentially heavy
            result_data = await asyncio.to_thread(analyzer.generate_analysis_data, df, analysis_type, unit)

            # Add metadata
            result_data['metadata'] = {
                'project_name': project_name, 'profile_id': profile_id, 'analysis_type': analysis_type,
                'unit': unit, 'data_points_analyzed': len(df),
                'parameters_used': parameters or {}, 'generated_at': datetime.now().isoformat()
            }
            self._analysis_cache[cache_key] = result_data
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            return result_data
        except Exception as e:
            logger.exception(f"Error in '{analysis_type}' for '{profile_id}' in project '{project_name}': {e}")
            raise ProcessingError(f"Analysis failed: {str(e)}")

    # ... Other methods like compare_profiles, benchmark_profile, export_analysis_results etc.
    # would follow a similar pattern:
    # 1. Accept project_name.
    # 2. Instantiate or get a project-specific LoadProfileAnalyzer.
    # 3. Use `asyncio.to_thread` for blocking calls within the analyzer if they are not async.
    # 4. Adapt return structures for FastAPI responses (e.g., using Pydantic models).
    # 5. For file exports, instead of Flask's send_file, use FastAPI's FileResponse.
    #    This would typically be handled in the router/endpoint, not directly in the service.
    #    The service might return a Path to the temporary file.

    async def export_analysis_results(self, project_name: str, profile_id: str,
                                      export_format: str = 'xlsx',
                                      analysis_types: Optional[List[str]] = None) -> Path:
        """
        Exports analysis results to a temporary file and returns its path.
        The router will then use this path with FileResponse.
        """
        if export_format not in self.export_formats:
            raise ValidationError(f"Unsupported export format: {export_format}")

        analyzer = await self._get_project_specific_analyzer(project_name) # await
        analysis_types_to_export = analysis_types or ['overview', 'statistical'] # Default export

        export_data_dict: Dict[str, Any] = {
            'profile_id': profile_id,
            'project_name': project_name,
            'export_format': export_format,
            'export_timestamp': datetime.now().isoformat(),
            'analysis_results': {}
        }

        for analysis_type in analysis_types_to_export:
            try:
                # Assuming perform_analysis is adapted to be async
                # This might need parameters if perform_analysis expects them
                analysis_result = await self.perform_analysis(project_name, profile_id, analysis_type)
                export_data_dict['analysis_results'][analysis_type] = analysis_result
            except Exception as e:
                logger.warning(f"Could not retrieve '{analysis_type}' for export: {e}")
                export_data_dict['analysis_results'][analysis_type] = {'error': str(e)}

        # Create temporary file (FastAPI's BackgroundTask can clean this up)
        # Or the router that calls this can handle cleanup after sending the response.
        # suffix = f".{export_format}"
        # temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='w' if export_format == 'json' else 'wb')

        # temp_file_path = Path(temp_file.name)
        # temp_file.close() # Close it so pandas can write to it

        # This is a simplified export logic, actual pandas-to-file needs to be here.
        # For now, let's assume a placeholder function _create_export_file_sync exists and works with Path.
        # temp_file_path = await asyncio.to_thread(
        #     self._create_export_file_sync_placeholder,
        #     export_data_dict,
        #     export_format,
        #     analyzer.project_path # Pass base path for context if needed by export func
        # )
        # Placeholder: create an empty temp file for structure
        fd, temp_file_path_str = tempfile.mkstemp(suffix=f".{export_format}")
        os.close(fd)
        temp_file_path = Path(temp_file_path_str)
        # In a real scenario, you'd write the actual content here based on format
        logger.info(f"Generated export file (placeholder content) at: {temp_file_path}")


        return temp_file_path # Return the Path object


print("Defining load profile analysis service for FastAPI... (merged and adapted)")
