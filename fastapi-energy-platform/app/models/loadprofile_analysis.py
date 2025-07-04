# fastapi-energy-platform/app/models/loadprofile_analysis.py
"""
Pydantic models for Load Profile Analysis features.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

logger_models = logging.getLogger(__name__)

class ProfileIdentifier(BaseModel):
    project_name: str
    profile_id: str

class AnalysisRequestBase(ProfileIdentifier):
    unit: Optional[str] = Field(default="kW", description="Unit for analysis results if applicable.")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StatisticalSummary(BaseModel):
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_dev: float
    q1_value: float # 25th percentile
    q3_value: float # 75th percentile
    total_sum: Optional[float] = None
    count: int
    duration_hours: Optional[float] = None
    load_factor: Optional[float] = None

# --- Specific Analysis Parameter Models ---
class PeakAnalysisParams(BaseModel):
    top_n_peaks: int = Field(default=5, gt=0, le=50)
    peak_definition_window_hours: Optional[float] = Field(None, gt=0, description="Window (hours) to define distinct peaks.")
    unit: str = Field(default="kW", description="Unit for peak values in response.")

class DurationCurveParams(BaseModel):
    num_points: int = Field(default=100, gt=10, le=8760, description="Number of points for the duration curve.")
    unit: str = Field(default="kW", description="Unit for demand values in response.")

class SeasonalAnalysisParams(BaseModel):
    aggregation_type: str = Field(default="average_daily_profile", description="e.g., 'average_daily_profile', 'monthly_totals'")
    unit: str = Field(default="kW", description="Unit for demand values in response.")

class ComprehensiveAnalysisParams(BaseModel):
    unit: str = Field(default="kW", description="Unit for values in the analysis response.")

# --- Specific Analysis Result Models ---
class PeakInfo(BaseModel):
    timestamp: datetime
    value: float

class PeakAnalysisResultData(BaseModel):
    profile_id: str
    unit: str
    top_peaks: List[PeakInfo]
    overall_peak_demand: float
    average_demand: float
    parameters_used: PeakAnalysisParams

class DurationCurvePoint(BaseModel):
    percentage_of_time: float
    demand_value: float

class DurationCurveResultData(BaseModel):
    profile_id: str
    unit: str
    duration_curve_points: List[DurationCurvePoint]
    parameters_used: DurationCurveParams

class SeasonalAverageProfile(BaseModel):
    hour_of_day: int
    average_demand: float

class SeasonalAnalysisResultData(BaseModel):
    profile_id: str
    unit: str
    seasonal_profiles: Dict[str, List[SeasonalAverageProfile]]
    parameters_used: SeasonalAnalysisParams

class DailyAverageProfilePoint(BaseModel):
    hour_of_day: int
    average_load: float

class WeeklyAverageProfilePoint(BaseModel):
    day_of_week: Union[int, str]
    average_load: float

class RampRateStats(BaseModel):
    max_ramp_up_value: float
    max_ramp_up_timestamp: Optional[datetime] = None
    max_ramp_down_value: float
    max_ramp_down_timestamp: Optional[datetime] = None
    average_ramp_rate_abs: float
    ramp_unit: str

class MissingDataPeriod(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_hours: float

class LoadFactorDetails(BaseModel):
    overall_load_factor: Optional[float] = None

class ComprehensiveAnalysisResultData(BaseModel):
    profile_id: str
    unit: str
    parameters_used: ComprehensiveAnalysisParams
    basic_stats: StatisticalSummary
    load_factor_details: LoadFactorDetails
    average_daily_profiles: Dict[str, List[DailyAverageProfilePoint]] = Field(default_factory=dict)
    average_weekly_profile: List[WeeklyAverageProfilePoint] = Field(default_factory=list)
    ramp_rates: Optional[RampRateStats] = None
    missing_data_periods: List[MissingDataPeriod] = Field(default_factory=list)
    data_resolution_minutes: Optional[float] = None
    data_period_start: Optional[datetime] = None
    data_period_end: Optional[datetime] = None

# --- Profile Comparison Models ---
class ProfileComparisonParams(BaseModel):
    profile_ids: List[str] = Field(..., min_items=2, max_items=2, description="List containing two profile IDs to compare.")
    unit: str = Field(default="kW", description="Unit for comparison results.")
    # Optional: Add date range for comparison if needed
    # start_date: Optional[datetime] = None
    # end_date: Optional[datetime] = None

class ComparisonMetric(BaseModel):
    metric_name: str
    value_profile1: Optional[Any] = None # Using Any to accommodate non-float values like timestamps
    value_profile2: Optional[Any] = None
    difference: Optional[float] = None
    percent_difference: Optional[float] = None

class ComparedProfilesTimeSeriesPoint(BaseModel):
    timestamp: datetime
    value_profile1: Optional[float] = None
    value_profile2: Optional[float] = None
    difference: Optional[float] = None

class ProfileComparisonResultData(BaseModel):
    profiles_compared: List[str] # [profile_id1, profile_id2]
    unit: str
    parameters_used: ProfileComparisonParams
    summary_profile1: Optional[StatisticalSummary] = None
    summary_profile2: Optional[StatisticalSummary] = None
    comparative_metrics: List[ComparisonMetric] = Field(default_factory=list)
    time_series_data: Optional[List[ComparedProfilesTimeSeriesPoint]] = Field(default_factory=list, description="Aligned time series data for the common period, or resampled.")
    correlation_coefficient: Optional[float] = None
    common_period_start: Optional[datetime] = None
    common_period_end: Optional[datetime] = None
    notes: Optional[List[str]] = Field(default_factory=list, description="Notes on resampling, alignment, or discrepancies.")


# --- Generic and Utility Models ---
class ProfileAnalysisResult(BaseModel):
    profile_id: str # This might be redundant if the result_data itself contains it.
    analysis_type: str
    parameters_used: Optional[Dict[str, Any]] = None
    result_data: Union[
        StatisticalSummary,
        PeakAnalysisResultData,
        DurationCurveResultData,
        SeasonalAnalysisResultData,
        ComprehensiveAnalysisResultData,
        ProfileComparisonResultData, # Added
        Dict[str, Any] # Fallback
    ]
    error: Optional[str] = None

class AvailableProfileForAnalysis(BaseModel):
    profile_id: str
    project_name: str
    method_used: Optional[str] = None
    created_at: Optional[datetime] = None
    years_generated: Optional[List[int]] = None
    frequency: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None
    quick_validation_status: Optional[Dict[str, Any]] = None

class ProfileComparisonRequest(BaseModel): # This seems like a duplicate of ProfileComparisonParams in terms of intent for API body
    project_name: str # Typically from path
    profile_ids: List[str] = Field(..., min_items=2, max_items=5) # If allowing more than 2 for some reason
    comparison_type: str = Field(default="overview", description="Type of comparison, e.g., 'overview', 'statistical', 'seasonal'")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parameters for the comparison, e.g., unit, metrics")

class ProfileComparisonResult(BaseModel): # This seems like a duplicate of ProfileComparisonResultData
    profile_ids_compared: List[str]
    comparison_type: str
    comparison_data: Dict[str, Any]

class BatchAnalysisRequest(BaseModel):
    project_name: str
    profile_ids: List[str] = Field(..., min_items=1, max_items=10)
    analysis_types: List[str] = Field(..., min_items=1, description="List of analysis types to perform on each profile")
    common_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Common parameters for all analyses")

class BatchAnalysisResponse(BaseModel):
    project_name: str
    results: List[ProfileAnalysisResult]
    summary: Dict[str, int]

logger_models.info("Load Profile Analysis Pydantic models defined/updated with Comparison models.")
