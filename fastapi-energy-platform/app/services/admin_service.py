# fastapi-energy-platform/app/services/admin_service.py
import asyncio
import datetime
import json
import logging
import os
import platform
import shutil
import psutil # type: ignore
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union # Added Union

from app.config import settings # Assuming settings.PROJECT_DATA_ROOT and settings.LOG_DIR
# from app.models.admin import FeatureConfig # Import from API or define locally if needed for service logic

logger = logging.getLogger(__name__)

# Define paths (these could also come from settings)
GLOBAL_FEATURES_CONFIG_PATH = Path(settings.APP_ROOT) / "data" / "admin" / "features_config.json"
PROJECT_ADMIN_SETTINGS_DIR_NAME = "admin_settings"
PROJECT_FEATURES_FILENAME = "project_features.json"
LOG_DIR_PATH = Path(settings.LOG_DIR if hasattr(settings, 'LOG_DIR') and settings.LOG_DIR else settings.APP_ROOT.parent / "logs")

# Helper function for async file I/O
async def read_json_async(file_path: Path) -> Optional[Dict[str, Any]]:
    if not await asyncio.to_thread(file_path.exists):
        return None
    try:
        # Use standard open with asyncio.to_thread for reading file content
        def _read_file():
            with open(file_path, 'r') as f_sync:
                return f_sync.read()
        content = await asyncio.to_thread(_read_file)
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error reading JSON from {file_path}: {e}")
        return None

async def write_json_async(file_path: Path, data: Dict[str, Any]) -> bool:
    try:
        await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
        # Use standard open with asyncio.to_thread for writing file content
        def _write_file():
            with open(file_path, 'w') as f_sync:
                json.dump(data, f_sync, indent=2)
        await asyncio.to_thread(_write_file)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON to {file_path}: {e}")
        return False

