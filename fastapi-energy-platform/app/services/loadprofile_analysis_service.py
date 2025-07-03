# fastapi-energy-platform/app/services/loadprofile_analysis_service.py
"""
Service Layer for Load Profile Analysis.
Performs various analytical operations on existing load profiles.
"""
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np # For statistical calculations

from app.services.loadprofile_service import LoadProfileService # To fetch profile data
from app.models.loadprofile_analysis import AvailableProfileForAnalysis, StatisticalSummary # Pydantic models
from app.utils.error_handlers import ResourceNotFoundError, ProcessingError
from app.utils.constants import UNIT_FACTORS # For unit conversions

logger = logging.getLogger(__name__)

class LoadProfileAnalysisService:
    def __init__(self, project_data_root: Path, load_profile_service: LoadProfileService):
        self.project_data_root = project_data_root # May not be directly used if all data comes via LoadProfileService
        self.load_profile_service = load_profile_service
        # Could also have its own ProjectLoadProfileManager if it needs to access files not exposed by LoadProfileService
        # For now, assumes LoadProfileService provides necessary raw data.

    async def _get_profile_dataframe(self, project_name: str, profile_id: str) -> pd.DataFrame:
        """
        Helper to fetch profile data and convert it to a pandas DataFrame.
        Assumes data_records contain 'timestamp' and 'demand_kw' (or similar value column).
        """
        try:
            profile_details = await self.load_profile_service.get_profile_detailed_data(project_name, profile_id)
            data_records = profile_details.get("data_records")
            if not data_records:
                raise ResourceNotFoundError(f"No data records found for profile '{profile_id}' in project '{project_name}'.")

            df = pd.DataFrame(data_records)
            if 'timestamp' not in df.columns:
                raise ProcessingError(f"Profile '{profile_id}' data is missing 'timestamp' column.")

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # Assuming there's a single value column for demand, e.g., 'demand_kw' or the first non-timestamp column
            # This part might need to be more robust based on actual CSV structure from LoadProfileService/Manager
            value_col = next((col for col in df.columns if col.lower().startswith('demand') or col.lower().startswith('value')), None)
            if not value_col and len(df.columns) > 1:
                value_col = df.columns[1] # Fallback: assume second column is value

            if not value_col:
                 raise ProcessingError(f"Could not identify demand value column in profile '{profile_id}'.")

            df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
            df = df.dropna(subset=[value_col]) # Remove rows where demand is NaN after conversion
            df = df.rename(columns={value_col: 'demand'}) # Standardize value column name to 'demand'

            return df.set_index('timestamp').sort_index()

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error loading DataFrame for profile '{profile_id}', project '{project_name}': {e}")
            raise ProcessingError(f"Failed to load data for profile '{profile_id}': {str(e)}")

    async def list_available_profiles_for_analysis(self, project_name: str) -> List[AvailableProfileForAnalysis]:
        """
        Lists profiles available for analysis, potentially adding quick validation status.
        Leverages LoadProfileService.list_saved_profiles.
        """
        saved_profiles_metadata = await self.load_profile_service.list_saved_profiles(project_name)

        analysis_profiles = []
        for meta in saved_profiles_metadata:
            # Perform a very basic validation (e.g., does data file exist and have some content?)
            # More complex validation would be a separate analysis type.
            quick_validation = {"valid": True, "issues": []}
            if not meta.get('file_info', {}).get('exists'):
                quick_validation['valid'] = False
                quick_validation['issues'].append("Data file (CSV) is missing.")
            elif meta.get('file_info', {}).get('size_kb', 0) < 0.1: # Arbitrary small size check
                quick_validation['valid'] = False
                quick_validation['issues'].append("Data file seems empty or too small.")

            analysis_profiles.append(
                AvailableProfileForAnalysis(
                    profile_id=meta['profile_id'],
                    project_name=meta.get('project_name', project_name), # Ensure project_name
                    method_used=meta.get('method_used'),
                    created_at=meta.get('created_at'),
                    years_generated=meta.get('years_generated'),
                    frequency=meta.get('frequency'),
                    file_info=meta.get('file_info'),
                    quick_validation_status=quick_validation
                )
            )
        return analysis_profiles

    async def get_statistical_summary(
        self, project_name: str, profile_id: str, unit: str = "kW"
    ) -> StatisticalSummary:
        """Calculates and returns basic statistical summary of a load profile."""
        df = await self._get_profile_dataframe(project_name, profile_id)
        if df.empty or 'demand' not in df.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id}' for statistical summary.")

        demand_series = df['demand']

        # Convert to requested unit if necessary (assuming 'demand' is in kW from source)
        # This logic depends on the base unit of saved profiles. If it's always kW:
        conversion_factor = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(unit, 1)
        demand_series_converted = demand_series * conversion_factor

        stats = StatisticalSummary(
            min_value=float(demand_series_converted.min()),
            max_value=float(demand_series_converted.max()),
            mean_value=float(demand_series_converted.mean()),
            median_value=float(demand_series_converted.median()),
            std_dev=float(demand_series_converted.std()),
            q1_value=float(demand_series_converted.quantile(0.25)),
            q3_value=float(demand_series_converted.quantile(0.75)),
            total_sum=float(demand_series_converted.sum()), # This is energy if demand is power and time step is 1hr
            count=int(demand_series_converted.count())
        )

        # Calculate duration and load factor if possible (assuming hourly data for simplicity here)
        if pd.api.types.is_datetime64_any_dtype(df.index):
            duration_seconds = (df.index.max() - df.index.min()).total_seconds()
            if duration_seconds > 0:
                stats.duration_hours = duration_seconds / 3600
                if stats.max_value > 0 : # Avoid division by zero
                    # Load factor calculation needs average power over the exact period.
                    # If data is regular, mean is fine.
                    stats.load_factor = stats.mean_value / stats.max_value if stats.max_value else 0.0


        return stats

    # Placeholder for other analysis methods mentioned in the Flask blueprint:
    # async def perform_single_analysis(self, project_name: str, profile_id: str, analysis_type: str, params: Dict) -> Dict: ...
    # async def get_comprehensive_analysis(self, project_name: str, profile_id: str) -> Dict: ...
    # async def compare_multiple_profiles(self, project_name: str, profile_ids: List[str], comparison_type: str, params: Dict) -> Dict: ...
    # ... and so on for seasonal, decomposition, validation, export, batch, reports.

logger.info("LoadProfileAnalysisService defined for FastAPI.")
