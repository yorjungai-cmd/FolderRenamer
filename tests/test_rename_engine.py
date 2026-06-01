import os
from core.rename_engine import (
    check_conflicts, check_missing_sources, apply_renames, safe_filename_length
)

def test_no_conflicts():
    renames = [("a.mp4", "b.mp4"), ("c.mp4", "d.mp4")]
    assert check_conflicts(renames) == []

def test_detects_conflict():
    renames = [("a.mp4", "same.mp4"), ("b.mp4", "same.mp4")]
    assert "same.mp4" in check_conflicts(renames)

def test_missing_source(tmp_path):
    missing = str(tmp_path / "gone.mp4")
    existing = str(tmp_path / "here.mp4")
    (tmp_path / "here.mp4").write_text("")
    result = check_missing_sources([(missing, "x"), (existing, "y")])
    assert missing in result
    assert existing not in result

def test_apply_renames_success(tmp_path):
    src = tmp_path / "old.mp4"
    src.write_text("data")
    dst = str(tmp_path / "new.mp4")
    results = apply_renames([(str(src), dst)])
    assert results[0]["status"] == "renamed"
    assert os.path.exists(dst)
    assert not src.exists()

def test_apply_renames_failure(tmp_path):
    results = apply_renames([(str(tmp_path / "nope.mp4"), str(tmp_path / "x.mp4"))])
    assert results[0]["status"] == "failed"
    assert results[0]["error"] is not None

def test_safe_filename_length_short():
    assert safe_filename_length("short", ".mp4") == "short"

def test_safe_filename_length_truncates():
    long_stem = "a" * 300
    result = safe_filename_length(long_stem, ".mp4")
    assert len((result + ".mp4").encode("utf-8")) <= 255
