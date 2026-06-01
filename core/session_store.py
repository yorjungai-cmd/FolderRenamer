import json, os
from datetime import datetime
from typing import List

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
SESSIONS_DIR = os.path.join(APPDATA, "FolderFileRenamer", "sessions")
MAX_SESSIONS = 50

def _ensure():
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_session(data: dict) -> str:
    _ensure()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(SESSIONS_DIR, f"{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _prune()
    return path

def list_sessions() -> List[dict]:
    _ensure()
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({"path": fpath, **data})
        except Exception:
            continue
    return sessions

def load_session(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def revert_session(path: str) -> dict:
    data = load_session(path)
    reverted = skipped = failed = 0
    for entry in data.get("files", []):
        if entry.get("status") != "renamed":
            continue
        old_p, new_p = entry["old_path"], entry["new_path"]
        if not os.path.exists(new_p):
            entry["revert_status"] = "skipped"
            skipped += 1
            continue
        try:
            os.replace(new_p, old_p)  # atomic on Windows, overwrites if old_p exists
            entry["revert_status"] = "reverted"
            reverted += 1
        except OSError as e:
            entry["revert_status"] = f"failed: {e}"
            failed += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"reverted": reverted, "skipped": skipped, "failed": failed}

def _prune():
    files = sorted(f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json"))
    while len(files) > MAX_SESSIONS:
        os.remove(os.path.join(SESSIONS_DIR, files.pop(0)))
