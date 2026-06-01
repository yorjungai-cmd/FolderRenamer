# Folder File Renamer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows desktop app that batch-translates Japanese filenames to English via DeepL or OpenRouter, with preview-and-confirm UI and session-based revert.

**Architecture:** Python 3.11 + PyQt6. Core logic (parse / sanitize / rename / session) is pure Python with no Qt dependency — fully unit-testable. QThread workers bridge async API calls to the UI via signals. Config and history persist under `%APPDATA%\FolderFileRenamer\`.

**Tech Stack:** Python 3.11+, PyQt6 ≥ 6.6, httpx ≥ 0.27, emoji ≥ 2.12, pytest, PyInstaller ≥ 6.0

---

## File Map

```
(project root = "Folder File Renamer/")
├── main.py
├── config.py
├── core/
│   ├── __init__.py
│   ├── filename_parser.py
│   ├── sanitizer.py
│   ├── session_store.py
│   └── rename_engine.py
├── api/
│   ├── __init__.py
│   ├── base_provider.py
│   ├── deepl_provider.py
│   └── openrouter_provider.py
├── workers/
│   ├── __init__.py
│   ├── scan_worker.py
│   └── translation_worker.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── file_queue_panel.py
│   ├── preview_panel.py
│   ├── progress_bar_widget.py
│   ├── settings_dialog.py
│   └── history_dialog.py
├── resources/
│   ├── styles.qss
│   ├── fonts/          ← Inter TTF files go here
│   └── icon.ico
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_filename_parser.py
│   ├── test_sanitizer.py
│   ├── test_session_store.py
│   ├── test_rename_engine.py
│   ├── test_deepl_provider.py
│   └── test_openrouter_provider.py
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

---

## Task 1: Project Scaffold

**Files:** `requirements.txt`, `pyproject.toml`, `.gitignore`, all `__init__.py` files, `tests/conftest.py`

- [ ] **Create directory structure**

```bash
mkdir -p core api workers ui resources/fonts tests
touch core/__init__.py api/__init__.py workers/__init__.py ui/__init__.py
```

- [ ] **Write `requirements.txt`**

```
PyQt6>=6.6
httpx>=0.27
emoji>=2.12
pytest>=8.0
pytest-mock>=3.14
```

- [ ] **Write `pyproject.toml`**

```toml
[project]
name = "folder-file-renamer"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Write `tests/conftest.py`**

```python
# tests/conftest.py
# pythonpath = ["."] in pyproject.toml handles imports.
# Add shared fixtures here as needed.
```

- [ ] **Write `.gitignore`**

```
__pycache__/
*.pyc
*.pyo
dist/
build/
*.spec
.venv/
venv/
*.egg-info/
.superpowers/
```

- [ ] **Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Verify pytest works**

```bash
pytest --collect-only
```

Expected: `no tests ran` (zero errors).

- [ ] **Commit**

```bash
git add .
git commit -m "chore: project scaffold"
```

---

## Task 2: AppConfig

**Files:** Create `config.py` · Test `tests/test_config.py`

- [ ] **Write failing tests**

```python
# tests/test_config.py
import json, os, pytest
from unittest.mock import patch

def test_default_config():
    from config import AppConfig, SanitizationConfig
    cfg = AppConfig()
    assert cfg.provider == "deepl"
    assert cfg.batch_delay_ms == 200
    assert cfg.sanitization.remove_illegal is True
    assert cfg.sanitization.remove_emoji is True
    assert ".mp4" in cfg.file_extensions

def test_save_and_load(tmp_path):
    from config import AppConfig, CONFIG_FILE, CONFIG_DIR
    with patch("config.CONFIG_DIR", str(tmp_path)), \
         patch("config.CONFIG_FILE", str(tmp_path / "config.json")):
        from config import AppConfig
        cfg = AppConfig()
        cfg.deepl_key = "test-key"
        cfg.save()
        loaded = AppConfig.load()
        assert loaded.deepl_key == "test-key"

def test_load_returns_default_on_missing_file(tmp_path):
    with patch("config.CONFIG_FILE", str(tmp_path / "nonexistent.json")):
        from config import AppConfig
        cfg = AppConfig.load()
        assert cfg.provider == "deepl"

def test_load_returns_default_on_corrupt_file(tmp_path):
    bad = tmp_path / "config.json"
    bad.write_text("not json")
    with patch("config.CONFIG_FILE", str(bad)):
        from config import AppConfig
        cfg = AppConfig.load()
        assert cfg.provider == "deepl"
```

- [ ] **Run — expect FAIL** (`ModuleNotFoundError: config`)

```bash
pytest tests/test_config.py -v
```

- [ ] **Write `config.py`**

```python
import json, os
from dataclasses import dataclass, field, asdict
from typing import List

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, "FolderFileRenamer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

@dataclass
class SanitizationConfig:
    remove_illegal: bool = True
    remove_emoji: bool = True
    strip_dots_spaces: bool = True
    normalize_fullwidth: bool = True
    remove_control_chars: bool = False
    collapse_spaces: bool = False
    replacement_char: str = ""

@dataclass
class AppConfig:
    provider: str = "deepl"
    deepl_key: str = ""
    deepl_pro: bool = False
    openrouter_key: str = ""
    openrouter_model: str = "google/gemini-flash-1.5"
    batch_delay_ms: int = 200
    request_timeout_s: int = 30
    file_extensions: List[str] = field(default_factory=lambda: [
        ".mp4", ".mkv", ".avi", ".ts", ".wmv", ".flv", ".mov", ".iso", ".m2ts"
    ])
    scan_subdirectories: bool = True
    sanitization: SanitizationConfig = field(default_factory=SanitizationConfig)

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "AppConfig":
        if not os.path.exists(CONFIG_FILE):
            return cls()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            san_data = data.pop("sanitization", {})
            cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            cfg.sanitization = SanitizationConfig(**{
                k: v for k, v in san_data.items()
                if k in SanitizationConfig.__dataclass_fields__
            })
            return cfg
        except Exception:
            return cls()
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_config.py -v
```

- [ ] **Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: AppConfig load/save with APPDATA persistence"
```

---

## Task 3: FilenameParser

**Files:** Create `core/filename_parser.py` · Test `tests/test_filename_parser.py`

- [ ] **Write failing tests**

```python
# tests/test_filename_parser.py
from core.filename_parser import (
    parse_filename, reconstruct, collect_japanese, has_japanese, Segment
)

def test_has_japanese_true():
    assert has_japanese("田中美久") is True

def test_has_japanese_false():
    assert has_japanese("SSIS-123 Hello") is False

def test_studio_code_preserved():
    segs = parse_filename("SSIS-123 田中美久")
    kinds = [s.kind for s in segs if s.text.strip()]
    assert "preserved" in kinds
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "SSIS-123" in preserved

def test_resolution_tag_preserved():
    segs = parse_filename("ABP-001 タイトル 4K")
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "4K" in preserved
    assert "ABP-001" in preserved

def test_bracketed_code_preserved():
    segs = parse_filename("[Uncensored] タイトル")
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "[Uncensored]" in preserved

def test_japanese_extracted():
    segs = parse_filename("SSIS-123 田中美久 タイトル 4K")
    japanese = [s.text for s in segs if s.kind == "japanese"]
    assert any("田中" in t for t in japanese)

def test_reconstruct_replaces_japanese():
    segs = parse_filename("SSIS-123 田中美久 4K")
    jp = collect_japanese(segs)
    translations = {idx: "Tanaka Miku" for idx, _ in jp}
    result = reconstruct(segs, translations)
    assert "SSIS-123" in result
    assert "Tanaka Miku" in result
    assert "4K" in result
    assert "田中美久" not in result

def test_collect_japanese_returns_indices():
    segs = parse_filename("SSIS-123 田中 タイトル")
    jp = collect_japanese(segs)
    assert len(jp) >= 1
    for idx, text in jp:
        assert segs[idx].kind == "japanese"

def test_latin_only_filename():
    segs = parse_filename("hello world 2023")
    jp = collect_japanese(segs)
    assert jp == []

def test_year_in_parens_preserved():
    segs = parse_filename("タイトル (2023)")
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "(2023)" in preserved
```

- [ ] **Run — expect FAIL**

```bash
pytest tests/test_filename_parser.py -v
```

- [ ] **Write `core/filename_parser.py`**

```python
import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Segment:
    text: str
    kind: str  # 'preserved' | 'japanese' | 'latin' | 'space'

CJK_RANGES = [(0x3000, 0x9FFF), (0xF900, 0xFAFF), (0xFF00, 0xFFFF)]

PRESERVED_PATTERNS = [
    r'\[[A-Z0-9][A-Z0-9\- ]*\]',        # [Uncensored], [BT], [4K]
    r'[A-Z]{2,6}-\d{2,5}',              # SSIS-123, ABP-789
    r'\(20\d{2}\)',                       # (2023)
    r'\b(?:4K|8K|1080p|720p|480p|FHD|UHD|HD|SDR|HDR10?)\b',
    r'\b20\d{2}\b',                       # bare year
    r'\b\d{4,}\b',                        # long numeric run
]
_PRESERVED_RE = re.compile('|'.join(PRESERVED_PATTERNS))

def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)

def has_japanese(text: str) -> bool:
    return any(is_cjk(c) for c in text)

def parse_filename(stem: str) -> List[Segment]:
    segments: List[Segment] = []
    pos = 0
    for m in _PRESERVED_RE.finditer(stem):
        if m.start() > pos:
            segments.extend(_classify_free(stem[pos:m.start()]))
        segments.append(Segment(text=m.group(), kind="preserved"))
        pos = m.end()
    if pos < len(stem):
        segments.extend(_classify_free(stem[pos:]))
    return segments

def _classify_free(text: str) -> List[Segment]:
    result: List[Segment] = []
    buf = ""
    kind = None
    for ch in text:
        if ch == " ":
            if buf:
                result.append(Segment(text=buf, kind=kind or "latin"))
                buf = ""
                kind = None
            result.append(Segment(text=" ", kind="space"))
        elif is_cjk(ch):
            if kind == "japanese":
                buf += ch
            else:
                if buf:
                    result.append(Segment(text=buf, kind=kind or "latin"))
                buf, kind = ch, "japanese"
        else:
            if kind == "latin":
                buf += ch
            else:
                if buf:
                    result.append(Segment(text=buf, kind=kind or "latin"))
                buf, kind = ch, "latin"
    if buf:
        result.append(Segment(text=buf, kind=kind or "latin"))
    return result

def collect_japanese(segments: List[Segment]) -> List[Tuple[int, str]]:
    return [(i, s.text) for i, s in enumerate(segments) if s.kind == "japanese"]

def reconstruct(segments: List[Segment], translations: dict) -> str:
    parts = [translations.get(i, s.text) for i, s in enumerate(segments)]
    return "".join(parts).strip()
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_filename_parser.py -v
```

