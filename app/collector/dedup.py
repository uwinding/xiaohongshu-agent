from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.collector.models import CollectorNote


def is_duplicate(note_id: str, content_hash: str = "", db: Optional[Session] = None) -> bool:
    _close = False
    if db is None:
        db = SessionLocal()
        _close = True
    try:
        existing = db.query(CollectorNote).filter(
            CollectorNote.note_id == note_id
        ).first()
        if existing:
            return True
        if content_hash:
            hash_exists = db.query(CollectorNote).filter(
                CollectorNote.content_hash == content_hash
            ).first()
            if hash_exists:
                return True
        return False
    finally:
        if _close:
            db.close()
