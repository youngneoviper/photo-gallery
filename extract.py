import json, colorsys
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


def palette(img, top=8):
    """Bin pixels into fixed HSV regions and count them. Shares are real proportions."""
    small = img.copy()
    small.thumbnail((200, 200))
    # Posterize to 4 bits/channel so getcolors() returns a manageable number of
    # unique values — we only need approximate colour, and this makes the loop fast.
    reduced = ImageOps.posterize(small, 4)
    unique = reduced.getcolors(65536) or []

    bins = {}
    total = 0
    for count, rgb in unique:
        r, g, b = (c / 255 for c in rgb)
        hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
        hue *= 360

        # Dark, pale or washed-out pixels have unreliable hue — bin them by
        # lightness alone rather than letting rounding noise assign a colour.
        if val < 0.18 or sat < 0.15 or val > 0.95:
            key = ("grey", round(val * 6))
        else:
            key = ("hue", int(hue // 24), min(2, int(sat * 3)), min(3, int(val * 4)))

        entry = bins.setdefault(key, {"n": 0, "r": 0, "g": 0, "b": 0})
        entry["n"] += count
        entry["r"] += rgb[0] * count
        entry["g"] += rgb[1] * count
        entry["b"] += rgb[2] * count
        total += count

    entries = []
    for key, acc in bins.items():
        n = acc["n"]
        rgb = (round(acc["r"] / n), round(acc["g"] / n), round(acc["b"] / n))
        hue, sat, val = rgb_to_hsv(rgb)
        share = n / total
        # sqrt(share) stops big dull areas from dominating; sat squared rewards
        # purity. A small patch of vivid pink should beat a large patch of mud.
        salience = (share ** 0.25) * (sat ** 2) * val
        entries.append({
            "rgb": list(rgb),
            "hex": "#{:02x}{:02x}{:02x}".format(*rgb),
            "hue": hue,
            "saturation": sat,
            "value": val,
            "share": round(share, 4),
            "salience": round(salience, 5),
            "achromatic": key[0] == "grey",
        })

    # Pick on two axes: the biggest areas, and the most eye-catching colours.
    # Sorting by share alone drops small vivid regions before they're considered.
    by_share = sorted(entries, key=lambda e: e["share"], reverse=True)
    by_salience = sorted(entries, key=lambda e: e["salience"], reverse=True)

    chosen, seen = [], set()
    for entry in [*by_share[: top - 3], *by_salience[:4]]:
        if entry["hex"] not in seen:
            seen.add(entry["hex"])
            chosen.append(entry)

    chosen.sort(key=lambda e: e["share"], reverse=True)
    return chosen


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
        colors = palette(img)
        exif = read_exif(raw)
        chromatic = [c for c in colors if not c["achromatic"]]
        monochrome = not chromatic

        # ... then in the returned dict:

    return {
        "file": path.relative_to(PHOTO_DIR).as_posix(),
        "collection": collection_of(path),
        "width": width,
        "height": height,
        "aspect": round(width / height, 4),
        "orientation": "landscape" if width > height else "portrait" if height > width else "square",
        "color": colors[0],
        "accent": max(chromatic, key=lambda c: c["salience"]) if chromatic else None,
        "monochrome": monochrome,
        "palette": colors,
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