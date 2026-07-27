from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class AssetType(str, Enum):
    main = "main"
    angle = "angle"
    detail = "detail"
    lifestyle = "lifestyle"
    transparent = "transparent"
    logo = "logo"


class SceneType(str, Enum):
    product_hero = "product_hero"
    product_closeup = "product_closeup"
    lifestyle_use = "lifestyle_use"
    comparison = "comparison"
    atmosphere = "atmosphere"
    cta = "cta"


class GenerationStrategy(str, Enum):
    image_to_video = "image_to_video"
    template_composite = "template_composite"


class PostprocessConfig(BaseModel):
    """确定性后期模板参数，不允许把品牌、价格和字幕交给模型生成。"""

    template: Literal["product_promo_portrait"] = "product_promo_portrait"
    subtitle: Optional[str] = Field(default=None, max_length=120)
    price_text: Optional[str] = Field(default=None, max_length=80)
    cta: Optional[str] = Field(default=None, max_length=40)
    transparent_asset_id: Optional[int] = None
    logo_asset_id: Optional[int] = None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    brand: Optional[str] = Field(default=None, max_length=120)
    price: Optional[str] = Field(default=None, max_length=80)
    specs: dict[str, Any] = Field(default_factory=dict)
    selling_points: list[str] = Field(default_factory=list)
    prohibited_terms: list[str] = Field(default_factory=list)


class ProductAssetCreate(BaseModel):
    asset_type: AssetType
    url: HttpUrl
    is_primary: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryboardSceneCreate(BaseModel):
    scene_no: int = Field(ge=1)
    scene_type: SceneType
    target_duration: float = Field(gt=0, le=5)
    asset_id: Optional[int] = None
    generation_strategy: GenerationStrategy = GenerationStrategy.image_to_video
    motion_prompt: str = Field(default="", max_length=2000)
    identity_constraints: list[str] = Field(default_factory=list)
    postprocess_layers: list[str] = Field(
        default_factory=lambda: ["transparent_product", "brand_logo", "subtitle", "price_tag", "cta"]
    )
    postprocess_config: PostprocessConfig = Field(default_factory=PostprocessConfig)


class StoryboardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    scenes: list[StoryboardSceneCreate] = Field(min_length=1)


class StoryboardSceneUpdate(BaseModel):
    asset_id: Optional[int] = None
    scene_type: Optional[SceneType] = None
    target_duration: Optional[float] = Field(default=None, gt=0, le=5)
    generation_strategy: Optional[GenerationStrategy] = None
    motion_prompt: Optional[str] = Field(default=None, max_length=2000)
    identity_constraints: Optional[list[str]] = None
    postprocess_layers: Optional[list[str]] = None
    postprocess_config: Optional[PostprocessConfig] = None
