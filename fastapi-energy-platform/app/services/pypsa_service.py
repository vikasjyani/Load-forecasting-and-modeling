# fastapi-energy-platform/app/services/pypsa_service.py
"""
Service layer for PyPSA operations.
Handles interaction with PyPSA models, data, and simulation runs.
"""
import logging
import uuid
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import pypsa
import pandas as pd
from fastapi import BackgroundTasks

from app.utils.constants import JOB_STATUS # Assuming similar job status constants
from app.utils.pypsa_runner import run_pypsa_model_core # Core simulation logic
from app.utils.helpers import get_file_info, safe_filename, ensure_directory
# Import pau if it's made available in app.utils
# For now, direct calls or simplified versions might be used.
# import app.utils.pypsa_analysis_utils as pau


logger = logging.getLogger(__name__)

# --- Data Classes ---
@dataclass
class PyPSAJob:
    id: str
    project_name: str
    scenario_name: str
    status: str
    progress: int = 0
    current_step: Optional[str] = None
    start_time_iso: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time_iso: Optional[str] = None
    log: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None # e.g., path to network file, key metrics
    ui_settings_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PyPSANetworkInfo:
    name: str # Typically scenario_name or specific network file name part
    relative_path: str # Relative to project's pypsa_results directory
    full_path: str
    size_mb: Optional[float] = None
    last_modified_iso: Optional[str] = None
    snapshot_count: Optional[int] = None
    # Add more specific metadata if extractable without full load
    # E.g. components_summary: Dict[str, int] (counts of generators, lines etc.)


class PyPSAJobManager:
    """Manages PyPSA simulation jobs (in-memory for now)."""
    def __init__(self):
        self.jobs: Dict[str, PyPSAJob] = {}
        self.lock = asyncio.Lock()

    async def create_job(self, project_name: str, scenario_name: str, ui_settings_overrides: Dict[str, Any]) -> PyPSAJob:
        job_id = str(uuid.uuid4())
        job = PyPSAJob(
            id=job_id,
            project_name=project_name,
            scenario_name=scenario_name,
            status=JOB_STATUS['STARTING'], # Or 'QUEUED'
            ui_settings_overrides=ui_settings_overrides,
        )
        async with self.lock:
            self.jobs[job_id] = job
        logger.info(f"Created PyPSA Job {job_id} for project '{project_name}', scenario '{scenario_name}'.")
        return job

    async def update_job_status(self, job_id: str, status: str, progress: Optional[int] = None, current_step: Optional[str] = None):
        async with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = status
                if progress is not None:
                    self.jobs[job_id].progress = progress
                if current_step is not None:
                    self.jobs[job_id].current_step = current_step
                self.jobs[job_id].log.append(f"{datetime.now().isoformat()} - {status} - {current_step or ''} ({progress or ''}%)")
                if len(self.jobs[job_id].log) > 200: # Keep log manageable
                    self.jobs[job_id].log = self.jobs[job_id].log[-100:]
            else:
                logger.warning(f"Attempted to update status for non-existent PyPSA job: {job_id}")

    async def complete_job(self, job_id: str, result_summary: Dict[str, Any]):
        async with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = JOB_STATUS['COMPLETED']
                self.jobs[job_id].progress = 100
                self.jobs[job_id].end_time_iso = datetime.now().isoformat()
                self.jobs[job_id].result_summary = result_summary
                self.jobs[job_id].log.append(f"{self.jobs[job_id].end_time_iso} - COMPLETED - Results: {result_summary.get('output_network_path', 'N/A')}")
            else:
                logger.warning(f"Attempted to complete non-existent PyPSA job: {job_id}")

    async def fail_job(self, job_id: str, error_message: str):
        async with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = JOB_STATUS['FAILED']
                self.jobs[job_id].progress = 100 # Or current progress if preferred
                self.jobs[job_id].end_time_iso = datetime.now().isoformat()
                self.jobs[job_id].error_message = error_message
                self.jobs[job_id].log.append(f"{self.jobs[job_id].end_time_iso} - FAILED - Error: {error_message}")
            else:
                logger.warning(f"Attempted to fail non-existent PyPSA job: {job_id}")

    async def get_job(self, job_id: str) -> Optional[PyPSAJob]:
        async with self.lock:
            return self.jobs.get(job_id)

# Global instance (consider shared store for multi-worker setup)
pypsa_job_manager = PyPSAJobManager()


