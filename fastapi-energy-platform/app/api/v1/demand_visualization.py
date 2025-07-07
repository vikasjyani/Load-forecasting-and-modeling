# fastapi-energy-platform/app/api/v1/demand_visualization.py
"""
Demand Visualization API Endpoints for FastAPI.
Provides data for visualizing demand forecasts and scenarios.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path as FastAPIPath
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile # For export
from datetime import datetime

from app.services.demand_visualization_service import DemandVisualizationService, ScenarioInfo, ScenarioOutput
from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError
from app.utils.helpers import safe_filename # For export filename

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for DemandVisualizationService ---
from app.dependencies import get_demand_visualization_service as get_demand_visualization_service_dependency

# --- Pydantic Models ---
# Using models from service if they are Pydantic, or defining API-specific ones here.
# ScenarioInfo and ScenarioOutput are dataclasses in the service, FastAPI can serialize them.

class ScenarioFilters(BaseModel):
    unit: Optional[str] = Field(default="TWh", example="GWh")
    start_year: Optional[int] = Field(default=None, example=2025)
    end_year: Optional[int] = Field(default=None, example=2040)
    sectors: Optional[List[str]] = Field(default=None, example=["Residential", "Commercial"])

class ModelSelectionPayload(BaseModel):
    model_selection: Dict[str, str] = Field(..., example={"SectorA": "MLR", "SectorB": "WAM"})

class TdLossItem(BaseModel):
    year: int
    loss_percentage: float = Field(..., ge=0, le=100) # Percentage input

class TdLossesPayload(BaseModel):
    td_losses: List[TdLossItem]

class GenerateConsolidatedPayload(BaseModel):
    model_selection: Dict[str, str]
    td_losses: List[TdLossItem]
    filters: Optional[ScenarioFilters] = None # For display unit of the response mainly

class ScenarioComparisonQuery(BaseModel):
    scenario1_name: str = Field(..., alias="scenario1")
    scenario2_name: str = Field(..., alias="scenario2")
    filters: Optional[ScenarioFilters] = Depends() # Using Depends for nested query params

class ExportQuery(BaseModel):
    data_type: str = Field(default="consolidated", pattern="^(consolidated|scenario_detail)$")
    filters: Optional[ScenarioFilters] = Depends()


# --- API Endpoints ---

@router.get("/{project_name}/scenarios", response_model=List[ScenarioInfo], summary="List Available Scenarios")
async def list_scenarios_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        scenarios = await service.list_available_scenarios(project_name=project_name)
        return scenarios # FastAPI handles dataclass list to JSON
    except Exception as e:
        logger.exception(f"Error listing scenarios for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to list scenarios: {str(e)}")

@router.get("/{project_name}/scenario/{scenario_name}", response_model=ScenarioOutput, summary="Get Data for a Specific Scenario")
async def get_scenario_data_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    filters: ScenarioFilters = Depends(), # Query parameters via Pydantic model (Depends)
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        filter_dict = filters.model_dump(exclude_none=True) if filters else {}
        data = await service.get_scenario_data(project_name, scenario_name, filter_dict)
        return data # ScenarioOutput is a dataclass
    except FileNotFoundError as e: # Service raises FileNotFoundError if scenario/data missing
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting data for scenario {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scenario data: {str(e)}")

@router.get("/{project_name}/comparison", summary="Compare Two Scenarios")
async def get_comparison_data_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    params: ScenarioComparisonQuery = Depends(), # scenario1, scenario2 from query
    filters: ScenarioFilters = Depends(), # Common filters
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        filter_dict = filters.model_dump(exclude_none=True) if filters else {}
        comparison_data = await service.get_comparison_data(
            project_name, params.scenario1_name, params.scenario2_name, filter_dict
        )
        return comparison_data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error comparing scenarios for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to compare scenarios: {str(e)}")

@router.get("/{project_name}/model_selection/{scenario_name}", summary="Get Model Selection Config")
async def get_model_selection_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    config = await service.get_model_selection(project_name, scenario_name)
    if config is None or not config.get("model_selection"): # Service returns {"model_selection": {}} if not found
        raise HTTPException(status_code=404, detail="Model selection configuration not found or empty.")
    return config

@router.post("/{project_name}/model_selection/{scenario_name}", summary="Save Model Selection Config")
async def save_model_selection_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    payload: ModelSelectionPayload,
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        success = await service.save_model_selection(project_name, scenario_name, payload.model_selection)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save model selection configuration.")
        return {"message": "Model selection configuration saved successfully."}
    except Exception as e:
        logger.exception(f"Error saving model selection for {project_name}/{scenario_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving model selection: {str(e)}")


@router.get("/{project_name}/td_losses/{scenario_name}", summary="Get T&D Losses Config")
async def get_td_losses_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    config = await service.get_td_losses(project_name, scenario_name)
    if config is None or not config.get("td_losses"): # Service returns {"td_losses": []} if not found
        # Allow returning empty list if that's the stored state, but raise if file truly absent and service returns None
        # The service implementation returns `{"td_losses": []}` if file not found, so this check might be too strict
        # if an empty list is a valid "not set" state. Assuming for now that `None` means error.
         raise HTTPException(status_code=404, detail="T&D losses configuration not found or empty.")
    return config

@router.post("/{project_name}/td_losses/{scenario_name}", summary="Save T&D Losses Config")
async def save_td_losses_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    payload: TdLossesPayload,
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        success = await service.save_td_losses(project_name, scenario_name, [item.model_dump() for item in payload.td_losses])
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save T&D losses configuration.")
        return {"message": "T&D losses configuration saved successfully."}
    except Exception as e:
        logger.exception(f"Error saving T&D losses for {project_name}/{scenario_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving T&D losses: {str(e)}")


@router.post("/{project_name}/consolidated_results/{scenario_name}", summary="Generate Or Get Consolidated Results")
async def generate_or_get_consolidated_results_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    payload: Optional[GenerateConsolidatedPayload] = None, # Optional: if not provided, tries to load existing
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        # This POST endpoint is now solely for generating/regenerating consolidated results.
        # A separate GET endpoint would be needed to fetch existing pre-generated results if desired.
        if not payload: # Payload is optional, but if not provided, it's a bad request for generation.
            raise HTTPException(status_code=422, detail="Payload required to generate consolidated results.")

        result = await service.generate_consolidated_results(
            project_name,
            scenario_name,
            payload.model_selection,
            [item.model_dump() for item in payload.td_losses], # Convert TdLossItem to dict
            payload.filters.model_dump(exclude_none=True) if payload.filters else None
        )
        return result
    except ProcessingError as e: # Errors from the service during processing
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error with consolidated results for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to process consolidated results: {str(e)}")

@router.get("/{project_name}/analysis_summary/{scenario_name}", summary="Get Analysis Summary for Scenario")
async def get_analysis_summary_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    filters: ScenarioFilters = Depends(),
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        filter_dict = filters.model_dump(exclude_none=True) if filters else {}
        summary = await service.get_analysis_summary(project_name, scenario_name, filter_dict)
        return summary
    except ProcessingError as e: # e.g. model selection not done
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting analysis summary for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to get analysis summary: {str(e)}")

@router.get("/{project_name}/export/{scenario_name}", summary="Export Scenario Data")
async def export_scenario_data_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    export_params: ExportQuery = Depends(), # data_type and filters from query
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        filter_dict = export_params.filters.model_dump(exclude_none=True) if export_params.filters and export_params.filters else {}

        # Service's export_data method returns a Path object to the temporary CSV file
        temp_file_path = await service.export_data(
            project_name,
            scenario_name,
            export_params.data_type,
            filter_dict
        )

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        download_filename = f"{safe_filename(scenario_name)}_{export_params.data_type}_export_{timestamp}.csv"

        # Ensure temp_file_path is absolute, or handle relative paths correctly for FileResponse
        # If service returns an absolute path, this is fine.
        return FileResponse(
            path=str(temp_file_path),
            filename=download_filename,
            media_type='text/csv'
        )
    except FileNotFoundError as e: # Raised by service if source data for export is missing
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e: # For invalid data_type
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error exporting data for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")

@router.get("/{project_name}/validate_configurations/{scenario_name}", summary="Validate Scenario Configurations")
async def validate_scenario_configs_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    service: DemandVisualizationService = Depends(get_demand_visualization_service_dependency)
):
    try:
        validation_results = await service.validate_scenario_configurations(project_name, scenario_name)
        return validation_results
    except Exception as e:
        logger.exception(f"Error validating configurations for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to validate configurations: {str(e)}")

logger.info("Demand Visualization API router defined for FastAPI.")
print("Demand Visualization API router defined for FastAPI.")
