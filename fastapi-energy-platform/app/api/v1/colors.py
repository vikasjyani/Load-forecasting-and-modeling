# fastapi-energy-platform/app/api/v1/colors.py
"""
Color Management API Endpoints for FastAPI
Provides endpoints for managing application-wide color schemes.
"""
import logging
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, Query, HTTPException, Body, Response
from pydantic import BaseModel, Field, constr, validator # For request/response models & validation

# Assuming ColorManager is adapted and available for DI or direct instantiation.
# For now, using a placeholder if the actual utility isn't ready.
try:
    from app.utils.color_manager import ColorManager
    # This assumes ColorManager is refactored to not depend on Flask app context directly.
    # It might take configuration paths in its __init__.
    # Example: color_manager_instance = ColorManager(config_path=Path("app/config/colors.json"))
    # For DI, a dependency function would provide this instance.
    # For simplicity, let's instantiate it globally here for now, assuming it's self-contained.
    # This path would ideally come from settings/config.
    from pathlib import Path
    # Determine a base path, e.g., parent of this 'api' directory, then 'static/config'
    # This relative path needs to be robust.
    # Assuming 'app' is the root for execution or PYTHONPATH.
    _color_config_path = Path(__file__).resolve().parent.parent.parent / "static_config" / "colors.json"

    # Ensure the directory exists before ColorManager tries to create a default file
    _color_config_path.parent.mkdir(parents=True, exist_ok=True)

    color_manager = ColorManager(config_file_path=_color_config_path) # Pass Path object
except ImportError:
    logging.warning("ColorManager not found or not adapted, using placeholder for colors API.")
    class ColorManager: # Placeholder
        def get_all_colors(self) -> Dict: return {"error": "Placeholder ColorManager"}
        def get_category_colors(self, category: str) -> Dict: return {"error": f"Placeholder for category {category}"}
        def get_sector_colors(self, sectors: List[str]) -> Dict: return {s: "#FF0000" for s in sectors}
        def get_model_colors(self, models: List[str]) -> Dict: return {m: "#00FF00" for m in models}
        def get_carrier_colors(self, carriers: List[str]) -> Dict: return {c: "#0000FF" for c in carriers}
        def get_chart_colors(self, count: int) -> List[str]: return ["#FF6384"] * count
        def set_color(self, category: str, item: str, color: str) -> bool: return True
        def set_colors(self, category: str, color_dict: Dict[str, str]) -> bool: return True
        def reset_to_defaults(self, category: Optional[str] = None) -> bool: return True
        def export_colors_for_js(self) -> str: return "window.AppColors = {'error': 'Placeholder'};"
        def get_gradient(self, gradient_name: str) -> List[str]: return ["#FF0000", "#00FF00"]
        def get_theme_colors(self, theme: str = "light") -> Dict[str, str]: return {"background": "#FFFFFF"}
    color_manager = ColorManager()

from app.utils.error_handlers import ProcessingError, ValidationError as CustomValidationError, ResourceNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---
HexColor = constr(pattern=r"^#[0-9a-fA-F]{6}$")

class SetColorPayload(BaseModel):
    category: str = Field(..., min_length=1)
    item: str = Field(..., min_length=1)
    color: HexColor

class SetMultipleColorsPayload(BaseModel):
    category: str = Field(..., min_length=1)
    colors: Dict[str, HexColor]

class ResetColorsPayload(BaseModel):
    category: Optional[str] = None

class ColorPalettePayload(BaseModel):
    category: str = Field(..., min_length=1)
    items: List[str] = Field(..., min_items=1)

