# fastapi-energy-platform/app/services/pypsa_service.py
"""
Service layer for PyPSA operations for FastAPI.
Handles interaction with PyPSA models, data, and simulation runs.
Due to missing 'utils/pypsa_runner.py' and 'utils/pypsa_analysis_utils.py',
this service will implement MOCK logic for simulation and data extraction.
"""
import logging
import uuid
import time
import asyncio
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

import pandas as pd # For data structures
# PyPSA import is kept for type hinting and basic structure, but actual network ops will be mocked.
import pypsa
from fastapi import BackgroundTasks

from app.utils.constants import JOB_STATUS
# Actual run_pypsa_model_core is missing. We will define a mock for it.
# from app.utils.pypsa_runner import run_pypsa_model_core
# Actual pypsa_analysis_utils are missing. We will define mock for them.
# import app.utils.pypsa_analysis_utils as pau

from app.utils.helpers import get_file_info, safe_filename, ensure_directory
from app.config import settings as global_settings # For PYPSA_NETWORK_CACHE_SIZE
from app.models.pypsa import PyPSAJobRunPayload # For type hint consistency with API

logger = logging.getLogger(__name__)

# --- Mocked PyPSA Utilities ---
async def mock_run_pypsa_model_core(
    job_id: str,
    project_path_str: str,
    scenario_name: str,
    ui_settings_overrides: Dict[str, Any],
    job_manager: 'PyPSAJobManager', # Forward reference
    event_loop: Optional[asyncio.AbstractEventLoop] = None
):
    """Mocks the actual PyPSA simulation run."""
    logger.info(f"Job {job_id}: Starting MOCK PyPSA simulation for scenario '{scenario_name}' in project '{project_path_str}'.")

    async def update_status_safe(status: str, progress: int, current_step: str):
        if event_loop and not event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                job_manager.update_job_status(job_id, status, progress, current_step),
                event_loop
            )
        else: # Fallback for direct call if no loop or for testing
            await job_manager.update_job_status(job_id, status, progress, current_step)

    await update_status_safe(JOB_STATUS['RUNNING'], 10, "Initializing mock PyPSA model...")
    await asyncio.sleep(2) # Simulate setup time

    project_path = Path(project_path_str)
    results_dir = project_path / "results" / "pypsa" / safe_filename(scenario_name)
    await asyncio.to_thread(ensure_directory, results_dir)

    mock_network_filename = f"{safe_filename(scenario_name)}_mock_network.nc"
    mock_network_path = results_dir / mock_network_filename

    # Simulate steps
    steps = ["Loading components", "Attaching load profiles", "Preparing constraints",
             "Optimizing network (LPOF)", "Exporting results"]
    for i, step_name in enumerate(steps):
        progress = 20 + int((i / len(steps)) * 70) # Progress from 20% to 90%
        await update_status_safe(JOB_STATUS['RUNNING'], progress, step_name)
        await asyncio.sleep(random.uniform(1, 3)) # Simulate work for this step

    # Create a dummy .nc file
    await asyncio.to_thread(mock_network_path.touch)

    result_summary = {
        "output_network_path": str(mock_network_path),
        "objective_value": random.uniform(1e6, 1e7),
        "solve_time_seconds": random.uniform(60, 600),
        "message": "Mock simulation completed successfully."
    }
    await job_manager.complete_job(job_id, result_summary)
    logger.info(f"Job {job_id}: MOCK PyPSA simulation completed for '{scenario_name}'.")


class MockPyPSAAnalysisUtils:
    """Replaces the missing pau module with mock data extraction functions."""

    def _mock_series_data(self, index_name: str = "snapshot", value_name: str = "value", num_entries: int = 5) -> pd.DataFrame:
        return pd.DataFrame({
            index_name: pd.date_range(start="2030-01-01", periods=num_entries, freq="h"),
            value_name: [random.uniform(100, 1000) for _ in range(num_entries)]
        }).set_index(index_name)

    def dispatch_data_payload_former(self, n: Any, snapshots_slice: Any = None, **kwargs) -> Dict[str, Any]:
        logger.info(f"MOCK dispatch_data_payload_former called with network: {type(n)}, snapshots: {snapshots_slice}, kwargs: {kwargs}")
        return {
            "generators_dispatch": self._mock_series_data(value_name="Generator A"),
            "storage_units_dispatch": self._mock_series_data(value_name="Battery 1"),
            "loads_p": self._mock_series_data(value_name="Total Load")
        }

    def capacity_data_payload_former(self, n: Any, **kwargs) -> Dict[str, Any]:
        logger.info(f"MOCK capacity_data_payload_former called with network: {type(n)}, kwargs: {kwargs}")
        return {
            "generators_capacity": {"Generator A": random.uniform(500,1000), "Generator B": random.uniform(300,800)},
            "storage_units_energy_capacity": {"Battery 1": random.uniform(1000,4000)},
            "lines_capacity": {"Line 1-2": random.uniform(200,500)}
        }

    def transmission_data_payload_former(self, n: Any, snapshots_slice: Any = None, **kwargs) -> Dict[str, Any]:
        logger.info(f"MOCK transmission_data_payload_former called with network: {type(n)}, snapshots: {snapshots_slice}, kwargs: {kwargs}")
        return {
            "lines_p0": self._mock_series_data(value_name="Line 1-2 Flow"),
            "links_p0": self._mock_series_data(value_name="HVDC Link Flow")
        }

    def compare_networks_results(self, networks_dict: Dict[str, Any], comparison_type: str = "capacity", **kwargs) -> Dict[str, Any]:
        logger.info(f"MOCK compare_networks_results called for {len(networks_dict)} networks, type: {comparison_type}, kwargs: {kwargs}")
        comparison = {}
        for label, net_mock in networks_dict.items():
            comparison[label] = {
                "objective": net_mock.get("objective_value", random.uniform(1e6, 1e7)),
                "total_capacity_GW": random.uniform(10,50)
            }
        return {"comparison_data": comparison, "summary": "Mock comparison successful."}

    def get_color_palette(self, n: Any) -> Dict[str, str]:
        logger.info(f"MOCK get_color_palette called with network: {type(n)}")
        return {"Solar": "#FFD700", "Wind": "#ADD8E6", "Coal": "#A9A9A9"}

# Instantiate the mock utils
pau = MockPyPSAAnalysisUtils()


# --- Data Classes (from pypsa.py API router, assuming they are defined in app.models.pypsa) ---
@dataclass
class PyPSAJob: # Duplicates definition from pypsa.py API router, ensure consistency or import
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
    result_summary: Optional[Dict[str, Any]] = None
    ui_settings_overrides: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PyPSANetworkInfo: # Duplicates definition, ensure consistency or import
    name: str
    relative_path: str
    full_path: str # Storing as string for Pydantic model compatibility
    size_mb: Optional[float] = None
    last_modified_iso: Optional[str] = None
    snapshot_count: Optional[int] = None
    objective_value: Optional[float] = None # Added field


