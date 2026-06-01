from PyQt6.QtWidgets import QWidget
class FileQueuePanel(QWidget):
    def __init__(self, config, parent=None): super().__init__(parent)
    def add_file(self, path): pass
    def set_status(self, path, status): pass
    def get_pending_files(self): return []
    def update_path(self, old, new): pass
