import re, unicodedata
import emoji as _emoji
from config import SanitizationConfig

_ILLEGAL_RE = re.compile(r'[\\/:*?"<>|]')

def sanitize(text: str, cfg: SanitizationConfig) -> str:
    if cfg.normalize_fullwidth:
        text = unicodedata.normalize("NFKC", text)
    if cfg.remove_emoji:
        text = _emoji.replace_emoji(text, replace=cfg.replacement_char)
    if cfg.remove_illegal:
        text = _ILLEGAL_RE.sub(cfg.replacement_char, text)
    if cfg.remove_control_chars:
        text = "".join(c for c in text if unicodedata.category(c) != "Cc")
    if cfg.collapse_spaces:
        text = re.sub(r" {2,}", " ", text)
    if cfg.strip_dots_spaces:
        text = text.strip().strip(".")
    return text
