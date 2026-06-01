import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from config import AppConfig

class FileQueuePanel(QWidget):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._path_to_item: dict[str, QTreeWidgetItem] = {}
        self._folder_nodes: dict[str, QTreeWidgetItem] = {}
        self._known_paths:  set[str] = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        hdr = QWidget()
        hdr.setObjectName("panel-header")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 6, 10, 6)
        lbl = QLabel("FILE QUEUE")
        lbl.setObjectName("header")
        self._count_lbl = QLabel("0 files")
        self._count_lbl.setObjectName("header")
        hl.addWidget(lbl)
        hl.addStretch()
        hl.addWidget(self._count_lbl)
        layout.addWidget(hdr)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 72)
        self.tree.setIndentation(14)
        layout.addWidget(self.tree)

    def add_file(self, file_path: str):
        if file_path in self._known_paths:
            return
        self._known_paths.add(file_path)
        folder = os.path.dirname(file_path)
        if folder not in self._folder_nodes:
            node = QTreeWidgetItem(self.tree)
            node.setText(0, f"📁  {folder}")
            node.setExpanded(True)
            node.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._folder_nodes[folder] = node
        item = QTreeWidgetItem(self._folder_nodes[folder])
        item.setText(0, os.path.basename(file_path))
        item.setText(1, "pending")
        item.setForeground(1, QColor("#9ca3af"))
        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        self._path_to_item[file_path] = item
        self._count_lbl.setText(f"{len(self._path_to_item)} files")

    def set_status(self, file_path: str, status: str):
        item = self._path_to_item.get(file_path)
        if not item:
            return
        labels = {
            "pending":     ("pending",      "#9ca3af"),
            "translating": ("translating…", "#6366f1"),
            "done":        ("done",          "#10b981"),
            "no-op":       ("no-op",         "#d1d5db"),
            "error":       ("error",         "#ef4444"),
        }
        text, color = labels.get(status, (status, "#9ca3af"))
        item.setText(1, text)
        item.setForeground(1, QColor(color))

    def get_pending_files(self) -> list[str]:
        return [fp for fp, item in self._path_to_item.items()
                if item.text(1) in ("pending", "error")]

    def update_path(self, old_path: str, new_path: str):
        item = self._path_to_item.pop(old_path, None)
        if item:
            item.setText(0, os.path.basename(new_path))
            item.setData(0, Qt.ItemDataRole.UserRole, new_path)
            self._path_to_item[new_path] = item
            self._known_paths.discard(old_path)
            self._known_paths.add(new_path)

    def clear(self):
        self.tree.clear()
        self._path_to_item.clear()
        self._folder_nodes.clear()
        self._known_paths.clear()
        self._count_lbl.setText("0 files")