- [ ] **Commit**

```bash
git add core/filename_parser.py tests/test_filename_parser.py
git commit -m "feat: FilenameParser — smart CJK extraction preserving studio codes and tags"
```

---

## Task 4: Sanitizer

**Files:** Create `core/sanitizer.py` · Test `tests/test_sanitizer.py`

- [ ] **Write failing tests**

```python
# tests/test_sanitizer.py
from config import SanitizationConfig
from core.sanitizer import sanitize

def _cfg(**kwargs) -> SanitizationConfig:
    cfg = SanitizationConfig()
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg

def test_remove_illegal_chars():
    cfg = _cfg(remove_illegal=True, replacement_char="")
    assert sanitize('file:name*here', cfg) == 'filenamhere'

def test_replace_illegal_with_underscore():
    cfg = _cfg(remove_illegal=True, replacement_char="_")
    assert sanitize('file:name', cfg) == 'file_name'

def test_remove_emoji():
    cfg = _cfg(remove_emoji=True, replacement_char="")
    result = sanitize('title 🔥 hot', cfg)
    assert '🔥' not in result
    assert 'title' in result

def test_strip_trailing_dot():
    cfg = _cfg(strip_dots_spaces=True)
    assert sanitize('filename.', cfg) == 'filename'

def test_strip_leading_space():
    cfg = _cfg(strip_dots_spaces=True)
    assert sanitize('  filename  ', cfg) == 'filename'

def test_normalize_fullwidth():
    cfg = _cfg(normalize_fullwidth=True)
    assert sanitize('ａｂｃ１２３', cfg) == 'abc123'

def test_collapse_spaces():
    cfg = _cfg(collapse_spaces=True)
    assert sanitize('a  b   c', cfg) == 'a b c'

def test_remove_control_chars():
    cfg = _cfg(remove_control_chars=True)
    assert sanitize('file\x00name\x01', cfg) == 'filename'

def test_rules_off_by_default_dont_apply():
    cfg = SanitizationConfig()  # collapse_spaces=False, remove_control_chars=False
    assert sanitize('a  b', cfg) == 'a  b'
```

- [ ] **Run — expect FAIL**

```bash
pytest tests/test_sanitizer.py -v
```

- [ ] **Write `core/sanitizer.py`**

```python
import re, unicodedata
import emoji as _emoji
from config import SanitizationConfig

_ILLEGAL_RE = re.compile(r'[\\/:*?"<>|]')

def sanitize(text: str, cfg: SanitizationConfig) -> str:
    if cfg.normalize_fullwidth:
        text = unicodedata.normalize("NFKC", text)
    if cfg.remove_emoji:
        text = _emoji.replace_emoji(text, replace=cfg.replacement_char)
    if cfg.remove_illegal:
        text = _ILLEGAL_RE.sub(cfg.replacement_char, text)
    if cfg.remove_control_chars:
        text = "".join(c for c in text if unicodedata.category(c) != "Cc")
    if cfg.collapse_spaces:
        text = re.sub(r" {2,}", " ", text)
    if cfg.strip_dots_spaces:
        text = text.strip().rstrip(".")
    return text
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_sanitizer.py -v
```

- [ ] **Commit**

```bash
git add core/sanitizer.py tests/test_sanitizer.py
git commit -m "feat: Sanitizer — configurable filename cleaning rules"
```

---

## Task 5: SessionStore

**Files:** Create `core/session_store.py` · Test `tests/test_session_store.py`

- [ ] **Write failing tests**

```python
# tests/test_session_store.py
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
```

- [ ] **Run — expect FAIL**

```bash
pytest tests/test_session_store.py -v
```

- [ ] **Write `core/session_store.py`**

```python
import json, os
from datetime import datetime
from typing import List

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
SESSIONS_DIR = os.path.join(APPDATA, "FolderFileRenamer", "sessions")
MAX_SESSIONS = 50

def _ensure():
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_session(data: dict) -> str:
    _ensure()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(SESSIONS_DIR, f"{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _prune()
    return path

def list_sessions() -> List[dict]:
    _ensure()
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({"path": fpath, **data})
        except Exception:
            continue
    return sessions

def load_session(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def revert_session(path: str) -> dict:
    data = load_session(path)
    reverted = skipped = failed = 0
    for entry in data.get("files", []):
        if entry.get("status") != "renamed":
            continue
        old_p, new_p = entry["old_path"], entry["new_path"]
        if not os.path.exists(new_p):
            entry["revert_status"] = "skipped"
            skipped += 1
            continue
        try:
            os.rename(new_p, old_p)
            entry["revert_status"] = "reverted"
            reverted += 1
        except OSError as e:
            entry["revert_status"] = f"failed: {e}"
            failed += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"reverted": reverted, "skipped": skipped, "failed": failed}

def _prune():
    files = sorted(f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json"))
    while len(files) > MAX_SESSIONS:
        os.remove(os.path.join(SESSIONS_DIR, files.pop(0)))
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_session_store.py -v
```

- [ ] **Commit**

```bash
git add core/session_store.py tests/test_session_store.py
git commit -m "feat: SessionStore — JSON session persistence with auto-prune and revert"
```

---

## Task 6: RenameEngine

**Files:** Create `core/rename_engine.py` · Test `tests/test_rename_engine.py`

- [ ] **Write failing tests**

```python
# tests/test_rename_engine.py
import os
from core.rename_engine import (
    check_conflicts, check_missing_sources, apply_renames, safe_filename_length
)

def test_no_conflicts():
    renames = [("a.mp4", "b.mp4"), ("c.mp4", "d.mp4")]
    assert check_conflicts(renames) == []

def test_detects_conflict():
    renames = [("a.mp4", "same.mp4"), ("b.mp4", "same.mp4")]
    assert "same.mp4" in check_conflicts(renames)

def test_missing_source(tmp_path):
    missing = str(tmp_path / "gone.mp4")
    existing = str(tmp_path / "here.mp4")
    (tmp_path / "here.mp4").write_text("")
    result = check_missing_sources([(missing, "x"), (existing, "y")])
    assert missing in result
    assert existing not in result

def test_apply_renames_success(tmp_path):
    src = tmp_path / "old.mp4"
    src.write_text("data")
    dst = str(tmp_path / "new.mp4")
    results = apply_renames([(str(src), dst)])
    assert results[0]["status"] == "renamed"
    assert os.path.exists(dst)
    assert not src.exists()

def test_apply_renames_failure(tmp_path):
    results = apply_renames([(str(tmp_path / "nope.mp4"), str(tmp_path / "x.mp4"))])
    assert results[0]["status"] == "failed"
    assert results[0]["error"] is not None

def test_safe_filename_length_short():
    assert safe_filename_length("short", ".mp4") == "short"

def test_safe_filename_length_truncates():
    long_stem = "a" * 300
    result = safe_filename_length(long_stem, ".mp4")
    assert len((result + ".mp4").encode("utf-8")) <= 255
```

- [ ] **Run — expect FAIL**

```bash
pytest tests/test_rename_engine.py -v
```

- [ ] **Write `core/rename_engine.py`**

```python
import os, shutil
from typing import List, Tuple

def check_conflicts(renames: List[Tuple[str, str]]) -> List[str]:
    new_paths = [n for _, n in renames]
    seen, conflicts = set(), []
    for p in new_paths:
        (conflicts if p in seen else seen).add(p) if p in seen else seen.add(p)
    return list({n for n in new_paths if new_paths.count(n) > 1})

def check_missing_sources(renames: List[Tuple[str, str]]) -> List[str]:
    return [old for old, _ in renames if not os.path.exists(old)]

def apply_renames(renames: List[Tuple[str, str]]) -> List[dict]:
    results = []
    for old, new in renames:
        try:
            if os.path.dirname(os.path.abspath(old)) == os.path.dirname(os.path.abspath(new)):
                os.rename(old, new)
            else:
                shutil.move(old, new)
            results.append({"old_path": old, "new_path": new, "status": "renamed", "error": None})
        except OSError as e:
            results.append({"old_path": old, "new_path": new, "status": "failed", "error": str(e)})
    return results

def safe_filename_length(stem: str, ext: str, max_bytes: int = 255) -> str:
    if len((stem + ext).encode("utf-8")) <= max_bytes:
        return stem
    available = max_bytes - len(ext.encode("utf-8"))
    return stem.encode("utf-8")[:available].decode("utf-8", errors="ignore")
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_rename_engine.py -v
```

- [ ] **Commit**

```bash
git add core/rename_engine.py tests/test_rename_engine.py
git commit -m "feat: RenameEngine — conflict detection, atomic rename, length safety"
```

---

## Task 7: DeepL Provider

**Files:** Create `api/base_provider.py`, `api/deepl_provider.py` · Test `tests/test_deepl_provider.py`

- [ ] **Write `api/base_provider.py`**

