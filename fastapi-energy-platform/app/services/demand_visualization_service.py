# fastapi-energy-platform/app/services/demand_visualization_service.py
"""
Demand Visualization Service for FastAPI
Provides data for visualizing demand forecasts and scenarios.
"""
import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# Assuming utilities are adapted and available
# from app.utils.helpers import ... # Specific helpers if needed
# from app.config import Settings # For configured paths

logger = logging.getLogger(__name__)

@dataclass
class ScenarioInfo:
    name: str
    path: str # Should be relative to a base or not stored directly if security sensitive
    sectors_count: int
    year_range: Dict[str, int]
    has_data: bool # Indicates if any processable data found
    file_count: int = 0
    last_modified_iso: Optional[str] = None # ISO format string

@dataclass
class SectorData:
    sector_name: str
    years: List[int]
    models_available: List[str]
    # Store data as model_name: [values]
    model_data: Dict[str, List[float]] = field(default_factory=dict)

@dataclass
class ScenarioOutput:
    scenario_name: str
    sectors_data: Dict[str, SectorData] # Key: sector_name
    all_years_in_scenario: List[int] = field(default_factory=list)
    all_models_in_scenario: List[str] = field(default_factory=list)
    applied_filters: Dict[str, Any] = field(default_factory=dict)
    unit: str = "TWh" # Default unit for display

