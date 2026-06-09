# folder_file_renamer.spec

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
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name="FolderFileRenamer",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon="resources/icon.ico",
)
