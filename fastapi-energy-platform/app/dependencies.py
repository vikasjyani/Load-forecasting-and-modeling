"""
Application-wide dependencies for FastAPI.
"""
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from app.config import Settings, settings as global_settings # Import the global instance
# Import services - adjust paths as necessary if services are moved/restructured
from app.services.project_service import ProjectService
from app.services.data_service import DataService
from app.services.demand_projection_service import DemandProjectionService, forecast_job_manager as global_forecast_job_manager
from app.services.demand_visualization_service import DemandVisualizationService
from app.services.loadprofile_service import LoadProfileService
from app.services.loadprofile_analysis_service import LoadProfileAnalysisService
from app.services.admin_service import AdminService


# Dependency to get the application settings
async def get_settings() -> Settings:
    """
    Dependency to get the application settings object.

    Returns:
        Settings: The application settings instance.
    """
    return global_settings

# Dependency to get the project data root path
async def get_project_data_root(settings: Annotated[Settings, Depends(get_settings)]) -> Path:
    """
    Dependency to get the configured root path for project data.

    Args:
        settings (Settings): The application settings, injected by FastAPI.

    Returns:
        Path: The absolute path to the project data root directory.
    """
    return settings.PROJECT_DATA_ROOT

# --- Service Dependencies ---
# These dependencies can be used to inject service instances into API routes.
# This makes it easier to manage service instantiation and their own dependencies.

async def get_project_service(
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> ProjectService:
    """
    Dependency to get an instance of ProjectService.

    Args:
        project_data_root (Path): The root directory for project data.

    Returns:
        ProjectService: An instance of the project service.
    """
    return ProjectService(project_data_root=project_data_root)

async def get_data_service(
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> DataService:
    """
    Dependency to get an instance of DataService.

    Args:
        project_data_root (Path): The root directory for project data.

    Returns:
        DataService: An instance of the data service.
    """
    # DataService might need more specific paths or configs in the future
    return DataService(base_data_path=project_data_root)

async def get_demand_projection_service(
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> DemandProjectionService:
    """
    Dependency to get an instance of DemandProjectionService.

    Args:
        project_data_root (Path): The root directory for project data.

    Returns:
        DemandProjectionService: An instance of the demand projection service.
    """
    # Note: The global forecast_job_manager is used by this service.
    # If the manager needed request-specific context or configuration,
    # it would also need to be managed via dependency injection.
    return DemandProjectionService(project_data_root=project_data_root)

async def get_forecast_job_manager(): # No direct dependencies for now
    """
    Dependency to get the global ForecastJobManager instance.
    """
    return global_forecast_job_manager


async def get_demand_visualization_service(
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> DemandVisualizationService:
    """
    Dependency to get an instance of DemandVisualizationService.

    Args:
        project_data_root (Path): The root directory for project data.

    Returns:
        DemandVisualizationService: An instance of the demand visualization service.
    """
    return DemandVisualizationService(project_data_root=project_data_root)

async def get_load_profile_service(
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> LoadProfileService:
    """
    Dependency to get an instance of LoadProfileService.

    Args:
        project_data_root (Path): The root directory for project data.

    Returns:
        LoadProfileService: An instance of the load profile service.
    """
    return LoadProfileService(project_data_root=project_data_root)

async def get_load_profile_analysis_service(
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> LoadProfileAnalysisService:
    """
    Dependency to get an instance of LoadProfileAnalysisService.

    Args:
        project_data_root (Path): The root directory for project data.

    Returns:
        LoadProfileAnalysisService: An instance of the load profile analysis service.
    """
    return LoadProfileAnalysisService(project_data_root=project_data_root)

async def get_admin_service(
    settings: Annotated[Settings, Depends(get_settings)],
    project_data_root: Annotated[Path, Depends(get_project_data_root)]
) -> AdminService:
    """
    Dependency to get an instance of AdminService.

    Args:
        settings (Settings): The application settings.
        project_data_root (Path): The root directory for project data.

    Returns:
        AdminService: An instance of the admin service.
    """
    return AdminService(settings=settings, project_data_root=project_data_root)

print("Dependencies defined.")
# Remove the old print statement
# print("Defining dependencies...")
