import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app_metadata import APP_VERSION, GITHUB_OWNER, GITHUB_REPO
from core.update_checker import UpdateInfo, check_for_update, download_update


def default_update_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(base) / "FolderFileRenamer" / "updates"


class UpdateCheckWorker(QThread):
    update_checked = pyqtSignal(object)
    update_error = pyqtSignal(str)

    def run(self):
        try:
            self.update_checked.emit(check_for_update(APP_VERSION, GITHUB_OWNER, GITHUB_REPO))
        except Exception as e:
            self.update_error.emit(str(e))


class UpdateDownloadWorker(QThread):
    download_progress = pyqtSignal(int, int)
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, update_info: UpdateInfo, target_dir: Path | None = None, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.target_dir = target_dir or default_update_dir()

    def run(self):
        try:
            path = download_update(
                self.update_info,
                self.target_dir,
                progress_callback=self.download_progress.emit,
            )
            self.download_finished.emit(str(path))
        except Exception as e:
            self.download_error.emit(str(e))
