from pathlib import Path
from PIL import Image, ExifTags

PHOTO_DIR = Path("photos")


def read_all_exif(path):
    """Return {tag_name: value} from both the main EXIF block and the Exif sub-IFD."""
    with Image.open(path) as img:
        exif = img.getexif()
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        # The interesting camera settings live in a nested block, not the top level.
        sub = exif.get_ifd(0x8769)
        tags.update({ExifTags.TAGS.get(k, k): v for k, v in sub.items()})
        gps = exif.get_ifd(0x8825)
        if gps:
            tags["_GPS_PRESENT"] = True
    return tags


def main():
    images = sorted(p for p in PHOTO_DIR.iterdir() if p.suffix.lower() == ".jpg")
    if not images:
        print("No JPGs found.")
        return

    first = images[0]
    print(f"=== All EXIF tags in {first.name} ===\n")
    for name, value in sorted(read_all_exif(first).items(), key=lambda x: str(x[0])):
        text = str(value)
        if len(text) > 70:
            text = text[:70] + "…"
        print(f"{str(name):<28} {text}")

    print(f"\n=== Which tags appear in all {len(images)} images? ===\n")
    per_image = [set(read_all_exif(p).keys()) for p in images]
    common = set.intersection(*per_image)
    everything = set.union(*per_image)
    for name in sorted(common, key=str):
        print(f"  always: {name}")
    for name in sorted(everything - common, key=str):
        print(f"  sometimes: {name}")


if __name__ == "__main__":
    main()