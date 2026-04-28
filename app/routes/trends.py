from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Trend
from app.schemas import TrendOut

router = APIRouter(prefix="/api", tags=["trends"])


@router.get("/trends", response_model=list[TrendOut])
def list_trends(db: Session = Depends(get_db)):
    return db.query(Trend).order_by(Trend.fetch_date.desc()).limit(50).all()
