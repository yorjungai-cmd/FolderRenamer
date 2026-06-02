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


def test_status_counters_track_translate_and_error():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp1 = r"C:\demo\a.mp4"
    fp2 = r"C:\demo\b.mp4"
    fp3 = r"C:\demo\c.mp4"

    panel.add_row(fp1, "a.mp4")
    panel.add_row(fp2, "b.mp4")
    panel.add_row(fp3, "c.mp4")
    panel.set_translated(fp1, "aa.mp4")
    panel.set_translated(fp2, "bb.mp4")
    panel.set_error(fp3, "network error")

    assert panel.approved_count == 2
    assert panel.count_by_status("approved") == 2
    assert panel.count_by_status("error") == 1


def test_status_counters_track_conflict():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp1 = r"C:\demo\a.mp4"
    fp2 = r"C:\demo\b.mp4"

    panel.add_row(fp1, "a.mp4")
    panel.add_row(fp2, "b.mp4")
    panel.set_translated(fp1, "same.mp4")
    panel.set_translated(fp2, "same.mp4")

    assert panel.count_by_status("conflict") == 2
    assert panel.approved_count == 0


def test_status_counters_reset_on_clear():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp1 = r"C:\demo\a.mp4"
    fp2 = r"C:\demo\b.mp4"

    panel.add_row(fp1, "a.mp4")
    panel.add_row(fp2, "b.mp4")
    panel.set_translated(fp1, "aa.mp4")
    panel.set_error(fp2, "oops")

    assert panel.approved_count == 1
    assert panel.count_by_status("error") == 1

    panel.clear()

    assert panel.approved_count == 0
    assert panel.count_by_status("error") == 0
    assert panel.count_by_status("conflict") == 0


def test_end_bulk_sets_action_widgets():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QPushButton
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp1 = r"C:\demo\action1.mp4"
    fp2 = r"C:\demo\action2.mp4"

    panel.add_row(fp1, "action1.mp4")
    panel.add_row(fp2, "action2.mp4")
    panel.begin_bulk()
    panel.set_translated(fp1, "aa.mp4")
    panel.set_translated(fp2, "bb.mp4")

    # Mid-bulk: no action widgets at all
    def btn_count(fp):
        w = panel.table.cellWidget(panel._row_map[fp], panel.ACT_COL)
        return len(w.findChildren(QPushButton)) if w else 0

    assert panel.table.cellWidget(panel._row_map[fp1], panel.ACT_COL) is None
    assert panel.table.cellWidget(panel._row_map[fp2], panel.ACT_COL) is None

    panel.end_bulk()

    # After end_bulk: action widgets with approve + edit buttons
    assert btn_count(fp1) >= 2
    assert btn_count(fp2) >= 2


def test_issues_filter_shows_only_errors_and_conflicts():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig())
    fp_ok    = r"C:\demo\ok.mp4"
    fp_err   = r"C:\demo\err.mp4"
    fp_same1 = r"C:\demo\c1.mp4"
    fp_same2 = r"C:\demo\c2.mp4"

    panel.add_row(fp_ok, "ok.mp4");     panel.set_translated(fp_ok,    "ok.mp4")
    panel.add_row(fp_err, "err.mp4");   panel.set_error(fp_err,        "network error")
    panel.add_row(fp_same1, "c1.mp4");  panel.set_translated(fp_same1, "same.mp4")
    panel.add_row(fp_same2, "c2.mp4");  panel.set_translated(fp_same2, "same.mp4")

    panel.btn_show_issues.click()

    assert panel.table.isRowHidden(panel._row_map[fp_ok])    is True   # approved → hidden
    assert panel.table.isRowHidden(panel._row_map[fp_err])   is False  # error → visible
    assert panel.table.isRowHidden(panel._row_map[fp_same1]) is False  # conflict → visible
    assert panel.table.isRowHidden(panel._row_map[fp_same2]) is False  # conflict → visible


def test_trim_all_deduplicates_against_stable_file():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from config import AppConfig
    from ui.preview_panel import PreviewPanel

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel(AppConfig(max_filename_chars=5))
    fp_long = r"C:\demo\long.mp4"
    fp_short = r"C:\demo\short.mp4"

    panel.add_row(fp_long, "long.mp4")
    panel.set_translated(fp_long, "abcdefghij.mp4")   # will trim to "abcde.mp4"
    panel.add_row(fp_short, "short.mp4")
    panel.set_translated(fp_short, "abcde.mp4")        # already short — stable, not trimmed

    panel.btn_trim_all.click()

    long_name = panel.table.item(panel._row_map[fp_long], panel.TRANS_COL).text()
    short_name = panel.table.item(panel._row_map[fp_short], panel.TRANS_COL).text()
    assert short_name == "abcde.mp4"       # stable file unchanged
    assert long_name != "abcde.mp4"        # trimmed file must not collide
    assert long_name == "abcde_2.mp4"      # gets next suffix


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
