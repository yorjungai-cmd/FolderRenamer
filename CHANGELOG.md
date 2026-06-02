# Changelog

All notable changes to Folder File Renamer are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.2.5] — 2026-06-02

### Added
- **Issues filter** — new `⚠ Issues` button in the preview header narrows the table to only rows with status `error`, `conflict`, or `pending` (everything that blocks a clean rename). The same filter is available in the Filter dropdown as "Issues".
- **Auto-focus on issues** — when a batch translation finishes and any errors or conflicts remain, the view automatically switches to the Issues filter so the user lands directly on rows that need attention.

---

## [0.2.4] — 2026-06-02

### Performance
- **Single repaint at batch end** — `end_bulk` now wraps conflict rechecks, action-widget creation for all rows, and the filter pass inside one `setUpdatesEnabled(False)` block. The table repaints once instead of once per file.
- **Filter changes suppress per-row repaints** — selecting a filter item on a large table now costs one repaint instead of one per row.
- **O(N) conflict detection** — `_recheck_all_conflicts_in_folder` was O(N²) (called `_flag_conflicts` for every row); rewritten to build a name-count map in one pass, then mark/clear conflicts in a second pass.
- **O(1) status counters** — `approved_count`, `count_by_status("error")`, and `count_by_status("conflict")` are now maintained incrementally as rows change state; no full table scan needed for batch-end summary.
- **Action widgets deferred during bulk** — during a batch translation, `_set_actions` is no longer called per result; `end_bulk` creates all action widgets in one batched pass.

### Fixed
- `add_row` wrapped all `setItem` calls in `blockSignals` — previously adding a row triggered `_on_item_changed` (the user-edit handler) which created spurious action buttons for "Translating…" rows.
- **Trim All deduplication against stable files** — if a file trimmed to a name already held by an untrimmed row, it kept the colliding name. The deduplication now pre-populates `in_use` from all non-trimmed rows before assigning suffixes.

---

## [0.2.3] — 2026-06-02

### Performance
- **Translate All no longer freezes on large batches** — introduced `begin_bulk` / `end_bulk` on `PreviewPanel`. During a batch: per-result filter reapplication (was O(N) × N = O(N²)) and conflict rechecks (same) are deferred. On `end_bulk`, one filter pass and one conflict recheck per distinct folder run instead.
- `add_row` loop wrapped in `setUpdatesEnabled(False)` / `setSortingEnabled(False)` to suppress 1 400+ layout recalculations during bulk table population.
- `get_approved_renames` call in `_on_translation_result` throttled to every 50 results (was every result, O(N) × N = O(N²)).

---

## [0.2.2] — 2026-06-01

### Added
- **✂ Trim All** — new button in the preview header trims every filename exceeding the configured length limit in one click; defers individual filter and conflict rechecks to a single batched pass at the end.
- **Smart suffix deduplication** — when Trim All causes multiple files in the same folder to resolve to the same name, they are renamed `stem_2.ext`, `stem_3.ext`, … avoiding collisions with each other and with untrimmed rows.
- **Per-row retry** — error rows now show a ↺ button that re-translates that single file without restarting the full batch.

### Fixed
- `mark_applied` now sets the row's UserRole to `"applied"`, making applied rows distinguishable from approved rows in all subsequent logic.
- Retry button (↺) was created but never connected; it now emits `retry_requested` and `MainWindow._on_retry_file` handles it.
- `_trim_all` previously processed rejected, applied, pending, and error rows; it now skips them via UserRole check.
- `_recheck_all_conflicts_in_folder` and `_approve_all` detected error state via `text.startswith("Error:")` text prefix rather than UserRole; switched to canonical UserRole checks.
- `_trim_all` called `_trim_row` per file, each triggering a full O(N) folder conflict recheck → O(N²) total; rewritten to batch all text changes then recheck once per distinct folder.

---

## [0.2.1] — 2026-05-31

### Fixed
- App version is now shown in the window title bar (`Folder File Renamer v0.2.1`).

---

## [0.2.0] — 2026-05-30

Initial public release.

### Added
- Batch Japanese → English filename translation via DeepL or any OpenRouter LLM.
- Smart filename parsing: preserves studio codes, resolution tags, bracketed labels, years; only sends CJK text to the API.
- Preview table with per-file approve / reject / inline-edit workflow.
- Conflict detection and visual highlighting for duplicate translated names.
- Filename length guard: yellow ≥ 200 chars, red ≥ 255 chars; configurable autotrim soft limit.
- Filename sanitization: emojis, Windows-illegal chars, full-width → ASCII, trailing dots, control chars, double spaces.
- Atomic apply with full session history and per-session revert.
- Recursive folder scan (QThread) with cancel support.
- Batched translation worker (QThread) with ETA, cancel, and per-batch delay.
- Settings dialog: API keys, provider, model, sanitization rules, file-type filter, autotrim limit.
- History dialog: session browser, per-file detail, revert action.
- In-app updater: checks GitHub Releases, downloads EXE, verifies SHA256, opens download folder.
- PyInstaller single-file EXE build.
- GitHub Actions CI: builds EXE and publishes GitHub Release on version tag.
