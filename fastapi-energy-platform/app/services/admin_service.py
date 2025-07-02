# fastapi-energy-platform/app/services/admin_service.py
"""
Admin Service Layer for FastAPI
Handles system administration, feature management, and monitoring.
"""
import os
import json
import time
import psutil
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Assuming these utilities are now in fastapi-energy-platform/app/utils/
# Adjust imports as necessary based on their final structure and content.
from app.utils.features_manager import FeatureManager # Needs adaptation for FastAPI context
from app.utils.memory_manager import memory_manager # May need adaptation
from app.utils.performance_profiler import profiler # May need adaptation
from app.utils.cache_manager import cache # Assuming cache is an instance of a cache manager
from app.utils.helpers import cleanup_old_files, get_file_info

# FastAPI specific imports (if needed for dependency injection, settings)
# from fastapi import Depends
# from ..config import Settings # Example: Pydantic settings

logger = logging.getLogger(__name__)

class AdminService:
    """
    Service layer for admin operations.
    In FastAPI, dependencies like FeatureManager or settings would typically be injected.
    """

    def __init__(
        self,
        # feature_manager: FeatureManager = Depends(get_feature_manager_dependency), # Example
        # settings: Settings = Depends(get_settings_dependency) # Example
    ):
        # For now, let's assume FeatureManager might be initialized here or passed.
        # This part needs careful refactoring based on how FeatureManager is designed for FastAPI.
        # self.feature_manager = feature_manager
        # self.settings = settings
        self.feature_manager: Optional[FeatureManager] = None # Placeholder
        # A proper FeatureManager for FastAPI wouldn't rely on Flask's `current_app`.
        # It would likely load config from files or a database, perhaps via `config.py`.
        # self._init_feature_manager_placeholder()
        pass


    # Placeholder for feature manager initialization if not using DI
    # def _init_feature_manager_placeholder(self):
    #     # This is a simplified init. In reality, FeatureManager needs to be
    #     # independent of Flask's app context.
    #     try:
    #         # Path to a global features.json or project-specific one
    #         # config_path = Path(self.settings.FEATURES_CONFIG_PATH)
    #         # self.feature_manager = FeatureManager(config_path=config_path)
    #         logger.info("FeatureManager (placeholder) initialized in AdminService.")
    #     except Exception as e:
    #         logger.error(f"Failed to initialize placeholder FeatureManager: {e}")
    #         self.feature_manager = None

    async def get_features_configuration(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive features configuration.
        `project_name` would be used by FeatureManager to load project-specific overrides.
        """
        # This method needs to be fully re-implemented once FeatureManager is adapted.
        # The original relied on Flask's `current_app` and a specific FeatureManager structure.
        if not self.feature_manager: # Or if FeatureManager DI fails
            return {'features': {}, 'feature_groups': {}, 'error': 'Feature manager not available or not configured for FastAPI.'}

        try:
            # features_config = self.feature_manager.get_merged_features(project_name) # Adapted call
            # This is a mock, replace with actual FeatureManager logic
            features_config = {"features": {"example_feature": {"enabled": True, "description": "An example feature", "category": "general"}}, "feature_groups": {}, "metadata": {}}

            features_by_category: Dict[str, List[Dict]] = {}
            for feature_id, config_val in features_config.get('features', {}).items():
                category = config_val.get('category', 'general')
                features_by_category.setdefault(category, []).append({
                    'id': feature_id,
                    'description': config_val.get('description', ''),
                    'enabled': config_val.get('enabled', False),
                    'category': category,
                    'last_modified': config_val.get('last_modified', '')
                })

            total_features = len(features_config.get('features', {}))
            enabled_count = sum(1 for f_cfg in features_config.get('features', {}).values() if f_cfg.get('enabled', False))

            return {
                'features': features_config.get('features', {}),
                'features_by_category': features_by_category,
                'feature_groups': features_config.get('feature_groups', {}),
                'total_features': total_features,
                'enabled_count': enabled_count,
                'metadata': features_config.get('metadata', {}),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting features configuration: {e}")
            return {'error': str(e), 'features': {}, 'feature_groups': {}}

    async def update_feature_status(self, feature_id: str, enabled: bool, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Update feature status."""
        if not self.feature_manager:
            return {'success': False, 'error': 'Feature manager not available.'}
        try:
            # success = await self.feature_manager.set_feature_enabled(feature_id, enabled, project_name) # Adapted
            # Mocking success
            success = True
            if success:
                # updated_feature = await self.feature_manager.get_feature_info(feature_id, project_name) # Adapted
                updated_feature = {"id": feature_id, "enabled": enabled, "description": "Mocked feature"}
                logger.info(f"Feature {feature_id} (project: {project_name}) updated: enabled={enabled}")
                return {
                    'success': True,
                    'feature_id': feature_id,
                    'enabled': enabled,
                    'feature_info': updated_feature,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'success': False, 'error': 'Feature update operation failed in FeatureManager.'}
        except Exception as e:
            logger.exception(f"Error updating feature {feature_id}: {e}")
            return {'success': False, 'error': str(e)}

    # bulk_update_features would be similar, iterating and calling update_feature_status.

    async def perform_system_cleanup(self, cleanup_type: str = 'logs', max_age_days: int = 30) -> Dict[str, Any]:
        """Perform system cleanup. Paths should come from config (e.g., self.settings)."""
        # This needs access to configured paths (LOGS_FOLDER, UPLOAD_FOLDER)
        # Example: logs_folder = self.settings.LOGS_DIR
        # Example: upload_folder = self.settings.UPLOADS_DIR
        logs_folder = Path("logs") # Placeholder - use configured path from self.settings (e.g., self.settings.LOGS_DIR)
        upload_folder = Path("uploads_temp") # Placeholder - use configured path (e.g., self.settings.TEMP_UPLOAD_DIR)
        import asyncio # Required for asyncio.to_thread

        cleanup_results: Dict[str, Any] = {}
        total_cleaned = 0
        try:
            logs_folder_exists = await asyncio.to_thread(logs_folder.exists)
            if cleanup_type in ['all', 'logs'] and logs_folder_exists:
                logs_result = await cleanup_old_files(logs_folder, max_age_days=max_age_days, file_patterns=['.log'])
                cleanup_results['logs'] = logs_result
                total_cleaned += len(logs_result.get('cleaned_files', []))
            elif cleanup_type in ['all', 'logs']:
                 cleanup_results['logs'] = {'success': True, 'message': f'Logs directory {logs_folder} does not exist. Skipping cleanup.'}


            upload_folder_exists = await asyncio.to_thread(upload_folder.exists)
            if cleanup_type in ['all', 'temp'] and upload_folder_exists:
                temp_result = await cleanup_old_files(upload_folder, max_age_days=7, file_patterns=['.tmp', '.temp'])
                cleanup_results['temp'] = temp_result
                total_cleaned += len(temp_result.get('cleaned_files', []))
            elif cleanup_type in ['all', 'temp']:
                cleanup_results['temp'] = {'success': True, 'message': f'Temp upload directory {upload_folder} does not exist. Skipping cleanup.'}


            if cleanup_type in ['all', 'cache']:
                # cache.clear_all() # Example if cache object has a clear_all method
                if self.feature_manager and hasattr(self.feature_manager, 'clear_cache'):
                     self.feature_manager.clear_cache()
                if hasattr(cache, 'clear'): # from app.utils.cache_manager import cache
                    cache.clear() # Or specific cache regions
                cleanup_results['cache'] = {'success': True, 'message': 'Caches cleared (attempted).'}

            if cleanup_type in ['all', 'memory'] and hasattr(memory_manager, 'force_cleanup'):
                memory_manager.force_cleanup()
                cleanup_results['memory'] = {'success': True, 'message': 'Memory cleanup performed (attempted).'}

            return {
                'cleanup_results': cleanup_results,
                'total_files_cleaned': total_cleaned,
                'cleanup_type': cleanup_type,
                'max_age_days': max_age_days,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error during system cleanup: {e}")
            return {'cleanup_results': {}, 'total_files_cleaned': 0, 'error': str(e)}


    async def get_comprehensive_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        # This method can largely remain the same, assuming psutil is available.
        # Application info part needs to be FastAPI specific.
        import platform
        try:
            system_info_platform = {
                'system': platform.system(), 'release': platform.release(), 'machine': platform.machine(),
                'processor': platform.processor(), 'python_version': platform.python_version()
            }
            resource_info = {
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'cpu_count_physical': psutil.cpu_count(logical=False),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
                'memory_percent_used': psutil.virtual_memory().percent
            }
            # Disk info for root path or a configured path
            # disk_info_path = self.settings.DATA_DIR if hasattr(self, 'settings') else Path("/")
            disk_info_path = Path("/") # Placeholder
            disk_usage = psutil.disk_usage(str(disk_info_path))
            disk_info = {
                'path': str(disk_info_path),
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'percent_used': disk_usage.percent
            }
            app_info = { # FastAPI specific app info
                'version': "1.0.0", # from config or version file
                # 'environment': self.settings.ENVIRONMENT if hasattr(self, 'settings') else os.getenv("ENVIRONMENT", "dev"),
                'features_enabled': len(await self.get_enabled_features_list()) if self.feature_manager else "N/A"
            }

            # performance_metrics = profiler.get_stats() if profiler else {}
            # memory_usage_stats = memory_manager.get_memory_stats() if memory_manager else {}
            # cache_stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
            # project_stats = await self._get_project_statistics_async() # Example if it becomes async

            return {
                'platform': system_info_platform,
                'resources': resource_info,
                'disk': disk_info,
                'application': app_info,
                # 'performance_metrics': performance_metrics,
                # 'memory_usage': memory_usage_stats,
                # 'cache_stats': cache_stats,
                # 'project_stats': project_stats,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting comprehensive system info: {e}")
            return {'error': str(e)}

    async def get_enabled_features_list(self) -> list:
        """Helper to get list of enabled features, if FeatureManager is used."""
        if not self.feature_manager or not hasattr(self.feature_manager, 'get_enabled_features'):
            return []
        # Assuming get_enabled_features might be async or sync
        # features = await self.feature_manager.get_enabled_features() # if async
        # features = self.feature_manager.get_enabled_features() # if sync
        return ["mock_feature1", "mock_feature2"] # Placeholder


    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get real-time system health metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1) # Non-blocking
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage('/') # Or configured path

            # app_health = await self._check_application_health_async() # If it becomes async
            app_health = {"healthy": True, "components": {"feature_manager": True}} # Placeholder

            health_status = self._determine_health_status(cpu_percent, memory.percent, app_health)

            return {
                'overall_health': health_status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk_usage.percent,
                'disk_free_gb': round(disk_usage.free / (1024**3), 2),
                'application_health': app_health,
                'active_processes': len(psutil.pids()),
                'uptime_seconds': round(time.time() - psutil.boot_time(), 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting system health: {e}")
            return {'error': str(e), 'overall_health': 'unknown'}


    def _determine_health_status(self, cpu_percent: float, memory_percent: float, app_health: Dict) -> str:
        """Determine overall system health status (remains largely the same logic)."""
        try:
            if cpu_percent > 95 or memory_percent > 95: return 'critical'
            if cpu_percent > 80 or memory_percent > 85: return 'warning'
            if not app_health.get('healthy', True): return 'degraded' # Check app specific health
            if cpu_percent > 60 or memory_percent > 70: return 'degraded'
            return 'healthy'
        except Exception:
            return 'unknown'

    # Other helper methods like _get_project_statistics might need to be async
    # if they involve I/O operations that should be non-blocking in FastAPI.
    # For example, walking directories:
    # async def _get_project_statistics_async(self) -> Dict[str, Any]:
    #     # project_root = self.settings.PROJECTS_DIR
    #     # ... use anyio.Path for async file operations or run_in_threadpool
    #     return {"total_projects": 0, "projects": []} # Placeholder

print("Defining admin service for FastAPI... (merged and adapted from old_admin_service.py)")
