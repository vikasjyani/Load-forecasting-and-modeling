"""
Pydantic models for load profile generation, analysis, and management.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from enum import Enum

from app.models.common import JobStatusResponse, TaskAcceptedResponse # For async task responses
from app.models.core import TimeSeriesDataPoint # For representing profile data

class LoadProfileCategory(str, Enum):
    """
    Categories for load profiles.
    """
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    PUBLIC_SERVICES = "public_services"
    MIXED = "mixed"
    GENERATION_SOLAR = "generation_solar"
    GENERATION_WIND = "generation_wind"
    EV_CHARGING = "ev_charging"
    CUSTOM = "custom"

class LoadProfileBase(BaseModel):
    """
    Base attributes for a load profile.
    """
    name: str = Field(..., min_length=3, max_length=100, example="Typical Residential Summer Weekday")
    description: Optional[str] = Field(None, max_length=500)
    category: LoadProfileCategory = Field(..., example=LoadProfileCategory.RESIDENTIAL)
    region: Optional[str] = Field(None, example="Nordic Region")
    year: Optional[int] = Field(None, example=2023)
    resolution_minutes: Optional[int] = Field(None, gt=0, example=60, description="Time resolution in minutes (e.g., 15, 30, 60)")
    units: str = Field(default="kW", example="kW") # or kWh, MW, etc.
    source: Optional[str] = Field(None, example="Smart Meter Data Aggregation") # Or "Synthetic Generation"
    tags: Optional[List[str]] = Field(default_factory=list, example=["summer", "weekday", "smart_meter"])

class LoadProfileCreateData(BaseModel):
    """
    Data structure for creating a load profile with explicit data points.
    """
    data_points: List[TimeSeriesDataPoint] = Field(..., description="Time series data for the load profile")

class LoadProfileCreate(LoadProfileBase, LoadProfileCreateData):
    """
    Model for creating/uploading a new load profile with its data.
    """
    project_name: Optional[str] = Field(None, example="CommunityEnergyProject") # Optional project link

class LoadProfileResponse(LoadProfileBase):
    """
    Model for returning load profile data and metadata.
    """
    load_profile_id: str = Field(..., example="lp_res_summer_wd_001")
    project_name: Optional[str] = Field(None, example="CommunityEnergyProject")
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified_at: datetime = Field(default_factory=datetime.now)
    data_points: Optional[List[TimeSeriesDataPoint]] = Field(None, description="Actual data points, might be omitted in list views for brevity")
    # summary_statistics: Optional[Dict[str, float]] = Field(None, example={"peak_demand": 12.5, "average_demand": 5.2, "load_factor": 0.42})

    class Config:
        orm_mode = True

class LoadProfileGenerationConfig(BaseModel):
    """
    Parameters for generating a synthetic load profile.
    This is highly dependent on the generation algorithm.
    """
    profile_type_to_generate: LoadProfileCategory = Field(..., example=LoadProfileCategory.RESIDENTIAL)
    number_of_households: Optional[int] = Field(None, gt=0, example=100)
    base_year: int = Field(..., example=2023)
    target_date_start: Optional[date] = Field(None, description="Start date for the profile generation period")
    target_date_end: Optional[date] = Field(None, description="End date for the profile generation period")
    simulation_parameters: Dict[str, Any] = Field(default_factory=dict, example={"appliance_saturation": {"ac": 0.8, "heater": 0.6}})
    output_resolution_minutes: int = Field(default=60, example=60)
    random_seed: Optional[int] = Field(None)

class LoadProfileGenerationRequest(BaseModel):
    """
    Request to generate a load profile.
    """
    project_name: Optional[str] = Field(None, example="FutureCitySim")
    profile_name: str = Field(..., example="Generated Residential Profile Q1")
    generation_config: LoadProfileGenerationConfig

# Response for generation could be TaskAcceptedResponse leading to a LoadProfileResponse or JobStatusResponse

class LoadProfileAnalysisType(str, Enum):
    """
    Enum for different types of load profile analysis.
    """
    PEAK_ANALYSIS = "peak_analysis"
    LOAD_FACTOR_CALCULATION = "load_factor_calculation"
    DURATION_CURVE = "duration_curve"
    CLUSTERING_ANALYSIS = "clustering_analysis" # e.g., k-means on daily profiles
    PATTERN_RECOGNITION = "pattern_recognition"
    FREQUENCY_ANALYSIS = "frequency_analysis" # FFT for periodicity

class LoadProfileAnalysisConfigBase(BaseModel):
    """Base for analysis configurations."""
    analysis_type: LoadProfileAnalysisType

class PeakAnalysisConfig(LoadProfileAnalysisConfigBase):
    analysis_type: LoadProfileAnalysisType = Field(default=LoadProfileAnalysisType.PEAK_ANALYSIS, frozen=True)
    top_n_peaks: Optional[int] = Field(default=5, gt=0, example=10)
    peak_definition_window_hours: Optional[float] = Field(None, gt=0, example=1, description="Window to define a distinct peak")

class LoadFactorConfig(LoadProfileAnalysisConfigBase):
    analysis_type: LoadProfileAnalysisType = Field(default=LoadProfileAnalysisType.LOAD_FACTOR_CALCULATION, frozen=True)
    period_days: Optional[int] = Field(None, description="Period over which to calculate load factor (e.g., 30 for monthly). Defaults to entire profile duration.")

class ClusteringConfig(LoadProfileAnalysisConfigBase):
    analysis_type: LoadProfileAnalysisType = Field(default=LoadProfileAnalysisType.CLUSTERING_ANALYSIS, frozen=True)
    num_clusters: int = Field(..., gt=1, example=5)
    features_to_use: Optional[List[str]] = Field(None, example=["hourly_mean", "ramp_rate_max"]) # Features derived from daily profiles
    normalization_method: Optional[str] = Field(default="min_max", example="z_score")

# Union of all specific config types
AnalysisConfigType = Union[PeakAnalysisConfig, LoadFactorConfig, ClusteringConfig]


class LoadProfileAnalysisRequest(BaseModel):
    """
    Request to perform an analysis on one or more load profiles.
    """
    project_name: Optional[str] = Field(None, example="UniversityCampusStudy")
    load_profile_ids: List[str] = Field(..., min_items=1, example=["lp_main_building_2023", "lp_library_2023"])
    # analysis_config: AnalysisConfigType # This should work with discriminated unions in FastAPI
    analysis_configs: List[AnalysisConfigType] = Field(..., description="List of analysis configurations to apply.")


class LoadProfileAnalysisResultBase(BaseModel):
    """
    Base model for analysis results.
    """
    load_profile_id: str
    analysis_type: LoadProfileAnalysisType
    execution_timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None

class PeakInfo(BaseModel):
    timestamp: datetime
    value: float

class PeakAnalysisResultDetail(LoadProfileAnalysisResultBase):
    analysis_type: LoadProfileAnalysisType = Field(default=LoadProfileAnalysisType.PEAK_ANALYSIS, frozen=True)
    peaks: List[PeakInfo]
    average_demand: float
    peak_demand: float

class LoadFactorResultDetail(LoadProfileAnalysisResultBase):
    analysis_type: LoadProfileAnalysisType = Field(default=LoadProfileAnalysisType.LOAD_FACTOR_CALCULATION, frozen=True)
    load_factor: float = Field(..., ge=0, le=1)
    average_load: float
    peak_load: float
    period_analyzed_days: Optional[float] = None

class ClusterInfo(BaseModel):
    cluster_id: int
    member_profile_days_identifiers: List[Union[date, str]] # e.g., list of dates or daily profile IDs
    centroid_profile: Optional[List[float]] = None # Representative profile for the cluster
    silhouette_score: Optional[float] = None # If applicable

class ClusteringResultDetail(LoadProfileAnalysisResultBase):
    analysis_type: LoadProfileAnalysisType = Field(default=LoadProfileAnalysisType.CLUSTERING_ANALYSIS, frozen=True)
    num_clusters: int
    clusters: List[ClusterInfo]
    overall_inertia: Optional[float] = None
    # We might have multiple load_profile_ids if clustering across them
    # For simplicity, let's assume clustering is done on data from a single load_profile_id
    # or that the service layer handles aggregation if multiple IDs are passed.

# Union of specific result types
AnalysisResultDetailType = Union[PeakAnalysisResultDetail, LoadFactorResultDetail, ClusteringResultDetail]

class LoadProfileAnalysisJobResult(BaseModel):
    """Holds results for all requested analyses in a job."""
    job_id: str
    results_per_profile_and_analysis: List[AnalysisResultDetailType]


class LoadProfileInputDataSummary(BaseModel):
    """
    Summary of input data available for load profile tasks.
    """
    project_name: str
    available_load_profile_ids: List[str]
    data_time_range_start: Optional[datetime]
    data_time_range_end: Optional[datetime]
    notes: Optional[str] = None

class LoadProfileComparisonRequest(BaseModel):
    project_name: Optional[str]
    profile_ids_to_compare: List[str] = Field(..., min_items=2, max_items=10)
    metrics_to_compare: List[str] = Field(default=["peak_demand", "load_factor", "total_consumption"])
    baseline_profile_id: Optional[str] = Field(None, description="If provided, comparisons are relative to this profile")

class LoadProfileComparisonResult(BaseModel):
    comparison_timestamp: datetime = Field(default_factory=datetime.now)
    compared_profile_ids: List[str]
    baseline_profile_id: Optional[str]
    results: Dict[str, Dict[str, Any]] = Field(..., description="Key is profile_id, value is dict of metrics")
    # Example: {"lp1": {"peak_demand": 100, "load_factor": 0.5}, "lp2": {"peak_demand": 120, "load_factor": 0.4}}
    difference_from_baseline: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="If baseline, differences per profile")
