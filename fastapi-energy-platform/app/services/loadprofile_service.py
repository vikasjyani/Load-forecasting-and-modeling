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

    def load_template_data(self) -> Dict[str, Any]: # Mock implementation
        logger.debug(f"Loading template data (mock) from {self.inputs_path / 'load_curve_template.xlsx'}")
        return {"historical_demand": pd.DataFrame(), "total_demand": pd.DataFrame(), "monthly_peaks": None, "calculated_monthly_peaks": None, "monthly_load_factors": None, "calculated_load_factors": None, "template_info": {}}

    def get_available_base_years(self, historical_df: pd.DataFrame) -> List[int]: # Mock
        if not historical_df.empty and 'financial_year' in historical_df.columns:
            return sorted(historical_df['financial_year'].unique().tolist())
        return [2020, 2021, 2022] # Default mock

    def generate_base_profile_forecast(self, **kwargs) -> Dict[str, Any]: # Mock
        logger.debug(f"Generating base profile forecast (mock) with args: {kwargs.get('base_year')}, {kwargs.get('start_fy')}-{kwargs.get('end_fy')}")
        return {"status": "success", "data": {"load_profile": pd.DataFrame([{'timestamp': datetime.now().isoformat(), 'demand': 100}]), "method": "base_mock", "years_generated": [kwargs.get('start_fy')], "frequency": "hourly", "constraints_applied": False}}

    def generate_stl_forecast(self, **kwargs) -> Dict[str, Any]: # Mock
        logger.debug(f"Generating STL profile forecast (mock) with args: {kwargs.get('start_fy')}-{kwargs.get('end_fy')}")
        return {"status": "success", "data": {"load_profile": pd.DataFrame([{'timestamp': datetime.now().isoformat(), 'demand': 120}]), "method": "stl_mock", "years_generated": [kwargs.get('start_fy')], "frequency": "hourly", "constraints_applied": False}}

    def save_forecast(self, forecast_data: Dict[str, Any], profile_id: Optional[str] = None) -> Dict[str, Any]: # Mock
        if not profile_id:
            profile_id = f"mockprofile_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        df_to_save = forecast_data.get('load_profile', pd.DataFrame())
        if not isinstance(df_to_save, pd.DataFrame): # Ensure it's a DataFrame
             df_to_save = pd.DataFrame(df_to_save)


        file_path = self.results_profiles_path / f"{profile_id}.csv"
        df_to_save.to_csv(file_path, index=False)

        metadata = {
            "profile_id": profile_id, "method": forecast_data.get("method", "unknown"),
            "created_at": datetime.now().isoformat(), "source_config": forecast_data.get("config_snapshot"),
            "years": forecast_data.get("years_generated"), "frequency": forecast_data.get("frequency")
        }
        with open(self.config_path / f"{profile_id}_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved mock forecast {profile_id} to {file_path}")
        return {"profile_id": profile_id, "file_path": str(file_path), "metadata_path": str(self.config_path / f"{profile_id}_metadata.json")}

    def get_saved_profiles(self) -> List[Dict[str, Any]]: # Mock
        profiles = []
        for meta_file in self.config_path.glob("*_metadata.json"):
            try:
                with open(meta_file, "r") as f:
                    profiles.append(json.load(f))
            except Exception: continue
        logger.debug(f"Found {len(profiles)} saved mock profiles.")
        return profiles

    def get_profile_data(self, profile_id: str) -> Dict[str, Any]: # Mock
        meta_path = self.config_path / f"{profile_id}_metadata.json"
        csv_path = self.results_profiles_path / f"{profile_id}.csv"
        if meta_path.exists() and csv_path.exists():
            with open(meta_path, "r") as f: metadata = json.load(f)
            df = pd.read_csv(csv_path)
            logger.debug(f"Loaded mock profile data for {profile_id}.")
            return {"metadata": metadata, "data": df.to_dict("records")}
        raise ResourceNotFoundError(f"Mock profile {profile_id} not found.")

    def load_scenario_data(self, scenario_csv_path: Path) -> pd.DataFrame: # Mock
        if scenario_csv_path.exists():
            logger.debug(f"Loading mock scenario data from {scenario_csv_path}")
            return pd.read_csv(scenario_csv_path)
        return pd.DataFrame()


