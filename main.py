import sys
from pathlib import Path

from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication

from config import AppConfig
from ui.main_window import MainWindow


def resource_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)


def set_application_icon(app: QApplication, icon_path: Path) -> bool:
    if not icon_path.exists():
        return False

    icon = QIcon(str(icon_path))
    if icon.isNull():
        return False

    app.setWindowIcon(icon)
    return True


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FolderFileRenamer")
    set_application_icon(app, resource_path("resources", "icon.ico"))
    fonts_dir = resource_path("resources", "fonts")
    if fonts_dir.is_dir():
        for font_path in fonts_dir.iterdir():
            if font_path.suffix.lower() in (".ttf", ".otf"):
                QFontDatabase.addApplicationFont(str(font_path))
    qss = resource_path("resources", "styles.qss")
    if qss.exists():
        with qss.open("r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    config = AppConfig.load()
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
