# Folder File Renamer

Windows desktop app that batch-translates Japanese filenames to English using DeepL or an OpenRouter LLM, with a preview-and-confirm workflow and session-based revert.

---

## Features

- **Add Folder / Add Files / Clear** — browse or drag-and-drop; clear resets everything including any in-progress translation
- **Smart parsing** — studio codes (`SSIS-123`), resolution tags (`4K`, `1080p`), bracketed labels (`[Uncensored]`) and years are preserved; only CJK text is sent for translation
- **Dual provider** — DeepL (batch of 50) or any OpenRouter model (batch of 5); configurable in Settings
- **Preview table** — per-file approve / reject / inline edit before committing any renames
- **Filename length guard** — translated names >= 200 chars turn yellow (warning), >= 255 chars turn red; optional autotrim limit in Settings
- **Sanitization** — strip emojis, Windows-illegal chars, full-width to ASCII, trailing dots, control chars, double spaces
- **Apply & Revert** — renames are written atomically; every session is saved to `%APPDATA%\FolderFileRenamer\sessions\` and can be reverted from the History dialog
- **Guided updates** — checks GitHub Releases for newer stable builds, downloads the EXE, verifies SHA256, then opens the update folder
- **Single-file EXE** — ships as one self-contained `FolderFileRenamer.exe`

---

## Quick Start

### Run from source

```bash
pip install -r requirements.txt
python main.py
```

### Build single-file EXE

```bash
pyinstaller folder_file_renamer.spec --clean
# output: dist\FolderFileRenamer.exe
```

---

## Requirements

| Package | Version |
|---------|---------|
| Python  | 3.11+   |
| PyQt6   | >= 6.6  |
| httpx   | >= 0.27 |
| emoji   | >= 2.12 |
| pytest  | >= 8.0 (dev) |

```bash
pip install -r requirements.txt
```

---

## Project Structure

```
Folder File Renamer/
├── main.py                    # Entry point — loads config, stylesheet, launches window
├── config.py                  # AppConfig + SanitizationConfig (persisted to %APPDATA%)
├── folder_file_renamer.spec   # PyInstaller single-file build spec
│
├── core/
│   ├── filename_parser.py     # CJK segment extraction, preserving studio codes & tags
│   ├── sanitizer.py           # Configurable filename cleaning rules
│   ├── rename_engine.py       # Conflict check, apply renames, safe_filename_length
│   └── session_store.py       # JSON session persistence, revert, auto-prune (max 50)
│
├── api/
│   ├── base_provider.py       # Abstract BaseProvider interface
│   ├── deepl_provider.py      # DeepL free/pro batch translation + connection test
│   └── openrouter_provider.py # OpenRouter LLM translation + model listing
│
├── workers/
│   ├── scan_worker.py         # QThread — recursive folder scan with cancel support
│   └── translation_worker.py  # QThread — batched translation with ETA and cancel
│
├── ui/
│   ├── main_window.py         # QMainWindow — toolbar, splitter, drag-drop, apply logic
│   ├── file_queue_panel.py    # Left panel — folder tree with per-file status badges
│   ├── preview_panel.py       # Right panel — translation table, approve/reject, length warnings
│   ├── progress_bar_widget.py # Bottom bar — progress, ETA, Apply / Stop / Revert buttons
│   ├── settings_dialog.py     # API keys, sanitization rules, file filters, autotrim
│   └── history_dialog.py      # Session list + per-file detail + revert action
│
├── resources/
│   ├── styles.qss             # Indigo-accent light theme (Inter font)
│   ├── fonts/                 # Inter TTF variants (bundled in EXE)
│   └── icon.ico
│
└── tests/
    ├── test_config.py
    ├── test_filename_parser.py
    ├── test_sanitizer.py
    ├── test_session_store.py
    ├── test_rename_engine.py
    ├── test_deepl_provider.py
    └── test_openrouter_provider.py
```

---

## Configuration

Settings are persisted to `%APPDATA%\FolderFileRenamer\config.json`.

| Setting | Default | Description |
|---------|---------|-------------|
| `provider` | `deepl` | `deepl` or `openrouter` |
| `deepl_key` | — | DeepL API key (append `:fx` for free tier) |
| `openrouter_key` | — | OpenRouter API key (`sk-or-v1-...`) |
| `openrouter_model` | `google/gemini-flash-1.5` | Any model ID from OpenRouter |
| `file_extensions` | `.mp4 .mkv .avi ...` | Extensions to include when scanning folders |
| `scan_subdirectories` | `true` | Recurse into subfolders |
| `max_filename_chars` | `0` (off) | Autotrim stem to this many chars (0 = disabled) |
| `batch_delay_ms` | `200` | Delay between API batches (ms) |
| `request_timeout_s` | `30` | HTTP timeout per request (s) |
| `check_updates_on_startup` | `true` | Check GitHub Releases for stable updates when the app starts |

---

## Updates & Releases

The app checks the latest stable GitHub Release from `yorjungai-cmd/FolderRenamer`. It downloads `FolderFileRenamer-vX.Y.Z.exe`, verifies it against `FolderFileRenamer-vX.Y.Z.exe.sha256`, then opens the downloaded file location. It does not overwrite the running EXE automatically.

To publish a client update:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The release workflow builds the PyInstaller EXE and attaches the EXE plus SHA256 file to the GitHub Release.

---

## Filename Length Behaviour

Windows NTFS allows up to **255 characters** per filename component. However, deeply nested paths can hit the 260-char MAX_PATH limit even with shorter filenames.

| Translated name length | Preview colour | Meaning |
|------------------------|---------------|---------|
| < 200 chars | Normal (dark) | Safe |
| 200 – 254 chars | Yellow | Warning — may cause issues in deep paths |
| >= 255 chars | Red | At NTFS limit — stem was auto-trimmed |

The hard trim (255-byte UTF-8) runs in `core/rename_engine.safe_filename_length` and always applies. The configurable soft limit (`max_filename_chars`) runs first, in Settings > Sanitization.

---

## Running Tests

```bash
pytest -v
```

Core logic (`filename_parser`, `sanitizer`, `rename_engine`, `session_store`, API providers) is pure Python — no Qt dependency — and is fully unit-tested.

---

## Session History & Revert

Every "Apply" writes a timestamped JSON file to `%APPDATA%\FolderFileRenamer\sessions\`. Open **History** (toolbar) to browse sessions and revert any of them. Sessions are pruned to the 50 most recent.
