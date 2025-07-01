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

        scenario_infos = []
        for item_path in scenarios_base_path.iterdir():
            if item_path.is_dir(): # Each scenario is a directory
                try:
                    # _analyze_scenario_directory_async needs to be defined or adapted
                    # For now, using a synchronous placeholder or direct analysis
                    info = self._analyze_scenario_directory_sync(item_path.name, item_path)
                    if info.has_data:
                        scenario_infos.append(info)
                except Exception as e:
                    logger.warning(f"Error analyzing scenario directory {item_path.name} in project '{project_name}': {e}")

        scenario_infos.sort(key=lambda s: s.last_modified_iso or "", reverse=True)
        logger.info(f"Found {len(scenario_infos)} scenarios for project '{project_name}'.")
        return scenario_infos

    def _analyze_scenario_directory_sync(self, scenario_dir_name: str, scenario_path: Path) -> ScenarioInfo:
        """Synchronously analyzes a scenario directory for metadata."""
        excel_files = [f for f in scenario_path.iterdir() if f.is_file() and f.suffix == '.xlsx' and not f.name.startswith(('_', '~'))]
        year_min, year_max = 2025, 2037 # Defaults
        last_mod_timestamp = 0.0

        if excel_files:
            for f_path in excel_files[:3]: # Quick scan a few files
                try:
                    if f_path.stat().st_mtime > last_mod_timestamp:
                        last_mod_timestamp = f_path.stat().st_mtime
                    # Simplified year extraction: assumes 'Year' column exists and is numeric
                    # df_sample = pd.read_excel(f_path, nrows=50, usecols=lambda x: 'year' in str(x).lower())
                    # if not df_sample.empty and not df_sample.iloc[:, 0].empty:
                    #     years_in_file = pd.to_numeric(df_sample.iloc[:, 0], errors='coerce').dropna()
                    #     if not years_in_file.empty:
                    #         year_min = min(year_min, int(years_in_file.min()))
                    #         year_max = max(year_max, int(years_in_file.max()))
                except Exception as e_file:
                    logger.debug(f"Could not quickly analyze file {f_path.name} for scenario {scenario_dir_name}: {e_file}")

        return ScenarioInfo(
            name=scenario_dir_name, path=str(scenario_path), # Storing path might be a security concern if exposed directly
            sectors_count=len(excel_files), year_range={'min': year_min, 'max': year_max},
            has_data=bool(excel_files), file_count=len(excel_files),
            last_modified_iso=datetime.fromtimestamp(last_mod_timestamp).isoformat() if last_mod_timestamp else None
        )

    async def get_scenario_data(self, project_name: str, scenario_name: str, filters: Optional[Dict] = None) -> ScenarioOutput:
        """
        Retrieves and processes data for a specific scenario, applying filters.
        Filters example: {'unit': 'GWh', 'start_year': 2025, 'end_year': 2040, 'sectors': ['Residential']}
        """
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name
        if not scenario_path.exists() or not scenario_path.is_dir():
            raise FileNotFoundError(f"Scenario '{scenario_name}' not found in project '{project_name}'.")

        filters = filters or {}
        unit = filters.get('unit', 'TWh')
        start_year_filter = filters.get('start_year')
        end_year_filter = filters.get('end_year')
        selected_sectors_filter = filters.get('sectors')

        processed_sectors_data: Dict[str, SectorData] = {}
        all_years_set = set()
        all_models_set = set()

        for file_path in scenario_path.iterdir():
            if file_path.is_file() and file_path.suffix == '.xlsx' and not file_path.name.startswith(('_', '~')):
                sector_name_from_file = file_path.stem # Filename without extension
                if selected_sectors_filter and sector_name_from_file not in selected_sectors_filter:
                    continue

                # sector_data_obj = await asyncio.to_thread( # Run blocking pandas I/O in thread
                #     self._load_and_process_single_sector_file,
                #     file_path, sector_name_from_file, unit, start_year_filter, end_year_filter
                # )
                sector_data_obj = self._load_and_process_single_sector_file( # Sync for now
                     file_path, sector_name_from_file, unit, start_year_filter, end_year_filter
                )

                if sector_data_obj:
                    processed_sectors_data[sector_name_from_file] = sector_data_obj
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

    def _load_and_process_single_sector_file(
        self, file_path: Path, sector_name: str, target_unit: str,
        start_year: Optional[int], end_year: Optional[int]
    ) -> Optional[SectorData]:
        try:
            # Determine sheet name (Results or first sheet)
            with pd.ExcelFile(file_path) as xls:
                sheet_name = 'Results' if 'Results' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name)

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
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name
        if not scenario_path.is_dir(): scenario_path.mkdir(parents=True, exist_ok=True)

        config_file_path = scenario_path / f"{config_type}_config.json"
        try:
            with open(config_file_path, "w") as f:
                json.dump(config_data, f, indent=2)
            logger.info(f"Saved {config_type} config for {project_name}/{scenario_name}.")
            return True
        except IOError as e:
            logger.error(f"Failed to save {config_type} config for {project_name}/{scenario_name}: {e}")
            return False

    async def load_ui_configuration(self, project_name: str, scenario_name: str, config_type: str) -> Optional[Dict]:
        """Loads UI related configuration."""
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name
        config_file_path = scenario_path / f"{config_type}_config.json"

        if config_file_path.exists():
            try:
                with open(config_file_path, "r") as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load {config_type} config for {project_name}/{scenario_name}: {e}")
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