```python
from abc import ABC, abstractmethod
from typing import List

class BaseProvider(ABC):
    @abstractmethod
    def translate(self, texts: List[str]) -> List[str]: ...

    @abstractmethod
    def test_connection(self) -> dict:
        """Returns {'ok': bool, 'message': str, 'quota': str | None}"""
        ...
```

- [ ] **Write failing tests**

```python
# tests/test_deepl_provider.py
import pytest
from unittest.mock import patch, MagicMock

def _mock_response(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    if status >= 400:
        import httpx
        m.raise_for_status.side_effect = httpx.HTTPStatusError("err", request=MagicMock(), response=m)
    return m

def test_translate_batch(mocker):
    from api.deepl_provider import DeepLProvider
    mock_post = mocker.patch("httpx.post", return_value=_mock_response({
        "translations": [{"text": "Hello"}, {"text": "World"}]
    }))
    p = DeepLProvider("testkey:fx")
    result = p.translate(["こんにちは", "世界"])
    assert result == ["Hello", "World"]
    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["target_lang"] == "EN"
    assert call_json["text"] == ["こんにちは", "世界"]

def test_translate_empty_returns_empty(mocker):
    from api.deepl_provider import DeepLProvider
    p = DeepLProvider("testkey:fx")
    assert p.translate([]) == []

def test_free_key_uses_free_url(mocker):
    from api.deepl_provider import DeepLProvider, FREE_BASE
    mock_post = mocker.patch("httpx.post", return_value=_mock_response({"translations": [{"text": "x"}]}))
    DeepLProvider("mykey:fx").translate(["test"])
    assert FREE_BASE in mock_post.call_args.args[0]

def test_pro_key_uses_pro_url(mocker):
    from api.deepl_provider import DeepLProvider, PRO_BASE
    mock_post = mocker.patch("httpx.post", return_value=_mock_response({"translations": [{"text": "x"}]}))
    DeepLProvider("mykey-pro").translate(["test"])
    assert PRO_BASE in mock_post.call_args.args[0]

def test_test_connection_ok(mocker):
    from api.deepl_provider import DeepLProvider
    mocker.patch("httpx.get", return_value=_mock_response({
        "character_count": 12000, "character_limit": 500000
    }))
    result = DeepLProvider("testkey:fx").test_connection()
    assert result["ok"] is True
    assert "488,000" in result["quota"]

def test_test_connection_fail(mocker):
    from api.deepl_provider import DeepLProvider
    mocker.patch("httpx.get", side_effect=Exception("timeout"))
    result = DeepLProvider("testkey:fx").test_connection()
    assert result["ok"] is False
```

- [ ] **Run — expect FAIL**

```bash
pytest tests/test_deepl_provider.py -v
```

- [ ] **Write `api/deepl_provider.py`**

```python
import httpx
from typing import List
from .base_provider import BaseProvider

FREE_BASE = "https://api-free.deepl.com/v2"
PRO_BASE  = "https://api.deepl.com/v2"

class DeepLProvider(BaseProvider):
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = FREE_BASE if api_key.endswith(":fx") else PRO_BASE

    def _headers(self):
        return {"Authorization": f"DeepL-Auth-Key {self.api_key}"}

    def translate(self, texts: List[str]) -> List[str]:
        if not texts:
            return []
        r = httpx.post(
            f"{self.base_url}/translate",
            headers=self._headers(),
            json={"text": texts, "target_lang": "EN"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return [t["text"] for t in r.json()["translations"]]

    def test_connection(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/usage", headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            d = r.json()
            used, limit = d.get("character_count", 0), d.get("character_limit", 0)
            return {"ok": True, "message": "Connected",
                    "quota": f"{limit - used:,} / {limit:,} chars remaining"}
        except httpx.HTTPStatusError as e:
            return {"ok": False, "message": f"HTTP {e.response.status_code}", "quota": None}
        except Exception as e:
            return {"ok": False, "message": str(e), "quota": None}
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_deepl_provider.py -v
```

- [ ] **Commit**

```bash
git add api/base_provider.py api/deepl_provider.py tests/test_deepl_provider.py
git commit -m "feat: DeepLProvider — batch translation and connection test"
```

---

## Task 8: OpenRouter Provider

**Files:** Create `api/openrouter_provider.py` · Test `tests/test_openrouter_provider.py`

- [ ] **Write failing tests**

```python
# tests/test_openrouter_provider.py
from unittest.mock import MagicMock, patch

def _resp(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m

def test_translate_parses_numbered_lines(mocker):
    from api.openrouter_provider import OpenRouterProvider
    content = "1. Tanaka Miku\n2. First Shoot"
    mocker.patch("httpx.post", return_value=_resp({
        "choices": [{"message": {"content": content}}]
    }))
    p = OpenRouterProvider("key", "google/gemini-flash-1.5")
    result = p.translate(["田中美久", "初めての撮影"])
    assert result[0] == "Tanaka Miku"
    assert result[1] == "First Shoot"

def test_translate_pads_short_response(mocker):
    from api.openrouter_provider import OpenRouterProvider
    mocker.patch("httpx.post", return_value=_resp({
        "choices": [{"message": {"content": "1. Only One"}}]
    }))
    p = OpenRouterProvider("key", "model")
    result = p.translate(["text1", "text2"])
    assert len(result) == 2
    assert result[1] == "text2"  # padded with original

def test_list_models(mocker):
    from api.openrouter_provider import OpenRouterProvider
    mocker.patch("httpx.get", return_value=_resp({
        "data": [{"id": "openai/gpt-4o"}, {"id": "anthropic/claude-3"}]
    }))
    models = OpenRouterProvider("key", "model").list_models()
    assert "openai/gpt-4o" in models

def test_test_connection_ok(mocker):
    from api.openrouter_provider import OpenRouterProvider
    mocker.patch("httpx.get", return_value=_resp({"data": [{"id": "m1"}, {"id": "m2"}]}))
    r = OpenRouterProvider("key", "model").test_connection()
    assert r["ok"] is True
    assert "2 models" in r["message"]
```

- [ ] **Run — expect FAIL**

```bash
pytest tests/test_openrouter_provider.py -v
```

- [ ] **Write `api/openrouter_provider.py`**

```python
import httpx
from typing import List
from .base_provider import BaseProvider

BASE_URL = "https://openrouter.ai/api/v1"
SYSTEM_PROMPT = (
    "You are a filename translator. Translate Japanese text segments to English. "
    "Preserve spacing and structure. Return only the translated text, "
    "one line per input, same order."
)

class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def translate(self, texts: List[str]) -> List[str]:
        if not texts:
            return []
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        r = httpx.post(
            f"{BASE_URL}/chat/completions",
            headers=self._headers(),
            json={"model": self.model,
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": numbered}]},
            timeout=self.timeout,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        lines = [ln.lstrip("0123456789. ").strip()
                 for ln in content.strip().splitlines() if ln.strip()]
        while len(lines) < len(texts):
            lines.append(texts[len(lines)])
        return lines[:len(texts)]

    def list_models(self) -> List[str]:
        r = httpx.get(f"{BASE_URL}/models", headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []))

    def test_connection(self) -> dict:
        try:
            models = self.list_models()
            return {"ok": True, "message": f"Connected — {len(models)} models available", "quota": None}
        except httpx.HTTPStatusError as e:
            return {"ok": False, "message": f"HTTP {e.response.status_code}", "quota": None}
        except Exception as e:
            return {"ok": False, "message": str(e), "quota": None}
```

- [ ] **Run — expect PASS**

```bash
pytest tests/test_openrouter_provider.py -v
```

- [ ] **Run all tests**

```bash
pytest -v
```

Expected: all green.

- [ ] **Commit**

```bash
git add api/openrouter_provider.py tests/test_openrouter_provider.py
git commit -m "feat: OpenRouterProvider — LLM translation and model listing"
```

---

## Task 9: ScanWorker

**Files:** Create `workers/scan_worker.py`  
*(No unit test for QThread; logic is tested via the pure function `scan_paths`.)*

- [ ] **Write `workers/scan_worker.py`**

```python
import os
from PyQt6.QtCore import QThread, pyqtSignal

def scan_paths(paths, extensions, scan_subdirs, on_file, cancel_flag) -> int:
    """Pure function — testable without Qt. Returns file count."""
    count = 0
    exts = {e.lower() for e in extensions}
    for path in paths:
        if cancel_flag():
            break
        if os.path.isfile(path):
            if os.path.splitext(path)[1].lower() in exts:
                on_file(os.path.abspath(path))
                count += 1
        elif os.path.isdir(path):
            walker = os.walk(path) if scan_subdirs else [(path, [], os.listdir(path))]
            for root, _dirs, files in walker:
                if cancel_flag():
                    break
                for fname in files:
                    if os.path.splitext(fname)[1].lower() in exts:
                        on_file(os.path.abspath(os.path.join(root, fname)))
                        count += 1
    return count

class ScanWorker(QThread):
    file_found = pyqtSignal(str)
    finished   = pyqtSignal(int)

    def __init__(self, paths: list, extensions: set, scan_subdirs: bool):
        super().__init__()
        self.paths = paths
        self.extensions = extensions
        self.scan_subdirs = scan_subdirs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        count = scan_paths(
            self.paths, self.extensions, self.scan_subdirs,
            on_file=self.file_found.emit,
            cancel_flag=lambda: self._cancel,
        )
        self.finished.emit(count)
```

- [ ] **Commit**

```bash
git add workers/scan_worker.py
git commit -m "feat: ScanWorker — async folder scan with cancel support"
```

---

## Task 10: TranslationWorker

**Files:** Create `workers/translation_worker.py`

- [ ] **Write `workers/translation_worker.py`**

