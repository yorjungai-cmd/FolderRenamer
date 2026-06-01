from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal

class ProgressBarWidget(QWidget):
    stop_requested   = pyqtSignal()
    apply_requested  = pyqtSignal()
    revert_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self._bar = QProgressBar()
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        top.addWidget(self._bar, stretch=1)
        self._count_lbl = QLabel("0 / 0")
        self._count_lbl.setStyleSheet("font-weight:500;color:#111827;")
        self._eta_lbl = QLabel("")
        self._eta_lbl.setStyleSheet("color:#9ca3af;")
        self._btn_stop = QPushButton("■ Stop")
        self._btn_stop.setObjectName("btn-danger")
        self._btn_stop.clicked.connect(self.stop_requested)
        top.addWidget(self._count_lbl)
        top.addWidget(self._eta_lbl)
        top.addWidget(self._btn_stop)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet("color:#9ca3af;font-size:11px;")
        bottom.addWidget(self._summary_lbl)
        bottom.addStretch()
        self._btn_revert = QPushButton("🕒 Revert Last Session")
        self._btn_revert.clicked.connect(self.revert_requested)
        self._btn_apply = QPushButton("✓ Apply Approved (0)")
        self._btn_apply.setObjectName("btn-success")
        self._btn_apply.clicked.connect(self.apply_requested)
        bottom.addWidget(self._btn_revert)
        bottom.addWidget(self._btn_apply)
        layout.addLayout(bottom)

    def set_total(self, total: int):
        self._bar.setMaximum(total)
        self._bar.setValue(0)
        self._count_lbl.setText(f"0 / {total}")

    def set_progress(self, done: int, total: int):
        self._bar.setMaximum(total)
        self._bar.setValue(done)
        self._count_lbl.setText(f"{done} / {total}")

    def set_eta(self, seconds: float):
        if seconds >= 60:
            self._eta_lbl.setText(f"~{int(seconds // 60)}m {int(seconds % 60)}s")
        else:
            self._eta_lbl.setText(f"~{int(seconds)}s")

    def set_approved_count(self, n: int):
        self._btn_apply.setText(f"✓ Apply Approved ({n})")

    def set_summary(self, approved: int, errors: int, conflicts: int):
        parts = [f"{approved} approved"]
        if errors:    parts.append(f"{errors} errors")
        if conflicts: parts.append(f"{conflicts} conflicts")
        self._summary_lbl.setText(" · ".join(parts))
