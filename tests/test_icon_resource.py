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
