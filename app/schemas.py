from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BloggerPersonaCreate(BaseModel):
    name: str
    age_range: str = ""
    body_type: str
    size_category: str = ""
    height: str = ""
    style_tags: list[str] = []
    tone_of_voice: str = ""
    avatar_desc: str = ""
    content_focus: list[str] = []
    avoid_tags: list[str] = []


class BloggerPersonaOut(BloggerPersonaCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    category: str = ""
    price: float = 0.0
    brand: str = ""
    size_available: str = ""
    source_url: str = ""
    attributes: dict = {}
    images: list[str] = []


class ProductOut(ProductCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class OutfitOut(BaseModel):
    id: int
    product_ids: list[int] = []
    description: Optional[str] = ""
    pos_prompt: Optional[str] = ""
    neg_prompt: Optional[str] = ""
    style_tags: list[str] = []
    scene: Optional[str] = ""
    body_type_suitability: Optional[str] = ""
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: int
    outfit_id: Optional[int] = None
    images: list[str] = []
    title: Optional[str] = ""
    content: Optional[str] = ""
    hashtags: list[str] = []
    product_tags: list[dict] = []
    status: Optional[str] = "draft"
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    outfit: Optional[OutfitOut] = None
    model_config = {"from_attributes": True}


class PostUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


class PerformanceOut(BaseModel):
    id: int
    post_id: int
    likes: int
    comments: int
    shares: int
    click_rate: float
    publish_date: datetime
    model_config = {"from_attributes": True}


class TrendOut(BaseModel):
    id: int
    keyword: str
    category: str
    hot_score: int
    source_posts: list[str]
    fetch_date: datetime
    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    product_url: str = ""
    product_ids: list[int] = []
    persona_id: int = 1
    num_images: int = 1
    style: str = ""
    scene: str = ""


class GenerateResponse(BaseModel):
    post: PostOut
    outfit: OutfitOut
    generated_images: list[str]
    quality_report: dict = {}
