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
    async def perform_peak_analysis(self, project_name: str, profile_id: str, params: PeakAnalysisParams) -> PeakAnalysisResultData:
        df = await self._get_profile_dataframe(project_name, profile_id)
        if df.empty or 'demand' not in df.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id}' for peak analysis.")

        demand_series = df['demand']
        conversion_factor = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(params.unit, 1)
        demand_series_converted = demand_series * conversion_factor

        # Simplified peak finding (top N values)
        # More sophisticated peak finding would consider window, prominence, etc.
        top_peaks_series = demand_series_converted.nlargest(params.top_n_peaks)

        top_peaks_info = [
            PeakInfo(timestamp=ts, value=round(val,3))
            for ts, val in top_peaks_series.items()
        ]

        return PeakAnalysisResultData(
            profile_id=profile_id,
            unit=params.unit,
            top_peaks=top_peaks_info,
            overall_peak_demand=round(float(demand_series_converted.max()),3),
            average_demand=round(float(demand_series_converted.mean()),3),
            parameters_used=params
        )

    async def generate_duration_curve(self, project_name: str, profile_id: str, params: DurationCurveParams) -> DurationCurveResultData:
        df = await self._get_profile_dataframe(project_name, profile_id)
        if df.empty or 'demand' not in df.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id}' for duration curve.")

        demand_series = df['demand']
        conversion_factor = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(params.unit, 1)
        demand_series_converted = demand_series * conversion_factor

        sorted_demand = demand_series_converted.sort_values(ascending=False).reset_index(drop=True)
        total_hours = len(sorted_demand)

        duration_curve_points = []
        if total_hours > 0:
            for i in range(params.num_points):
                percentage = (i / (params.num_points -1)) * 100
                index = int(np.floor((i / (params.num_points-1)) * (total_hours - 1))) # Ensure index is within bounds
                demand_value = sorted_demand.iloc[index]
                duration_curve_points.append(
                    DurationCurvePoint(percentage_of_time=round(percentage,2), demand_value=round(float(demand_value),3))
                )

        return DurationCurveResultData(
            profile_id=profile_id,
            unit=params.unit,
            duration_curve_points=duration_curve_points,
            parameters_used=params
        )

    async def perform_seasonal_analysis(self, project_name: str, profile_id: str, params: SeasonalAnalysisParams) -> SeasonalAnalysisResultData:
        df = await self._get_profile_dataframe(project_name, profile_id)
        if df.empty or 'demand' not in df.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id}' for seasonal analysis.")

        demand_series = df['demand']
        conversion_factor = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(params.unit, 1)
        demand_series_converted = demand_series * conversion_factor

        # Define seasons (Northern Hemisphere)
        # Winter: Dec, Jan, Feb (Months 12, 1, 2)
        # Spring: Mar, Apr, May (Months 3, 4, 5)
        # Summer: Jun, Jul, Aug (Months 6, 7, 8)
        # Autumn: Sep, Oct, Nov (Months 9, 10, 11)
        def get_season(month):
            if month in [12, 1, 2]: return "winter"
            if month in [3, 4, 5]: return "spring"
            if month in [6, 7, 8]: return "summer"
            if month in [9, 10, 11]: return "autumn"
            return "unknown"

        df_analysis = pd.DataFrame({'demand': demand_series_converted})
        df_analysis['month'] = df_analysis.index.month
        df_analysis['hour'] = df_analysis.index.hour
        df_analysis['season'] = df_analysis['month'].apply(get_season)

        seasonal_profiles_dict: Dict[str, List[SeasonalAverageProfile]] = {}

        if params.aggregation_type == "average_daily_profile":
            for season, group in df_analysis.groupby('season'):
                if group.empty: continue
                avg_daily_profile = group.groupby('hour')['demand'].mean()
                seasonal_profiles_dict[season] = [
                    SeasonalAverageProfile(hour_of_day=hr, average_demand=round(float(avg_val),3))
                    for hr, avg_val in avg_daily_profile.items()
                ]
        # Add other aggregation types like 'monthly_totals' if needed
        else:
            logger.warning(f"Unsupported aggregation type for seasonal analysis: {params.aggregation_type}")
            # Fallback or error
        else:
             logger.warning(f"Unsupported aggregation type for seasonal analysis: {params.aggregation_type}")
             # Potentially raise ProcessingError or return empty/error structure in result data


        return SeasonalAnalysisResultData(
            profile_id=profile_id,
            unit=params.unit,
            seasonal_profiles=seasonal_profiles_dict,
            parameters_used=params
        )

    async def perform_comprehensive_analysis(
        self, project_name: str, profile_id: str, params: 'ComprehensiveAnalysisParams' # Forward ref for type hint
    ) -> 'ComprehensiveAnalysisResultData': # Forward ref
        from app.models.loadprofile_analysis import ( # Import here to avoid circular dependency at module level
            ComprehensiveAnalysisParams, ComprehensiveAnalysisResultData,
            DailyAverageProfilePoint, WeeklyAverageProfilePoint, RampRateStats,
            MissingDataPeriod, LoadFactorDetails, StatisticalSummary
        )

        df_orig = await self._get_profile_dataframe(project_name, profile_id)
        if df_orig.empty or 'demand' not in df_orig.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id}' for comprehensive analysis.")

        demand_series_orig = df_orig['demand']

        conversion_factor = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(params.unit, 1)
        demand_series = demand_series_orig * conversion_factor

        df = pd.DataFrame({'demand': demand_series}) # Work with converted data

        # 1. Basic Statistics (re-using StatisticalSummary model structure)
        basic_stats = StatisticalSummary(
            min_value=float(demand_series.min()),
            max_value=float(demand_series.max()),
            mean_value=float(demand_series.mean()),
            median_value=float(demand_series.median()),
            std_dev=float(demand_series.std()),
            q1_value=float(demand_series.quantile(0.25)),
            q3_value=float(demand_series.quantile(0.75)),
            total_sum=float(demand_series.sum()), # Represents energy if original is power & steps are hourly
            count=int(demand_series.count())
        )
        data_period_start = df.index.min().to_pydatetime() if not df.empty else None
        data_period_end = df.index.max().to_pydatetime() if not df.empty else None

        # 2. Load Factor
        overall_load_factor = None
        if basic_stats.max_value > 0: # Avoid division by zero
            overall_load_factor = basic_stats.mean_value / basic_stats.max_value
        load_factor_details = LoadFactorDetails(overall_load_factor=overall_load_factor)

        # 3. Data Resolution
        data_resolution_minutes = None
        if len(df.index) > 1:
            # Infer frequency, then convert to minutes
            inferred_freq = pd.infer_freq(df.index)
            if inferred_freq:
                try:
                    # Attempt to convert frequency string to timedelta, then to minutes
                    td = pd.to_timedelta(pd.tseries.frequencies.to_offset(inferred_freq).nanos, unit='ns')
                    data_resolution_minutes = td.total_seconds() / 60
                except Exception: # Handle cases where conversion might fail for complex frequencies
                    logger.warning(f"Could not parse inferred frequency '{inferred_freq}' to minutes for profile {profile_id}.")
                    # Fallback: calculate median difference if parse fails
                    time_diffs = np.diff(df.index.values)
                    median_diff_ns = np.median(time_diffs)
                    data_resolution_minutes = median_diff_ns / (1e9 * 60) # Nanoseconds to minutes
            else: # Fallback if infer_freq is None (irregular data)
                time_diffs = np.diff(df.index.values) # Nanoseconds
                if len(time_diffs) > 0:
                    median_diff_ns = np.median(time_diffs)
                    data_resolution_minutes = median_diff_ns / (1e9 * 60)

        if data_resolution_minutes is not None:
            basic_stats.duration_hours = (basic_stats.count * data_resolution_minutes) / 60.0


        # 4. Average Daily Profiles
        average_daily_profiles_dict: Dict[str, List[DailyAverageProfilePoint]] = {}
        df_daily = df.copy()
        df_daily['hour'] = df_daily.index.hour
        df_daily['dayofweek'] = df_daily.index.dayofweek # Monday=0, Sunday=6

        # Overall average daily profile
        overall_avg_daily = df_daily.groupby('hour')['demand'].mean()
        average_daily_profiles_dict['overall'] = [
            DailyAverageProfilePoint(hour_of_day=hr, average_load=round(float(val),3))
            for hr, val in overall_avg_daily.items()
        ]
        # Weekday average daily profile
        weekday_avg_daily = df_daily[df_daily['dayofweek'] < 5].groupby('hour')['demand'].mean() # 0-4 are Mon-Fri
        if not weekday_avg_daily.empty:
            average_daily_profiles_dict['weekday'] = [
                DailyAverageProfilePoint(hour_of_day=hr, average_load=round(float(val),3))
                for hr, val in weekday_avg_daily.items()
            ]
        # Weekend average daily profile
        weekend_avg_daily = df_daily[df_daily['dayofweek'] >= 5].groupby('hour')['demand'].mean() # 5-6 are Sat-Sun
        if not weekend_avg_daily.empty:
            average_daily_profiles_dict['weekend'] = [
                DailyAverageProfilePoint(hour_of_day=hr, average_load=round(float(val),3))
                for hr, val in weekend_avg_daily.items()
            ]

        # 5. Average Weekly Profile (average load for each day of the week)
        # Using day names for clarity in results
        day_map = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
        avg_weekly_profile_series = df_daily.groupby('dayofweek')['demand'].mean()
        average_weekly_profile_list = [
            WeeklyAverageProfilePoint(day_of_week=day_map.get(day_idx, str(day_idx)), average_load=round(float(val),3))
            for day_idx, val in avg_weekly_profile_series.sort_index().items() # Ensure sorted by day index
        ]

        # 6. Ramp Rates (simplified: diff between consecutive points)
        ramp_rate_stats: Optional[RampRateStats] = None
        if data_resolution_minutes and data_resolution_minutes > 0 and len(demand_series) > 1:
            ramps = demand_series.diff() # Difference from previous point
            # Normalize to "per hour" if resolution is known
            ramps_per_hour = ramps * (60 / data_resolution_minutes) if data_resolution_minutes else ramps

            max_ramp_up = ramps_per_hour.max()
            max_ramp_down = ramps_per_hour.min() # This will be negative

            ramp_rate_stats = RampRateStats(
                max_ramp_up_value=round(float(max_ramp_up),3) if pd.notna(max_ramp_up) else 0.0,
                max_ramp_up_timestamp=ramps_per_hour.idxmax().to_pydatetime() if pd.notna(max_ramp_up) and pd.notna(ramps_per_hour.idxmax()) else None,
                max_ramp_down_value=round(float(max_ramp_down),3) if pd.notna(max_ramp_down) else 0.0,
                max_ramp_down_timestamp=ramps_per_hour.idxmin().to_pydatetime() if pd.notna(max_ramp_down) and pd.notna(ramps_per_hour.idxmin()) else None,
                average_ramp_rate_abs=round(float(ramps_per_hour.abs().mean()),3) if pd.notna(ramps_per_hour.abs().mean()) else 0.0,
                ramp_unit=f"{params.unit}/hour" if data_resolution_minutes else f"{params.unit}/interval"
            )

        # 7. Missing Data Periods (simple check for gaps larger than, say, 2x resolution)
        missing_data_periods_list: List[MissingDataPeriod] = []
        if data_resolution_minutes and len(df.index) > 1:
            time_diffs_minutes = df.index.to_series().diff().dt.total_seconds().fillna(0) / 60
            # Identify gaps significantly larger than typical resolution (e.g., > 2 * resolution, or a fixed threshold like 2 hours)
            gap_threshold_minutes = max(data_resolution_minutes * 2.5, 120) # e.g. 2.5x resolution or 2 hours

            gaps = df.index[time_diffs_minutes > gap_threshold_minutes]
            gap_starts = df.index[time_diffs_minutes.index.get_indexer(gaps) -1 ] # timestamp before the gap

            for start, end_of_gap_data_point in zip(gap_starts, gaps):
                duration_hours = (end_of_gap_data_point - start).total_seconds() / 3600
                # Refine duration to be the actual missing period, not including the data points themselves
                # This is approximate; more precise would be end_of_gap_data_point - (start + resolution_timedelta)
                actual_gap_duration_hours = duration_hours - (data_resolution_minutes / 60)
                if actual_gap_duration_hours > data_resolution_minutes / 60 : # Only report if gap is larger than one interval
                    missing_data_periods_list.append(
                        MissingDataPeriod(
                            start_time=start.to_pydatetime(), # Timestamp of last data point before gap
                            end_time=end_of_gap_data_point.to_pydatetime(), # Timestamp of first data point after gap
                            duration_hours=round(actual_gap_duration_hours,2)
                        )
                    )

        return ComprehensiveAnalysisResultData(
            profile_id=profile_id,
            unit=params.unit,
            parameters_used=params,
            basic_stats=basic_stats,
            load_factor_details=load_factor_details,
            average_daily_profiles=average_daily_profiles_dict,
            average_weekly_profile=average_weekly_profile_list,
            ramp_rates=ramp_rate_stats,
            missing_data_periods=missing_data_periods_list,
            data_resolution_minutes=round(data_resolution_minutes,2) if data_resolution_minutes is not None else None,
            data_period_start=data_period_start,
            data_period_end=data_period_end
        )

    async def compare_load_profiles(
        self, project_name: str, params: 'ProfileComparisonParams'
    ) -> 'ProfileComparisonResultData':
        from app.models.loadprofile_analysis import ( # Local import for Pydantic models
            ProfileComparisonParams, ProfileComparisonResultData, ComparisonMetric,
            ComparedProfilesTimeSeriesPoint, StatisticalSummary
        )

        if len(params.profile_ids) != 2:
            raise ProcessingError("Profile comparison requires exactly two profile IDs.")

        profile_id1, profile_id2 = params.profile_ids[0], params.profile_ids[1]

        # Fetch data for both profiles
        df1_orig = await self._get_profile_dataframe(project_name, profile_id1)
        df2_orig = await self._get_profile_dataframe(project_name, profile_id2)

        if df1_orig.empty or 'demand' not in df1_orig.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id1}' for comparison.")
        if df2_orig.empty or 'demand' not in df2_orig.columns:
            raise ProcessingError(f"No valid demand data in profile '{profile_id2}' for comparison.")

        # Unit conversion
        conversion_factor1 = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(params.unit, 1)
        conversion_factor2 = UNIT_FACTORS.get("kW", 1) / UNIT_FACTORS.get(params.unit, 1) # Could be different if base units differ

        df1 = pd.DataFrame({'demand': df1_orig['demand'] * conversion_factor1})
        df2 = pd.DataFrame({'demand': df2_orig['demand'] * conversion_factor2})

        # --- Time Series Alignment & Common Period ---
        # This is a simplified alignment: find common index and use it.
        # More advanced would involve resampling if frequencies differ.
        common_index = df1.index.intersection(df2.index)
        notes = []
        if len(common_index) == 0:
            notes.append("Profiles have no overlapping time period. Time-series comparison is not possible.")
            # Fallback: Calculate individual summaries but no direct comparison or time-series.
            summary1 = await self.get_statistical_summary(project_name, profile_id1, params.unit)
            summary2 = await self.get_statistical_summary(project_name, profile_id2, params.unit)
            return ProfileComparisonResultData(
                profiles_compared=[profile_id1, profile_id2],
                unit=params.unit,
                parameters_used=params,
                summary_profile1=summary1,
                summary_profile2=summary2,
                comparative_metrics=[],
                time_series_data=[],
                correlation_coefficient=None,
                notes=notes
            )

        df1_aligned = df1.loc[common_index]
        df2_aligned = df2.loc[common_index]

        common_period_start = common_index.min().to_pydatetime()
        common_period_end = common_index.max().to_pydatetime()

        # --- Calculate Statistical Summaries for the aligned period ---
        def calculate_summary_from_series(series: pd.Series, resolution_minutes: Optional[float]) -> StatisticalSummary:
            # Simplified summary calculation, similar to get_statistical_summary but from series
            summary = StatisticalSummary(
                min_value=float(series.min()), max_value=float(series.max()),
                mean_value=float(series.mean()), median_value=float(series.median()),
                std_dev=float(series.std()), q1_value=float(series.quantile(0.25)),
                q3_value=float(series.quantile(0.75)), total_sum=float(series.sum()),
                count=int(series.count())
            )
            if resolution_minutes and summary.count > 0: # Estimate duration if resolution is available
                 summary.duration_hours = (summary.count * resolution_minutes) / 60.0
            if summary.max_value > 0:
                summary.load_factor = summary.mean_value / summary.max_value
            return summary

        # Approximate resolution from aligned data (could be passed or inferred more robustly)
        # For simplicity, let's assume resolution of first profile if common_index is long enough
        approx_resolution_minutes = None
        if len(common_index) > 1:
            time_diffs = np.diff(common_index.values)
            median_diff_ns = np.median(time_diffs)
            approx_resolution_minutes = median_diff_ns / (1e9 * 60)

        summary1 = calculate_summary_from_series(df1_aligned['demand'], approx_resolution_minutes)
        summary2 = calculate_summary_from_series(df2_aligned['demand'], approx_resolution_minutes)

        # --- Comparative Metrics ---
        comparative_metrics_list: List[ComparisonMetric] = []
        metrics_to_compare = ["min_value", "max_value", "mean_value", "median_value", "std_dev", "total_sum", "load_factor"]
        for metric_key in metrics_to_compare:
            val1 = getattr(summary1, metric_key, None)
            val2 = getattr(summary2, metric_key, None)
            diff = None
            perc_diff = None
            if val1 is not None and val2 is not None:
                diff = val1 - val2
                if val1 != 0:
                    perc_diff = (diff / val1) * 100 if val1 else None # Avoid division by zero if val1 is 0

            comparative_metrics_list.append(ComparisonMetric(
                metric_name=metric_key.replace('_', ' ').capitalize(),
                value_profile1=val1, value_profile2=val2,
                difference=diff, percent_difference=perc_diff
            ))

        # --- Time Series Data for Plotting ---
        time_series_comparison: List[ComparedProfilesTimeSeriesPoint] = []
        # Downsample if too many points for frontend (e.g., > 2000 points)
        # This is a very basic downsample, more sophisticated methods exist (e.g., LTTB)
        max_points_frontend = 2000
        step = 1
        if len(df1_aligned) > max_points_frontend:
            step = int(len(df1_aligned) / max_points_frontend)
            notes.append(f"Time series data downsampled by a factor of {step} for display.")

        for i in range(0, len(df1_aligned), step):
            ts = df1_aligned.index[i].to_pydatetime()
            v1 = df1_aligned['demand'].iloc[i]
            v2 = df2_aligned['demand'].iloc[i]
            time_series_comparison.append(ComparedProfilesTimeSeriesPoint(
                timestamp=ts,
                value_profile1=round(float(v1),3) if pd.notna(v1) else None,
                value_profile2=round(float(v2),3) if pd.notna(v2) else None,
                difference=round(float(v1-v2),3) if pd.notna(v1) and pd.notna(v2) else None
            ))

        # --- Correlation Coefficient ---
        correlation = None
        if not df1_aligned['demand'].isnull().all() and not df2_aligned['demand'].isnull().all():
             # Ensure series are not all NaNs and have some variance
            if df1_aligned['demand'].nunique() > 1 and df2_aligned['demand'].nunique() > 1:
                correlation = df1_aligned['demand'].corr(df2_aligned['demand'])
            else:
                notes.append("Correlation not calculated due to constant values in one or both profiles over the common period.")


        return ProfileComparisonResultData(
            profiles_compared=[profile_id1, profile_id2],
            unit=params.unit,
            parameters_used=params,
            summary_profile1=summary1,
            summary_profile2=summary2,
            comparative_metrics=comparative_metrics_list,
            time_series_data=time_series_comparison,
            correlation_coefficient=correlation if pd.notna(correlation) else None,
            common_period_start=common_period_start,
            common_period_end=common_period_end,
            notes=notes
        )

    # TODO: Implement other analysis methods: benchmark, decomposition, validation, export, batch, reports.

logger.info("LoadProfileAnalysisService defined for FastAPI.")
