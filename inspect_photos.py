from pathlib import Path
from PIL import Image

PHOTO_DIR = Path("photos")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def find_images(folder):
    """Yield image files in folder, sorted, ignoring case on extensions."""
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            yield path


def describe(path):
    with Image.open(path) as img:
        width, height = img.size
        mode = img.mode
        exif = img.getexif()
    size_mb = path.stat().st_size / 1_000_000
    has_exif = "exif" if len(exif) else "no exif"
    return f"{path.name:<40} {width}x{height:<12} {mode:<6} {size_mb:>6.1f} MB   {has_exif}"


def main():
    if not PHOTO_DIR.exists():
        print(f"No '{PHOTO_DIR}' folder found. Create it and add some images.")
        return

    images = list(find_images(PHOTO_DIR))
    if not images:
        print(f"'{PHOTO_DIR}' exists but has no images in it.")
        return

    for path in images:
        print(describe(path))
    print(f"\n{len(images)} images.")


if __name__ == "__main__":
    main()