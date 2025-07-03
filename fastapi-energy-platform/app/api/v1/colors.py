# fastapi-energy-platform/app/api/v1/colors.py
"""
Color Management API Endpoints for FastAPI
Provides endpoints for managing application-wide color schemes.
"""
import logging
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, Query, HTTPException, Body, Response
from pydantic import BaseModel, Field, constr, validator # For request/response models & validation

# Removed direct ColorManager instantiation. Service will be injected.
from app.services.color_service import ColorService
from app.dependencies import get_color_service
from app.models.colors import ( # Import Pydantic models
    HexColor, SetColorPayload, SetMultipleColorsPayload, ResetColorsPayload,
    ColorPaletteRequestPayload, ColorPaletteResponse,
    ColorValidationRequestPayload, ColorValidationDetail,
    ColorStatsResponse, ThemeColorsResponse, GradientResponse
)
from app.utils.error_handlers import ProcessingError, ValidationError as CustomValidationError, ResourceNotFoundError # Already imported

logger = logging.getLogger(__name__)
router = APIRouter()

# --- API Endpoints ---

@router.get("/all", summary="Get All Color Configurations", response_model=Dict[str, Any])
async def get_all_colors_api(service: ColorService = Depends(get_color_service)):
    try:
        colors = await service.get_all_colors_config()
        return colors
    except Exception as e:
        logger.error(f"Error getting all colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get colors: {str(e)}")

@router.get("/category/{category}", summary="Get Colors for a Specific Category", response_model=Dict[str, HexColor])
async def get_category_colors_api(
    category: str = FastAPIPath(..., description="The color category name"),
    service: ColorService = Depends(get_color_service)
):
    try:
        colors = await service.get_colors_for_category(category)
        return colors # Service raises ResourceNotFoundError if category not found
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting colors for category {category}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get category colors: {str(e)}")

@router.get("/sectors", summary="Get Sector Colors", response_model=Dict[str, HexColor])
async def get_sector_colors_api(
    sectors: Optional[List[str]] = Query(None, description="List of specific sector names to retrieve colors for. If empty, returns all sector colors."),
    service: ColorService = Depends(get_color_service)
):
    try:
        if sectors:
            colors = await service.get_specific_item_colors('sectors', sectors)
        else:
            colors = await service.get_colors_for_category('sectors')
        return colors
    except Exception as e:
        logger.error(f"Error getting sector colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get sector colors: {str(e)}")

@router.get("/models", summary="Get Model Colors", response_model=Dict[str, HexColor])
async def get_model_colors_api(
    models: Optional[List[str]] = Query(None),
    service: ColorService = Depends(get_color_service)
):
    try:
        if models:
            colors = await service.get_specific_item_colors('models', models)
        else:
            colors = await service.get_colors_for_category('models')
        return colors
    except Exception as e:
        logger.error(f"Error getting model colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get model colors.")

@router.get("/carriers", summary="Get Carrier Colors", response_model=Dict[str, HexColor])
async def get_carrier_colors_api(
    carriers: Optional[List[str]] = Query(None),
    service: ColorService = Depends(get_color_service)
):
    try:
        if carriers:
            colors = await service.get_specific_item_colors('carriers', carriers)
        else:
            colors = await service.get_colors_for_category('carriers')
        return colors
    except Exception as e:
        logger.error(f"Error getting carrier colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get carrier colors.")


@router.get("/chart/{count}", summary="Get Chart Colors", response_model=List[HexColor])
async def get_chart_colors_api(
    count: int = FastAPIPath(..., gt=0, le=50, description="Number of chart colors to generate (1-50)"),
    service: ColorService = Depends(get_color_service)
):
    try:
        colors = await service.get_chart_color_list(count)
        return colors
    except Exception as e: # Includes potential errors from service if count is out of range internally
        logger.error(f"Error getting chart colors for count {count}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get chart colors: {str(e)}")

@router.post("/set", summary="Set a Specific Color")
async def set_color_api(payload: SetColorPayload, service: ColorService = Depends(get_color_service)):
    try:
        success = await service.set_item_color(payload.category, payload.item, payload.color)
        if success:
            return {"message": f"Color set for {payload.category}.{payload.item}", "details": payload.model_dump()}
        else:
            raise ProcessingError(message="Failed to save color, check logs or configuration.")
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting color: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set color: {str(e)}")

