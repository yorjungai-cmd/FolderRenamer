import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_set_application_icon_applies_valid_icon(tmp_path):
    from PyQt6.QtWidgets import QApplication
    from main import set_application_icon

    source_icon = Path(__file__).resolve().parents[1] / "resources" / "icon.ico"
    test_icon = tmp_path / "icon.ico"
    with source_icon.open("rb") as source, test_icon.open("wb") as destination:
        destination.write(source.read())

    app = QApplication.instance() or QApplication([])
    previous_icon = app.windowIcon()

    try:
        assert set_application_icon(app, test_icon) is True
        assert not app.windowIcon().isNull()
    finally:
        app.setWindowIcon(previous_icon)


def test_set_application_icon_returns_false_for_missing_icon(tmp_path):
    from PyQt6.QtWidgets import QApplication
    from main import set_application_icon

    app = QApplication.instance() or QApplication([])

    assert set_application_icon(app, tmp_path / "missing.ico") is False


def test_main_sets_application_icon_before_window_creation(monkeypatch, tmp_path):
    import main

    events = []
    created = {}
    config = object()

    class FakeApplication:
        def __init__(self, args):
            created["app"] = self

        def setApplicationName(self, name):
            events.append(("application_name", name))

        def exec(self):
            events.append(("exec",))
            return 0

    class FakeConfig:
        @staticmethod
        def load():
            events.append(("config",))
            return config

    class FakeMainWindow:
        def __init__(self, loaded_config):
            events.append(("window", loaded_config))

        def show(self):
            events.append(("show",))

    def fake_set_application_icon(app, icon_path):
        events.append(("icon", app, icon_path))
        return True

    def fake_exit(code):
        events.append(("exit", code))

    monkeypatch.setattr(main, "QApplication", FakeApplication)
    monkeypatch.setattr(main, "AppConfig", FakeConfig)
    monkeypatch.setattr(main, "MainWindow", FakeMainWindow)
    monkeypatch.setattr(main, "set_application_icon", fake_set_application_icon)
    monkeypatch.setattr(
        main, "resource_path", lambda *parts: tmp_path.joinpath(*parts)
    )
    monkeypatch.setattr(main.sys, "exit", fake_exit)

    main.main()

    icon_event = (
        "icon",
        created["app"],
        tmp_path / "resources" / "icon.ico",
    )
    assert events.index(("application_name", "FolderFileRenamer")) < events.index(
        icon_event
    )
    assert events.index(icon_event) < events.index(("window", config))
    assert events[-2:] == [("exec",), ("exit", 0)]


def test_main_window_title_includes_app_version():
    from PyQt6.QtWidgets import QApplication
    from app_metadata import APP_VERSION
    from config import AppConfig
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(AppConfig(check_updates_on_startup=False))

    assert window.windowTitle() == f"Folder File Renamer v{APP_VERSION}"
