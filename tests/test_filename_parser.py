from core.filename_parser import (
    parse_filename, reconstruct, collect_japanese, has_japanese, Segment
)

def test_has_japanese_true():
    assert has_japanese("田中美久") is True

def test_has_japanese_false():
    assert has_japanese("SSIS-123 Hello") is False

def test_studio_code_preserved():
    segs = parse_filename("SSIS-123 田中美久")
    kinds = [s.kind for s in segs if s.text.strip()]
    assert "preserved" in kinds
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "SSIS-123" in preserved

def test_resolution_tag_preserved():
    segs = parse_filename("ABP-001 タイトル 4K")
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "4K" in preserved
    assert "ABP-001" in preserved

def test_bracketed_code_preserved():
    segs = parse_filename("[Uncensored] タイトル")
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "[Uncensored]" in preserved

def test_japanese_extracted():
    segs = parse_filename("SSIS-123 田中美久 タイトル 4K")
    japanese = [s.text for s in segs if s.kind == "japanese"]
    assert any("田中" in t for t in japanese)

def test_reconstruct_replaces_japanese():
    segs = parse_filename("SSIS-123 田中美久 4K")
    jp = collect_japanese(segs)
    translations = {idx: "Tanaka Miku" for idx, _ in jp}
    result = reconstruct(segs, translations)
    assert "SSIS-123" in result
    assert "Tanaka Miku" in result
    assert "4K" in result
    assert "田中美久" not in result

def test_collect_japanese_returns_indices():
    segs = parse_filename("SSIS-123 田中 タイトル")
    jp = collect_japanese(segs)
    assert len(jp) >= 1
    for idx, text in jp:
        assert segs[idx].kind == "japanese"

def test_latin_only_filename():
    segs = parse_filename("hello world 2023")
    jp = collect_japanese(segs)
    assert jp == []

def test_year_in_parens_preserved():
    segs = parse_filename("タイトル (2023)")
    preserved = [s.text for s in segs if s.kind == "preserved"]
    assert "(2023)" in preserved
