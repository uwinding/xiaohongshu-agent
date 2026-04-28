# AI 穿搭博主 Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Python FastAPI 后端 + Web 管理后台的 AI 穿搭博主 Agent，包含 6 个独立 Skill 模块，输入商品链接自动产出小红书穿搭图文。

**Architecture:** FastAPI 单体应用，SQLite 持久化，6 个 Skill 模块通过 LLM API 调用实现，Pipeline 层串联调度。管理后台用 Jinja2 模板直出。Docker Compose 一键部署。

**Tech Stack:** Python 3.11+, FastAPI, SQLite (SQLAlchemy), OpenAI SDK (GPT-4o + DALL-E 3), requests + BeautifulSoup4, Jinja2 模板, Docker

**参考设计文档:** `/home/lhy/workspace/AI穿搭博主Agent-项目设计文档.md`

---

## 文件结构

```
xiaohongshu-agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI 入口 + 静态文件挂载
│   ├── config.py              # 环境变量配置
│   ├── database.py            # SQLite 连接 + 初始化
│   ├── models.py              # SQLAlchemy ORM 模型
│   ├── schemas.py             # Pydantic 请求/响应 Schema
│   ├── llm_client.py          # OpenAI SDK 封装（GPT-4o + DALL-E）
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── base.py            # Skill 抽象基类
│   │   ├── trend_radar.py     # Skill 1: 趋势雷达
│   │   ├── product_matcher.py # Skill 2: 商品匹配
│   │   ├── outfit_composer.py # Skill 3: 穿搭合成
│   │   ├── image_generator.py # Skill 4: 图片生成
│   │   ├── content_writer.py  # Skill 5: 文案写作
│   │   └── performance_tracker.py # Skill 6: 数据追踪
│   ├── pipeline.py            # 流程编排
│   ├── scraper.py             # 小红书趋势爬虫
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── generate.py        # POST /api/generate
│   │   ├── posts.py           # GET/PATCH /api/posts
│   │   └── trends.py          # GET /api/trends
│   └── templates/             # Jinja2 管理后台模板
│       ├── base.html
│       ├── index.html         # 内容列表
│       ├── post_detail.html   # 详情 + 审核
│       └── trends.html        # 趋势数据
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # pytest fixtures
│   ├── test_models.py
│   ├── test_llm_client.py
│   ├── test_scraper.py
│   ├── test_skills/
│   │   ├── __init__.py
│   │   ├── test_trend_radar.py
│   │   ├── test_product_matcher.py
│   │   ├── test_outfit_composer.py
│   │   ├── test_image_generator.py
│   │   ├── test_content_writer.py
│   │   └── test_performance_tracker.py
│   ├── test_pipeline.py
│   └── test_routes.py
├── data/
│   ├── persona.yaml           # 默认博主人设
│   └── products.csv           # 初始商品库
├── storage/
│   └── images/                # 生成的图片
├── pyproject.toml             # 项目依赖（uv/pip）
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

### Task 1: 项目脚手架搭建

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/database.py`
- Create: `app/models.py`
- Create: `app/schemas.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `data/persona.yaml`
- Create: `data/products.csv`

- [ ] **Step 1: 创建 pyproject.toml 项目依赖**

```toml
[project]
name = "xiaohongshu-agent"
version = "0.1.0"
description = "AI fashion blogger agent for Xiaohongshu"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy>=2.0.0",
    "openai>=1.30.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.2.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.9",
    "pyyaml>=6.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 2: 创建 .env.example**

```env
# OpenAI API
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
# 如果使用代理或兼容API(如Gemini)，修改 BASE_URL
# OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# LLM 模型配置
LLM_MODEL=gpt-4o
IMAGE_MODEL=dall-e-3

# 应用配置
DATABASE_URL=sqlite:///./data/agent.db
STORAGE_DIR=./storage/images
```

- [ ] **Step 3: 创建 app/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    image_model: str = "dall-e-3"
    database_url: str = "sqlite:///./data/agent.db"
    storage_dir: str = "./storage/images"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 创建 app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: 创建 app/models.py（所有数据模型）**

```python
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
    style_tags = Column(JSON, default=[])
    tone_of_voice = Column(Text)
    avatar_desc = Column(Text)
    content_focus = Column(JSON, default=[])
    avoid_tags = Column(JSON, default=[])
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
    attributes = Column(JSON, default={})
    images = Column(JSON, default=[])
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Outfit(Base):
    __tablename__ = "outfits"
    id = Column(Integer, primary_key=True, index=True)
    product_ids = Column(JSON, default=[])
    description = Column(Text)
    pos_prompt = Column(Text)
    neg_prompt = Column(Text)
    style_tags = Column(JSON, default=[])
    scene = Column(String(255))
    body_type_suitability = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GeneratedPost(Base):
    __tablename__ = "generated_posts"
    id = Column(Integer, primary_key=True, index=True)
    outfit_id = Column(Integer, ForeignKey("outfits.id"))
    images = Column(JSON, default=[])
    title = Column(String(500))
    content = Column(Text)
    hashtags = Column(JSON, default=[])
    product_tags = Column(JSON, default=[])
    status = Column(String(20), default="draft")  # draft | reviewed | published
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
    source_posts = Column(JSON, default=[])
    fetch_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 6: 创建 app/schemas.py（Pydantic 模型）**

```python
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
    product_ids: list[int]
    description: str
    pos_prompt: str
    neg_prompt: str
    style_tags: list[str]
    scene: str
    body_type_suitability: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: int
    outfit_id: Optional[int]
    images: list[str]
    title: str
    content: str
    hashtags: list[str]
    product_tags: list[dict]
    status: str
    created_at: datetime
    published_at: Optional[datetime]
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
    style: str = ""
    scene: str = ""


class GenerateResponse(BaseModel):
    post: PostOut
    outfit: OutfitOut
    generated_images: list[str]
```

- [ ] **Step 7: 创建 app/main.py（FastAPI 入口）**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import init_db
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="AI 穿搭博主 Agent", version="0.1.0")

# 创建存储目录
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
Path("data").mkdir(exist_ok=True)

# 静态文件
app.mount("/images", StaticFiles(directory=settings.storage_dir), name="images")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: 创建 tests/conftest.py**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient

TEST_DB_URL = "sqlite:///./tests/test.db"


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_db):
    def override_get_db():
        yield setup_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 9: 创建 data/persona.yaml（默认博主）**

```yaml
name: "小鹿学姐"
age_range: "25-30"
body_type: "大码"
size_category: "XL-2XL"
height: "165cm"
style_tags:
  - "法式优雅"
  - "通勤穿搭"
  - "温柔系"
tone_of_voice: "亲切温柔，像闺蜜推荐，常用'姐妹们''绝绝子'"
avatar_desc: "圆脸、温柔杏眼、长发微卷、暖白皮、气质优雅、微笑自然"
content_focus:
  - "大码显瘦穿搭"
  - "微胖女生职场穿搭"
  - "法式氛围感搭配"
avoid_tags:
  - "紧身包臀"
  - "低腰"
  - "横条纹"
```

- [ ] **Step 10: 创建 data/products.csv（初始商品库）**

```csv
name,category,price,brand,size_available,source_url,attributes
"法式碎花连衣裙 大码显瘦",裙装,199,"某品牌","XL-4XL","https://example.com/product/1","{""color"":""碎花蓝"",""fabric"":""雪纺"",""fit"":""A字""}"
"高腰阔腿裤 通勤显高",裤装,159,"某品牌","M-3XL","https://example.com/product/2","{""color"":""黑色"",""fabric"":""西装料"",""fit"":""阔腿""}"
"短款针织开衫 法式温柔",上衣,129,"某品牌","M-2XL","https://example.com/product/3","{""color"":""米白"",""fabric"":""针织"",""fit"":""短款""}"
```

- [ ] **Step 11: 创建 tests/test_models.py**

```python
from app.models import BloggerPersona, Product, Outfit, GeneratedPost, PostPerformance, Trend


