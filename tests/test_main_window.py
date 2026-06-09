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


def test_set_application_icon_loads_existing_resource(tmp_path):
    from PyQt6.QtWidgets import QApplication
    from main import set_application_icon

    app = QApplication.instance() or QApplication([])
    source_icon = os.path.join(
        os.path.dirname(__file__), "..", "resources", "icon.ico"
    )
    icon_path = tmp_path / "icon.ico"
    with open(source_icon, "rb") as source:
        icon_path.write_bytes(source.read())

    assert set_application_icon(app, icon_path) is True
    assert app.windowIcon().isNull() is False


def test_set_application_icon_ignores_missing_resource(tmp_path):
    from PyQt6.QtWidgets import QApplication
    from main import set_application_icon

    app = QApplication.instance() or QApplication([])

    assert set_application_icon(app, tmp_path / "missing.ico") is False