class PyPSAJobManager:
    """Manages PyPSA simulation jobs (in-memory)."""
    def __init__(self):
        self.jobs: Dict[str, PyPSAJob] = {}
        self.lock = asyncio.Lock()

    async def create_job(self, project_name: str, scenario_name: str, ui_settings_overrides: Dict[str, Any], id: Optional[str]=None, type: Optional[str]=None) -> PyPSAJob: # Added id, type for API call
        job_id = id or str(uuid.uuid4())
        job = PyPSAJob(
            id=job_id, project_name=project_name, scenario_name=scenario_name,
            status=JOB_STATUS['STARTING'], ui_settings_overrides=ui_settings_overrides
        )
        async with self.lock:
            self.jobs[job_id] = job
        logger.info(f"Created PyPSA Job {job_id} for project '{project_name}', scenario '{scenario_name}'.")
        return job

    async def update_job_status(self, job_id: str, status: str, progress: Optional[int] = None, current_step: Optional[str] = None):
        async with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = status
                if progress is not None: job.progress = progress
                if current_step is not None: job.current_step = current_step
                # Log entry handled by add_log_entry to avoid duplication if called separately
                # self.add_log_entry_sync(job, f"{datetime.now().isoformat()} - {status} - {current_step or ''} ({progress or ''}%)")
            else:
                logger.warning(f"PyPSAJobManager: Update for non-existent job {job_id}")

    def add_log_entry_sync(self, job: PyPSAJob, message: str): # Sync version for use in threads
        log_message = f"{datetime.now().isoformat()} - {message}"
        job.log.append(log_message)
        if len(job.log) > 200: job.log = job.log[-100:]

    async def add_log_entry(self, job_id: str, message: str, level: str = "INFO"): # Async version for service
        async with self.lock:
            job = self.jobs.get(job_id)
            if job:
                self.add_log_entry_sync(job, f"{level} - {message}")

    async def complete_job(self, job_id: str, result_summary: Dict[str, Any]):
        async with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = JOB_STATUS['COMPLETED']
                job.progress = 100
                job.end_time_iso = datetime.now().isoformat()
                job.result_summary = result_summary
                self.add_log_entry_sync(job, f"COMPLETED - Results: {result_summary.get('output_network_path', 'N/A')}")

    async def fail_job(self, job_id: str, error_message: str):
        async with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = JOB_STATUS['FAILED']
                job.end_time_iso = datetime.now().isoformat()
                job.error_message = error_message
                self.add_log_entry_sync(job, f"ERROR - {error_message}")

    async def get_job(self, job_id: str) -> Optional[PyPSAJob]:
        async with self.lock:
            return self.jobs.get(job_id)

    async def get_jobs_summary(self) -> Dict[str, Any]: # Added for API endpoint
        async with self.lock:
            return {
                "total_jobs": len(self.jobs),
                "active_jobs": sum(1 for job in self.jobs.values() if job.status == JOB_STATUS['RUNNING']),
                # Add more stats if needed
            }

pypsa_job_manager = PyPSAJobManager()


