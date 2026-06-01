# folder_file_renamer.spec
import os
block_cipher = None
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[("resources", "resources")],
    hiddenimports=[
        "PyQt6.QtCore", "PyQt6.QtWidgets", "PyQt6.QtGui",
        "httpx", "emoji", "unicodedata",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="FolderFileRenamer",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon="resources/icon.ico" if os.path.exists("resources/icon.ico") else None,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True,
    name="FolderFileRenamer",
)
