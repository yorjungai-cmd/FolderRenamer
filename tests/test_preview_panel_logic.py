def test_length_state_normal_under_warning_limit():
    from ui.preview_panel import filename_length_state

    assert filename_length_state("a" * 199) == "normal"


def test_length_state_near_limit_at_warning_limit():
    from ui.preview_panel import filename_length_state

    assert filename_length_state("a" * 201) == "near_limit"


def test_length_state_exceeds_limit_at_windows_limit():
    from ui.preview_panel import filename_length_state

    assert filename_length_state("a" * 256) == "exceeds_limit"


def test_trim_name_uses_configured_stem_limit():
    from ui.preview_panel import trim_filename_for_preview

    result = trim_filename_for_preview("a" * 240 + ".mp4", max_filename_chars=120)

    assert result == ("a" * 120) + ".mp4"


def test_trim_name_uses_warning_threshold_when_autotrim_off():
    from ui.preview_panel import trim_filename_for_preview

    result = trim_filename_for_preview("a" * 240 + ".mp4", max_filename_chars=0)

    assert result == ("a" * 196) + ".mp4"


def test_trim_all_trims_only_rows_that_need_it():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig(max_filename_chars=10))
    long_fp = r"C:\demo\long.mp4"
    short_fp = r"C:\demo\short.mp4"
    error_fp = r"C:\demo\error.mp4"

    panel.add_row(long_fp, "long.mp4")
    panel.set_translated(long_fp, "a" * 20 + ".mp4")
    panel.add_row(short_fp, "short.mp4")
    panel.set_translated(short_fp, "short.mp4")
    panel.add_row(error_fp, "error.mp4")
    panel.set_error(error_fp, "network problem")

    panel.btn_trim_all.click()

    assert panel.table.item(panel._row_map[long_fp], panel.TRANS_COL).text() == ("a" * 10) + ".mp4"
    assert panel.table.item(panel._row_map[short_fp], panel.TRANS_COL).text() == "short.mp4"
    assert panel.table.item(panel._row_map[error_fp], panel.TRANS_COL).text() == "Error: network problem"


def test_trim_row_rechecks_conflicts_after_name_changes():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig(max_filename_chars=10))
    first_fp = r"C:\demo\first.mp4"
    second_fp = r"C:\demo\second.mp4"

    panel.add_row(first_fp, "first.mp4")
    panel.set_translated(first_fp, "a" * 20 + ".mp4")
    panel.add_row(second_fp, "second.mp4")
    panel.set_translated(second_fp, "a" * 20 + ".mp4")

    assert panel.table.item(panel._row_map[first_fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "conflict"
    assert panel.table.item(panel._row_map[second_fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "conflict"

    panel._trim_row(first_fp)

    assert panel.table.item(panel._row_map[first_fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "approved"
    assert panel.table.item(panel._row_map[second_fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "approved"
