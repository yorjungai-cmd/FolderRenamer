from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
class ProgressBarWidget(QWidget):
    stop_requested = pyqtSignal()
    apply_requested = pyqtSignal()
    revert_requested = pyqtSignal()
    def __init__(self, parent=None): super().__init__(parent)
    def set_total(self, n): pass
    def set_progress(self, done, total): pass
    def set_eta(self, s): pass
    def set_approved_count(self, n): pass
    def set_summary(self, a, e, c): pass