class PypsaService:
    def __init__(self, project_data_root: Path):
        self.project_data_root = project_data_root
        # Simple network cache (can be expanded like Flask's NetworkManager)
        self._network_cache: Dict[str, pypsa.Network] = {}
        self._network_mtimes: Dict[str, float] = {}
        self._cache_lock = asyncio.Lock()


    def _get_project_pypsa_path(self, project_name: str) -> Path:
        safe_project_name = safe_filename(project_name)
        return self.project_data_root / safe_project_name / "pypsa"

    def _get_pypsa_results_path(self, project_name: str, scenario_name: Optional[str] = None) -> Path:
        # Results are typically stored under project/results/PyPSA_Modeling/scenario_name/
        # Adapting to a more common structure for results.
        # The original Flask blueprint used project_path/results/Pypsa_results
        # Let's assume a structure like: project_data_root/project_name/results/pypsa/scenario_name
        base_results_path = self.project_data_root / safe_filename(project_name) / "results" / "pypsa"
        if scenario_name:
            return base_results_path / safe_filename(scenario_name)
        return base_results_path

    def _get_pypsa_input_excel_path(self, project_name: str, scenario_name: str) -> Path:
        # Inputs for a scenario might be here:
        # project_data_root/project_name/inputs/pypsa/scenario_name/pypsa_input_template.xlsx
        # Or a single template is used. The runner seems to imply it's in project_path/inputs
        return self.project_data_root / safe_filename(project_name) / "inputs" / "pypsa_input_template.xlsx"


    async def run_pypsa_simulation(
        self, project_name: str, scenario_name: str,
        ui_settings_overrides: Dict[str, Any],
        background_tasks: BackgroundTasks
    ) -> PyPSAJob:
        job = await pypsa_job_manager.create_job(project_name, scenario_name, ui_settings_overrides)

        project_path_str = str(self.project_data_root / safe_filename(project_name))

        # The run_pypsa_model_core needs to be adapted to use PyPSAJobManager for updates
        # For now, it takes the job_store (pypsa_jobs dict) directly.
        # A better way would be to pass a callback or the manager instance.
        # Adapting the call based on its current known signature from pypsa_bp.py's usage
        # which seems to imply that run_pypsa_model_core updates a shared dictionary.

        # This is a blocking call, so it needs to run in a background task correctly
        # and the `run_pypsa_model_core` itself must be designed to update the shared `pypsa_jobs`
        # dictionary in a thread-safe way or via callbacks to async functions.

        # For now, assuming run_pypsa_model_core is structured to handle its own threading
        # and updates the global pypsa_jobs dict. This is not ideal for FastAPI.
        # A better pattern:
        # background_tasks.add_task(self._execute_simulation_wrapper, job.id, project_path_str, scenario_name, ui_settings_overrides)

        # Direct call for now, assuming run_pypsa_model_core handles threading or is quick for some cases.
        # This will block if run_pypsa_model_core is long-running and not internally threaded.
        # The Flask version used ThreadPoolExecutor. FastAPI's BackgroundTasks uses a ThreadPoolExecutor for sync functions.

        # The original run_pypsa_model_core in Flask was called like this:
        # executor.submit(run_pypsa_model_core, job_id, project_path, scenario_name, settings_overrides, pypsa_jobs_dict)
        # So, it IS designed to be run in a thread and update a shared dict.

        background_tasks.add_task(
            run_pypsa_model_core, # This is the function from app.utils.pypsa_runner
            job.id,
            project_path_str, # project_path for run_pypsa_model_core
            scenario_name,
            ui_settings_overrides,
            pypsa_job_manager # Pass the manager instance instead of raw dict
        )

        return job

    async def get_simulation_status(self, job_id: str) -> Optional[PyPSAJob]:
        return await pypsa_job_manager.get_job(job_id)

    async def list_available_network_files(self, project_name: str, scenario_name: Optional[str] = None) -> List[PyPSANetworkInfo]:
        """Lists available PyPSA network .nc files."""
        results_path = self._get_pypsa_results_path(project_name, scenario_name)

        network_files_info = []
        if not await asyncio.to_thread(results_path.is_dir):
            if scenario_name:
                 logger.info(f"PyPSA results directory not found for project '{project_name}', scenario '{scenario_name}': {results_path}")
            else:
                 logger.info(f"PyPSA results base directory not found for project '{project_name}': {results_path}")
            return []

        # Scan for network files
        # If scenario_name is None, this could scan all scenarios, which might be too much.
        # For now, assume if scenario_name is None, it means list scenarios, not files across all.
        # This method is more for listing specific .nc files within a scenario or a known output dir.

        # Let's redefine: if scenario_name is provided, list .nc files in that scenario's result dir.
        # If scenario_name is None, list scenario directories themselves.

        if scenario_name: # List .nc files within this specific scenario result directory
            scan_path = results_path
        else: # List scenario directories under the main pypsa results path for the project
            scan_path = self._get_pypsa_results_path(project_name) # project/results/pypsa/

        try:
            items = await asyncio.to_thread(list, scan_path.iterdir())
        except FileNotFoundError:
             logger.warning(f"Path not found during network listing: {scan_path}")
             return []


        for item_path in items:
            if scenario_name: # Expecting .nc files
                if await asyncio.to_thread(item_path.is_file) and item_path.suffix == '.nc':
                    file_info = await get_file_info(item_path)
                    # Relative path from the scenario's result directory
                    rel_path = item_path.name
                    network_files_info.append(PyPSANetworkInfo(
                        name=item_path.stem,
                        relative_path=rel_path,
                        full_path=str(item_path),
                        size_mb=file_info.get('size_mb'),
                        last_modified_iso=file_info.get('modified_iso')
                        # snapshot_count might require loading the network, defer this
                    ))
            else: # Expecting scenario directories
                 if await asyncio.to_thread(item_path.is_dir):
                    # This is a scenario directory
                    network_files_info.append(PyPSANetworkInfo(
                        name=item_path.name, # Scenario name
                        relative_path=item_path.name, # Relative to pypsa_results_path
                        full_path=str(item_path)
                        # Further details like num snapshots would require deeper scan or metadata file
                    ))

        network_files_info.sort(key=lambda x: x.last_modified_iso or "0", reverse=True)
        return network_files_info

    # Further methods like get_network_info, get_network_data, compare_networks_data to be added.
    # These will use a proper NetworkManager-like component for loading and caching.
    # And a DataExtractionComponent for getting specific data.

logger.info("PyPSA Service structure defined.")
