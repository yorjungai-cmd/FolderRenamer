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
        [
            (20, 78),
            (20, 62),
            (36, 42),
            (104, 42),
            (132, 72),
            (236, 72),
            (236, 112),
            (20, 112),
        ],
        fill=LIGHT_INDIGO,
    )

    stroke = 18
    draw.line((68, 137, 174, 137), fill=WHITE, width=stroke)
    draw.line(
        (154, 116, 178, 137, 154, 158),
        fill=WHITE,
        width=stroke,
        joint="curve",
    )
    draw.line((188, 183, 82, 183), fill=WHITE, width=stroke)
    draw.line(
        (102, 162, 78, 183, 102, 204),
        fill=WHITE,
        width=stroke,
        joint="curve",
    )
    return image


def main() -> None:
    project_root = Path(__file__).parents[1]
    output_path = project_root / "resources" / "icon.ico"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draw_icon().save(
        output_path,
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