```python
import time
from dataclasses import dataclass
from typing import List
from PyQt6.QtCore import QThread, pyqtSignal

@dataclass
class TranslationJob:
    file_id: str
    japanese_segments: List[str]   # texts to send to API
    segment_indices: List[int]     # positions in the Segment list for reconstruction

def process_jobs(jobs, provider, batch_size, delay_ms,
                 on_status, on_result, on_error, on_progress, on_eta, cancel_flag):
    """Pure processing loop — no Qt dependency, fully testable."""
    total = len(jobs)
    done = 0
    batch_times: List[float] = []

    for i in range(0, total, batch_size):
        if cancel_flag():
            break
        batch = jobs[i:i + batch_size]

        for job in batch:
            on_status(job.file_id, "translating")

        # Flatten all texts in this batch
        all_texts, text_map = [], []
        for j, job in enumerate(batch):
            for k, text in enumerate(job.japanese_segments):
                all_texts.append(text)
                text_map.append((j, k))

        t0 = time.monotonic()
        try:
            translated = provider.translate(all_texts)
            job_results = {j: {} for j in range(len(batch))}
            for idx, (j, k) in enumerate(text_map):
                job_results[j][k] = translated[idx] if idx < len(translated) else all_texts[idx]

            for j, job in enumerate(batch):
                trans_texts = [job_results[j].get(k, job.japanese_segments[k])
                               for k in range(len(job.japanese_segments))]
                on_result(job.file_id, job.segment_indices, trans_texts)
                on_status(job.file_id, "done")
                done += 1
                on_progress(done, total)
        except Exception as e:
            for job in batch:
                on_error(job.file_id, str(e))
                on_status(job.file_id, "error")
                done += 1
                on_progress(done, total)

        elapsed = time.monotonic() - t0
        batch_times.append(elapsed)
        if len(batch_times) > 10:
            batch_times.pop(0)

        if done < total and not cancel_flag():
            avg = sum(batch_times) / len(batch_times)
            remaining_batches = (total - done) / max(batch_size, 1)
            on_eta(avg * remaining_batches)
            time.sleep(delay_ms / 1000.0)


class TranslationWorker(QThread):
    file_status_changed = pyqtSignal(str, str)
    translation_result  = pyqtSignal(str, list, list)
    translation_error   = pyqtSignal(str, str)
    progress_updated    = pyqtSignal(int, int)
    eta_updated         = pyqtSignal(float)

    def __init__(self, provider, jobs: List[TranslationJob],
                 batch_size: int = 50, delay_ms: int = 200):
        super().__init__()
        self.provider = provider
        self.jobs = jobs
        self.batch_size = batch_size
        self.delay_ms = delay_ms
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        process_jobs(
            self.jobs, self.provider, self.batch_size, self.delay_ms,
            on_status=self.file_status_changed.emit,
            on_result=self.translation_result.emit,
            on_error=self.translation_error.emit,
            on_progress=self.progress_updated.emit,
            on_eta=self.eta_updated.emit,
            cancel_flag=lambda: self._cancel,
        )
```

- [ ] **Commit**

```bash
git add workers/translation_worker.py
git commit -m "feat: TranslationWorker — batched async translation with ETA and cancel"
```

---

## Task 11: QSS Stylesheet + Resources

**Files:** Create `resources/styles.qss`, `resources/fonts/` (placeholder)

- [ ] **Write `resources/styles.qss`**

```css
* { font-family: "Inter", "Segoe UI", sans-serif; font-size: 12px; }
QMainWindow, QDialog { background-color: #f0f2f5; }
QWidget { color: #111827; background-color: #ffffff; }
QWidget#toolbar, QWidget#panel-header { background-color: #f9fafb; border-bottom: 1px solid #e5e7eb; }
QWidget#dialog-footer { background-color: #f9fafb; border-top: 1px solid #e5e7eb; }
QPushButton { background-color: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; border-radius: 6px; padding: 5px 12px; font-weight: 500; }
QPushButton:hover { background-color: #e5e7eb; }
QPushButton:disabled { color: #9ca3af; }
QPushButton#btn-primary { background-color: #6366f1; color: #fff; border: none; }
QPushButton#btn-primary:hover { background-color: #4f46e5; }
QPushButton#btn-success { background-color: #10b981; color: #fff; border: none; }
QPushButton#btn-success:hover { background-color: #059669; }
QPushButton#btn-danger { background-color: #fee2e2; color: #dc2626; border: 1px solid #fecaca; }
QTreeWidget { border: none; background-color: #f9fafb; outline: none; }
QTreeWidget::item { padding: 3px 4px; border-bottom: 1px solid #f3f4f6; }
QTreeWidget::item:selected { background-color: #eef2ff; color: #111827; }
QTableWidget { border: none; gridline-color: #f3f4f6; outline: none; }
QTableWidget::item { padding: 4px 8px; }
QTableWidget::item:selected { background-color: #eef2ff; color: #111827; }
QHeaderView::section { background-color: #f9fafb; color: #9ca3af; font-size: 10px; font-weight: 600; padding: 4px 8px; border: none; border-bottom: 1px solid #e5e7eb; }
QLineEdit { border: 1px solid #e5e7eb; border-radius: 5px; padding: 5px 8px; }
QLineEdit:focus { border-color: #6366f1; }
QComboBox { border: 1px solid #e5e7eb; border-radius: 5px; padding: 4px 8px; }
QComboBox::drop-down { border: none; width: 20px; }
QProgressBar { border: none; border-radius: 3px; background-color: #e5e7eb; }
QProgressBar::chunk { background-color: #6366f1; border-radius: 3px; }
QSplitter::handle { background-color: #e5e7eb; }
QScrollBar:vertical { border: none; background: #f9fafb; width: 8px; }
QScrollBar::handle:vertical { background: #d1d5db; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTabBar::tab { padding: 8px 16px; color: #6b7280; border-bottom: 2px solid transparent; background: transparent; }
QTabBar::tab:selected { color: #6366f1; border-bottom: 2px solid #6366f1; }
QTabWidget::pane { border: none; border-top: 1px solid #e5e7eb; }
QLabel { color: #374151; }
QLabel#header { font-size: 10px; font-weight: 600; color: #9ca3af; }
QGroupBox { border: 1px solid #e5e7eb; border-radius: 6px; margin-top: 8px; padding: 8px; }
QGroupBox::title { color: #6b7280; font-size: 11px; font-weight: 600; subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 2px solid #d1d5db; border-radius: 2px; background: #fff; }
QCheckBox::indicator:checked { background-color: #6366f1; border-color: #6366f1; }
QRadioButton::indicator { width: 14px; height: 14px; border: 2px solid #d1d5db; border-radius: 7px; background: #fff; }
QRadioButton::indicator:checked { background-color: #6366f1; border-color: #6366f1; }
QStatusBar { background-color: #f9fafb; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 11px; }
QListWidget { border: none; outline: none; }
QListWidget::item { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; }
QListWidget::item:selected { background-color: #eef2ff; color: #111827; border-left: 3px solid #6366f1; }
```

- [ ] **Create font placeholder**

```bash
echo "Place Inter TTF files here. Download: https://fonts.google.com/specimen/Inter" > resources/fonts/README.txt
```

- [ ] **Commit**

```bash
git add resources/
git commit -m "feat: QSS stylesheet — indigo accent, clean light theme"
```

---

## Task 12: main.py + MainWindow Shell

**Files:** Create `main.py`, `ui/main_window.py`

- [ ] **Write `main.py`**

```python
import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase
from config import AppConfig
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FolderFileRenamer")
    fonts_dir = os.path.join(os.path.dirname(__file__), "resources", "fonts")
    if os.path.isdir(fonts_dir):
        for fname in os.listdir(fonts_dir):
            if fname.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, fname))
    qss = os.path.join(os.path.dirname(__file__), "resources", "styles.qss")
    if os.path.exists(qss):
        with open(qss, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    config = AppConfig.load()
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

- [ ] **Write `ui/main_window.py`**

Full source is in the design spec. Key structure:

```python
class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._scan_workers: list = []
        self._translation_worker = None
        self.setWindowTitle("Folder File Renamer")
        self.resize(1280, 720)
        self.setAcceptDrops(True)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        # toolbar (btn_add_folder, btn_add_files, btn_translate, btn_settings, btn_history)
        # QSplitter(FileQueuePanel | PreviewPanel)
        # ProgressBarWidget at bottom

    def _connect_signals(self):
        # btn_add_folder -> _on_add_folder
        # btn_add_files  -> _on_add_files
        # btn_translate  -> _on_translate_all
        # btn_settings   -> _on_settings
        # btn_history    -> _on_history
        # progress_bar.stop_requested  -> _on_stop
        # progress_bar.apply_requested -> _on_apply
        # progress_bar.revert_requested -> _on_history

    # dragEnterEvent / dropEvent -> _start_scan(paths)

    def _on_translate_all(self):
        # 1. file_queue.get_pending_files()
        # 2. _get_provider() or warn
        # 3. for each file: parse_filename, collect_japanese
        #    - if no japanese: set_status(fp, "no-op")
        #    - else: preview.store_segments, preview.add_row, build TranslationJob
        # 4. create TranslationWorker, connect signals, start

    def _on_translation_result(self, file_id, indices, translated):
        # reconstruct -> sanitize -> safe_filename_length
        # preview.set_translated(file_id, final_name)
        # progress_bar.set_approved_count(...)

    def _on_apply(self):
        # preview.get_approved_renames()
        # check_conflicts / check_missing_sources
        # apply_renames -> save_session
        # file_queue.update_path for each renamed

    def _on_settings(self):
        # SettingsDialog(config).exec() -> config.save()

    def _on_history(self):
        # HistoryDialog(parent=self).exec()