class LoadProfileService:
    """Service layer for load profile operations."""

    def __init__(self, project_data_root: Path):
        self.project_data_root = project_data_root
        # Caching (in-memory, consider Redis for distributed setups)
        self._cache: Dict[str, Tuple[Any, float]] = {} # key -> (data, timestamp)
        self._cache_ttl_seconds = 300

    def _get_project_generator(self, project_name: str) -> PlaceholderLoadProfileGenerator: # Type hint to actual generator when ready
        project_path = self.project_data_root / project_name
        if not project_path.is_dir():
            # Option: Create project path here if it's standard practice for new projects
            # ensure_directory(project_path)
            # ensure_directory(project_path / "inputs")
            # ensure_directory(project_path / "results" / "load_profiles")
            # ensure_directory(project_path / "config")
            raise ResourceNotFoundError(f"Project '{project_name}' path not found: {project_path}")
        return PlaceholderLoadProfileGenerator(project_path) # Use placeholder for now

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
            generator = self._get_project_generator(project_name)
            # These generator methods might do I/O, wrap in to_thread if they are blocking
            # available_scenarios = await asyncio.to_thread(self._get_available_scenarios_sync, project_name)
            # saved_profiles_data = await asyncio.to_thread(generator.get_saved_profiles) # Assuming this is list of dicts
            # template_info = await asyncio.to_thread(self._get_template_availability_sync, generator)

            available_scenarios = self._get_available_scenarios_sync(project_name)
            saved_profiles_raw = generator.get_saved_profiles()
            template_info = self._get_template_availability_sync(generator)

            # Enhance saved profiles with file info
            saved_profiles_enhanced = []
            for profile_meta in saved_profiles_raw:
                profile_id = profile_meta.get("profile_id")
                if profile_id:
                    csv_path = generator.results_profiles_path / f"{profile_id}.csv"
                    if csv_path.exists():
                        profile_meta['file_info'] = get_file_info(csv_path)
                saved_profiles_enhanced.append(profile_meta)


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


    def _get_template_availability_sync(self, generator: PlaceholderLoadProfileGenerator) -> Dict[str, Any]:
        """Synchronous helper for template availability."""
        template_path = generator.inputs_path / 'load_curve_template.xlsx'
        exists = template_path.exists()
        return {
            'exists': exists,
            'path': str(template_path),
            'file_info': get_file_info(template_path) if exists else None
        }

    def _get_available_scenarios_sync(self, project_name: str) -> List[Dict[str, Any]]:
        """Synchronous helper to get available demand scenarios."""
        # This path should point to where demand projection results are stored for the project
        scenarios_base_path = self.project_data_root / project_name / "results" / "demand_projection"
        available_scenarios = []
        if scenarios_base_path.is_dir():
            for item_path in scenarios_base_path.iterdir():
                if item_path.is_dir(): # Each scenario is a directory
                    # Check for a specific file that indicates a completed scenario, e.g., consolidated_results.csv
                    consolidated_file = item_path / 'consolidated_results.csv'
                    if consolidated_file.exists():
                        available_scenarios.append({
                            'name': item_path.name,
                            'path_to_consolidated_csv': str(consolidated_file), # For generator to load
                            'file_info': get_file_info(consolidated_file)
                        })
        return available_scenarios


    async def generate_profile(self, project_name: str, generation_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a load profile (base or STL) for a project."""
        # Validation should ideally happen at the Pydantic model level in the router,
        # but can also be done here for business logic specific checks.
        # validation_result = self.validate_generation_request(config, generation_type) # Assuming this method exists & is adapted
        # if not validation_result['valid']:
        #     raise ValidationError(f"Invalid generation request: {validation_result['errors']}")

        generator = self._get_project_generator(project_name)

        # Prepare demand scenarios from config
        demand_source = config.get('demand_source', 'template')
        demand_scenarios_df: pd.DataFrame
        if demand_source == 'template':
            # template_data = await asyncio.to_thread(generator.load_template_data)
            template_data = generator.load_template_data() # Sync for now
            demand_scenarios_df = template_data.get('total_demand', pd.DataFrame())
        elif demand_source == 'scenario':
            scenario_name = config.get('scenario_name')
            if not scenario_name: raise ValidationError("Scenario name required for scenario-based demand.")
            # Construct path to the scenario's consolidated results
            scenario_csv_path = self.project_data_root / project_name / "results" / "demand_projection" / scenario_name / "consolidated_results.csv"
            # demand_scenarios_df = await asyncio.to_thread(generator.load_scenario_data, scenario_csv_path)
            demand_scenarios_df = generator.load_scenario_data(scenario_csv_path) # Sync for now
        else:
            raise ValidationError(f"Invalid demand_source: {demand_source}")

        # historical_data_df = (await asyncio.to_thread(generator.load_template_data)).get('historical_demand', pd.DataFrame())
        historical_data_df = generator.load_template_data().get('historical_demand', pd.DataFrame()) # Sync for now

        # Prepare constraints (simplified, adapt _prepare_constraints if complex)
        # constraints = self._prepare_constraints(config, template_data) # Needs template_data

        # Call the appropriate generator method (potentially in a thread)
        if generation_type == "base_profile":
            # result = await asyncio.to_thread(
            #     generator.generate_base_profile_forecast,
            #     historical_data=historical_data_df, demand_scenarios=demand_scenarios_df,
            #     base_year=int(config['base_year']), start_fy=int(config['start_fy']), end_fy=int(config['end_fy']),
            #     frequency=config.get('frequency', 'hourly'), # constraints=constraints
            # )
            result = generator.generate_base_profile_forecast( # Sync for now
                 historical_data=historical_data_df, demand_scenarios=demand_scenarios_df,
                 base_year=int(config['base_year']), start_fy=int(config['start_fy']), end_fy=int(config['end_fy']),
                 frequency=config.get('frequency', 'hourly'), # constraints=constraints
            )
        elif generation_type == "stl_profile":
            # result = await asyncio.to_thread(
            #     generator.generate_stl_forecast,
            #      historical_data=historical_data_df, demand_scenarios=demand_scenarios_df,
            #      start_fy=int(config['start_fy']), end_fy=int(config['end_fy']),
            #      frequency=config.get('frequency', 'hourly'), stl_params=config.get('stl_params', {}), # constraints=constraints
            # )
            result = generator.generate_stl_forecast( # Sync for now
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

            # save_info = await asyncio.to_thread(generator.save_forecast, result['data'], profile_id=profile_id_to_save)
            save_info = generator.save_forecast(result['data'], profile_id=profile_id_to_save) # Sync for now

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

        generator = self._get_project_generator(project_name)
        try:
            # profile_content = await asyncio.to_thread(generator.get_profile_data, profile_id)
            profile_content = generator.get_profile_data(profile_id) # Sync for now (metadata + data records)
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
        generator = self._get_project_generator(project_name)
        files_deleted_log = []

        csv_path = generator.results_profiles_path / f"{profile_id}.csv"
        metadata_path = generator.config_path / f"{profile_id}_metadata.json"

        try:
            if csv_path.exists():
                # await asyncio.to_thread(csv_path.unlink)
                csv_path.unlink() # Sync for now
                files_deleted_log.append(f"Deleted data file: {csv_path.name}")
            if metadata_path.exists():
                # await asyncio.to_thread(metadata_path.unlink)
                metadata_path.unlink() # Sync for now
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
        generator = self._get_project_generator(project_name)
        template_file_path = generator.inputs_path / "load_curve_template.xlsx" # Standard name

        try:
            # Save the uploaded file, overwriting if exists
            with open(template_file_path, "wb") as buffer:
                content = await file.read() # Read from UploadFile
                buffer.write(content)

            # Perform a basic validation by trying to load it (can be more extensive)
            # await asyncio.to_thread(generator.load_template_data) # This would raise if format is very wrong
            generator.load_template_data() # Sync for now

            # Clear relevant caches if template changes
            self._cache.pop(f"template_analysis:{project_name}", None) # Example cache key
            self._cache.pop(f"base_years:{project_name}", None)

            logger.info(f"Uploaded and validated template for project '{project_name}' to {template_file_path}")
            return {
                "success": True, "message": "Template uploaded and validated successfully.",
                "file_info": get_file_info(template_file_path)
            }
        except Exception as e:
            logger.exception(f"Error uploading or validating template for project '{project_name}': {e}")
            # Attempt to remove partially saved or invalid file
            if template_file_path.exists(): template_file_path.unlink(missing_ok=True)
            raise ProcessingError(f"Template upload/validation failed: {str(e)}")


    # Methods like get_template_analysis, get_available_base_years, get_scenario_analysis
    # would be adapted similarly, using the project-specific generator and async calls.
    # The analysis logic itself (_analyze_template_data, etc.) would remain largely the same
    # but ensure it works with data loaded by the (potentially refactored) generator.

print("Defining load profile service (generation/management) for FastAPI... (merged and adapted)")
