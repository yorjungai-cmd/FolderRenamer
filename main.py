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
