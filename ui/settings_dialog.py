from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QGroupBox,
    QRadioButton, QLineEdit, QPushButton, QLabel, QComboBox, QCheckBox,
    QGridLayout, QListWidget, QMessageBox, QHeaderView, QTableWidget,
    QTableWidgetItem
)
from config import AppConfig
from api.deepl_provider import DeepLProvider
from api.openrouter_provider import OpenRouterProvider
from core.sanitizer import sanitize as _sanitize

class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, preview_samples: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.config = config
        self._samples = preview_samples or ["SSIS-123 🔥田中美久.mp4", "title：special／file.mp4"]
        self.setWindowTitle("Settings")
        self.setFixedSize(580, 520)
        self._build_ui()
        self._load()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._api_tab(),   "API")
        self.tabs.addTab(self._san_tab(),   "Sanitization")
        self.tabs.addTab(self._filt_tab(),  "File Filters")
        v.addWidget(self.tabs)
        footer = QWidget()
        footer.setObjectName("dialog-footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.addStretch()
        b_cancel = QPushButton("Cancel")
        b_cancel.clicked.connect(self.reject)
        b_save = QPushButton("Save Settings")
        b_save.setObjectName("btn-primary")
        b_save.clicked.connect(self._save)
        fl.addWidget(b_cancel)
        fl.addWidget(b_save)
        v.addWidget(footer)

    def _api_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        pg = QGroupBox("Translation Provider")
        ph = QHBoxLayout(pg)
        self._r_deepl = QRadioButton("DeepL")
        self._r_or    = QRadioButton("OpenRouter")
        ph.addWidget(self._r_deepl)
        ph.addWidget(self._r_or)
        ph.addStretch()
        self._r_deepl.toggled.connect(self._toggle_provider)
        v.addWidget(pg)

        self._dg = QGroupBox("DeepL API")
        dv = QVBoxLayout(self._dg)
        dr = QHBoxLayout()
        self._dk = QLineEdit()
        self._dk.setPlaceholderText("API Key (ends :fx for free tier)")
        self._dk.setEchoMode(QLineEdit.EchoMode.Password)
        self._bt_dl = QPushButton("Test Connection")
        self._bt_dl.clicked.connect(self._test_deepl)
        dr.addWidget(self._dk)
        dr.addWidget(self._bt_dl)
        dv.addLayout(dr)
        self._ds = QLabel("")
        dv.addWidget(self._ds)
        v.addWidget(self._dg)

        self._og = QGroupBox("OpenRouter API")
        ov = QVBoxLayout(self._og)
        orow = QHBoxLayout()
        self._ok = QLineEdit()
        self._ok.setPlaceholderText("API Key (sk-or-v1-…)")
        self._ok.setEchoMode(QLineEdit.EchoMode.Password)
        self._bt_or = QPushButton("Test Connection")
        self._bt_or.clicked.connect(self._test_or)
        orow.addWidget(self._ok)
        orow.addWidget(self._bt_or)
        ov.addLayout(orow)
        mr = QHBoxLayout()
        mr.addWidget(QLabel("Model:"))
        self._mc = QComboBox()
        self._mc.setEditable(True)
        b_ref = QPushButton("↺")
        b_ref.setFixedWidth(32)
        b_ref.clicked.connect(self._refresh_models)
        mr.addWidget(self._mc, stretch=1)
        mr.addWidget(b_ref)
        ov.addLayout(mr)
        self._os = QLabel("")
        ov.addWidget(self._os)
        v.addWidget(self._og)
        v.addStretch()
        return w

    def _san_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)
        rules = [
            ("remove_illegal",      "Remove Windows-illegal chars",       r'\ / : * ? " < > |'),
            ("remove_emoji",        "Remove emojis",                      "Strips emoji Unicode ranges"),
            ("strip_dots_spaces",   "Strip leading/trailing dots/spaces", "Windows forbids trailing ."),
            ("normalize_fullwidth", "Normalize full-width → ASCII",       "ａｂｃ → abc"),
            ("remove_control_chars","Remove control characters",          "Strips invisible chars"),
            ("collapse_spaces",     "Collapse multiple spaces",           '"a  b" → "a b"'),
        ]
        self._sc: dict[str, QCheckBox] = {}
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (key, label, desc) in enumerate(rules):
            cb = QCheckBox(label)
            dl = QLabel(desc)
            dl.setStyleSheet("color:#9ca3af;font-size:10px;")
            cell = QWidget()
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(1)
            cl.addWidget(cb)
            cl.addWidget(dl)
            grid.addWidget(cell, i // 2, i % 2)
            self._sc[key] = cb
            cb.stateChanged.connect(self._refresh_preview)
        v.addLayout(grid)
        rr = QHBoxLayout()
        rr.addWidget(QLabel("Replace removed chars with:"))
        self._rn = QRadioButton("nothing")
        self._ru = QRadioButton("underscore _")
        self._rd = QRadioButton("dash -")
        for rb in (self._rn, self._ru, self._rd):
            rr.addWidget(rb)
            rb.toggled.connect(self._refresh_preview)
        rr.addStretch()
        v.addLayout(rr)
        pg = QGroupBox("Live Preview")
        pl = QVBoxLayout(pg)
        self._pt = QTableWidget(len(self._samples), 2)
        self._pt.setHorizontalHeaderLabels(["Before", "After"])
        self._pt.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._pt.setFixedHeight(80)
        self._pt.verticalHeader().setVisible(False)
        self._pt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        pl.addWidget(self._pt)
        v.addWidget(pg)
        v.addStretch()
        return w

    def _filt_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(8)
        self._subdirs = QCheckBox("Include files in subfolders recursively")
        v.addWidget(self._subdirs)
        v.addWidget(QLabel("File extensions to include:"))
        self._el = QListWidget()
        self._el.setFixedHeight(160)
        v.addWidget(self._el)
        er = QHBoxLayout()
        self._ei = QLineEdit()
        self._ei.setPlaceholderText(".mp4")
        ba = QPushButton("Add")
        ba.clicked.connect(self._add_ext)
        br = QPushButton("Remove")
        br.clicked.connect(self._rm_ext)
        er.addWidget(self._ei)
        er.addWidget(ba)
        er.addWidget(br)
        v.addLayout(er)
        v.addStretch()
        return w

    def _load(self):
        (self._r_deepl if self.config.provider == "deepl" else self._r_or).setChecked(True)
        self._dk.setText(self.config.deepl_key)
        self._ok.setText(self.config.openrouter_key)
        self._mc.addItem(self.config.openrouter_model)
        self._mc.setCurrentText(self.config.openrouter_model)
        san = self.config.sanitization
        for key, cb in self._sc.items():
            cb.setChecked(getattr(san, key, False))
        rep = san.replacement_char
        (self._ru if rep == "_" else self._rd if rep == "-" else self._rn).setChecked(True)
        self._subdirs.setChecked(self.config.scan_subdirectories)
        for ext in self.config.file_extensions:
            self._el.addItem(ext)
        self._toggle_provider()
        self._refresh_preview()

    def _save(self):
        self.config.provider = "deepl" if self._r_deepl.isChecked() else "openrouter"
        self.config.deepl_key = self._dk.text().strip()
        self.config.openrouter_key = self._ok.text().strip()
        self.config.openrouter_model = self._mc.currentText()
        san = self.config.sanitization
        for key, cb in self._sc.items():
            setattr(san, key, cb.isChecked())
        san.replacement_char = "_" if self._ru.isChecked() else "-" if self._rd.isChecked() else ""
        self.config.scan_subdirectories = self._subdirs.isChecked()
        self.config.file_extensions = [self._el.item(i).text() for i in range(self._el.count())]
        self.accept()

    def _toggle_provider(self):
        is_dl = self._r_deepl.isChecked()
        self._dg.setEnabled(is_dl)
        self._og.setEnabled(not is_dl)

    def _test_deepl(self):
        key = self._dk.text().strip()
        if not key:
            self._ds.setText("⚠ Enter API key first")
            return
        self._bt_dl.setEnabled(False)
        self._ds.setText("Testing…")
        r = DeepLProvider(key).test_connection()
        msg = f"{'✓' if r['ok'] else '✕'} {r['message']}"
        if r.get("quota"):
            msg += f"  ·  {r['quota']}"
        self._ds.setStyleSheet(f"color:{'#10b981' if r['ok'] else '#ef4444'};")
        self._ds.setText(msg)
        self._bt_dl.setEnabled(True)

    def _test_or(self):
        key = self._ok.text().strip()
        if not key:
            self._os.setText("⚠ Enter API key first")
            return
        self._bt_or.setEnabled(False)
        self._os.setText("Testing…")
        r = OpenRouterProvider(key, self._mc.currentText()).test_connection()
        self._os.setStyleSheet(f"color:{'#10b981' if r['ok'] else '#ef4444'};")
        self._os.setText(f"{'✓' if r['ok'] else '✕'} {r['message']}")
        self._bt_or.setEnabled(True)

    def _refresh_models(self):
        key = self._ok.text().strip()
        if not key:
            return
        try:
            models = OpenRouterProvider(key, "").list_models()
            cur = self._mc.currentText()
            self._mc.clear()
            self._mc.addItems(models)
            if cur in models:
                self._mc.setCurrentText(cur)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _add_ext(self):
        ext = self._ei.text().strip()
        if ext and not ext.startswith("."):
            ext = "." + ext
        if ext:
            existing = [self._el.item(i).text() for i in range(self._el.count())]
            if ext not in existing:
                self._el.addItem(ext)
            self._ei.clear()

    def _rm_ext(self):
        for item in self._el.selectedItems():
            self._el.takeItem(self._el.row(item))

    def _refresh_preview(self):
        from config import SanitizationConfig
        san = SanitizationConfig()
        for key, cb in self._sc.items():
            setattr(san, key, cb.isChecked())
        san.replacement_char = "_" if self._ru.isChecked() else "-" if self._rd.isChecked() else ""
        for i, sample in enumerate(self._samples):
            after = _sanitize(sample, san)
            self._pt.setItem(i, 0, QTableWidgetItem(sample))
            self._pt.setItem(i, 1, QTableWidgetItem(after))
