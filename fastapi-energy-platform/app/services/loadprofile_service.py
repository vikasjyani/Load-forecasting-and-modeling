# fastapi-energy-platform/app/services/loadprofile_service.py
"""
Load Profile Service Layer for FastAPI
Handles business logic for load profile generation, management, and retrieval.
"""
import os
import json
import pandas as pd
import numpy as np # For potential use in analysis methods
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from fastapi import UploadFile

# Assuming the original LoadProfileGenerator is in the root 'models' directory
# This might require PYTHONPATH adjustments or a different import strategy
# depending on how the FastAPI app is run.
from models.load_profile_generator import LoadProfileGenerator
from app.utils.helpers import get_file_info, ensure_directory, safe_filename
from app.utils.constants import VALIDATION_RULES, UNIT_FACTORS # Check relevance
from app.utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# Basic Async In-Memory Cache
class AsyncInMemoryCache:
    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            item = self._cache.get(key)
            if item:
                data, timestamp = item
                if (datetime.now().timestamp() - timestamp) < self._default_ttl:
                    logger.debug(f"Cache HIT for key: {key}")
                    return data
                else:
                    logger.debug(f"Cache STALE for key: {key}")
                    del self._cache[key] # Remove stale item
            logger.debug(f"Cache MISS for key: {key}")
            return None

    async def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        async with self._lock:
            # Use specific ttl if provided, else default
            # For simplicity, current implementation uses default_ttl for all items
            self._cache[key] = (data, datetime.now().timestamp())
            logger.debug(f"Cache SET for key: {key}")

    async def clear_pattern(self, pattern: str):
        async with self._lock:
            keys_to_delete = [key for key in self._cache if pattern in key]
            for key in keys_to_delete:
                del self_cache[key]
            logger.info(f"Cache cleared for pattern: {pattern}, {len(keys_to_delete)} items removed.")

    async def clear(self, key: Optional[str] = None):
        async with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                    logger.info(f"Cache cleared for key: {key}")
            else:
                self._cache.clear()
                logger.info("Cache fully cleared.")


