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
import asyncio # Added for asyncio.to_thread
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from app.utils.features_manager import FeatureManager
# from app.utils.memory_manager import memory_manager # Assuming not used for now or replaced
# from app.utils.performance_profiler import profiler # Assuming not used for now or replaced
from app.utils.cache_manager import cache as global_app_cache # Assuming this is the intended global cache
from app.utils.helpers import cleanup_old_files # get_file_info might be useful later

from app.config import Settings # For type hinting and accessing settings

logger = logging.getLogger(__name__)

class AdminService:
    """
    Service layer for admin operations.
    """

    def __init__(self, settings: Settings, project_data_root: Path):
        self.settings = settings
        self.project_data_root = project_data_root # For project-specific feature flags if needed by FM

        # Initialize FeatureManager
        # Assuming GLOBAL_FEATURES_CONFIG_PATH is defined in Settings, e.g., settings.APP_CONFIG_DIR / "features.json"
        # If settings.APP_CONFIG_DIR is not defined, we might need to construct path from settings.BASE_DIR
        if hasattr(settings, 'GLOBAL_FEATURES_CONFIG_PATH') and settings.GLOBAL_FEATURES_CONFIG_PATH:
            global_features_path = settings.GLOBAL_FEATURES_CONFIG_PATH
        else: # Fallback path construction
            global_features_path = settings.BASE_DIR.parent / "app_config_data" / "features.json"
            logger.warning(f"GLOBAL_FEATURES_CONFIG_PATH not set in Settings, defaulting FeatureManager to: {global_features_path}")

        self.feature_manager = FeatureManager(
            global_config_path=global_features_path,
            project_data_root=self.project_data_root # Pass project_data_root for project-specific overrides
        )
        logger.info(f"AdminService initialized. FeatureManager using global config: {global_features_path}")


    async def list_features(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive features configuration, including categories and groups.
        """
        try:
            # FeatureManager methods are synchronous (file I/O)
            features_config = await asyncio.to_thread(
                self.feature_manager.get_merged_features, project_name
            )

            if "error" in features_config: # Error from feature_manager itself
                raise Exception(features_config["error"])

            features_by_category: Dict[str, List[Dict]] = {}
            raw_features = features_config.get('features', {})
            for feature_id, config_val in raw_features.items():
                if not isinstance(config_val, dict): # Skip malformed entries
                    logger.warning(f"Skipping malformed feature config for '{feature_id}': {config_val}")
                    continue
                category = config_val.get('category', 'general')
                features_by_category.setdefault(category, []).append({
                    'id': feature_id,
                    'description': config_val.get('description', ''),
                    'enabled': config_val.get('enabled', False),
                    'category': category, # Redundant but useful for client
                    'last_modified': config_val.get('last_modified', '')
                })

            total_features = len(raw_features)
            enabled_count = sum(1 for f_cfg in raw_features.values() if isinstance(f_cfg, dict) and f_cfg.get('enabled', False))

            return {
                # 'raw_features_config': raw_features, # For debugging or full data needs
                'features_by_category': features_by_category,
                'feature_groups': features_config.get('feature_groups', {}),
                'total_features': total_features,
                'enabled_features_count': enabled_count,
                'metadata': features_config.get('metadata', {}),
                'data_source_project': project_name if project_name and features_config.get("metadata",{}).get("project_config_used") else None,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting features configuration (project: {project_name}): {e}")
            # Return a structure consistent with success but indicating error
            return {
                'features_by_category': {}, 'feature_groups': {}, 'total_features': 0, 'enabled_features_count': 0,
                'metadata': {}, 'error': f"Failed to retrieve features: {str(e)}"
            }

    async def update_feature_status(self, feature_id: str, enabled: bool, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Update a single feature's status."""
        try:
            success = await asyncio.to_thread(
                self.feature_manager.set_feature_enabled, feature_id, enabled, project_name
            )
            if success:
                # Optionally, get updated feature info to return
                updated_feature_info = await asyncio.to_thread(
                    self.feature_manager.get_feature_info, feature_id, project_name
                )
                logger.info(f"Feature '{feature_id}' (project: {project_name}) updated to enabled={enabled}")
                return {
                    'success': True,
                    'feature_id': feature_id,
                    'new_status': enabled,
                    'updated_info': updated_feature_info,
                    'message': f"Feature '{feature_id}' status updated successfully."
                }
            else:
                return {'success': False, 'error': f"Failed to update feature '{feature_id}' via FeatureManager."}
        except Exception as e:
            logger.exception(f"Error updating feature '{feature_id}' (project: {project_name}): {e}")
            return {'success': False, 'error': str(e)}

    async def bulk_update_features_status(self, updates: Dict[str, bool], project_name: Optional[str] = None) -> Dict[str, Any]:
        """Bulk update statuses of multiple features."""
        successful_updates = []
        failed_updates = []

        for feature_id, enabled_status in updates.items():
            try:
                # Each call to set_feature_enabled involves file I/O, so run in thread.
                success = await asyncio.to_thread(
                    self.feature_manager.set_feature_enabled, feature_id, enabled_status, project_name
                )
                if success:
                    successful_updates.append({"feature_id": feature_id, "set_to": enabled_status})
                else:
                    failed_updates.append({"feature_id": feature_id, "error": "Update failed in FeatureManager"})
            except Exception as e:
                logger.warning(f"Failed to update feature '{feature_id}' during bulk operation: {e}")
                failed_updates.append({"feature_id": feature_id, "error": str(e)})

        # After all updates, clear relevant cache once.
        await asyncio.to_thread(self.feature_manager.clear_cache, project_name)

        return {
            "message": f"Bulk update process completed. Successful: {len(successful_updates)}, Failed: {len(failed_updates)}.",
            "successful_updates": successful_updates,
            "failed_updates": failed_updates
        }


    async def perform_system_cleanup(self, cleanup_type: str = 'logs', max_age_days: int = 30) -> Dict[str, Any]:
        """Perform system cleanup tasks."""
        cleanup_summary: Dict[str, Any] = {}
        total_files_cleaned_count = 0

        try:
            # Cleanup Logs
            if cleanup_type in ['all', 'logs'] and self.settings.LOGS_DIR:
                logs_path = Path(self.settings.LOGS_DIR) # Ensure LOGS_DIR is Path or str
                if await asyncio.to_thread(logs_path.exists):
                    logs_result = await cleanup_old_files(logs_path, max_age_days=max_age_days, file_patterns=['*.log', '*.log.*'])
                    cleanup_summary['logs'] = logs_result
                    total_files_cleaned_count += len(logs_result.get('cleaned_files', []))
                else:
                    cleanup_summary['logs'] = {'status': 'skipped', 'message': f'Logs directory not found: {logs_path}'}

            # Cleanup Temporary Uploads
            if cleanup_type in ['all', 'temp'] and self.settings.TEMP_UPLOAD_DIR:
                temp_path = Path(self.settings.TEMP_UPLOAD_DIR) # Ensure TEMP_UPLOAD_DIR is Path or str
                if await asyncio.to_thread(temp_path.exists):
                    # Temp files usually have shorter retention, e.g., 7 days
                    temp_result = await cleanup_old_files(temp_path, max_age_days=min(max_age_days, 7), file_patterns=['*.tmp', '*.temp', 'upload_*'])
                    cleanup_summary['temporary_uploads'] = temp_result
                    total_files_cleaned_count += len(temp_result.get('cleaned_files', []))
                else:
                    cleanup_summary['temporary_uploads'] = {'status': 'skipped', 'message': f'Temp upload directory not found: {temp_path}'}

            # Clear Caches
            if cleanup_type in ['all', 'cache']:
                await asyncio.to_thread(self.feature_manager.clear_cache) # Clear feature manager's internal cache
                if hasattr(global_app_cache, 'clear_all'): # If a global cache manager with clear_all exists
                    await asyncio.to_thread(global_app_cache.clear_all)
                elif hasattr(global_app_cache, 'clear'):
                     await asyncio.to_thread(global_app_cache.clear)
                cleanup_summary['application_caches'] = {'status': 'success', 'message': 'Application caches cleared (attempted).'}

            return {
                'overall_status': 'success',
                'details': cleanup_summary,
                'total_files_cleaned': total_files_cleaned_count,
                'cleanup_type_requested': cleanup_type,
                'max_age_days_for_logs_temp': max_age_days,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error during system cleanup (type: {cleanup_type}): {e}")
            return {'overall_status': 'error', 'details': cleanup_summary, 'error': str(e)}


    async def get_comprehensive_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        import platform # platform is lightweight, can be imported here
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

            disk_info_path = Path(self.settings.PROJECT_DATA_ROOT) # Check disk of project data root
            if not await asyncio.to_thread(disk_info_path.exists): disk_info_path = Path("/")

            disk_usage = await asyncio.to_thread(psutil.disk_usage, str(disk_info_path))
            disk_info = {
                'path_checked': str(disk_info_path),
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'percent_used': disk_usage.percent
            }

            enabled_features = await asyncio.to_thread(self.feature_manager.get_enabled_features)
            app_info = {
                'app_name': self.settings.APP_NAME,
                'version': self.settings.APP_VERSION,
                'environment': self.settings.ENVIRONMENT,
                'debug_mode': self.settings.DEBUG,
                'project_data_root': str(self.settings.PROJECT_DATA_ROOT),
                'global_features_config_path': str(self.feature_manager.global_config_path),
                'enabled_features_count': len(enabled_features)
            }

            return {
                'platform': system_info_platform,
                'resources': resource_info,
                'disk': disk_info,
                'application': app_info,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting comprehensive system info: {e}")
            return {'error': f"Failed to retrieve system info: {str(e)}"}


    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get real-time system health metrics."""
        try:
            cpu_percent = await asyncio.to_thread(psutil.cpu_percent, interval=0.1)
            memory = await asyncio.to_thread(psutil.virtual_memory)
            disk_usage = await asyncio.to_thread(psutil.disk_usage, str(self.settings.PROJECT_DATA_ROOT)) # Check project data disk

            # Basic app health check (can be expanded)
            app_component_health = {
                "feature_manager_loadable": self.feature_manager is not None and self.feature_manager.global_config_path.exists(),
                # Add other component checks, e.g., database connectivity if used
            }
            app_overall_healthy = all(app_component_health.values())

            health_status_string = self._determine_health_status_string(cpu_percent, memory.percent, app_overall_healthy)

            return {
                'overall_health': health_status_string,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent_project_data': disk_usage.percent,
                'disk_free_gb_project_data': round(disk_usage.free / (1024**3), 2),
                'application_components_health': app_component_health,
                'active_processes_count': len(await asyncio.to_thread(psutil.pids)),
                'system_uptime_seconds': round(time.time() - await asyncio.to_thread(psutil.boot_time), 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting system health: {e}")
            return {'error': str(e), 'overall_health': 'unknown'}


    def _determine_health_status_string(self, cpu: float, memory: float, app_is_healthy: bool) -> str:
        """Determine overall system health status string."""
        if not app_is_healthy: return 'degraded (app component issue)'
        if cpu > 95 or memory > 95: return 'critical'
        if cpu > 80 or memory > 85: return 'warning'
        if cpu > 60 or memory > 70: return 'degraded'
        return 'healthy'

logger.info("AdminService defined for FastAPI.")
