import json, os
from dataclasses import dataclass, field, asdict
from typing import List

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, "FolderFileRenamer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

@dataclass
class SanitizationConfig:
    remove_illegal: bool = True
    remove_emoji: bool = True
    strip_dots_spaces: bool = True
    normalize_fullwidth: bool = True
    remove_control_chars: bool = False
    collapse_spaces: bool = False
    replacement_char: str = ""

@dataclass
class AppConfig:
    provider: str = "deepl"
    deepl_key: str = ""
    deepl_pro: bool = False
    openrouter_key: str = ""
    openrouter_model: str = "google/gemini-flash-1.5"
    batch_delay_ms: int = 200
    request_timeout_s: int = 30
    file_extensions: List[str] = field(default_factory=lambda: [
        ".mp4", ".mkv", ".avi", ".ts", ".wmv", ".flv", ".mov", ".iso", ".m2ts"
    ])
    scan_subdirectories: bool = True
    sanitization: SanitizationConfig = field(default_factory=SanitizationConfig)

    def save(self):
        import config as _cfg_module
        os.makedirs(_cfg_module.CONFIG_DIR, exist_ok=True)
        with open(_cfg_module.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "AppConfig":
        import config as _cfg_module
        if not os.path.exists(_cfg_module.CONFIG_FILE):
            return cls()
        try:
            with open(_cfg_module.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            san_data = data.pop("sanitization", {})
            cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            cfg.sanitization = SanitizationConfig(**{
                k: v for k, v in san_data.items()
                if k in SanitizationConfig.__dataclass_fields__
            })
            return cfg
        except Exception:
            return cls()
