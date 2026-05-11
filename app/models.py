from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class BloggerPersona(Base):
    __tablename__ = "blogger_personas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age_range = Column(String(50))
    body_type = Column(String(50), nullable=False)
    size_category = Column(String(50))
    height = Column(String(20))
    style_tags = Column(JSON, default=list)
    tone_of_voice = Column(Text)
    avatar_desc = Column(Text)
    content_focus = Column(JSON, default=list)
    avoid_tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    price = Column(Float)
    brand = Column(String(100))
    size_available = Column(String(255))
    source_url = Column(String(500))
    attributes = Column(JSON, default=dict)
    images = Column(JSON, default=list)
    style = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Outfit(Base):
    __tablename__ = "outfits"
    id = Column(Integer, primary_key=True, index=True)
    product_ids = Column(JSON, default=list)
    description = Column(Text)
    pos_prompt = Column(Text)
    neg_prompt = Column(Text)
    style_tags = Column(JSON, default=list)
    scene = Column(String(255))
    body_type_suitability = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GeneratedPost(Base):
    __tablename__ = "generated_posts"
    id = Column(Integer, primary_key=True, index=True)
    outfit_id = Column(Integer, ForeignKey("outfits.id"))
    images = Column(JSON, default=list)
    title = Column(String(500))
    content = Column(Text)
    hashtags = Column(JSON, default=list)
    product_tags = Column(JSON, default=list)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)
    outfit = relationship("Outfit")


class PostPerformance(Base):
    __tablename__ = "post_performances"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("generated_posts.id"), unique=True)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    click_rate = Column(Float, default=0.0)
    publish_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    post = relationship("GeneratedPost")


class Trend(Base):
    __tablename__ = "trends"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False)
    category = Column(String(100))
    hot_score = Column(Integer, default=0)
    source_posts = Column(JSON, default=list)
    fetch_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
