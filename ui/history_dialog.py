import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.session_store import list_sessions, revert_session

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename History")
        self.resize(780, 520)
        self._sessions = list_sessions()
        self._current_path: str | None = None
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hdr = QWidget()
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 12, 16, 10)
        title = QLabel("🕒  Rename History")
        title.setStyleSheet("font-size:15px;font-weight:600;color:#111827;")
        hl.addWidget(title)
        hl.addStretch()
        layout.addWidget(hdr)

        sp = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        lhdr = QLabel("Past Sessions")
        lhdr.setObjectName("header")
        lhdr.setContentsMargins(12, 6, 12, 6)
        lv.addWidget(lhdr)
        self._sl = QListWidget()
        self._sl.currentRowChanged.connect(self._on_row)
        lv.addWidget(self._sl)
        sp.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        self._dh = QLabel("")
        self._dh.setObjectName("header")
        self._dh.setContentsMargins(12, 6, 12, 6)
        rv.addWidget(self._dh)
        self._wl = QLabel("")
        self._wl.setStyleSheet(
            "background:#fffbeb;color:#92400e;padding:6px 12px;border-bottom:1px solid #fcd34d;")
        self._wl.setVisible(False)
        rv.addWidget(self._wl)
        self._dt = QTableWidget()
        self._dt.setColumnCount(3)
        self._dt.setHorizontalHeaderLabels(["", "Current Name → restore to", "Original Name"])
        h = self._dt.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._dt.setColumnWidth(0, 24)
        self._dt.verticalHeader().setVisible(False)
        self._dt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        rv.addWidget(self._dt)
        sp.addWidget(right)
        sp.setSizes([240, 540])
        layout.addWidget(sp, stretch=1)

        footer = QWidget()
        footer.setObjectName("dialog-footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        hint = QLabel("Reverting restores original filenames.")
        hint.setStyleSheet("color:#9ca3af;font-size:10px;")
        fl.addWidget(hint)
        fl.addStretch()
        b_cancel = QPushButton("Cancel")
        b_cancel.clicked.connect(self.reject)
        self._b_rev = QPushButton("↺ Revert")
        self._b_rev.setObjectName("btn-danger")
        self._b_rev.setEnabled(False)
        self._b_rev.clicked.connect(self._do_revert)
        fl.addWidget(b_cancel)
        fl.addWidget(self._b_rev)
        layout.addWidget(footer)

    def _populate(self):
        for s in self._sessions:
            stats   = s.get("stats", {})
            renamed = stats.get("renamed", len(s.get("files", [])))
            ts      = s.get("timestamp", "")[:16].replace("T", ", ")
            item = QListWidgetItem(f"{ts}\n{renamed} files renamed")
            item.setData(Qt.ItemDataRole.UserRole, s["path"])
            self._sl.addItem(item)

    def _on_row(self, row: int):
        if row < 0 or row >= len(self._sessions):
            return
        s = self._sessions[row]
        self._current_path = s["path"]
        files   = s.get("files", [])
        renamed = [f for f in files if f.get("status") == "renamed"]
        missing = [f for f in renamed if not os.path.exists(f.get("new_path", ""))]
        if missing:
            self._wl.setText(
                f"⚠  {len(missing)} files were moved/deleted — skipped during revert.")
            self._wl.setVisible(True)
        else:
            self._wl.setVisible(False)
        ts   = s.get("timestamp", "")[:16].replace("T", " ")
        prov = s.get("provider", "").upper()
        self._dh.setText(f"{ts}  ·  {len(renamed)} files  ·  {prov}")
        self._dt.setRowCount(0)
        for entry in renamed[:300]:
            r = self._dt.rowCount()
            self._dt.insertRow(r)
            new_p = entry.get("new_path", "")
            old_p = entry.get("old_path", "")
            exists = os.path.exists(new_p)
            icon = QTableWidgetItem("✓" if exists else "⚠")
            icon.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setForeground(QColor("#10b981" if exists else "#f59e0b"))
            cur  = QTableWidgetItem(os.path.basename(new_p))
            cur.setForeground(QColor("#6b7280" if exists else "#d1d5db"))
            orig = QTableWidgetItem(os.path.basename(old_p))
            orig.setForeground(QColor("#111827" if exists else "#9ca3af"))
            self._dt.setItem(r, 0, icon)
            self._dt.setItem(r, 1, cur)
            self._dt.setItem(r, 2, orig)
        if len(renamed) > 300:
            r = self._dt.rowCount()
            self._dt.insertRow(r)
            more = QTableWidgetItem(f"… {len(renamed) - 300} more files")
            more.setForeground(QColor("#9ca3af"))
            self._dt.setItem(r, 1, more)
        revertible = len(renamed) - len(missing)
        self._b_rev.setText(f"↺ Revert {revertible} Files")
        self._b_rev.setEnabled(revertible > 0)

    def _do_revert(self):
        if not self._current_path:
            return
        reply = QMessageBox.question(
            self, "Confirm Revert",
            "Rename files back to their original Japanese names?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = revert_session(self._current_path)
        QMessageBox.information(
            self, "Revert Complete",
            f"Reverted: {result['reverted']}\n"
            f"Skipped (not found): {result['skipped']}\n"
            f"Failed: {result['failed']}",
        )
        self.accept()
