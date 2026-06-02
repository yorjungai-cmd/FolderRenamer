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
