import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_window_title_includes_app_version():
    from PyQt6.QtWidgets import QApplication
    from app_metadata import APP_VERSION
    from config import AppConfig
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(AppConfig(check_updates_on_startup=False))

    assert window.windowTitle() == f"Folder File Renamer v{APP_VERSION}"
