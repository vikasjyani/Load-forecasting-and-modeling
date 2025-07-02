"""
Pydantic models for core functionalities and shared concepts.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ScenarioBase(BaseModel):
    """
    Base model for a scenario.
    A scenario represents a specific set of assumptions or inputs for an analysis.
    """
    name: str = Field(..., min_length=3, max_length=100, example="High Growth 2030")
    description: Optional[str] = Field(None, max_length=500, example="Scenario assuming high economic growth and rapid adoption of EVs.")
    tags: Optional[List[str]] = Field(None, example=["forecast", "ev_impact"])

class ScenarioCreate(ScenarioBase):
    """
    Model for creating a new scenario.
    """
    # project_id: str = Field(..., example="project_alpha") # If scenarios are tied to projects at this level
    parameters: Dict[str, Any] = Field(default_factory=dict, example={"inflation_rate": 0.03, "ev_adoption_rate": 0.15})

class ScenarioResponse(ScenarioBase):
    """
    Model for returning scenario information.
    """
    scenario_id: str = Field(..., example="scn_67f9a8s7df9")
    project_id: Optional[str] = Field(None, example="project_alpha") # If linked
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified_at: datetime = Field(default_factory=datetime.now)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True # If you were to use this with an ORM

class AnalysisParameters(BaseModel):
    """
    Generic model for analysis parameters that might be shared or reused.
    """
    time_horizon_start: Optional[datetime] = Field(None, example=datetime(2024, 1, 1))
    time_horizon_end: Optional[datetime] = Field(None, example=datetime(2030, 12, 31))
    discount_rate: Optional[float] = Field(None, ge=0, le=1, example=0.05)
    additional_params: Dict[str, Any] = Field(default_factory=dict)

class TimeSeriesDataPoint(BaseModel):
    """
    Represents a single data point in a time series.
    """
    timestamp: datetime = Field(..., example="2024-01-01T10:00:00Z")
    value: float = Field(..., example=105.7)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the data point")

class TimeSeriesDataSet(BaseModel):
    """
    Represents a set of time series data, possibly for multiple series.
    """
    dataset_id: str = Field(..., example="temperature_forecast_hourly")
    series_label: Optional[str] = Field(None, example="Average Temperature")
    unit: Optional[str] = Field(None, example="Celsius")
    data_points: List[TimeSeriesDataPoint]
    summary_stats: Optional[Dict[str, float]] = Field(None, example={"mean": 15.5, "max": 22.0, "min": 8.0})
    generated_at: datetime = Field(default_factory=datetime.now)
    source: Optional[str] = Field(None, example="WeatherModel_v2")

class FileReference(BaseModel):
    """
    Represents a reference to a file, often used in responses.
    """
    filename: str = Field(..., example="results_summary.csv")
    url: Optional[str] = Field(None, example="/files/project_alpha/results/results_summary.csv") # If served
    file_type: Optional[str] = Field(None, example="text/csv")
    size_bytes: Optional[int] = Field(None, example=20480)
    description: Optional[str] = Field(None, example="Summary of key result metrics.")
    last_modified: Optional[datetime] = None
