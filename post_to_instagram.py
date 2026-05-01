#!/usr/bin/env python3
"""
post_to_instagram.py

Generates 3 abstract story cards for a Hapi topic and publishes them
as an Instagram carousel. Images are temporarily committed to GitHub
Pages for hosting and deleted immediately after posting.

Setup
-----
Export these env vars (or put them in a .env file and source it):
  IG_ACCESS_TOKEN   — long-lived Instagram Graph API token (60-day expiry)
  IG_BUSINESS_ID    — Instagram Business Account ID
  DEFAULT_IG_TOPIC  — (optional) topic to post when none is given on CLI
                       defaults to "Health & Wellness"

Usage
-----
  python3 post_to_instagram.py                        # uses DEFAULT_IG_TOPIC
  python3 post_to_instagram.py "Health & Wellness"
  python3 post_to_instagram.py "Pets & Wildlife"
"""

import json, os, sys, time, random, subprocess, requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
BASE          = Path("/Users/areznik/Documents/Claude/Projects/LiRoS")
SITE          = "https://arkashka.github.io/liros"
IG_IMG_SUBDIR = "ig"
IG_IMG_DIR    = BASE / IG_IMG_SUBDIR

FONT_DIR      = BASE / "fonts"
FONT_FILE     = FONT_DIR / "Nunito-Bold.ttf"
FONT_URL      = "https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito%5Bwght%5D.ttf"

IG_TOKEN      = os.environ.get("IG_ACCESS_TOKEN", "")
IG_BIZ_ID     = os.environ.get("IG_BUSINESS_ID", "")
DEFAULT_TOPIC = os.environ.get("DEFAULT_IG_TOPIC", "Health & Wellness")

IMG_SIZE      = (1080, 1080)
IG_API        = "https://graph.instagram.com/v20.0"

_font_cache: dict = {}


# ── Font ──────────────────────────────────────────────────────────────────────
def get_font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _font_cache:
        if not FONT_FILE.exists():
            print(f"  Downloading Nunito Bold → {FONT_FILE}")
            FONT_DIR.mkdir(exist_ok=True)
            r = requests.get(FONT_URL, timeout=30)
            r.raise_for_status()
            FONT_FILE.write_bytes(r.content)
        _font_cache[size] = ImageFont.truetype(str(FONT_FILE), size)
    return _font_cache[size]


# ── Colour helpers ────────────────────────────────────────────────────────────
def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def blend(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

def darken(rgb: tuple, factor: float = 0.7) -> tuple:
    return tuple(max(0, int(c * (1 - factor))) for c in rgb)

def lighten(rgb: tuple, factor: float = 0.3) -> tuple:
    return tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)


# ── Image generation ──────────────────────────────────────────────────────────
def wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont,
              max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def make_card(story: dict, topic_color: str,
              card_index: int, total_cards: int,
              out_path: Path) -> None:
    W, H    = IMG_SIZE
    color   = hex_to_rgb(topic_color)
    dark_bg = darken(color, 0.88)
    mid_bg  = darken(color, 0.62)
    light   = lighten(color, 0.30)

    # ── Base canvas ───────────────────────────────────────────────────────────
    img = Image.new("RGBA", (W, H), (*dark_bg, 255))

    # Vertical gradient (dark top → mid bottom)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        c = blend(dark_bg, mid_bg, y / H)
        draw.line([(0, y), (W, y)], fill=(*c, 255))

    # ── Abstract decorative circles ───────────────────────────────────────────
    rng = random.Random(hash(story["title"]) + card_index * 9973)
    for _ in range(14):
        cx     = rng.randint(-180, W + 180)
        cy     = rng.randint(-180, int(H * 0.72))
        radius = rng.randint(50, 290)
        alpha  = rng.randint(20, 58)
        bright = rng.randint(15, 58)
        fill   = tuple(min(255, c + bright) for c in color)
        layer  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*fill, alpha)
        )
        img = Image.alpha_composite(img, layer)

    # Subtle diagonal light streak
    streak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(streak).polygon(
        [(W * 0.55, 0), (W * 0.76, 0), (W * 0.46, H * 0.58), (W * 0.25, H * 0.58)],
        fill=(*light, 14)
    )
    img = Image.alpha_composite(img, streak)

    # ── Bottom text panel ─────────────────────────────────────────────────────
    panel_h = 390
    panel_y = H - panel_h
    panel   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rectangle([0, panel_y, W, H], fill=(8, 8, 20, 218))
    img  = Image.alpha_composite(img, panel)
    draw = ImageDraw.Draw(img)

    # ── Progress dots (top-right) ─────────────────────────────────────────────
    dot_r       = 9
    dot_y       = 50
    dot_spacing = 30
    total_dots_w = (total_cards - 1) * dot_spacing
    dot_start_x  = W - 48 - total_dots_w
    for i in range(total_cards):
        x = dot_start_x + i * dot_spacing
        a = 255 if i == card_index else 90
        draw.ellipse([x - dot_r, dot_y - dot_r, x + dot_r, dot_y + dot_r],
                     fill=(*light, a))

    # ── Title text ────────────────────────────────────────────────────────────
    title_font  = get_font(54)
    source_font = get_font(30)
    padding     = 60
    max_w       = W - padding * 2

    lines    = wrap_text(draw, story["title"], title_font, max_w)
    line_h   = 72
    total_th = len(lines) * line_h
    text_y   = panel_y + (panel_h - total_th - 55) // 2

    for ln in lines:
        bbox   = draw.textbbox((0, 0), ln, font=title_font)
        text_w = bbox[2] - bbox[0]
        x      = (W - text_w) // 2
        # drop shadow
        draw.text((x + 2, text_y + 2), ln, font=title_font, fill=(0, 0, 0, 110))
        draw.text((x, text_y),         ln, font=title_font, fill=(255, 255, 255, 255))
        text_y += line_h

    # ── Source line ───────────────────────────────────────────────────────────
    src       = story["source"]
    src_bbox  = draw.textbbox((0, 0), src, font=source_font)
    src_w     = src_bbox[2] - src_bbox[0]
    draw.text(((W - src_w) // 2, H - 50), src,
              font=source_font, fill=(175, 175, 200, 210))

    # ── Save as JPEG ──────────────────────────────────────────────────────────
    img.convert("RGB").save(out_path, "JPEG", quality=95)
    print(f"  ✓ {out_path.name}")


# ── GitHub Pages hosting ──────────────────────────────────────────────────────
def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(BASE), *args], check=True,
                   capture_output=True, text=True)


