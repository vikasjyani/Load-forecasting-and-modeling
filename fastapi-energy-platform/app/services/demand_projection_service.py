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
from app.models.forecasting import Main_forecasting_function # Assuming this is the core ML model function

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

        if not input_file_path.exists():
            raise FileNotFoundError(f"Input file not found for project '{project_name}': {input_file_path}")

        # TODO: Adapt validate_input_file and input_demand_data to be async or run in threadpool
        # For now, assuming they are synchronous and potentially blocking
        # validation_result = await asyncio.to_thread(validate_input_file, str(input_file_path))
        validation_result = validate_input_file(str(input_file_path)) # Blocking call
        if not validation_result['valid']:
            raise ValueError(f"Input file validation failed: {'; '.join(validation_result['errors'])}")
        for warning in validation_result.get('warnings', []):
            logger.warning(f"Input file warning for {project_name}: {warning}")

        # data_tuple = await asyncio.to_thread(input_demand_data, str(input_file_path))
        data_tuple = input_demand_data(str(input_file_path)) # Blocking call

        self._project_input_data_cache[cache_key] = (data_tuple, time.time())
        logger.info(f"Loaded input data for project '{project_name}'.")
        return data_tuple

    async def get_input_data_summary(self, project_name: str) -> Dict[str, Any]:
        """Gets a summary of the input data for a project."""
        try:
            sectors, missing_sectors, param_dict, _, aggregated_ele = await self._load_input_data(project_name)
            input_file_path = self._get_project_input_file_path(project_name)
            return {
                'project_name': project_name,
                'sectors_available': sectors,
                'sectors_missing_in_data': missing_sectors,
                'parameters_from_file': param_dict,
                'aggregated_data_summary': {
                    'num_rows': len(aggregated_ele),
                    'num_columns': len(aggregated_ele.columns)
                } if not aggregated_ele.empty else "Not available",
                'input_file_last_modified': datetime.fromtimestamp(input_file_path.stat().st_mtime).isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting input data summary for project '{project_name}': {e}")
            return {'error': str(e), 'project_name': project_name, 'data_available': False}

    async def get_sector_data(self, project_name: str, sector_name: str) -> Dict[str, Any]:
        """Gets detailed data for a specific sector within a project."""
        try:
            _, _, _, sector_data_map, _ = await self._load_input_data(project_name)
            if sector_name not in sector_data_map:
                raise ValueError(f"Sector '{sector_name}' not found in project '{project_name}'.")
            df = sector_data_map[sector_name]
            return {
                'project_name': project_name,
                'sector_name': sector_name,
                'columns': df.columns.tolist(),
                'data_records': df.to_dict('records'), # Consider pagination for large data
                'data_summary': {
                    'num_rows': len(df),
                    'year_range': (int(df['Year'].min()), int(df['Year'].max())) if 'Year' in df.columns and not df.empty else None,
                    'electricity_mean': float(df['Electricity'].mean()) if 'Electricity' in df.columns and not df.empty else None
                }
            }
        except Exception as e:
            logger.exception(f"Error getting sector data for '{sector_name}' in project '{project_name}': {e}")
            raise # Re-raise to be caught by error handling middleware


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
            # data_end_year = param_dict.get('End_Year', VALIDATION_RULES['MAX_YEAR'] -1) # Default from data
            # if config.target_year <= data_end_year:
            #     errors.append(f"Target year ({config.target_year}) should be after data end year ({data_end_year}).")

            for sec_name, sec_cfg in config.sector_configs.items():
                if sec_name not in sector_data_map:
                    errors.append(f"Sector '{sec_name}' not found in input data for project '{project_name}'.")
                    continue
                models = sec_cfg.get('models', [])
                if not models: errors.append(f"No models specified for sector '{sec_name}'.")
                for model in models:
                    if model not in FORECAST_MODELS: errors.append(f"Invalid model '{model}' for sector '{sec_name}'.")
                # Add more model-specific validation (MLR vars, WAM window size) here if needed
        except Exception as e:
            errors.append(f"Error during validation against input data: {str(e)}")
        return errors

    async def execute_forecast_async(self, project_name: str, config: ForecastJobConfig, job_id: str):
        """
        The core forecasting logic, designed to be run in the background.
        This method will be called by a BackgroundTask in the API route.
        """
        project_input_file = self._get_project_input_file_path(project_name)
        project_results_dir = self.project_data_root / project_name / "results" / "demand_projection" / config.scenario_name
        project_results_dir.mkdir(parents=True, exist_ok=True)

        try:
            await forecast_job_manager.update_job(job_id, status=JOB_STATUS['RUNNING'], progress=5, current_message='Loading input data...')
            # These are blocking I/O, should be wrapped with to_thread for true async
            # sectors, _, param_dict, sector_data_map, _ = await asyncio.to_thread(input_demand_data, str(project_input_file))
            sectors, _, param_dict, sector_data_map, _ = input_demand_data(str(project_input_file))


            await forecast_job_manager.update_job(job_id, progress=10, current_message='Data loaded. Saving configuration...')
            # Save full configuration to a file in project_results_dir
            full_config_data = {
                "job_config": asdict(config),
                "data_parameters_from_file": param_dict,
                "available_sectors_in_file": sectors,
                "execution_timestamp": datetime.now().isoformat()
            }
            with open(project_results_dir / "forecast_run_config.json", "w") as f:
                json.dump(full_config_data, f, indent=2)

            all_sector_results: List[SectorProcessingResult] = []

            for i, (sec_name, sec_cfg) selected_models = sec_cfg.get('models', [])
                model_params_cfg = {}
                if 'MLR' in selected_models: model_params_cfg['MLR'] = {'independent_vars': sec_cfg.get('independentVars', [])}
                if 'WAM' in selected_models: model_params_cfg['WAM'] = {'window_size': int(sec_cfg.get('windowSize', 10))}

                # Progress callback for Main_forecasting_function
                def _sector_progress_callback(prog_percent, current_model_msg):
                    # This callback runs in the thread of Main_forecasting_function.
                    # To update job_manager (which is async), we'd need to schedule it on the event loop.
                    # For simplicity here, we might log or store progress temporarily.
                    # A more robust way is to use a queue or another async-safe communication.
                    loop = asyncio.get_event_loop() # Get current loop if any, or main loop
                    current_job_progress = 15 + int(((i + (prog_percent / 100)) / len(config.sector_configs)) * 70)
                    asyncio.run_coroutine_threadsafe(
                        forecast_job_manager.update_job(
                            job_id,
                            progress=current_job_progress,
                            current_message=f"{sec_name} - {current_model_msg}"
                        ),
                        loop # Assuming Main_forecasting_function is run in a thread managed by FastAPI or similar
                    )


                try:
                    # Main_forecasting_function is likely CPU-bound and synchronous.
                    # Run it in a thread pool to avoid blocking the event loop.
                    sector_forecast_result = await asyncio.to_thread(
                        Main_forecasting_function,
                        sheet_name=sec_name,
                        forecast_path=str(project_results_dir), # Ensure path is string
                        main_df=sector_data_map[sec_name],
                        selected_models=selected_models,
                        model_params=model_params_cfg,
                        target_year=config.target_year,
                        exclude_covid=config.exclude_covid_years,
                        progress_callback=_sector_progress_callback # Pass the callback
                    )
                    # Assuming sector_forecast_result is a dict from Main_forecasting_function
                    # Adapt this based on actual return type of Main_forecasting_function
                    s_result = SectorProcessingResult(
                        sector_name=sec_name, status='success',
                        message=sector_forecast_result.get('message', 'Completed'),
                        models_used=sector_forecast_result.get('models_used', selected_models),
                        processing_time_seconds=time.time() - sector_start_time,
                        configuration_used=sec_cfg
                    )
                except Exception as e_sec:
                    logger.error(f"Error forecasting sector {sec_name}: {e_sec}", exc_info=True)
                    s_result = SectorProcessingResult(
                        sector_name=sec_name, status='failed', message=str(e_sec), error=str(e_sec),
                        processing_time_seconds=time.time() - sector_start_time, configuration_used=sec_cfg
                    )
                all_sector_results.append(s_result)
                await forecast_job_manager.add_sector_result(job_id, s_result)

            # Finalize job
            # TODO: Create a summary of all_sector_results
            # For now, just marking as complete if no errors, or partial if some errors.
            final_status = JOB_STATUS['COMPLETED']
            final_message = "Forecast completed."
            if any(sr.status == 'failed' for sr in all_sector_results):
                final_message = "Forecast completed with some errors."
                # final_status could remain 'COMPLETED' or be a specific 'PARTIAL_SUCCESS'

            await forecast_job_manager.update_job(job_id, status=final_status, progress=100, current_message=final_message, result_summary={"sector_outputs_path": str(project_results_dir)})
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
