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


def test_trim_all_skips_rejected_rows():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig(max_filename_chars=10))
    fp = r"C:\demo\rejected.mp4"

    panel.add_row(fp, "rejected.mp4")
    panel.set_translated(fp, "a" * 20 + ".mp4")
    panel._reject_all()

    assert panel.table.item(panel._row_map[fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "rejected"
    original_text = panel.table.item(panel._row_map[fp], panel.TRANS_COL).text()

    panel.btn_trim_all.click()

    assert panel.table.item(panel._row_map[fp], panel.TRANS_COL).text() == original_text
    assert panel.table.item(panel._row_map[fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "rejected"


def test_trim_all_skips_applied_rows():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig(max_filename_chars=10))
    fp = r"C:\demo\applied.mp4"

    panel.add_row(fp, "applied.mp4")
    panel.set_translated(fp, "a" * 20 + ".mp4")
    panel.mark_applied(fp)

    assert panel.table.item(panel._row_map[fp], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "applied"
    original_text = panel.table.item(panel._row_map[fp], panel.TRANS_COL).text()

    panel.btn_trim_all.click()

    assert panel.table.item(panel._row_map[fp], panel.TRANS_COL).text() == original_text


def test_bulk_mode_defers_filter():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp = r"C:\demo\file.mp4"
    panel.add_row(fp, "file.mp4")

    # Set filter to "Approved" so once the row is translated it would be shown,
    # but any pending row would be hidden if filter were reapplied mid-bulk.
    panel._filter.setCurrentText("Pending")

    panel.begin_bulk()
    panel.set_translated(fp, "translated.mp4")

    # Mid-bulk: filter NOT reapplied — row should still match the old filter state
    # (i.e., setRowHidden was not called with the new status). The easiest observable
    # outcome: the row is visible (was matching "Pending" before bulk started, and no
    # filter pass has hidden it as "Approved" yet).
    assert not panel.table.isRowHidden(panel._row_map[fp])

    panel.end_bulk()

    # After end_bulk: filter reapplied once — row is "approved", filter is "Pending" → hidden
    assert panel.table.isRowHidden(panel._row_map[fp])


def test_bulk_mode_defers_conflict_recheck():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp1 = r"C:\demo\file1.mp4"
    fp2 = r"C:\demo\file2.mp4"
    panel.add_row(fp1, "file1.mp4")
    panel.add_row(fp2, "file2.mp4")

    panel.begin_bulk()
    panel.set_translated(fp1, "same.mp4")
    panel.set_translated(fp2, "same.mp4")

    # Mid-bulk: conflict detection was skipped, both rows should be "approved"
    assert panel.table.item(panel._row_map[fp1], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "approved"
    assert panel.table.item(panel._row_map[fp2], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "approved"

    panel.end_bulk()

    # After end_bulk: conflict recheck runs, both rows flagged
    assert panel.table.item(panel._row_map[fp1], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "conflict"
    assert panel.table.item(panel._row_map[fp2], panel.S_COL).data(Qt.ItemDataRole.UserRole) == "conflict"


def test_trim_all_deduplicates_same_trimmed_name():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig(max_filename_chars=5))
    fp1 = r"C:\demo\file1.mp4"
    fp2 = r"C:\demo\file2.mp4"
    fp3 = r"C:\demo\file3.mp4"

    panel.add_row(fp1, "file1.mp4")
    panel.set_translated(fp1, "abcdefghij.mp4")
    panel.add_row(fp2, "file2.mp4")
    panel.set_translated(fp2, "abcdefghij.mp4")
    panel.add_row(fp3, "file3.mp4")
    panel.set_translated(fp3, "abcdefghij.mp4")

    panel.btn_trim_all.click()

    names = [
        panel.table.item(panel._row_map[fp1], panel.TRANS_COL).text(),
        panel.table.item(panel._row_map[fp2], panel.TRANS_COL).text(),
        panel.table.item(panel._row_map[fp3], panel.TRANS_COL).text(),
    ]
    assert names[0] == "abcde.mp4"
    assert names[1] == "abcde_2.mp4"
    assert names[2] == "abcde_3.mp4"
    assert len(set(names)) == 3
