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
        data_s1 = await self.get_scenario_data(project_name, scenario_name1, filters)
        data_s2 = await self.get_scenario_data(project_name, scenario_name2, filters)

        # Basic comparison: find common sectors and years, then diff the data for a common model if possible
        comparison_result = {
            "scenario1_name": scenario_name1,
            "scenario2_name": scenario_name2,
            "common_filters": filters or {},
            "comparison_by_sector": {},
            "summary": "Comparison data generated."
        }

        common_sectors = set(data_s1.sectors_data.keys()) & set(data_s2.sectors_data.keys())

        for sector_name in common_sectors:
            s1_sector_data = data_s1.sectors_data[sector_name]
            s2_sector_data = data_s2.sectors_data[sector_name]

            # Find common years
            s1_years_map = {year: idx for idx, year in enumerate(s1_sector_data.years)}
            s2_years_map = {year: idx for idx, year in enumerate(s2_sector_data.years)}
            common_years_detail = sorted(list(set(s1_sector_data.years) & set(s2_sector_data.years)))

            if not common_years_detail:
                continue

            comparison_by_sector[sector_name] = {
                "common_years": common_years_detail,
                "models_comparison": {} # Model_name -> {year: {s1_val, s2_val, diff}}
            }

            common_models = set(s1_sector_data.models_available) & set(s2_sector_data.models_available)
            for model_name in common_models:
                model_comp_data = {}
                for year in common_years_detail:
                    s1_idx = s1_years_map.get(year)
                    s2_idx = s2_years_map.get(year)
                    s1_val = s1_sector_data.model_data[model_name][s1_idx] if s1_idx is not None and model_name in s1_sector_data.model_data else None
                    s2_val = s2_sector_data.model_data[model_name][s2_idx] if s2_idx is not None and model_name in s2_sector_data.model_data else None

                    if s1_val is not None and s2_val is not None:
                        model_comp_data[year] = {
                            scenario_name1: s1_val,
                            scenario_name2: s2_val,
                            "difference": round(s1_val - s2_val, 3)
                        }
                if model_comp_data:
                    comparison_by_sector[sector_name]["models_comparison"][model_name] = model_comp_data

        comparison_result["comparison_by_sector"] = comparison_by_sector
        return comparison_result

    async def get_model_selection(self, project_name: str, scenario_name: str) -> Dict[str, Any]:
        return await self.load_ui_configuration(project_name, scenario_name, "model_selection") or {"model_selection": {}}

    async def save_model_selection(self, project_name: str, scenario_name: str, selection_config: Dict[str, str]) -> bool:
        # selection_config is expected to be {sector_name: model_name}
        return await self.save_ui_configuration(project_name, scenario_name, "model_selection", {"model_selection": selection_config})

    async def get_td_losses(self, project_name: str, scenario_name: str) -> Dict[str, Any]:
        return await self.load_ui_configuration(project_name, scenario_name, "td_losses") or {"td_losses": []}

    async def save_td_losses(self, project_name: str, scenario_name: str, losses_config: List[Dict[str, float]]) -> bool:
        # losses_config is expected to be [{'year': YYYY, 'loss_percentage': X.X}, ...]
        return await self.save_ui_configuration(project_name, scenario_name, "td_losses", {"td_losses": losses_config})

    async def save_ui_configuration(self, project_name: str, scenario_name: str, config_type: str, config_data: Dict) -> bool:
        """Saves UI related configuration (e.g., 'model_selection', 'td_losses')."""
        # import asyncio # Already imported at module level
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name

        is_dir = await asyncio.to_thread(scenario_path.is_dir)
        if not is_dir:
            try:
                await asyncio.to_thread(scenario_path.mkdir, parents=True, exist_ok=True)
            except Exception as e_mkdir: # More specific error for directory creation
                 logger.error(f"Failed to create directory for UI config {project_name}/{scenario_name}/{config_type}: {e_mkdir}", exc_info=True)
                 return False


        config_file_path = scenario_path / f"{config_type}_config.json"

        def _dump_json_sync():
            with open(config_file_path, "w") as f:
                json.dump(config_data, f, indent=2)
        try:
            await asyncio.to_thread(_dump_json_sync)
            logger.info(f"Saved {config_type} config for {project_name}/{scenario_name} to {config_file_path}")
            return True
        except IOError as e:
            logger.error(f"Failed to save {config_type} config for {project_name}/{scenario_name}: {e}", exc_info=True)
            return False
        except Exception as e_gen:
            logger.error(f"Unexpected error saving {config_type} config for {project_name}/{scenario_name}: {e_gen}", exc_info=True)
            return False


    async def load_ui_configuration(self, project_name: str, scenario_name: str, config_type: str) -> Optional[Dict]:
        """Loads UI related configuration."""
        # import asyncio # Already imported
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
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load {config_type} config for {project_name}/{scenario_name}: {e}", exc_info=True)
            except Exception as e_gen:
                logger.error(f"Unexpected error loading {config_type} config for {project_name}/{scenario_name}: {e_gen}", exc_info=True)
        return None

    def _interpolate_td_losses(self, td_losses_config: List[Dict[str, float]], target_years: List[int]) -> pd.Series:
        """Interpolates T&D losses for a list of target years."""
        if not td_losses_config or not target_years:
            return pd.Series(0.0, index=target_years) # Default to 0% loss if no config or no years

        loss_df = pd.DataFrame(td_losses_config).sort_values('year')
        if loss_df.empty or 'year' not in loss_df.columns or 'loss_percentage' not in loss_df.columns:
             return pd.Series(0.0, index=target_years)

        # Ensure numeric types
        loss_df['year'] = pd.to_numeric(loss_df['year'])
        loss_df['loss_percentage'] = pd.to_numeric(loss_df['loss_percentage']) / 100.0 # Convert to fraction

        # Create a series with all years from min target to max target for interpolation
        full_range_years = range(min(target_years), max(target_years) + 1)

        # Interpolate: Use years from config as index, then reindex to full range and interpolate
        # Then select only the target_years.
        # Using pandas Series for easier interpolation
        loss_series = loss_df.set_index('year')['loss_percentage']

        # Handle cases where target_years are outside the range of td_losses_config
        # by forward-filling from the first available loss year and back-filling from the last.
        min_loss_year, max_loss_year = loss_series.index.min(), loss_series.index.max()

        interpolated_losses = pd.Series(index=full_range_years, dtype=float)

        for year in full_range_years:
            if year < min_loss_year:
                interpolated_losses[year] = loss_series.iloc[0] # Use first available loss
            elif year > max_loss_year:
                interpolated_losses[year] = loss_series.iloc[-1] # Use last available loss
            elif year in loss_series.index:
                interpolated_losses[year] = loss_series[year]
            else: # Year is within range but not explicitly in config, needs interpolation
                # Find bounding years
                lower_year = loss_series.index[loss_series.index < year].max()
                upper_year = loss_series.index[loss_series.index > year].min()

                if pd.isna(lower_year) or pd.isna(upper_year): # Should not happen if year is within overall range
                    interpolated_losses[year] = np.nan # Or some default
                    continue

                lower_loss = loss_series[lower_year]
                upper_loss = loss_series[upper_year]

                # Linear interpolation
                interpolated_losses[year] = lower_loss + (upper_loss - lower_loss) * \
                                           ((year - lower_year) / (upper_year - lower_year))

        # Fill any remaining NaNs (e.g., if only one loss year provided) with method='ffill' then 'bfill'
        interpolated_losses = interpolated_losses.fillna(method='ffill').fillna(method='bfill')

        return interpolated_losses.reindex(target_years).fillna(0.0)


    async def generate_consolidated_results(self, project_name: str, scenario_name: str,
                                            model_selection: Dict[str, str], # sector_name -> model_name
                                            td_losses_config: List[Dict], # [{'year': Y, 'loss_percentage': P}]
                                            filters: Optional[Dict] = None) -> Dict[str, Any]: # Returns ScenarioOutput like structure
        """Generates consolidated results including T&D losses."""
        logger.info(f"Generating consolidated results for {project_name}/{scenario_name}.")

        # 1. Fetch scenario data (likely in kWh for calculations, so unit='kWh')
        # Ensure filters for get_scenario_data don't conflict with consolidation logic.
        # We need all years initially for T&D loss interpolation.
        scenario_data_filters = (filters or {}).copy()
        scenario_data_filters['unit'] = 'kWh' # Calculate in kWh then convert
        scenario_data_kwh = await self.get_scenario_data(project_name, scenario_name, scenario_data_filters)

        if not scenario_data_kwh.sectors_data:
            raise ProcessingError("No sector data available to generate consolidated results.")

        all_years = scenario_data_kwh.all_years_in_scenario
        if not all_years:
            raise ProcessingError("No year data available in the scenario.")

        # 2. Interpolate T&D losses for all relevant years.
        loss_series_fraction = self._interpolate_td_losses(td_losses_config, all_years)

        # 3. For each year, sum demands from selected models for each sector.
        consolidated_demand_gross_kwh = pd.Series(0.0, index=all_years)

        for sector_name, sector_data_obj in scenario_data_kwh.sectors_data.items():
            selected_model = model_selection.get(sector_name)
            if not selected_model or selected_model not in sector_data_obj.model_data:
                logger.warning(f"Model for sector '{sector_name}' not selected or not available. Skipping.")
                continue

            sector_demand_kwh = pd.Series(sector_data_obj.model_data[selected_model], index=sector_data_obj.years)
            consolidated_demand_gross_kwh = consolidated_demand_gross_kwh.add(sector_demand_kwh, fill_value=0)

        # 4. Apply T&D losses to the total gross demand. Net demand = Gross / (1 + loss_fraction)
        consolidated_demand_net_kwh = consolidated_demand_gross_kwh / (1 + loss_series_fraction.reindex(all_years).fillna(0.0))

        # 5. Save to CSV
        output_df = pd.DataFrame({
            'Year': all_years,
            'Gross_Demand_kWh': consolidated_demand_gross_kwh.reindex(all_years).round(3),
            'TD_Loss_Percentage': (loss_series_fraction.reindex(all_years)*100).round(2),
            'Net_Demand_kWh': consolidated_demand_net_kwh.reindex(all_years).round(3)
        })
        output_df = output_df.sort_values('Year').reset_index(drop=True)

        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_results_path = scenarios_base_path / scenario_name
        await asyncio.to_thread(scenario_results_path.mkdir, parents=True, exist_ok=True)
        consolidated_csv_path = scenario_results_path / "consolidated_results.csv"

        await asyncio.to_thread(output_df.to_csv, consolidated_csv_path, index=False)
        logger.info(f"Saved consolidated results to {consolidated_csv_path}")

        # 6. Convert to desired display unit from filters for the response
        display_unit = (filters or {}).get('unit', 'TWh')
        conversion_factor = self.unit_factors['kWh'] / self.unit_factors.get(display_unit, 1e9) # kWh to display_unit

        response_data = {
            "scenario_name": scenario_name,
            "display_unit": display_unit,
            "years": all_years,
            "gross_demand": (consolidated_demand_gross_kwh.reindex(all_years) * conversion_factor).round(3).tolist(),
            "td_losses_percentage": (loss_series_fraction.reindex(all_years)*100).round(2).tolist(),
            "net_demand": (consolidated_demand_net_kwh.reindex(all_years) * conversion_factor).round(3).tolist(),
            "model_selection_used": model_selection,
            "td_losses_config_used": td_losses_config,
            "output_file_path": str(consolidated_csv_path)
        }
        return response_data

    async def get_analysis_summary(self, project_name: str, scenario_name: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Generates an analysis summary for the consolidated results of a scenario."""
        logger.info(f"Generating analysis summary for {project_name}/{scenario_name}.")

        # Ensure consolidated results exist by calling generate_consolidated_results
        # This assumes model selection and T&D losses are already configured or default.
        # For a real scenario, the UI would guide the user to configure these first.
        # Here, we might need to load them or use defaults.

        model_selection_conf = await self.get_model_selection(project_name, scenario_name)
        td_losses_conf = await self.get_td_losses(project_name, scenario_name)

        if not model_selection_conf.get("model_selection"):
            raise ProcessingError(f"Model selection not configured for scenario {scenario_name}. Cannot generate analysis.")
        if not td_losses_conf.get("td_losses"):
            # Use default 0% loss if not configured, or raise error
            logger.warning(f"T&D losses not configured for scenario {scenario_name}. Assuming 0% loss for analysis.")
            # Defaulting to 0% loss might require adjusting how generate_consolidated_results handles empty td_losses_config
            # For now, let's assume generate_consolidated_results can handle it or it's pre-generated.

        # We need the consolidated data, preferably in a consistent unit like kWh for calculations
        # The filters passed here might be for display unit of the analysis, not for fetching raw data
        consolidation_filters = (filters or {}).copy()
        consolidation_filters['unit'] = 'kWh' # Ensure calculations are on base unit

        consolidated_data = await self.generate_consolidated_results(
            project_name, scenario_name,
            model_selection_conf["model_selection"],
            td_losses_conf["td_losses"], # This needs to be the list itself
            consolidation_filters
        )

        if not consolidated_data.get("net_demand") or not consolidated_data.get("years"):
            raise ProcessingError("Consolidated data (net demand or years) is empty or missing.")

        df = pd.DataFrame({
            'Year': consolidated_data["years"],
            'Net_Demand_kWh': consolidated_data["net_demand"]
        }).sort_values('Year').reset_index(drop=True)

        if df.empty:
            return {"error": "No data for analysis."}

        # Calculations
        start_year_analysis = df['Year'].min()
        end_year_analysis = df['Year'].max()
        num_years = end_year_analysis - start_year_analysis

        peak_demand_kwh = df['Net_Demand_kWh'].max()
        average_demand_kwh = df['Net_Demand_kWh'].mean()
        total_energy_kwh = df['Net_Demand_kWh'].sum()

        cagr = 0.0
        if num_years > 0 and df.iloc[0]['Net_Demand_kWh'] > 0:
            cagr = ((df.iloc[-1]['Net_Demand_kWh'] / df.iloc[0]['Net_Demand_kWh']) ** (1/num_years)) - 1
            cagr *= 100 # Percentage

        # Convert to display unit for reporting
        display_unit = (filters or {}).get('unit', 'TWh') # Default to TWh for analysis summary
        conversion_factor_display = self.unit_factors['kWh'] / self.unit_factors.get(display_unit, 1e9)

        summary = {
            "scenario_name": scenario_name,
            "analysis_period_years": [int(start_year_analysis), int(end_year_analysis)],
            "display_unit": display_unit,
            "peak_demand": round(peak_demand_kwh * conversion_factor_display, 3),
            "average_demand": round(average_demand_kwh * conversion_factor_display, 3),
            "total_energy_consumed": round(total_energy_kwh * conversion_factor_display, 3),
            "cagr_percentage": round(cagr, 2),
            "notes": "Analysis based on net demand after T&D losses."
        }
        return summary

    async def export_data(self, project_name: str, scenario_name: str, data_type: str, filters: Optional[Dict] = None) -> Path:
        """Exports specified data type (scenario or consolidated) to a temporary CSV file."""
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name

        if data_type == "consolidated":
            file_to_export = scenario_path / "consolidated_results.csv"
            if not await asyncio.to_thread(file_to_export.exists):
                 # Attempt to generate it if missing, assuming defaults for model_selection & td_losses
                logger.info(f"Consolidated results CSV not found for {scenario_name}, attempting to generate with defaults.")
                model_sel = await self.get_model_selection(project_name, scenario_name)
                td_loss = await self.get_td_losses(project_name, scenario_name)
                if not model_sel.get("model_selection"): raise FileNotFoundError("Model selection not set, cannot generate consolidated for export.")
                # td_loss can be empty list for 0% loss
                await self.generate_consolidated_results(project_name, scenario_name, model_sel["model_selection"], td_loss.get("td_losses",[]), filters)

                if not await asyncio.to_thread(file_to_export.exists): # Check again
                    raise FileNotFoundError(f"Consolidated results file for scenario '{scenario_name}' could not be generated or found.")
            return file_to_export

        elif data_type == "scenario_detail": # Exporting raw scenario data with filters
            scenario_data_obj = await self.get_scenario_data(project_name, scenario_name, filters)
            if not scenario_data_obj.sectors_data:
                raise FileNotFoundError(f"No detailed data found for scenario '{scenario_name}' with applied filters.")

            # Combine all sector data into a single DataFrame for export
            all_dfs = []
            for sector_name, sector_data in scenario_data_obj.sectors_data.items():
                df_sector = pd.DataFrame(sector_data.model_data) # Model data already in display unit
                df_sector['Year'] = sector_data.years
                df_sector['Sector'] = sector_name
                df_sector = df_sector[['Year', 'Sector'] + sector_data.models_available]
                all_dfs.append(df_sector)

            if not all_dfs:
                raise FileNotFoundError(f"No data to export for scenario '{scenario_name}'.")

            export_df = pd.concat(all_dfs).sort_values(['Sector', 'Year']).reset_index(drop=True)

            temp_dir = Path(tempfile.gettempdir())
            temp_file_path = temp_dir / f"{safe_filename(project_name)}_{safe_filename(scenario_name)}_detail_export.csv"
            await asyncio.to_thread(export_df.to_csv, temp_file_path, index=False)
            return temp_file_path
        else:
            raise ValueError(f"Invalid data_type for export: {data_type}. Must be 'consolidated' or 'scenario_detail'.")

    async def validate_scenario_configurations(self, project_name: str, scenario_name: str) -> Dict[str, Any]:
        """Validates if a scenario has necessary configurations set."""
        model_sel = await self.get_model_selection(project_name, scenario_name)
        td_losses = await self.get_td_losses(project_name, scenario_name)

        # Check if consolidated results file exists
        scenarios_base_path = self._get_scenario_base_path(project_name)
        scenario_path = scenarios_base_path / scenario_name
        consolidated_csv_path = scenario_path / "consolidated_results.csv"
        consolidated_exists = await asyncio.to_thread(consolidated_csv_path.exists)

        return {
            "scenario_name": scenario_name,
            "has_model_selection": bool(model_sel.get("model_selection")),
            "model_selection_details_count": len(model_sel.get("model_selection", {})),
            "has_td_losses_config": bool(td_losses.get("td_losses")),
            "td_losses_points_count": len(td_losses.get("td_losses", [])),
            "has_consolidated_results_file": consolidated_exists,
            "is_fully_configured_for_analysis": bool(model_sel.get("model_selection")) and bool(td_losses.get("td_losses"))
        }

print("Defining demand visualization service for FastAPI... (merged and adapted)")