class ColorValidationPayload(BaseModel):
    color: str # Can be any string, will be validated by endpoint

    @validator('color')
    def color_must_be_hex(cls, v):
        if not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be a valid hex color string (e.g., #RRGGBB)')
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError('Invalid hex characters in color string')
        return v

# --- API Endpoints ---

@router.get("/all", summary="Get All Color Configurations")
async def get_all_colors_api():
    try:
        colors = color_manager.get_all_colors()
        return colors
    except Exception as e:
        logger.error(f"Error getting all colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get colors: {str(e)}")

@router.get("/category/{category}", summary="Get Colors for a Specific Category")
async def get_category_colors_api(category: str):
    try:
        colors = color_manager.get_category_colors(category)
        if not colors and category not in color_manager.get_all_colors(): # Check if category itself is valid but empty or truly non-existent
            raise ResourceNotFoundError(resource_type="Color Category", resource_id=category)
        return {"category": category, "colors": colors}
    except ResourceNotFoundError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting colors for category {category}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get category colors: {str(e)}")

# Example for query parameters: /sectors?sectors=Residential&sectors=Commercial
@router.get("/sectors", summary="Get Sector Colors")
async def get_sector_colors_api(sectors: Optional[List[str]] = Query(None)):
    try:
        if sectors:
            colors = color_manager.get_sector_colors(sectors)
        else:
            colors = color_manager.get_category_colors('sectors')
        return {"sectors_requested": sectors or list(colors.keys()), "colors": colors}
    except Exception as e:
        logger.error(f"Error getting sector colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get sector colors: {str(e)}")


@router.get("/chart/{count}", summary="Get Chart Colors")
async def get_chart_colors_api(count: int):
    if not (1 <= count <= 50):
        raise CustomValidationError(message="Count must be between 1 and 50.", field="count")
    try:
        colors = color_manager.get_chart_colors(count)
        return {"count": count, "colors": colors}
    except Exception as e:
        logger.error(f"Error getting chart colors for count {count}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get chart colors: {str(e)}")

@router.post("/set", summary="Set a Specific Color")
async def set_color_api(payload: SetColorPayload):
    try:
        success = color_manager.set_color(payload.category, payload.item, payload.color)
        if success:
            return {"message": f"Color set for {payload.category}.{payload.item}", "details": payload.model_dump()}
        else:
            raise ProcessingError(message="Failed to save color, check logs.")
    except Exception as e:
        logger.error(f"Error setting color: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set color: {str(e)}")

@router.post("/set_multiple", summary="Set Multiple Colors for a Category")
async def set_multiple_colors_api(payload: SetMultipleColorsPayload):
    try:
        success = color_manager.set_colors(payload.category, payload.colors)
        if success:
            return {"message": f"Set {len(payload.colors)} colors for category '{payload.category}'", "details": payload.model_dump()}
        else:
            raise ProcessingError(message="Failed to save multiple colors, check logs.")
    except Exception as e:
        logger.error(f"Error setting multiple colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set colors: {str(e)}")

@router.post("/reset", summary="Reset Colors to Defaults")
async def reset_colors_api(payload: Optional[ResetColorsPayload] = None): # Optional payload
    category_to_reset = payload.category if payload else None
    try:
        success = color_manager.reset_to_defaults(category_to_reset)
        if success:
            message = f"Reset colors for category '{category_to_reset}'" if category_to_reset else "Reset all colors to defaults"
            return {"message": message, "category_reset": category_to_reset, "reset_all": category_to_reset is None}
        else:
            raise ProcessingError(message="Failed to reset colors, check logs.")
    except Exception as e:
        logger.error(f"Error resetting colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset colors: {str(e)}")

@router.get("/export/js", summary="Export Colors as JavaScript Object")
async def export_colors_for_js_api():
    try:
        js_export_string = color_manager.export_colors_for_js()
        return Response(content=js_export_string, media_type="application/javascript")
    except Exception as e:
        logger.error(f"Error exporting colors for JS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export colors for JS: {str(e)}")

# ... (similar adaptations for get_model_colors, get_carrier_colors, get_gradient, get_theme_colors, validate_color, get_color_stats)

logger.info("Color Management API router defined for FastAPI.")
print("Color Management API router defined for FastAPI.")