class LoadProfileService:
    """Service layer for load profile operations for FastAPI."""

    def __init__(self, project_data_root: Path):
        self.project_data_root = project_data_root
        self.cache = AsyncInMemoryCache(default_ttl_seconds=600) # 10 min TTL

    def _get_project_specific_path(self, project_name: str) -> Path:
        # Sanitize project_name to prevent path traversal if it's ever sourced unsafely
        # Though typically project_name would come from a validated source (e.g., projects API)
        s_project_name = safe_filename(project_name) # Basic sanitization
        if not s_project_name:
            raise ValueError("Invalid project name provided.")
        return self.project_data_root / s_project_name

    async def _get_generator_for_project(self, project_name: str) -> LoadProfileGenerator:
        project_path = self._get_project_specific_path(project_name)
        # Ensure project directories exist (idempotent)
        # These are synchronous but should be quick. If problematic, make them async.
        # LoadProfileGenerator itself might also ensure these.
        await asyncio.to_thread(ensure_directory, project_path / "inputs")
        await asyncio.to_thread(ensure_directory, project_path / "results" / "load_profiles")
        await asyncio.to_thread(ensure_directory, project_path / "config")

        # LoadProfileGenerator instantiation is synchronous.
        return await asyncio.to_thread(LoadProfileGenerator, str(project_path))

    # --- Ported/Adapted Methods from Flask Service ---

    async def get_main_page_data(self, project_name: str) -> Dict[str, Any]:
        cache_key = f"lp_main_data:{project_name}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)

        available_scenarios_task = self._get_available_scenarios(project_name)
        saved_profiles_task = self.get_saved_profiles_with_metadata(project_name) # This is already async
        template_info_task = self._get_template_availability(generator)

        available_scenarios, saved_profiles_data, template_info = await asyncio.gather(
            available_scenarios_task, saved_profiles_task, template_info_task
        )

        data = {
            'project_name': project_name,
            'template_info': template_info,
            'available_scenarios': available_scenarios,
            'saved_profiles': saved_profiles_data.get('profiles', []),
            'total_saved_profiles': saved_profiles_data.get('total_count', 0),
            'stl_available': hasattr(generator, 'generate_stl_forecast'), # Check actual capability
            'page_loaded_at': datetime.now().isoformat()
        }
        await self.cache.set(cache_key, data)
        return data

    async def get_template_info(self, project_name: str) -> Dict[str, Any]: # Renamed from get_template_analysis
        cache_key = f"lp_template_info:{project_name}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            # Assuming generator.load_template_data() is sync and returns the structure
            # needed by _analyze_template_data (which is also sync)
            template_data = await asyncio.to_thread(generator.load_template_data)
            analysis = await asyncio.to_thread(self._analyze_template_data, template_data, generator) # Pass generator

            await self.cache.set(cache_key, analysis)
            return analysis
        except FileNotFoundError:
             raise ResourceNotFoundError(f"Load curve template not found for project '{project_name}'.")
        except Exception as e:
            logger.exception(f"Error analyzing template for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to analyze template: {str(e)}")

    async def get_available_base_years(self, project_name: str) -> List[int]:
        cache_key = f"lp_base_years:{project_name}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            template_data = await asyncio.to_thread(generator.load_template_data)
            historical_data = template_data['historical_demand']
            available_years = await asyncio.to_thread(generator.get_available_base_years, historical_data)

            # No complex year_analysis here, just the list of years for the API.
            # The old service returned a dict with 'year_analysis', 'recommended_year', etc.
            # For now, returning just the list as per React client's expectation for this specific endpoint.
            # More detailed info can be fetched via get_base_year_detailed_info.

            await self.cache.set(cache_key, available_years)
            return available_years
        except FileNotFoundError: # Raised by load_template_data if template is missing
            return [] # Return empty list if template is not found
        except Exception as e:
            logger.exception(f"Error getting available base years for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get base years: {str(e)}")

    async def get_demand_scenario_info(self, project_name: str, scenario_name: str) -> Dict[str, Any]:
        # Renamed from get_scenario_analysis for clarity with API endpoint
        cache_key = f"lp_scenario_info:{project_name}:{scenario_name}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            scenario_df = await asyncio.to_thread(generator.load_scenario_data, scenario_name)
            if scenario_df.empty:
                raise ResourceNotFoundError(f"Demand scenario '{scenario_name}' data is empty or not found.")

            project_path = self._get_project_specific_path(project_name)
            scenario_csv_path = project_path / "results" / "demand_projection" / safe_filename(scenario_name) / "consolidated_results.csv"

            analysis = await asyncio.to_thread(self._analyze_scenario_data, scenario_df, scenario_name, str(scenario_csv_path))

            await self.cache.set(cache_key, analysis)
            return analysis
        except FileNotFoundError as e: # Raised by load_scenario_data
            raise ResourceNotFoundError(f"Demand scenario '{scenario_name}' not found for project '{project_name}': {str(e)}")
        except Exception as e:
            logger.exception(f"Error analyzing scenario '{scenario_name}' for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get scenario info: {str(e)}")


    async def generate_profile(self, project_name: str, generation_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a load profile (base or STL) for a project."""
        generator = await self._get_generator_for_project(project_name)

        # Load template data once
        try:
            template_data = await asyncio.to_thread(generator.load_template_data)
            historical_data_df = template_data.get('historical_demand', pd.DataFrame())
        except FileNotFoundError:
             raise ProcessingError(f"Load curve template not found for project '{project_name}'. Cannot generate profile.")
        except Exception as e:
            raise ProcessingError(f"Error loading template data for profile generation: {str(e)}")

        # Load demand scenario if specified
        demand_scenarios_df = None
        if config.get("demand_source") == "scenario" and config.get("scenario_name"):
            try:
                demand_scenarios_df = await asyncio.to_thread(generator.load_scenario_data, config["scenario_name"])
            except FileNotFoundError:
                raise ProcessingError(f"Demand scenario '{config['scenario_name']}' not found.")
        elif config.get("demand_source") == "template":
            demand_scenarios_df = template_data.get('total_demand', pd.DataFrame())

        if demand_scenarios_df is None or demand_scenarios_df.empty:
            raise ProcessingError("Demand data (from template or scenario) is not available or empty.")

        constraints = await asyncio.to_thread(self._prepare_constraints, config, template_data)

        try:
            if generation_type == "base_profile":
                if 'base_year' not in config: raise ValidationError("'base_year' is required for base profile.")
                result = await asyncio.to_thread(
                    generator.generate_base_profile_forecast,
                    historical_data=historical_data_df,
                    demand_scenarios=demand_scenarios_df,
                    base_year=int(config['base_year']),
                    start_fy=int(config['start_fy']),
                    end_fy=int(config['end_fy']),
                    frequency=config.get('frequency', 'hourly'),
                    constraints=constraints
                )
            elif generation_type == "stl_profile":
                result = await asyncio.to_thread(
                    generator.generate_stl_forecast,
                    historical_data=historical_data_df,
                    demand_scenarios=demand_scenarios_df,
                    start_fy=int(config['start_fy']),
                    end_fy=int(config['end_fy']),
                    frequency=config.get('frequency', 'hourly'),
                    stl_params=config.get('stl_params', {}),
                    constraints=constraints,
                    lf_improvement=config.get('lf_improvement')
                )
            else:
                raise ValidationError(f"Unknown profile generation type: {generation_type}")

            if result.get('status') == 'success':
                custom_name = config.get('custom_name', '').strip()
                profile_id_suggestion = f"{custom_name}_{generation_type}" if custom_name else None

                save_info = await asyncio.to_thread(generator.save_forecast, result['data'], profile_id=profile_id_suggestion)

                await self.cache.clear_pattern(f"lp_profiles_list:{project_name}")
                await self.cache.clear(f"lp_profile_detail:{project_name}:{save_info['profile_id']}")

                # Create a summary for the response
                profile_summary_data = result['data']
                profile_summary_data['method'] = generation_type # Ensure method is in the summary data
                profile_summary_data['start_fy'] = config['start_fy']
                profile_summary_data['end_fy'] = config['end_fy']
                profile_summary_data['frequency'] = config.get('frequency', 'hourly')


                return {
                    'success': True,
                    'profile_id': save_info['profile_id'],
                    'file_path': str(save_info['file_path']), # Convert Path to str
                    'metadata_path': str(save_info['metadata_path']), # Convert Path to str
                    'generation_config': config,
                    'summary': self._create_generation_summary(profile_summary_data) # Use sync helper for now
                }
            else:
                raise ProcessingError(result.get('message', "Profile generation failed internally."))
        except Exception as e:
            logger.exception(f"Error during {generation_type} profile generation for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to generate {generation_type} profile: {str(e)}")


    async def get_saved_profiles_with_metadata(self, project_name: str) -> Dict[str, Any]:
        cache_key = f"lp_profiles_list:{project_name}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            profiles = await asyncio.to_thread(generator.get_saved_profiles) # This is sync in original

            enhanced_profiles = []
            for profile_meta in profiles:
                profile_id = profile_meta.get("profile_id")
                if profile_id:
                    csv_path = generator.results_profiles_path / f"{profile_id}.csv"
                    if await asyncio.to_thread(csv_path.exists):
                        profile_meta['file_info'] = await get_file_info(csv_path)
                    else:
                         profile_meta['file_info'] = {'exists': False, 'error': 'CSV missing.'}
                enhanced_profiles.append(profile_meta)

            enhanced_profiles.sort(key=lambda x: x.get('generated_at', ''), reverse=True)

            data = {
                'profiles': enhanced_profiles,
                'total_count': len(enhanced_profiles),
                # Removed _group_profiles_by_method for simplicity, can be added if needed by frontend
            }
            await self.cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.exception(f"Error getting saved profiles for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to retrieve saved profiles: {str(e)}")

    async def get_profile_detailed_data(self, project_name: str, profile_id: str) -> Dict[str, Any]:
        cache_key = f"lp_profile_detail:{project_name}:{profile_id}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            # get_profile_data in original generator loads CSV and metadata
            profile_data = await asyncio.to_thread(generator.get_profile_data, profile_id)

            # If _analyze_profile_data is complex/IO-bound, make it async or run in thread
            # Assuming it's CPU-bound for now if it does significant pandas work
            # detailed_analysis = await asyncio.to_thread(self._analyze_profile_data, profile_data, profile_id)
            # For now, returning the raw loaded data; analysis can be a separate endpoint.
            # The original Flask service's _analyze_profile_data was mostly placeholders.

            await self.cache.set(cache_key, profile_data)
            return profile_data
        except FileNotFoundError:
            raise ResourceNotFoundError(f"Profile '{profile_id}' not found for project '{project_name}'.")
        except Exception as e:
            logger.exception(f"Error getting detailed data for profile '{profile_id}' in project '{project_name}': {e}")
            raise ProcessingError(f"Could not retrieve profile details: {str(e)}")

    async def delete_profile(self, project_name: str, profile_id: str) -> Dict[str, Any]:
        generator = await self._get_generator_for_project(project_name)
        try:
            # delete_profile in original generator handles file deletions
            result = await asyncio.to_thread(generator.delete_profile, profile_id) # Original is synchronous

            if result.get('success'):
                await self.cache.clear_pattern(f"lp_profiles_list:{project_name}")
                await self.cache.clear(f"lp_profile_detail:{project_name}:{profile_id}")
                return {'success': True, 'message': f"Profile '{profile_id}' deleted.", 'files_deleted': result.get('files_deleted', [])}
            else:
                raise ProcessingError(result.get('error', "Failed to delete profile."))
        except Exception as e:
            logger.exception(f"Error deleting profile '{profile_id}' for project '{project_name}': {e}")
            raise ProcessingError(f"Could not delete profile: {str(e)}")

    async def get_profile_file_path(self, project_name: str, profile_id: str) -> Path:
        generator = await self._get_generator_for_project(project_name)
        # get_profile_file_path in original generator is synchronous
        file_path_str = await asyncio.to_thread(generator.get_profile_file_path, profile_id)
        if not file_path_str:
            raise ResourceNotFoundError(f"File path for profile '{profile_id}' not found in project '{project_name}'.")
        return Path(file_path_str)

    async def upload_template_file(self, project_name: str, file: UploadFile) -> Dict[str, Any]:
        generator = await self._get_generator_for_project(project_name)
        template_file_path = generator.inputs_path / 'load_curve_template.xlsx'

        try:
            # Ensure inputs directory exists (synchronous, but should be quick)
            await asyncio.to_thread(ensure_directory, generator.inputs_path)

            file_content = await file.read()

            def _save_file_sync():
                with open(template_file_path, "wb") as buffer:
                    buffer.write(file_content)
            await asyncio.to_thread(_save_file_sync)

            # Validate by trying to load it (original service used test_generator.load_template_data())
            # The new generator.load_template_data() should perform similar validation.
            template_analysis = await asyncio.to_thread(generator.load_template_data) # This also validates implicitly
            # Could add _validate_template_structure call here if it's more robust

            await self.cache.clear_pattern(f"lp_template_info:{project_name}")
            await self.cache.clear_pattern(f"lp_base_years:{project_name}")

            file_info_data = await get_file_info(template_file_path)
            return {"success": True, "message": "Template uploaded and validated.", "file_info": file_info_data}
        except Exception as e:
            logger.exception(f"Error uploading/validating template for project '{project_name}': {e}")
            # Attempt to remove partially uploaded/invalid file
            if await asyncio.to_thread(template_file_path.exists):
                await asyncio.to_thread(os.remove, template_file_path)
            raise ProcessingError(f"Template upload/validation failed: {str(e)}")

    # --- Helper methods (adapted from Flask service) ---
    async def _get_available_scenarios(self, project_name: str) -> List[Dict[str, Any]]:
        project_path = self._get_project_specific_path(project_name)
        scenarios_dir = project_path / 'results' / 'demand_projection'
        available_scenarios = []

        if await asyncio.to_thread(scenarios_dir.is_dir):
            try:
                # os.listdir is sync, run in thread
                items = await asyncio.to_thread(os.listdir, scenarios_dir)
                for item_name in items:
                    scenario_path = scenarios_dir / item_name
                    if await asyncio.to_thread(scenario_path.is_dir):
                        consolidated_file = scenario_path / 'consolidated_results.csv'
                        if await asyncio.to_thread(consolidated_file.exists):
                            file_info_data = await get_file_info(consolidated_file)
                            available_scenarios.append({
                                'name': item_name,
                                'path': str(consolidated_file), # For reference, not direct use by client
                                'file_info': file_info_data
                            })
            except Exception as e:
                logger.exception(f"Error listing available scenarios for project '{project_name}': {e}")
        return available_scenarios

    async def _get_template_availability(self, generator: LoadProfileGenerator) -> Dict[str, Any]:
        # generator.input_file_path is already a Path object
        template_path = generator.input_file_path # This is load_curve_template.xlsx from generator
        exists = await asyncio.to_thread(template_path.exists)
        file_info_data = None
        if exists:
            file_info_data = await get_file_info(template_path)
        return {
            'exists': exists,
            'path': str(template_path),
            'file_info': file_info_data
        }

    # _analyze_template_data, _analyze_scenario_data, _prepare_constraints,
    # _sanitize_name, _create_generation_summary, _group_profiles_by_method,
    # _validate_template_structure, and analysis helpers (_analyze_profile_data, etc.)
    # are mostly synchronous data manipulation logic. They can be called within
    # asyncio.to_thread if they become part of an async flow, or if they are complex.
    # For now, I'll keep them as synchronous helper methods called by async public methods.

    def _analyze_template_data(self, template_data: Dict, generator: LoadProfileGenerator) -> Dict[str, Any]:
        # This method is synchronous.
        # Original Flask service used generator.get_available_base_years.
        # For consistency, let's assume generator provides this.
        historical_demand_df = template_data.get('historical_demand', pd.DataFrame())
        total_demand_df = template_data.get('total_demand', pd.DataFrame())

        available_base_years_list = []
        if not historical_demand_df.empty:
            available_base_years_list = generator.get_available_base_years(historical_demand_df)


        return {
            'historical_data': {
                'records': len(historical_demand_df),
                'date_range': {
                    'start': historical_demand_df['ds'].min().isoformat() if not historical_demand_df.empty and 'ds' in historical_demand_df else None,
                    'end': historical_demand_df['ds'].max().isoformat() if not historical_demand_df.empty and 'ds' in historical_demand_df else None,
                },
                'available_years': sorted([int(y) for y in historical_demand_df['financial_year'].unique()]) if not historical_demand_df.empty and 'financial_year' in historical_demand_df else [],
                'complete_years': available_base_years_list
            },
            'total_demand': {
                'years': len(total_demand_df),
                'year_range': {
                    'start': int(total_demand_df['Financial_Year'].min()) if not total_demand_df.empty and 'Financial_Year' in total_demand_df else None,
                    'end': int(total_demand_df['Financial_Year'].max()) if not total_demand_df.empty and 'Financial_Year' in total_demand_df else None,
                }
            },
            'constraints_available': { # Logic from original
                'monthly_peaks': template_data.get('monthly_peaks') is not None or template_data.get('calculated_monthly_peaks') is not None,
                'monthly_load_factors': template_data.get('monthly_load_factors') is not None or template_data.get('calculated_load_factors') is not None,
            },
            'template_info': template_data.get('template_info', {})
        }

    def _analyze_scenario_data(self, scenario_df: pd.DataFrame, scenario_name: str, scenario_csv_path: str) -> Dict[str, Any]:
        # Synchronous helper
        demand_cols = [col for col in scenario_df.columns if col.lower() in ['total_on_grid_demand', 'total', 'total_demand']]
        if not demand_cols: raise ValueError("No total demand column found in scenario CSV.")
        demand_col = demand_cols[0]

        file_info_data = {} # Would need get_file_info here if path is valid & exists
        # This is tricky because this helper is sync. get_file_info is async.
        # For now, omitting file_info from here, API layer can add it if needed.

        return {
            'scenario_name': scenario_name,
            'file_path': scenario_csv_path, # Path passed in
            'data_summary': {
                'total_years': len(scenario_df),
                'year_range': {'start': int(scenario_df['Year'].min()), 'end': int(scenario_df['Year'].max())},
                'demand_range': {'min': float(scenario_df[demand_col].min()), 'max': float(scenario_df[demand_col].max())},
                'demand_column': demand_col,
            },
            'years_data': scenario_df[['Year', demand_col]].to_dict('records')
        }

    def _prepare_constraints(self, config: Dict, template_data: Dict) -> Optional[Dict]:
        # Synchronous helper
        # ... (logic from Flask service, seems fine as sync)
        apply_monthly_peaks = config.get('apply_monthly_peaks', False)
        apply_load_factors = config.get('apply_load_factors', False)
        if not apply_monthly_peaks and not apply_load_factors: return None
        constraints = {}
        if apply_monthly_peaks:
            constraints['monthly_peaks'] = template_data.get('monthly_peaks') or template_data.get('calculated_monthly_peaks')
        if apply_load_factors:
            constraints['monthly_load_factors'] = template_data.get('monthly_load_factors') or template_data.get('calculated_load_factors')
        return constraints

    def _create_generation_summary(self, data: Dict) -> Dict[str, Any]:
        # Synchronous helper from Flask service, seems fine
        forecast_df = data.get('forecast', pd.DataFrame()) # Ensure it's a DataFrame
        if not isinstance(forecast_df, pd.DataFrame):
            forecast_df = pd.DataFrame(forecast_df)

        return {
            'method': data.get('method', 'unknown'),
            'start_fy': data.get('start_fy'),
            'end_fy': data.get('end_fy'),
            'frequency': data.get('frequency', 'hourly'),
            'total_records': len(forecast_df),
            'peak_demand_generated': float(forecast_df['demand'].max()) if 'demand' in forecast_df.columns and not forecast_df.empty else None,
            'average_demand_generated': float(forecast_df['demand'].mean()) if 'demand' in forecast_df.columns and not forecast_df.empty else None,
            'validation_results': data.get('validation', {}),
            'stl_components_summary': {k: bool(v is not None) for k,v in data.get('stl_components', {}).items()},
            'load_factor_improvement_details': data.get('load_factor_improvement')
        }

    # --- Methods for new API endpoints ---
    async def get_historical_data_summary(self, project_name: str) -> Dict[str, Any]:
        cache_key = f"lp_hist_summary:{project_name}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            template_data = await asyncio.to_thread(generator.load_template_data)
            historical_data = template_data.get('historical_demand', pd.DataFrame())
            if historical_data.empty:
                return {"error": "No historical demand data in template."}

            # This logic was in Flask service, can be run in thread
            summary = await asyncio.to_thread(self._calculate_historical_summary_stats, historical_data)
            await self.cache.set(cache_key, summary)
            return summary
        except FileNotFoundError:
            raise ResourceNotFoundError(f"Load curve template not found for project '{project_name}'.")
        except Exception as e:
            logger.exception(f"Error getting historical summary for project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get historical summary: {str(e)}")

    def _calculate_historical_summary_stats(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        # Synchronous helper for stats calculation
        if historical_data.empty: return {}

        total_years = len(historical_data['financial_year'].unique())
        total_records = len(historical_data)
        date_range = {
            'start': historical_data['ds'].min().isoformat() if 'ds' in historical_data else None,
            'end': historical_data['ds'].max().isoformat() if 'ds' in historical_data else None,
        }
        peak_demand = float(historical_data['demand'].max()) if 'demand' in historical_data else 0
        avg_demand = float(historical_data['demand'].mean()) if 'demand' in historical_data else 0
        avg_load_factor = (avg_demand / peak_demand * 100) if peak_demand > 0 else 0

        # Simplified yearly_stats for this summary
        yearly_stats_summary = historical_data.groupby('financial_year')['demand'].agg(['count', 'mean', 'max']).reset_index().to_dict('records')

        return {
            'total_years_of_data': total_years,
            'total_data_points': total_records,
            'overall_date_range': date_range,
            'overall_peak_demand': peak_demand,
            'overall_average_demand': avg_demand,
            'overall_average_load_factor': round(avg_load_factor, 2),
            'yearly_stats_preview': yearly_stats_summary
        }

    async def get_base_year_detailed_info(self, project_name: str, year: int) -> Dict[str, Any]:
        cache_key = f"lp_base_year_detail:{project_name}:{year}"
        cached = await self.cache.get(cache_key)
        if cached: return cached

        generator = await self._get_generator_for_project(project_name)
        try:
            template_data = await asyncio.to_thread(generator.load_template_data)
            historical_data = template_data.get('historical_demand', pd.DataFrame())

            year_data_df = historical_data[historical_data['financial_year'] == year]
            if year_data_df.empty:
                raise ResourceNotFoundError(f"No data found for base year {year} in project '{project_name}'.")

            # This logic was in Flask service, can be run in thread
            info = await asyncio.to_thread(self._calculate_base_year_stats, year, year_data_df)
            await self.cache.set(cache_key, info)
            return info
        except FileNotFoundError:
            raise ResourceNotFoundError(f"Load curve template not found for project '{project_name}'.")
        except ResourceNotFoundError: # If year data itself is not found after loading template
            raise
        except Exception as e:
            logger.exception(f"Error getting detailed info for base year {year}, project '{project_name}': {e}")
            raise ProcessingError(f"Failed to get base year info: {str(e)}")

    def _calculate_base_year_stats(self, year: int, year_data_df: pd.DataFrame) -> Dict[str, Any]:
        # Synchronous helper for stats calculation
        if year_data_df.empty: return {}

        date_range = {
            'start': year_data_df['ds'].min().isoformat() if 'ds' in year_data_df else None,
            'end': year_data_df['ds'].max().isoformat() if 'ds' in year_data_df else None,
        }
        demand_series = year_data_df['demand'].dropna()
        data_quality = {
            'missing_values': int(year_data_df['demand'].isnull().sum()),
            'zero_values': int((demand_series == 0).sum()),
            'negative_values': int((demand_series < 0).sum())
        }
        demand_stats = {
            'peak': float(demand_series.max()) if not demand_series.empty else 0,
            'min': float(demand_series.min()) if not demand_series.empty else 0,
            'avg': float(demand_series.mean()) if not demand_series.empty else 0,
            'std': float(demand_series.std()) if len(demand_series) > 1 else 0,
        }
        # Placeholder for pattern preview, original was complex
        pattern_preview_data = {"message": "Pattern preview generation needs to be fully ported if required."}

        return {
            'year': year,
            'total_records': len(year_data_df),
            'date_range': date_range,
            'data_quality': data_quality,
            'demand_stats': demand_stats,
            'pattern_preview': pattern_preview_data # Placeholder
        }

    # Placeholder for analysis methods from Flask service, if they need to be ported
    # async def analyze_profile(self, project_name: str, profile_id: str) -> Dict[str, Any]:
    #     # ... port logic from Flask service, making it async and using ProjectLoadProfileManager ...
    #     raise NotImplementedError("Profile analysis not yet fully ported.")

    # async def compare_profiles(self, project_name: str, profile_ids: List[str]) -> Dict[str, Any]:
    #     # ... port logic ...
    #     raise NotImplementedError("Profile comparison not yet fully ported.")

logger.info("FastAPI LoadProfileService defined.")
print("FastAPI LoadProfileService defined.")
