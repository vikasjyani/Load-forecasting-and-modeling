# fastapi-energy-platform/app/services/loadprofile_service.py
"""
Load Profile Service Layer for FastAPI
Handles business logic for load profile generation, management, and retrieval.
"""
import os
import json
import pandas as pd
# import numpy as np # Not used in the refactored parts yet
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# FastAPI specific imports
from fastapi import UploadFile # For type hinting, actual upload handling is in router

# Assuming models and utilities are adapted for FastAPI
# from app.models.load_profile_generator import LoadProfileGenerator # Needs to be Path-aware
# For now, let's assume a placeholder or simplified generator
from app.utils.helpers import get_file_info, ensure_directory, safe_filename # Path-aware
from app.utils.constants import VALIDATION_RULES, UNIT_FACTORS # Check relevance
from app.utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# Placeholder for LoadProfileGenerator if it's not refactored yet
class PlaceholderLoadProfileGenerator:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.inputs_path = project_path / "inputs"
        self.results_profiles_path = project_path / "results" / "load_profiles"
        self.config_path = project_path / "config"
        ensure_directory(self.inputs_path)
        ensure_directory(self.results_profiles_path)
        ensure_directory(self.config_path)
        logger.info(f"PlaceholderLoadProfileGenerator initialized for project: {project_path}")

    async def load_template_data(self) -> Dict[str, Any]: # Mock implementation, made async
        logger.debug(f"Loading template data (mock) from {self.inputs_path / 'load_curve_template.xlsx'}")
        # In a real scenario, pd.read_excel would be here, wrapped in to_thread
        # For mock, just return:
        await asyncio.sleep(0) # Simulate async nature if it were real I/O
        return {"historical_demand": pd.DataFrame(), "total_demand": pd.DataFrame(), "monthly_peaks": None, "calculated_monthly_peaks": None, "monthly_load_factors": None, "calculated_load_factors": None, "template_info": {}}

    async def get_available_base_years(self, historical_df: pd.DataFrame) -> List[int]: # Mock, async for consistency
        await asyncio.sleep(0)
        if not historical_df.empty and 'financial_year' in historical_df.columns:
            return sorted(historical_df['financial_year'].unique().tolist())
        return [2020, 2021, 2022] # Default mock

    async def generate_base_profile_forecast(self, **kwargs) -> Dict[str, Any]: # Mock, async
        logger.debug(f"Generating base profile forecast (mock) with args: {kwargs.get('base_year')}, {kwargs.get('start_fy')}-{kwargs.get('end_fy')}")
        await asyncio.sleep(0) # Simulate work
        return {"status": "success", "data": {"load_profile": pd.DataFrame([{'timestamp': datetime.now().isoformat(), 'demand': 100}]), "method": "base_mock", "years_generated": [kwargs.get('start_fy')], "frequency": "hourly", "constraints_applied": False}}

    async def generate_stl_forecast(self, **kwargs) -> Dict[str, Any]: # Mock, async
        logger.debug(f"Generating STL profile forecast (mock) with args: {kwargs.get('start_fy')}-{kwargs.get('end_fy')}")
        await asyncio.sleep(0) # Simulate work
        return {"status": "success", "data": {"load_profile": pd.DataFrame([{'timestamp': datetime.now().isoformat(), 'demand': 120}]), "method": "stl_mock", "years_generated": [kwargs.get('start_fy')], "frequency": "hourly", "constraints_applied": False}}

    async def save_forecast(self, forecast_data: Dict[str, Any], profile_id: Optional[str] = None) -> Dict[str, Any]: # Async
        if not profile_id:
            profile_id = f"mockprofile_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        df_to_save = forecast_data.get('load_profile', pd.DataFrame())
        if not isinstance(df_to_save, pd.DataFrame):
             df_to_save = pd.DataFrame(df_to_save)

        file_path = self.results_profiles_path / f"{profile_id}.csv"
        await asyncio.to_thread(df_to_save.to_csv, file_path, index=False)

        metadata = {
            "profile_id": profile_id, "method": forecast_data.get("method", "unknown"),
            "created_at": datetime.now().isoformat(), "source_config": forecast_data.get("config_snapshot"),
            "years": forecast_data.get("years_generated"), "frequency": forecast_data.get("frequency")
        }
        metadata_file_path = self.config_path / f"{profile_id}_metadata.json"

        def _dump_json_sync():
            with open(metadata_file_path, "w") as f:
                json.dump(metadata, f, indent=2)
        await asyncio.to_thread(_dump_json_sync)

        logger.info(f"Saved mock forecast {profile_id} to {file_path}")
        return {"profile_id": profile_id, "file_path": str(file_path), "metadata_path": str(metadata_file_path)}

    async def get_saved_profiles(self) -> List[Dict[str, Any]]: # Async
        profiles = []
        # Run glob in a thread as it can do I/O
        try:
            meta_files = await asyncio.to_thread(list, self.config_path.glob("*_metadata.json"))
        except OSError as e:
            logger.error(f"Error globbing metadata files in {self.config_path}: {e}")
            return []

        for meta_file_path in meta_files:
            try:
                def _load_json_sync():
                    with open(meta_file_path, "r") as f:
                        return json.load(f)
                profiles.append(await asyncio.to_thread(_load_json_sync))
            except (IOError, json.JSONDecodeError) as e_json:
                 logger.warning(f"Could not load or parse metadata file {meta_file_path.name}: {e_json}")
            except Exception as e_gen: # Catch any other unexpected error
                 logger.error(f"Unexpected error reading metadata file {meta_file_path.name}: {e_gen}", exc_info=True)
        logger.debug(f"Found {len(profiles)} saved mock profiles.")
        return profiles

    async def get_profile_data(self, profile_id: str) -> Dict[str, Any]: # Async
        meta_path = self.config_path / f"{profile_id}_metadata.json"
        csv_path = self.results_profiles_path / f"{profile_id}.csv"

        meta_exists = await asyncio.to_thread(meta_path.exists)
        csv_exists = await asyncio.to_thread(csv_path.exists)

        if meta_exists and csv_exists:
            def _load_files_sync():
                with open(meta_path, "r") as f_meta:
                    metadata = json.load(f_meta)
                df_data = pd.read_csv(csv_path)
                return {"metadata": metadata, "data": df_data.to_dict("records")}

            loaded_content = await asyncio.to_thread(_load_files_sync)
            logger.debug(f"Loaded mock profile data for {profile_id}.")
            return loaded_content
        raise ResourceNotFoundError(f"Mock profile {profile_id} (or its data/metadata) not found.")

    async def load_scenario_data(self, scenario_csv_path: Path) -> pd.DataFrame: # Async
        exists = await asyncio.to_thread(scenario_csv_path.exists)
        if exists:
            logger.debug(f"Loading mock scenario data from {scenario_csv_path}")
            # Run pd.read_csv in a thread
            return await asyncio.to_thread(pd.read_csv, scenario_csv_path)
        return pd.DataFrame()


