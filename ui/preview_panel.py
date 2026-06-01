from PyQt6.QtWidgets import QWidget
class PreviewPanel(QWidget):
    def __init__(self, config, parent=None): super().__init__(parent)
    def store_segments(self, fp, segs): pass
    def get_segments(self, fp): return []
    def add_row(self, fp, name): pass
    def set_translated(self, fp, name): pass
    def set_error(self, fp, msg): pass
    def get_approved_renames(self): return []
    def count_by_status(self, s): return 0