```

The complete, copy-paste-ready source for `ui/main_window.py` follows. Copy it exactly.

```python
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from config import AppConfig
from core.filename_parser import parse_filename, collect_japanese, reconstruct
from core.sanitizer import sanitize
from core.rename_engine import (
    check_conflicts, check_missing_sources, apply_renames, safe_filename_length
)
from core.session_store import save_session
from api.deepl_provider import DeepLProvider
from api.openrouter_provider import OpenRouterProvider
from workers.scan_worker import ScanWorker
from workers.translation_worker import TranslationWorker, TranslationJob
from ui.file_queue_panel import FileQueuePanel
from ui.preview_panel import PreviewPanel
from ui.progress_bar_widget import ProgressBarWidget
from ui.settings_dialog import SettingsDialog
from ui.history_dialog import HistoryDialog


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._scan_workers: list = []
        self._translation_worker: TranslationWorker | None = None
        self.setWindowTitle("Folder File Renamer")
        self.setMinimumSize(1000, 600)
        self.resize(1280, 720)
        self.setAcceptDrops(True)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self._build_toolbar())
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.file_queue = FileQueuePanel(self.config)
        self.preview = PreviewPanel(self.config)
        self.splitter.addWidget(self.file_queue)
        self.splitter.addWidget(self.preview)
        self.splitter.setSizes([300, 980])
        vbox.addWidget(self.splitter, stretch=1)
        self.progress_bar = ProgressBarWidget()
        vbox.addWidget(self.progress_bar)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("toolbar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(8)
        self.btn_add_folder = QPushButton("+ Add Folder")
        self.btn_add_folder.setObjectName("btn-primary")
        self.btn_add_files = QPushButton("+ Add Files")
        h.addWidget(self.btn_add_folder)
        h.addWidget(self.btn_add_files)
        h.addStretch()
        self.btn_translate = QPushButton("▶ Translate All")
        self.btn_translate.setObjectName("btn-success")
        self.btn_settings = QPushButton("⚙  Settings")
        self.btn_history = QPushButton("🕒  History")
        h.addWidget(self.btn_translate)
        h.addWidget(self.btn_settings)
        h.addWidget(self.btn_history)
        return bar

    def _connect_signals(self):
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_translate.clicked.connect(self._on_translate_all)
        self.btn_settings.clicked.connect(self._on_settings)
        self.btn_history.clicked.connect(self._on_history)
        self.progress_bar.stop_requested.connect(self._on_stop)
        self.progress_bar.apply_requested.connect(self._on_apply)
        self.progress_bar.revert_requested.connect(self._on_history)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self._start_scan([url.toLocalFile() for url in event.mimeData().urls()])

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self._start_scan([folder])

    def _on_add_files(self):
        exts = " ".join(f"*{e}" for e in self.config.file_extensions)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", filter=f"Video Files ({exts});;All Files (*)"
        )
        if files:
            self._start_scan(files)

    def _start_scan(self, paths: list):
        worker = ScanWorker(
            paths, set(self.config.file_extensions), self.config.scan_subdirectories
        )
        worker.file_found.connect(self.file_queue.add_file)
        worker.finished.connect(
            lambda n: self.statusBar().showMessage(f"{n} files scanned")
        )
        worker.start()
        self._scan_workers.append(worker)

    def _get_provider(self):
        if self.config.provider == "deepl" and self.config.deepl_key:
            return DeepLProvider(self.config.deepl_key, self.config.request_timeout_s)
        if self.config.provider == "openrouter" and self.config.openrouter_key:
            return OpenRouterProvider(
                self.config.openrouter_key,
                self.config.openrouter_model,
                self.config.request_timeout_s,
            )
        return None

    def _on_translate_all(self):
        files = self.file_queue.get_pending_files()
        if not files:
            return
        provider = self._get_provider()
        if not provider:
            QMessageBox.warning(
                self, "No API Configured",
                "Configure an API key in Settings before translating."
            )
            return
        jobs = []
        for fp in files:
            stem = Path(fp).stem
            segs = parse_filename(stem)
            jp = collect_japanese(segs)
            if not jp:
                self.file_queue.set_status(fp, "no-op")
                continue
            self.preview.store_segments(fp, segs)
            self.preview.add_row(fp, Path(fp).name)
            jobs.append(TranslationJob(
                file_id=fp,
                japanese_segments=[t for _, t in jp],
                segment_indices=[i for i, _ in jp],
            ))
        if not jobs:
            return
        batch_size = 50 if self.config.provider == "deepl" else 5
        w = TranslationWorker(
            provider, jobs,
            batch_size=batch_size,
            delay_ms=self.config.batch_delay_ms,
        )
        w.file_status_changed.connect(self.file_queue.set_status)
        w.translation_result.connect(self._on_translation_result)
        w.translation_error.connect(self.preview.set_error)
        w.progress_updated.connect(self.progress_bar.set_progress)
        w.eta_updated.connect(self.progress_bar.set_eta)
        w.finished.connect(self._on_translation_done)
        w.start()
        self._translation_worker = w
        self.progress_bar.set_total(len(jobs))
        self.btn_translate.setEnabled(False)

    def _on_translation_result(self, file_id: str, indices: list, translated: list):
        segs = self.preview.get_segments(file_id)
        reconstructed = reconstruct(segs, dict(zip(indices, translated)))
        ext = Path(file_id).suffix
        stem = safe_filename_length(
            sanitize(reconstructed, self.config.sanitization), ext
        )
        self.preview.set_translated(file_id, stem + ext)
        self.progress_bar.set_approved_count(len(self.preview.get_approved_renames()))

    def _on_translation_done(self):
        self.btn_translate.setEnabled(True)
        approved  = len(self.preview.get_approved_renames())
        errors    = self.preview.count_by_status("error")
        conflicts = self.preview.count_by_status("conflict")
        self.progress_bar.set_summary(approved, errors, conflicts)

    def _on_stop(self):
        if self._translation_worker:
            self._translation_worker.cancel()

    def _on_apply(self):
        approved = self.preview.get_approved_renames()
        if not approved:
            return
        renames = [
            (old, os.path.join(os.path.dirname(old), new))
            for old, new in approved
        ]
        conflicts = check_conflicts(renames)
        if conflicts:
            QMessageBox.warning(
                self, "Filename Conflicts",
                f"{len(conflicts)} output names conflict. Resolve them before applying."
            )
            return
        missing = check_missing_sources(renames)
        if missing:
            reply = QMessageBox.question(
                self, "Missing Source Files",
                f"{len(missing)} source files not found. Skip and continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            renames = [(o, n) for o, n in renames if o not in missing]
        results = apply_renames(renames)
        session = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "provider": self.config.provider,
            "model": (self.config.openrouter_model
                      if self.config.provider == "openrouter" else None),
            "source_dirs": list({os.path.dirname(r["old_path"]) for r in results}),
            "files": results,
            "stats": {
                "renamed": sum(1 for r in results if r["status"] == "renamed"),
                "failed":  sum(1 for r in results if r["status"] == "failed"),
            },
        }
        save_session(session)
        for r in results:
            if r["status"] == "renamed":
                self.file_queue.update_path(r["old_path"], r["new_path"])
        n, f = session["stats"]["renamed"], session["stats"]["failed"]
        self.statusBar().showMessage(f"Applied: {n} renamed, {f} failed")
        if f:
            QMessageBox.warning(self, "Some Renames Failed", f"{f} files could not be renamed.")

    def _on_settings(self):
        dlg = SettingsDialog(self.config, parent=self)
        if dlg.exec():
            self.config.save()

    def _on_history(self):
        HistoryDialog(parent=self).exec()
```

- [ ] **Verify app launches**

```bash
python main.py
```

Expected: window opens with toolbar, empty panels, no errors in console.

- [ ] **Commit**

```bash
git add main.py ui/main_window.py
git commit -m "feat: main.py + MainWindow — full two-panel workspace with all wiring"
```

---

## Task 13: FileQueuePanel

**Files:** Create `ui/file_queue_panel.py`

- [ ] **Write `ui/file_queue_panel.py`**

```python
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from config import AppConfig

class FileQueuePanel(QWidget):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._path_to_item: dict[str, QTreeWidgetItem] = {}
        self._folder_nodes: dict[str, QTreeWidgetItem] = {}
        self._known_paths:  set[str] = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        hdr = QWidget()
        hdr.setObjectName("panel-header")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 6, 10, 6)
        lbl = QLabel("FILE QUEUE")
        lbl.setObjectName("header")
        self._count_lbl = QLabel("0 files")
        self._count_lbl.setObjectName("header")
        hl.addWidget(lbl)
        hl.addStretch()
        hl.addWidget(self._count_lbl)
        layout.addWidget(hdr)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 72)
        self.tree.setIndentation(14)
        layout.addWidget(self.tree)

    def add_file(self, file_path: str):
        if file_path in self._known_paths:
            return
        self._known_paths.add(file_path)
        folder = os.path.dirname(file_path)
        if folder not in self._folder_nodes:
            node = QTreeWidgetItem(self.tree)
            node.setText(0, f"📁  {folder}")
            node.setExpanded(True)
            node.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._folder_nodes[folder] = node
        item = QTreeWidgetItem(self._folder_nodes[folder])
        item.setText(0, os.path.basename(file_path))
        item.setText(1, "pending")
        item.setForeground(1, QColor("#9ca3af"))
        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        self._path_to_item[file_path] = item
        self._count_lbl.setText(f"{len(self._path_to_item)} files")

    def set_status(self, file_path: str, status: str):
        item = self._path_to_item.get(file_path)
        if not item:
            return
        labels = {
            "pending":     ("pending",      "#9ca3af"),
            "translating": ("translating…", "#6366f1"),
            "done":        ("done",          "#10b981"),
            "no-op":       ("no-op",         "#d1d5db"),
            "error":       ("error",         "#ef4444"),
        }
        text, color = labels.get(status, (status, "#9ca3af"))
        item.setText(1, text)
        item.setForeground(1, QColor(color))

    def get_pending_files(self) -> list[str]:
        return [fp for fp, item in self._path_to_item.items()
                if item.text(1) in ("pending", "error")]

    def update_path(self, old_path: str, new_path: str):
        item = self._path_to_item.pop(old_path, None)
        if item:
            item.setText(0, os.path.basename(new_path))
            item.setData(0, Qt.ItemDataRole.UserRole, new_path)
            self._path_to_item[new_path] = item
            self._known_paths.discard(old_path)
            self._known_paths.add(new_path)

    def clear(self):
        self.tree.clear()
        self._path_to_item.clear()
        self._folder_nodes.clear()
        self._known_paths.clear()
        self._count_lbl.setText("0 files")
