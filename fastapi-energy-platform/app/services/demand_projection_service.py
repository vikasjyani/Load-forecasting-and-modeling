# fastapi-energy-platform/app/services/demand_projection_service.py
"""
Demand Projection Service Layer for FastAPI
Handles all business logic for demand forecasting and projection.
"""
import os
import json
import asyncio # For async job management if needed, or use background tasks
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Assuming these utilities are adapted and available in the new structure
from app.utils.constants import JOB_STATUS, FORECAST_MODELS, VALIDATION_RULES, ERROR_MESSAGES
from app.utils.data_loading import input_demand_data, validate_input_file # These need to be Path-aware
from app.utils.demand_utils import (
    handle_nan_values, safe_numeric_conversion, create_summary, # create_summary needs review
    # validate_project_path, # Project path validation will be part of service constructor/config
    validate_year_range
)
# from app.utils.response_utils import ... # Response construction will be handled by routers

# This model import needs to be updated if its location or structure changes
# from app.models.forecasting import Main_forecasting_function # Assuming this is the core ML model function
# Corrected import path:
from models.forecasting import Main_forecasting_function


# FastAPI specific imports
# from fastapi import BackgroundTasks # For running forecasts in the background

logger = logging.getLogger(__name__)

@dataclass
class ForecastJobConfig:
    """Configuration for a forecast job."""
    scenario_name: str
    target_year: int
    exclude_covid_years: bool
    sector_configs: Dict[str, Any] # Key: sector_name, Value: sector-specific config
    # Optional fields with defaults
    detailed_configuration: Dict[str, Any] = field(default_factory=dict) # Global/advanced settings
    request_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SectorProcessingResult:
    """Result of processing a single sector."""
    sector_name: str
    status: str  # 'success', 'existing_data', 'failed'
    message: str
    models_used: List[str] = field(default_factory=list)
    error: Optional[str] = None
    processing_time_seconds: float = 0.0
    configuration_used: Dict[str, Any] = field(default_factory=dict)


class ForecastJobManager:
    """
    Manages forecast jobs.
    In a distributed FastAPI setup, this might be backed by Redis or a database.
    For simplicity, using an in-memory dict with asyncio.Lock for async safety.
    """
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock() # For async operations
        self.cleanup_task: Optional[asyncio.Task] = None
        # self._start_cleanup_task() # Start cleanup if running as part of a long-lived app instance

    # def _start_cleanup_task(self):
    #     if self.cleanup_task is None or self.cleanup_task.done():
    #         self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
    #         logger.info("Forecast job cleanup task started.")

    # async def _periodic_cleanup(self):
    #     while True:
    #         await asyncio.sleep(300)  # Run every 5 minutes
    #         await self._cleanup_old_jobs()

    async def create_job(self, config: ForecastJobConfig, **kwargs) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        async with self.lock:
            job_data = {
                'id': job_id,
                'status': JOB_STATUS['STARTING'],
                'progress': 0,
                'current_sector': None,
                'processed_sectors_count': 0,
                'total_sectors': len(config.sector_configs),
                'scenario_name': config.scenario_name,
                'target_year': config.target_year,
                'start_time_unix': time.time(),
                'last_update_unix': time.time(),
                'result_summary': None, # Overall summary when done
                'error_message': None,
                'current_message': 'Initializing forecast job...',
                'configuration_snapshot': asdict(config), # Store the config used
                'sector_results': [], # List of SectorProcessingResult
                'progress_history': [], # List of progress updates
                'detailed_log': [], # More detailed log entries
                **kwargs
            }
            self.jobs[job_id] = job_data
            logger.info(f"Created forecast job {job_id} for scenario '{config.scenario_name}'.")
            return job_data

    async def update_job(self, job_id: str, **updates: Any) -> bool:
        async with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Attempted to update non-existent job: {job_id}")
                return False
            job = self.jobs[job_id]
            job.update(updates)
            job['last_update_unix'] = time.time()

            if 'message' in updates: # Add to detailed log
                log_entry = {'timestamp': datetime.now().isoformat(), 'message': updates['message']}
                job['detailed_log'].append(log_entry)
                if len(job['detailed_log']) > 100: job['detailed_log'] = job['detailed_log'][-50:]

            if 'progress' in updates and 'current_message' in updates: # Add to progress history
                 prog_entry = {
                     'timestamp': datetime.now().isoformat(),
                     'progress': updates['progress'],
                     'message': updates['current_message']
                 }
                 job['progress_history'].append(prog_entry)
                 if len(job['progress_history']) > 50: job['progress_history'] = job['progress_history'][-25:]
            return True

    async def add_sector_result(self, job_id: str, result: SectorProcessingResult) -> bool:
        async with self.lock:
            if job_id not in self.jobs: return False
            job = self.jobs[job_id]
            job['sector_results'].append(asdict(result))
            job['processed_sectors_count'] = len(job['sector_results'])
            return True

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with self.lock:
            job_dict = self.jobs.get(job_id)
            if not job_dict: return None

            # Add some computed fields for easier frontend consumption
            computed_job = job_dict.copy()
            start_time = computed_job.get('start_time_unix', 0)
            computed_job['start_time_iso'] = datetime.fromtimestamp(start_time).isoformat()
            computed_job['last_update_iso'] = datetime.fromtimestamp(computed_job.get('last_update_unix', 0)).isoformat()
            elapsed_seconds = time.time() - start_time
            computed_job['elapsed_time_seconds'] = round(elapsed_seconds, 2)

            progress = computed_job.get('progress', 0)
            if progress > 0 and computed_job.get('status') == JOB_STATUS['RUNNING']:
                estimated_total_time = (elapsed_seconds / progress) * 100
                computed_job['estimated_remaining_seconds'] = round(max(0, estimated_total_time - elapsed_seconds), 2)

            return computed_job

    async def cancel_job(self, job_id: str) -> bool:
        # Actual cancellation of a running thread/task is complex.
        # This marks it for cancellation; the running task should check this status.
        return await self.update_job(job_id, status=JOB_STATUS['CANCELLED'], current_message='Job cancelled by user.')

    async def _cleanup_old_jobs(self):
        async with self.lock:
            current_time = time.time()
            jobs_to_remove = []
            for job_id, job in self.jobs.items():
                last_update = job.get('last_update_unix', 0)
                # Remove jobs completed/failed/cancelled over an hour ago
                if job.get('status') in [JOB_STATUS['COMPLETED'], JOB_STATUS['FAILED'], JOB_STATUS['CANCELLED']] \
                   and (current_time - last_update > 3600):
                    jobs_to_remove.append(job_id)
                # Mark very old running jobs as stalled/failed (e.g., > 4 hours)
                elif job.get('status') == JOB_STATUS['RUNNING'] and (current_time - last_update > 14400):
                    logger.warning(f"Job {job_id} appears stalled, marking as FAILED.")
                    job['status'] = JOB_STATUS['FAILED']
                    job['error_message'] = "Job stalled and timed out."
            for job_id_rem in jobs_to_remove:
                del self.jobs[job_id_rem]
                logger.info(f"Cleaned up old job: {job_id_rem}")

