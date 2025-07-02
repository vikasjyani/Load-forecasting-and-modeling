"""
Pydantic models for demand projection, forecasting, and related data.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.common import JobStatusResponse # For job status responses
from app.utils.constants import FORECAST_MODELS # For model validation

class SectorForecastParams(BaseModel):
    """
    Specific parameters for a forecasting model within a sector.
    e.g., for MLR, the independent variables; for WAM, window size.
    """
    independent_vars: Optional[List[str]] = Field(None, example=["GDP", "Population"])
    window_size: Optional[int] = Field(None, gt=0, example=10)
    # Add other model-specific parameters as needed
    # e.g., arima_order: Optional[Tuple[int, int, int]] = None

class SectorForecastConfig(BaseModel):
    """
    Configuration for forecasting for a single sector.
    """
    sector_name: str = Field(..., example="Residential")
    models_to_run: List[str] = Field(..., min_items=1, example=["MLR", "SARIMAX"])
    model_specific_params: Optional[Dict[str, SectorForecastParams]] = Field(
        default_factory=dict,
        description="Model-specific parameters, keyed by model name (e.g., 'MLR', 'WAM')",
        example={"MLR": {"independent_vars": ["GDP", "Population"]}, "WAM": {"window_size": 5}}
    )
    # Deprecating old structure, use model_specific_params instead
    # independent_vars: Optional[List[str]] = Field(None, deprecated=True, description="For MLR, use model_specific_params", example=["GDP", "Population"])
    # window_size: Optional[int] = Field(None, deprecated=True, gt=0, description="For WAM, use model_specific_params", example=10)


    @validator('models_to_run', each_item=True)
    def check_model_name(cls, model_name):
        if model_name not in FORECAST_MODELS:
            raise ValueError(f"Invalid forecast model: {model_name}. Allowed models are: {', '.join(FORECAST_MODELS.keys())}")
        return model_name

    # Example of how to ensure params are provided if a model is selected
    # @root_validator
    # def check_params_for_models(cls, values):
    #     models_to_run = values.get('models_to_run', [])
    #     model_specific_params = values.get('model_specific_params', {})
    #     if "MLR" in models_to_run and not model_specific_params.get("MLR", {}).get("independent_vars"):
    #         raise ValueError("Independent variables must be provided for MLR model.")
    #     if "WAM" in models_to_run and not model_specific_params.get("WAM", {}).get("window_size"):
    #         raise ValueError("Window size must be provided for WAM model.")
    #     return values


class DemandForecastJobConfigBase(BaseModel):
    """
    Base configuration for a demand forecast job.
    """
    project_name: str = Field(..., example="NationalEnergyOutlook")
    scenario_name: str = Field(..., min_length=3, max_length=100, example="HighEV_Adoption_2035")
    target_year: int = Field(..., gt=datetime.now().year, example=2035)
    exclude_covid_years: bool = Field(default=False, example=True)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(None, example=["forecast", "ev_impact", "national_level"])

class DemandForecastJobCreate(DemandForecastJobConfigBase):
    """
    Model for creating a new demand forecast job. This is the request body.
    """
    sector_configs: List[SectorForecastConfig] = Field(..., min_items=1)
    # Optional advanced settings can go here
    # advanced_settings: Optional[Dict[str, Any]] = None

class DemandForecastJobInfo(DemandForecastJobConfigBase, JobStatusResponse):
    """
    Extends common JobStatusResponse with demand forecast specific config.
    Useful for returning detailed job status.
    """
    job_id: str # Overrides from JobStatusResponse to ensure it's always present
    created_at: datetime = Field(default_factory=datetime.now)
    sector_configs_summary: Optional[List[str]] = Field(None, description="List of sector names configured for this job")

    @validator('sector_configs_summary', pre=True, always=True)
    def set_sector_configs_summary(cls, v, values):
        # This validator is tricky if sector_configs isn't part of this model directly.
        # This model is intended for RESPONSE, so it would be populated by the service.
        # If this model were used for CREATION and had sector_configs, then it could be:
        # configs = values.get('sector_configs')
        # if configs:
        #     return [sc.sector_name for sc in configs]
        return v # Placeholder if populated by service


class SectorForecastOutputFiles(BaseModel):
    """
    Paths to output files generated for a sector forecast.
    """
    forecast_data_csv: Optional[str] = Field(None, example="Residential_forecast_MLR.csv")
    visualization_plot_png: Optional[str] = Field(None, example="Residential_forecast_MLR_plot.png")
    log_file_txt: Optional[str] = Field(None, example="Residential_forecast_MLR.log")


class SectorForecastResult(BaseModel):
    """
    Detailed result for a single sector's forecast.
    Corresponds to SectorProcessingResult dataclass in service.
    """
    sector_name: str = Field(..., example="Industrial")
    status: str = Field(..., example="success") # e.g., 'success', 'failed', 'skipped'
    message: str = Field(..., example="Forecast completed successfully using SARIMAX.")
    models_used: List[str] = Field(default_factory=list, example=["SARIMAX"])
    error_details: Optional[str] = Field(None)
    processing_time_seconds: float = Field(..., example=120.5)
    configuration_used: SectorForecastConfig # The config that was used for this sector
    # Output files might be part of the message or a separate structure
    # output_files: Optional[SectorForecastOutputFiles] = None
    # Or a more generic way if Main_forecasting_function returns a dict with file paths:
    result_files: Optional[Dict[str, str]] = Field(None, description="Key-value pairs of result file descriptions and their paths", example={"csv_output": "results/Industrial_MLR.csv"})
    key_metrics: Optional[Dict[str, float]] = Field(None, description="Key metrics from the forecast", example={"MAPE": 0.05, "RMSE": 12.3})


class DemandForecastOverallResult(BaseModel):
    """
    The overall result of a demand forecast job.
    Corresponds to the 'detailed_summary' generated by the service.
    """
    job_id: str = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    scenario_name: str = Field(..., example="HighEV_Adoption_2035")
    status: str = Field(..., example="COMPLETED")
    completion_message: str = Field(..., example="Forecast completed with some errors.")
    total_sectors_configured: int = Field(..., example=5)
    total_sectors_processed: int = Field(..., example=5)
    successful_sectors: int = Field(..., example=4)
    failed_sectors: int = Field(..., example=1)
    # existing_data_sectors: int = Field(..., example=0) # If this status is used
    overall_output_path: str = Field(..., description="Base path where all results for this scenario are stored", example="projects/NationalEnergyOutlook/results/demand_projection/HighEV_Adoption_2035")
    total_forecast_processing_time_seconds: float = Field(..., example=650.2)
    processed_sector_details: List[SectorForecastResult]
    # Add other summary information as needed, e.g., aggregated energy totals


class DemandInputDataSummaryResponse(BaseModel):
    """
    Response model for summarizing input data for a demand projection project.
    Based on `get_input_data_summary` in service.
    """
    project_name: str
    sectors_available: List[str]
    sectors_missing_in_data: List[str]
    parameters_from_file: Dict[str, Any]
    aggregated_data_summary: Optional[Dict[str, Any]] # e.g., num_rows, num_columns
    input_file_last_modified: Optional[datetime]
    error: Optional[str] = None # If there was an error fetching the summary
    data_available: bool = True # Default to true, set to false on error

class SectorDataDetailResponse(BaseModel):
    """
    Response model for detailed data of a specific sector.
    Based on `get_sector_data` in service.
    """
    project_name: str
    sector_name: str
    columns: List[str]
    data_records: List[Dict[str, Any]] # Could be paginated in a real app
    data_summary: Dict[str, Any] # e.g., num_rows, year_range, electricity_mean

# Model for demand visualization requests/responses can be added if distinct from general charting.
# For now, assuming visualization parameters are part of specific API endpoints.

# Example:
# class DemandVisualizationParams(BaseModel):
#     project_name: str
#     scenario_name: str
#     sector_name: Optional[str] # Visualize specific sector or overall
#     chart_type: str = Field(default="time_series_forecast", example="time_series_forecast") # e.g., "actual_vs_forecast", "component_breakdown"
#     time_range_start: Optional[datetime]
#     time_range_end: Optional[datetime]