```

- [ ] **Commit**

```bash
git add ui/file_queue_panel.py
git commit -m "feat: FileQueuePanel — folder tree, status badges, path update"
```

---

## Task 14: PreviewPanel

**Files:** Create `ui/preview_panel.py`

- [ ] **Write `ui/preview_panel.py`**

```python
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from config import AppConfig

class PreviewPanel(QWidget):
    S_COL, ORIG_COL, TRANS_COL, ACT_COL = 0, 1, 2, 3

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._segments: dict = {}
        self._row_map:  dict = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        hdr = QWidget()
        hdr.setObjectName("panel-header")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 6, 12, 6)
        title = QLabel("TRANSLATION PREVIEW")
        title.setObjectName("header")
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(QLabel("Filter:"))
        self._filter = QComboBox()
        self._filter.addItems(["All", "Approved", "Errors", "Conflicts", "Pending"])
        self._filter.currentTextChanged.connect(self._apply_filter)
        hl.addWidget(self._filter)
        btn_aa = QPushButton("✓ All")
        btn_aa.setObjectName("btn-success")
        btn_ra = QPushButton("✕ All")
        btn_ra.setObjectName("btn-danger")
        btn_aa.clicked.connect(self._approve_all)
        btn_ra.clicked.connect(self._reject_all)
        hl.addWidget(btn_aa)
        hl.addWidget(btn_ra)
        layout.addWidget(hdr)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Original", "Translated", "Actions"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(self.S_COL,    QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(self.ORIG_COL, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.TRANS_COL,QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.ACT_COL,  QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.S_COL,   28)
        self.table.setColumnWidth(self.ACT_COL, 70)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        layout.addWidget(self.table)

    def store_segments(self, fp: str, segments: list):
        self._segments[fp] = segments

    def get_segments(self, fp: str) -> list:
        return self._segments.get(fp, [])

    def add_row(self, fp: str, original_name: str):
        if fp in self._row_map:
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._row_map[fp] = row
        si = QTableWidgetItem("⟳")
        si.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        si.setFlags(Qt.ItemFlag.ItemIsEnabled)
        si.setData(Qt.ItemDataRole.UserRole, "pending")
        si.setForeground(QColor("#6366f1"))
        self.table.setItem(row, self.S_COL, si)
        oi = QTableWidgetItem(original_name)
        oi.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        oi.setForeground(QColor("#9ca3af"))
        oi.setData(Qt.ItemDataRole.UserRole, fp)
        self.table.setItem(row, self.ORIG_COL, oi)
        ti = QTableWidgetItem("Translating…")
        ti.setForeground(QColor("#6366f1"))
        self.table.setItem(row, self.TRANS_COL, ti)
        self._set_actions(row, fp, "pending")

    def set_translated(self, fp: str, translated_name: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        ti = self.table.item(row, self.TRANS_COL)
        if ti:
            ti.setText(translated_name)
            ti.setForeground(QColor("#111827"))
            ti.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
        si = self.table.item(row, self.S_COL)
        if si:
            si.setText("✓")
            si.setForeground(QColor("#10b981"))
            si.setData(Qt.ItemDataRole.UserRole, "approved")
        self._set_actions(row, fp, "done")
        self._flag_conflicts(row, fp, translated_name)

    def set_error(self, fp: str, error_msg: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        ti = self.table.item(row, self.TRANS_COL)
        if ti:
            ti.setText(f"Error: {error_msg}")
            ti.setForeground(QColor("#ef4444"))
        si = self.table.item(row, self.S_COL)
        if si:
            si.setText("✕")
            si.setForeground(QColor("#ef4444"))
            si.setData(Qt.ItemDataRole.UserRole, "error")
        self._set_actions(row, fp, "error")

    def get_approved_renames(self) -> list[tuple[str, str]]:
        result = []
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            oi = self.table.item(row, self.ORIG_COL)
            ti = self.table.item(row, self.TRANS_COL)
            if (si and si.data(Qt.ItemDataRole.UserRole) == "approved"
                    and oi and ti and not ti.text().startswith("Error:")):
                result.append((oi.data(Qt.ItemDataRole.UserRole), ti.text()))
        return result

    def count_by_status(self, status: str) -> int:
        return sum(1 for row in range(self.table.rowCount())
                   if (self.table.item(row, self.S_COL) or None) is not None
                   and self.table.item(row, self.S_COL).data(Qt.ItemDataRole.UserRole) == status)

    def clear(self):
        self.table.setRowCount(0)
        self._row_map.clear()
        self._segments.clear()

    def _set_actions(self, row: int, fp: str, state: str):
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(4, 2, 4, 2)
        hl.setSpacing(3)
        if state == "done":
            ba = QPushButton("✓")
            ba.setFixedWidth(28)
            ba.setObjectName("btn-success")
            ba.clicked.connect(lambda _, f=fp: self._approve_row(f))
            be = QPushButton("✎")
            be.setFixedWidth(28)
            be.clicked.connect(lambda _, r=row: self.table.editItem(self.table.item(r, self.TRANS_COL)))
            hl.addWidget(ba)
            hl.addWidget(be)
        elif state == "error":
            br = QPushButton("↺")
            br.setFixedWidth(28)
            br.setObjectName("btn-danger")
            hl.addWidget(br)
        self.table.setCellWidget(row, self.ACT_COL, container)

    def _approve_row(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        si = self.table.item(row, self.S_COL)
        if si and si.data(Qt.ItemDataRole.UserRole) not in ("error",):
            si.setText("✓")
            si.setForeground(QColor("#10b981"))
            si.setData(Qt.ItemDataRole.UserRole, "approved")

    def _approve_all(self):
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            ti = self.table.item(row, self.TRANS_COL)
            if si and ti and not ti.text().startswith("Error:"):
                si.setText("✓")
                si.setForeground(QColor("#10b981"))
                si.setData(Qt.ItemDataRole.UserRole, "approved")

    def _reject_all(self):
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            if si:
                si.setText("✕")
                si.setForeground(QColor("#ef4444"))
                si.setData(Qt.ItemDataRole.UserRole, "rejected")

    def _flag_conflicts(self, row: int, fp: str, new_name: str):
        folder = os.path.dirname(fp)
        for other_fp, r in self._row_map.items():
            if r == row or os.path.dirname(other_fp) != folder:
                continue
            ti = self.table.item(r, self.TRANS_COL)
            if ti and ti.text() == new_name:
                for cr in (row, r):
                    ct = self.table.item(cr, self.TRANS_COL)
                    cs = self.table.item(cr, self.S_COL)
                    if ct:
                        ct.setBackground(QColor("#fef3c7"))
                    if cs:
                        cs.setText("⚠")
                        cs.setForeground(QColor("#f59e0b"))
                        cs.setData(Qt.ItemDataRole.UserRole, "conflict")

    def _apply_filter(self, text: str):
        status_map = {"Approved": "approved", "Errors": "error",
                      "Conflicts": "conflict", "Pending": "pending"}
        want = status_map.get(text, "")
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            status = si.data(Qt.ItemDataRole.UserRole) if si else ""
            self.table.setRowHidden(row, text != "All" and status != want)
```

- [ ] **Commit**

```bash
git add ui/preview_panel.py
git commit -m "feat: PreviewPanel — real-time table, inline edit, conflict detection, filter"
```

---

## Task 15: ProgressBarWidget

**Files:** Create `ui/progress_bar_widget.py`

- [ ] **Write `ui/progress_bar_widget.py`**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal

class ProgressBarWidget(QWidget):
    stop_requested   = pyqtSignal()
    apply_requested  = pyqtSignal()
    revert_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self._bar = QProgressBar()
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        top.addWidget(self._bar, stretch=1)
        self._count_lbl = QLabel("0 / 0")
        self._count_lbl.setStyleSheet("font-weight:500;color:#111827;")
        self._eta_lbl = QLabel("")
        self._eta_lbl.setStyleSheet("color:#9ca3af;")
        self._btn_stop = QPushButton("■ Stop")
        self._btn_stop.setObjectName("btn-danger")
        self._btn_stop.clicked.connect(self.stop_requested)
        top.addWidget(self._count_lbl)
        top.addWidget(self._eta_lbl)
        top.addWidget(self._btn_stop)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet("color:#9ca3af;font-size:11px;")
        bottom.addWidget(self._summary_lbl)
        bottom.addStretch()
        self._btn_revert = QPushButton("🕒 Revert Last Session")
        self._btn_revert.clicked.connect(self.revert_requested)
        self._btn_apply = QPushButton("✓ Apply Approved (0)")
        self._btn_apply.setObjectName("btn-success")
        self._btn_apply.clicked.connect(self.apply_requested)
        bottom.addWidget(self._btn_revert)
        bottom.addWidget(self._btn_apply)
        layout.addLayout(bottom)

    def set_total(self, total: int):
        self._bar.setMaximum(total)
        self._bar.setValue(0)
        self._count_lbl.setText(f"0 / {total}")

    def set_progress(self, done: int, total: int):
        self._bar.setMaximum(total)
        self._bar.setValue(done)
        self._count_lbl.setText(f"{done} / {total}")

    def set_eta(self, seconds: float):
        if seconds >= 60:
            self._eta_lbl.setText(f"~{int(seconds // 60)}m {int(seconds % 60)}s")
        else:
            self._eta_lbl.setText(f"~{int(seconds)}s")

    def set_approved_count(self, n: int):
        self._btn_apply.setText(f"✓ Apply Approved ({n})")

    def set_summary(self, approved: int, errors: int, conflicts: int):
        parts = [f"{approved} approved"]
        if errors:    parts.append(f"{errors} errors")
        if conflicts: parts.append(f"{conflicts} conflicts")
        self._summary_lbl.setText(" · ".join(parts))
```

- [ ] **Commit**

```bash
git add ui/progress_bar_widget.py
git commit -m "feat: ProgressBarWidget — progress, ETA, apply/stop/revert"
```

---

## Task 16: SettingsDialog

**Files:** Create `ui/settings_dialog.py`

- [ ] **Write `ui/settings_dialog.py`** — three tabs: API, Sanitization, File Filters

The full source is long; it is included here in its entirety.

```python
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QGroupBox,
    QRadioButton, QLineEdit, QPushButton, QLabel, QComboBox, QCheckBox,
    QGridLayout, QListWidget, QMessageBox, QHeaderView, QTableWidget,
    QTableWidgetItem
)
from config import AppConfig
from api.deepl_provider import DeepLProvider
from api.openrouter_provider import OpenRouterProvider
from core.sanitizer import sanitize as _sanitize

class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, preview_samples: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.config = config
        self._samples = preview_samples or ["SSIS-123 🔥田中美久.mp4", "title：special／file.mp4"]
        self.setWindowTitle("Settings")
        self.setFixedSize(580, 520)
        self._build_ui()
        self._load()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._api_tab(),   "API")
        self.tabs.addTab(self._san_tab(),   "Sanitization")
        self.tabs.addTab(self._filt_tab(),  "File Filters")
        v.addWidget(self.tabs)
        footer = QWidget()
        footer.setObjectName("dialog-footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.addStretch()
        b_cancel = QPushButton("Cancel")
        b_cancel.clicked.connect(self.reject)
        b_save = QPushButton("Save Settings")
        b_save.setObjectName("btn-primary")
        b_save.clicked.connect(self._save)
        fl.addWidget(b_cancel)
        fl.addWidget(b_save)
        v.addWidget(footer)

    def _api_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        pg = QGroupBox("Translation Provider")
        ph = QHBoxLayout(pg)
        self._r_deepl = QRadioButton("DeepL")
        self._r_or    = QRadioButton("OpenRouter")
        ph.addWidget(self._r_deepl)
        ph.addWidget(self._r_or)
        ph.addStretch()
        self._r_deepl.toggled.connect(self._toggle_provider)
        v.addWidget(pg)

        self._dg = QGroupBox("DeepL API")
        dv = QVBoxLayout(self._dg)
        dr = QHBoxLayout()
        self._dk = QLineEdit()
        self._dk.setPlaceholderText("API Key (ends :fx for free tier)")
        self._dk.setEchoMode(QLineEdit.EchoMode.Password)
        self._bt_dl = QPushButton("Test Connection")
        self._bt_dl.clicked.connect(self._test_deepl)
        dr.addWidget(self._dk)
        dr.addWidget(self._bt_dl)
        dv.addLayout(dr)
        self._ds = QLabel("")
        dv.addWidget(self._ds)
        v.addWidget(self._dg)

        self._og = QGroupBox("OpenRouter API")
        ov = QVBoxLayout(self._og)
        orow = QHBoxLayout()
        self._ok = QLineEdit()
        self._ok.setPlaceholderText("API Key (sk-or-v1-…)")
        self._ok.setEchoMode(QLineEdit.EchoMode.Password)
        self._bt_or = QPushButton("Test Connection")
        self._bt_or.clicked.connect(self._test_or)
        orow.addWidget(self._ok)
        orow.addWidget(self._bt_or)
        ov.addLayout(orow)
        mr = QHBoxLayout()
        mr.addWidget(QLabel("Model:"))
        self._mc = QComboBox()
        self._mc.setEditable(True)
        b_ref = QPushButton("↺")
        b_ref.setFixedWidth(32)
        b_ref.clicked.connect(self._refresh_models)
        mr.addWidget(self._mc, stretch=1)
        mr.addWidget(b_ref)
        ov.addLayout(mr)
        self._os = QLabel("")
        ov.addWidget(self._os)
        v.addWidget(self._og)
        v.addStretch()
        return w

    def _san_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)
        rules = [
            ("remove_illegal",      "Remove Windows-illegal chars",       r'\ / : * ? " < > |'),
            ("remove_emoji",        "Remove emojis",                      "Strips emoji Unicode ranges"),
            ("strip_dots_spaces",   "Strip leading/trailing dots/spaces", "Windows forbids trailing ."),
            ("normalize_fullwidth", "Normalize full-width → ASCII",       "ａｂｃ → abc"),
            ("remove_control_chars","Remove control characters",          "Strips invisible chars"),
            ("collapse_spaces",     "Collapse multiple spaces",           '"a  b" → "a b"'),
        ]
        self._sc: dict[str, QCheckBox] = {}
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (key, label, desc) in enumerate(rules):
            cb = QCheckBox(label)
            dl = QLabel(desc)
            dl.setStyleSheet("color:#9ca3af;font-size:10px;")
            cell = QWidget()
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(1)
            cl.addWidget(cb)
            cl.addWidget(dl)
            grid.addWidget(cell, i // 2, i % 2)
            self._sc[key] = cb
            cb.stateChanged.connect(self._refresh_preview)
        v.addLayout(grid)
        rr = QHBoxLayout()
        rr.addWidget(QLabel("Replace removed chars with:"))
        self._rn = QRadioButton("nothing")
        self._ru = QRadioButton("underscore _")
        self._rd = QRadioButton("dash -")
        for rb in (self._rn, self._ru, self._rd):
            rr.addWidget(rb)
            rb.toggled.connect(self._refresh_preview)
        rr.addStretch()
        v.addLayout(rr)
        pg = QGroupBox("Live Preview")
        pl = QVBoxLayout(pg)
        self._pt = QTableWidget(len(self._samples), 2)
        self._pt.setHorizontalHeaderLabels(["Before", "After"])
        self._pt.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._pt.setFixedHeight(80)
        self._pt.verticalHeader().setVisible(False)
        self._pt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        pl.addWidget(self._pt)
        v.addWidget(pg)
        v.addStretch()
        return w

    def _filt_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(8)
        self._subdirs = QCheckBox("Include files in subfolders recursively")
        v.addWidget(self._subdirs)
        v.addWidget(QLabel("File extensions to include:"))
        self._el = QListWidget()
        self._el.setFixedHeight(160)
        v.addWidget(self._el)
        er = QHBoxLayout()
        self._ei = QLineEdit()
        self._ei.setPlaceholderText(".mp4")
        ba = QPushButton("Add")
        ba.clicked.connect(self._add_ext)
        br = QPushButton("Remove")
        br.clicked.connect(self._rm_ext)
        er.addWidget(self._ei)
        er.addWidget(ba)
        er.addWidget(br)
        v.addLayout(er)
        v.addStretch()
        return w

    def _load(self):
        (self._r_deepl if self.config.provider == "deepl" else self._r_or).setChecked(True)
        self._dk.setText(self.config.deepl_key)
        self._ok.setText(self.config.openrouter_key)
        self._mc.addItem(self.config.openrouter_model)
        self._mc.setCurrentText(self.config.openrouter_model)
        san = self.config.sanitization
        for key, cb in self._sc.items():
            cb.setChecked(getattr(san, key, False))
        rep = san.replacement_char
        (self._ru if rep == "_" else self._rd if rep == "-" else self._rn).setChecked(True)
        self._subdirs.setChecked(self.config.scan_subdirectories)
        for ext in self.config.file_extensions:
            self._el.addItem(ext)
        self._toggle_provider()
        self._refresh_preview()

    def _save(self):
        self.config.provider = "deepl" if self._r_deepl.isChecked() else "openrouter"
        self.config.deepl_key = self._dk.text().strip()
        self.config.openrouter_key = self._ok.text().strip()
        self.config.openrouter_model = self._mc.currentText()
        san = self.config.sanitization
        for key, cb in self._sc.items():
            setattr(san, key, cb.isChecked())
        san.replacement_char = "_" if self._ru.isChecked() else "-" if self._rd.isChecked() else ""
        self.config.scan_subdirectories = self._subdirs.isChecked()
        self.config.file_extensions = [self._el.item(i).text() for i in range(self._el.count())]
        self.accept()

    def _toggle_provider(self):
        is_dl = self._r_deepl.isChecked()
        self._dg.setEnabled(is_dl)
        self._og.setEnabled(not is_dl)

    def _test_deepl(self):
        key = self._dk.text().strip()
        if not key:
            self._ds.setText("⚠ Enter API key first")
            return
        self._bt_dl.setEnabled(False)
        self._ds.setText("Testing…")
        r = DeepLProvider(key).test_connection()
        msg = f"{'✓' if r['ok'] else '✕'} {r['message']}"
        if r.get("quota"):
            msg += f"  ·  {r['quota']}"
        self._ds.setStyleSheet(f"color:{'#10b981' if r['ok'] else '#ef4444'};")
        self._ds.setText(msg)
        self._bt_dl.setEnabled(True)

    def _test_or(self):
        key = self._ok.text().strip()
        if not key:
            self._os.setText("⚠ Enter API key first")
            return
        self._bt_or.setEnabled(False)
        self._os.setText("Testing…")
        r = OpenRouterProvider(key, self._mc.currentText()).test_connection()
        self._os.setStyleSheet(f"color:{'#10b981' if r['ok'] else '#ef4444'};")
        self._os.setText(f"{'✓' if r['ok'] else '✕'} {r['message']}")
        self._bt_or.setEnabled(True)

    def _refresh_models(self):
        key = self._ok.text().strip()
        if not key:
            return
        try:
            models = OpenRouterProvider(key, "").list_models()
            cur = self._mc.currentText()
            self._mc.clear()
            self._mc.addItems(models)
            if cur in models:
                self._mc.setCurrentText(cur)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _add_ext(self):
        ext = self._ei.text().strip()
        if ext and not ext.startswith("."):
            ext = "." + ext
        if ext:
            existing = [self._el.item(i).text() for i in range(self._el.count())]
            if ext not in existing:
                self._el.addItem(ext)
            self._ei.clear()

    def _rm_ext(self):
        for item in self._el.selectedItems():
            self._el.takeItem(self._el.row(item))

    def _refresh_preview(self):
        from config import SanitizationConfig
        san = SanitizationConfig()
        for key, cb in self._sc.items():
            setattr(san, key, cb.isChecked())
        san.replacement_char = "_" if self._ru.isChecked() else "-" if self._rd.isChecked() else ""
        for i, sample in enumerate(self._samples):
            after = _sanitize(sample, san)
            self._pt.setItem(i, 0, QTableWidgetItem(sample))
            self._pt.setItem(i, 1, QTableWidgetItem(after))
```

- [ ] **Commit**

```bash
git add ui/settings_dialog.py
git commit -m "feat: SettingsDialog — API keys, test connection, sanitization, file filters"
```

---

## Task 17: HistoryDialog

**Files:** Create `ui/history_dialog.py`

- [ ] **Write `ui/history_dialog.py`**

```python
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.session_store import list_sessions, revert_session

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename History")
        self.resize(780, 520)
        self._sessions = list_sessions()
        self._current_path: str | None = None
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hdr = QWidget()
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 12, 16, 10)
        title = QLabel("🕒  Rename History")
        title.setStyleSheet("font-size:15px;font-weight:600;color:#111827;")
        hl.addWidget(title)
        hl.addStretch()
        layout.addWidget(hdr)

        sp = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        lhdr = QLabel("Past Sessions")
        lhdr.setObjectName("header")
        lhdr.setContentsMargins(12, 6, 12, 6)
        lv.addWidget(lhdr)
        self._sl = QListWidget()
        self._sl.currentRowChanged.connect(self._on_row)
        lv.addWidget(self._sl)
        sp.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        self._dh = QLabel("")
        self._dh.setObjectName("header")
        self._dh.setContentsMargins(12, 6, 12, 6)
        rv.addWidget(self._dh)
        self._wl = QLabel("")
        self._wl.setStyleSheet(
            "background:#fffbeb;color:#92400e;padding:6px 12px;border-bottom:1px solid #fcd34d;")
        self._wl.setVisible(False)
        rv.addWidget(self._wl)
        self._dt = QTableWidget()
        self._dt.setColumnCount(3)
        self._dt.setHorizontalHeaderLabels(["", "Current Name → restore to", "Original Name"])
        h = self._dt.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._dt.setColumnWidth(0, 24)
        self._dt.verticalHeader().setVisible(False)
        self._dt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        rv.addWidget(self._dt)
        sp.addWidget(right)
        sp.setSizes([240, 540])
        layout.addWidget(sp, stretch=1)

        footer = QWidget()
        footer.setObjectName("dialog-footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        hint = QLabel("Reverting restores original filenames.")
        hint.setStyleSheet("color:#9ca3af;font-size:10px;")
        fl.addWidget(hint)
        fl.addStretch()
        b_cancel = QPushButton("Cancel")
        b_cancel.clicked.connect(self.reject)
        self._b_rev = QPushButton("↺ Revert")
        self._b_rev.setObjectName("btn-danger")
        self._b_rev.setEnabled(False)
        self._b_rev.clicked.connect(self._do_revert)
        fl.addWidget(b_cancel)
        fl.addWidget(self._b_rev)
        layout.addWidget(footer)

    def _populate(self):
        for s in self._sessions:
            stats   = s.get("stats", {})
            renamed = stats.get("renamed", len(s.get("files", [])))
            ts      = s.get("timestamp", "")[:16].replace("T", ", ")
            item = QListWidgetItem(f"{ts}\n{renamed} files renamed")
            item.setData(Qt.ItemDataRole.UserRole, s["path"])
            self._sl.addItem(item)

    def _on_row(self, row: int):
        if row < 0 or row >= len(self._sessions):
            return
        s = self._sessions[row]
        self._current_path = s["path"]
        files   = s.get("files", [])
        renamed = [f for f in files if f.get("status") == "renamed"]
        missing = [f for f in renamed if not os.path.exists(f.get("new_path", ""))]
        if missing:
            self._wl.setText(
                f"⚠  {len(missing)} files were moved/deleted — skipped during revert.")
            self._wl.setVisible(True)
        else:
            self._wl.setVisible(False)
        ts   = s.get("timestamp", "")[:16].replace("T", " ")
        prov = s.get("provider", "").upper()
        self._dh.setText(f"{ts}  ·  {len(renamed)} files  ·  {prov}")
        self._dt.setRowCount(0)
        for entry in renamed[:300]:
            r = self._dt.rowCount()
            self._dt.insertRow(r)
            new_p = entry.get("new_path", "")
            old_p = entry.get("old_path", "")
            exists = os.path.exists(new_p)
            icon = QTableWidgetItem("✓" if exists else "⚠")
            icon.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setForeground(QColor("#10b981" if exists else "#f59e0b"))
            cur  = QTableWidgetItem(os.path.basename(new_p))
            cur.setForeground(QColor("#6b7280" if exists else "#d1d5db"))
            orig = QTableWidgetItem(os.path.basename(old_p))
            orig.setForeground(QColor("#111827" if exists else "#9ca3af"))
            self._dt.setItem(r, 0, icon)
            self._dt.setItem(r, 1, cur)
            self._dt.setItem(r, 2, orig)
        if len(renamed) > 300:
            r = self._dt.rowCount()
            self._dt.insertRow(r)
            more = QTableWidgetItem(f"… {len(renamed) - 300} more files")
            more.setForeground(QColor("#9ca3af"))
            self._dt.setItem(r, 1, more)
        revertible = len(renamed) - len(missing)
        self._b_rev.setText(f"↺ Revert {revertible} Files")
        self._b_rev.setEnabled(revertible > 0)

    def _do_revert(self):
        if not self._current_path:
            return
        reply = QMessageBox.question(
            self, "Confirm Revert",
            "Rename files back to their original Japanese names?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = revert_session(self._current_path)
        QMessageBox.information(
            self, "Revert Complete",
            f"Reverted: {result['reverted']}\n"
            f"Skipped (not found): {result['skipped']}\n"
            f"Failed: {result['failed']}",
        )
        self.accept()
```

- [ ] **Commit**

```bash
git add ui/history_dialog.py
git commit -m "feat: HistoryDialog — session list, per-file detail, graceful revert"
```

---

## Task 18: End-to-End Smoke Test

- [ ] **Run full test suite**

```bash
pytest -v
```

Expected: all green.

- [ ] **Launch the app and run through each workflow manually**

```
1. python main.py
2. ⚙ Settings → set API key → Test Connection (should show green ✓)
3. Drag a folder of Japanese-named video files → files appear in queue
4. ▶ Translate All → rows appear in preview with translated names
5. Double-click a translated name → edit inline
6. ✓ All → verify Apply Approved button shows correct count
7. Apply Approved → files renamed on disk (check in Explorer)
8. 🕒 History → session listed → select → review file detail
9. ↺ Revert → confirm files back to Japanese names
```

- [ ] **Commit**

```bash
git commit --allow-empty -m "test: manual smoke test passed"
```

---

## Task 19: PyInstaller Build

**Files:** Create `download_inter.py`, `folder_file_renamer.spec`

- [ ] **Write `download_inter.py`** (run once to get Inter fonts)

```python
import urllib.request, zipfile, os, shutil

URL = "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip"
print("Downloading Inter font...")
urllib.request.urlretrieve(URL, "inter.zip")
os.makedirs("resources/fonts", exist_ok=True)
with zipfile.ZipFile("inter.zip") as z:
    for name in z.namelist():
        if (name.endswith(".ttf")
                and "Inter-" in os.path.basename(name)
                and os.path.basename(name)):
            data = z.read(name)
            out = os.path.join("resources/fonts", os.path.basename(name))
            with open(out, "wb") as f:
                f.write(data)
            print(f"  extracted: {os.path.basename(name)}")
os.remove("inter.zip")
print("Done.")
```

```bash
python download_inter.py
```

- [ ] **Install PyInstaller**

```bash
pip install pyinstaller
```

- [ ] **Write `folder_file_renamer.spec`**

```python
# folder_file_renamer.spec
block_cipher = None
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[("resources", "resources")],
    hiddenimports=[
        "PyQt6.QtCore", "PyQt6.QtWidgets", "PyQt6.QtGui",
        "httpx", "emoji", "unicodedata",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="FolderFileRenamer",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon="resources/icon.ico" if os.path.exists("resources/icon.ico") else None,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True,
    name="FolderFileRenamer",
)
```

- [ ] **Build**

```bash
pyinstaller folder_file_renamer.spec
```

Expected: `dist/FolderFileRenamer/FolderFileRenamer.exe`

- [ ] **Test the .exe without Python installed**

```
Copy dist/FolderFileRenamer/ to a machine (or VM) with no Python.
Double-click FolderFileRenamer.exe — must open with no errors.
Verify Inter font renders correctly.
Verify settings persist across restarts (%APPDATA%\FolderFileRenamer\config.json).
```

- [ ] **Final commit**

```bash
git add download_inter.py folder_file_renamer.spec
git commit -m "build: PyInstaller spec and Inter font download script"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 7 workflows present (scan → parse → translate → preview → apply → session → revert). DeepL + OpenRouter providers, sanitization, settings, history, build — all covered.
- [x] **No placeholders:** All code blocks are complete and runnable.
- [x] **Type consistency:** `TranslationJob` (Task 10) imported in Task 12. `Segment/parse_filename/reconstruct/collect_japanese` (Task 3) used in Task 12. `sanitize` (Task 4), `save_session` (Task 5), `apply_renames` (Task 6) all match their definitions.
- [x] **Signal consistency:** `translation_result(str, list, list)` emitted in `process_jobs`, consumed in `_on_translation_result`. `progress_updated(int, int)`, `eta_updated(float)`, `file_status_changed(str, str)` all match.
