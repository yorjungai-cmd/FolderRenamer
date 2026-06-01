import os
import shutil
from typing import List, Tuple


def check_conflicts(renames: List[Tuple[str, str]]) -> List[str]:
    """Return a list of new paths that appear more than once in the rename list."""
    new_paths = [new for _, new in renames]
    seen: set = set()
    conflicts: set = set()
    for path in new_paths:
        if path in seen:
            conflicts.add(path)
        else:
            seen.add(path)
    return list(conflicts)


def check_filesystem_conflicts(renames: List[Tuple[str, str]]) -> List[str]:
    """Return new_paths that already exist on disk (excluding same-file renames)."""
    return [
        new for old, new in renames
        if os.path.exists(new) and os.path.abspath(new) != os.path.abspath(old)
    ]


def check_missing_sources(renames: List[Tuple[str, str]]) -> List[str]:
    """Return a list of source paths that do not exist on disk."""
    return [old for old, _ in renames if not os.path.exists(old)]


def apply_renames(renames: List[Tuple[str, str]]) -> List[dict]:
    """Rename each (old, new) pair and return per-file result dicts.

    Each result dict has keys: old_path, new_path, status ('renamed' | 'failed'), error.
    Same-directory renames use os.rename; cross-directory moves use shutil.move.
    """
    results = []
    for old, new in renames:
        try:
            if os.path.dirname(os.path.abspath(old)) == os.path.dirname(os.path.abspath(new)):
                os.rename(old, new)
            else:
                shutil.move(old, new)
            results.append({"old_path": old, "new_path": new, "status": "renamed", "error": None})
        except OSError as e:
            results.append({"old_path": old, "new_path": new, "status": "failed", "error": str(e)})
    return results


def safe_filename_length(stem: str, ext: str, max_bytes: int = 255) -> str:
    """Truncate stem so that (stem + ext) fits within max_bytes when UTF-8 encoded.

    Partial multi-byte characters at the cut point are silently dropped.
    """
    if len((stem + ext).encode("utf-8")) <= max_bytes:
        return stem
    available = max_bytes - len(ext.encode("utf-8"))
    truncated = stem.encode("utf-8")[:available]
    return truncated.decode("utf-8", errors="ignore")
