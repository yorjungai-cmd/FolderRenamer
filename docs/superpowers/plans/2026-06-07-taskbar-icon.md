# Taskbar Icon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Windows executable and running Qt application the approved indigo folder-and-arrows icon.

**Architecture:** Generate a deterministic multi-resolution Windows icon from a small Pillow script and commit both the generator and generated asset. Add a focused `main.py` helper that resolves bundled resources and applies the icon before the main window is created, then make PyInstaller require the same asset at build time.

**Tech Stack:** Python 3.11+, Pillow, PyQt6, pytest, PyInstaller

---

## File Structure

- Create `tools/generate_icon.py`: draw the approved icon and write all required `.ico` sizes.
- Create `resources/icon.ico`: generated Windows application icon consumed by Qt and PyInstaller.
- Create `tests/test_icon_resource.py`: validate the committed icon's format and embedded resolutions.
- Modify `main.py`: resolve resource paths and apply the Qt application icon.
- Modify `tests/test_main_window.py`: verify runtime icon loading and missing-resource tolerance.
- Modify `folder_file_renamer.spec`: require the icon instead of silently falling back.

### Task 1: Generate the Multi-Resolution Icon

**Files:**
- Create: `tests/test_icon_resource.py`
- Create: `tools/generate_icon.py`
- Create: `resources/icon.ico`

- [ ] **Step 1: Write the failing icon resource test**

Create `tests/test_icon_resource.py`:

```python
from pathlib import Path

from PIL import Image


REQUIRED_ICON_SIZES = {
    (16, 16),
    (20, 20),
    (24, 24),
    (32, 32),
    (40, 40),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
}


def test_windows_icon_contains_required_sizes():
    icon_path = Path(__file__).parents[1] / "resources" / "icon.ico"

    assert icon_path.is_file()
    with Image.open(icon_path) as icon:
        assert icon.format == "ICO"
        assert REQUIRED_ICON_SIZES <= icon.ico.sizes()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
pytest tests/test_icon_resource.py -v
```

Expected: FAIL because `resources/icon.ico` does not exist.

- [ ] **Step 3: Add the deterministic icon generator**

Create `tools/generate_icon.py`:

```python
from pathlib import Path

from PIL import Image, ImageDraw


ICON_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
CANVAS_SIZE = 256
INDIGO = "#4f46e5"
LIGHT_INDIGO = "#818cf8"
WHITE = "#ffffff"


def draw_icon() -> Image.Image:
    image = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((20, 56, 236, 220), radius=36, fill=INDIGO)
    draw.polygon(
        [(20, 78), (20, 62), (36, 42), (104, 42), (132, 72), (236, 72), (236, 112), (20, 112)],
        fill=LIGHT_INDIGO,
    )

    stroke = 18
    draw.line((68, 137, 174, 137), fill=WHITE, width=stroke)
    draw.line((154, 116, 178, 137, 154, 158), fill=WHITE, width=stroke, joint="curve")
    draw.line((188, 183, 82, 183), fill=WHITE, width=stroke)
    draw.line((102, 162, 78, 183, 102, 204), fill=WHITE, width=stroke, joint="curve")
    return image


def main() -> None:
    project_root = Path(__file__).parents[1]
    output_path = project_root / "resources" / "icon.ico"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draw_icon().save(output_path, format="ICO", sizes=[(size, size) for size in ICON_SIZES])
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the icon**

Run:

```powershell
python tools/generate_icon.py
```

Expected: prints `Wrote ...\resources\icon.ico`.

- [ ] **Step 5: Run the icon test**

Run:

```powershell
pytest tests/test_icon_resource.py -v
```

Expected: PASS, confirming ICO format and all nine required sizes.

- [ ] **Step 6: Inspect the generated artwork**

Open `resources/icon.ico` or render its 256 px frame and confirm:

- Transparent exterior corners.
- Indigo folder and lighter tab.
- Two white opposing arrows.
- No text or fine decorative details.
- Arrows remain distinguishable at 16, 24, and 32 px.

If small frames are unclear, adjust only coordinates or stroke width in `tools/generate_icon.py`, regenerate, and rerun the test.

- [ ] **Step 7: Commit the icon asset**

```powershell
git add tools/generate_icon.py resources/icon.ico tests/test_icon_resource.py
git commit -m "feat: add Windows application icon"
```

### Task 2: Apply the Icon at Qt Runtime

**Files:**
- Modify: `tests/test_main_window.py`
- Modify: `main.py`

- [ ] **Step 1: Write failing runtime icon tests**

Append to `tests/test_main_window.py`:

```python
def test_set_application_icon_loads_existing_resource(tmp_path):
    from PyQt6.QtWidgets import QApplication
    from main import set_application_icon

    app = QApplication.instance() or QApplication([])
    icon_path = tmp_path / "icon.ico"
    source_icon = os.path.join(os.path.dirname(__file__), "..", "resources", "icon.ico")
    icon_path.write_bytes(open(source_icon, "rb").read())

    assert set_application_icon(app, icon_path) is True
    assert app.windowIcon().isNull() is False