# Global instance (consider how this is managed in a multi-worker FastAPI setup)
# For multi-worker, a shared store like Redis would be needed.
forecast_job_manager = ForecastJobManager()


class DemandProjectionService:
    def __init__(self, project_data_root: Path):
        self.project_data_root = project_data_root # Base directory for all projects
        # Cache for loaded input data to avoid frequent re-reads for the same project
        self._project_input_data_cache: Dict[str, Tuple[Any, float]] = {} # project_name -> (data, timestamp)
        self._cache_ttl_seconds = 300  # 5 minutes

    def _get_project_input_file_path(self, project_name: str) -> Path:
        # Ensure project_name is safe for path construction
        safe_project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
        return self.project_data_root / safe_project_name / "inputs" / "input_demand_file.xlsx"

    async def _load_input_data(self, project_name: str, force_reload: bool = False) -> Tuple[List[str], List[str], Dict, Dict, Any]:
        """Loads input data for a project, with caching."""
        input_file_path = self._get_project_input_file_path(project_name)
        cache_key = project_name

        cached_item = self._project_input_data_cache.get(cache_key)
        if not force_reload and cached_item:
            data, timestamp = cached_item
            if time.time() - timestamp < self._cache_ttl_seconds:
                logger.debug(f"Using cached input data for project '{project_name}'.")
                return data

        path_exists = await asyncio.to_thread(input_file_path.exists)
        if not path_exists:
            raise FileNotFoundError(f"Input file not found for project '{project_name}': {input_file_path}")

        # Adapt validate_input_file and input_demand_data to be async or run in threadpool
        # These functions use pandas which is synchronous, so we run them in a thread pool.
        try:
            validation_result = await asyncio.to_thread(validate_input_file, str(input_file_path))
            if not validation_result['valid']:
                raise ValueError(f"Input file validation failed for {input_file_path}: {'; '.join(validation_result['errors'])}")
            for warning in validation_result.get('warnings', []):
                logger.warning(f"Input file warning for project '{project_name}', file {input_file_path}: {warning}")

            data_tuple = await asyncio.to_thread(input_demand_data, str(input_file_path))
        except Exception as e:
            logger.error(f"Failed to load or validate input data for project '{project_name}' from {input_file_path}: {e}", exc_info=True)
            raise ValueError(f"Error processing input file for project '{project_name}': {str(e)}")


        self._project_input_data_cache[cache_key] = (data_tuple, time.time())
        logger.info(f"Loaded input data for project '{project_name}'.")
        return data_tuple

    async def get_input_data_summary(self, project_name: str) -> Dict[str, Any]:
        """Gets a summary of the input data for a project."""
        try:
            input_file_path = self._get_project_input_file_path(project_name)
            if not await asyncio.to_thread(input_file_path.exists):
                return {
                    'error': f"Input file not found: {input_file_path.name}",
                    'project_name': project_name,
                    'data_available': False,
                    'message': f"Input file '{input_file_path.name}' does not exist for project '{project_name}'. Please upload it."
                }

            sectors, missing_sectors, param_dict, sector_data_map, aggregated_ele = await self._load_input_data(project_name)

            file_stat = await asyncio.to_thread(input_file_path.stat)
            data_quality = self._assess_data_quality(sectors, missing_sectors, sector_data_map)

            return {
                'project_name': project_name,
                'data_available': True,
                'sectors_available': sectors,
                'sectors_missing_in_data': missing_sectors, # Sectors defined in file but sheets missing
                'parameters_from_file': param_dict,
                'aggregated_data_summary': {
                    'num_rows': len(aggregated_ele),
                    'num_columns': len(aggregated_ele.columns),
                    'years': aggregated_ele['Year'].tolist() if 'Year' in aggregated_ele.columns and not aggregated_ele.empty else [],
                } if not aggregated_ele.empty else {"message": "Aggregated data not available or empty."},
                'input_file_metadata': {
                    'name': input_file_path.name,
                    'size_kb': round(file_stat.st_size / 1024, 2),
                    'last_modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                },
                'data_quality_assessment': data_quality,
                 # For compatibility with Flask blueprint's expectation for _render_main_page context
                'sectors': sectors, # Duplicate of sectors_available for now
                'parameters': param_dict, # Duplicate of parameters_from_file
            }
        except FileNotFoundError:
             return {'error': f"Input file not found for project '{project_name}'.", 'project_name': project_name, 'data_available': False}
        except ValueError as ve: # Catch validation errors from _load_input_data
            return {'error': str(ve), 'project_name': project_name, 'data_available': False}
        except Exception as e:
            logger.exception(f"Error getting input data summary for project '{project_name}': {e}")
            return {'error': f"An unexpected error occurred: {str(e)}", 'project_name': project_name, 'data_available': False}

    def _assess_data_quality(self, sectors_available: List[str], sectors_missing: List[str], sector_data_map: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to assess overall data quality."""
        total_defined_sectors = len(sectors_available) + len(sectors_missing)
        if total_defined_sectors == 0:
            return {'quality_score': 0, 'rating': 'No Data', 'issues': ['No sectors defined in input file.']}

        available_actual_data_count = len(sectors_available) # Sectors with sheets

        completeness_score = (available_actual_data_count / total_defined_sectors) * 100 if total_defined_sectors > 0 else 0

        rating = "Poor"
        if completeness_score >= 95: rating = "Excellent"
        elif completeness_score >= 80: rating = "Good"
        elif completeness_score >= 60: rating = "Fair"

        issues = []
        if sectors_missing:
            issues.append(f"{len(sectors_missing)} sector sheets are missing: {', '.join(sectors_missing)}.")

        for sec_name in sectors_available:
            df = sector_data_map.get(sec_name)
            if df is None or df.empty:
                issues.append(f"Sector '{sec_name}' sheet is empty or unreadable.")
                continue
            if 'Electricity' not in df.columns:
                 issues.append(f"Sector '{sec_name}' is missing 'Electricity' column.")
            if 'Year' not in df.columns:
                 issues.append(f"Sector '{sec_name}' is missing 'Year' column.")
            # Could add more checks: NaN values, data types, year continuity etc.

        return {
            'quality_score': round(completeness_score, 2),
            'rating': rating,
            'total_defined_sectors': total_defined_sectors,
            'sectors_with_data': available_actual_data_count,
            'issues': issues if issues else ["Basic checks passed. Further validation might be needed."]
        }


    async def get_sector_data(self, project_name: str, sector_name: str) -> Dict[str, Any]:
        """Gets detailed data for a specific sector within a project."""
        try:
            _, _, _, sector_data_map, _ = await self._load_input_data(project_name) # sectors, missing_sectors, param_dict, sector_data_map, aggregated_ele
            if sector_name not in sector_data_map:
                raise ValueError(f"Sector '{sector_name}' not found or has no data in project '{project_name}'.")

            df = sector_data_map[sector_name]
            if df.empty:
                 return {
                    'project_name': project_name,
                    'sector_name': sector_name,
                    'message': 'Sector data is empty.',
                    'columns': [],
                    'data_records': [],
                    'data_summary': {}
                 }

            # Convert all data to JSON serializable types (e.g. int, float, str, handle NaNs)
            df_serializable = df.copy()
            for col in df_serializable.columns:
                if pd.api.types.is_numeric_dtype(df_serializable[col]):
                    df_serializable[col] = df_serializable[col].apply(lambda x: None if pd.isna(x) else (int(x) if x == int(x) else float(x)))
                else:
                    df_serializable[col] = df_serializable[col].apply(lambda x: None if pd.isna(x) else str(x))


            return {
                'project_name': project_name,
                'sector_name': sector_name,
                'columns': df_serializable.columns.tolist(),
                'data_records': df_serializable.to_dict('records'),
                'data_summary': {
                    'num_rows': len(df_serializable),
                    'year_range': (int(df['Year'].min()), int(df['Year'].max())) if 'Year' in df.columns and not df.empty and df['Year'].notna().all() else "N/A",
                    'electricity_mean': float(df['Electricity'].mean()) if 'Electricity' in df.columns and not df.empty and df['Electricity'].notna().all() else "N/A"
                }
            }
        except FileNotFoundError:
             raise ValueError(f"Input file not found for project '{project_name}'. Cannot get sector data.") # More specific error
        except ValueError as ve: # Catch specific errors like sector not found
            logger.warning(f"Value error getting sector data for '{sector_name}' in project '{project_name}': {ve}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error getting sector data for '{sector_name}' in project '{project_name}': {e}")
            # Raise a generic error or a custom app exception
            raise Exception(f"An unexpected error occurred while fetching data for sector '{sector_name}'.")


    async def get_independent_variables(self, project_name: str, sector_name: str) -> Dict[str, Any]:
        """
        Determines suitable independent variables for a given sector's electricity consumption data.
        Ported and adapted from Flask blueprint's expected service functionality.
        """
        try:
            _, _, _, sector_data_map, _ = await self._load_input_data(project_name)
            if sector_name not in sector_data_map:
                raise ValueError(f"Sector '{sector_name}' not found in project '{project_name}'.")

            df = sector_data_map[sector_name]
            if df.empty or 'Electricity' not in df.columns:
                return {
                    "sector_name": sector_name,
                    "suitable_variables": [],
                    "all_variables": [],
                    "analysis_details": "Dataframe is empty or 'Electricity' column is missing."
                }

            all_variables = [col for col in df.columns if col not in ['Year', 'Electricity']]
            suitable_variables = []
            analysis_details = {}

            for var in all_variables:
                col_data = df[var]
                details = {}
                if col_data.isnull().all():
                    details['status'] = 'unsuitable'
                    details['reason'] = 'All values are null.'
                elif not pd.api.types.is_numeric_dtype(col_data):
                    details['status'] = 'unsuitable'
                    details['reason'] = f'Non-numeric data type ({col_data.dtype}).'
                else:
                    # Attempt conversion just in case some numerics are objects
                    try:
                        numeric_col_data = pd.to_numeric(col_data, errors='coerce')
                        if numeric_col_data.isnull().all():
                             details['status'] = 'unsuitable'
                             details['reason'] = 'All values are null after numeric conversion.'
                        elif numeric_col_data.nunique() <= 1: # Also check for constant values
                            details['status'] = 'unsuitable'
                            details['reason'] = 'Variable has no variance (constant or mostly null).'
                        elif numeric_col_data.isnull().sum() > 0.3 * len(numeric_col_data): # Example: >30% missing
                            details['status'] = 'check_caution'
                            details['reason'] = f'{numeric_col_data.isnull().sum()} missing values ({round(numeric_col_data.isnull().mean() * 100, 1)}%).'
                            suitable_variables.append(var) # Still add, but with caution
                        else:
                            details['status'] = 'suitable'
                            details['reason'] = 'Numeric with sufficient data.'
                            suitable_variables.append(var)
                    except Exception as e_conv:
                        details['status'] = 'unsuitable'
                        details['reason'] = f'Error during numeric conversion: {str(e_conv)}'
                analysis_details[var] = details

            return {
                "project_name": project_name,
                "sector_name": sector_name,
                "suitable_variables": suitable_variables,
                "all_variables": all_variables,
                "analysis_details": analysis_details,
                "message": f"Found {len(suitable_variables)} suitable variables out of {len(all_variables)} for sector '{sector_name}'."
            }

        except FileNotFoundError:
             raise ValueError(f"Input file not found for project '{project_name}'.")
        except ValueError as ve:
            logger.warning(f"Value error getting independent variables for '{sector_name}' in project '{project_name}': {ve}")
            raise
        except Exception as e:
            logger.exception(f"Error getting independent variables for '{sector_name}' in project '{project_name}': {e}")
            raise Exception(f"An unexpected error occurred while analyzing variables for sector '{sector_name}'.")


    async def get_correlation_data(self, project_name: str, sector_name: str) -> Dict[str, Any]:
        """
        Calculates correlation of variables with 'Electricity' for a sector.
        Ported and adapted from Flask blueprint's expected service functionality.
        """
        try:
            _, _, _, sector_data_map, _ = await self._load_input_data(project_name)
            if sector_name not in sector_data_map:
                raise ValueError(f"Sector '{sector_name}' not found in project '{project_name}'.")

            df = sector_data_map[sector_name].copy() # Use a copy for modifications

            if df.empty or 'Electricity' not in df.columns:
                 return {
                    "project_name": project_name,
                    "sector_name": sector_name,
                    "error": "Dataframe is empty or 'Electricity' column is missing."
                }

            # Ensure 'Electricity' is numeric and handle NaNs
            df['Electricity'] = pd.to_numeric(df['Electricity'], errors='coerce')
            df.dropna(subset=['Electricity'], inplace=True) # Remove rows where electricity is NaN for correlation

            numeric_cols_for_corr = ['Electricity']
            potential_vars = [col for col in df.columns if col not in ['Year', 'Electricity']]

            for var in potential_vars:
                if pd.api.types.is_numeric_dtype(df[var]):
                    df[var] = pd.to_numeric(df[var], errors='coerce') # Ensure it's float/int
                    numeric_cols_for_corr.append(var)
                # else: logger.debug(f"Skipping non-numeric column {var} for correlation in sector {sector_name}")

            if len(numeric_cols_for_corr) <= 1 : # Only 'Electricity' or no numeric vars
                return {
                    "project_name": project_name,
                    "sector_name": sector_name,
                    "message": "Not enough numeric variables for correlation analysis.",
                    "correlation_matrix": {},
                    "electricity_correlations": {}
                }

            correlation_matrix = df[numeric_cols_for_corr].corr()
            # Convert NaN correlations to None for JSON serialization
            correlation_matrix_serializable = correlation_matrix.where(pd.notnull(correlation_matrix), None)

            electricity_correlations = correlation_matrix_serializable['Electricity'].drop('Electricity', errors='ignore').to_dict()

            return {
                "project_name": project_name,
                "sector_name": sector_name,
                "correlation_matrix": correlation_matrix_serializable.to_dict(),
                "electricity_correlations": electricity_correlations,
                "variables_included": numeric_cols_for_corr
            }

        except FileNotFoundError:
             raise ValueError(f"Input file not found for project '{project_name}'.")
        except ValueError as ve:
            logger.warning(f"Value error getting correlation data for '{sector_name}' in project '{project_name}': {ve}")
            raise
        except Exception as e:
            logger.exception(f"Error calculating correlation for '{sector_name}' in project '{project_name}': {e}")
            raise Exception(f"An unexpected error occurred during correlation analysis for sector '{sector_name}'.")

    async def get_chart_data(self, project_name: str, sector_name: str) -> Dict[str, Any]:
        """
        Prepares data formatted for chart display (e.g., historical trends).
        If sector_name is 'aggregated', it provides aggregated data.
        """
        try:
            _, _, _, sector_data_map, aggregated_ele_df = await self._load_input_data(project_name)

            if sector_name.lower() == 'aggregated':
                if aggregated_ele_df.empty:
                    return {"type": "aggregated", "error": "Aggregated data is not available or empty."}

                df_agg_serializable = aggregated_ele_df.copy()
                for col in df_agg_serializable.columns: # Ensure JSON serializable
                     df_agg_serializable[col] = df_agg_serializable[col].apply(lambda x: None if pd.isna(x) else (int(x) if x == int(x) else (float(x) if isinstance(x, (float, int)) else str(x) )))

                datasets = []
                for col in df_agg_serializable.columns:
                    if col.lower() != 'year':
                        datasets.append({
                            "label": col,
                            "data": df_agg_serializable[col].tolist()
                        })
                return {
                    "project_name": project_name,
                    "type": "aggregated",
                    "sector_name": "Aggregated",
                    "years": df_agg_serializable['Year'].tolist() if 'Year' in df_agg_serializable.columns else [],
                    "datasets": datasets,
                    "total_consumption": df_agg_serializable.sum(axis=1, numeric_only=True).tolist() if not df_agg_serializable.empty else [] # Example, needs refinement
                }

            if sector_name not in sector_data_map:
                raise ValueError(f"Sector '{sector_name}' not found in project '{project_name}'.")

            df_sector = sector_data_map[sector_name]
            if df_sector.empty:
                return {"type": "sector", "sector_name": sector_name, "error": "Sector data is empty."}

            df_sec_serializable = df_sector.copy()
            for col in df_sec_serializable.columns: # Ensure JSON serializable
                 df_sec_serializable[col] = df_sec_serializable[col].apply(lambda x: None if pd.isna(x) else (int(x) if x == int(x) else (float(x) if isinstance(x, (float, int)) else str(x) )))


            chart_datasets = []
            if 'Electricity' in df_sec_serializable.columns:
                chart_datasets.append({
                    "label": "Electricity",
                    "data": df_sec_serializable['Electricity'].tolist()
                })
            # Could add other variables to chart_datasets if needed

            return {
                "project_name": project_name,
                "type": "sector",
                "sector_name": sector_name,
                "years": df_sec_serializable['Year'].tolist() if 'Year' in df_sec_serializable.columns else [],
                "datasets": chart_datasets
            }
        except FileNotFoundError:
             raise ValueError(f"Input file not found for project '{project_name}'.")
        except ValueError as ve:
            logger.warning(f"Value error getting chart data for '{sector_name}' in project '{project_name}': {ve}")
            raise
        except Exception as e:
            logger.exception(f"Error preparing chart data for '{sector_name}' in project '{project_name}': {e}")
            raise Exception(f"An unexpected error occurred while preparing chart data for sector '{sector_name}'.")


    async def validate_forecast_config(self, project_name: str, config: ForecastJobConfig) -> List[str]:
        """Validates the forecast configuration against project data."""
        errors = []
        if not config.scenario_name or len(config.scenario_name.strip()) < 2:
            errors.append("Scenario name must be at least 2 characters long.")
        # Basic scenario name validation (can be enhanced)
        if not all(c.isalnum() or c.isspace() or c in ('-', '_') for c in config.scenario_name):
            errors.append("Scenario name contains invalid characters.")

        if not (VALIDATION_RULES['MIN_YEAR'] <= config.target_year <= VALIDATION_RULES['MAX_YEAR']):
            errors.append(f"Target year must be between {VALIDATION_RULES['MIN_YEAR']} and {VALIDATION_RULES['MAX_YEAR']}.")

        if not config.sector_configs: errors.append("No sector configurations provided.")

        try:
            _, _, param_dict, sector_data_map, _ = await self._load_input_data(project_name)
            data_end_year = param_dict.get('End_Year')
            if data_end_year and isinstance(data_end_year, (int, float)) and config.target_year <= data_end_year :
                 errors.append(f"Target year ({config.target_year}) should be after data end year ({int(data_end_year)}).")


            for sec_name, sec_cfg in config.sector_configs.items():
                if sec_name not in sector_data_map:
                    errors.append(f"Sector '{sec_name}' not found in input data for project '{project_name}'.")
                    continue
                models = sec_cfg.get('models', [])
                if not models: errors.append(f"No models specified for sector '{sec_name}'.")
                for model in models:
                    if model not in FORECAST_MODELS: errors.append(f"Invalid model '{model}' for sector '{sec_name}'.")

                # Validate MLR independent variables
                if 'MLR' in models:
                    mlr_vars = sec_cfg.get('independentVars', [])
                    if not mlr_vars:
                        errors.append(f"MLR model selected for sector '{sec_name}' but no independent variables provided.")
                    else:
                        sector_df = sector_data_map.get(sec_name)
                        if sector_df is not None:
                            for var in mlr_vars:
                                if var not in sector_df.columns:
                                    errors.append(f"Independent variable '{var}' for MLR in sector '{sec_name}' not found in sector data.")
                                elif sector_df[var].isnull().all():
                                    errors.append(f"Independent variable '{var}' for MLR in sector '{sec_name}' contains all null values.")


                # Validate WAM window size
                if 'WAM' in models:
                    window_size_str = sec_cfg.get('windowSize')
                    if window_size_str is None:
                        errors.append(f"WAM model selected for sector '{sec_name}' but no window size provided.")
                    else:
                        try:
                            window_size = int(window_size_str)
                            if not (VALIDATION_RULES['MIN_WAM_WINDOW'] <= window_size <= VALIDATION_RULES['MAX_WAM_WINDOW']):
                                errors.append(f"WAM window size for sector '{sec_name}' must be between {VALIDATION_RULES['MIN_WAM_WINDOW']} and {VALIDATION_RULES['MAX_WAM_WINDOW']}.")
                        except ValueError:
                             errors.append(f"Invalid window size '{window_size_str}' for WAM in sector '{sec_name}'. Must be an integer.")
        except FileNotFoundError:
            errors.append(f"Input data file not found for project '{project_name}'. Cannot validate configuration.")
        except ValueError as ve: # Catch data loading/validation errors
             errors.append(f"Error loading input data for validation: {str(ve)}")
        except Exception as e:
            logger.exception(f"Unexpected error during forecast config validation for project '{project_name}': {e}")
            errors.append(f"An unexpected error occurred during validation: {str(e)}")
        return errors

    async def execute_forecast_async(self, project_name: str, config: ForecastJobConfig, job_id: str):
        """
        The core forecasting logic, designed to be run in the background.
        This method will be called by a BackgroundTask in the API route.
        """
        project_input_file = self._get_project_input_file_path(project_name)
        project_results_dir = self.project_data_root / project_name / "results" / "demand_projection" / config.scenario_name

        # Async directory creation
        await asyncio.to_thread(project_results_dir.mkdir, parents=True, exist_ok=True)

        try:
            await forecast_job_manager.update_job(job_id, status=JOB_STATUS['RUNNING'], progress=5, current_message='Loading input data...')

            # Assuming _load_input_data is preferred. If direct call is needed, make it async.
            # For this review, let's assume data is loaded via _load_input_data if possible,
            # or if not, this call needs to be async. For now, making it async.
            sectors, _, param_dict, sector_data_map, _ = await asyncio.to_thread(
                input_demand_data, str(project_input_file)
            )
            # A better approach might be:
            # sectors, _, param_dict, sector_data_map, _ = await self._load_input_data(project_name, force_reload=True)


            await forecast_job_manager.update_job(job_id, progress=10, current_message='Data loaded. Saving configuration...')
            # Save full configuration to a file in project_results_dir
            full_config_data = {
                "job_config": asdict(config),
                "data_parameters_from_file": param_dict,
                "available_sectors_in_file": sectors,
                "execution_timestamp": datetime.now().isoformat()
            }

            def _dump_json_sync():
                with open(project_results_dir / "forecast_run_config.json", "w") as f:
                    json.dump(full_config_data, f, indent=2)
            await asyncio.to_thread(_dump_json_sync)

            all_sector_results: List[SectorProcessingResult] = []
            total_configured_sectors = len(config.sector_configs)

            # Get the current event loop to schedule job updates from the thread
            # This loop should be the one FastAPI's BackgroundTask is running on.
            try:
                main_event_loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error(f"Job {job_id}: Could not get running event loop. Progress updates might fail.")
                main_event_loop = None # Continue, but progress updates from thread might not work as expected

            for i, (sec_name, sec_cfg) in enumerate(config.sector_configs.items()):
                # Check for cancellation before processing each sector
                current_job_status_obj = await forecast_job_manager.get_job(job_id)
                if current_job_status_obj and current_job_status_obj.get('status') == JOB_STATUS['CANCELLED']:
                    logger.info(f"Job {job_id}: Detected cancellation before processing sector '{sec_name}'. Halting forecast execution.")
                    await forecast_job_manager.update_job(job_id, current_message="Forecast execution halted due to cancellation request.")
                    # No need to update to CANCELLED again if already marked by cancel_job,
                    # but ensure final state reflects it if loop breaks here.
                    # If loop terminates early, the final summary might be incomplete or not generated.
                    # Consider how to handle this - perhaps a specific "CANCELLED_IN_PROGRESS" state
                    # or just ensure the final summary reflects partial work.
                    # For now, just break and let the job remain in CANCELLED state.
                    break # Exit the sector processing loop

                sector_start_time = time.time()
                current_sector_message_prefix = f"Processing sector {i+1}/{total_configured_sectors}: '{sec_name}'"
                await forecast_job_manager.update_job(job_id, current_sector=sec_name, current_message=f"{current_sector_message_prefix} - Starting...")

                selected_models = sec_cfg.get('models', [])
                model_params_cfg = {} # Ensure it's always a dict

                # Prepare model_params carefully, converting windowSize if present
                raw_mlr_params = sec_cfg.get('mlrParams', {}) # Assuming frontend might send it this way
                raw_wam_params = sec_cfg.get('wamParams', {})

                if 'MLR' in selected_models:
                    model_params_cfg['MLR'] = {'independent_vars': sec_cfg.get('independentVars', [])}
                if 'WAM' in selected_models:
                    window_size_val = sec_cfg.get('windowSize', wam_params.get('window_size', 10)) # Check sec_cfg then global
                    try:
                        # Ensure window_size_val is treated as potentially string from config
                        model_params_cfg['WAM'] = {'window_size': int(str(window_size_val))}
                    except (ValueError, TypeError):
                        logger.warning(f"Job {job_id}, Sector {sec_name}: Invalid window size '{window_size_val}'. Defaulting to 10.")
                        model_params_cfg['WAM'] = {'window_size': 10} # Default WAM window size

                # Check if sector data is available
                if sec_name not in sector_data_map or sector_data_map[sec_name].empty:
                    logger.warning(f"Job {job_id}: No data for sector '{sec_name}'. Skipping forecast.")
                    s_result = SectorProcessingResult(
                        sector_name=sec_name, status='failed',
                        message="No input data found for this sector or data is empty.",
                        error="Missing or empty sector data sheet.",
                        processing_time_seconds=round(time.time() - sector_start_time, 2),
                        configuration_used=sec_cfg
                    )
                    all_sector_results.append(s_result)
                    await forecast_job_manager.add_sector_result(job_id, s_result)
                    # Update overall progress immediately
                    current_job_progress = 15 + int(((i + 1) / total_configured_sectors) * 70) # Mark this sector as "done" for progress
                    await forecast_job_manager.update_job(job_id, progress=current_job_progress)
                    continue # Move to the next sector


                def _sector_progress_callback(progress_percent_sector: int, cb_sector_name: str, cb_message: str):
                    # Before updating progress, check if the job has been cancelled.
                    # This callback runs in the thread, so direct await is not possible here.
                    # We can schedule a check or rely on the main loop's check.
                    # For simplicity here, we'll assume the main loop check is frequent enough.
                    # If more immediate halting of the ML function itself is needed, Main_forecasting_function
                    # would need to accept a cancellation event/flag.

                    if main_event_loop and not main_event_loop.is_closed():
                        # Calculate overall progress: 15% for initial setup, 70% for sectors, 15% for finalization
                        # This sector's contribution to the 70%
                        overall_progress_for_sector = (progress_percent_sector / 100.0) / total_configured_sectors
                        # Progress from previous sectors + current sector's partial progress
                        current_overall_progress = 15 + int(((i + (progress_percent_sector / 100.0)) / total_configured_sectors) * 70)

                        full_message = f"{current_sector_message_prefix} - {cb_message}"
                        asyncio.run_coroutine_threadsafe(
                            forecast_job_manager.update_job(
                                job_id,
                                progress=current_overall_progress,
                                current_message=full_message
                            ),
                            main_event_loop
                        )
                    else:
                        logger.warning(f"Job {job_id}: Event loop not available or closed. Cannot update progress for {cb_sector_name} - {cb_message}")

                try:
                    sector_df = sector_data_map[sec_name]
                    # Ensure main_df is a DataFrame, not None or other type
                    if not isinstance(sector_df, pd.DataFrame):
                         raise TypeError(f"Data for sector '{sec_name}' is not a pandas DataFrame.")

                    sector_forecast_result = await asyncio.to_thread(
                        Main_forecasting_function,
                        sheet_name=sec_name,
                        forecast_path=str(project_results_dir),
                        main_df=sector_df, # Pass the actual DataFrame for the sector
                        selected_models=selected_models,
                        model_params=model_params_cfg,
                        target_year=config.target_year,
                        exclude_covid=config.exclude_covid_years,
                        progress_callback=_sector_progress_callback
                    )

                    # Interpret result from Main_forecasting_function
                    if sector_forecast_result.get('status') == 'success':
                        s_status = 'success'
                        if sector_forecast_result.get('used_existing_data', False):
                            s_status = 'existing_data' # Special status if no forecast was run

                        s_result = SectorProcessingResult(
                            sector_name=sec_name, status=s_status,
                            message=sector_forecast_result.get('message', 'Completed successfully.'),
                            models_used=sector_forecast_result.get('models_used', selected_models),
                            processing_time_seconds=round(time.time() - sector_start_time, 2),
                            configuration_used=sec_cfg
                        )
                    elif sector_forecast_result.get('status') == 'warning': # Handle warnings as partial success or note
                        s_result = SectorProcessingResult(
                            sector_name=sec_name, status='warning', # Or map to 'success' with notes
                            message=sector_forecast_result.get('message', 'Completed with warnings.'),
                            error=sector_forecast_result.get('error_details'), # Optional error detail
                            models_used=sector_forecast_result.get('models_used', []),
                            processing_time_seconds=round(time.time() - sector_start_time, 2),
                            configuration_used=sec_cfg
                        )
                    else: # Error status
                        s_result = SectorProcessingResult(
                            sector_name=sec_name, status='failed',
                            message=sector_forecast_result.get('message', 'Forecasting failed for this sector.'),
                            error=sector_forecast_result.get('error_details', 'Unknown error during forecasting.'),
                            processing_time_seconds=round(time.time() - sector_start_time, 2),
                            configuration_used=sec_cfg
                        )
                except Exception as e_sec:
                    logger.error(f"Job {job_id}: Unhandled error during forecasting sector '{sec_name}': {e_sec}", exc_info=True)
                    s_result = SectorProcessingResult(
                        sector_name=sec_name, status='failed',
                        message=f"An unexpected error occurred: {str(e_sec)}",
                        error=str(e_sec),
                        processing_time_seconds=round(time.time() - sector_start_time, 2),
                        configuration_used=sec_cfg
                    )

                all_sector_results.append(s_result)
                await forecast_job_manager.add_sector_result(job_id, s_result)
                # Update overall progress after each sector is fully processed by Main_forecasting_function
                final_sector_progress = 15 + int(((i + 1) / total_configured_sectors) * 70)
                await forecast_job_manager.update_job(job_id, progress=final_sector_progress, current_message=f"{current_sector_message_prefix} - {s_result.message}")

            # Finalize job: Set progress to 85 initially, then 100 upon completion of summary
            await forecast_job_manager.update_job(job_id, progress=85, current_message="Aggregating results...")
            # Create a summary of all_sector_results
            successful_sectors_count = sum(1 for sr in all_sector_results if sr.status == 'success')
            failed_sectors_count = sum(1 for sr in all_sector_results if sr.status == 'failed')
            existing_data_sectors_count = sum(1 for sr in all_sector_results if sr.status == 'existing_data') # Assuming this status exists
            total_processing_time = sum(sr.processing_time_seconds for sr in all_sector_results)

            detailed_summary = {
                "total_sectors_configured": len(config.sector_configs),
                "total_sectors_processed": len(all_sector_results),
                "successful_sectors": successful_sectors_count,
                "failed_sectors": failed_sectors_count,
                "existing_data_sectors": existing_data_sectors_count, # If applicable
                "processed_sector_details": [asdict(sr) for sr in all_sector_results], # Includes individual messages, errors, times
                "overall_output_path": str(project_results_dir),
                "total_forecast_processing_time_seconds": round(total_processing_time, 2)
            }

            final_status = JOB_STATUS['COMPLETED']
            final_message = "Forecast completed."
            if failed_sectors_count > 0 and successful_sectors_count > 0:
                final_message = "Forecast completed with some errors."
                # final_status = JOB_STATUS['PARTIAL_SUCCESS'] # If you add such a status
            elif failed_sectors_count > 0 and successful_sectors_count == 0:
                final_status = JOB_STATUS['FAILED']
                final_message = "Forecast failed for all sectors."
            elif not all_sector_results:
                 final_status = JOB_STATUS['FAILED'] # Or COMPLETED if no sectors was valid
                 final_message = "No sectors were processed."


            await forecast_job_manager.update_job(
                job_id,
                status=final_status,
                progress=100,
                current_message=final_message,
                result_summary=detailed_summary
            )
            logger.info(f"Forecast job {job_id} for project '{project_name}' finished with status: {final_status}")

        except FileNotFoundError as e_fnf:
            logger.error(f"FileNotFoundError in job {job_id}: {e_fnf}", exc_info=True)
            await forecast_job_manager.update_job(job_id, status=JOB_STATUS['FAILED'], error_message=str(e_fnf), current_message="Input file not found.")
        except ValueError as e_val:
            logger.error(f"ValueError in job {job_id}: {e_val}", exc_info=True)
            await forecast_job_manager.update_job(job_id, status=JOB_STATUS['FAILED'], error_message=str(e_val), current_message="Validation error.")
        except Exception as e_gen:
            logger.error(f"Unhandled exception in forecast job {job_id}: {e_gen}", exc_info=True)
            await forecast_job_manager.update_job(job_id, status=JOB_STATUS['FAILED'], error_message="An unexpected server error occurred.", current_message="Critical error.")

print("Defining demand projection service for FastAPI... (merged and adapted)")
