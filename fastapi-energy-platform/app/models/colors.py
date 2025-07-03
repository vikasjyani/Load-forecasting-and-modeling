# fastapi-energy-platform/app/models/colors.py
"""
Pydantic models for Color Management API.
"""
from pydantic import BaseModel, Field, constr, validator
from typing import List, Dict, Any, Optional

HexColor = constr(pattern=r"^#[0-9a-fA-F]{6}$")

class ColorItem(BaseModel):
    item_name: str
    color_value: HexColor

class CategoryColors(BaseModel):
    category_name: str
    colors: Dict[str, HexColor]

class SetColorPayload(BaseModel):
    category: str = Field(..., min_length=1)
    item: str = Field(..., min_length=1)
    color: HexColor

class SetMultipleColorsPayload(BaseModel):
    category: str = Field(..., min_length=1)
    colors: Dict[str, HexColor]

class ResetColorsPayload(BaseModel):
    category: Optional[str] = None

class ColorPaletteRequestPayload(BaseModel):
    category: str = Field(..., min_length=1)
    items: List[str] = Field(..., min_items=1)

class ColorPaletteResponse(BaseModel):
    category: str
    items: List[str]
    palette: Dict[str, HexColor]

class ColorValidationRequestPayload(BaseModel):
    color: str

class ColorValidationDetail(BaseModel):
    is_valid_hex: bool
    input_color: str
    standard_hex: Optional[HexColor] = None # if valid and normalized
    rgb_string: Optional[str] = None
    rgb_values: Optional[Tuple[int, int, int]] = None
    brightness: Optional[float] = None # 0-255 typical scale
    is_light: Optional[bool] = None

class ColorStatsCategoryDetail(BaseModel):
    count: int
    items: Optional[List[str]] = None # For dict categories
    type_if_not_dict: Optional[str] = None # For non-dict categories (e.g. a single color string)

class ColorStatsResponse(BaseModel):
    total_categories: int
    total_colors_defined: int # Sum of items in all dict categories
    categories: Dict[str, ColorStatsCategoryDetail]

class ThemeColorsResponse(BaseModel):
    theme_name: str
    colors: Dict[str, HexColor]

class GradientResponse(BaseModel):
    gradient_name: str
    colors: List[HexColor]