def test_set_application_icon_ignores_missing_resource(tmp_path):
    from PyQt6.QtWidgets import QApplication
    from main import set_application_icon

    app = QApplication.instance() or QApplication([])

    assert set_application_icon(app, tmp_path / "missing.ico") is False
```

Use a context manager instead of the bare `open()` call when implementing the
test:

```python
    with open(source_icon, "rb") as source:
        icon_path.write_bytes(source.read())
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```powershell
pytest tests/test_main_window.py::test_set_application_icon_loads_existing_resource tests/test_main_window.py::test_set_application_icon_ignores_missing_resource -v
```

Expected: FAIL with an import error because `set_application_icon` does not exist.

- [ ] **Step 3: Implement resource resolution and icon application**

Update the imports and add helpers near the top of `main.py`:

```python
import os
import sys
from pathlib import Path

from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication


def resource_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)


def set_application_icon(app: QApplication, icon_path: Path) -> bool:
    if not icon_path.is_file():
        return False

    icon = QIcon(str(icon_path))
    if icon.isNull():
        return False

    app.setWindowIcon(icon)
    return True
```

Keep the existing application imports below the Qt imports:

```python
from config import AppConfig
from ui.main_window import MainWindow
```

At the start of `main()`, apply the icon immediately after setting the
application name:

```python
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FolderFileRenamer")
    set_application_icon(app, resource_path("resources", "icon.ico"))
```

Replace the current `os.path.dirname(__file__)` resource joins with:

```python
    fonts_dir = resource_path("resources", "fonts")
```

and:

```python
    qss = resource_path("resources", "styles.qss")
```

Use `Path` operations for iteration and file loading:

```python
    if fonts_dir.is_dir():
        for font_path in fonts_dir.iterdir():
            if font_path.suffix.lower() in (".ttf", ".otf"):
                QFontDatabase.addApplicationFont(str(font_path))
    if qss.is_file():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
pytest tests/test_main_window.py -v
```

Expected: all main-window tests PASS.

- [ ] **Step 5: Run the complete test suite**

Run:

```powershell
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the runtime integration**

```powershell
git add main.py tests/test_main_window.py
git commit -m "fix: apply application icon at runtime"
```

### Task 3: Require the Icon in PyInstaller

**Files:**
- Modify: `folder_file_renamer.spec`

- [ ] **Step 1: Remove the silent fallback**

Delete the unused `import os` and change the EXE icon argument from:

```python
icon="resources/icon.ico" if os.path.exists("resources/icon.ico") else None,
```

to:

```python
icon="resources/icon.ico",
```

This makes a missing icon a visible build failure rather than producing another
generic executable.

- [ ] **Step 2: Check the spec diff**

Run:

```powershell
git diff --check -- folder_file_renamer.spec
git diff -- folder_file_renamer.spec
```

Expected: no whitespace errors; the diff only removes `import os` and requires
`resources/icon.ico`.

- [ ] **Step 3: Build the executable**

Run:

```powershell
pyinstaller folder_file_renamer.spec --clean
```

Expected: exit code 0 and `dist\FolderFileRenamer.exe` exists.

- [ ] **Step 4: Verify the executable icon resource**

Run:

```powershell
@'
from pathlib import Path
from PIL import Image

icon = Image.open(Path("resources/icon.ico"))
print(sorted(icon.ico.sizes()))
assert Path("dist/FolderFileRenamer.exe").is_file()
'@ | python -
```

Expected: all required sizes are printed and the executable assertion passes.
PyInstaller's successful `icon=` processing confirms that the icon was embedded
into the PE resource.

- [ ] **Step 5: Launch and visually verify the taskbar**

Run:

```powershell
Start-Process -FilePath (Resolve-Path "dist\FolderFileRenamer.exe")
```

Confirm the running app's taskbar button shows the approved folder-and-arrows
icon. Also confirm the executable shows the same icon in File Explorer. Close
the application after verification.

If Explorer still shows an old icon, rename the freshly built executable once
or restart Explorer to bypass the Windows icon cache, then verify again.

- [ ] **Step 6: Commit the packaging fix**

```powershell
git add folder_file_renamer.spec
git commit -m "build: require Windows application icon"
```

### Task 4: Final Regression and Graph Update

**Files:**
- Modify: `graphify-out/` generated graph files

- [ ] **Step 1: Run final automated verification**

Run:

```powershell
pytest -v
python -m compileall -q main.py tools tests
git diff --check
```

Expected: all tests PASS, compilation exits 0, and no whitespace errors are
reported.

- [ ] **Step 2: Confirm no unrelated files are staged**

Run:

```powershell
git status --short
```

Expected: pre-existing unrelated changes such as `CLAUDE.md`, `.codex/`,
`AGENTS.md`, or `.ai_temp_log.txt` remain unstaged and untouched.

- [ ] **Step 3: Refresh the knowledge graph**

Run:

```powershell
graphify update .
```

Expected: graph extraction completes successfully and records the new runtime
helper, icon test, and generator relationships.

- [ ] **Step 4: Review the completed history**

Run:

```powershell
git log -4 --oneline
```

Expected: separate commits exist for the design, icon asset, runtime
integration, and PyInstaller requirement.
