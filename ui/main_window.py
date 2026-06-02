import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QFileDialog, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from app_metadata import APP_VERSION
from config import AppConfig
from core.update_checker import UpdateInfo
from core.filename_parser import parse_filename, collect_japanese, reconstruct
from core.sanitizer import sanitize
from core.rename_engine import (
    check_conflicts, check_filesystem_conflicts, check_missing_sources,
    apply_renames, safe_filename_length
)
from core.session_store import save_session
from api.deepl_provider import DeepLProvider
from api.openrouter_provider import OpenRouterProvider
from workers.scan_worker import ScanWorker
from workers.translation_worker import TranslationWorker, TranslationJob
from workers.update_worker import UpdateCheckWorker, UpdateDownloadWorker
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
        self._update_worker: UpdateCheckWorker | UpdateDownloadWorker | None = None
        self._update_progress: QProgressDialog | None = None
        self.setWindowTitle("Folder File Renamer")
        self.setMinimumSize(1000, 600)
        self.resize(1280, 720)
        self.setAcceptDrops(True)
        self._build_ui()
        self._connect_signals()
        if self.config.check_updates_on_startup:
            QTimer.singleShot(1500, self._check_updates_on_startup)

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
        self.btn_clear = QPushButton("✕ Clear")
        self.btn_clear.setObjectName("btn-danger")
        h.addWidget(self.btn_add_folder)
        h.addWidget(self.btn_add_files)
        h.addWidget(self.btn_clear)
        h.addStretch()
        self.btn_translate = QPushButton("▶ Translate All")
        self.btn_translate.setObjectName("btn-success")
        self.btn_settings = QPushButton("⚙  Settings")
        self.btn_history = QPushButton("🕒  History")
        self.btn_updates = QPushButton("↻  Updates")
        h.addWidget(self.btn_translate)
        h.addWidget(self.btn_updates)
        h.addWidget(self.btn_settings)
        h.addWidget(self.btn_history)
        return bar

    def _connect_signals(self):
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_translate.clicked.connect(self._on_translate_all)
        self.btn_updates.clicked.connect(self._on_check_updates)
        self.btn_settings.clicked.connect(self._on_settings)
        self.btn_history.clicked.connect(self._on_history)
        self.progress_bar.stop_requested.connect(self._on_stop)
        self.progress_bar.apply_requested.connect(self._on_apply)
        self.progress_bar.revert_requested.connect(self._on_history)

    def _check_updates_on_startup(self):
        self._start_update_check(manual=False)

    def _on_check_updates(self):
        self._start_update_check(manual=True)

    def _start_update_check(self, manual: bool):
        if self._update_worker and self._update_worker.isRunning():
            if manual:
                QMessageBox.information(self, "Updates", "An update check is already running.")
            return
        if manual:
            self.statusBar().showMessage("Checking for updates...")
        self.btn_updates.setEnabled(False)
        worker = UpdateCheckWorker()
        worker.update_checked.connect(lambda info, m=manual: self._on_update_checked(info, m))
        worker.update_error.connect(lambda message, m=manual: self._on_update_error(message, m))
        worker.finished.connect(lambda: self.btn_updates.setEnabled(True))
        worker.finished.connect(lambda: self._clear_update_worker(worker))
        self._update_worker = worker
        worker.start()

    def _clear_update_worker(self, worker):
        if self._update_worker is worker:
            self._update_worker = None

    def _on_update_error(self, message: str, manual: bool):
        self.statusBar().clearMessage()
        if manual:
            QMessageBox.warning(self, "Update Check Failed", message)

    def _on_update_checked(self, info: UpdateInfo, manual: bool):
        self.statusBar().clearMessage()
        if not info.update_available:
            if manual:
                QMessageBox.information(
                    self,
                    "No Updates",
                    info.message or f"Version {APP_VERSION} is the latest version.",
                )
            return
        self._prompt_for_update(info)

    def _prompt_for_update(self, info: UpdateInfo):
        box = QMessageBox(self)
        box.setWindowTitle("Update Available")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"Folder File Renamer {info.latest_version} is available.")
        box.setInformativeText(
            f"You are running {info.current_version}. Download the verified update now?"
        )
        if info.notes:
            box.setDetailedText(info.notes[:4000])
        download_btn = box.addButton("Download", QMessageBox.ButtonRole.AcceptRole)
        release_btn = box.addButton("Open Release", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is download_btn:
            self._start_update_download(info)
        elif clicked is release_btn and info.release_url:
            QDesktopServices.openUrl(QUrl(info.release_url))

    def _start_update_download(self, info: UpdateInfo):
        if self._update_worker and self._update_worker.isRunning():
            QMessageBox.information(self, "Updates", "An update operation is already running.")
            return
        progress = QProgressDialog("Downloading update...", "Cancel", 0, max(info.asset_size, 1), self)
        progress.setCancelButton(None)
        progress.setWindowTitle("Downloading Update")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        self._update_progress = progress

        worker = UpdateDownloadWorker(info)
        worker.download_progress.connect(self._on_update_download_progress)
        worker.download_finished.connect(self._on_update_download_finished)
        worker.download_error.connect(self._on_update_download_error)
        worker.finished.connect(lambda: self._clear_update_worker(worker))
        self._update_worker = worker
        worker.start()

    def _on_update_download_progress(self, current: int, total: int):
        if not self._update_progress:
            return
        if total > 0 and self._update_progress.maximum() != total:
            self._update_progress.setMaximum(total)
        self._update_progress.setValue(current)

    def _on_update_download_finished(self, path: str):
        if self._update_progress:
            self._update_progress.close()
            self._update_progress = None
        folder = os.path.dirname(path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        QMessageBox.information(
            self,
            "Update Ready",
            "The update was downloaded and verified.\n\n"
            "Close Folder File Renamer, then run the downloaded EXE or replace your current copy.",
        )

    def _on_update_download_error(self, message: str):
        if self._update_progress:
            self._update_progress.close()
            self._update_progress = None
        QMessageBox.warning(self, "Update Download Failed", message)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self._start_scan([url.toLocalFile() for url in event.mimeData().urls()])

    def _on_clear(self):
        if self._translation_worker:
            self._translation_worker.cancel()
        self.file_queue.clear()
        self.preview.clear()
        self.progress_bar.reset()
        self.statusBar().clearMessage()

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
        worker.start()
        self._scan_workers.append(worker)

        def _on_finished(n, w=worker):
            self.statusBar().showMessage(f"{n} files scanned")
            if w in self._scan_workers:
                self._scan_workers.remove(w)

        worker.finished.connect(_on_finished)

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
        sanitized = sanitize(reconstructed, self.config.sanitization)
        limit = self.config.max_filename_chars
        if limit > 0 and len(sanitized) > limit:
            sanitized = sanitized[:limit].rstrip()
        stem = safe_filename_length(sanitized, ext)
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
        fs_conflicts = check_filesystem_conflicts(renames)
        if fs_conflicts:
            QMessageBox.warning(
                self, "Files Already Exist",
                f"{len(fs_conflicts)} target filenames already exist on disk. "
                "Edit the translations to use unique names before applying."
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
                self.preview.mark_applied(r["old_path"])
                self.file_queue.update_path(r["old_path"], r["new_path"])
            else:
                self.preview.mark_failed(r["old_path"])
        n, f = session["stats"]["renamed"], session["stats"]["failed"]
        self.statusBar().showMessage(f"Applied: {n} renamed, {f} failed")
        def _s(count): return "s" if count != 1 else ""
        if f:
            QMessageBox.warning(
                self, "Apply Complete",
                f"{n} file{_s(n)} renamed successfully.\n{f} file{_s(f)} could not be renamed."
            )
        else:
            QMessageBox.information(
                self, "Apply Complete",
                f"✓ {n} file{_s(n)} renamed successfully."
            )

    def closeEvent(self, event):
        # Cancel any in-progress workers before closing
        for w in self._scan_workers:
            w.cancel()
        if self._translation_worker:
            self._translation_worker.cancel()
        event.accept()

    def _on_settings(self):
        dlg = SettingsDialog(self.config, parent=self)
        if dlg.exec():
            self.config.save()

    def _on_history(self):
        HistoryDialog(parent=self).exec()
