import json, os
from unittest.mock import patch

def _patched(tmp_path):
    sessions_dir = str(tmp_path / "sessions")
    return patch("core.session_store.SESSIONS_DIR", sessions_dir)

def _make_session(old="C:/old.mp4", new="C:/new.mp4"):
    return {
        "timestamp": "2026-06-01T12:00:00",
        "provider": "deepl",
        "model": None,
        "source_dirs": ["C:/"],
        "files": [{"old_path": old, "new_path": new, "status": "renamed"}],
        "stats": {"renamed": 1, "failed": 0},
    }

def test_save_creates_file(tmp_path):
    with _patched(tmp_path):
        from core.session_store import save_session
        path = save_session(_make_session())
        assert os.path.exists(path)

def test_list_sessions_returns_newest_first(tmp_path):
    with _patched(tmp_path):
        from core.session_store import save_session, list_sessions
        import time
        save_session(_make_session())
        time.sleep(0.01)
        save_session(_make_session())
        sessions = list_sessions()
        assert len(sessions) == 2
        assert sessions[0]["timestamp"] >= sessions[1]["timestamp"]

def test_load_session(tmp_path):
    with _patched(tmp_path):
        from core.session_store import save_session, load_session
        path = save_session(_make_session())
        data = load_session(path)
        assert data["provider"] == "deepl"
        assert len(data["files"]) == 1

def test_revert_renames_back(tmp_path):
    old_file = tmp_path / "old.mp4"
    new_file = tmp_path / "new.mp4"
    new_file.write_text("content")

    session = _make_session(old=str(old_file), new=str(new_file))
    with _patched(tmp_path):
        from core.session_store import save_session, revert_session
        path = save_session(session)
        result = revert_session(path)
        assert result["reverted"] == 1
        assert result["skipped"] == 0
        assert old_file.exists()
        assert not new_file.exists()

def test_revert_skips_missing_file(tmp_path):
    session = _make_session(old=str(tmp_path / "old.mp4"), new=str(tmp_path / "gone.mp4"))
    with _patched(tmp_path):
        from core.session_store import save_session, revert_session
        path = save_session(session)
        result = revert_session(path)
        assert result["reverted"] == 0
        assert result["skipped"] == 1

def test_prune_keeps_max_50(tmp_path):
    with _patched(tmp_path):
        from core.session_store import save_session, list_sessions, MAX_SESSIONS
        import time
        for _ in range(MAX_SESSIONS + 5):
            save_session(_make_session())
            time.sleep(0.005)
        assert len(list_sessions()) <= MAX_SESSIONS
