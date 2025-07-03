# fastapi-energy-platform/app/services/color_service.py
"""
Service layer for Color Management.
Interacts with ColorManager and provides an async interface for API endpoints.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.utils.color_manager import ColorManager # Assuming refactored version
from app.config import settings # To get the path for colors.json
from app.utils.error_handlers import ResourceNotFoundError, ProcessingError

logger = logging.getLogger(__name__)

class ColorService:
    def __init__(self, color_manager_instance: ColorManager):
        self.manager = color_manager_instance

    @classmethod
    async def create(cls):
        # Determine the path for colors.json, e.g., from settings
        # For example, if settings.STATIC_CONFIG_PATH points to '.../static_config/'
        # and colors file is 'colors.json' inside it.
        # This path needs to be correctly configured.
        # Using a placeholder path resolution for now, assuming settings.BASE_DIR
        # and a conventional location.

        # Path from the original Flask app was effectively 'static/config/colors.json'
        # FastAPI app dir is 'fastapi-energy-platform/app/'
        # Project root is 'fastapi-energy-platform/'
        # So, if 'static_config' is at the same level as 'app', then:
        # config_path = settings.BASE_DIR.parent / "static_config" / "colors.json"
        # For now, let's assume a path relative to where the app runs, or a fixed dev path.
        # The Flask app used app.static_folder + '/config/colors.json'.
        # If static_folder is 'fastapi-energy-platform/app/static', then path is 'app/static/config/colors.json'

        # Let's try to place it in a config directory at the project root for FastAPI
        # e.g., fastapi-energy-platform/config_data/colors.json
        # This needs to be consistent with where ColorManager is instantiated in api/v1/colors.py if not using this service.
        # For service-based approach, this is the place to define it.

        # Correct path based on typical project structure where settings.BASE_DIR is 'fastapi-energy-platform/app'
        color_config_file = settings.BASE_DIR.parent / "app_config_data" / "colors.json"

        # Ensure directory exists for the ColorManager
        await asyncio.to_thread(color_config_file.parent.mkdir, parents=True, exist_ok=True)

        manager_instance = await asyncio.to_thread(ColorManager, color_config_file)
        return cls(manager_instance)

    async def get_all_colors_config(self) -> Dict:
        return await asyncio.to_thread(self.manager.get_all_colors)

    async def get_colors_for_category(self, category_name: str) -> Dict[str, str]:
        colors = await asyncio.to_thread(self.manager.get_category_colors, category_name)
        # The ColorManager itself might return empty dict if category is valid but empty.
        # We need to distinguish "category not found" from "category exists but is empty".
        # This might require a check in ColorManager like `has_category`.
        # For now, if it's empty and not in default_colors, consider it not found.
        if not colors and category_name not in self.manager.default_colors:
             raise ResourceNotFoundError(resource_type="Color Category", resource_id=category_name)
        return colors

    async def get_specific_item_colors(self, category_name: str, items: List[str]) -> Dict[str, str]:
        # This typically calls get_color_palette which handles item-specific generation
        return await asyncio.to_thread(self.manager.get_color_palette, category_name, items)

    async def get_chart_color_list(self, count: int) -> List[str]:
        return await asyncio.to_thread(self.manager.get_chart_colors, count)

    async def set_item_color(self, category_name: str, item_name: str, color_value: str) -> bool:
        return await asyncio.to_thread(self.manager.set_color, category_name, item_name, color_value)

    async def set_multiple_item_colors(self, category_name: str, colors_map: Dict[str, str]) -> bool:
        return await asyncio.to_thread(self.manager.set_colors, category_name, colors_map)

    async def reset_color_config(self, category_name: Optional[str] = None) -> bool:
        return await asyncio.to_thread(self.manager.reset_to_defaults, category_name)

    async def export_colors_as_js_string(self) -> str:
        return await asyncio.to_thread(self.manager.export_colors_for_js)

    async def get_gradient_definition(self, gradient_name: str) -> List[str]:
        gradient = await asyncio.to_thread(self.manager.get_gradient, gradient_name)
        if not gradient or gradient == ["#CCCCCC", "#333333"]: # Default fallback if not found
             # Check if it actually exists or if it's just the default fallback
            if gradient_name not in self.manager.colors.get("gradients", {}):
                 raise ResourceNotFoundError(resource_type="Gradient", resource_id=gradient_name)
        return gradient

    async def get_theme_color_definitions(self, theme_name: str) -> Dict[str, str]:
        theme_colors = await asyncio.to_thread(self.manager.get_theme_colors, theme_name)
        # Default theme 'light' always exists in ColorManager's defaults
        if theme_name != "light" and theme_colors == self.manager.default_colors["themes"]["light"]:
            if theme_name not in self.manager.colors.get("themes", {}):
                raise ResourceNotFoundError(resource_type="Theme", resource_id=theme_name)
        return theme_colors

    async def validate_color_format_details(self, color_value: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self.manager.validate_hex_color, color_value)

    async def get_color_configuration_stats(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self.manager.get_color_stats)

logger.info("ColorService defined for FastAPI.")