class DemandVisualizationService:
    """Service for demand visualization tasks."""

    def __init__(self, project_data_root: Path):
        # project_data_root is the base directory like 'user_projects_data/'
        self.project_data_root = project_data_root
        self.unit_factors = {'kWh': 1, 'MWh': 1e3, 'GWh': 1e6, 'TWh': 1e9}
        logger.info(f"DemandVisualizationService initialized for project data root: {self.project_data_root}")

    def _get_scenario_base_path(self, project_name: str) -> Path:
        # Ensure project_name is safe for path construction
        safe_project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
        return self.project_data_root / safe_project_name / "results" / "demand_projection"

    async def list_available_scenarios(self, project_name: str) -> List[ScenarioInfo]:
        """Lists available forecast scenarios for a given project."""
        scenarios_base_path = self._get_scenario_base_path(project_name)
        if not scenarios_base_path.exists() or not scenarios_base_path.is_dir():
            logger.warning(f"Scenarios path does not exist for project '{project_name}': {scenarios_base_path}")
            return []

        scenario_infos_raw = []
        import asyncio # Ensure asyncio is imported

        # Get directory items asynchronously
        try:
            dir_items = await asyncio.to_thread(list, scenarios_base_path.iterdir())
        except OSError as e:
            logger.error(f"Error iterating scenarios directory {scenarios_base_path} for project '{project_name}': {e}")
            return []

        tasks = []
        for item_path in dir_items:
            # Check if item is directory asynchronously
            is_dir = await asyncio.to_thread(item_path.is_dir)
            if is_dir: # Each scenario is a directory
                tasks.append(self._analyze_scenario_directory_async(item_path.name, item_path, project_name))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, ScenarioInfo) and res.has_data:
                    scenario_infos_raw.append(res)
                elif isinstance(res, Exception):
                    # Log the exception, already logged in _analyze_scenario_directory_async if it's from there
                    logger.warning(f"An exception was returned from scenario analysis: {res}")


        scenario_infos_raw.sort(key=lambda s: s.last_modified_iso or "", reverse=True)
        logger.info(f"Found {len(scenario_infos_raw)} valid scenarios for project '{project_name}'.")
        return scenario_infos_raw

    async def _analyze_scenario_directory_async(self, scenario_dir_name: str, scenario_path: Path, project_name: str) -> Optional[ScenarioInfo]:
        """Asynchronously analyzes a scenario directory for metadata."""
        import asyncio # Ensure asyncio is imported
        excel_files_paths = []
        try:
            dir_items = await asyncio.to_thread(list, scenario_path.iterdir())
            for f in dir_items:
                is_file = await asyncio.to_thread(f.is_file)
                if is_file and f.suffix == '.xlsx' and not f.name.startswith(('_', '~')):
                    excel_files_paths.append(f)
        except OSError as e:
            logger.error(f"Error iterating scenario directory {scenario_path} for project '{project_name}': {e}")
            return None


        year_min, year_max = 2025, 2037 # Defaults
        last_mod_timestamp = 0.0

        if excel_files_paths:
            for f_path in excel_files_paths[:3]: # Quick scan a few files
                try:
                    stat_info = await asyncio.to_thread(f_path.stat)
                    if stat_info.st_mtime > last_mod_timestamp:
                        last_mod_timestamp = stat_info.st_mtime
                    # Simplified year extraction (can be computationally intensive with pd.read_excel)
                    # For a quick analysis, this part might be omitted or simplified further
                    # to avoid many blocking pd.read_excel calls even with to_thread.
                    # Consider storing metadata in a separate JSON if this becomes too slow.
                except Exception as e_file:
                    logger.debug(f"Could not quickly analyze file {f_path.name} for scenario {scenario_dir_name}: {e_file}")

        if not excel_files_paths: # No data if no excel files
             return ScenarioInfo(
                name=scenario_dir_name, path=str(scenario_path),
                sectors_count=0, year_range={'min': 0, 'max': 0},
                has_data=False, file_count=0,
                last_modified_iso=None
            )

        return ScenarioInfo(
            name=scenario_dir_name, path=str(scenario_path),
            sectors_count=len(excel_files_paths), year_range={'min': year_min, 'max': year_max},
            has_data=bool(excel_files_paths), file_count=len(excel_files_paths),
            last_modified_iso=datetime.fromtimestamp(last_mod_timestamp).isoformat() if last_mod_timestamp > 0 else None
        )

    async def get_scenario_data(self, project_name: str, scenario_name: str, filters: Optional[Dict] = None) -> ScenarioOutput:
        """
        Retrieves and processes data for a specific scenario, applying filters.
        Filters example: {'unit': 'GWh', 'start_year': 2025, 'end_year': 2040, 'sectors': ['Residential']}
        """
        import asyncio # Ensure asyncio is imported
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name

        path_exists = await asyncio.to_thread(scenario_path.exists)
        is_dir = await asyncio.to_thread(scenario_path.is_dir)
        if not path_exists or not is_dir:
            raise FileNotFoundError(f"Scenario '{scenario_name}' not found in project '{project_name}'.")

        filters = filters or {}
        unit = filters.get('unit', 'TWh')
        start_year_filter = filters.get('start_year')
        end_year_filter = filters.get('end_year')
        selected_sectors_filter = filters.get('sectors')

        processed_sectors_data: Dict[str, SectorData] = {}
        all_years_set = set()
        all_models_set = set()

        tasks = []
        try:
            dir_items = await asyncio.to_thread(list, scenario_path.iterdir())
        except OSError as e:
            logger.error(f"Error iterating scenario directory {scenario_path} for data processing: {e}")
            # Depending on desired behavior, could raise error or return empty output
            return ScenarioOutput(scenario_name=scenario_name, sectors_data={}, applied_filters=filters, unit=unit)


        for file_path in dir_items:
            is_file = await asyncio.to_thread(file_path.is_file)
            if is_file and file_path.suffix == '.xlsx' and not file_path.name.startswith(('_', '~')):
                sector_name_from_file = file_path.stem
                if selected_sectors_filter and sector_name_from_file not in selected_sectors_filter:
                    continue
                tasks.append(self._load_and_process_single_sector_file_async(
                    file_path, sector_name_from_file, unit, start_year_filter, end_year_filter
                ))

        if tasks:
            sector_results = await asyncio.gather(*tasks)
            for sector_data_obj in sector_results:
                if sector_data_obj:
                    processed_sectors_data[sector_data_obj.sector_name] = sector_data_obj
                    all_years_set.update(sector_data_obj.years)
                    all_models_set.update(sector_data_obj.models_available)

        return ScenarioOutput(
            scenario_name=scenario_name,
            sectors_data=processed_sectors_data,
            all_years_in_scenario=sorted(list(all_years_set)) if all_years_set else [],
            all_models_in_scenario=sorted(list(all_models_set)) if all_models_set else [],
            applied_filters=filters,
            unit=unit
        )

    async def _load_and_process_single_sector_file_async(
        self, file_path: Path, sector_name: str, target_unit: str,
        start_year: Optional[int], end_year: Optional[int]
    ) -> Optional[SectorData]:
        import asyncio # Ensure asyncio is imported
        try:
            # Asynchronously read Excel file using pandas in a thread
            def _read_excel_sync():
                # Determine sheet name (Results or first sheet)
                # pd.ExcelFile is also I/O bound
                xls_file = pd.ExcelFile(file_path)
                sheet_name_to_read = 'Results' if 'Results' in xls_file.sheet_names else xls_file.sheet_names[0]
                return pd.read_excel(xls_file, sheet_name=sheet_name_to_read)

            df = await asyncio.to_thread(_read_excel_sync)

            year_col_name = next((col for col in df.columns if 'year' in str(col).lower()), None)
            if not year_col_name: return None # No year column

            df[year_col_name] = pd.to_numeric(df[year_col_name], errors='coerce').dropna().astype(int)
            df = df.dropna(subset=[year_col_name])

            if start_year: df = df[df[year_col_name] >= start_year]
            if end_year: df = df[df[year_col_name] <= end_year]
            if df.empty: return None

            df = df.sort_values(year_col_name)
            years_list = df[year_col_name].tolist()

            models_data_dict: Dict[str, List[float]] = {}
            models_available_list: List[str] = []

            # Identify potential model columns (heuristic)
            potential_model_cols = [
                col for col in df.columns if col != year_col_name and
                not str(col).lower().startswith(('unnamed', 'index', 'id')) and
                df[col].dtype in [np.number, object] # Object for numbers read as string
            ]

            unit_conversion_factor = self.unit_factors.get(target_unit, 1.0) / self.unit_factors['kWh'] # Convert from kWh base

            for col_name in potential_model_cols:
                # Attempt to convert column to numeric, coercing errors.
                numeric_series = pd.to_numeric(df[col_name], errors='coerce')
                if not numeric_series.isna().all(): # If at least one number exists
                    models_available_list.append(str(col_name))
                    # Convert from kWh (assumed base) to target_unit
                    converted_values = (numeric_series.fillna(0) * unit_conversion_factor).round(3).tolist()
                    models_data_dict[str(col_name)] = converted_values

            if not models_available_list: return None # No valid model data columns found

            return SectorData(
                sector_name=sector_name, years=years_list,
                models_available=models_available_list, model_data=models_data_dict
            )
        except Exception as e:
            logger.warning(f"Error loading data from sector file {file_path.name} for '{sector_name}': {e}")
            return None

    async def get_comparison_data(
        self, project_name: str, scenario_name1: str, scenario_name2: str, filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Prepares data for comparing two scenarios under the same project and filters."""
        # This will call get_scenario_data for both scenarios and then structure for comparison.
        # The core logic would involve finding common sectors, years, and models.
        data_s1 = await self.get_scenario_data(project_name, scenario_name1, filters)
        data_s2 = await self.get_scenario_data(project_name, scenario_name2, filters)

        # Further processing to align data for comparison (e.g., common sectors, years)
        # This part can be complex depending on how deep the comparison needs to be.
        # For now, just returning both datasets.
        return {
            "scenario1_data": data_s1, # ScenarioOutput object
            "scenario2_data": data_s2, # ScenarioOutput object
            "common_filters": filters or {}
        }

    # Methods for saving/loading UI configurations (model selection, T&D losses)
    # These would typically involve reading/writing small JSON files within the scenario's directory.
    async def save_ui_configuration(self, project_name: str, scenario_name: str, config_type: str, config_data: Dict) -> bool:
        """Saves UI related configuration (e.g., 'model_selection', 'td_losses')."""
        import asyncio # Ensure asyncio is imported
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name

        is_dir = await asyncio.to_thread(scenario_path.is_dir)
        if not is_dir:
            await asyncio.to_thread(scenario_path.mkdir, parents=True, exist_ok=True)

        config_file_path = scenario_path / f"{config_type}_config.json"

        def _dump_json_sync():
            with open(config_file_path, "w") as f:
                json.dump(config_data, f, indent=2)
        try:
            await asyncio.to_thread(_dump_json_sync)
            logger.info(f"Saved {config_type} config for {project_name}/{scenario_name}.")
            return True
        except IOError as e: # Keep specific IOError for file operations
            logger.error(f"Failed to save {config_type} config for {project_name}/{scenario_name}: {e}", exc_info=True)
            return False
        except Exception as e_gen: # Catch other potential errors from to_thread or json serialisation
            logger.error(f"Unexpected error saving {config_type} config for {project_name}/{scenario_name}: {e_gen}", exc_info=True)
            return False


    async def load_ui_configuration(self, project_name: str, scenario_name: str, config_type: str) -> Optional[Dict]:
        """Loads UI related configuration."""
        import asyncio # Ensure asyncio is imported
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name
        config_file_path = scenario_path / f"{config_type}_config.json"

        exists = await asyncio.to_thread(config_file_path.exists)
        if exists:
            def _load_json_sync():
                with open(config_file_path, "r") as f:
                    return json.load(f)
            try:
                return await asyncio.to_thread(_load_json_sync)
            except (IOError, json.JSONDecodeError) as e: # Specific errors related to file and JSON
                logger.error(f"Failed to load {config_type} config for {project_name}/{scenario_name}: {e}", exc_info=True)
            except Exception as e_gen: # Catch other potential errors
                logger.error(f"Unexpected error loading {config_type} config for {project_name}/{scenario_name}: {e_gen}", exc_info=True)
        return None

    # Consolidated results generation might be complex and could be a separate service or part of job manager
    # For now, a simplified placeholder.
    async def generate_consolidated_results(self, project_name: str, scenario_name: str,
                                            model_selection: Dict[str, str], # sector_name -> model_name
                                            td_losses_config: List[Dict], # [{'year': Y, 'loss_percentage': P}]
                                            filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Generates consolidated results including T&D losses."""
        # 1. Fetch scenario data (likely in kWh for calculations)
        # 2. Interpolate T&D losses for all relevant years.
        # 3. For each year, sum demands from selected models for each sector.
        # 4. Apply T&D losses to the total gross demand.
        # 5. Convert to the desired display unit.
        # This is a placeholder for the actual logic.
        logger.info(f"Generating consolidated results for {project_name}/{scenario_name} (placeholder).")
        # This would involve logic similar to the original _interpolate_td_losses and summing up demands
        # based on model_selection, then applying T&D losses.
        return {"status": "placeholder", "message": "Consolidated results generation not fully implemented yet."}

print("Defining demand visualization service for FastAPI... (merged and adapted)")
