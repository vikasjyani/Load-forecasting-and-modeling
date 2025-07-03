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
# Actual LoadProfileGenerator logic will be more complex and handle real data processing.
# from app.models.load_profile_generator import LoadProfileGenerator # This needs to be Path-aware and potentially async-friendly

from app.utils.helpers import get_file_info, ensure_directory, safe_filename # Path-aware
from app.utils.constants import VALIDATION_RULES, UNIT_FACTORS # Check relevance
from app.utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError
import app.utils.load_profile_engine as lp_engine # Assuming this contains core algorithms

logger = logging.getLogger(__name__)


class ProjectLoadProfileManager: # Renamed from PlaceholderLoadProfileGenerator for clarity
    """
    Manages load profile data and generation for a specific project.
    This class will contain the actual logic for file I/O and calling generation algorithms.
    """
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.inputs_path = project_path / "inputs"
        self.results_profiles_path = project_path / "results" / "load_profiles"
        # Config path for metadata related to this project's load profiles
        self.profiles_config_path = project_path / "config" / "load_profiles"

        # Ensure directories exist (can be done once at project creation/loading)
        # For this service, we assume they might need creation if accessed.
        # These are synchronous but generally quick. If they become an issue, make them async.
        ensure_directory(self.inputs_path)
        ensure_directory(self.results_profiles_path)
        ensure_directory(self.profiles_config_path)
        logger.info(f"ProjectLoadProfileManager initialized for project: {project_path}")

    async def get_template_file_path(self) -> Path:
        return self.inputs_path / 'load_curve_template.xlsx'

    async def load_template_data(self) -> Dict[str, Any]:
        template_path = await self.get_template_file_path()
        exists = await asyncio.to_thread(template_path.exists)
        if not exists:
            raise ResourceNotFoundError(f"Load curve template not found at {template_path}")
        try:
            # Assuming lp_engine.analyze_template is synchronous and needs to_thread
            # It should return a dict with DataFrames and analysis results.
            # Example: {'historical_df': pd.DataFrame, 'analysis': {...}}
            template_analysis_result = await asyncio.to_thread(lp_engine.analyze_template, str(template_path))
            logger.info(f"Successfully loaded and analyzed template: {template_path.name}")
            return template_analysis_result # This should include DataFrames and summary info
        except Exception as e:
            logger.error(f"Error loading or analyzing template {template_path.name}: {e}", exc_info=True)
            raise ProcessingError(f"Failed to process template file: {str(e)}")


    async def get_available_base_years(self) -> List[int]:
        template_data = await self.load_template_data()
        historical_df = template_data.get('historical_df') # Assuming key from analyze_template
        if historical_df is not None and not historical_df.empty and 'financial_year' in historical_df.columns:
             # Ensure years are integers and unique
            return sorted([int(y) for y in historical_df['financial_year'].unique()])
        logger.warning(f"Could not determine base years from template for project {self.project_path.name}")
        return [] # Return empty or default if no data

    async def generate_base_profile_forecast(self, config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Generating base profile for project {self.project_path.name} with config: {config}")
        # This will call the core logic from lp_engine or similar module
        logger.info(f"Generating base profile for project {self.project_path.name} with config: {config}")

        template_path_str = str(await self.get_template_file_path())
        demand_scenario_df = None
        if config.get("demand_source") == "scenario" and config.get("scenario_name"):
            try:
                demand_scenario_df = await self.load_demand_scenario_data(config["scenario_name"])
            except ResourceNotFoundError as e:
                raise ProcessingError(f"Demand scenario '{config['scenario_name']}' not found for base profile generation: {e}")

        try:
            # Assuming lp_engine.run_base_profile_scaling returns a DataFrame
            result_df = await asyncio.to_thread(
                lp_engine.run_base_profile_scaling, # Ensure this function exists and is imported
                template_path=template_path_str,
                historical_data=config.get("historical_data"), # Must be passed in or loaded by engine
                demand_scenarios=demand_scenario_df, # Pass loaded scenario DataFrame
                base_year=int(config['base_year']),
                start_fy=int(config['start_fy']),
                end_fy=int(config['end_fy']),
                frequency=config.get('frequency', 'hourly'),
                constraints=config.get('constraints')
            )
            logger.info(f"Base profile scaling completed for project {self.project_path.name}, scenario {config.get('scenario_name', 'N/A')}")
            return {
                "status": "success",
                "data": {
                    "load_profile_df": result_df,
                    "method": "base_profile_scaling",
                    "config_snapshot": config, # Store the input config for metadata
                    "years_generated": list(range(int(config['start_fy']), int(config['end_fy']) + 1)),
                    "frequency": config.get('frequency', 'hourly')
                }
            }
        except Exception as e:
            logger.error(f"Error during base profile scaling for project {self.project_path.name}: {e}", exc_info=True)
            raise ProcessingError(f"Base profile generation failed: {str(e)}")


    async def generate_stl_forecast(self, config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Generating STL profile for project {self.project_path.name} with config: {config}")

        template_path_str = str(await self.get_template_file_path())
        demand_scenario_df = None
        if config.get("demand_source") == "scenario" and config.get("scenario_name"):
            try:
                demand_scenario_df = await self.load_demand_scenario_data(config["scenario_name"])
            except ResourceNotFoundError as e:
                raise ProcessingError(f"Demand scenario '{config['scenario_name']}' not found for STL profile generation: {e}")

        try:
            # Assuming lp_engine.run_stl_decomposition returns a DataFrame
            result_df = await asyncio.to_thread(
                lp_engine.run_stl_decomposition, # Ensure this function exists and is imported
                template_path=template_path_str,
                historical_data=config.get("historical_data"), # Must be passed in or loaded by engine
                demand_scenarios=demand_scenario_df, # Pass loaded scenario DataFrame
                start_fy=int(config['start_fy']),
                end_fy=int(config['end_fy']),
                frequency=config.get('frequency', 'hourly'),
                stl_params=config.get('stl_params', {}),
                constraints=config.get('constraints')
            )
            logger.info(f"STL decomposition completed for project {self.project_path.name}, scenario {config.get('scenario_name', 'N/A')}")
            return {
                "status": "success",
                "data": {
                    "load_profile_df": result_df,
                    "method": "stl_decomposition",
                    "config_snapshot": config, # Store the input config
                    "years_generated": list(range(int(config['start_fy']), int(config['end_fy']) + 1)),
                    "frequency": config.get('frequency', 'hourly')
                }
            }
        except Exception as e:
            logger.error(f"Error during STL decomposition for project {self.project_path.name}: {e}", exc_info=True)
            raise ProcessingError(f"STL profile generation failed: {str(e)}")


    async def save_generated_profile(self, profile_data_dict: Dict[str, Any], profile_id: Optional[str] = None) -> Dict[str, Any]:
        if not profile_id:
            method_abbr = profile_data_dict.get("method", "custom")[:4].lower()
            profile_id = f"lp_{method_abbr}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        profile_id = safe_filename(profile_id) # Sanitize

        df_to_save = profile_data_dict.get('load_profile_df')
        if not isinstance(df_to_save, pd.DataFrame) or df_to_save.empty:
             raise ProcessingError("No load profile data found to save.")

        file_path = self.results_profiles_path / f"{profile_id}.csv"
        await asyncio.to_thread(df_to_save.to_csv, file_path, index=False)

        metadata = {
            "profile_id": profile_id,
            "project_name": self.project_path.name,
            "method_used": profile_data_dict.get("method", "unknown"),
            "generation_config": profile_data_dict.get("config_snapshot"),
            "years_generated": profile_data_dict.get("years_generated"),
            "frequency": profile_data_dict.get("frequency"),
            "created_at": datetime.now().isoformat(),
            "original_filename": profile_data_dict.get("original_filename"), # If uploaded
            "source_description": profile_data_dict.get("source_description", "Generated by system")
        }
        metadata_file_path = self.profiles_config_path / f"{profile_id}_meta.json" # Changed suffix

        def _dump_json_sync():
            with open(metadata_file_path, "w") as f:
                json.dump(metadata, f, indent=2)
        await asyncio.to_thread(_dump_json_sync)

        logger.info(f"Saved generated profile '{profile_id}' for project '{self.project_path.name}' to {file_path}")
        return {"profile_id": profile_id, "file_path": str(file_path), "metadata_path": str(metadata_file_path), "metadata": metadata}

    async def get_saved_profiles_metadata(self) -> List[Dict[str, Any]]:
        profiles_meta = []
        try:
            meta_files = await asyncio.to_thread(list, self.profiles_config_path.glob("*_meta.json"))
        except OSError as e:
            logger.error(f"Error globbing metadata files in {self.profiles_config_path} for project {self.project_path.name}: {e}")
            return []

        for meta_file_path in meta_files:
            try:
                def _load_json_sync():
                    with open(meta_file_path, "r") as f: return json.load(f)
                meta_content = await asyncio.to_thread(_load_json_sync)

                # Add file info for the CSV
                csv_path = self.results_profiles_path / f"{meta_content['profile_id']}.csv"
                csv_exists = await asyncio.to_thread(csv_path.exists)
                if csv_exists:
                    meta_content['file_info'] = await get_file_info(csv_path)
                else:
                    meta_content['file_info'] = {'exists': False, 'error': 'CSV data file missing.'}
                profiles_meta.append(meta_content)

            except (IOError, json.JSONDecodeError) as e_json:
                 logger.warning(f"Could not load or parse metadata file {meta_file_path.name}: {e_json}")
            except Exception as e_gen:
                 logger.error(f"Unexpected error reading metadata {meta_file_path.name}: {e_gen}", exc_info=True)
        logger.debug(f"Found {len(profiles_meta)} saved profiles for project {self.project_path.name}.")
        return profiles_meta

    async def get_profile_data_with_metadata(self, profile_id: str) -> Dict[str, Any]:
        profile_id = safe_filename(profile_id)
        meta_path = self.profiles_config_path / f"{profile_id}_meta.json"
        csv_path = self.results_profiles_path / f"{profile_id}.csv"

        meta_exists = await asyncio.to_thread(meta_path.exists)
        if not meta_exists:
            raise ResourceNotFoundError(f"Metadata for profile '{profile_id}' not found in project '{self.project_path.name}'.")

        csv_exists = await asyncio.to_thread(csv_path.exists)
        if not csv_exists:
            raise ResourceNotFoundError(f"Data CSV for profile '{profile_id}' not found in project '{self.project_path.name}'.")

        def _load_files_sync():
            with open(meta_path, "r") as f_meta: metadata = json.load(f_meta)
            # Assuming CSV has 'timestamp' and 'demand_kw' or similar
            df_data = pd.read_csv(csv_path, parse_dates=['timestamp'])
            return {"metadata": metadata, "data_records": df_data.to_dict("records")}

        loaded_content = await asyncio.to_thread(_load_files_sync)
        logger.debug(f"Loaded profile data and metadata for '{profile_id}' in project '{self.project_path.name}'.")
        return loaded_content

    async def delete_profile_files(self, profile_id: str) -> List[str]:
        profile_id = safe_filename(profile_id)
        files_deleted_log = []
        csv_path = self.results_profiles_path / f"{profile_id}.csv"
        meta_path = self.profiles_config_path / f"{profile_id}_meta.json"

        csv_exists = await asyncio.to_thread(csv_path.exists)
        if csv_exists:
            await asyncio.to_thread(csv_path.unlink)
            files_deleted_log.append(str(csv_path))

        meta_exists = await asyncio.to_thread(meta_path.exists)
        if meta_exists:
            await asyncio.to_thread(meta_path.unlink)
            files_deleted_log.append(str(meta_path))
        return files_deleted_log

    async def load_demand_scenario_data(self, scenario_name: str) -> pd.DataFrame:
        # Path to where demand projection scenarios are stored for this project
        scenario_csv_path = self.project_path / "results" / "demand_projection" / safe_filename(scenario_name) / "consolidated_results.csv"
        exists = await asyncio.to_thread(scenario_csv_path.exists)
        if exists:
            logger.debug(f"Loading demand scenario data from {scenario_csv_path} for project {self.project_path.name}")
            return await asyncio.to_thread(pd.read_csv, scenario_csv_path) # Assuming CSV format
        raise ResourceNotFoundError(f"Demand scenario '{scenario_name}' (consolidated_results.csv) not found for project {self.project_path.name}")


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
        generator = await self._get_project_generator(project_name)

        # Load necessary base data (template data for historical info)
        # This is loaded once and passed into the config for manager methods
        try:
            template_data = await generator.load_template_data()
            historical_data_df = template_data.get('historical_df')
            if historical_data_df is None: # Check if historical_df key exists and is not None
                historical_data_df = pd.DataFrame() # Ensure it's a DataFrame

            # Add historical_data to the config that will be passed to manager's generation methods
            # The manager methods themselves will decide if/how to use it or the template_path
            config_for_generation = config.copy()
            config_for_generation['historical_data'] = historical_data_df
            # No need to pass demand_scenarios_df directly here, manager's methods will load it if 'scenario' source

        except ResourceNotFoundError as e:
            logger.error(f"Template file missing for project {project_name}, cannot generate profile. Error: {e}")
            raise ProcessingError(f"Cannot generate profile: Load curve template not found for project '{project_name}'.")
        except Exception as e:
            logger.error(f"Error loading template data for profile generation in project {project_name}: {e}", exc_info=True)
            raise ProcessingError(f"Failed to prepare data for profile generation: {str(e)}")


        # Call the appropriate generator method (now async) from ProjectLoadProfileManager
        if generation_type == "base_profile":
            # Validate specific fields for base_profile if not handled by Pydantic in router
            if 'base_year' not in config or 'start_fy' not in config or 'end_fy' not in config:
                raise ValidationError("Missing required fields (base_year, start_fy, end_fy) for base profile generation.")
            result_from_manager = await generator.generate_base_profile_forecast(config_for_generation)
        elif generation_type == "stl_profile":
            if 'start_fy' not in config or 'end_fy' not in config:
                 raise ValidationError("Missing required fields (start_fy, end_fy) for STL profile generation.")
            result_from_manager = await generator.generate_stl_forecast(config_for_generation)
        else:
            raise ValidationError(f"Unknown generation type: {generation_type}")

        if result_from_manager.get('status') == 'success' and result_from_manager.get('data'):
            profile_data_to_save = result_from_manager['data']

            custom_name = config.get('custom_name', '').strip()
            # profile_id_to_save = None # Let save_generated_profile handle ID generation if None
            # if custom_name:
            #     safe_name = "".join(c if c.isalnum() else '_' for c in custom_name)
            #     profile_id_to_save = f"{safe_name[:30]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Pass the original config (or config_for_generation which includes historical_data)
            # to be stored as part of metadata. The `profile_data_to_save` should also include it.
            if 'config_snapshot' not in profile_data_to_save: # Ensure config is part of what's saved
                profile_data_to_save['config_snapshot'] = config

            save_info = await generator.save_generated_profile(profile_data_to_save, profile_id=custom_name or None)

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
        generator = await self._get_project_generator(project_name)
        template_file_path = await generator.get_template_file_path()

        try:
            content = await file.read()

            def _write_file_sync(path: Path, data: bytes):
                with open(path, "wb") as buffer:
                    buffer.write(data)
            await asyncio.to_thread(_write_file_sync, template_file_path, content)

            # Perform validation by trying to load and analyze it
            # This implicitly validates structure and basic content.
            await generator.load_template_data()

            self._cache.pop(f"template_info:{project_name}", None)
            self._cache.pop(f"available_base_years:{project_name}", None)

            file_info_data = await get_file_info(template_file_path)
            logger.info(f"Uploaded and validated template for project '{project_name}' to {template_file_path}")
            return {
                "success": True, "message": "Template uploaded and validated successfully.",
                "file_info": file_info_data
            }
        except Exception as e:
            logger.exception(f"Error uploading or validating template for project '{project_name}': {e}")
            exists = await asyncio.to_thread(template_file_path.exists)
            if exists:
                await asyncio.to_thread(template_file_path.unlink, missing_ok=True)
            raise ProcessingError(f"Template upload/validation failed: {str(e)}")

    async def get_template_info(self, project_name: str) -> Dict[str, Any]:
        """Retrieves analysis/summary of the load curve template for a project."""
        cache_key = f"template_info:{project_name}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"Using cached template info for project '{project_name}'")
            return cached_data

        generator = await self._get_project_generator(project_name)
        try:
            # load_template_data in manager now returns the analysis result
            template_analysis = await generator.load_template_data()

            # Add file path info
            template_path = await generator.get_template_file_path()
            template_analysis['file_path'] = str(template_path)
            template_analysis['file_exists'] = await asyncio.to_thread(template_path.exists)
            if template_analysis['file_exists']:
                 template_analysis['file_info'] = await get_file_info(template_path)

            self._set_cache(cache_key, template_analysis)
            return template_analysis
        except ResourceNotFoundError:
            # If template doesn't exist, return a specific structure
            return {
                "error": "Template file not found.",
                "file_exists": False,
                "file_path": str(await generator.get_template_file_path()),
                "message": "Please upload 'load_curve_template.xlsx' to the project's input folder."
            }
        except Exception as e:
            logger.exception(f"Error getting template info for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get template information: {str(e)}")

    async def get_available_base_years(self, project_name: str) -> List[int]:
        """Retrieves available base years from the project's load curve template."""
        cache_key = f"available_base_years:{project_name}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"Using cached available base years for project '{project_name}'")
            return cached_data

        generator = await self._get_project_generator(project_name)
        try:
            base_years = await generator.get_available_base_years()
            self._set_cache(cache_key, base_years)
            return base_years
        except ResourceNotFoundError: # Raised by load_template_data if template missing
            return [] # No base years if template is missing
        except Exception as e:
            logger.exception(f"Error getting available base years for project '{project_name}': {e}")
            # Depending on strictness, could raise ProcessingError or return empty list
            return []

    async def list_saved_profiles(self, project_name: str) -> List[Dict[str, Any]]:
        """Lists all saved load profiles with their metadata for a project."""
        cache_key = f"profiles_list:{project_name}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"Using cached list of saved profiles for project '{project_name}'")
            return cached_data

        generator = await self._get_project_generator(project_name)
        try:
            profiles_metadata = await generator.get_saved_profiles_metadata()
            self._set_cache(cache_key, profiles_metadata)
            return profiles_metadata
        except Exception as e:
            logger.exception(f"Error listing saved profiles for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to list saved profiles: {str(e)}")

    # Methods like get_scenario_analysis
    # would be adapted similarly, using the project-specific generator and async calls.
    # The analysis logic itself (_analyze_template_data, etc.) would remain largely the same
    # but ensure it works with data loaded by the (potentially refactored) generator.

print("Defining load profile service (generation/management) for FastAPI... (merged and adapted)")