class PypsaService:
    def __init__(self, project_data_root: Path):
        self.project_data_root = project_data_root
        self._network_cache: Dict[str, Tuple[Any, float]] = {} # path_str -> (mock_network_obj, mtime)
        self._cache_lock = asyncio.Lock()
        # Access PYPSA_NETWORK_CACHE_SIZE from global_settings
        self.PYPSA_NETWORK_CACHE_SIZE = global_settings.PYPSA_NETWORK_CACHE_SIZE

    def _get_project_pypsa_inputs_path(self, project_name: str) -> Path:
        return self.project_data_root / safe_filename(project_name) / "inputs" / "pypsa"

    def _get_project_pypsa_results_path(self, project_name: str, scenario_name: Optional[str] = None) -> Path:
        base = self.project_data_root / safe_filename(project_name) / "results" / "pypsa"
        return base / safe_filename(scenario_name) if scenario_name else base

    async def run_pypsa_simulation(
        self, project_name: str, scenario_name: str,
        ui_settings_overrides: Dict[str, Any],
        background_tasks: BackgroundTasks
    ) -> PyPSAJob:
        job = await pypsa_job_manager.create_job(project_name, scenario_name, ui_settings_overrides)
        project_path_str = str(self.project_data_root / safe_filename(project_name))

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            logger.warning(f"Job {job.id}: No running asyncio loop found when starting PyPSA simulation. Status updates from thread might not work as expected.")

        # Pass the job_manager instance to the core runner
        background_tasks.add_task(
            mock_run_pypsa_model_core, # Using the mock runner
            job.id,
            project_path_str,
            scenario_name,
            ui_settings_overrides,
            pypsa_job_manager, # Pass the manager instance
            loop
        )
        return job

    async def get_simulation_status(self, job_id: str) -> Optional[PyPSAJob]:
        return await pypsa_job_manager.get_job(job_id)

    async def list_available_network_files(self, project_name: str, scenario_name: Optional[str] = None) -> List[PyPSANetworkInfo]:
        base_results_path = self._get_project_pypsa_results_path(project_name)
        scan_path = base_results_path / safe_filename(scenario_name) if scenario_name else base_results_path

        network_infos = []
        if not await asyncio.to_thread(scan_path.is_dir):
            return []

        items = await asyncio.to_thread(list, scan_path.iterdir())
        for item_path in items:
            if scenario_name: # Listing .nc files within a scenario
                if await asyncio.to_thread(item_path.is_file) and item_path.suffix == '.nc':
                    file_info = await get_file_info(item_path) # get_file_info is async
                    network_infos.append(PyPSANetworkInfo(
                        name=item_path.stem,
                        relative_path=item_path.name, # Relative to scenario folder
                        full_path=str(item_path),
                        size_mb=file_info.get('size_mb'),
                        last_modified_iso=file_info.get('modified_iso'),
                        snapshot_count=None, # Mock: Would require loading .nc
                        objective_value=None # Mock
                    ))
            else: # Listing scenario folders
                if await asyncio.to_thread(item_path.is_dir):
                     # Check if any .nc file exists to confirm it's a valid scenario output
                    nc_files_in_scenario = [f for f in await asyncio.to_thread(list,item_path.glob('*.nc')) if await asyncio.to_thread(f.is_file)]
                    if nc_files_in_scenario:
                        # Use the first .nc file for some basic info, or just list the scenario
                        first_nc_info = await get_file_info(nc_files_in_scenario[0])
                        network_infos.append(PyPSANetworkInfo(
                            name=item_path.name, # Scenario name
                            relative_path=item_path.name, # Relative to pypsa results path
                            full_path=str(item_path),
                            size_mb=first_nc_info.get('size_mb'), # Could sum all .nc sizes
                            last_modified_iso=first_nc_info.get('modified_iso') # Could use latest .nc
                        ))
        network_infos.sort(key=lambda x: x.last_modified_iso or "0", reverse=True)
        return network_infos

    async def _load_mock_pypsa_network(self, network_path: Path) -> Dict[str, Any]:
        """Mocks loading a PyPSA network. Returns a dict with basic info."""
        abs_path_str = str(network_path.resolve())
        async with self._cache_lock:
            current_mtime = 0.0
            if await asyncio.to_thread(network_path.exists) and await asyncio.to_thread(network_path.is_file):
                current_mtime = (await asyncio.to_thread(network_path.stat)).st_mtime

            cached_network, cached_mtime = self._network_cache.get(abs_path_str, (None, 0.0))
            if cached_network and cached_mtime == current_mtime:
                logger.info(f"Cache hit for MOCK PyPSA network: {network_path.name}")
                return cached_network

        logger.info(f"MOCK loading PyPSA network: {network_path.name}")
        if not await asyncio.to_thread(network_path.exists) or not await asyncio.to_thread(network_path.is_file):
            raise FileNotFoundError(f"PyPSA (mock) network file not found: {network_path}")

        # Simulate network properties
        mock_network_obj = {
            "name": network_path.stem,
            "path": str(network_path),
            "snapshots": pd.date_range(start="2030-01-01", periods=8760, freq="h"), # Mock snapshots
            "objective_value": random.uniform(1e6, 1e7),
            "components_mock": { # Mock components
                "generators": pd.DataFrame({'p_nom': [100,200]}),
                "loads": pd.DataFrame({'p_set': [150, 250]}),
                "lines": pd.DataFrame({'s_nom': [300,400]})
            }
        }

        async with self._cache_lock:
            self._network_cache[abs_path_str] = (mock_network_obj, current_mtime)
            if len(self._network_cache) > self.PYPSA_NETWORK_CACHE_SIZE:
                # Simple FIFO eviction for mock cache
                oldest_key = next(iter(self._network_cache))
                del self._network_cache[oldest_key]
                logger.info(f"PyPSA mock network cache full. Removed oldest: {Path(oldest_key).name}")
        return mock_network_obj

    async def get_network_info(self, project_name: str, scenario_name: str, network_file_name: str) -> Dict[str, Any]:
        network_path = self._get_project_pypsa_results_path(project_name, scenario_name) / network_file_name
        mock_network = await self._load_mock_pypsa_network(network_path)

        return {
            'file_name': network_file_name,
            'full_path_on_server': str(network_path),
            'snapshots': {
                'count': len(mock_network['snapshots']),
                'start': str(mock_network['snapshots'].min()) if not mock_network['snapshots'].empty else None,
                'end': str(mock_network['snapshots'].max()) if not mock_network['snapshots'].empty else None,
                'freq': str(pd.infer_freq(mock_network['snapshots'])) if not mock_network['snapshots'].empty else None,
            },
            'components': {name: {"count": len(df), "columns": df.columns.tolist()}
                           for name, df in mock_network["components_mock"].items()},
            'objective_value': mock_network.get('objective_value')
        }

    async def get_network_data(
        self, project_name: str, scenario_name: str, network_file_name: str,
        extraction_func_name: str, filters: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        network_path = self._get_project_pypsa_results_path(project_name, scenario_name) / network_file_name
        mock_network_obj = await self._load_mock_pypsa_network(network_path) # This is now a dict

        try:
            if not hasattr(pau, extraction_func_name): # pau is our MockPyPSAAnalysisUtils instance
                raise AttributeError(f"Extraction function '{extraction_func_name}' not found in mock PyPSA analysis utils.")
            func_to_call = getattr(pau, extraction_func_name)
        except AttributeError as e:
            raise ValueError(f"Invalid data extraction function: {extraction_func_name}")

        call_args = {"n": mock_network_obj} # Pass the mock network dict
        if filters: call_args.update(filters)
        if kwargs: call_args.update(kwargs)

        # Mock pau functions are synchronous, so call with to_thread
        extracted_data = await asyncio.to_thread(func_to_call, **call_args)
        colors = await asyncio.to_thread(pau.get_color_palette, mock_network_obj)

        return {
            "data": extracted_data, "colors": colors,
            "metadata": {
                "project_name": project_name, "scenario_name": scenario_name, "network_file_name": network_file_name,
                "extraction_function": extraction_func_name, "filters_applied": filters, "kwargs_applied": kwargs,
                "timestamp": datetime.now().isoformat()
            }
        }

    async def compare_networks_data(
        self, project_name: str, network_specs: List[Dict[str, str]],
        comparison_func_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if len(network_specs) < 2: raise ValueError("At least two networks needed for comparison.")

        loaded_mock_networks = {}
        for spec in network_specs:
            s_name = spec.get("scenario_name")
            nf_name = spec.get("network_file_name")
            label = spec.get("label", f"{s_name}_{nf_name}")
            if not s_name or not nf_name: raise ValueError(f"Invalid spec: {spec}")

            network_path = self._get_project_pypsa_results_path(project_name, s_name) / nf_name
            try:
                loaded_mock_networks[label] = await self._load_mock_pypsa_network(network_path)
            except FileNotFoundError:
                raise ResourceNotFoundError(f"Network file {nf_name} in scenario {s_name} not found for comparison.")

        if not hasattr(pau, comparison_func_name):
            raise AttributeError(f"Comparison function '{comparison_func_name}' not found in mock PyPSA utils.")
        func_to_call = getattr(pau, comparison_func_name)

        call_args = {"networks_dict": loaded_mock_networks}
        if params: call_args.update(params)

        return await asyncio.to_thread(func_to_call, **call_args)

    async def get_pypsa_system_status(self) -> Dict[str, Any]:
        async with self._cache_lock:
            cache_size = len(self._network_cache)
        jobs_summary = await pypsa_job_manager.get_jobs_summary()
        return {
            "network_cache_current_size": cache_size,
            "network_cache_max_size": self.PYPSA_NETWORK_CACHE_SIZE,
            "active_simulation_jobs": jobs_summary.get("active_jobs", 0),
            "total_tracked_jobs": jobs_summary.get("total_jobs", 0),
        }

logger.info("FastAPI PyPSA Service (with MOCK core logic) defined.")
print("FastAPI PyPSA Service (with MOCK core logic) defined.")

[end of fastapi-energy-platform/app/services/pypsa_service.py]

[start of blueprints/pypsa_bp.py]
# blueprints/pypsa_bp.py (OPTIMIZED - Fixed)
"""
Optimized PyPSA Blueprint - High-performance power system modeling
error handling, memory management, and standardized response patterns
Fixed to work without service layer dependency
"""
from flask import Blueprint, flash, redirect, url_for, render_template, request, jsonify, current_app, send_file, g
import os
import pandas as pd
import numpy as np
import json
import threading
import uuid
import tempfile
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Callable, Tuple
import psutil
import gc
import weakref
from functools import lru_cache, wraps
import logging
import time

# Optimization utilities
from utils.response_utils import success_json, error_json, validation_error_json
from utils.common_decorators import require_project, handle_exceptions, api_route, track_performance
from utils.constants import ERROR_MESSAGES, SUCCESS_MESSAGES
from utils.demand_utils import handle_nan_values

# PyPSA imports
import pypsa
# import utils.pypsa_analysis_utils as pau # This will be missing
# from utils.pypsa_runner import run_pypsa_model_core # This will be missing
from utils.helpers import extract_tables_by_markers, validate_file_path, get_file_info
from werkzeug.utils import secure_filename

# Initialize blueprint
pypsa_bp = Blueprint('pypsa', __name__,
                     template_folder='../templates',
                     static_folder='../static',
                     url_prefix='/pypsa')

logger = logging.getLogger(__name__)

# ========== Placeholder for missing utils ==========
# Mocking pau and run_pypsa_model_core as they are missing from utils

class MockPau:
    def dispatch_data_payload_former(self, *args, **kwargs): return {"mock_dispatch": "data"}
    def capacity_data_payload_former(self, *args, **kwargs): return {"mock_capacity": "data"}
    def transmission_data_payload_former(self, *args, **kwargs): return {"mock_transmission": "data"}
    def compare_networks_results(self, *args, **kwargs): return {"mock_comparison": "data"}
    def get_color_palette(self, *args, **kwargs): return {"mock_color": "palette"}

pau = MockPau()

# Mock run_pypsa_model_core
# This is a complex function. The actual implementation would involve:
# 1. Setting up a PyPSA network (possibly from an Excel template).
# 2. Integrating load data, renewable profiles.
# 3. Adding components (generators, lines, storage) based on configuration.
# 4. Solving the network (network.lopf()).
# 5. Saving the solved network to a .nc file.
# 6. Updating job status in a shared dictionary (pypsa_jobs_dict).
# For the mock, we'll just simulate these steps with print statements and delays.

# Global dictionary to simulate job tracking (as used in the original blueprint)
pypsa_jobs_dict = {}
pypsa_jobs_lock = threading.Lock()


def run_pypsa_model_core(job_id, project_path, scenario_name, settings_overrides, job_store, event_loop=None):
    """
    MOCK implementation of the core PyPSA model runner.
    Updates job_store with progress and status.
    """
    current_process_id = os.getpid()
    current_thread_id = threading.get_ident()
    logger.info(f"MOCK PyPSA Job {job_id} started. Process: {current_process_id}, Thread: {current_thread_id}")

    def update_status_in_job_store(status, progress, message):
        # If job_store is PyPSAJobManager, use its async method via event_loop
        if event_loop and hasattr(job_store, 'update_job_status') and asyncio.iscoroutinefunction(job_store.update_job_status):
            asyncio.run_coroutine_threadsafe(
                job_store.update_job_status(job_id, status, progress, message),
                event_loop
            )
        elif isinstance(job_store, dict): # Original Flask dict-based job_store
             with pypsa_jobs_lock:
                if job_id in job_store:
                    job_store[job_id]['status'] = status
                    job_store[job_id]['progress'] = progress
                    job_store[job_id]['message'] = message
                    job_store[job_id]['last_update'] = time.time()
                    job_store[job_id]['log'].append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {status} - {message} ({progress}%)")
        else:
            logger.error(f"Job {job_id}: Unknown job_store type for status update: {type(job_store)}")


    update_status_in_job_store(JOB_STATUS['RUNNING'], 10, "Initializing MOCK PyPSA model")
    time.sleep(2)

    # Simulate creating results directory
    results_base_dir = Path(project_path) / "results" / "pypsa"
    scenario_results_dir = results_base_dir / safe_filename(scenario_name)
    try:
        scenario_results_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Job {job_id}: Failed to create results directory {scenario_results_dir}: {e}")
        update_status_in_job_store(JOB_STATUS['FAILED'], 10, f"Error creating results directory: {e}")
        return

    update_status_in_job_store(JOB_STATUS['RUNNING'], 30, "MOCK: Loading components")
    time.sleep(3)
    update_status_in_job_store(JOB_STATUS['RUNNING'], 60, "MOCK: Optimizing network")
    time.sleep(5)

    # Simulate creating a dummy output file
    mock_network_filename = f"{safe_filename(scenario_name)}_mock_output.nc"
    mock_output_path = scenario_results_dir / mock_network_filename
    try:
        with open(mock_output_path, "w") as f:
            f.write(f"Mock PyPSA output for job {job_id}, scenario {scenario_name}\n")
            json.dump({"settings_overrides": settings_overrides, "completion_time": time.time()}, f, indent=2)
        logger.info(f"Job {job_id}: Created dummy output file: {mock_output_path}")
    except Exception as e:
        logger.error(f"Job {job_id}: Failed to create dummy output file {mock_output_path}: {e}")
        update_status_in_job_store(JOB_STATUS['FAILED'], 90, f"Error creating output file: {e}")
        return

    update_status_in_job_store(JOB_STATUS['RUNNING'], 90, "MOCK: Exporting results")
    time.sleep(2)

    result_summary = {
        "output_network_path": str(mock_output_path),
        "objective_value": random.uniform(1e6, 1e8),
        "solve_time_seconds": random.uniform(10, 100),
        "message": "MOCK PyPSA simulation completed successfully."
    }

    # If job_store is PyPSAJobManager, use its async method
    if event_loop and hasattr(job_store, 'complete_job') and asyncio.iscoroutinefunction(job_store.complete_job):
         asyncio.run_coroutine_threadsafe(
            job_store.complete_job(job_id, result_summary),
            event_loop
        )
    elif isinstance(job_store, dict): # Original Flask dict-based job_store
        with pypsa_jobs_lock:
            if job_id in job_store:
                job_store[job_id].update({
                    'status': JOB_STATUS['COMPLETED'],
                    'progress': 100,
                    'result': result_summary,
                    'end_time': time.time(),
                    'message': 'MOCK PyPSA simulation completed.'
                })
    else:
        logger.error(f"Job {job_id}: Unknown job_store type for completion: {type(job_store)}")

    logger.info(f"MOCK PyPSA Job {job_id} completed for scenario '{scenario_name}'.")

# ========== Memory Management ==========

def memory_efficient_operation(func):
    """Decorator for memory-efficient operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        initial_memory = psutil.Process().memory_info().rss

        try:
            result = func(*args, **kwargs)
            return result
        except MemoryError as e:
            logger.error(f"Memory error in {func.__name__}: {e}")
            gc.collect()
            raise
        finally:
            final_memory = psutil.Process().memory_info().rss
            memory_delta = (final_memory - initial_memory) / (1024 * 1024)
            if memory_delta > 100:  # Log if more than 100MB used
                logger.warning(f"{func.__name__} used {memory_delta:.1f}MB memory")

    return wrapper

def cached_with_ttl(ttl_seconds=300):
    """caching with TTL"""
    def decorator(func):
        cache = {}
        timestamps = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()

            if (key in cache and
                key in timestamps and
                current_time - timestamps[key] < ttl_seconds):
                return cache[key]

            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = current_time

            # Cleanup old entries
            if len(cache) > 100:
                old_keys = [k for k, t in timestamps.items()
                          if current_time - t > ttl_seconds]
                for k in old_keys:
                    cache.pop(k, None)
                    timestamps.pop(k, None)

            return result

        wrapper.cache_clear = lambda: cache.clear() or timestamps.clear()
        return wrapper

    return decorator

# ========== Network Management ==========

@dataclass
class NetworkCacheEntry:
    """Optimized cache entry for PyPSA networks"""
    network: pypsa.Network
    file_path: str
    file_mtime: float
    last_accessed: float
    memory_usage_mb: float
    access_count: int = 0

class NetworkManager:
    """
    High-performance network manager with intelligent caching and memory management
    """

    def __init__(self, max_cached_networks: int = 3, memory_threshold_mb: int = 1500):
        self.max_cached_networks = max_cached_networks
        self.memory_threshold_mb = memory_threshold_mb
        self.network_cache: Dict[str, NetworkCacheEntry] = {}
        self.cache_lock = threading.RLock()

        # Thread pools optimized for PyPSA operations
        self.io_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pypsa-io")

        # Background cleanup
        self._start_cache_cleanup()

        logger.info(f"NetworkManager initialized: max_networks={max_cached_networks}, memory_threshold={memory_threshold_mb}MB")

    def _start_cache_cleanup(self):
        """Start optimized background cache cleanup"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(180)  # Every 3 minutes
                    self._cleanup_cache()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

    @memory_efficient_operation
    def load_network(self, file_path: str) -> pypsa.Network:
        """Load network with caching and memory management"""
        abs_path = os.path.abspath(file_path)

        with self.cache_lock:
            # Check cache first
            if abs_path in self.network_cache:
                entry = self.network_cache[abs_path]
                current_mtime = os.path.getmtime(abs_path)

                if entry.file_mtime == current_mtime:
                    # Update access stats
                    entry.last_accessed = time.time()
                    entry.access_count += 1
                    logger.debug(f"Cache hit for network: {abs_path}")
                    return entry.network
                else:
                    # File modified, remove from cache
                    logger.debug(f"Network file modified, removing from cache: {abs_path}")
                    del self.network_cache[abs_path]

            # Memory check before loading
            memory_status = self._check_memory_status()
            if memory_status['critical']:
                self._emergency_cleanup()

                # Recheck after cleanup
                if self._check_memory_status()['critical']:
                    raise MemoryError("Insufficient memory to load PyPSA network")

            # Load network with monitoring
            logger.info(f"Loading PyPSA network: {abs_path}")
            initial_memory = psutil.Process().memory_info().rss

            try:
                # MOCK: Return a dummy network object for analysis as actual .nc might not be valid
                # network = pypsa.Network(abs_path)
                network = pypsa.Network() # Create an empty network
                network.add("Bus", "MockBus")
                network.add("Load", "MockLoad", bus="MockBus", p_set=100)
                network.add("Generator", "MockGenerator", bus="MockBus", p_nom=200, marginal_cost=20)
                network.snapshots = pd.date_range("2023-01-01", periods=3, freq="h")
                logger.info(f"MOCK: Loaded dummy PyPSA network for path {abs_path}")


                final_memory = psutil.Process().memory_info().rss
                memory_usage_mb = (final_memory - initial_memory) / (1024 * 1024)

                # Cache if space available
                if len(self.network_cache) < self.max_cached_networks:
                    entry = NetworkCacheEntry(
                        network=network,
                        file_path=abs_path,
                        file_mtime=os.path.getmtime(abs_path) if os.path.exists(abs_path) else time.time(), # handle dummy file
                        last_accessed=time.time(),
                        memory_usage_mb=memory_usage_mb,
                        access_count=1
                    )
                    self.network_cache[abs_path] = entry
                    logger.info(f"Cached network: {abs_path} ({memory_usage_mb:.1f}MB)")
                else:
                    logger.info(f"Network cache full, not caching: {abs_path}")

                return network

            except Exception as e:
                logger.error(f"Error loading network {abs_path}: {e}")
                raise

    def _check_memory_status(self) -> Dict[str, Any]:
        """Check current memory status"""
        memory = psutil.virtual_memory()
        process_memory = psutil.Process().memory_info().rss / (1024 * 1024)

        return {
            'system_percent': memory.percent,
            'process_mb': process_memory,
            'critical': memory.percent > 85 or process_memory > 2000,
            'warning': memory.percent > 70 or process_memory > 1500
        }

    def _cleanup_cache(self):
        """Intelligent cache cleanup using LRU and access patterns"""
        with self.cache_lock:
            if not self.network_cache:
                return

            current_time = time.time()
            total_memory_mb = sum(entry.memory_usage_mb for entry in self.network_cache.values())

            if total_memory_mb > self.memory_threshold_mb:
                logger.info(f"Cache cleanup triggered: {total_memory_mb:.1f}MB > {self.memory_threshold_mb}MB")

                # Sort by combined score (recency + access frequency)
                def cache_score(entry):
                    recency_score = current_time - entry.last_accessed
                    frequency_score = 1000 / max(entry.access_count, 1)  # Lower is better
                    return recency_score + frequency_score

                sorted_entries = sorted(
                    self.network_cache.items(),
                    key=lambda x: cache_score(x[1]),
                    reverse=True  # Highest score (least valuable) first
                )

                # Remove least valuable entries
                for file_path, entry in sorted_entries:
                    del self.network_cache[file_path]
                    total_memory_mb -= entry.memory_usage_mb
                    logger.info(f"Removed cached network: {file_path}")

                    if total_memory_mb <= self.memory_threshold_mb * 0.7:  # 30% buffer
                        break

                gc.collect()

    def _emergency_cleanup(self):
        """Emergency cleanup when memory is critical"""
        with self.cache_lock:
            logger.warning("Emergency cache cleanup - clearing all cached networks")
            self.network_cache.clear()
            gc.collect()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics"""
        with self.cache_lock:
            if not self.network_cache:
                return {
                    'cached_networks': 0,
                    'total_memory_mb': 0,
                    'average_memory_mb': 0,
                    'cache_hit_efficiency': 0
                }

            total_memory = sum(entry.memory_usage_mb for entry in self.network_cache.values())
            total_accesses = sum(entry.access_count for entry in self.network_cache.values())

            return {
                'cached_networks': len(self.network_cache),
                'total_memory_mb': round(total_memory, 2),
                'average_memory_mb': round(total_memory / len(self.network_cache), 2),
                'cache_paths': list(self.network_cache.keys()),
                'total_accesses': total_accesses,
                'memory_threshold_mb': self.memory_threshold_mb
            }

# Global network manager
network_manager = NetworkManager()

# ========== Data Extraction ==========

class OptimizedDataExtractor:
    """
    High-performance data extraction with intelligent caching and parallel processing
    """

    def __init__(self):
        self.extraction_cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 600  # 10 minutes for data
        self.max_cache_size = 50

    @cached_with_ttl(ttl_seconds=600)
    def extract_data_with_cache(self, network_path: str, extraction_func: str,
                               snapshots_filter: Optional[pd.Index] = None,
                               **kwargs) -> Dict[str, Any]:
        """Extract data with caching and validation"""

        # Validate extraction function
        if not hasattr(pau, extraction_func):
            raise ValueError(f"Unknown extraction function: {extraction_func}")

        # Load network
        network = network_manager.load_network(network_path)

        # Get extraction function
        extraction_function = getattr(pau, extraction_func)

        # Prepare arguments with validation
        func_args = {'n': network}
        if snapshots_filter is not None:
            func_args['snapshots_slice'] = snapshots_filter

        # Add and validate kwargs
        import inspect
        sig = inspect.signature(extraction_function)
        valid_args = {k: v for k, v in {**func_args, **kwargs}.items()
                     if k in sig.parameters}

        logger.info(f"Extracting data using {extraction_func} with {len(valid_args)} parameters")

        try:
            result = extraction_function(**valid_args)

            # Validate result
            if result is None:
                raise ValueError(f"Extraction function {extraction_func} returned None")

            return result

        except Exception as e:
            logger.error(f"Error in data extraction {extraction_func}: {e}")
            raise

# Global data extractor
data_extractor = OptimizedDataExtractor()

# ========== Route Handlers ==========

@pypsa_bp.route('/modeling')
@require_project
@track_performance(threshold_ms=2000)
@handle_exceptions('pypsa')
def pypsa_modeling_route():
    """PyPSA modeling interface"""
    logger.info("Loading PyPSA modeling page")

    try:
        # Get cached page data
        page_data = get_cached_modeling_page_data()

        if 'error' in page_data:
            flash(f'Error loading PyPSA modeling: {page_data["error"]}', 'danger')
            return redirect(url_for('core.home'))

        return render_template('pypsa_modeling.html', **page_data)

    except Exception as e:
        logger.exception(f"Error in PyPSA modeling route: {e}")
        flash(f'Error loading PyPSA modeling: {str(e)}', 'danger')
        return redirect(url_for('core.home'))

@pypsa_bp.route('/results')
@require_project
@track_performance(threshold_ms=1500)
@handle_exceptions('pypsa')
def pypsa_results_route():
    """PyPSA results interface"""
    logger.info("Loading PyPSA results page")

    try:
        # Get basic page data
        page_data = get_basic_results_page_data()

        if 'error' in page_data:
            flash(f'Error loading results: {page_data["error"]}', 'danger')
            return redirect(url_for('core.home'))

        return render_template('pypsa_results.html', **page_data)

    except Exception as e:
        logger.exception(f"Error in PyPSA results route: {e}")
        flash(f'Error loading PyPSA results: {str(e)}', 'danger')
        return redirect(url_for('core.home'))

@pypsa_bp.route('/api/network_info/<path:network_rel_path>')
@api_route(cache_ttl=600)
def get_network_info_api(network_rel_path):
    """network info endpoint with comprehensive validation"""
    try:
        # Validate and get full path
        full_path = validate_and_get_network_path(network_rel_path)

        # Load network
        network = network_manager.load_network(full_path)

        # Extract comprehensive info
        info = extract_network_info(network, network_rel_path)

        return success_json("Network information retrieved successfully", info)

    except ValueError as e:
        return validation_error_json(str(e))
    except FileNotFoundError:
        return error_json(f'Network file not found: {network_rel_path}', status_code=404)
    except Exception as e:
        logger.exception(f"Error getting network info: {e}")
        return error_json(f"Failed to get network info: {str(e)}")

@pypsa_bp.route('/api/dispatch_data/<path:network_rel_path>')
@api_route(cache_ttl=300)
@memory_efficient_operation
def get_dispatch_data_api(network_rel_path):
    """dispatch data endpoint with optimized processing"""
    return get_pypsa_data(network_rel_path, 'dispatch_data_payload_former')

@pypsa_bp.route('/api/capacity_data/<path:network_rel_path>')
@api_route(cache_ttl=300)
@memory_efficient_operation
def get_capacity_data_api(network_rel_path):
    """capacity data endpoint"""
    return get_pypsa_data(network_rel_path, 'capacity_data_payload_former')

@pypsa_bp.route('/api/transmission_data/<path:network_rel_path>')
@api_route(cache_ttl=300)
@memory_efficient_operation
def get_transmission_data_api(network_rel_path):
    """transmission data endpoint"""
    return get_pypsa_data(network_rel_path, 'transmission_data_payload_former')

@pypsa_bp.route('/api/compare_networks', methods=['POST'])
@api_route(required_json_fields=['file_paths'])
@memory_efficient_operation
def compare_networks_api():
    """network comparison with parallel processing and validation"""
    try:
        data = request.get_json()
        file_paths = data.get('file_paths', [])
        comparison_type = data.get('comparison_type', 'capacity')

        # validation
        if not isinstance(file_paths, list):
            return validation_error_json("file_paths must be a list")

        if len(file_paths) < 2:
            return validation_error_json('At least 2 networks required for comparison')

        if len(file_paths) > 8:  # Reduced limit for stability
            return validation_error_json('Maximum 8 networks can be compared')

        # Validate all paths first
        validated_paths = []
        for file_path in file_paths:
            try:
                full_path = validate_and_get_network_path(file_path)
                validated_paths.append(full_path)
            except Exception as e:
                return validation_error_json(f"Invalid path '{file_path}': {str(e)}")

        # Load networks in parallel with error handling
        networks = load_networks_parallel(validated_paths)

        if len(networks) < 2:
            return error_json("Failed to load sufficient networks for comparison")

        # Perform comparison
        comparison_result = pau.compare_networks_results(
            networks,
            comparison_type=comparison_type,
            **data.get('comparison_params', {})
        )

        # Add metadata
        comparison_result['metadata'] = {
            'networks_compared': len(networks),
            'comparison_type': comparison_type,
            'successful_loads': len(networks),
            'failed_loads': len(file_paths) - len(networks),
            'timestamp': time.time()
        }

        return success_json("Network comparison completed successfully", comparison_result)

    except Exception as e:
        logger.exception(f"Error comparing networks: {e}")
        return error_json(f"Network comparison failed: {str(e)}")

@pypsa_bp.route('/api/available_networks')
@api_route(cache_ttl=180)
def get_available_networks_api():
    """Get available PyPSA networks with metadata"""
    try:
        pypsa_folder = get_pypsa_results_folder()
        if not pypsa_folder or not os.path.exists(pypsa_folder):
            return success_json("No PyPSA results folder found", {'networks': []})

        networks = []

        # Scan for network files
        for root, dirs, files in os.walk(pypsa_folder):
            for file in files:
                if file.endswith('.nc'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, pypsa_folder)

                    try:
                        file_info = get_file_info(file_path)
                        networks.append({
                            'name': file,
                            'relative_path': rel_path,
                            'full_path': file_path,
                            'size_mb': file_info.get('size_mb', 0),
                            'modified': file_info.get('modified', ''),
                            'directory': os.path.dirname(rel_path)
                        })
                    except Exception as e:
                        logger.warning(f"Error processing network file {file_path}: {e}")

        # Sort by modification time (newest first)
        networks.sort(key=lambda x: x.get('modified', ''), reverse=True)

        return success_json(
            "Available networks retrieved successfully",
            {
                'networks': networks,
                'total_count': len(networks),
                'cache_stats': network_manager.get_cache_stats()
            }
        )

    except Exception as e:
        logger.exception(f"Error getting available networks: {e}")
        return error_json(f"Failed to get available networks: {str(e)}")

@pypsa_bp.route('/api/system_status')
@api_route(cache_ttl=60)
def get_system_status_api():
    """Get PyPSA system status and performance metrics"""
    try:
        # Memory status
        memory_status = network_manager._check_memory_status()

        # Cache statistics
        cache_stats = network_manager.get_cache_stats()

        # System metrics
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'active_threads': threading.active_count()
        }

        # Determine overall health
        health_status = 'healthy'
        if memory_status['critical'] or system_metrics['memory_percent'] > 90:
            health_status = 'critical'
        elif memory_status['warning'] or system_metrics['memory_percent'] > 80:
            health_status = 'warning'

        return success_json(
            "System status retrieved successfully",
            {
                'health_status': health_status,
                'memory_status': memory_status,
                'cache_stats': cache_stats,
                'system_metrics': system_metrics,
                'pypsa_folder_available': get_pypsa_results_folder() is not None,
                'timestamp': time.time()
            }
        )

    except Exception as e:
        logger.exception(f"Error getting system status: {e}")
        return error_json(f"Failed to get system status: {str(e)}")

# ========== Helper Functions ==========

def validate_and_get_network_path(network_rel_path: str) -> str:
    """Validate network path and return full path with security"""
    if not network_rel_path or '..' in network_rel_path:
        raise ValueError("Invalid network path format")

    pypsa_folder = get_pypsa_results_folder()
    if not pypsa_folder:
        raise ValueError("PyPSA results folder not configured")

    full_path = os.path.normpath(os.path.join(pypsa_folder, network_rel_path))

    # security check
    if not full_path.startswith(os.path.normpath(pypsa_folder)):
        raise ValueError("Path outside allowed directory")

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Network file not found: {network_rel_path}")

    # Additional validation for .nc files
    if not full_path.endswith('.nc'):
        raise ValueError("Invalid network file format - must be .nc file")

    return full_path

def get_pypsa_results_folder() -> Optional[str]:
    """Get PyPSA results folder with validation"""
    try:
        project_path = current_app.config.get('CURRENT_PROJECT_PATH')
        if not project_path:
            return None

        pypsa_folder = os.path.join(project_path, 'results', 'Pypsa_results')
        return pypsa_folder if os.path.exists(pypsa_folder) else None

    except Exception as e:
        logger.error(f"Error getting PyPSA results folder: {e}")
        return None

def load_networks_parallel(file_paths: List[str]) -> Dict[str, pypsa.Network]:
    """Load multiple networks in parallel with error handling"""
    networks = {}

    def load_single_network_safe(file_path: str) -> Tuple[str, Optional[pypsa.Network], Optional[str]]:
        try:
            network = network_manager.load_network(file_path)
            return file_path, network, None
        except Exception as e:
            logger.error(f"Error loading network {file_path}: {e}")
            return file_path, None, str(e)

    # Use thread pool with limited workers
    max_workers = min(3, len(file_paths))  # Limit concurrent loads

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(load_single_network_safe, path) for path in file_paths]

        for future in as_completed(futures):
            file_path, network, error = future.result()

            if network is not None:
                # Use filename as key for networks dict
                network_name = os.path.basename(file_path)
                networks[network_name] = network
            else:
                logger.warning(f"Failed to load network {file_path}: {error}")

    return networks

def get_pypsa_data(network_rel_path: str, extraction_func: str, **kwargs):
    """data extraction with comprehensive error handling"""
    try:
        # Validate path
        full_path = validate_and_get_network_path(network_rel_path)

        # Parse request parameters
        filters = {
            'period': request.args.get('period'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'resolution': request.args.get('resolution', '1H'),
        }

        # Get filtered snapshots
        network = network_manager.load_network(full_path)
        snapshots = get_filtered_snapshots(network, filters)

        # Extract data with caching
        result = data_extractor.extract_data_with_cache(
            full_path, extraction_func, snapshots,
            **filters, **kwargs
        )

        # Get color palette if available
        colors = {}
        if hasattr(pau, 'get_color_palette'):
            try:
                colors = pau.get_color_palette(network)
            except Exception as e:
                logger.warning(f"Failed to get color palette: {e}")

        # Serialize result efficiently
        serialized_result = serialize_pypsa_data(result)

        # Create response
        response_key = extraction_func.replace('_payload_former', '').replace('_data', '') + '_data'

        response_data = {
            response_key: serialized_result,
            'colors': colors,
            'metadata': {
                'network_path': network_rel_path,
                'extraction_func': extraction_func,
                'snapshots_count': len(snapshots) if snapshots is not None else 0,
                'filters_applied': {k: v for k, v in filters.items() if v},
                'extraction_time': time.time()
            }
        }

        return success_json("Data extracted successfully", response_data)

    except ValueError as e:
        return validation_error_json(str(e))
    except FileNotFoundError as e:
        return error_json(str(e), status_code=404)
    except Exception as e:
        logger.exception(f"Error in data extraction: {e}")
        return error_json(f"Data extraction failed: {str(e)}")

def get_filtered_snapshots(network: pypsa.Network, filters: Dict) -> Optional[pd.Index]:
    """Get filtered snapshots with validation"""
    try:
        snapshots = network.snapshots

        if filters.get('start_date') or filters.get('end_date'):
            start_date = pd.to_datetime(filters.get('start_date')) if filters.get('start_date') else snapshots.min()
            end_date = pd.to_datetime(filters.get('end_date')) if filters.get('end_date') else snapshots.max()

            # Validate date range
            if start_date > end_date:
                raise ValueError("Start date must be before end date")

            mask = (snapshots >= start_date) & (snapshots <= end_date)
            snapshots = snapshots[mask]

        return snapshots if len(snapshots) > 0 else None

    except Exception as e:
        logger.warning(f"Error filtering snapshots: {e}")
        return network.snapshots

def serialize_pypsa_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """data serialization with memory optimization"""
    def serialize_item_safe(item):
        try:
            if isinstance(item, pd.DataFrame):
                # Memory-efficient DataFrame serialization
                if len(item) > 5000:  # Large DataFrame
                    # Sample for performance
                    sample_size = 2500
                    sampled_df = item.head(sample_size).copy()
                    logger.info(f"Large DataFrame ({len(item)} rows) sampled to {sample_size} for response")
                    return handle_nan_values(sampled_df.to_dict(orient='records'))
                else:
                    return handle_nan_values(item.to_dict(orient='records'))
            elif isinstance(item, pd.Series):
                return handle_nan_values(item.to_dict())
            elif isinstance(item, np.ndarray):
                return handle_nan_values(item.tolist())
            else:
                return handle_nan_values(item)
        except Exception as e:
            logger.warning(f"Error serializing item: {e}")
            return {'error': f'Serialization failed: {str(e)}'}

    return {k: serialize_item_safe(v) for k, v in data.items()}



def extract_network_info(network: pypsa.Network, network_rel_path: str) -> Dict[str, Any]:
    """Extract comprehensive network information with error handling"""
    try:
        info = {
            'network_path': network_rel_path,
            'basic_info': {
                'name': os.path.basename(network_rel_path),
                'snapshots_count': len(network.snapshots),
                'snapshot_range': {
                    'start': network.snapshots.min().isoformat() if len(network.snapshots) > 0 else None,
                    'end': network.snapshots.max().isoformat() if len(network.snapshots) > 0 else None
                }
            },
            'components': {},
            'summary_statistics': {}
        }

        # Component information
        for component in network.iterate_components():
            try:
                df = component.df
                info['components'][component.name] = {
                    'count': len(df),
                    'columns': df.columns.tolist() if hasattr(df, 'columns') else []
                }
            except Exception as e:
                logger.warning(f"Error processing component {component.name}: {e}")
                info['components'][component.name] = {'error': str(e)}

        # Summary statistics
        try:
            if hasattr(network, 'generators') and len(network.generators) > 0:
                info['summary_statistics']['total_generator_capacity'] = float(
                    network.generators['p_nom'].sum()
                )

            if hasattr(network, 'loads') and len(network.loads) > 0:
                info['summary_statistics']['total_load'] = float(
                    network.loads_t.p_set.sum().sum()
                ) if hasattr(network, 'loads_t') and not network.loads_t.p_set.empty else 0

        except Exception as e:
            logger.warning(f"Error calculating summary statistics: {e}")
            info['summary_statistics']['error'] = str(e)

        return info

    except Exception as e:
        logger.error(f"Error extracting network info: {e}")
        return {'error': str(e), 'network_path': network_rel_path}

@cached_with_ttl(ttl_seconds=300)
def get_cached_modeling_page_data() -> Dict[str, Any]:
    """Get cached modeling page data with validation"""
    try:
        project_path = current_app.config.get('CURRENT_PROJECT_PATH')
        if not project_path:
            return {'error': 'No project selected'}

        input_excel_path = Path(project_path) / "inputs" / "pypsa_input_template.xlsx"

        return {
            'current_project': current_app.config.get('CURRENT_PROJECT'),
            'input_file_exists': input_excel_path.exists(),
            'input_file_info': {
                'path': str(input_excel_path),
                'exists': input_excel_path.exists(),
                'size_mb': input_excel_path.stat().st_size / (1024*1024) if input_excel_path.exists() else 0
            },
            'optimization_engines': ['glpk', 'cbc', 'highs'],
            'solver_status': check_solver_availability(),
            'cache_stats': network_manager.get_cache_stats(),
            'system_status': network_manager._check_memory_status()
        }
    except Exception as e:
        logger.error(f"Error getting modeling page data: {e}")
        return {'error': str(e)}

def get_basic_results_page_data() -> Dict[str, Any]:
    """Get basic results page data with error handling"""
    try:
        pypsa_folder = get_pypsa_results_folder()
        scenarios = []

        if pypsa_folder and os.path.exists(pypsa_folder):
            # directory scanning
            for item in os.listdir(pypsa_folder):
                item_path = os.path.join(pypsa_folder, item)
                if os.path.isdir(item_path):
                    try:
                        # Count network files
                        nc_files = [f for f in os.listdir(item_path) if f.endswith('.nc')]
                        scenarios.append({
                            'name': item,
                            'path': item_path,
                            'file_count': len(nc_files),
                            'files': nc_files
                        })
                    except Exception as e:
                        logger.warning(f"Error processing scenario directory {item}: {e}")

        return {
            'scenarios': scenarios,
            'current_project': current_app.config.get('CURRENT_PROJECT', 'N/A'),
            'pypsa_folder': pypsa_folder,
            'cache_stats': network_manager.get_cache_stats(),
            'memory_stats': network_manager._check_memory_status()
        }
    except Exception as e:
        logger.error(f"Error getting basic results data: {e}")
        return {'error': str(e)}

def check_solver_availability() -> Dict[str, bool]:
    """Check availability of optimization solvers with detection"""
    solvers = {}

    solver_commands = {
        'glpk': ['glpsol', '--version'],
        'cbc': ['cbc', '-version'],
        'highs': ['highs', '--version']
    }

    for solver, command in solver_commands.items():
        try:
            import subprocess
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5
            )
            solvers[solver] = result.returncode == 0
        except Exception:
            solvers[solver] = False

    return solvers

# ========== Blueprint Cleanup ==========

@pypsa_bp.teardown_request
def cleanup_pypsa_resources(exception):
    """cleanup of PyPSA resources after request"""
    if exception:
        logger.error(f"PyPSA request ended with exception: {exception}")

    # Periodic cache cleanup with smart timing
    if hasattr(g, 'request_count'):
        g.request_count += 1
        # More frequent cleanup for memory-intensive operations
        if g.request_count % 10 == 0:
            network_manager._cleanup_cache()
    else:
        g.request_count = 1

    # Force garbage collection for large operations
    if hasattr(g, 'pypsa_large_operation'):
        gc.collect()

# Register shutdown handler
import atexit

def cleanup_on_shutdown():
    """Clean up resources on application shutdown"""
    try:
        network_manager.io_executor.shutdown(wait=True)
        logger.info("PyPSA blueprint cleanup completed")
    except Exception as e:
        logger.error(f"Error during PyPSA cleanup: {e}")

atexit.register(cleanup_on_shutdown)

# ========== Blueprint Registration ==========

def register_pypsa_bp(app):
    """Register the PyPSA blueprint"""
    try:
        app.register_blueprint(pypsa_bp)
        logger.info("PyPSA blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register PyPSA blueprint: {e}")
        raise
[end of blueprints/pypsa_bp.py]
