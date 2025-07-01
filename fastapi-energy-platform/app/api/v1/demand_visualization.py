# fastapi-energy-platform/app/api/v1/demand_visualization.py
"""
Demand Visualization API Endpoints for FastAPI.
Provides data for visualizing demand forecasts and scenarios.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path as FastAPIPath
from pydantic import BaseModel, Field # For request/response models
from pathlib import Path # For project_path type hint

# Assuming DemandVisualizationService is adapted and available for DI.
try:
    from app.services.demand_visualization_service import DemandVisualizationService, ScenarioInfo, ScenarioOutput
except ImportError:
    logging.warning("DemandVisualizationService not found, using placeholder for demand visualization API.")
    # Simplified placeholders
    class ScenarioInfo(BaseModel): name: str; sectors_count: int; year_range: Dict[str,int]; has_data: bool; file_count: int = 0; last_modified_iso: Optional[str] = None
    class ScenarioOutput(BaseModel): scenario_name: str; sectors_data: Dict; unit: str = "TWh"
    class DemandVisualizationService:
        def __init__(self, project_data_root: Path): self.project_data_root = project_data_root
        async def list_available_scenarios(self, project_name: str) -> List[ScenarioInfo]: return [ScenarioInfo(name="mock_scenario", sectors_count=1, year_range={"min":2020,"max":2030}, has_data=True)]
        async def get_scenario_data(self, project_name: str, scenario_name: str, filters: Optional[Dict] = None) -> ScenarioOutput:
            if scenario_name == "mock_scenario": return ScenarioOutput(scenario_name=scenario_name, sectors_data={"mock_sector": {}})
            raise FileNotFoundError("Scenario not found")
        async def get_comparison_data(self, project_name: str, scenario_name1: str, scenario_name2: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
            s1 = await self.get_scenario_data(project_name, scenario_name1, filters)
            s2 = await self.get_scenario_data(project_name, scenario_name2, filters)
            return {"scenario1_data": s1, "scenario2_data": s2, "common_filters": filters or {}}
        async def save_ui_configuration(self, project_name: str, scenario_name: str, config_type: str, config_data: Dict) -> bool: return True
        async def load_ui_configuration(self, project_name: str, scenario_name: str, config_type: str) -> Optional[Dict]: return {"mock_config_type": config_type}
        async def generate_consolidated_results(self, project_name: str, scenario_name: str, model_selection: Dict[str, str], td_losses_config: List[Dict], filters: Optional[Dict] = None) -> Dict[str, Any]: return {"status": "mock_consolidated"}
        # async def export_data(...) -> Path: # Service would return path to temp file for FileResponse
        #     temp_file = Path(tempfile.mkstemp(suffix=".csv")[1])
        #     temp_file.write_text("mock,csv,data")
        #     return temp_file


from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for DemandVisualizationService ---
async def get_visualization_service(request: Request):
    # project_data_root = Path(request.app.state.settings.PROJECT_DATA_ROOT) # Example from global settings
    project_data_root = Path("user_projects_data") # Placeholder
    return DemandVisualizationService(project_data_root=project_data_root)

# --- Pydantic Models ---
class ScenarioFilters(BaseModel):
    unit: Optional[str] = Field(default="TWh", example="GWh")
    start_year: Optional[int] = Field(default=None, example=2025)
    end_year: Optional[int] = Field(default=None, example=2040)
    sectors: Optional[List[str]] = Field(default=None, example=["Residential", "Commercial"])

class ModelSelectionPayload(BaseModel):
    model_selection: Dict[str, str] = Field(..., example={"SectorA": "MLR", "SectorB": "WAM"})

class TdLossItem(BaseModel):
    year: int
    loss_percentage: float = Field(..., ge=0, le=100)

class TdLossesPayload(BaseModel):
    td_losses: List[TdLossItem]

class ConsolidatedPayload(BaseModel):
    model_selection: Dict[str, str]
    td_losses: List[TdLossItem]
    filters: Optional[ScenarioFilters] = None


# --- API Endpoints ---
# Note: The main HTML rendering route is omitted.

@router.get("/{project_name}/scenarios", response_model=List[ScenarioInfo], summary="List Available Scenarios for a Project")
async def api_get_scenarios(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: DemandVisualizationService = Depends(get_visualization_service)
):
    try:
        scenarios = await service.list_available_scenarios(project_name=project_name)
        return scenarios
    except Exception as e:
        logger.exception(f"Error getting scenarios for project {project_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/scenario/{scenario_name}", response_model=ScenarioOutput, summary="Get Data for a Specific Scenario")
async def api_get_scenario_data(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    filters: ScenarioFilters = Depends(), # Query parameters via Pydantic model
    service: DemandVisualizationService = Depends(get_visualization_service)
):
    try:
        # Pydantic model `filters` will have None for fields not provided in query
        filter_dict = filters.model_dump(exclude_none=True)
        data = await service.get_scenario_data(project_name, scenario_name, filter_dict)
        return data
    except FileNotFoundError as e:
        raise ResourceNotFoundError(resource_type="Scenario", resource_id=scenario_name, message=str(e))
    except Exception as e:
        logger.exception(f"Error getting data for scenario {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/comparison", summary="Compare Two Scenarios")
async def api_get_comparison_data(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario1: str = Query(..., description="Name of the first scenario for comparison"),
    scenario2: str = Query(..., description="Name of the second scenario for comparison"),
    filters: ScenarioFilters = Depends(),
    service: DemandVisualizationService = Depends(get_visualization_service)
):
    try:
        filter_dict = filters.model_dump(exclude_none=True)
        comparison_data = await service.get_comparison_data(project_name, scenario1, scenario2, filter_dict)
        return comparison_data
    except FileNotFoundError as e: # If one of the scenarios is not found
        raise ResourceNotFoundError(resource_type="Scenario", message=str(e))
    except Exception as e:
        logger.exception(f"Error comparing scenarios for project {project_name}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_name}/ui_config/{scenario_name}/{config_type}", summary="Get UI Configuration")
async def api_get_ui_config(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    config_type: str = FastAPIPath(..., description="Type of config (e.g., 'model_selection', 'td_losses')"),
    service: DemandVisualizationService = Depends(get_visualization_service)
):
    try:
        config = await service.load_ui_configuration(project_name, scenario_name, config_type)
        if config is None:
            raise ResourceNotFoundError(resource_type=f"{config_type} configuration for scenario", resource_id=scenario_name)
        return {"config_type": config_type, "configuration": config}
    except ResourceNotFoundError as e:
        raise e
    except Exception as e:
        logger.exception(f"Error getting UI config {config_type} for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{project_name}/ui_config/{scenario_name}/{config_type}", summary="Save UI Configuration")
async def api_save_ui_config(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    config_type: str = FastAPIPath(..., description="Type of config (e.g., 'model_selection', 'td_losses')"),
    config_data: Dict[str, Any] = Body(...), # Generic dict for now, can be specific Pydantic models
    service: DemandVisualizationService = Depends(get_visualization_service)
):
    # Add specific validation for config_data based on config_type if needed
    # e.g., if config_type == "model_selection", expect ModelSelectionPayload
    try:
        success = await service.save_ui_configuration(project_name, scenario_name, config_type, config_data)
        if not success:
            raise ProcessingError(message=f"Failed to save {config_type} configuration.")
        return {"message": f"{config_type} configuration saved successfully for scenario '{scenario_name}'."}
    except Exception as e:
        logger.exception(f"Error saving UI config {config_type} for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/consolidated/{scenario_name}", summary="Generate Consolidated Results")
async def api_generate_consolidated_results(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="The name of the scenario"),
    payload: ConsolidatedPayload,
    service: DemandVisualizationService = Depends(get_visualization_service)
):
    try:
        result = await service.generate_consolidated_results(
            project_name, scenario_name, payload.model_selection,
            [item.model_dump() for item in payload.td_losses], # Convert Pydantic items to dicts
            payload.filters.model_dump(exclude_none=True) if payload.filters else None
        )
        if "error" in result: # Check if service method returned an error structure
            raise ProcessingError(message=result["error"])
        return result
    except Exception as e:
        logger.exception(f"Error generating consolidated results for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=str(e))

# Omitted: /api/analysis, /api/export, /api/validate from Flask blueprint.
# These would require more complex Pydantic models for request/response and potentially
# FileResponse for export, or significant adaptation of the service methods.

logger.info("Demand Visualization API router defined for FastAPI.")
print("Demand Visualization API router defined for FastAPI.")