@router.post("/set_multiple", summary="Set Multiple Colors for a Category")
async def set_multiple_colors_api(payload: SetMultipleColorsPayload, service: ColorService = Depends(get_color_service)):
    try:
        success = await service.set_multiple_item_colors(payload.category, payload.colors)
        if success:
            return {"message": f"Set {len(payload.colors)} colors for category '{payload.category}'", "details": payload.model_dump()}
        else:
            raise ProcessingError(message="Failed to save multiple colors, check logs or configuration.")
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting multiple colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set colors: {str(e)}")

@router.post("/reset", summary="Reset Colors to Defaults")
async def reset_colors_api(payload: Optional[ResetColorsPayload] = None, service: ColorService = Depends(get_color_service)):
    category_to_reset = payload.category if payload else None
    try:
        success = await service.reset_color_config(category_to_reset)
        if success:
            message = f"Reset colors for category '{category_to_reset}'" if category_to_reset else "Reset all colors to defaults"
            return {"message": message, "category_reset": category_to_reset, "reset_all": category_to_reset is None}
        else:
            # This case might occur if category_to_reset is specified but not found in defaults by service
            raise ProcessingError(message=f"Failed to reset colors. Category '{category_to_reset}' might not be resettable or an error occurred.")
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e)) # Or 500 if it's a save error
    except Exception as e:
        logger.error(f"Error resetting colors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset colors: {str(e)}")

@router.get("/export/js", summary="Export Colors as JavaScript Object String")
async def export_colors_for_js_api(service: ColorService = Depends(get_color_service)):
    try:
        js_export_string = await service.export_colors_as_js_string()
        return Response(content=js_export_string, media_type="application/javascript")
    except Exception as e:
        logger.error(f"Error exporting colors for JS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export colors for JS: {str(e)}")

@router.post("/palette", response_model=ColorPaletteResponse, summary="Get Color Palette for Multiple Items")
async def get_color_palette_api(payload: ColorPaletteRequestPayload, service: ColorService = Depends(get_color_service)):
    try:
        palette = await service.get_specific_item_colors(payload.category, payload.items)
        return ColorPaletteResponse(category=payload.category, items=payload.items, palette=palette)
    except Exception as e:
        logger.error(f"Error getting color palette: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get color palette.")

@router.get("/gradient/{gradient_name}", response_model=GradientResponse, summary="Get Gradient Colors")
async def get_gradient_api(
    gradient_name: str = FastAPIPath(..., description="Name of the gradient"),
    service: ColorService = Depends(get_color_service)
):
    try:
        colors = await service.get_gradient_definition(gradient_name)
        return GradientResponse(gradient_name=gradient_name, colors=colors)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting gradient {gradient_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get gradient: {str(e)}")

@router.get("/theme/{theme_name}", response_model=ThemeColorsResponse, summary="Get Theme Colors")
async def get_theme_colors_api(
    theme_name: str = FastAPIPath(default="light", description="Name of the theme (e.g., 'light', 'dark')"),
    service: ColorService = Depends(get_color_service)
):
    try:
        colors = await service.get_theme_color_definitions(theme_name)
        return ThemeColorsResponse(theme_name=theme_name, colors=colors)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting theme {theme_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get theme colors: {str(e)}")

@router.post("/validate", response_model=ColorValidationDetail, summary="Validate Color Format")
async def validate_color_api(
    payload: ColorValidationRequestPayload, # Pydantic model will do basic validation if defined there
    service: ColorService = Depends(get_color_service)
):
    try:
        # Service method performs more detailed validation and info gathering
        validation_details = await service.validate_color_format_details(payload.color)
        return ColorValidationDetail(**validation_details)
    except Exception as e:
        logger.error(f"Error validating color: {e}", exc_info=True)
        # Return a structured error, or re-raise as HTTPException
        # For now, let's assume service's validate_hex_color returns enough info
        # and doesn't typically raise exceptions for invalid formats but flags them in response.
        # If it can raise, catch specific ones.
        raise HTTPException(status_code=500, detail=f"Failed to validate color: {str(e)}")

@router.get("/stats", response_model=ColorStatsResponse, summary="Get Color Configuration Statistics")
async def get_color_stats_api(service: ColorService = Depends(get_color_service)):
    try:
        stats = await service.get_color_configuration_stats()
        return ColorStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting color stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get color statistics: {str(e)}")


logger.info("Color Management API router defined for FastAPI, using ColorService.")
print("Color Management API router defined for FastAPI, using ColorService.")
