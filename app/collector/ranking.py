from datetime import datetime, timezone, timedelta

from app.collector.note_detail import NoteDetail


def select_top_recent_notes(
    notes: list[NoteDetail],
    recent_days: int = 0,
    top_per_metric: int = 0,
    now: datetime | None = None,
) -> list[NoteDetail]:
    now = now or datetime.now(timezone.utc)
    candidates = list(notes)
    if recent_days > 0:
        cutoff = now - timedelta(days=recent_days)
        candidates = [
            note for note in candidates
            if _parse_publish_time(note.publish_time) and _parse_publish_time(note.publish_time) >= cutoff
        ]
    if top_per_metric <= 0:
        return candidates

    selected: list[NoteDetail] = []
    seen: set[str] = set()
    metrics = ("like_count", "comment_count", "collect_count")
    for metric in metrics:
        ranked = sorted(
            [note for note in candidates if int(getattr(note, metric, 0) or 0) > 0],
            key=lambda note: (
                int(getattr(note, metric, 0) or 0),
                int(note.like_count or 0) + int(note.collect_count or 0) * 2 + int(note.comment_count or 0) * 3,
                note.note_id,
            ),
            reverse=True,
        )
        for note in ranked[:top_per_metric]:
            if note.note_id in seen:
                continue
            seen.add(note.note_id)
            selected.append(note)
    return selected


def _parse_publish_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
