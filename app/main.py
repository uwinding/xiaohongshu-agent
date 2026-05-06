from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import init_db, get_db
from app.config import get_settings
from app.models import GeneratedPost, Trend
from app.routes import generate, posts, trends
from fastapi import Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    init_db()
    yield


app = FastAPI(title="AI 穿搭博主 Agent", version="0.1.0", lifespan=lifespan)

app.include_router(generate.router)
app.include_router(posts.router)
app.include_router(trends.router)

app.mount("/images", StaticFiles(directory=settings.storage_dir), name="images")

from app.schemas import PostOut, TrendOut

templates = Jinja2Templates(directory="app/templates")
templates.env.cache = None


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db=Depends(get_db)):
    posts = db.query(GeneratedPost).order_by(GeneratedPost.created_at.desc()).all()
    posts_out = [PostOut.model_validate(p).model_dump(mode='json') for p in posts]
    return templates.TemplateResponse(request=request, name="index.html", context={"posts": posts_out})


@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_detail(post_id: int, request: Request, db=Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        return HTMLResponse("Post not found", status_code=404)
    post_out = PostOut.model_validate(post).model_dump(mode='json')
    return templates.TemplateResponse(request=request, name="post_detail.html", context={"post": post_out})


@app.get("/trends", response_class=HTMLResponse)
def trends_page(request: Request, db=Depends(get_db)):
    trends_data = db.query(Trend).order_by(Trend.fetch_date.desc()).limit(50).all()
    trends_out = [TrendOut.model_validate(t).model_dump(mode='json') for t in trends_data]
    return templates.TemplateResponse(request=request, name="trends.html", context={"trends": trends_out})


@app.get("/health")
def health():
    return {"status": "ok"}
