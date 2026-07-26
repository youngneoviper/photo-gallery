import json
from pathlib import Path
from PIL import Image, ExifTags, ImageOps

PHOTO_DIR = Path("photos")
OUTPUT = Path("data/photos.json")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

# EXIF fields worth keeping. Everything here may be missing.
WANTED_EXIF = [
    "Make", "Model", "DateTimeOriginal", "ISOSpeedRatings",
    "FNumber", "ExposureTime", "FocalLength", "LensModel",
]


def find_images(folder):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            yield path


def read_exif(img):
    """Pull wanted tags from the main block and the Exif sub-IFD. Missing -> None."""
    out = {key: None for key in WANTED_EXIF}
    try:
        exif = img.getexif()
    except Exception:
        return out
    if not exif:
        return out

    tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    try:
        tags.update({ExifTags.TAGS.get(k, k): v for k, v in exif.get_ifd(0x8769).items()})
    except Exception:
        pass

    for key in WANTED_EXIF:
        value = tags.get(key)
        if value is None:
            continue
        if isinstance(value, bytes):
            continue          # skip binary blobs, they don't belong in JSON
        if isinstance(value, str):
            value = value.strip().rstrip("\x00")
            if not value:
                continue
        else:
            value = round(float(value), 4)
        out[key] = value
    return out


def dominant_color(img, palette_size=5):
    """Median-cut the image down to a few colors, return the most common as (r,g,b)."""
    small = img.copy()
    small.thumbnail((120, 120))
    quantized = small.quantize(colors=palette_size, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    counts = sorted(quantized.getcolors(), reverse=True)
    index = counts[0][1]
    return tuple(palette[index * 3: index * 3 + 3])


def rgb_to_hsv(rgb):
    """Return hue 0-360, saturation 0-1, value 0-1."""
    r, g, b = (c / 255 for c in rgb)
    high, low = max(r, g, b), min(r, g, b)
    delta = high - low
    if delta == 0:
        hue = 0.0
    elif high == r:
        hue = (60 * ((g - b) / delta)) % 360
    elif high == g:
        hue = 60 * ((b - r) / delta) + 120
    else:
        hue = 60 * ((r - g) / delta) + 240
    sat = 0.0 if high == 0 else delta / high
    return round(hue, 1), round(sat, 3), round(high, 3)


def brightness(img):
    """Mean perceived luminance, 0-1."""
    small = img.copy()
    small.thumbnail((80, 80))
    pixels = list(small.convert("RGB").getdata())
    total = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels)
    return round(total / len(pixels) / 255, 3)

def collection_of(path):
    """Top-level folder under photos/ — 'film', 'digital', 'charmera'."""
    parts = path.relative_to(PHOTO_DIR).parts
    return parts[0] if len(parts) > 1 else "uncategorized"

def describe(path):
    with Image.open(path) as raw:
        img = ImageOps.exif_transpose(raw)   # apply rotation so w/h are what you see
        img = img.convert("RGB")
        width, height = img.size
        rgb = dominant_color(img)
        hue, sat, val = rgb_to_hsv(rgb)
        exif = read_exif(raw)

    return {
        "file": path.relative_to(PHOTO_DIR).as_posix(),
        "collection": collection_of(path),
        "width": width,
        "height": height,
        "aspect": round(width / height, 4),
        "orientation": "landscape" if width > height else "portrait" if height > width else "square",
        "color": {
            "rgb": list(rgb),
            "hex": "#{:02x}{:02x}{:02x}".format(*rgb),
            "hue": hue,
            "saturation": sat,
            "value": val,
        },
        "brightness": brightness(img),
        "exif": exif,
        "size_bytes": path.stat().st_size,
    }


def main():
    if not PHOTO_DIR.exists():
        print(f"No '{PHOTO_DIR}' folder.")
        return

    records = []
    for path in find_images(PHOTO_DIR):
        try:
            records.append(describe(path))
            print(f"ok    {path.name}")
        except Exception as err:
            print(f"FAIL  {path.name}: {err}")

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(records, indent=2))

    with_exif = sum(1 for r in records if r["exif"]["Model"])
    from collections import Counter
    by_collection = Counter(r["collection"] for r in records)
    with_exif = sum(1 for r in records if r["exif"]["Model"])

    print(f"\nWrote {len(records)} records to {OUTPUT}")
    for name, count in sorted(by_collection.items()):
        print(f"  {name}: {count}")
    print(f"{with_exif}/{len(records)} have a camera model.")


if __name__ == "__main__":
    main()