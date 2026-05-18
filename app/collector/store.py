import csv
import json
import os
from datetime import datetime, timezone
from typing import List

from app.database import SessionLocal
from app.collector.models import CollectorTask, CollectorNote, CollectorSnapshot
from app.collector.note_detail import NoteDetail
from app.collector.search import Hotword, SearchResult
from app.collector.config import CollectorConfig

import logging

logger = logging.getLogger(__name__)

_config = CollectorConfig()


def _ensure_output_dir() -> str:
    os.makedirs(_config.output_dir, exist_ok=True)
    return _config.output_dir


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_task(task_id: str, keyword: str, status: str = "running") -> None:
    db = SessionLocal()
    try:
        task = CollectorTask(
            task_id=task_id,
            keyword=keyword,
            note_type="image_text",
            sort="time_filtered",
            status=status,
            start_time=_now(),
        )
        db.merge(task)
        db.commit()
    finally:
        db.close()


def update_task(task_id: str, status: str, notes_found: int = 0,
                notes_saved: int = 0, error_msg: str = "") -> None:
    db = SessionLocal()
    try:
        task = db.query(CollectorTask).filter(CollectorTask.task_id == task_id).first()
        if task:
            task.status = status
            task.notes_found = notes_found
            task.notes_saved = notes_saved
            task.end_time = _now()
            if error_msg:
                task.error_msg = error_msg
            db.commit()
    finally:
        db.close()


def save_note(note: NoteDetail) -> bool:
    db = SessionLocal()
    try:
        existing = db.query(CollectorNote).filter(
            CollectorNote.note_id == note.note_id
        ).first()
        if existing:
            return False

        db_note = CollectorNote(
            note_id=note.note_id,
            title=note.title,
            content_raw=note.content_raw,
            content_clean=note.content_clean,
            content_hash=note.content_hash,
            author_id=note.author_id,
            author_name=note.author_name,
            publish_time=note.publish_time,
            like_count=note.like_count,
            collect_count=note.collect_count,
            comment_count=note.comment_count,
            note_type=note.note_type,
            source_url=note.source_url,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(db_note)
        db.commit()
        return True
    finally:
        db.close()


def save_snapshot(task_id: str, note: NoteDetail, keyword: str,
                  hotwords: List[Hotword]) -> None:
    db = SessionLocal()
    try:
        snapshot = CollectorSnapshot(
            task_id=task_id,
            note_id=note.note_id,
            keyword=keyword,
            hotwords_json=json.dumps(
                [{"rank": h.rank, "text": h.text} for h in hotwords],
                ensure_ascii=False,
            ),
            tags_json=json.dumps(note.tags, ensure_ascii=False),
            crawled_at=_now(),
        )
        db.add(snapshot)
        db.commit()
    finally:
        db.close()


def export_csv(result: SearchResult, notes: List[NoteDetail]) -> str:
    out_dir = _ensure_output_dir()
    filename = os.path.join(
        out_dir, f"xhs_{result.keyword}_{_now()[:10]}.csv"
    )
    hotwords_str = ",".join(h.text for h in result.hotwords)

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "keyword", "note_id", "title", "author_name", "publish_time",
            "content_clean", "tags", "hotwords", "like_count", "source_url", "crawled_at",
        ])
        for note in notes:
            writer.writerow([
                result.keyword,
                note.note_id,
                note.title,
                note.author_name,
                note.publish_time,
                note.content_clean,
                ";".join(note.tags),
                hotwords_str,
                note.like_count,
                note.source_url,
                _now(),
            ])
    logger.info("CSV exported: %s (%d rows)", filename, len(notes))
    return filename


def export_json(result: SearchResult, notes: List[NoteDetail]) -> str:
    out_dir = _ensure_output_dir()
    filename = os.path.join(
        out_dir, f"xhs_{result.keyword}_{_now()[:10]}.json"
    )
    output = {
        "keyword": result.keyword,
        "crawled_at": _now(),
        "hotwords": [h.text for h in result.hotwords],
        "notes_count": len(notes),
        "notes": [
            {
                "note_id": n.note_id,
                "title": n.title,
                "author_name": n.author_name,
                "publish_time": n.publish_time,
                "content_clean": n.content_clean,
                "tags": n.tags,
                "like_count": n.like_count,
                "source_url": n.source_url,
            }
            for n in notes
        ],
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info("JSON exported: %s", filename)
    return filename
