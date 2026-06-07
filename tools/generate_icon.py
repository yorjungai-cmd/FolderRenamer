from pathlib import Path

from PIL import Image, ImageDraw


CANVAS_SIZE = 256
SUPERSAMPLE = 4
ICON_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

INDIGO = "#4F46E5"
LIGHT_INDIGO = "#818CF8"
WHITE = "#FFFFFF"


def scaled_box(box):
    return tuple(value * SUPERSAMPLE for value in box)


def scaled_points(points):
    return [(x * SUPERSAMPLE, y * SUPERSAMPLE) for x, y in points]


def draw_icon() -> Image.Image:
    image = Image.new(
        "RGBA",
        (CANVAS_SIZE * SUPERSAMPLE, CANVAS_SIZE * SUPERSAMPLE),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        scaled_box((38, 38, 139, 105)),
        radius=18 * SUPERSAMPLE,
        fill=LIGHT_INDIGO,
    )
    draw.rounded_rectangle(
        scaled_box((24, 70, 232, 224)),
        radius=26 * SUPERSAMPLE,
        fill=INDIGO,
    )

    draw.polygon(
        scaled_points(
            [
                (54, 102),
                (160, 102),
                (160, 86),
                (211, 118),
                (160, 150),
                (160, 134),
                (54, 134),
            ]
        ),
        fill=WHITE,
    )
    draw.polygon(
        scaled_points(
            [
                (202, 158),
                (96, 158),
                (96, 142),
                (45, 174),
                (96, 206),
                (96, 190),
                (202, 190),
            ]
        ),
        fill=WHITE,
    )

    return image.resize(
        (CANVAS_SIZE, CANVAS_SIZE),
        Image.Resampling.LANCZOS,
    )


def main() -> None:
    output_path = Path(__file__).resolve().parents[1] / "resources" / "icon.ico"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draw_icon().save(
        output_path,
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
    )


if __name__ == "__main__":
    main()
