"""Create a deduplicated, standardized manifest from the raw stage folders."""

import argparse
import csv
import hashlib
import re
from pathlib import Path

from PIL import Image, ImageOps


CLASSES = ("seedling", "vegetative", "reproductive", "maturity")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def plant_id(stage: str, source: str, path: Path) -> str:
    stem = re.sub(r"^(train|valid|test)_", "", path.stem, flags=re.IGNORECASE)
    stem = re.sub(r"\.rf\.[0-9a-f]+$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    return f"{stage}-{source}-{stem}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--size", type=int, default=256)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    rows = []

    for stage in CLASSES:
        stage_dir = args.raw_dir / stage
        for path in sorted(stage_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            source = path.relative_to(stage_dir).parts[0]
            target_dir = args.output_dir / stage
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{digest[:20]}.jpg"
            if not target.exists():
                with Image.open(path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((args.size, args.size), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGB", (args.size, args.size), (127, 127, 127))
                    canvas.paste(image, ((args.size - image.width) // 2, (args.size - image.height) // 2))
                    canvas.save(target, "JPEG", quality=92, optimize=True)
            rows.append({
                "image_path": target.relative_to(args.manifest.parent).as_posix(),
                "plant_id": plant_id(stage, source, path),
                "stage_label": stage,
            })

    with args.manifest.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=("image_path", "plant_id", "stage_label"))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Prepared {len(rows)} unique images at {args.output_dir}")


if __name__ == "__main__":
    main()
