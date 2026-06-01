from config import SanitizationConfig
from core.sanitizer import sanitize

def _cfg(**kwargs) -> SanitizationConfig:
    cfg = SanitizationConfig()
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg

def test_remove_illegal_chars():
    cfg = _cfg(remove_illegal=True, replacement_char="")
    assert sanitize('file:name*here', cfg) == 'filenamehere'

def test_replace_illegal_with_underscore():
    cfg = _cfg(remove_illegal=True, replacement_char="_")
    assert sanitize('file:name', cfg) == 'file_name'

def test_remove_emoji():
    cfg = _cfg(remove_emoji=True, replacement_char="")
    result = sanitize('title 🔥 hot', cfg)
    assert '🔥' not in result
    assert 'title' in result

def test_strip_trailing_dot():
    cfg = _cfg(strip_dots_spaces=True)
    assert sanitize('filename.', cfg) == 'filename'

def test_strip_leading_dot():
    cfg = _cfg(strip_dots_spaces=True)
    assert sanitize('.hidden_file', cfg) == 'hidden_file'

def test_strip_leading_space():
    cfg = _cfg(strip_dots_spaces=True)
    assert sanitize('  filename  ', cfg) == 'filename'

def test_normalize_fullwidth():
    cfg = _cfg(normalize_fullwidth=True)
    assert sanitize('ａｂｃ１２３', cfg) == 'abc123'

def test_collapse_spaces():
    cfg = _cfg(collapse_spaces=True)
    assert sanitize('a  b   c', cfg) == 'a b c'

def test_remove_control_chars():
    cfg = _cfg(remove_control_chars=True)
    assert sanitize('file\x00name\x01', cfg) == 'filename'

def test_rules_off_by_default_dont_apply():
    cfg = SanitizationConfig()  # collapse_spaces=False, remove_control_chars=False
    assert sanitize('a  b', cfg) == 'a  b'