def test_create_persona(setup_db):
    persona = BloggerPersona(
        name="测试博主",
        body_type="大码",
        style_tags=["法式", "通勤"],
    )
    setup_db.add(persona)
    setup_db.commit()
    assert persona.id is not None


def test_create_product(setup_db):
    product = Product(
        name="测试连衣裙",
        category="裙装",
        price=199.0,
    )
    setup_db.add(product)
    setup_db.commit()
    assert product.id is not None


def test_create_post_chain(setup_db):
    persona = BloggerPersona(name="测试", body_type="大码")
    setup_db.add(persona)

    product = Product(name="裙子", price=150.0)
    setup_db.add(product)
    setup_db.commit()

    outfit = Outfit(
        product_ids=[product.id],
        description="测试穿搭",
        pos_prompt="test prompt",
    )
    setup_db.add(outfit)
    setup_db.commit()

    post = GeneratedPost(
        outfit_id=outfit.id,
        title="测试标题",
        content="测试内容",
    )
    setup_db.add(post)
    setup_db.commit()

    perf = PostPerformance(post_id=post.id, likes=100)
    setup_db.add(perf)
    setup_db.commit()
    assert perf.likes == 100
```

- [ ] **Step 12: 运行测试验证脚手架**

Run: `pip install -e ".[dev]" && pytest tests/test_models.py -v`
Expected: 3 tests PASS

- [ ] **Step 13: Commit**

```bash
git add -A && git commit -m "feat: 项目脚手架 + 数据模型 + 测试框架"
```

---

### Task 2: LLM Client 封装

**Files:**
- Create: `app/llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: 创建 tests/test_llm_client.py（写失败测试）**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient, LLMResponse


def test_llm_client_initialization():
    client = LLMClient(api_key="test-key", model="gpt-4o")
    assert client.model == "gpt-4o"


def test_llm_response_model():
    resp = LLMResponse(content="test content", model="gpt-4o", tokens_used=100)
    assert resp.content == "test content"
    assert resp.model == "gpt-4o"
    assert resp.tokens_used == 100


@patch("openai.OpenAI")
def test_chat_completion(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"key": "value"}'
    mock_completion.usage.total_tokens = 150
    mock_client.chat.completions.create.return_value = mock_completion

    client = LLMClient(api_key="test-key")
    resp = client.chat(
        system_prompt="You are helpful",
        user_prompt="Hello",
        response_format={"type": "json_object"},
    )

    assert resp.content == '{"key": "value"}'
    assert resp.tokens_used == 150


@patch("openai.OpenAI")
def test_chat_with_error_retry(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_client.chat.completions.create.side_effect = [
        Exception("API Error"),
        Exception("API Error again"),
    ]

    client = LLMClient(api_key="test-key")
    with pytest.raises(RuntimeError, match="LLM call failed after"):
        client.chat(system_prompt="test", user_prompt="test", max_retries=2)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL (ImportError, module not found)

- [ ] **Step 3: 创建 app/llm_client.py**

```python
from dataclasses import dataclass
from openai import OpenAI
from app.config import get_settings


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0


class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.llm_model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> LLMResponse:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        last_error = None
        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                completion = self.client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content or ""
                tokens = completion.usage.total_tokens if completion.usage else 0
                return LLMResponse(content=content, model=self.model, tokens_used=tokens)
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_error}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_llm_client.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/llm_client.py tests/test_llm_client.py && git commit -m "feat: LLM Client 封装 (OpenAI SDK + 重试)"
```

---

### Task 3: Skill 基类

**Files:**
- Create: `app/skills/__init__.py`
- Create: `app/skills/base.py`
- Create: `tests/test_skills/__init__.py`

- [ ] **Step 1: 创建 app/skills/base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from app.llm_client import LLMClient


@dataclass
class SkillResult:
    success: bool
    data: Any = None
    error: str = ""
    metadata: dict = field(default_factory=dict)


class BaseSkill(ABC):
    name: str = "base"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @abstractmethod
    def execute(self, **kwargs) -> SkillResult:
        raise NotImplementedError

    def _llm_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        import json
        resp = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        try:
            return json.loads(resp.content)
        except json.JSONDecodeError:
            return {"raw": resp.content}
```

- [ ] **Step 2: 不单独测试基类（抽象类），保留就位**

- [ ] **Step 3: Commit**

```bash
git add app/skills/ tests/test_skills/ && git commit -m "feat: Skill 基类 BaseSkill"
```

---

### Task 4: TrendRadar Skill（趋势雷达）

**Files:**
- Create: `app/skills/trend_radar.py`
- Create: `app/scraper.py`
- Create: `tests/test_skills/test_trend_radar.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: 创建 tests/test_scraper.py**

```python
from unittest.mock import patch, MagicMock
from app.scraper import fetch_xiaohongshu_trends


def make_mock_soup():
    soup = MagicMock()
    card1 = MagicMock()
    title1 = MagicMock()
    title1.get_text.return_value = "大码法式连衣裙推荐 姐妹们冲"
    card1.select_one.return_value = title1
    soup.select.return_value = [card1, MagicMock()]
    card2 = MagicMock()
    title2 = MagicMock()
    title2.get_text.return_value = "通勤穿搭"
    card2.select_one.return_value = title2
    soup.select.return_value = [card1, card2]
    return soup


@patch("app.scraper.requests.get")
@patch("app.scraper.BeautifulSoup")
def test_fetch_trends_returns_keywords(mock_bs, mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    mock_bs.return_value = make_mock_soup()

    result = fetch_xiaohongshu_trends(keyword="法式穿搭")
    assert len(result) > 0
    assert any("法式" in kw for kw in result)


@patch("app.scraper.requests.get")
def test_fetch_trends_handles_network_error(mock_get):
    import requests
    mock_get.side_effect = requests.ConnectionError("Network error")
    result = fetch_xiaohongshu_trends(keyword="test")
    assert result == []
```

- [ ] **Step 2: 创建 app/scraper.py**

```python
import requests
from bs4 import BeautifulSoup

XHS_SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword="


def fetch_xiaohongshu_trends(keyword: str, max_items: int = 20) -> list[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        resp = requests.get(f"{XHS_SEARCH_URL}{keyword}", headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select(".note-item, .feeds-page .note-item, section.note-item")
        titles = []
        for card in cards[:max_items]:
            title_el = card.select_one(".title, .note-title, a.title span")
            if title_el:
                titles.append(title_el.get_text(strip=True))
        return titles
    except Exception:
        return []


def get_hot_search_keywords() -> list[str]:
    try:
        resp = requests.get(
            "https://www.xiaohongshu.com/web_api/sns/v10/homefeed",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("items", [])
        keywords = []
        for item in items:
            tag = item.get("note_card", {}).get("tag_list", [])
            for t in tag:
                if t.get("name"):
                    keywords.append(t["name"])
        return keywords[:30]
    except Exception:
        return []


def fetch_trends_for_persona(style_tags: list[str]) -> list[str]:
    all_titles = []
    for tag in style_tags[:3]:
        titles = fetch_xiaohongshu_trends(keyword=tag)
        all_titles.extend(titles)
    return list(dict.fromkeys(all_titles))[:50]
```

- [ ] **Step 3: 创建 tests/test_skills/test_trend_radar.py**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.trend_radar import TrendRadar


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_trend_radar_execute_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"keywords":["法式碎花","通勤显瘦"],"style_trends":["法式田园风"],'
        '"hot_items":["碎花连衣裙","阔腿裤"],"trend_summary":"今夏法式通勤风热","hot_scores":[9,8]}',
        model="gpt-4o",
        tokens_used=200,
    )

    with patch("app.skills.trend_radar.fetch_trends_for_persona") as mock_fetch:
        mock_fetch.return_value = ["法式连衣裙 绝绝子", "通勤穿搭 显瘦", "碎花裙 法式"]

        radar = TrendRadar(llm)
        result = radar.execute(style_tags=["法式", "通勤"])

    assert result.success
    data = result.data
    assert len(data["keywords"]) >= 2
    assert "trend_summary" in data


