# fastapi-energy-platform/app/utils/features_manager.py
import os
import json
import time
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class FeatureManager:
    """
    Feature Manager for FastAPI.
    Manages feature flags from a global configuration and optional project-specific overrides.
    Configuration paths should be absolute or resolvable from a known base path.
    """

    def __init__(self, global_config_path: Path, project_data_root: Optional[Path] = None):
        self.global_config_path = global_config_path
        self.project_data_root = project_data_root

        self._ensure_global_config()
        self.cache_timeout_seconds = 300  # 5 minutes
        self._last_load_time: Dict[str, float] = {}
        self._feature_cache: Dict[str, Dict] = {}
        logger.info(f"FeatureManager initialized with global config: {self.global_config_path}")

    def _ensure_global_config(self):
        try:
            if not self.global_config_path.exists():
                logger.info(f"Creating default global feature configuration at {self.global_config_path}")
                self.global_config_path.parent.mkdir(parents=True, exist_ok=True)
                default_config = {
                    "features": {
                        "demand_projection": {"enabled": True, "description": "Electricity demand forecasting", "category": "forecasting"},
                        "demand_visualization": {"enabled": True, "description": "Demand forecast visualization", "category": "visualization"},
                        "load_profile_generation": {"enabled": True, "description": "Load curve generation", "category": "load_management"},
                        "load_profile_analysis": {"enabled": True, "description": "Load profile analysis", "category": "load_management"},
                        "pypsa_modeling": {"enabled": True, "description": "Power system modeling with PyPSA", "category": "power_systems"}
                    },
                    "feature_groups": {
                        "core_forecasting": ["demand_projection", "demand_visualization"],
                        "advanced_analysis": ["load_profile_generation", "load_profile_analysis", "pypsa_modeling"]
                    },
                    "metadata": {"created_at": datetime.now().isoformat(), "version": "1.0"}
                }
                with open(self.global_config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info("Default global feature configuration created.")
        except Exception as e:
            logger.error(f"Error ensuring global feature config at {self.global_config_path}: {e}", exc_info=True)

    def _load_config_from_file(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            logger.debug(f"Configuration file not found: {file_path}")
            return {"features": {}, "feature_groups": {}}
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            if not isinstance(config.get("features"), dict): config["features"] = {}
            if not isinstance(config.get("feature_groups"), dict): config["feature_groups"] = {}
            return config
        except json.JSONDecodeError as e_json:
            logger.error(f"Error decoding JSON from {file_path}: {e_json}")
        except Exception as e_io:
            logger.error(f"Error reading configuration file {file_path}: {e_io}")
        return {"features": {}, "feature_groups": {}, "error": f"Failed to load/parse {file_path.name}"}

    def _get_project_config_path(self, project_name: str) -> Optional[Path]:
        if not self.project_data_root or not project_name:
            return None
        safe_project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
        return self.project_data_root / safe_project_name / 'config' / 'features.json'

    def _needs_reload(self, cache_key: str) -> bool:
        if cache_key not in self._feature_cache: return True
        last_load = self._last_load_time.get(cache_key, 0)
        return (time.time() - last_load) > self.cache_timeout_seconds

    def get_merged_features(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        cache_key = project_name or "_global_"

        if not self._needs_reload(cache_key):
            logger.debug(f"Using cached feature configuration for '{cache_key}'.")
            return self._feature_cache[cache_key]

        logger.debug(f"Reloading feature configuration for '{cache_key}'.")
        global_config = self._load_config_from_file(self.global_config_path)
        if "error" in global_config:
            logger.error(f"Failed to load global features: {global_config['error']}")
            self._feature_cache[cache_key] = {"features": {}, "feature_groups": {}, "metadata": {"error": "Global config load failed"}}
            self._last_load_time[cache_key] = time.time()
            return self._feature_cache[cache_key]

        final_config = {"features": dict(global_config["features"]), "feature_groups": dict(global_config["feature_groups"])}
        final_config["metadata"] = {"source": "global", "loaded_at": datetime.now().isoformat()}
        final_config["metadata"].update(global_config.get("metadata", {}))

        if project_name:
            project_config_path = self._get_project_config_path(project_name)
            if project_config_path:
                project_config = self._load_config_from_file(project_config_path)
                if "error" not in project_config:
                    for feature_id, p_config in project_config["features"].items():
                        final_config["features"].setdefault(feature_id, {}).update(p_config)
                    final_config["feature_groups"].update(project_config["feature_groups"])
                    final_config["metadata"]["source"] = "global_merged_with_project"
                    final_config["metadata"]["project_config_used"] = str(project_config_path)
                    if "metadata" in project_config:
                        final_config["metadata"].update(project_config["metadata"])
                else:
                    logger.warning(f"Failed to load project features for '{project_name}': {project_config['error']}")

        self._feature_cache[cache_key] = final_config
        self._last_load_time[cache_key] = time.time()
        return final_config

    def is_feature_enabled(self, feature_id: str, project_name: Optional[str] = None) -> bool:
        config = self.get_merged_features(project_name)
        return config.get("features", {}).get(feature_id, {}).get("enabled", False)

    def get_enabled_features(self, project_name: Optional[str] = None) -> List[str]:
        config = self.get_merged_features(project_name)
        return [fid for fid, fcfg in config.get("features", {}).items() if fcfg.get("enabled", False)]

    def set_feature_enabled(self, feature_id: str, enabled: bool, project_name: Optional[str] = None) -> bool:
        config_path_to_modify = self.global_config_path
        if project_name:
            project_c_path = self._get_project_config_path(project_name)
            if project_c_path:
                config_path_to_modify = project_c_path
                config_path_to_modify.parent.mkdir(parents=True, exist_ok=True)

        try:
            current_config = self._load_config_from_file(config_path_to_modify)
            if "error" in current_config and config_path_to_modify.exists():
                 logger.error(f"Cannot set feature: error loading config {config_path_to_modify}.")
                 return False

            current_config["features"].setdefault(feature_id, {})
            current_config["features"][feature_id]["enabled"] = enabled
            current_config["features"][feature_id]["last_modified"] = datetime.now().isoformat()
            current_config.setdefault("metadata", {})["last_modified"] = datetime.now().isoformat()

            with open(config_path_to_modify, 'w') as f:
                json.dump(current_config, f, indent=2)

            cache_key_to_invalidate = project_name or "_global_"
            if cache_key_to_invalidate in self._feature_cache: del self._feature_cache[cache_key_to_invalidate]
            if cache_key_to_invalidate in self._last_load_time: del self._last_load_time[cache_key_to_invalidate]
            logger.info(f"Feature '{feature_id}' set to {enabled} in {config_path_to_modify}. Cache invalidated.")
            return True
        except Exception as e:
            logger.error(f"Error setting feature '{feature_id}' in {config_path_to_modify}: {e}", exc_info=True)
            return False

    def get_feature_info(self, feature_id: str, project_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        config = self.get_merged_features(project_name)
        feature_config = config.get("features", {}).get(feature_id)
        if not feature_config: return None

        return {
            "id": feature_id,
            "enabled": feature_config.get("enabled", False),
            "description": feature_config.get("description", ""),
            "category": feature_config.get("category", "general"),
            "groups": [gid for gid, flist in config.get("feature_groups", {}).items() if feature_id in flist],
            "last_modified": feature_config.get("last_modified", ""),
            "metadata_source": config.get("metadata", {}).get("source")
        }

    def clear_cache(self, project_name: Optional[str] = None):
        if project_name is None:
            self._feature_cache.clear()
            self._last_load_time.clear()
            logger.info("All feature caches cleared.")
        else:
            if project_name in self._feature_cache: del self._feature_cache[project_name]
            if project_name in self._last_load_time: del self._last_load_time[project_name]
            logger.info(f"Cache cleared for project '{project_name}'.")

logger.info("FeatureManager for FastAPI defined.")
print("FeatureManager for FastAPI defined.")