def push_images(paths: list[Path], date: str) -> None:
    IG_IMG_DIR.mkdir(exist_ok=True)
    git("add", *[str(p) for p in paths])
    git("commit", "-m", f"temp: instagram images {date}")
    git("push", "origin", "main")
    print("  Pushed to GitHub Pages")


def delete_images(paths: list[Path], date: str) -> None:
    for p in paths:
        p.unlink(missing_ok=True)
    # Stage deletions (git add -A handles removals in the ig/ dir)
    git("add", str(IG_IMG_DIR))
    git("commit", "-m", f"temp: remove instagram images {date}")
    git("push", "origin", "main")
    print("  Cleaned up images from GitHub Pages")


def wait_for_url(url: str, timeout: int = 600, interval: int = 15) -> None:
    """Poll until GitHub Pages serves the image (can take a few minutes)."""
    print(f"  Waiting for Pages: {url}", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.head(url, timeout=10)
            if r.status_code == 200:
                print(" ✓")
                return
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(interval)
    raise TimeoutError(f"Image not available at {url} after {timeout}s")


# ── Instagram Graph API ───────────────────────────────────────────────────────
def ig_post(path: str, payload: dict) -> dict:
    r = requests.post(
        f"{IG_API}/{path}",
        params={"access_token": IG_TOKEN},
        json=payload,
        timeout=30,
    )
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print(f"  Instagram API error: {r.text}")
        raise
    return r.json()


def wait_for_media_ready(media_id: str, timeout: int = 120) -> None:
    """Instagram needs time to process uploaded images before carousel assembly."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(
            f"{IG_API}/{media_id}",
            params={"fields": "status_code", "access_token": IG_TOKEN},
            timeout=10,
        )
        status = r.json().get("status_code", "")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram media {media_id} failed processing")
        time.sleep(5)
    raise TimeoutError(f"Media {media_id} not ready after {timeout}s")


def post_carousel(image_urls: list[str], caption: str) -> str:
    child_ids = []
    for i, url in enumerate(image_urls, 1):
        print(f"  Creating media container {i}/{len(image_urls)} …")
        result = ig_post(f"{IG_BIZ_ID}/media", {
            "image_url": url,
            "is_carousel_item": True,
        })
        media_id = result["id"]
        wait_for_media_ready(media_id)
        child_ids.append(media_id)
        time.sleep(2)

    print("  Assembling carousel …")
    carousel = ig_post(f"{IG_BIZ_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
    })

    print("  Publishing …")
    published = ig_post(f"{IG_BIZ_ID}/media_publish", {
        "creation_id": carousel["id"],
    })
    return published["id"]


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    topic_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC

    if not IG_TOKEN or not IG_BIZ_ID:
        sys.exit(
            "Error: IG_ACCESS_TOKEN and IG_BUSINESS_ID must be set.\n"
            "  export IG_ACCESS_TOKEN='your_token'\n"
            "  export IG_BUSINESS_ID='your_business_id'"
        )

    print(f"\n📸  Posting '{topic_name}' to Instagram\n")

    # Load stories
    data   = json.load(open(BASE / "topics.json"))
    pull   = data["pulls"][0]
    topic  = pull["topics"].get(topic_name)
    if not topic:
        available = list(pull["topics"].keys())
        sys.exit(f"Topic '{topic_name}' not found.\nAvailable: {available}")

    stories = topic["stories"]
    color   = topic["color"]
    date    = pull["date"]

    # Generate images
    print("🎨  Generating images …")
    IG_IMG_DIR.mkdir(exist_ok=True)
    img_paths = []
    for i, story in enumerate(stories):
        fname = f"hapi-ig-{date}-{i+1}.jpg"
        make_card(story, color, i, len(stories), IG_IMG_DIR / fname)
        img_paths.append(IG_IMG_DIR / fname)

    # Push to GitHub Pages, then clean up regardless of what happens next
    print("\n🌐  Publishing images to GitHub Pages …")
    push_images(img_paths, date)

    try:
        # Wait for GitHub Pages to propagate
        image_urls = [f"{SITE}/{IG_IMG_SUBDIR}/{p.name}" for p in img_paths]
        print()
        for url in image_urls:
            wait_for_url(url)

        # Post carousel
        print("\n📲  Posting to Instagram …")
        post_id = post_carousel(image_urls, "#Hapi")
        print(f"\n✅  Posted! Instagram media ID: {post_id}")

    finally:
        # Always clean up, even if posting failed
        print("\n🧹  Removing images from GitHub Pages …")
        delete_images(img_paths, date)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
