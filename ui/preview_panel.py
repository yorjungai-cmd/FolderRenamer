import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from config import AppConfig

class PreviewPanel(QWidget):
    S_COL, ORIG_COL, TRANS_COL, ACT_COL = 0, 1, 2, 3

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._segments: dict = {}
        self._row_map:  dict = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        hdr = QWidget()
        hdr.setObjectName("panel-header")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 6, 12, 6)
        title = QLabel("TRANSLATION PREVIEW")
        title.setObjectName("header")
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(QLabel("Filter:"))
        self._filter = QComboBox()
        self._filter.addItems(["All", "Approved", "Errors", "Conflicts", "Pending"])
        self._filter.currentTextChanged.connect(self._apply_filter)
        hl.addWidget(self._filter)
        btn_aa = QPushButton("✓ All")
        btn_aa.setObjectName("btn-success")
        btn_ra = QPushButton("✕ All")
        btn_ra.setObjectName("btn-danger")
        btn_aa.clicked.connect(self._approve_all)
        btn_ra.clicked.connect(self._reject_all)
        hl.addWidget(btn_aa)
        hl.addWidget(btn_ra)
        layout.addWidget(hdr)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Original", "Translated", "Actions"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(self.S_COL,    QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(self.ORIG_COL, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.TRANS_COL,QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.ACT_COL,  QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.S_COL,   28)
        self.table.setColumnWidth(self.ACT_COL, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        layout.addWidget(self.table)

    def store_segments(self, fp: str, segments: list):
        self._segments[fp] = segments

    def get_segments(self, fp: str) -> list:
        return self._segments.get(fp, [])

    def add_row(self, fp: str, original_name: str):
        if fp in self._row_map:
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._row_map[fp] = row
        si = QTableWidgetItem("⟳")
        si.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        si.setFlags(Qt.ItemFlag.ItemIsEnabled)
        si.setData(Qt.ItemDataRole.UserRole, "pending")
        si.setForeground(QColor("#6366f1"))
        self.table.setItem(row, self.S_COL, si)
        oi = QTableWidgetItem(original_name)
        oi.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        oi.setForeground(QColor("#9ca3af"))
        oi.setData(Qt.ItemDataRole.UserRole, fp)
        self.table.setItem(row, self.ORIG_COL, oi)
        ti = QTableWidgetItem("Translating…")
        ti.setForeground(QColor("#6366f1"))
        self.table.setItem(row, self.TRANS_COL, ti)
        self._set_actions(row, fp, "pending")

    _WARN_CHARS = 200
    _MAX_CHARS  = 255

    def set_translated(self, fp: str, translated_name: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        ti = self.table.item(row, self.TRANS_COL)
        if ti:
            ti.setText(translated_name)
            ti.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            n = len(translated_name)
            if n >= self._MAX_CHARS:
                ti.setForeground(QColor("#ef4444"))
                ti.setToolTip(f"⚠ Filename is {n} chars — exceeds Windows 255-char limit; was auto-trimmed")
            elif n >= self._WARN_CHARS:
                ti.setForeground(QColor("#f59e0b"))
                ti.setToolTip(f"⚠ Filename is {n} chars — may cause issues on deeply nested paths (limit: 255)")
            else:
                ti.setForeground(QColor("#111827"))
                ti.setToolTip(f"{n} chars")
        si = self.table.item(row, self.S_COL)
        if si:
            si.setText("✓")
            si.setForeground(QColor("#10b981"))
            si.setData(Qt.ItemDataRole.UserRole, "approved")
        self._set_actions(row, fp, "done", show_trim=(n >= self._WARN_CHARS))
        self._flag_conflicts(row, fp, translated_name)

    def set_error(self, fp: str, error_msg: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        ti = self.table.item(row, self.TRANS_COL)
        if ti:
            ti.setText(f"Error: {error_msg}")
            ti.setForeground(QColor("#ef4444"))
        si = self.table.item(row, self.S_COL)
        if si:
            si.setText("✕")
            si.setForeground(QColor("#ef4444"))
            si.setData(Qt.ItemDataRole.UserRole, "error")
        self._set_actions(row, fp, "error")

    def get_approved_renames(self) -> list[tuple[str, str]]:
        result = []
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            oi = self.table.item(row, self.ORIG_COL)
            ti = self.table.item(row, self.TRANS_COL)
            if (si and si.data(Qt.ItemDataRole.UserRole) == "approved"
                    and oi and ti and not ti.text().startswith("Error:")):
                result.append((oi.data(Qt.ItemDataRole.UserRole), ti.text()))
        return result

    def count_by_status(self, status: str) -> int:
        return sum(1 for row in range(self.table.rowCount())
                   if (self.table.item(row, self.S_COL) or None) is not None
                   and self.table.item(row, self.S_COL).data(Qt.ItemDataRole.UserRole) == status)

    def clear(self):
        self.table.setRowCount(0)
        self._row_map.clear()
        self._segments.clear()

    def _set_actions(self, row: int, fp: str, state: str, show_trim: bool = False):
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(4, 2, 4, 2)
        hl.setSpacing(3)
        if state == "done":
            ba = QPushButton("✓")
            ba.setFixedWidth(28)
            ba.setObjectName("btn-success")
            ba.clicked.connect(lambda _, f=fp: self._approve_row(f))
            be = QPushButton("✎")
            be.setFixedWidth(28)
            be.clicked.connect(lambda _, r=row: self.table.editItem(self.table.item(r, self.TRANS_COL)))
            hl.addWidget(ba)
            hl.addWidget(be)
            if show_trim:
                limit = self.config.max_filename_chars if self.config.max_filename_chars > 0 else self._WARN_CHARS
                bt = QPushButton("✂")
                bt.setFixedWidth(28)
                bt.setToolTip(f"Trim filename stem to {limit} chars")
                bt.clicked.connect(lambda _, f=fp: self._trim_row(f))
                hl.addWidget(bt)
        elif state == "error":
            br = QPushButton("↺")
            br.setFixedWidth(28)
            br.setObjectName("btn-danger")
            hl.addWidget(br)
        self.table.setCellWidget(row, self.ACT_COL, container)

    def _trim_row(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        ti = self.table.item(row, self.TRANS_COL)
        if not ti:
            return
        current = ti.text()
        stem, ext = os.path.splitext(current)
        limit = self.config.max_filename_chars if self.config.max_filename_chars > 0 else self._WARN_CHARS
        if len(stem) <= limit:
            return
        new_name = stem[:limit].rstrip() + ext
        ti.setText(new_name)
        n = len(new_name)
        if n >= self._MAX_CHARS:
            ti.setForeground(QColor("#ef4444"))
            ti.setToolTip(f"⚠ Filename is {n} chars — exceeds Windows 255-char limit; was auto-trimmed")
        elif n >= self._WARN_CHARS:
            ti.setForeground(QColor("#f59e0b"))
            ti.setToolTip(f"⚠ Filename is {n} chars — may cause issues on deeply nested paths (limit: 255)")
        else:
            ti.setForeground(QColor("#111827"))
            ti.setToolTip(f"{n} chars")
        self._set_actions(row, fp, "done", show_trim=(n >= self._WARN_CHARS))
        self._flag_conflicts(row, fp, new_name)

    def _approve_row(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        si = self.table.item(row, self.S_COL)
        if si and si.data(Qt.ItemDataRole.UserRole) not in ("error",):
            si.setText("✓")
            si.setForeground(QColor("#10b981"))
            si.setData(Qt.ItemDataRole.UserRole, "approved")

    def _approve_all(self):
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            ti = self.table.item(row, self.TRANS_COL)
            if si and ti and not ti.text().startswith("Error:"):
                si.setText("✓")
                si.setForeground(QColor("#10b981"))
                si.setData(Qt.ItemDataRole.UserRole, "approved")

    def _reject_all(self):
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            if si:
                si.setText("✕")
                si.setForeground(QColor("#ef4444"))
                si.setData(Qt.ItemDataRole.UserRole, "rejected")

    def _flag_conflicts(self, row: int, fp: str, new_name: str):
        folder = os.path.dirname(fp)
        for other_fp, r in self._row_map.items():
            if r == row or os.path.dirname(other_fp) != folder:
                continue
            ti = self.table.item(r, self.TRANS_COL)
            if ti and ti.text() == new_name:
                for cr in (row, r):
                    ct = self.table.item(cr, self.TRANS_COL)
                    cs = self.table.item(cr, self.S_COL)
                    if ct:
                        ct.setBackground(QColor("#fef3c7"))
                    if cs:
                        cs.setText("⚠")
                        cs.setForeground(QColor("#f59e0b"))
                        cs.setData(Qt.ItemDataRole.UserRole, "conflict")

    def _apply_filter(self, text: str):
        status_map = {"Approved": "approved", "Errors": "error",
                      "Conflicts": "conflict", "Pending": "pending"}
        want = status_map.get(text, "")
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            status = si.data(Qt.ItemDataRole.UserRole) if si else ""
            self.table.setRowHidden(row, text != "All" and status != want)