class FeaturesManager:
    def __init__(self, global_config_path: Path, project_data_root: Path):
        self.global_config_path = global_config_path
        self.project_data_root = project_data_root
        self.global_config: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock() # Lock for managing global_config access/modification

    async def load_global_config(self, force_reload: bool = False) -> Dict[str, Any]:
        async with self._lock:
            if self.global_config is None or force_reload:
                config = await read_json_async(self.global_config_path)
                if config is None:
                    logger.error(f"Global features config not found or failed to load from {self.global_config_path}")
                    # Return a default empty structure to prevent downstream errors
                    return {"metadata": {}, "feature_categories": {}, "feature_definitions": {}}
                self.global_config = config
            return json.loads(json.dumps(self.global_config)) # Return a deep copy

    def _get_project_features_path(self, project_name: str) -> Path:
        return self.project_data_root / project_name / PROJECT_ADMIN_SETTINGS_DIR_NAME / PROJECT_FEATURES_FILENAME

    async def get_project_config(self, project_name: str) -> Optional[Dict[str, Any]]:
        project_features_path = self._get_project_features_path(project_name)
        return await read_json_async(project_features_path)

    async def get_effective_features(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        effective_config = await self.load_global_config() # Gets a deep copy

        if project_name:
            project_config = await self.get_project_config(project_name)
            if project_config and "feature_overrides" in project_config:
                for feature_id, override in project_config["feature_overrides"].items():
                    if feature_id in effective_config.get("feature_definitions", {}):
                        if "enabled" in override:
                             effective_config["feature_definitions"][feature_id]["enabled"] = override["enabled"]
                        if "project_specific_description" in override: # Example of another overridable field
                            effective_config["feature_definitions"][feature_id]["project_specific_description"] = override["project_specific_description"]
        return effective_config

    async def update_feature_in_config(self, feature_id: str, enabled: bool, project_name: Optional[str] = None) -> Tuple[bool, str]:
        if project_name:
            project_features_path = self._get_project_features_path(project_name)
            # Ensure project directory and admin_settings directory exist
            try:
                await asyncio.to_thread(project_features_path.parent.mkdir, parents=True, exist_ok=True)
            except Exception as e:
                 logger.error(f"Failed to create directory structure for {project_features_path.parent}: {e}")
                 return False, f"Failed to create directory for project {project_name} settings."


            project_config = await self.get_project_config(project_name) # Read current or None
            if project_config is None:
                project_config = {
                    "metadata": {"project_name": project_name, "description": f"Feature overrides for {project_name}"},
                    "feature_overrides": {}
                }

            if "feature_overrides" not in project_config: # Should be there if new, but good check
                project_config["feature_overrides"] = {}

            project_config["feature_overrides"][feature_id] = {"enabled": enabled, "last_modified": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            success = await write_json_async(project_features_path, project_config)
            msg = f"Feature {feature_id} updated to {enabled} for project {project_name}." if success else f"Failed to update feature {feature_id} for project {project_name}."
            return success, msg
        else: # Update global config
            async with self._lock: # Ensure atomic read-modify-write for global config
                current_global_config = await self.load_global_config(force_reload=True) # Get latest from disk
                if feature_id in current_global_config.get("feature_definitions", {}):
                    current_global_config["feature_definitions"][feature_id]["enabled"] = enabled
                    current_global_config["feature_definitions"][feature_id]["last_modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    success = await write_json_async(self.global_config_path, current_global_config)
                    if success:
                        self.global_config = current_global_config # Update cache
                        msg = f"Global feature {feature_id} updated to {enabled}."
                    else:
                        msg = f"Failed to update global feature {feature_id}."
                    return success, msg
                else:
                    return False, f"Feature {feature_id} not found in global configuration."


class AdminService:
    def __init__(self):
        self.project_data_root = Path(settings.PROJECT_DATA_ROOT)
        self.features_manager = FeaturesManager(GLOBAL_FEATURES_CONFIG_PATH, self.project_data_root)

        # Ensure log directory exists
        if not LOG_DIR_PATH.exists():
            try:
                LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created log directory: {LOG_DIR_PATH}")
            except Exception as e:
                logger.error(f"Failed to create log directory {LOG_DIR_PATH}: {e}")


    async def list_features(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            config = await self.features_manager.get_effective_features(project_name)

            features_by_category: Dict[str, List[Dict[str, Any]]] = {}
            feature_groups: Dict[str, List[str]] = {}

            total_features = 0
            enabled_features_count = 0

            raw_feature_definitions = config.get("feature_definitions", {})
            all_feature_details_map: Dict[str, Dict[str, Any]] = {} # Store by fid for easy lookup

            for fid, props in raw_feature_definitions.items():
                total_features += 1
                is_enabled = props.get("enabled", False)
                if is_enabled:
                    enabled_features_count += 1

                feature_detail = {
                    "id": fid,
                    "enabled": is_enabled,
                    "description": props.get("description", "No description"),
                    "category": props.get("category", "uncategorized"),
                    "last_modified": props.get("last_modified"),
                    "project_specific_description": props.get("project_specific_description") # Will be None if not overridden
                }
                all_feature_details_map[fid] = feature_detail

            for cat_id, cat_props in config.get("feature_categories", {}).items():
                cat_display_name = cat_props.get("name", cat_id)
                features_in_this_category = []
                feature_ids_in_this_group = []

                for f_id_in_cat_list in cat_props.get("features", []):
                    if f_id_in_cat_list in all_feature_details_map:
                        features_in_this_category.append(all_feature_details_map[f_id_in_cat_list])
                        feature_ids_in_this_group.append(f_id_in_cat_list)

                if features_in_this_category:
                     features_by_category[cat_display_name] = features_in_this_category
                if feature_ids_in_this_group:
                    feature_groups[cat_id] = feature_ids_in_this_group # Use original cat_id from config

            return {
                "features_by_category": features_by_category,
                "feature_groups": feature_groups,
                "total_features": total_features,
                "enabled_features_count": enabled_features_count,
                "metadata": config.get("metadata", {}),
                "data_source_project": project_name if project_name else "global",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "error": None
            }
        except Exception as e:
            logger.exception(f"Error listing features for project '{project_name}': {e}")
            return {
                "features_by_category": {}, "feature_groups": {}, "total_features": 0, "enabled_features_count": 0,
                "metadata": {}, "data_source_project": project_name if project_name else "global",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "error": str(e)
            }

    async def update_feature_status(self, feature_id: str, enabled: bool, project_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            # First, validate if the feature_id exists in the global definition to prevent arbitrary writes
            global_config = await self.features_manager.load_global_config()
            if feature_id not in global_config.get("feature_definitions", {}):
                msg = f"Feature ID '{feature_id}' not found in global definitions. Cannot update."
                logger.warning(msg)
                return {"success": False, "feature_id": feature_id, "enabled": enabled, "message": msg, "error": msg}

            success, message = await self.features_manager.update_feature_in_config(feature_id, enabled, project_name)
            return {"success": success, "feature_id": feature_id, "enabled": enabled, "message": message, "error": None if success else message}
        except Exception as e:
            logger.exception(f"Error updating feature {feature_id} for project '{project_name}': {e}")
            return {"success": False, "feature_id": feature_id, "enabled": enabled, "message": str(e), "error": str(e)}

    async def bulk_update_features_status(self, updates: Dict[str, bool], project_name: Optional[str] = None) -> Dict[str, Any]:
        successful_updates: List[Dict[str, Any]] = []
        failed_updates: List[Dict[str, Any]] = []

        # Optimization: If project_name is provided, load/create project config once
        # Then apply all updates, then save once. For global, load/save once.
        # For simplicity here, still iterative, but real scenario might batch file I/O.
        # The FeaturesManager.update_feature_in_config handles its own locking for global.
        # For project config, if multiple updates target the same project file, it's also read-modify-write per call.

        for feature_id, enabled_status in updates.items():
            result = await self.update_feature_status(feature_id, enabled_status, project_name) # This already checks feature_id validity
            if result["success"]:
                successful_updates.append({"feature_id": feature_id, "enabled": enabled_status, "message": result["message"]})
            else:
                failed_updates.append({"feature_id": feature_id, "enabled": enabled_status, "error": result.get("error", "Unknown error")})

        return {
            "message": f"Bulk update process completed. Successful: {len(successful_updates)}, Failed: {len(failed_updates)}.",
            "successful_updates": successful_updates,
            "failed_updates": failed_updates
        }

    async def perform_system_cleanup(self, cleanup_type: str = 'logs', max_age_days: int = 30) -> Dict[str, Any]:
        overall_status = "success"
        details: Dict[str, Any] = {}
        total_files_cleaned = 0
        error_messages: List[str] = []

        cutoff_timestamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_age_days)

        async def _cleanup_dir(target_dir: Path, pattern: str = "*.*") -> Tuple[int, List[str]]: # Changed pattern for logs
            cleaned_count = 0
            local_errors: List[str] = []
            if not await asyncio.to_thread(target_dir.exists):
                logger.warning(f"Cleanup directory not found: {target_dir}")
                return 0, [f"Directory not found: {target_dir}"]

            logger.info(f"Scanning {target_dir} for files older than {cutoff_timestamp.isoformat()} matching '{pattern}'")

            # Use a list to collect items first to avoid issues with modifying while iterating if glob is lazy
            items_to_check = list(await asyncio.to_thread(target_dir.glob, pattern))

            for item in items_to_check:
                if await asyncio.to_thread(item.is_file):
                    try:
                        file_mod_time_ts = await asyncio.to_thread(lambda: item.stat().st_mtime)
                        file_mod_time = datetime.datetime.fromtimestamp(file_mod_time_ts, datetime.timezone.utc)
                        if file_mod_time < cutoff_timestamp:
                            logger.info(f"Deleting old file: {item} (modified: {file_mod_time.isoformat()})")
                            await asyncio.to_thread(item.unlink)
                            cleaned_count += 1
                    except Exception as e_item:
                        err_msg = f"Failed to process/delete {item}: {e_item}"
                        logger.error(err_msg)
                        local_errors.append(err_msg)
            return cleaned_count, local_errors

        cleanup_actions: Dict[str, Tuple[Path, str]] = {} # Store path and pattern
        if cleanup_type in ['logs', 'all']:
            cleanup_actions['logs'] = (LOG_DIR_PATH, "*.log*") # More specific for logs
        if cleanup_type in ['temp', 'all']:
            global_temp_dir = self.project_data_root / "_global_temp_files"
            await asyncio.to_thread(global_temp_dir.mkdir, parents=True, exist_ok=True)
            cleanup_actions['temp_files'] = (global_temp_dir, "*.*")
        if cleanup_type in ['cache', 'all']:
            global_cache_dir = Path(settings.APP_ROOT) / "cache_data"
            await asyncio.to_thread(global_cache_dir.mkdir, parents=True, exist_ok=True)
            cleanup_actions['cache_data'] = (global_cache_dir, "*.*")

        for action_name, (action_path, file_pattern) in cleanup_actions.items():
            logger.info(f"Performing cleanup for '{action_name}' in directory: {action_path} with pattern '{file_pattern}'")
            cleaned, errors_action = await _cleanup_dir(action_path, file_pattern)
            details[action_name] = {"cleaned_files_count": cleaned, "path": str(action_path)}
            if errors_action:
                details[action_name]["errors"] = errors_action
                error_messages.extend(errors_action)
            total_files_cleaned += cleaned

        if error_messages:
            overall_status = "partial_success" if total_files_cleaned > 0 else "failed"
        if not cleanup_actions and cleanup_type != 'none': # 'none' could be a valid no-op type
             overall_status = "no_action" # Or "invalid_type"
             error_messages.append(f"Unknown or no cleanup type specified: {cleanup_type}")


        final_error_message = "; ".join(error_messages) if error_messages else None
        if overall_status == "failed" and not final_error_message : # Ensure error message if failed
            final_error_message = "Cleanup operation failed for an unknown reason."


        return {
            "overall_status": overall_status,
            "details": details,
            "total_files_cleaned": total_files_cleaned,
            "cleanup_type_requested": cleanup_type,
            "max_age_days_for_logs_temp": max_age_days,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "error": final_error_message
        }

    async def get_comprehensive_system_info(self) -> Dict[str, Any]:
        try:
            app_root_disk_usage = await asyncio.to_thread(shutil.disk_usage, str(settings.APP_ROOT))
            project_data_disk_usage = await asyncio.to_thread(shutil.disk_usage, str(self.project_data_root))

            app_info = {
                "name": getattr(settings, 'PROJECT_NAME', "KSEB Energy Platform"),
                "version": getattr(settings, 'VERSION', "0.1.0"),
                "python_version_detailed": platform.python_version(),
                "fastapi_version": "N/A",
            }
            try:
                import fastapi
                app_info["fastapi_version"] = fastapi.__version__
            except ImportError: pass

            return {
                "platform": {
                    "system": platform.system(), "release": platform.release(), "version": platform.version(),
                    "machine": platform.machine(), "processor": platform.processor(),
                    "python_version": f"{platform.python_implementation()} {platform.python_version()}",
                },
                "resources": {
                    "cpu_count_logical": psutil.cpu_count(logical=True),
                    "cpu_count_physical": psutil.cpu_count(logical=False),
                    "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                },
                "disk": {
                    "app_root": {"path": str(settings.APP_ROOT),
                                 "total_gb": round(app_root_disk_usage.total / (1024**3), 2),
                                 "used_gb": round(app_root_disk_usage.used / (1024**3), 2),
                                 "free_gb": round(app_root_disk_usage.free / (1024**3), 2)},
                    "project_data_root": {"path": str(self.project_data_root),
                                          "total_gb": round(project_data_disk_usage.total / (1024**3), 2),
                                          "used_gb": round(project_data_disk_usage.used / (1024**3), 2),
                                          "free_gb": round(project_data_disk_usage.free / (1024**3), 2)}
                },
                "application": app_info,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "error": None
            }
        except Exception as e:
            logger.exception(f"Error getting comprehensive system info: {e}")
            return {"error": str(e), "platform": {}, "resources": {}, "disk": {}, "application": {}, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    async def get_system_health_metrics(self) -> Dict[str, Any]:
        try:
            cpu_percent = await asyncio.to_thread(psutil.cpu_percent, interval=0.1)
            virtual_mem = await asyncio.to_thread(psutil.virtual_memory)
            project_data_disk = await asyncio.to_thread(shutil.disk_usage, str(self.project_data_root))

            boot_time_ts = await asyncio.to_thread(psutil.boot_time)
            system_uptime_seconds = datetime.datetime.now(datetime.timezone.utc).timestamp() - boot_time_ts # Use timezone aware now()

            app_components = {
                "feature_config_readable": "OK" if await asyncio.to_thread(GLOBAL_FEATURES_CONFIG_PATH.is_file) and await asyncio.to_thread(os.access, GLOBAL_FEATURES_CONFIG_PATH, os.R_OK) else "Error: Not Readable/Found",
                "project_data_writable": "OK" if await asyncio.to_thread(os.access, self.project_data_root, os.W_OK) else "Error: Not Writable",
                "log_directory_writable": "OK" if await asyncio.to_thread(os.access, LOG_DIR_PATH, os.W_OK) else "Error: Not Writable",
            }
            health_status = "healthy"
            if any("Error" in status for status in app_components.values()): health_status = "degraded"
            if virtual_mem.percent > 95 or (project_data_disk.used / project_data_disk.total * 100) > 95: health_status = "critical"
            elif virtual_mem.percent > 85 or (project_data_disk.used / project_data_disk.total * 100) > 85: health_status = "warning" if health_status == "healthy" else health_status


            return {
                "overall_health": health_status,
                "cpu_percent": cpu_percent,
                "memory_percent": virtual_mem.percent,
                "memory_available_gb": round(virtual_mem.available / (1024**3), 2),
                "disk_percent_project_data": round((project_data_disk.used / project_data_disk.total) * 100, 2),
                "disk_free_gb_project_data": round(project_data_disk.free / (1024**3), 2),
                "application_components_health": app_components,
                "active_processes_count": len(psutil.pids()),
                "system_uptime_seconds": round(system_uptime_seconds,0),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "error": None
            }
        except Exception as e:
            logger.exception(f"Error getting system health metrics: {e}")
            return {"error": str(e), "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "overall_health": "unknown"}

logger.info("AdminService defined with FeaturesManager and system utility methods.")
# Removed main_test and print statement for production code

# Standalone test setup (if needed, to be run manually, e.g. python -m app.services.admin_service)
async def _main_test_run():
    class MockSettings:
        def __init__(self):
            self.APP_ROOT = Path(__file__).resolve().parent.parent
            self.PROJECT_DATA_ROOT = self.APP_ROOT.parent / "data" / "projects_test"
            self.LOG_DIR = self.APP_ROOT.parent / "logs_test"
            self.PROJECT_NAME = "KSEB Test Platform"
            self.VERSION = "0.1-test-service"

            self.PROJECT_DATA_ROOT.mkdir(parents=True, exist_ok=True)
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)
            (self.APP_ROOT / "data" / "admin").mkdir(parents=True, exist_ok=True)

            # Ensure global_features_config.json exists for test
            global_cfg_path_test = self.APP_ROOT / "data" / "admin" / "features_config.json"
            if not global_cfg_path_test.exists():
                dummy_global_config = {
                    "metadata": {"version": "0.1-test", "description": "Test Global Config"},
                    "feature_categories": {
                        "test_cat": {"name": "Test Category", "description":"TC Desc", "features": ["test_f1", "test_f2"]}
                    },
                    "feature_definitions": {
                        "test_f1": {"description": "Test Feature One", "enabled": True, "category": "test_cat"},
                        "test_f2": {"description": "Test Feature Two", "enabled": False, "category": "test_cat"}
                    }
                }
                with open(global_cfg_path_test, 'w') as f:
                    json.dump(dummy_global_config, f, indent=2)


    import sys
    original_settings_module = sys.modules.get("app.config.settings")
    sys.modules["app.config.settings"] = MockSettings()

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logger.info(f"--- Running AdminService Standalone Test using MOCKED settings ---")
    logger.info(f"APP_ROOT (mocked): {settings.APP_ROOT}")
    logger.info(f"PROJECT_DATA_ROOT (mocked): {settings.PROJECT_DATA_ROOT}")
    logger.info(f"LOG_DIR (mocked): {settings.LOG_DIR}")
    logger.info(f"GLOBAL_FEATURES_CONFIG_PATH (derived): {GLOBAL_FEATURES_CONFIG_PATH}")


    admin_service = AdminService()
    test_project = "project_admin_test"
    (settings.PROJECT_DATA_ROOT / test_project).mkdir(parents=True, exist_ok=True)

    logger.info("\n[TEST] Listing global features:")
    print(json.dumps(await admin_service.list_features(), indent=2))

    logger.info(f"\n[TEST] Listing features for project '{test_project}' (before override):")
    print(json.dumps(await admin_service.list_features(project_name=test_project), indent=2))

    logger.info(f"\n[TEST] Updating 'test_f1' to False for project '{test_project}':")
    print(json.dumps(await admin_service.update_feature_status("test_f1", False, project_name=test_project), indent=2))

    logger.info(f"\n[TEST] Listing features for project '{test_project}' (after 'test_f1' override):")
    print(json.dumps(await admin_service.list_features(project_name=test_project), indent=2))

    logger.info(f"\n[TEST] Bulk updating features for project '{test_project}': 'test_f1': True, 'test_f2': True")
    print(json.dumps(await admin_service.bulk_update_features_status({"test_f1": True, "test_f2": True}, project_name=test_project), indent=2))

    logger.info(f"\n[TEST] Listing features for project '{test_project}' (after bulk update):")
    print(json.dumps(await admin_service.list_features(project_name=test_project), indent=2))

    logger.info("\n[TEST] System Info:")
    print(json.dumps(await admin_service.get_comprehensive_system_info(), indent=2))

    logger.info("\n[TEST] System Health:")
    print(json.dumps(await admin_service.get_system_health_metrics(), indent=2))

    logger.info("\n[TEST] System Cleanup (logs, 1 day old):")
    # Create dummy log files for cleanup test
    log_file_old = LOG_DIR_PATH / "old.log"
    log_file_new = LOG_DIR_PATH / "new.log"
    with open(log_file_old, "w") as f: f.write("old log")
    with open(log_file_new, "w") as f: f.write("new log")
    two_days_ago_ts = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).timestamp()
    os.utime(log_file_old, (two_days_ago_ts, two_days_ago_ts))

    print(json.dumps(await admin_service.perform_system_cleanup(cleanup_type="logs", max_age_days=1), indent=2))
    if log_file_old.exists(): logger.error("Old log file was NOT deleted by cleanup test!")
    if not log_file_new.exists(): logger.error("New log file WAS DELETED by cleanup test!")


    # Cleanup test artifacts
    shutil.rmtree(settings.PROJECT_DATA_ROOT)
    shutil.rmtree(settings.LOG_DIR)
    # (settings.APP_ROOT / "data" / "admin" / "features_config.json").unlink(missing_ok=True) # Keep global if it was pre-existing

    if original_settings_module: sys.modules["app.config.settings"] = original_settings_module
    else: del sys.modules["app.config.settings"]
    logger.info(f"--- AdminService Standalone Test Finished ---")

if __name__ == "__main__":
    asyncio.run(_main_test_run())
