import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from config import AppConfig


WARN_CHARS = 200
MAX_CHARS = 255


def filename_length_state(filename: str) -> str:
    n = len(filename)
    if n > MAX_CHARS:
        return "exceeds_limit"
    if n > WARN_CHARS:
        return "near_limit"
    return "normal"


def trim_filename_for_preview(filename: str, max_filename_chars: int) -> str:
    stem, ext = os.path.splitext(filename)
    if max_filename_chars > 0:
        limit = max_filename_chars
    else:
        limit = max(WARN_CHARS - len(ext), 0)
    if len(stem) <= limit:
        return filename
    return stem[:limit].rstrip() + ext


class PreviewPanel(QWidget):
    S_COL, ORIG_COL, TRANS_COL, ACT_COL = 0, 1, 2, 3
    retry_requested = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._segments: dict = {}
        self._row_map:  dict = {}
        self._bulk: bool = False
        self._bulk_dirty_folders: set = set()
        self._cnt_approved: int = 0
        self._cnt_error: int = 0
        self._cnt_conflict: int = 0
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
        self._filter.addItems([
            "All", "Approved", "Errors", "Conflicts", "Pending",
            "Char Near Limit", "Char Exceeds Limit"
        ])
        self._filter.currentTextChanged.connect(self._on_filter_changed)
        hl.addWidget(self._filter)
        btn_aa = QPushButton("✓ All")
        btn_aa.setObjectName("btn-success")
        btn_ra = QPushButton("✕ All")
        btn_ra.setObjectName("btn-danger")
        self.btn_trim_all = QPushButton("✂ Trim All")
        self.btn_trim_all.setObjectName("btn-warning")
        self.btn_trim_all.setToolTip("Trim all translated filenames that are near or over the length limit")
        btn_aa.clicked.connect(self._approve_all)
        btn_ra.clicked.connect(self._reject_all)
        self.btn_trim_all.clicked.connect(self._trim_all)
        hl.addWidget(btn_aa)
        hl.addWidget(self.btn_trim_all)
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
        self.table.setColumnWidth(self.ACT_COL, 112)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        layout.addWidget(self.table)
        self.table.itemChanged.connect(self._on_item_changed)

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
        self.table.blockSignals(True)
        try:
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
        finally:
            self.table.blockSignals(False)

    _WARN_CHARS = WARN_CHARS
    _MAX_CHARS  = MAX_CHARS

    def set_translated(self, fp: str, translated_name: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        self.table.blockSignals(True)
        try:
            ti = self.table.item(row, self.TRANS_COL)
            if ti:
                ti.setText(translated_name)
                ti.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                self._apply_length_style(ti)
            si = self.table.item(row, self.S_COL)
            if si:
                old = si.data(Qt.ItemDataRole.UserRole)
                si.setText("✓")
                si.setForeground(QColor("#10b981"))
                si.setData(Qt.ItemDataRole.UserRole, "approved")
                self._record_status_change(old, "approved")
            folder = os.path.dirname(fp)
            if self._bulk:
                self._bulk_dirty_folders.add(folder)
            else:
                self._recheck_all_conflicts_in_folder(folder)
        finally:
            self.table.blockSignals(False)
        self._refresh_row_after_name_change(row, fp)

    def set_error(self, fp: str, error_msg: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        self.table.blockSignals(True)
        try:
            ti = self.table.item(row, self.TRANS_COL)
            if ti:
                ti.setText(f"Error: {error_msg}")
                ti.setForeground(QColor("#ef4444"))
            si = self.table.item(row, self.S_COL)
            if si:
                old = si.data(Qt.ItemDataRole.UserRole)
                si.setText("✕")
                si.setForeground(QColor("#ef4444"))
                si.setData(Qt.ItemDataRole.UserRole, "error")
                self._record_status_change(old, "error")
        finally:
            self.table.blockSignals(False)
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
        if status == "approved":  return self._cnt_approved
        if status == "error":     return self._cnt_error
        if status == "conflict":  return self._cnt_conflict
        return sum(1 for row in range(self.table.rowCount())
                   if (self.table.item(row, self.S_COL) or None) is not None
                   and self.table.item(row, self.S_COL).data(Qt.ItemDataRole.UserRole) == status)

    @property
    def approved_count(self) -> int:
        return self._cnt_approved

    def _record_status_change(self, old: str, new: str) -> None:
        for state, attr in (("approved", "_cnt_approved"),
                            ("error",    "_cnt_error"),
                            ("conflict", "_cnt_conflict")):
            if old == state:
                setattr(self, attr, max(0, getattr(self, attr) - 1))
            if new == state:
                setattr(self, attr, getattr(self, attr) + 1)

    def begin_bulk(self) -> None:
        self._bulk = True
        self._bulk_dirty_folders.clear()

    def end_bulk(self) -> None:
        self._bulk = False
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            for folder in self._bulk_dirty_folders:
                self._recheck_all_conflicts_in_folder(folder)
        finally:
            self.table.blockSignals(False)
        self._bulk_dirty_folders.clear()
        for fp, row in self._row_map.items():
            si = self.table.item(row, self.S_COL)
            if not si:
                continue
            state = si.data(Qt.ItemDataRole.UserRole)
            if state in ("pending", "error"):
                continue
            ti = self.table.item(row, self.TRANS_COL)
            show_trim = bool(ti and self._needs_trim(ti.text()))
            self._set_actions(row, fp, "done", show_trim=show_trim)
        self._apply_filter(self._filter.currentText())
        self.table.setUpdatesEnabled(True)

    def clear(self):
        self.table.setRowCount(0)
        self._row_map.clear()
        self._segments.clear()
        self._bulk = False
        self._bulk_dirty_folders.clear()
        self._cnt_approved = 0
        self._cnt_error = 0
        self._cnt_conflict = 0

    def mark_applied(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        self.table.blockSignals(True)
        try:
            for col in (self.S_COL, self.ORIG_COL, self.TRANS_COL):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("#d1fae5"))
                    item.setForeground(QColor("#065f46"))
            si = self.table.item(row, self.S_COL)
            if si:
                old = si.data(Qt.ItemDataRole.UserRole)
                si.setText("✓")
                si.setData(Qt.ItemDataRole.UserRole, "applied")
                self._record_status_change(old, "applied")
        finally:
            self.table.blockSignals(False)

    def mark_failed(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        self.table.blockSignals(True)
        try:
            for col in (self.S_COL, self.ORIG_COL, self.TRANS_COL):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("#fee2e2"))
                    item.setForeground(QColor("#991b1b"))
            si = self.table.item(row, self.S_COL)
            if si:
                si.setText("✕")
        finally:
            self.table.blockSignals(False)

    def set_pending(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        self.table.blockSignals(True)
        try:
            ti = self.table.item(row, self.TRANS_COL)
            if ti:
                ti.setText("Translating…")
                ti.setForeground(QColor("#6366f1"))
                ti.setFlags(Qt.ItemFlag.ItemIsEnabled)
                ti.setBackground(QColor("transparent"))
            si = self.table.item(row, self.S_COL)
            if si:
                old = si.data(Qt.ItemDataRole.UserRole)
                si.setText("⟳")
                si.setForeground(QColor("#6366f1"))
                si.setData(Qt.ItemDataRole.UserRole, "pending")
                si.setBackground(QColor("transparent"))
                self._record_status_change(old, "pending")
        finally:
            self.table.blockSignals(False)
        self._set_actions(row, fp, "pending")

    def _set_actions(self, row: int, fp: str, state: str, show_trim: bool = False):
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(2, 2, 2, 2)
        hl.setSpacing(4)
        if state == "done":
            ba = self._make_action_button("✓", "preview-action-success", "Approve this rename")
            ba.clicked.connect(lambda _, f=fp: self._approve_row(f))
            be = self._make_action_button("✎", "preview-action-neutral", "Edit translated filename")
            be.clicked.connect(lambda _, r=row: self.table.editItem(self.table.item(r, self.TRANS_COL)))
            hl.addWidget(ba)
            hl.addWidget(be)
            if show_trim:
                limit = self.config.max_filename_chars if self.config.max_filename_chars > 0 else self._WARN_CHARS
                bt = self._make_action_button("✂", "preview-action-warning", f"Trim filename stem to {limit} chars")
                bt.clicked.connect(lambda _, f=fp: self._trim_row(f))
                hl.addWidget(bt)
        elif state == "error":
            br = self._make_action_button("↺", "preview-action-danger", "Retry translation")
            br.clicked.connect(lambda _, f=fp: self.retry_requested.emit(f))
            hl.addWidget(br)
        self.table.setCellWidget(row, self.ACT_COL, container)

    def _make_action_button(self, text: str, object_name: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setFixedSize(QSize(28, 24))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _trim_row(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        ti = self.table.item(row, self.TRANS_COL)
        if not ti:
            return
        current = ti.text()
        new_name = trim_filename_for_preview(current, self.config.max_filename_chars)
        if new_name == current:
            return
        self.table.blockSignals(True)
        try:
            ti.setText(new_name)
            self._apply_length_style(ti)
            self._recheck_all_conflicts_in_folder(os.path.dirname(fp))
        finally:
            self.table.blockSignals(False)
        self._refresh_row_after_name_change(row, fp)

    def _trim_all(self):
        _SKIP = {"error", "rejected", "applied", "pending"}
        # 1. Collect new names for all trimmable rows
        new_names: dict[str, str] = {}
        for fp, row in list(self._row_map.items()):
            si = self.table.item(row, self.S_COL)
            ti = self.table.item(row, self.TRANS_COL)
            if not si or not ti:
                continue
            if si.data(Qt.ItemDataRole.UserRole) in _SKIP:
                continue
            trimmed = trim_filename_for_preview(ti.text(), self.config.max_filename_chars)
            if trimmed != ti.text():
                new_names[fp] = trimmed
        if not new_names:
            return
        # 2. Deduplicate: files that trim to the same name in the same folder get _2, _3 …
        self._deduplicate_trim_names(new_names)
        # 3. Apply all text changes in one blocked pass
        self.table.blockSignals(True)
        try:
            for fp, new_name in new_names.items():
                row = self._row_map[fp]
                ti = self.table.item(row, self.TRANS_COL)
                if ti:
                    ti.setText(new_name)
                    self._apply_length_style(ti)
        finally:
            self.table.blockSignals(False)
        # 4. Recheck conflicts once per distinct folder (not once per file)
        self.table.blockSignals(True)
        try:
            for folder in {os.path.dirname(fp) for fp in new_names}:
                self._recheck_all_conflicts_in_folder(folder)
        finally:
            self.table.blockSignals(False)
        # 5. Refresh action widgets
        for fp in new_names:
            row = self._row_map[fp]
            self._refresh_row_after_name_change(row, fp)

    def _deduplicate_trim_names(self, new_names: dict) -> None:
        from collections import defaultdict
        trimming = set(new_names.keys())

        # Per folder: names already in use from rows NOT being trimmed (stable)
        in_use_per_folder: dict = defaultdict(set)
        for fp, row in self._row_map.items():
            if fp in trimming:
                continue
            ti = self.table.item(row, self.TRANS_COL)
            if ti:
                in_use_per_folder[os.path.dirname(fp)].add(ti.text())

        # Process each folder: assign non-conflicting names in order
        by_folder: dict = defaultdict(list)
        for fp in new_names:
            by_folder[os.path.dirname(fp)].append(fp)

        for folder, fps in by_folder.items():
            in_use = in_use_per_folder[folder].copy()
            for fp in fps:
                desired = new_names[fp]
                if desired not in in_use:
                    in_use.add(desired)
                    continue
                stem, ext = os.path.splitext(desired)
                counter = 2
                candidate = f"{stem}_{counter}{ext}"
                while candidate in in_use:
                    counter += 1
                    candidate = f"{stem}_{counter}{ext}"
                new_names[fp] = candidate
                in_use.add(candidate)

    def _on_item_changed(self, item):
        if item.column() != self.TRANS_COL:
            return
        oi = self.table.item(item.row(), self.ORIG_COL)
        if not oi:
            return
        fp = oi.data(Qt.ItemDataRole.UserRole)
        if not fp:
            return
        new_name = item.text()
        folder = os.path.dirname(fp)
        row = item.row()
        self.table.blockSignals(True)
        try:
            self._apply_length_style(item)
            self._recheck_all_conflicts_in_folder(folder)
        finally:
            self.table.blockSignals(False)
        self._refresh_row_after_name_change(row, fp)

    def _apply_length_style(self, item: QTableWidgetItem):
        n = len(item.text())
        state = filename_length_state(item.text())
        item.setData(Qt.ItemDataRole.UserRole + 1, state)
        if state == "exceeds_limit":
            item.setForeground(QColor("#ef4444"))
            item.setToolTip(f"⚠ Filename is {n} chars — exceeds Windows 255-char limit; trim before applying")
        elif state == "near_limit":
            item.setForeground(QColor("#f59e0b"))
            item.setToolTip(f"⚠ Filename is {n} chars — may cause issues on deeply nested paths (limit: 255)")
        else:
            item.setForeground(QColor("#111827"))
            item.setToolTip(f"{n} chars")

    def _refresh_row_after_name_change(self, row: int, fp: str):
        if self._bulk:
            return
        ti = self.table.item(row, self.TRANS_COL)
        show_trim = bool(ti and self._needs_trim(ti.text()))
        self._set_actions(row, fp, "done", show_trim=show_trim)
        self._apply_filter(self._filter.currentText())

    def _needs_trim(self, filename: str) -> bool:
        return trim_filename_for_preview(filename, self.config.max_filename_chars) != filename

    def _recheck_all_conflicts_in_folder(self, folder: str):
        _SKIP = {"error", "pending", "applied", "rejected"}
        folder_rows = [(fp, r) for fp, r in self._row_map.items()
                       if os.path.dirname(fp) == folder]
        name_count: dict = {}
        for fp, r in folder_rows:
            si = self.table.item(r, self.S_COL)
            ti = self.table.item(r, self.TRANS_COL)
            if si and ti and si.data(Qt.ItemDataRole.UserRole) not in _SKIP:
                name = ti.text()
                name_count[name] = name_count.get(name, 0) + 1
        for fp, r in folder_rows:
            si = self.table.item(r, self.S_COL)
            ti = self.table.item(r, self.TRANS_COL)
            if not si or not ti:
                continue
            state = si.data(Qt.ItemDataRole.UserRole)
            if state in _SKIP:
                continue
            is_conflict = name_count.get(ti.text(), 0) > 1
            if is_conflict and state != "conflict":
                ti.setBackground(QColor("#fef3c7"))
                si.setText("⚠")
                si.setForeground(QColor("#f59e0b"))
                si.setData(Qt.ItemDataRole.UserRole, "conflict")
                self._record_status_change(state, "conflict")
            elif not is_conflict and state == "conflict":
                si.setText("✓")
                si.setForeground(QColor("#10b981"))
                si.setData(Qt.ItemDataRole.UserRole, "approved")
                ti.setBackground(QColor("transparent"))
                self._record_status_change("conflict", "approved")

    def _approve_row(self, fp: str):
        row = self._row_map.get(fp)
        if row is None:
            return
        si = self.table.item(row, self.S_COL)
        if si and si.data(Qt.ItemDataRole.UserRole) not in ("error",):
            old = si.data(Qt.ItemDataRole.UserRole)
            si.setText("✓")
            si.setForeground(QColor("#10b981"))
            si.setData(Qt.ItemDataRole.UserRole, "approved")
            self._record_status_change(old, "approved")

    def _approve_all(self):
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            if si and si.data(Qt.ItemDataRole.UserRole) not in ("error", "applied"):
                old = si.data(Qt.ItemDataRole.UserRole)
                si.setText("✓")
                si.setForeground(QColor("#10b981"))
                si.setData(Qt.ItemDataRole.UserRole, "approved")
                self._record_status_change(old, "approved")

    def _reject_all(self):
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            if si:
                old = si.data(Qt.ItemDataRole.UserRole)
                si.setText("✕")
                si.setForeground(QColor("#ef4444"))
                si.setData(Qt.ItemDataRole.UserRole, "rejected")
                self._record_status_change(old, "rejected")

    def _on_filter_changed(self, text: str):
        self.table.setUpdatesEnabled(False)
        try:
            self._apply_filter(text)
        finally:
            self.table.setUpdatesEnabled(True)

    def _apply_filter(self, text: str):
        status_map = {"Approved": "approved", "Errors": "error",
                      "Conflicts": "conflict", "Pending": "pending"}
        want = status_map.get(text, "")
        for row in range(self.table.rowCount()):
            si = self.table.item(row, self.S_COL)
            ti = self.table.item(row, self.TRANS_COL)
            status = si.data(Qt.ItemDataRole.UserRole) if si else ""
            length_state = filename_length_state(ti.text()) if ti else ""
            if text == "Char Near Limit":
                hide = length_state != "near_limit"
            elif text == "Char Exceeds Limit":
                hide = length_state != "exceeds_limit"
            else:
                hide = text != "All" and status != want
            self.table.setRowHidden(row, hide)