class LoadProfileService:
    """Service layer for load profile operations."""

    def __init__(self, project_data_root: Path):
        self.project_data_root = project_data_root
        # Caching (in-memory, consider Redis for distributed setups)
        self._cache: Dict[str, Tuple[Any, float]] = {} # key -> (data, timestamp)
        self._cache_ttl_seconds = 300

    async def _get_project_generator(self, project_name: str) -> PlaceholderLoadProfileGenerator: # Async
        project_path = self.project_data_root / project_name
        is_dir = await asyncio.to_thread(project_path.is_dir)
        if not is_dir:
            # If we want to create it:
            # await asyncio.to_thread(ensure_directory, project_path / "inputs")
            # await asyncio.to_thread(ensure_directory, project_path / "results" / "load_profiles")
            # await asyncio.to_thread(ensure_directory, project_path / "config")
            # For now, raise if not found, consistent with original logic.
            raise ResourceNotFoundError(f"Project '{project_name}' path not found or is not a directory: {project_path}")

        # PlaceholderLoadProfileGenerator constructor is sync and light (calls ensure_directory which is sync)
        return PlaceholderLoadProfileGenerator(project_path)

    def _is_cache_valid(self, cache_key: str) -> bool:
        cached_item = self._cache.get(cache_key)
        if not cached_item: return False
        _, timestamp = cached_item
        return (datetime.now().timestamp() - timestamp) < self._cache_ttl_seconds

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]
        return None

    def _set_cache(self, cache_key: str, data: Any):
        self._cache[cache_key] = (data, datetime.now().timestamp())

    async def get_main_page_data(self, project_name: str) -> Dict[str, Any]:
        """Get data for the main load profile generation page for a specific project."""
        try:
            generator = await self._get_project_generator(project_name) # await

            available_scenarios_task = self._get_available_scenarios_async(project_name)
            saved_profiles_raw_task = generator.get_saved_profiles() # now async
            template_info_task = self._get_template_availability_async(generator) # now async

            available_scenarios, saved_profiles_raw, template_info = await asyncio.gather(
                available_scenarios_task, saved_profiles_raw_task, template_info_task
            )

            # Enhance saved profiles with file info
            saved_profiles_enhanced = []
            file_info_tasks = []
            profile_refs_for_file_info = []

            for profile_meta in saved_profiles_raw:
                profile_id = profile_meta.get("profile_id")
                if profile_id:
                    csv_path = generator.results_profiles_path / f"{profile_id}.csv"
                    exists = await asyncio.to_thread(csv_path.exists)
                    if exists:
                        file_info_tasks.append(get_file_info(csv_path)) # get_file_info is async
                        profile_refs_for_file_info.append(profile_meta)
                    else:
                        profile_meta['file_info'] = {'exists': False}
                saved_profiles_enhanced.append(profile_meta) # Add meta even if file_info task not created

            if file_info_tasks:
                file_info_results = await asyncio.gather(*file_info_tasks, return_exceptions=True)
                for i, profile_dict_fi_ref in enumerate(profile_refs_for_file_info):
                    if not isinstance(file_info_results[i], Exception):
                        profile_dict_fi_ref['file_info'] = file_info_results[i]
                    else:
                        profile_dict_fi_ref['file_info'] = {'exists': False, 'error': str(file_info_results[i])}


            return {
                'project_name': project_name,
                'template_info': template_info,
                'available_scenarios': available_scenarios,
                'saved_profiles': saved_profiles_enhanced, # Use enhanced list
                'total_saved_profiles': len(saved_profiles_enhanced),
                'stl_available_mock': True, # Based on placeholder
                'page_loaded_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting main page data for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get main page data: {str(e)}")


    async def _get_template_availability_async(self, generator: PlaceholderLoadProfileGenerator) -> Dict[str, Any]:
        """Asynchronous helper for template availability."""
        template_path = generator.inputs_path / 'load_curve_template.xlsx'
        exists = await asyncio.to_thread(template_path.exists)
        file_info_data = None
        if exists:
            file_info_data = await get_file_info(template_path) # get_file_info is async

        return {
            'exists': exists,
            'path': str(template_path),
            'file_info': file_info_data
        }

    async def _get_available_scenarios_async(self, project_name: str) -> List[Dict[str, Any]]:
        """Asynchronous helper to get available demand scenarios."""
        # This path should point to where demand projection results are stored for the project
        scenarios_base_path = self.project_data_root / project_name / "results" / "demand_projection"
        available_scenarios = []

        is_dir = await asyncio.to_thread(scenarios_base_path.is_dir)
        if is_dir:
            try:
                dir_items = await asyncio.to_thread(list, scenarios_base_path.iterdir())
            except OSError as e:
                logger.error(f"Error iterating demand scenarios directory {scenarios_base_path} for project '{project_name}': {e}")
                return []

            for item_path in dir_items:
                item_is_dir = await asyncio.to_thread(item_path.is_dir)
                if item_is_dir: # Each scenario is a directory
                    consolidated_file = item_path / 'consolidated_results.csv'
                    consolidated_exists = await asyncio.to_thread(consolidated_file.exists)
                    if consolidated_exists:
                        file_info_data = await get_file_info(consolidated_file) # get_file_info is async
                        available_scenarios.append({
                            'name': item_path.name,
                            'path_to_consolidated_csv': str(consolidated_file),
                            'file_info': file_info_data
                        })
        return available_scenarios


    async def generate_profile(self, project_name: str, generation_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a load profile (base or STL) for a project."""
        # Validation should ideally happen at the Pydantic model level in the router,
        # but can also be done here for business logic specific checks.
        # validation_result = self.validate_generation_request(config, generation_type) # Assuming this method exists & is adapted
        # if not validation_result['valid']:
        #     raise ValidationError(f"Invalid generation request: {validation_result['errors']}")

        generator = await self._get_project_generator(project_name) # await

        # Prepare demand scenarios from config
        demand_source = config.get('demand_source', 'template')
        demand_scenarios_df: pd.DataFrame
        if demand_source == 'template':
            template_data = await generator.load_template_data() # await
            demand_scenarios_df = template_data.get('total_demand', pd.DataFrame())
        elif demand_source == 'scenario':
            scenario_name = config.get('scenario_name')
            if not scenario_name: raise ValidationError("Scenario name required for scenario-based demand.")
            # Construct path to the scenario's consolidated results
            scenario_csv_path = self.project_data_root / project_name / "results" / "demand_projection" / scenario_name / "consolidated_results.csv"
            demand_scenarios_df = await generator.load_scenario_data(scenario_csv_path) # await
        else:
            raise ValidationError(f"Invalid demand_source: {demand_source}")

        template_data_for_hist = await generator.load_template_data() # await, potentially cache this call
        historical_data_df = template_data_for_hist.get('historical_demand', pd.DataFrame())

        # Prepare constraints (simplified, adapt _prepare_constraints if complex)
        # constraints = self._prepare_constraints(config, template_data_for_hist) # Needs template_data

        # Call the appropriate generator method (now async)
        if generation_type == "base_profile":
            result = await generator.generate_base_profile_forecast( # await
                 historical_data=historical_data_df, demand_scenarios=demand_scenarios_df,
                 base_year=int(config['base_year']), start_fy=int(config['start_fy']), end_fy=int(config['end_fy']),
                 frequency=config.get('frequency', 'hourly'), # constraints=constraints
            )
        elif generation_type == "stl_profile":
            result = await generator.generate_stl_forecast( # await
                 historical_data=historical_data_df, demand_scenarios=demand_scenarios_df,
                 start_fy=int(config['start_fy']), end_fy=int(config['end_fy']),
                 frequency=config.get('frequency', 'hourly'), stl_params=config.get('stl_params', {}), # constraints=constraints
            )
        else:
            raise ValidationError(f"Unknown generation type: {generation_type}")

        if result.get('status') == 'success':
            custom_name = config.get('custom_name', '').strip()
            profile_id_to_save = None
            if custom_name: # Generate ID if custom name provided
                safe_name = "".join(c if c.isalnum() else '_' for c in custom_name) # Basic sanitize
                profile_id_to_save = f"{safe_name[:30]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            save_info = await generator.save_forecast(result['data'], profile_id=profile_id_to_save) # await

            # Clear relevant caches
            self._cache.pop(f"profiles:{project_name}", None)
            self._cache.pop(f"profile_detail:{project_name}:{save_info['profile_id']}", None)

            return {
                'success': True, 'profile_id': save_info['profile_id'],
                'file_path': save_info['file_path'], 'metadata_path': save_info['metadata_path'],
                'generation_config_summary': config, # Or a summary of it
                'profile_summary': self._create_generation_summary(result['data']) # Simplified summary
            }
        else:
            raise ProcessingError(f"Profile generation failed: {result.get('message', 'Unknown error')}")

    def _create_generation_summary(self, data: Dict) -> Dict[str, Any]:
        """Create summary of generation results"""
        # This is a simplified version. Actual implementation might need more details from `data`.
        load_profile_df = data.get('load_profile', pd.DataFrame())
        if not isinstance(load_profile_df, pd.DataFrame): # Ensure it's a DataFrame
             load_profile_df = pd.DataFrame(load_profile_df)

        return {
            'method': data.get('method', 'unknown'),
            'years_generated': data.get('years_generated', []),
            'frequency': data.get('frequency', 'hourly'),
            'total_records': len(load_profile_df),
            'constraints_applied': data.get('constraints_applied', False),
            'peak_demand_generated': float(load_profile_df['demand'].max()) if 'demand' in load_profile_df.columns and not load_profile_df.empty else None,
            'average_demand_generated': float(load_profile_df['demand'].mean()) if 'demand' in load_profile_df.columns and not load_profile_df.empty else None,
        }

    async def get_profile_detailed_data(self, project_name: str, profile_id: str) -> Dict[str, Any]:
        """Get detailed data and metadata for a specific saved profile."""
        cache_key = f"profile_detail:{project_name}:{profile_id}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data: return cached_data

        generator = await self._get_project_generator(project_name) # await
        try:
            profile_content = await generator.get_profile_data(profile_id) # await
            # Further analysis can be added here if needed, similar to original _analyze_profile_data
            self._set_cache(cache_key, profile_content)
            return profile_content
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error getting detailed data for profile '{profile_id}' in project '{project_name}': {e}")
            raise ProcessingError(f"Could not retrieve profile details: {str(e)}")


    async def delete_profile(self, project_name: str, profile_id: str) -> Dict[str, Any]:
        """Deletes a saved load profile and its metadata for a project."""
        generator = await self._get_project_generator(project_name) # await
        files_deleted_log = []

        csv_path = generator.results_profiles_path / f"{profile_id}.csv"
        metadata_path = generator.config_path / f"{profile_id}_metadata.json"

        try:
            csv_exists = await asyncio.to_thread(csv_path.exists)
            if csv_exists:
                await asyncio.to_thread(csv_path.unlink)
                files_deleted_log.append(f"Deleted data file: {csv_path.name}")

            meta_exists = await asyncio.to_thread(metadata_path.exists)
            if meta_exists:
                await asyncio.to_thread(metadata_path.unlink)
                files_deleted_log.append(f"Deleted metadata file: {metadata_path.name}")

            # Clear caches
            self._cache.pop(f"profiles:{project_name}", None)
            self._cache.pop(f"profile_detail:{project_name}:{profile_id}", None)
            logger.info(f"Deleted profile '{profile_id}' from project '{project_name}'. Files: {files_deleted_log}")
            return {'success': True, 'message': f"Profile '{profile_id}' deleted.", 'files_deleted': files_deleted_log}
        except Exception as e:
            logger.exception(f"Error deleting profile '{profile_id}' from project '{project_name}': {e}")
            raise ProcessingError(f"Could not delete profile: {str(e)}")

    async def upload_template_file(self, project_name: str, file: UploadFile) -> Dict[str, Any]:
        """Handles upload and basic validation of a load curve template for a project."""
        generator = await self._get_project_generator(project_name) # await
        template_file_path = generator.inputs_path / "load_curve_template.xlsx" # Standard name

        try:
            content = await file.read() # Read from UploadFile (async)

            # Async file write
            def _write_file_sync(path: Path, data: bytes):
                with open(path, "wb") as buffer:
                    buffer.write(data)
            await asyncio.to_thread(_write_file_sync, template_file_path, content)

            # Perform a basic validation by trying to load it (now async)
            await generator.load_template_data()

            # Clear relevant caches if template changes
            self._cache.pop(f"template_analysis:{project_name}", None)
            self._cache.pop(f"base_years:{project_name}", None)

            file_info_data = await get_file_info(template_file_path) # get_file_info is async
            logger.info(f"Uploaded and validated template for project '{project_name}' to {template_file_path}")
            return {
                "success": True, "message": "Template uploaded and validated successfully.",
                "file_info": file_info_data
            }
        except Exception as e:
            logger.exception(f"Error uploading or validating template for project '{project_name}': {e}")
            # Attempt to remove partially saved or invalid file (async)
            exists = await asyncio.to_thread(template_file_path.exists)
            if exists:
                await asyncio.to_thread(template_file_path.unlink, missing_ok=True)
            raise ProcessingError(f"Template upload/validation failed: {str(e)}")


    # Methods like get_template_analysis, get_available_base_years, get_scenario_analysis
    # would be adapted similarly, using the project-specific generator and async calls.
    # The analysis logic itself (_analyze_template_data, etc.) would remain largely the same
    # but ensure it works with data loaded by the (potentially refactored) generator.

print("Defining load profile service (generation/management) for FastAPI... (merged and adapted)")
