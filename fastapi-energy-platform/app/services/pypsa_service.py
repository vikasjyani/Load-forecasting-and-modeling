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

    async def add_log_entry(self, job_id: str, message: str, level: str = "INFO"):
        async with self.lock:
            if job_id in self.jobs:
                log_message = f"{datetime.now().isoformat()} - {level} - {message}"
                self.jobs[job_id].log.append(log_message)
                if len(self.jobs[job_id].log) > 200: # Keep log manageable
                    self.jobs[job_id].log = self.jobs[job_id].log[-100:] # Keep last 100
            else:
                logger.warning(f"Attempted to add log entry for non-existent PyPSA job: {job_id}")


    async def complete_job(self, job_id: str, result_summary: Dict[str, Any]):
        async with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = JOB_STATUS['COMPLETED']
                self.jobs[job_id].progress = 100
                self.jobs[job_id].end_time_iso = datetime.now().isoformat()
                self.jobs[job_id].result_summary = result_summary
                # Log completion via add_log_entry for consistency
                await self.add_log_entry(job_id, f"COMPLETED - Results: {result_summary.get('output_network_path', 'N/A')}")
            else:
                logger.warning(f"Attempted to complete non-existent PyPSA job: {job_id}")

    async def fail_job(self, job_id: str, error_message: str):
        async with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = JOB_STATUS['FAILED']
                # self.jobs[job_id].progress = 100 # Or current progress if preferred - let's keep current progress
                self.jobs[job_id].end_time_iso = datetime.now().isoformat()
                self.jobs[job_id].error_message = error_message
                await self.add_log_entry(job_id, f"FAILED - Error: {error_message}", level="ERROR")
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

        # Capture the current event loop in the context where run_pypsa_simulation is called (i.e., FastAPI's main thread for the request)
        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # This might happen if called from a context without a running loop, though unlikely in FastAPI request cycle
            logger.error(f"Job {job.id}: Could not get running event loop for PyPSA simulation task. Status updates might fail.")
            # Fallback or re-raise, depending on desired robustness. For now, let it proceed but log.
            event_loop = None # Or handle error more strictly

        background_tasks.add_task(
            run_pypsa_model_core,
            job.id,
            project_path_str,
            scenario_name,
            ui_settings_overrides,
            pypsa_job_manager,
            event_loop # Pass the captured event loop
        )

        return job

    async def get_simulation_status(self, job_id: str) -> Optional[PyPSAJob]:
        return await pypsa_job_manager.get_job(job_id)

    async def list_available_network_files(self, project_name: str, scenario_name: Optional[str] = None) -> List[PyPSANetworkInfo]:
        """Lists available PyPSA scenarios or network .nc files within a scenario."""
        base_results_path = self._get_pypsa_results_path(project_name) # .../results/pypsa

        scan_path: Path
        if scenario_name:
            scan_path = base_results_path / safe_filename(scenario_name)
            listing_type = ".nc files"
        else:
            scan_path = base_results_path
            listing_type = "scenario folders"

        network_files_info = []
        if not await asyncio.to_thread(scan_path.is_dir):
            logger.info(f"PyPSA {listing_type} directory not found for project '{project_name}' (path: {scan_path})")
            return []

        try:
            items = await asyncio.to_thread(list, scan_path.iterdir())
        except FileNotFoundError:
            logger.warning(f"Path not found during network listing: {scan_path}")
            return []

        for item_path in items:
            if scenario_name: # Listing .nc files
                if await asyncio.to_thread(item_path.is_file) and item_path.suffix == '.nc':
                    file_info = await get_file_info(item_path)
                    # For .nc files within a scenario, relative_path is just the filename
                    network_files_info.append(PyPSANetworkInfo(
                        name=item_path.stem, # e.g., "my_scenario_2025_network"
                        relative_path=item_path.name, # e.g., "my_scenario_2025_network.nc"
                        full_path=str(item_path),
                        size_mb=file_info.get('size_mb'),
                        last_modified_iso=file_info.get('modified_iso')
                    ))
            else: # Listing scenario directories
                 if await asyncio.to_thread(item_path.is_dir):
                    network_files_info.append(PyPSANetworkInfo(
                        name=item_path.name,
                        relative_path=item_path.name,
                        full_path=str(item_path)
                        # Could add a quick scan for .nc files inside for a count, if needed here
                    ))
        network_files_info.sort(key=lambda x: x.last_modified_iso or "0", reverse=True)
        return network_files_info

    async def _load_pypsa_network(self, network_path: Path) -> pypsa.Network:
        """Loads a PyPSA network from a .nc file with simple caching."""
        abs_path_str = str(network_path.resolve())

        async with self._cache_lock:
            current_mtime = 0.0
            if await asyncio.to_thread(network_path.exists):
                current_mtime = (await asyncio.to_thread(network_path.stat)).st_mtime

            if abs_path_str in self._network_cache and self._network_mtimes.get(abs_path_str) == current_mtime:
                logger.info(f"Cache hit for PyPSA network: {network_path.name}")
                return self._network_cache[abs_path_str]

        # If not in cache or modified, load it (outside the lock to allow other cache access)
        logger.info(f"Loading PyPSA network: {network_path.name}")
        if not await asyncio.to_thread(network_path.exists):
            raise FileNotFoundError(f"PyPSA network file not found: {network_path}")

        try:
            network = await asyncio.to_thread(pypsa.Network, abs_path_str)

            async with self._cache_lock: # Re-acquire lock to update cache
                self._network_cache[abs_path_str] = network
                self._network_mtimes[abs_path_str] = current_mtime
                # Simple cache eviction: if cache too large, remove oldest accessed (not implemented here, basic size limit)
                if len(self._network_cache) > self.settings.PYPSA_NETWORK_CACHE_SIZE: # Assuming PYPSA_NETWORK_CACHE_SIZE in settings
                    oldest_key = next(iter(self._network_cache)) # Simplistic: removes based on insertion order
                    del self._network_cache[oldest_key]
                    if oldest_key in self._network_mtimes: del self._network_mtimes[oldest_key]
                    logger.info(f"PyPSA network cache full. Removed oldest entry: {Path(oldest_key).name}")
            return network
        except Exception as e:
            logger.exception(f"Error loading PyPSA network {network_path.name}: {e}")
            raise ProcessingError(f"Failed to load PyPSA network '{network_path.name}': {str(e)}")


    async def get_network_info(self, project_name: str, scenario_name: str, network_file_name: str) -> Dict[str, Any]:
        """Gets basic information about a specific PyPSA network file."""
        network_path = self._get_pypsa_results_path(project_name, scenario_name) / network_file_name
        network = await self._load_pypsa_network(network_path) # Handles FileNotFoundError

        # Extract info (adapted from pau.extract_network_info or Flask's version)
        info = {
            'file_name': network_file_name,
            'full_path_on_server': str(network_path), # For server reference
            'snapshots': {
                'count': len(network.snapshots),
                'start': str(network.snapshots.min()) if not network.snapshots.empty else None,
                'end': str(network.snapshots.max()) if not network.snapshots.empty else None,
                'freq': str(pd.infer_freq(network.snapshots)) if not network.snapshots.empty else None,
            },
            'components': {},
            'objective_value': float(network.objective) if hasattr(network, 'objective') else None
        }
        for component_name in pypsa.Network.components:
            comp_df = getattr(network, component_name)
            if not comp_df.empty:
                info['components'][component_name] = {
                    'count': len(comp_df),
                    'columns': comp_df.columns.tolist()
                }
        return info

    async def get_network_data(
        self,
        project_name: str,
        scenario_name: str,
        network_file_name: str,
        extraction_func_name: str,
        filters: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Loads a specific PyPSA network and extracts data using a function from pypsa_analysis_utils.
        """
        network_path = self._get_pypsa_results_path(project_name, scenario_name) / network_file_name
        network = await self._load_pypsa_network(network_path)

        # Dynamically get the extraction function from app.utils.pypsa_analysis_utils
        # Ensure pau is imported or available in the scope
        try:
            # Assuming pau is imported as `import app.utils.pypsa_analysis_utils as pau`
            # This needs to be at the top of the file.
            import app.utils.pypsa_analysis_utils as pau
            if not hasattr(pau, extraction_func_name):
                raise AttributeError(f"Extraction function '{extraction_func_name}' not found in pypsa_analysis_utils.")

            func_to_call = getattr(pau, extraction_func_name)
        except AttributeError as e:
            logger.error(f"PyPSA Analysis Util function error: {e}", exc_info=True)
            raise ValueError(f"Invalid data extraction function: {extraction_func_name}")

        # Prepare arguments for the pau function
        # Common arguments for pau functions are 'n' (network) and 'snapshots_slice'
        # Others can be passed via **kwargs or extracted from filters
        call_args = {"n": network, "snapshots_slice": None} # Default to all snapshots

        # Process filters if provided (e.g., to create snapshots_slice or pass as specific args)
        # This part needs to be robust based on how filters are defined and used by pau functions.
        # Example: if filters contain 'start_date' and 'end_date', create a snapshot slice.
        # For now, passing filters directly if pau functions expect them, plus other kwargs.
        if filters:
            call_args.update(filters)
        if kwargs:
            call_args.update(kwargs)

        # Some pau functions might modify the network (e.g. add colors); consider passing a copy if that's an issue.
        # For read-only operations, direct pass is fine.

        logger.info(f"Calling PyPSA analysis util: {extraction_func_name} for network {network_file_name}")
        try:
            # pau functions are synchronous and can be CPU/memory intensive
            extracted_data = await asyncio.to_thread(func_to_call, **call_args)
        except Exception as e:
            logger.exception(f"Error during execution of pau.{extraction_func_name}: {e}")
            raise ProcessingError(f"Data extraction failed using {extraction_func_name}: {str(e)}")

        # Ensure result is a dictionary (pau payload_formers should return dicts)
        if not isinstance(extracted_data, dict):
            logger.warning(f"Extraction function {extraction_func_name} did not return a dict. Result type: {type(extracted_data)}")
            # Attempt to convert if possible, or wrap it
            if hasattr(extracted_data, 'to_dict'): # e.g. pandas Series/DataFrame
                extracted_data = {"data": extracted_data.to_dict(orient='records' if isinstance(extracted_data, pd.DataFrame) else 'dict')}
            else:
                extracted_data = {"data": extracted_data} # Generic wrapping

        # Try to get a color palette (some pau functions might return it, others might not)
        colors = {}
        if hasattr(pau, 'get_color_palette'):
            try:
                colors = await asyncio.to_thread(pau.get_color_palette, network)
            except Exception as e_color:
                logger.warning(f"Could not retrieve color palette for network {network_file_name}: {e_color}")

        return {
            "data": extracted_data,
            "colors": colors,
            "metadata": {
                "project_name": project_name,
                "scenario_name": scenario_name,
                "network_file_name": network_file_name,
                "extraction_function": extraction_func_name,
                "filters_applied": filters,
                "kwargs_applied": kwargs,
                "timestamp": datetime.now().isoformat()
            }
        }

    async def compare_networks_data(
        self,
        project_name: str,
        network_specs: List[Dict[str, str]], # List of {"scenario_name": "s_name", "network_file_name": "nf_name.nc", "label": "custom_label"}
        comparison_func_name: str, # e.g., "compare_networks_results" from pau
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Loads multiple PyPSA networks and compares them using a function from pypsa_analysis_utils."""
        if len(network_specs) < 2:
            raise ValueError("At least two networks are required for comparison.")

        loaded_networks: Dict[str, pypsa.Network] = {}
        network_load_tasks = []

        for spec in network_specs:
            scenario_name = spec.get("scenario_name")
            network_file_name = spec.get("network_file_name")
            label = spec.get("label", f"{scenario_name}_{network_file_name}")
            if not scenario_name or not network_file_name:
                raise ValueError(f"Invalid network specification for comparison: {spec}. Must include 'scenario_name' and 'network_file_name'.")

            network_path = self._get_pypsa_results_path(project_name, scenario_name) / network_file_name
            # Create a task for each network load
            network_load_tasks.append(self._load_pypsa_network(network_path))

        # Load networks concurrently
        try:
            networks_list = await asyncio.gather(*network_load_tasks, return_exceptions=True)
        except Exception as e_gather: # Should not happen if return_exceptions=True
            logger.error(f"Unexpected error during asyncio.gather for network loading: {e_gather}")
            raise ProcessingError(f"Failed to initiate loading of networks for comparison.")

        for i, result_or_exc in enumerate(networks_list):
            spec = network_specs[i]
            label = spec.get("label", f"{spec.get('scenario_name')}_{spec.get('network_file_name')}")
            if isinstance(result_or_exc, pypsa.Network):
                loaded_networks[label] = result_or_exc
            else: # An exception occurred for this network
                error_msg = f"Failed to load network {spec.get('network_file_name')} from scenario {spec.get('scenario_name')}: {str(result_or_exc)}"
                logger.error(error_msg)
                # Depending on desired behavior, either raise error or exclude this network from comparison
                raise ProcessingError(error_msg) # Fail fast if any network fails to load

        if len(loaded_networks) < 2:
            raise ProcessingError("Fewer than two networks were successfully loaded for comparison.")

        # Dynamically get the comparison function
        import app.utils.pypsa_analysis_utils as pau
        if not hasattr(pau, comparison_func_name):
            raise AttributeError(f"Comparison function '{comparison_func_name}' not found in pypsa_analysis_utils.")
        func_to_call = getattr(pau, comparison_func_name)

        call_args = {"networks_dict": loaded_networks} # pau.compare_networks_results expects a dict
        if params:
            call_args.update(params)

        logger.info(f"Calling PyPSA comparison util: {comparison_func_name} for {len(loaded_networks)} networks.")
        try:
            comparison_results = await asyncio.to_thread(func_to_call, **call_args)
        except Exception as e:
            logger.exception(f"Error during execution of pau.{comparison_func_name}: {e}")
            raise ProcessingError(f"Network comparison failed using {comparison_func_name}: {str(e)}")

        return comparison_results


    async def get_pypsa_system_status(self) -> Dict[str, Any]:
        """Returns status information about the PyPSA service, like cache state."""
        async with self._cache_lock:
            cache_size = len(self._network_cache)
            cached_items_info = [
                {"path": path_str, "mtime": mtime} for path_str, mtime in self._network_mtimes.items()
            ]

        # Assuming settings are available via self.settings if this service is DI-managed with settings
        max_cache_size = getattr(self.settings, "PYPSA_NETWORK_CACHE_SIZE", "Not Set") if hasattr(self, 'settings') else "N/A"

        return {
            "network_cache_current_size": cache_size,
            "network_cache_max_size": max_cache_size,
            "cached_network_files_info": cached_items_info,
            "active_simulation_jobs": len(pypsa_job_manager.jobs), # Accessing global manager directly
            "job_manager_status": "operational" # Could add more details from job_manager if needed
        }

logger.info("PyPSA Service structure defined.")
