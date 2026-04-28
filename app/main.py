from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import init_db
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="AI 穿搭博主 Agent", version="0.1.0")

Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
Path("data").mkdir(exist_ok=True)

app.mount("/images", StaticFiles(directory=settings.storage_dir), name="images")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