def test_trend_radar_empty_trends():
    llm = make_llm()

    with patch("app.skills.trend_radar.fetch_trends_for_persona") as mock_fetch:
        mock_fetch.return_value = []

        radar = TrendRadar(llm)
        result = radar.execute(style_tags=["稀有标签"])

    assert result.success
    assert result.data["keywords"] == []
```

- [ ] **Step 4: 运行测试确认失败**

Run: `pytest tests/test_skills/test_trend_radar.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 5: 创建 app/skills/trend_radar.py**

```python
from app.skills.base import BaseSkill, SkillResult
from app.scraper import fetch_trends_for_persona

TREND_RADAR_SYSTEM_PROMPT = """你是一个小红书穿搭趋势分析专家。根据提供的热门笔记标题，
分析当前流行的穿搭趋势、热门关键词、热门单品，输出结构化JSON。

输出格式:
{
  "keywords": ["关键词1", "关键词2", ...],      // 5-10个热门穿搭关键词
  "style_trends": ["趋势风格1", ...],            // 3-5个正在流行的风格
  "hot_items": ["热门单品1", ...],               // 5-8个热门单品
  "hot_scores": [9, 8, 7, ...],                 // 对应的热度评分(1-10)
  "trend_summary": "趋势综合描述(100字以内)"
}
"""

USER_PROMPT_TEMPLATE = """请分析以下小红书穿搭内容的趋势:

热门笔记标题:
{titles}

关注的风格标签: {style_tags}

请输出JSON格式的趋势分析结果。"""


class TrendRadar(BaseSkill):
    name = "trend_radar"

    def execute(self, style_tags: list[str] | None = None, **kwargs) -> SkillResult:
        tags = style_tags or kwargs.get("style_tags", ["穿搭", "女装"])
        titles = fetch_trends_for_persona(tags)

        if not titles:
            return SkillResult(
                success=True,
                data={
                    "keywords": [],
                    "style_trends": [],
                    "hot_items": [],
                    "hot_scores": [],
                    "trend_summary": "暂无趋势数据",
                },
            )

        titles_str = "\n".join(f"- {t}" for t in titles[:30])
        user_prompt = USER_PROMPT_TEMPLATE.format(titles=titles_str, style_tags=", ".join(tags))
        result = self._llm_json(TREND_RADAR_SYSTEM_PROMPT, user_prompt)

        return SkillResult(
            success=True,
            data=result,
            metadata={"scraped_count": len(titles)},
        )
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_skills/test_trend_radar.py tests/test_scraper.py -v`
Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/skills/trend_radar.py app/scraper.py tests/test_scraper.py tests/test_skills/test_trend_radar.py
git commit -m "feat: TrendRadar Skill + 小红书爬虫"
```

---

### Task 5: ProductMatcher Skill（商品匹配）

**Files:**
- Create: `app/skills/product_matcher.py`
- Create: `tests/test_skills/test_product_matcher.py`

- [ ] **Step 1: 创建 tests/test_skills/test_product_matcher.py**

```python
from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.product_matcher import ProductMatcher


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_product_matcher_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"product_set":[{"name":"法式碎花裙","category":"裙装","brand":"品牌A",'
        '"reason":"A字版型适合大码","match_score":9}],'
        '"overall_match_score":8.5,"style_match":"法式优雅"}',
        model="gpt-4o",
        tokens_used=200,
    )

    matcher = ProductMatcher(llm)
    result = matcher.execute(
        products=[
            {"id": 1, "name": "法式碎花裙", "category": "裙装", "price": 199, "attributes": {"fit": "A字"}},
            {"id": 2, "name": "紧身包臀裙", "category": "裙装", "price": 159, "attributes": {"fit": "包臀"}},
        ],
        persona={
            "body_type": "大码",
            "style_tags": ["法式", "通勤"],
            "avoid_tags": ["紧身包臀"],
        },
    )

    assert result.success
    assert len(result.data["product_set"]) == 1
    assert "法式碎花裙" in str(result.data)


def test_product_matcher_empty_products():
    llm = make_llm()
    matcher = ProductMatcher(llm)
    result = matcher.execute(products=[], persona={"body_type": "大码", "style_tags": []})
    assert result.success
    assert result.data["product_set"] == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_skills/test_product_matcher.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 app/skills/product_matcher.py**

```python
from app.skills.base import BaseSkill, SkillResult
import json

PRODUCT_MATCHER_SYSTEM_PROMPT = """你是小红书穿搭商品匹配专家。根据博主人设（体型、风格偏好、避雷标签）
和待选商品，为博主挑选最合适的搭配商品组合。

穿搭约束规则:
- 大码体型: 优先A字/直筒/阔腿版型，V领/方领，深色/纯色，避免紧身/横条纹/低腰
- 小个子体型: 优先高腰线设计、短款/九分款、同色系搭配，避免过长/oversized
- 必须遵守博主的避雷标签，不能推荐避雷标签相关的商品

输出格式:
{
  "product_set": [
    {"name": "商品名", "category": "品类", "reason": "推荐理由", "match_score": 8}
  ],
  "overall_match_score": 8.5,
  "style_match": "风格匹配说明"
}
"""


class ProductMatcher(BaseSkill):
    name = "product_matcher"

    def execute(self, products: list[dict] | None = None, persona: dict | None = None, **kwargs) -> SkillResult:
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})

        if not products:
            return SkillResult(success=True, data={"product_set": [], "overall_match_score": 0.0, "style_match": ""})

        products_json = json.dumps(products, ensure_ascii=False, indent=2)
        persona_json = json.dumps(persona, ensure_ascii=False, indent=2)

        user_prompt = f"""请根据以下博主信息匹配最适合的商品:

博主人设:
{persona_json}

待选商品:
{products_json}

请输出JSON格式的匹配结果。"""

        result = self._llm_json(PRODUCT_MATCHER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_skills/test_product_matcher.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/skills/product_matcher.py tests/test_skills/test_product_matcher.py
git commit -m "feat: ProductMatcher Skill"
```

---

### Task 6: OutfitComposer Skill（穿搭合成）

**Files:**
- Create: `app/skills/outfit_composer.py`
- Create: `tests/test_skills/test_outfit_composer.py`

- [ ] **Step 1: 创建 tests/test_skills/test_outfit_composer.py**

```python
from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.outfit_composer import OutfitComposer


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_outfit_composer_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"outfit_desc":"法式碎花连衣裙搭配米白针织开衫，温柔优雅。"
        '"高腰阔腿裤拉长腿部线条，整体显瘦显高。",'
        '"pos_prompt":"一位微胖女性博主，穿着法式碎花A字连衣裙，外搭米白短款针织开衫，'
        '下身黑色高腰阔腿裤，法式咖啡馆背景，柔光自然光线，全身照，小红书OOTD风格，高清写实",'
        '"neg_prompt":"紧身服装，横条纹，低腰设计，面部崩坏，手指畸形，商品变形",'
        '"scene":"法式咖啡馆"}',
        model="gpt-4o",
        tokens_used=300,
    )

    composer = OutfitComposer(llm)
    result = composer.execute(
        product_set=[
            {"name": "法式碎花裙", "category": "裙装"},
            {"name": "米白针织开衫", "category": "上衣"},
            {"name": "高腰阔腿裤", "category": "裤装"},
        ],
        persona={
            "body_type": "大码",
            "height": "165cm",
            "style_tags": ["法式", "通勤"],
            "avatar_desc": "圆脸、温柔杏眼、长发微卷",
        },
        scene="法式咖啡馆",
    )

    assert result.success
    assert len(result.data["outfit_desc"]) > 10
    assert len(result.data["pos_prompt"]) > 20
    assert len(result.data["neg_prompt"]) > 5


def test_outfit_composer_empty_products():
    llm = make_llm()
    composer = OutfitComposer(llm)
    result = composer.execute(product_set=[], persona={})
    assert not result.success
    assert "Empty product set" in result.error
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_skills/test_outfit_composer.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 app/skills/outfit_composer.py**

```python
from app.skills.base import BaseSkill, SkillResult
import json

OUTFIT_COMPOSER_SYSTEM_PROMPT = """你是小红书穿搭搭配专家。根据提供的商品组合和博主人设，
创作完整的穿搭方案，并生成用于AI图片生成的Prompt。

穿搭要求:
- 考虑体型特点，运用显瘦/显高技巧
- 考虑颜色搭配、材质搭配、风格统一
- 描述要具体可生成：包含款式、颜色、材质、搭配细节、场景、光线、构图
- 生图Prompt必须是英文（DALL-E最佳输入语言），穿搭描述用中文

输出格式:
{
  "outfit_desc": "中文穿搭描述，100-200字",
  "pos_prompt": "DALL-E正向生图Prompt，英文，80-150词",
  "neg_prompt": "DALL-E反向Prompt，英文",
  "scene": "场景描述"
}
"""


class OutfitComposer(BaseSkill):
    name = "outfit_composer"

    def execute(
        self,
        product_set: list[dict] | None = None,
        persona: dict | None = None,
        scene: str = "",
        style: str = "",
        **kwargs,
    ) -> SkillResult:
        product_set = product_set or kwargs.get("product_set", [])
        persona = persona or kwargs.get("persona", {})
        scene = scene or kwargs.get("scene", "")

        if not product_set:
            return SkillResult(success=False, error="Empty product set")

        products_json = json.dumps(product_set, ensure_ascii=False, indent=2)
        persona_json = json.dumps(persona, ensure_ascii=False, indent=2)

        user_prompt = f"""请根据以下信息创作穿搭方案:

博主人设:
{persona_json}

搭配商品:
{products_json}

指定场景: {scene or '日常街拍/咖啡馆'}
指定风格: {style or persona_json}

请输出JSON格式的穿搭方案。"""

        result = self._llm_json(OUTFIT_COMPOSER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_skills/test_outfit_composer.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/skills/outfit_composer.py tests/test_skills/test_outfit_composer.py
git commit -m "feat: OutfitComposer Skill"
```

---

### Task 7: ImageGenerator Skill（图片生成）

**Files:**
- Create: `app/skills/image_generator.py`
- Create: `tests/test_skills/test_image_generator.py`

- [ ] **Step 1: 创建 tests/test_skills/test_image_generator.py**

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.llm_client import LLMClient
from app.skills.image_generator import ImageGenerator


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


@patch("app.skills.image_generator.OpenAI")
def test_generate_images_success(mock_openai_class):
    llm = make_llm()
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_image = MagicMock()
    mock_image.url = "https://example.com/fake-image.png"
    mock_response = MagicMock()
    mock_response.data = [mock_image]
    mock_client.images.generate.return_value = mock_response

    with patch("app.skills.image_generator.requests.get") as mock_get:
        mock_img_resp = MagicMock()
        mock_img_resp.raise_for_status = MagicMock()
        mock_img_resp.content = b"fake-image-bytes"
        mock_get.return_value = mock_img_resp

        with patch("app.skills.image_generator.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                generator = ImageGenerator(llm, storage_dir="/tmp/test-images")
                result = generator.execute(
                    pos_prompt="Fashion blogger outfit photo",
                    neg_prompt="bad quality",
                    persona_avatar="圆脸、长发微卷",
                    num_images=2,
                )

    assert result.success
    assert len(result.data["image_paths"]) == 2
    assert result.data["num_generated"] == 2


def test_generate_missing_prompt():
    llm = make_llm()
    generator = ImageGenerator(llm)
    result = generator.execute(pos_prompt="")
    assert not result.success
    assert "Missing pos_prompt" in result.error
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_skills/test_image_generator.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 app/skills/image_generator.py**

```python
import requests
import uuid
from pathlib import Path
from datetime import datetime, timezone
from openai import OpenAI
from app.skills.base import BaseSkill, SkillResult
from app.config import get_settings
from app.llm_client import LLMClient


class ImageGenerator(BaseSkill):
    name = "image_generator"

    def __init__(self, llm_client: LLMClient, storage_dir: str | None = None):
        super().__init__(llm_client)
        self.storage_dir = Path(storage_dir or get_settings().storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        pos_prompt: str = "",
        neg_prompt: str = "",
        persona_avatar: str = "",
        num_images: int = 3,
        **kwargs,
    ) -> SkillResult:
        pos_prompt = pos_prompt or kwargs.get("pos_prompt", "")
        neg_prompt = neg_prompt or kwargs.get("neg_prompt", "")
        persona_avatar = persona_avatar or kwargs.get("persona_avatar", "")
        num_images = min(num_images, int(kwargs.get("num_images", 3)))

        if not pos_prompt:
            return SkillResult(success=False, error="Missing pos_prompt")

        full_prompt = self._build_prompt(pos_prompt, neg_prompt, persona_avatar)

        try:
            image_paths = self._generate_images(full_prompt, num_images)
            return SkillResult(
                success=True,
                data={
                    "image_paths": image_paths,
                    "num_generated": len(image_paths),
                    "prompt_used": full_prompt,
                },
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _build_prompt(self, pos: str, neg: str, avatar: str) -> str:
        prompt = pos
        if avatar:
            prompt = f"Subject: {avatar}. " + prompt
        if neg:
            prompt += f" --no {neg}"
        return prompt

    def _generate_images(self, prompt: str, num: int) -> list[str]:
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        model = settings.image_model

        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=min(num, 3),
            size="1024x1024",
            quality="standard",
        )

        date_dir = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dir_path = self.storage_dir / date_dir
        dir_path.mkdir(parents=True, exist_ok=True)

        paths = []
        for img in response.data:
            if img.url:
                img_data = requests.get(img.url, timeout=30)
                img_data.raise_for_status()
                filename = f"{uuid.uuid4().hex[:12]}.png"
                filepath = dir_path / filename
                filepath.write_bytes(img_data.content)
                paths.append(str(filepath))

        return paths
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_skills/test_image_generator.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/skills/image_generator.py tests/test_skills/test_image_generator.py
git commit -m "feat: ImageGenerator Skill (DALL-E 3)"
```

---

### Task 8: ContentWriter Skill（文案写作）

**Files:**
- Create: `app/skills/content_writer.py`
- Create: `tests/test_skills/test_content_writer.py`

- [ ] **Step 1: 创建 tests/test_skills/test_content_writer.py**

```python
from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.content_writer import ContentWriter


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_content_writer_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"title":"绝绝子！大码姐妹这样穿法式碎花裙 秒变氛围感女神👗",'
        '"content":"姐妹们！今天一定要分享这套法式穿搭\\n\\n'
        '碎花A字连衣裙真的太适合我们微胖女生了，V领设计拉长颈部线条...\\n'
        '搭配高腰阔腿裤，整体比例拉满！",'
        '"hashtags":["大码穿搭","法式穿搭","显瘦穿搭","160斤穿搭","OOTD"],'
        '"product_tags":[{"name":"法式碎花连衣裙","url":"https://example.com/product/1"}]}',
        model="gpt-4o",
        tokens_used=400,
    )

    writer = ContentWriter(llm)
    result = writer.execute(
        outfit_desc="法式碎花连衣裙搭配高腰阔腿裤",
        products=[{"name": "法式碎花连衣裙", "source_url": "https://example.com/product/1"}],
        persona={"tone_of_voice": "亲切温柔，像闺蜜推荐", "body_type": "大码"},
    )

    assert result.success
    assert len(result.data["title"]) > 5
    assert len(result.data["hashtags"]) >= 3
    assert len(result.data["product_tags"]) >= 1


def test_content_writer_empty_outfit():
    llm = make_llm()
    writer = ContentWriter(llm)
    result = writer.execute(outfit_desc="", products=[], persona={})
    assert not result.success
    assert "Empty outfit" in result.error
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_skills/test_content_writer.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 app/skills/content_writer.py**

```python
import json
from app.skills.base import BaseSkill, SkillResult

CONTENT_WRITER_SYSTEM_PROMPT = """你是小红书穿搭爆款文案写手。根据穿搭描述和商品信息，
生成一篇吸引人的小红书穿搭笔记。

文案要求:
- 标题: 15-25字，包含emoji，制造好奇心或实用价值感
- 正文: 150-300字，口语化、亲切感，像闺蜜推荐
- 分段清晰，每段2-3句，多用emoji点缀
- 高频词: 姐妹们/绝绝子/冲/闭眼入/氛围感/谁穿谁好看
- 大码博主强调"显瘦""自信""微胖友好"
- 小个子博主强调"显高""拉长比例""小个子福音"
- 话题标签: 5-8个，包含体型标签+风格标签+泛流量标签

输出格式:
{
  "title": "标题",
  "content": "正文",
  "hashtags": ["标签1", "标签2", ...],
  "product_tags": [{"name": "商品名", "url": "商品链接"}]
}
"""


class ContentWriter(BaseSkill):
    name = "content_writer"

    def execute(
        self,
        outfit_desc: str = "",
        products: list[dict] | None = None,
        persona: dict | None = None,
        **kwargs,
    ) -> SkillResult:
        outfit_desc = outfit_desc or kwargs.get("outfit_desc", "")
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})

        if not outfit_desc:
            return SkillResult(success=False, error="Empty outfit description")

        user_prompt = f"""请根据以下信息生成一篇小红书穿搭笔记:

博主口吻: {persona.get('tone_of_voice', '亲切自然')}
博主体型: {persona.get('body_type', '标准')}

穿搭描述:
{outfit_desc}

关联商品:
{json.dumps(products, ensure_ascii=False, indent=2)}

请输出JSON格式的小红书笔记内容。"""

        result = self._llm_json(CONTENT_WRITER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_skills/test_content_writer.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/skills/content_writer.py tests/test_skills/test_content_writer.py
git commit -m "feat: ContentWriter Skill"
```

---

### Task 9: PerformanceTracker Skill（数据追踪）

**Files:**
- Create: `app/skills/performance_tracker.py`
- Create: `tests/test_skills/test_performance_tracker.py`

- [ ] **Step 1: 创建 tests/test_skills/test_performance_tracker.py**

```python
from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.performance_tracker import PerformanceTracker


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_analyze_performance_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"performance_summary":"本周3篇笔记，平均互动率3.2%",'
        '"best_style":"法式通勤风互动率最高(4.5%)",'
        '"best_time":"周五晚8点互动峰值",'
        '"optimization_suggestions":["增加通勤主题","尝试晚上8点发布","减少碎花元素比重"],'
        '"metrics_trend":"up"}',
        model="gpt-4o",
        tokens_used=250,
    )

    tracker = PerformanceTracker(llm)
    result = tracker.execute(
        performances=[
            {"likes": 120, "comments": 15, "shares": 8, "click_rate": 0.032},
            {"likes": 85, "comments": 10, "shares": 5, "click_rate": 0.025},
        ],
        posts_metadata=[
            {"title": "法式通勤", "style_tags": ["法式", "通勤"]},
            {"title": "碎花穿搭", "style_tags": ["碎花", "田园"]},
        ],
    )

    assert result.success
    assert "performance_summary" in result.data
    assert len(result.data["optimization_suggestions"]) > 0


def test_analyze_empty_performance():
    llm = make_llm()
    tracker = PerformanceTracker(llm)
    result = tracker.execute(performances=[], posts_metadata=[])
    assert result.success
    assert "暂无数据" in result.data["performance_summary"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_skills/test_performance_tracker.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 app/skills/performance_tracker.py**

```python
import json
from app.skills.base import BaseSkill, SkillResult

PERFORMANCE_TRACKER_SYSTEM_PROMPT = """你是小红书内容数据分析师。根据给出的笔记效果数据，
分析内容表现，并给出优化建议。

输出格式:
{
  "performance_summary": "总体表现总结(100字以内)",
  "best_style": "表现最好的风格/话题",
  "best_time": "建议最佳发布时间",
  "optimization_suggestions": ["建议1", "建议2", ...],
  "metrics_trend": "up|stable|down"
}
"""


class PerformanceTracker(BaseSkill):
    name = "performance_tracker"

    def execute(
        self,
        performances: list[dict] | None = None,
        posts_metadata: list[dict] | None = None,
        **kwargs,
    ) -> SkillResult:
        performances = performances or kwargs.get("performances", [])
        posts_metadata = posts_metadata or kwargs.get("posts_metadata", [])

        if not performances:
            return SkillResult(
                success=True,
                data={
                    "performance_summary": "暂无数据",
                    "best_style": "",
                    "best_time": "",
                    "optimization_suggestions": ["积累更多发布数据后再分析"],
                    "metrics_trend": "stable",
                },
            )

        perf_json = json.dumps(performances, ensure_ascii=False, indent=2)
        meta_json = json.dumps(posts_metadata, ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下穿搭笔记的效果数据:

笔记效果数据:
{perf_json}

笔记元信息:
{meta_json}

请输出JSON格式的分析结果。"""

        result = self._llm_json(PERFORMANCE_TRACKER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_skills/test_performance_tracker.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/skills/performance_tracker.py tests/test_skills/test_performance_tracker.py
git commit -m "feat: PerformanceTracker Skill"
```

---

### Task 10: Pipeline 流程编排

**Files:**
- Create: `app/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: 创建 tests/test_pipeline.py**

```python
import pytest
from unittest.mock import MagicMock, patch
from app.llm_client import LLMClient
from app.skills.base import SkillResult
from app.pipeline import GenerationPipeline
from app.models import BloggerPersona, Product


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


@patch("app.pipeline.get_db")
def test_pipeline_full_flow_success(mock_get_db, setup_db):
    mock_get_db.return_value = iter([setup_db])

    # 准备测试数据
    persona = BloggerPersona(name="测试博主", body_type="大码", style_tags=["法式"])
    setup_db.add(persona)

    product = Product(name="测试连衣裙", category="裙装", price=199.0)
    setup_db.add(product)
    setup_db.commit()

    llm = make_llm()
    pipeline = GenerationPipeline(llm_client=llm)

    # 测试参数验证
    with patch.object(pipeline.product_matcher, "execute") as mock_match:
        mock_match.return_value = SkillResult(
            success=True,
            data={
                "product_set": [{"name": "测试裙", "match_score": 9}],
                "overall_match_score": 9.0,
                "style_match": "法式",
            },
        )

        with patch.object(pipeline.outfit_composer, "execute") as mock_outfit:
            mock_outfit.return_value = SkillResult(
                success=True,
                data={
                    "outfit_desc": "测试穿搭描述",
                    "pos_prompt": "test prompt",
                    "neg_prompt": "bad stuff",
                    "scene": "街拍",
                },
            )

            with patch.object(pipeline.image_generator, "execute") as mock_img:
                mock_img.return_value = SkillResult(
                    success=True,
                    data={
                        "image_paths": ["/tmp/img1.png", "/tmp/img2.png"],
                        "num_generated": 2,
                    },
                )

                with patch.object(pipeline.content_writer, "execute") as mock_write:
                    mock_write.return_value = SkillResult(
                        success=True,
                        data={
                            "title": "测试标题",
                            "content": "测试正文",
                            "hashtags": ["大码穿搭", "法式"],
                            "product_tags": [{"name": "测试裙", "url": ""}],
                        },
                    )

                    result = pipeline.run(persona_id=persona.id)

    assert result is not None
    assert "post" in result
    assert "outfit" in result
    assert "images" in result
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 app/pipeline.py**

```python
from app.llm_client import LLMClient
from app.skills.trend_radar import TrendRadar
from app.skills.product_matcher import ProductMatcher
from app.skills.outfit_composer import OutfitComposer
from app.skills.image_generator import ImageGenerator
from app.skills.content_writer import ContentWriter
from app.skills.performance_tracker import PerformanceTracker
from app.models import BloggerPersona, Product, Outfit, GeneratedPost
from app.database import get_db


class GenerationPipeline:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()
        self.trend_radar = TrendRadar(self.llm)
        self.product_matcher = ProductMatcher(self.llm)
        self.outfit_composer = OutfitComposer(self.llm)
        self.image_generator = ImageGenerator(self.llm)
        self.content_writer = ContentWriter(self.llm)
        self.performance_tracker = PerformanceTracker(self.llm)

    def run(
        self,
        persona_id: int = 1,
        product_ids: list[int] | None = None,
        style: str = "",
        scene: str = "",
    ) -> dict:
        db = next(get_db())

        # 1. 获取博主人设
        persona = db.query(BloggerPersona).filter(BloggerPersona.id == persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        persona_dict = self._persona_to_dict(persona)

        # 2. 获取商品列表
        if product_ids:
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        else:
            products = db.query(Product).all()

        products_list = [self._product_to_dict(p) for p in products]

        # 3. ProductMatcher: 匹配商品
        match_result = self.product_matcher.execute(products=products_list, persona=persona_dict)
        if not match_result.success:
            raise RuntimeError(f"ProductMatcher failed: {match_result.error}")

        matched_products = match_result.data.get("product_set", [])

        # 4. OutfitComposer: 穿搭合成
        outfit_result = self.outfit_composer.execute(
            product_set=matched_products,
            persona=persona_dict,
            scene=scene,
            style=style,
        )
        if not outfit_result.success:
            raise RuntimeError(f"OutfitComposer failed: {outfit_result.error}")

        # 5. 保存穿搭方案
        outfit = Outfit(
            product_ids=[p.get("id", 0) for p in matched_products],
            description=outfit_result.data.get("outfit_desc", ""),
            pos_prompt=outfit_result.data.get("pos_prompt", ""),
            neg_prompt=outfit_result.data.get("neg_prompt", ""),
            style_tags=persona.style_tags,
            scene=outfit_result.data.get("scene", scene),
            body_type_suitability=persona.body_type,
        )
        db.add(outfit)
        db.commit()
        db.refresh(outfit)

        # 6. ImageGenerator: 生成图片
        img_result = self.image_generator.execute(
            pos_prompt=outfit_result.data.get("pos_prompt", ""),
            neg_prompt=outfit_result.data.get("neg_prompt", ""),
            persona_avatar=persona.avatar_desc or "",
            num_images=3,
        )
        if not img_result.success:
            raise RuntimeError(f"ImageGenerator failed: {img_result.error}")

        image_paths = img_result.data.get("image_paths", [])

        # 7. ContentWriter: 写文案
        content_result = self.content_writer.execute(
            outfit_desc=outfit_result.data.get("outfit_desc", ""),
            products=matched_products,
            persona=persona_dict,
        )
        if not content_result.success:
            raise RuntimeError(f"ContentWriter failed: {content_result.error}")

        # 8. 保存生成内容
        post = GeneratedPost(
            outfit_id=outfit.id,
            images=image_paths,
            title=content_result.data.get("title", ""),
            content=content_result.data.get("content", ""),
            hashtags=content_result.data.get("hashtags", []),
            product_tags=content_result.data.get("product_tags", []),
            status="draft",
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        return {
            "post": self._post_to_dict(post),
            "outfit": self._outfit_to_dict(outfit),
            "images": image_paths,
        }

    def _persona_to_dict(self, persona: BloggerPersona) -> dict:
        return {
            "id": persona.id,
            "name": persona.name,
            "body_type": persona.body_type,
            "style_tags": persona.style_tags or [],
            "tone_of_voice": persona.tone_of_voice or "",
            "avatar_desc": persona.avatar_desc or "",
            "avoid_tags": persona.avoid_tags or [],
            "height": persona.height or "",
        }

    def _product_to_dict(self, product: Product) -> dict:
        return {
            "id": product.id,
            "name": product.name,
            "category": product.category or "",
            "price": product.price or 0,
            "brand": product.brand or "",
            "source_url": product.source_url or "",
            "attributes": product.attributes or {},
        }

    def _post_to_dict(self, post: GeneratedPost) -> dict:
        return {
            "id": post.id,
            "outfit_id": post.outfit_id,
            "images": post.images,
            "title": post.title,
            "content": post.content,
            "hashtags": post.hashtags,
            "product_tags": post.product_tags,
            "status": post.status,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }

    def _outfit_to_dict(self, outfit: Outfit) -> dict:
        return {
            "id": outfit.id,
            "description": outfit.description,
            "pos_prompt": outfit.pos_prompt,
            "neg_prompt": outfit.neg_prompt,
            "style_tags": outfit.style_tags,
            "scene": outfit.scene,
        }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_pipeline.py -v`
Expected: 1 test PASS

- [ ] **Step 5: Commit**

```bash
git add app/pipeline.py tests/test_pipeline.py && git commit -m "feat: Pipeline 流程编排"
```

---

### Task 11: API 路由

**Files:**
- Create: `app/routes/__init__.py`
- Create: `app/routes/generate.py`
- Create: `app/routes/posts.py`
- Create: `app/routes/trends.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: 创建 tests/test_routes.py**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.models import BloggerPersona, Product, GeneratedPost, Outfit
from app.main import app


def seed_persona(db):
    p = BloggerPersona(name="测试博主", body_type="大码", style_tags=["法式"])
    db.add(p)
    db.commit()
    return p


def seed_product(db):
    prod = Product(name="测试连衣裙", category="裙装", price=199.0)
    db.add(prod)
    db.commit()
    return prod


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_post(client, setup_db):
    seed_persona(setup_db)
    seed_product(setup_db)

    with patch("app.routes.generate.GenerationPipeline") as mock_pipeline_class:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = {
            "post": {"id": 1, "title": "测试", "status": "draft"},
            "outfit": {"id": 1, "description": "测试"},
            "images": ["/tmp/test.png"],
        }
        mock_pipeline_class.return_value = mock_pipeline

        response = client.post("/api/generate", json={"persona_id": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["post"]["title"] == "测试"


def test_list_posts(client, setup_db):
    seed_persona(setup_db)

    outfit = Outfit(description="测试穿搭", pos_prompt="test")
    setup_db.add(outfit)
    setup_db.commit()

    post = GeneratedPost(
        outfit_id=outfit.id,
        title="测试帖子",
        content="测试内容",
        status="draft",
    )
    setup_db.add(post)
    setup_db.commit()

    response = client.get("/api/posts")
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) >= 1
    assert posts[0]["title"] == "测试帖子"


def test_update_post_status(client, setup_db):
    seed_persona(setup_db)

    outfit = Outfit(description="测试穿搭", pos_prompt="test")
    setup_db.add(outfit)
    setup_db.commit()

    post = GeneratedPost(outfit_id=outfit.id, title="待审核", content="内容", status="draft")
    setup_db.add(post)
    setup_db.commit()

    response = client.patch(f"/api/posts/{post.id}", json={"status": "reviewed"})
    assert response.status_code == 200
    assert response.json()["status"] == "reviewed"


def test_get_trends(client):
    response = client.get("/api/trends")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_routes.py -v`
Expected: FAIL (routes not registered)

- [ ] **Step 3: 创建 app/routes/generate.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import GenerateRequest, GenerateResponse, PostOut, OutfitOut
from app.pipeline import GenerationPipeline

router = APIRouter(prefix="/api", tags=["generate"])
pipeline = GenerationPipeline()


@router.post("/generate", response_model=GenerateResponse)
def generate_post(req: GenerateRequest, db: Session = Depends(get_db)):
    result = pipeline.run(
        persona_id=req.persona_id,
        product_ids=req.product_ids,
        style=req.style,
        scene=req.scene,
    )
    return GenerateResponse(
        post=PostOut(**result["post"]),
        outfit=OutfitOut(**result["outfit"]),
        generated_images=result["images"],
    )
```

- [ ] **Step 4: 创建 app/routes/posts.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import GeneratedPost
from app.schemas import PostOut, PostUpdate

router = APIRouter(prefix="/api", tags=["posts"])


@router.get("/posts", response_model=list[PostOut])
def list_posts(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(GeneratedPost).order_by(GeneratedPost.created_at.desc())
    if status:
        query = query.filter(GeneratedPost.status == status)
    return query.all()


@router.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, update: PostUpdate, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if update.status is not None:
        post.status = update.status
    if update.title is not None:
        post.title = update.title
    if update.content is not None:
        post.content = update.content

    db.commit()
    db.refresh(post)
    return post
```

- [ ] **Step 5: 创建 app/routes/trends.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Trend
from app.schemas import TrendOut

router = APIRouter(prefix="/api", tags=["trends"])


@router.get("/trends", response_model=list[TrendOut])
def list_trends(db: Session = Depends(get_db)):
    return db.query(Trend).order_by(Trend.fetch_date.desc()).limit(50).all()
```

- [ ] **Step 6: 在 app/main.py 注册路由**

```python
# 在文件的 import 区域添加:
from app.routes import generate, posts, trends

# 在 app = FastAPI(...) 之后添加:
app.include_router(generate.router)
app.include_router(posts.router)
app.include_router(trends.router)
```

- [ ] **Step 7: 运行测试确认通过**

Run: `pytest tests/test_routes.py -v`
Expected: 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add app/routes/ app/main.py tests/test_routes.py
git commit -m "feat: API路由 (generate + posts + trends)"
```

---

### Task 12: 管理后台页面（Jinja2 模板）

**Files:**
- Create: `app/templates/base.html`
- Create: `app/templates/index.html`
- Create: `app/templates/post_detail.html`
- Create: `app/templates/trends.html`
- Modify: `app/main.py`

- [ ] **Step 1: 创建 app/templates/base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 穿搭博主 Agent - {% block title %}管理后台{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        nav { background: #ff2442; color: white; padding: 16px 24px; display: flex; gap: 24px; align-items: center; }
        nav a { color: white; text-decoration: none; font-weight: 500; }
        nav a:hover { text-decoration: underline; }
        nav .brand { font-size: 18px; font-weight: 700; margin-right: 16px; }
        .container { max-width: 1200px; margin: 24px auto; padding: 0 24px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .btn { display: inline-block; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #ff2442; color: white; }
        .btn-success { background: #07c160; color: white; }
        .btn-warning { background: #ff976a; color: white; }
        .btn-danger { background: #ee0a24; color: white; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
        .badge-draft { background: #ffd666; color: #ad6800; }
        .badge-reviewed { background: #87d068; color: #135200; }
        .badge-published { background: #07c160; color: white; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; font-weight: 600; }
        img.thumb { width: 80px; height: 80px; object-fit: cover; border-radius: 4px; }
        .image-gallery { display: flex; gap: 12px; flex-wrap: wrap; }
        .image-gallery img { width: 300px; border-radius: 8px; }
        textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        input[type="text"] { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
    </style>
</head>
<body>
    <nav>
        <span class="brand">AI 穿搭博主 Agent</span>
        <a href="/">内容列表</a>
        <a href="/trends">趋势数据</a>
        <a href="/health">健康检查</a>
    </nav>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

- [ ] **Step 2: 创建 app/templates/index.html**

```html
{% extends "base.html" %}
{% block title %}内容列表{% endblock %}
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h1>内容管理</h1>
    <button class="btn btn-primary" onclick="document.getElementById('generate-form').style.display='block'">
        手动生成新内容
    </button>
</div>

<div id="generate-form" class="card" style="display: none;">
    <h2 style="margin-bottom: 12px;">生成新穿搭内容</h2>
    <form action="/api/generate" method="POST" id="gen-form">
        <div style="margin-bottom: 12px;">
            <label>博主ID: <input type="number" name="persona_id" value="1" style="width: 100px;"></label>
        </div>
        <div style="margin-bottom: 12px;">
            <label>风格 (可选): <input type="text" name="style" placeholder="法式/通勤/韩系"></label>
        </div>
        <div style="margin-bottom: 12px;">
            <label>场景 (可选): <input type="text" name="scene" placeholder="咖啡馆/街拍/办公室"></label>
        </div>
        <button type="submit" class="btn btn-success">开始生成</button>
        <button type="button" class="btn" onclick="document.getElementById('generate-form').style.display='none'">取消</button>
    </form>
</div>

<h2 style="margin: 20px 0 12px;">生成记录</h2>
<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>标题</th>
            <th>状态</th>
            <th>图片</th>
            <th>创建时间</th>
            <th>操作</th>
        </tr>
    </thead>
    <tbody>
        {% if posts %}
            {% for post in posts %}
            <tr>
                <td>{{ post.id }}</td>
                <td>{{ post.title[:30] }}{% if post.title|length > 30 %}...{% endif %}</td>
                <td><span class="badge badge-{{ post.status }}">{{ post.status }}</span></td>
                <td>{{ (post.images or [])|length }} 张</td>
                <td>{{ post.created_at[:19] if post.created_at }}</td>
                <td>
                    <a href="/post/{{ post.id }}" class="btn btn-primary" style="font-size:12px; padding:4px 8px;">查看</a>
                </td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="6" style="text-align:center; color:#999;">暂无生成内容</td></tr>
        {% endif %}
    </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: 创建 app/templates/post_detail.html**

```html
{% extends "base.html" %}
{% block title %}{{ post.title }}{% endblock %}
{% block content %}
<h1>{{ post.title }}</h1>
<div style="margin: 8px 0; color: #999;">
    状态: <span class="badge badge-{{ post.status }}">{{ post.status }}</span>
    创建时间: {{ post.created_at[:19] if post.created_at }}
</div>

{% if post.images %}
<div class="card">
    <h3>生成图片</h3>
    <div class="image-gallery">
        {% for img in post.images %}
            <img src="/images/{{ img.split('/')[-2] }}/{{ img.split('/')[-1] }}" alt="穿搭图">
        {% endfor %}
    </div>
</div>
{% endif %}

<div class="card">
    <h3>正文</h3>
    <p style="white-space: pre-wrap; line-height: 1.8;">{{ post.content }}</p>
</div>

<div class="card">
    <h3>话题标签</h3>
    <p>{% for tag in (post.hashtags or []) %}<span style="margin-right:8px; color:#ff2442;">#{{ tag }}</span>{% endfor %}</p>
</div>

{% if post.product_tags %}
<div class="card">
    <h3>商品标记</h3>
    <ul>
    {% for pt in post.product_tags %}
        <li><a href="{{ pt.url }}" target="_blank">{{ pt.name }}</a></li>
    {% endfor %}
    </ul>
</div>
{% endif %}

{% if post.outfit %}
<div class="card">
    <h3>穿搭方案</h3>
    <p>{{ post.outfit.description }}</p>
</div>
{% endif %}

<div class="card">
    <h3>操作</h3>
    <form id="status-form" style="display: inline-block;">
        <input type="hidden" id="post-id" value="{{ post.id }}">
        <button type="button" class="btn btn-success" onclick="updateStatus('reviewed')">审核通过</button>
        <button type="button" class="btn btn-warning" onclick="updateStatus('draft')">打回草稿</button>
        <button type="button" class="btn btn-danger" onclick="updateStatus('published')">标记已发布</button>
    </form>
</div>

<script>
async function updateStatus(status) {
    const postId = document.getElementById('post-id').value;
    const resp = await fetch(`/api/posts/${postId}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: status})
    });
    if (resp.ok) location.reload();
    else alert('操作失败');
}
</script>
{% endblock %}
```

- [ ] **Step 4: 创建 app/templates/trends.html**

```html
{% extends "base.html" %}
{% block title %}趋势数据{% endblock %}
{% block content %}
<h1>趋势数据</h1>
<table>
    <thead>
        <tr>
            <th>关键词</th>
            <th>品类</th>
            <th>热度</th>
            <th>获取时间</th>
        </tr>
    </thead>
    <tbody>
        {% if trends %}
            {% for t in trends %}
            <tr>
                <td>{{ t.keyword }}</td>
                <td>{{ t.category }}</td>
                <td>{{ t.hot_score }}</td>
                <td>{{ t.fetch_date[:19] if t.fetch_date }}</td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="4" style="text-align:center; color:#999;">暂无趋势数据</td></tr>
        {% endif %}
    </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: 在 app/main.py 添加页面路由**

```python
# 在 import 区域添加:
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.models import GeneratedPost, Trend

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db=Depends(get_db)):
    posts = db.query(GeneratedPost).order_by(GeneratedPost.created_at.desc()).all()
    return templates.TemplateResponse("index.html", {"request": request, "posts": posts})


@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_detail(post_id: int, request: Request, db=Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        return HTMLResponse("Post not found", status_code=404)
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post})


@app.get("/trends", response_class=HTMLResponse)
def trends_page(request: Request, db=Depends(get_db)):
    trends_data = db.query(Trend).order_by(Trend.fetch_date.desc()).limit(50).all()
    return templates.TemplateResponse("trends.html", {"request": request, "trends": trends_data})
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/ app/main.py && git commit -m "feat: Jinja2管理后台页面"
```

---

### Task 13: Docker 部署

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `README.md`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./
RUN uv pip install --system -e "."

COPY . .

RUN mkdir -p /app/data /app/storage/images

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./storage:/app/storage
      - ./.env:/app/.env
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.openai.com/v1}
      - LLM_MODEL=${LLM_MODEL:-gpt-4o}
      - IMAGE_MODEL=${IMAGE_MODEL:-dall-e-3}
    restart: unless-stopped
```

- [ ] **Step 3: 创建 README.md**

```markdown
# AI 穿搭博主 Agent

小红书 AI 虚拟穿搭博主，自动生成穿搭图文内容。

## 快速启动

1. 复制环境配置：
   ```bash
   cp .env.example .env
   # 编辑 .env 填入你的 OPENAI_API_KEY
   ```

2. Docker 启动：
   ```bash
   docker compose up -d
   ```

3. 访问管理后台: http://localhost:8000

## 初始化数据

```bash
# 导入默认博主
python scripts/seed.py
```

## API 文档

启动后访问 http://localhost:8000/docs (Swagger UI)

## 项目结构

```
xiaohongshu-agent/
├── app/
│   ├── skills/        # 6个Skill模块
│   ├── routes/        # API路由
│   ├── templates/     # 管理后台页面
│   ├── pipeline.py    # 流程编排
│   └── main.py        # 入口
├── tests/
├── data/              # 商品库+博主人设
├── storage/images/    # 生成的图片
└── docker-compose.yml
```
```

- [ ] **Step 4: 创建 scripts/seed.py（数据初始化脚本）**

```python
"""初始化数据库种子数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import csv
import json
from app.database import init_db, SessionLocal
from app.models import BloggerPersona, Product


def seed_persona():
    db = SessionLocal()
    try:
        with open("data/persona.yaml", "r") as f:
            data = yaml.safe_load(f)
        existing = db.query(BloggerPersona).filter(BloggerPersona.name == data["name"]).first()
        if existing:
            print(f"博主 [{data['name']}] 已存在，跳过")
            return
        persona = BloggerPersona(**data)
        db.add(persona)
        db.commit()
        print(f"博主 [{data['name']}] 导入成功")
    finally:
        db.close()


def seed_products():
    db = SessionLocal()
    try:
        with open("data/products.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing = db.query(Product).filter(Product.name == row["name"]).first()
                if existing:
                    continue
                product = Product(
                    name=row["name"],
                    category=row.get("category", ""),
                    price=float(row.get("price", 0)),
                    brand=row.get("brand", ""),
                    size_available=row.get("size_available", ""),
                    source_url=row.get("source_url", ""),
                    attributes=json.loads(row.get("attributes", "{}")),
                    images=json.loads(row.get("images", "[]")),
                )
                db.add(product)
            db.commit()
            print("商品库导入成功")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_persona()
    seed_products()
    print("种子数据初始化完成")
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml README.md scripts/ && git commit -m "feat: Docker部署 + README + 数据初始化"
```

---

### Task 14: 集成测试与联调

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 创建 tests/test_integration.py**

```python
"""集成测试：验证全链路生成流程（使用mock LLM）"""
import pytest
from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.models import BloggerPersona, Product
from app.pipeline import GenerationPipeline
from app.database import init_db


def seed_persona(db):
    p = BloggerPersona(
        name="小鹿学姐",
        body_type="大码",
        size_category="XL-2XL",
        style_tags=["法式", "通勤"],
        tone_of_voice="亲切温柔",
        avatar_desc="圆脸、温柔杏眼、长发微卷",
        avoid_tags=["紧身"],
    )
    db.add(p)
    db.commit()
    return p


def seed_products(db):
    products = [
        Product(name="法式碎花A字连衣裙", category="裙装", price=199.0, brand="品牌A", attributes={"fit": "A字", "color": "碎花蓝"}),
        Product(name="高腰阔腿西裤", category="裤装", price=159.0, brand="品牌B", attributes={"fit": "阔腿", "color": "黑色"}),
        Product(name="米白短款针织开衫", category="上衣", price=129.0, brand="品牌C", attributes={"fit": "短款", "color": "米白"}),
    ]
    for p in products:
        db.add(p)
    db.commit()
    return products


@patch("app.pipeline.get_db")
def test_full_pipeline_integration(mock_get_db, setup_db):
    """全链路集成测试：从商品 -> 穿搭 -> 图片 -> 文案"""
    mock_get_db.return_value = iter([setup_db])

    persona = seed_persona(setup_db)
    products = seed_products(setup_db)

    llm = MagicMock(spec=LLMClient)
    llm.model = "gpt-4o"

    call_count = 0

    def mock_chat(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # ProductMatcher
            return LLMResponse(content='{"product_set":[{"id":%d,"name":"%s","category":"%s","reason":"A字版型适合大码","match_score":9}],"overall_match_score":9.0,"style_match":"法式优雅"}' % (products[0].id, products[0].name, products[0].category), model="gpt-4o", tokens_used=200)
        elif call_count == 2:  # OutfitComposer
            return LLMResponse(content='{"outfit_desc":"法式碎花A字连衣裙搭配米白针织开衫和高腰阔腿裤，整体温柔大方。A字版型完美遮肉。","pos_prompt":"A plus-size woman wearing French floral dress, white cardigan, black wide-leg pants, coffee shop, soft light, full body shot","neg_prompt":"tight fit, horizontal stripes","scene":"法式咖啡馆"}', model="gpt-4o", tokens_used=300)
        return LLMResponse(content='{}', model="gpt-4o", tokens_used=100)

    llm.chat = mock_chat

    with patch.object(llm, 'chat', mock_chat):
        pipeline = GenerationPipeline(llm_client=llm)

        # Mock ImageGenerator 避免真实API调用
        with patch.object(pipeline.image_generator, 'execute') as mock_img:
            mock_img.return_value = MagicMock(
                success=True,
                data={"image_paths": ["/tmp/img1.png", "/tmp/img2.png"], "num_generated": 2},
            )

            # Mock ContentWriter
            with patch.object(pipeline.content_writer, 'execute') as mock_write:
                mock_write.return_value = MagicMock(
                    success=True,
                    data={
                        "title": "绝绝子！大码姐妹的法式穿搭 氛围感拉满",
                        "content": "姐妹们！这套法式穿搭真的太适合我们微胖女生了...",
                        "hashtags": ["大码穿搭", "法式穿搭", "显瘦穿搭"],
                        "product_tags": [{"name": products[0].name, "url": products[0].source_url or ""}],
                    },
                )

                result = pipeline.run(persona_id=persona.id)

    assert result is not None
    assert "post" in result
    assert result["post"]["title"] is not None
    assert len(result["images"]) == 2
    assert "outfit" in result
    assert result["outfit"]["description"] is not None
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/test_integration.py -v`
Expected: 1 test PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py && git commit -m "test: 全链路集成测试"
```

---

## 附录：环境变量清单汇总

```
OPENAI_API_KEY=sk-xxxxx          # 必填
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，兼容其他API
LLM_MODEL=gpt-4o                  # LLM模型
IMAGE_MODEL=dall-e-3              # 生图模型
DATABASE_URL=sqlite:///./data/agent.db
STORAGE_DIR=./storage/images
```

## 附录：pip install 命令

```bash
pip install -e ".[dev]"
```

## 附录：数据初始化命令

```bash
python scripts/seed.py
```
