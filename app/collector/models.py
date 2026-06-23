import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CollectorTask(Base):
    __tablename__ = "collector_task"

    task_id = Column(String(32), primary_key=True, default=_uuid)
    keyword = Column(String(255), nullable=False)
    note_type = Column(String(50), default="image_text")
    sort = Column(String(50), default="time_filtered")
    status = Column(String(20), default="pending")
    notes_found = Column(Integer, default=0)
    notes_saved = Column(Integer, default=0)
    start_time = Column(String(30), nullable=True)
    end_time = Column(String(30), nullable=True)
    error_msg = Column(Text, nullable=True)


class CollectorNote(Base):
    __tablename__ = "collector_note"

    note_id = Column(String(64), primary_key=True)
    title = Column(Text, nullable=True)
    content_raw = Column(Text, nullable=True)
    content_clean = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    author_id = Column(String(64), nullable=True)
    author_name = Column(String(255), nullable=True)
    publish_time = Column(String(30), nullable=True)
    like_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    note_type = Column(String(20), nullable=True)
    source_url = Column(Text, nullable=True)
    created_at = Column(String(30), default=_now)
    updated_at = Column(String(30), default=_now)


class CollectorSnapshot(Base):
    __tablename__ = "collector_snapshot"

    snapshot_id = Column(String(32), primary_key=True, default=_uuid)
    task_id = Column(String(32), ForeignKey("collector_task.task_id"), nullable=True)
    note_id = Column(String(64), nullable=True)
    keyword = Column(String(255), nullable=True)
    hotwords_json = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)
    crawled_at = Column(String(30), default=_now)


class CollectorHotwordObservation(Base):
    __tablename__ = "collector_hotword_observation"

    observation_id = Column(String(32), primary_key=True, default=_uuid)
    task_id = Column(String(32), ForeignKey("collector_task.task_id"), nullable=True)
    seed_keyword = Column(String(255), nullable=False)
    hotword = Column(String(255), nullable=False)
    rank = Column(Integer, nullable=True)
    source = Column(String(50), default="api_hot_query")
    observed_at = Column(String(30), default=_now)


class CollectorNoteObservation(Base):
    __tablename__ = "collector_note_observation"

    observation_id = Column(String(32), primary_key=True, default=_uuid)
    task_id = Column(String(32), ForeignKey("collector_task.task_id"), nullable=True)
    seed_keyword = Column(String(255), nullable=False)
    note_id = Column(String(64), nullable=False)
    like_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    publish_time = Column(String(30), nullable=True)
    tags_json = Column(Text, nullable=True)
    observed_at = Column(String(30), default=_now)
