# Taskbar Icon Design

## Goal

Replace the generic Windows taskbar and executable icon with a recognizable
Folder File Renamer icon.

## Selected Visual

Use the approved "Rename Folder" design:

- Indigo folder with a lighter folder tab.
- Two white opposing arrows representing renaming.
- No text or small decorative details.
- Strong silhouette and contrast at Windows taskbar sizes.

The icon source must produce a Windows `.ico` containing 16, 20, 24, 32, 40,
48, 64, 128, and 256 pixel variants. Small variants may simplify spacing and
stroke widths to remain legible.

## Runtime Behavior

`main.py` will resolve the bundled `resources/icon.ico` path and set it on the
`QApplication` before creating `MainWindow`. Qt will then propagate the icon to
the main window and taskbar button.

Path resolution must work in both source runs and PyInstaller's bundled
environment. If the icon cannot be loaded, startup must continue without an
exception.

## Packaged Executable

`folder_file_renamer.spec` will require `resources/icon.ico` as the executable
icon instead of silently falling back to `None`. The existing `resources`
bundle continues to include the same file for Qt runtime loading.

This gives the built executable and the running application's taskbar button
the same visual identity.

## Testing

Add a focused application-startup test that verifies the Qt application icon
is set when the icon resource exists.

Verification will include:

- The focused icon test first fails before the runtime change.
- The full pytest suite passes after implementation.
- `resources/icon.ico` contains the required embedded sizes.
- PyInstaller completes with the icon configured.
- The built executable contains a non-generic icon.
- A launched build displays the selected icon in the Windows taskbar.

## Scope

This change does not alter application behavior, window layout, updater logic,
version numbers, or release publishing. It only adds and consistently applies
the approved application icon.
