from pathlib import Path
from PIL import Image, ImageOps

PHOTO_DIR = Path("photos")
OUT_DIR = Path("web/images")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

SIZES = {
    "thumb": 400,
    "large": 1600,
}
QUALITY = 82


def find_images(folder):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            yield path


def output_path(source, kind):
    """photos/film/img_003.tif -> web/images/thumb/film/img_003.jpg"""
    relative = source.relative_to(PHOTO_DIR).with_suffix(".jpg")
    return OUT_DIR / kind / relative


def resize_one(source, kind, long_edge, force=False):
    target = output_path(source, kind)
    if target.exists() and not force:
        return False

    with Image.open(source) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
        img.thumbnail((long_edge, long_edge), Image.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        img.save(target, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return True


def main():
    images = list(find_images(PHOTO_DIR))
    if not images:
        print(f"No images found in '{PHOTO_DIR}'.")
        return

    made = skipped = failed = 0
    for source in images:
        for kind, long_edge in SIZES.items():
            try:
                if resize_one(source, kind, long_edge):
                    made += 1
                else:
                    skipped += 1
            except Exception as err:
                print(f"FAIL  {source.name} ({kind}): {err}")
                failed += 1

    total_bytes = sum(p.stat().st_size for p in OUT_DIR.rglob("*.jpg"))
    print(f"\nCreated {made}, skipped {skipped} (already existed), failed {failed}.")
    print(f"{OUT_DIR} is now {total_bytes / 1_000_000:.1f} MB")


if __name__ == "__main__":
    main()