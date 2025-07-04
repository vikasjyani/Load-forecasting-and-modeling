from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
from pathlib import Path
import os

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and/or .env file.
    """
    APP_NAME: str = Field("FastAPI Energy Platform", description="The name of the application.")
    APP_VERSION: str = Field("0.1.0", description="The version of the application.")
    APP_DESCRIPTION: Optional[str] = Field("A FastAPI platform for energy analysis and forecasting.", description="A brief description of the application.")
    API_V1_PREFIX: str = Field("/api/v1", description="The prefix for version 1 of the API.")

    # Logging configuration
    LOG_LEVEL: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).")

    # File storage paths
    # Default to a 'data' directory in the repository root if not set via environment variable.
    # For production, this should be an absolute path set via an environment variable.
    PROJECT_DATA_ROOT_DEFAULT: Path = Path(__file__).resolve().parent.parent.parent / "data" / "projects"
    PROJECT_DATA_ROOT: Path = Field(
        default_factory=lambda: Settings.PROJECT_DATA_ROOT_DEFAULT,
        description="The root directory for storing all project-related data and files. "
                    "It's highly recommended to set this via an environment variable for production deployments."
    )

    # CORS (Cross-Origin Resource Sharing)
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost", "http://localhost:3000", "http://localhost:5173"], description="List of allowed origins for CORS.")

    # PyPSA Specific Settings
    PYPSA_NETWORK_CACHE_SIZE: int = Field(default=3, ge=1, le=10, description="Maximum number of PyPSA networks to keep in in-memory cache.")
    GLOBAL_FEATURES_CONFIG_PATH: Path = Field(
        default_factory=lambda: Path(Settings().BASE_DIR.parent / "app_config_data" / "features.json"), # Access BASE_DIR via self or Settings()
        description="Path to the global features.json configuration file."
    )
    LOGS_DIR: Path = Field(
        default_factory=lambda: Path(Settings().PROJECT_DATA_ROOT.parent / "app_logs"), # Example: one level above project_data_root
        description="Directory to store application logs."
    )
    TEMP_UPLOAD_DIR: Path = Field(
        default_factory=lambda: Path(Settings().PROJECT_DATA_ROOT.parent / "temp_uploads"),
        description="Directory for temporary file uploads."
    )


    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env file if it exists
        env_file_encoding='utf-8',
        extra='ignore',  # Ignore extra fields from .env or environment
        case_sensitive=False # Environment variable names are case-insensitive by default on some systems
    )

    def __init__(self, **values: Any):
        super().__init__(**values)
        # Ensure project data root directory exists after initialization
        # This is a side effect, consider if it's best here or in app startup.
        # For now, it's convenient for development.
        if not self.PROJECT_DATA_ROOT.exists():
            try:
                self.PROJECT_DATA_ROOT.mkdir(parents=True, exist_ok=True)
                print(f"Created project data root directory: {self.PROJECT_DATA_ROOT}")
            except Exception as e:
                print(f"Warning: Could not create project data root directory {self.PROJECT_DATA_ROOT}: {e}")
        elif not os.access(str(self.PROJECT_DATA_ROOT), os.W_OK):
             print(f"Warning: Project data root directory {self.PROJECT_DATA_ROOT} is not writable.")


# Instantiate settings
# This instance will be imported by other modules.
settings = Settings()

# For debugging or verification during startup:
# print(f"Loading configuration for app: {settings.APP_NAME} v{settings.APP_VERSION}")
# print(f"Project data root: {settings.PROJECT_DATA_ROOT}")
# print(f"Log level: {settings.LOG_LEVEL}")

# Ensure necessary imports are available if this file is run directly (though it shouldn't be)
from typing import Any # Add this if not already present from pydantic or other imports
from pathlib import Path # Add this if not already present

# A check to ensure PROJECT_DATA_ROOT is correctly resolved, especially if default is used.
if settings.PROJECT_DATA_ROOT == Settings.PROJECT_DATA_ROOT_DEFAULT:
    print(f"Using default project data root: {settings.PROJECT_DATA_ROOT}")
    if not settings.PROJECT_DATA_ROOT.is_absolute():
        print(f"Warning: Default project data root '{settings.PROJECT_DATA_ROOT}' is not an absolute path. "
              "This might lead to unexpected behavior depending on the working directory. "
              "Consider setting PROJECT_DATA_ROOT environment variable to an absolute path.")

print("Configuration loaded successfully.")
# Remove the initial print statement from the old file
# print("Loading configuration...")
