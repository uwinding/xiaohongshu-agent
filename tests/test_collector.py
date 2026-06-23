import pytest


class TestCollectorConfig:
    def test_default_config(self):
        from app.collector.config import CollectorConfig
        cfg = CollectorConfig()
        assert cfg.headless is True
        assert cfg.max_notes_per_keyword == 50

    def test_custom_config(self):
        from app.collector.config import CollectorConfig
        cfg = CollectorConfig(max_notes_per_keyword=10, browser_executable_path="/tmp/chrome")
        assert cfg.max_notes_per_keyword == 10
        assert cfg.browser_executable_path == "/tmp/chrome"

    def test_load_keywords_default(self):
        from app.collector.config import load_keywords
        keywords = load_keywords("nonexistent.yaml")
        assert keywords == ["穿搭"]

    def test_load_keywords_from_yaml(self, tmpdir):
        import yaml
        from app.collector.config import load_keywords

        path = tmpdir.join("test_keywords.yaml")
        path.write(yaml.dump({"keywords": ["A", "B"]}))
        keywords = load_keywords(str(path))
        assert keywords == ["A", "B"]


class TestExtractor:
    def test_extract_tags(self):
        from app.collector.extractor import extract_tags
        tags = extract_tags("Hello #穿搭 #夏季穿搭 world #穿搭")
        assert tags == ["#穿搭", "#夏季穿搭"]

    def test_clean_content(self):
        from app.collector.extractor import clean_content
        result = clean_content("  hello   world  \n\n\n  foo  ")
        assert result == "hello world \n\n foo"

    def test_compute_content_hash(self):
        from app.collector.extractor import compute_content_hash
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello  world")
        assert h1 == h2


class TestSearchResult:
    def test_search_result_dataclass(self):
        from app.collector.search import SearchResult, Hotword, NoteCard
        r = SearchResult(
            keyword="test",
            hotwords=[Hotword(rank=1, text="A")],
            cards=[NoteCard(note_id="123", title="T", xsec_token="tok")],
        )
        assert r.keyword == "test"
        assert len(r.hotwords) == 1
        assert len(r.cards) == 1


class TestNoteDetail:
    def test_note_detail_dataclass(self):
        from app.collector.note_detail import NoteDetail
        n = NoteDetail(note_id="123", title="Hello", content_raw="raw")
        assert n.note_id == "123"
        assert n.title == "Hello"
        assert n.tags == []


class TestStore:
    def test_export_csv(self, tmpdir):
        import os
        from app.collector.store import export_csv, CollectorConfig
        from app.collector.search import SearchResult, Hotword
        from app.collector.note_detail import NoteDetail

        _cfg = CollectorConfig(output_dir=str(tmpdir))
        import app.collector.store as store_mod
        store_mod._config = _cfg

        r = SearchResult(keyword="test", hotwords=[Hotword(rank=1, text="H")])
        notes = [
            NoteDetail(
                note_id="1", title="T1", author_name="A1",
                content_clean="hello", tags=["#tag1", "#tag2"],
                source_url="http://x.com/1",
            )
        ]
        path = export_csv(r, notes)
        assert os.path.exists(path)

    def test_export_json(self, tmpdir):
        import os
        from app.collector.store import export_json, CollectorConfig
        from app.collector.search import SearchResult, Hotword
        from app.collector.note_detail import NoteDetail

        _cfg = CollectorConfig(output_dir=str(tmpdir))
        import app.collector.store as store_mod
        store_mod._config = _cfg

        r = SearchResult(keyword="test", hotwords=[Hotword(rank=1, text="H")])
        notes = [
            NoteDetail(
                note_id="1", title="T1", author_name="A1",
                content_clean="hello", tags=["#tag1"],
                source_url="http://x.com/1",
            )
        ]
        path = export_json(r, notes)
        assert os.path.exists(path)

    def test_save_trend_observations(self, setup_db):
        from app.collector.store import save_hotword_observations, save_note_observation
        from app.collector.search import Hotword
        from app.collector.note_detail import NoteDetail
        from app.collector.models import CollectorHotwordObservation, CollectorNoteObservation

        count = save_hotword_observations(
            "task1",
            "穿搭",
            [Hotword(rank=1, text="通勤穿搭"), Hotword(rank=2, text="通勤穿搭")],
            db=setup_db,
        )
        save_note_observation(
            "task1",
            "穿搭",
            NoteDetail(
                note_id="note1",
                like_count=10,
                collect_count=3,
                comment_count=2,
                tags=["#通勤穿搭"],
            ),
            db=setup_db,
        )

        assert count == 2
        assert setup_db.query(CollectorHotwordObservation).count() == 2
        assert setup_db.query(CollectorNoteObservation).count() == 1


class TestExceptions:
    def test_exceptions(self):
        from app.collector.exceptions import (
            LoginExpired, NoteNotFound, RateLimitError, DataFetchError
        )
        assert issubclass(LoginExpired, Exception)
        assert issubclass(RateLimitError, Exception)


class TestDedup:
    def test_is_duplicate_no_db(self, setup_db):
        from app.collector.dedup import is_duplicate
        result = is_duplicate("nonexistent_note_12345", db=setup_db)
        assert result is False

    def test_is_duplicate_with_db(self, setup_db):
        from app.collector.dedup import is_duplicate
        from app.collector.models import CollectorNote
        note = CollectorNote(
            note_id="existing_note_1",
            title="test",
            content_hash="hash1",
        )
        setup_db.add(note)
        setup_db.commit()
        result = is_duplicate("existing_note_1", db=setup_db)
        assert result is True
        result_hash = is_duplicate("other_note", content_hash="hash1", db=setup_db)
        assert result_hash is True
