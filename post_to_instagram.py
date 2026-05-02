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
  KEEP_IMAGES       — (optional) set to 1/true/yes to skip cleanup and keep
                       images in ig/ folder for later reposting

Usage
-----
  python3 post_to_instagram.py                        # uses DEFAULT_IG_TOPIC
  python3 post_to_instagram.py "Health & Wellness"
  python3 post_to_instagram.py "Pets & Wildlife"
  KEEP_IMAGES=1 python3 post_to_instagram.py          # keep images for reposting
"""

import json, os, sys, time, random, subprocess, requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
KEEP_IMAGES   = os.environ.get("KEEP_IMAGES", "").lower() in ("1", "true", "yes")

IMG_SIZE      = (1080, 1350)   # 4:5 portrait — optimal for Instagram feed
IG_API        = "https://graph.facebook.com/v20.0"

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


def fit_text_to_zone(draw: ImageDraw.Draw, text: str, max_width: int,
                      zone_height: int, size_start: int, size_min: int = 24,
                      step: int = 4, line_spacing: float = 1.3) -> tuple:
    """Scale font down until wrapped text fits within zone_height. Returns (font, lines, line_h)."""
    size = size_start
    while size >= size_min:
        font   = get_font(size)
        lines  = wrap_text(draw, text, font, max_width)
        sample = draw.textbbox((0, 0), "Ag", font=font)
        line_h = int((sample[3] - sample[1]) * line_spacing)
        if len(lines) * line_h <= zone_height:
            return font, lines, line_h
        size -= step
    font   = get_font(size_min)
    lines  = wrap_text(draw, text, font, max_width)
    sample = draw.textbbox((0, 0), "Ag", font=font)
    line_h = int((sample[3] - sample[1]) * line_spacing)
    return font, lines, line_h


def draw_zone(draw: ImageDraw.Draw, lines: list, font: ImageFont.FreeTypeFont,
              line_h: int, cx: int, zone_top: int, zone_h: int, fill: tuple) -> None:
    """Draw wrapped lines centred horizontally and vertically within a zone."""
    total_h = len(lines) * line_h
    y       = zone_top + (zone_h - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw   = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y), line, font=font, fill=fill)
        y += line_h


def make_card(story: dict, base_color: str,
              index: int, total: int,
              output_path: Path) -> None:
    width, height = IMG_SIZE   # 1080 × 1350 (4:5)

    # Seeded RNG — same story always produces the same card
    rng = random.Random(hash(story["title"]) + index * 9973)

    # ── Pastel background ─────────────────────────────────────────────────────
    bg_options = ["#E0F2F1", "#F3E5F5", "#FFF9C4", "#FCE4EC"]
    canvas     = Image.new("RGB", (width, height), rng.choice(bg_options))

    # ── Soft blurred organic bubbles ──────────────────────────────────────────
    bubble_palette = [
        (255, 182, 193),  # blush
        (173, 216, 230),  # baby blue
        (255, 253, 208),  # butter
        (200, 230, 201),  # mint
        (225, 190, 231),  # lavender
    ]
    for _ in range(8):
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        r       = rng.randint(300, 800)
        x       = rng.randint(-200, width)
        y       = rng.randint(-200, height)
        bc      = rng.choice(bubble_palette)
        ImageDraw.Draw(overlay).ellipse([x, y, x + r, y + r], fill=(*bc, 80))
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=60))
        canvas.paste(overlay, (0, 0), overlay)

    # ── Subtle grain (editorial tactile feel) ─────────────────────────────────
    noise = Image.effect_noise((width, height), 15).convert("RGBA")
    noise.putalpha(13)   # ~5% opacity
    canvas.paste(noise, (0, 0), noise)

    # ── Layout zones ──────────────────────────────────────────────────────────
    # Fixed zones prevent title/summary from ever overlapping:
    #   [80px top pad] [TITLE zone 460px] [60px gap] [SUMMARY zone 540px] [counter 80px]
    margin     = 100
    text_w     = width - margin * 2
    cx         = width // 2
    text_color = (55, 55, 55)
    muted      = (145, 145, 145)

    title_top  = 80;   title_h  = 460
    gap        = 60
    summ_top   = title_top + title_h + gap
    summ_h     = 540
    counter_y  = summ_top + summ_h + 20

    draw = ImageDraw.Draw(canvas)

    # Title — uppercase, scaled to fit zone
    t_font, t_lines, t_lh = fit_text_to_zone(
        draw, story["title"].upper(), text_w,
        zone_height=title_h, size_start=72, step=6)
    draw_zone(draw, t_lines, t_font, t_lh, cx, title_top, title_h, text_color)

    # Divider line between zones
    div_y = title_top + title_h + gap // 2
    draw.line([(cx - 60, div_y), (cx + 60, div_y)], fill=(*muted, 160), width=2)

    # Summary — sentence case, scaled to fit zone
    s_font, s_lines, s_lh = fit_text_to_zone(
        draw, story["summary"], text_w,
        zone_height=summ_h, size_start=42, step=4)
    draw_zone(draw, s_lines, s_font, s_lh, cx, summ_top, summ_h, text_color)

    # Progress counter (e.g. "1 / 3")
    counter      = f"{index + 1} / {total}"
    counter_bbox = draw.textbbox((0, 0), counter, font=get_font(30))
    cw           = counter_bbox[2] - counter_bbox[0]
    draw.text((cx - cw // 2, counter_y), counter, font=get_font(30), fill=muted)

    # ── Save ──────────────────────────────────────────────────────────────────
    canvas.save(output_path, "JPEG", quality=95)
    print(f"  ✓ {output_path.name}")


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


def cleanup_github_pages(date: str) -> None:
    """Remove images from GitHub Pages (always do this)."""
    git("add", str(IG_IMG_DIR))
    git("commit", "-m", f"temp: remove instagram images {date}")
    git("push", "origin", "main")
    print("  Cleaned up images from GitHub Pages")


def delete_local_images(paths: list[Path]) -> None:
    """Delete local image files (only if not KEEP_IMAGES)."""
    for p in paths:
        p.unlink(missing_ok=True)
    print("  Deleted local image files")


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


def wait_for_media_ready(media_id: str, timeout: int = 300) -> None:
    """Instagram needs time to process uploaded images before carousel assembly."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(
                f"{IG_API}/{media_id}",
                params={"fields": "status_code", "access_token": IG_TOKEN},
                timeout=10,
            )
            data = r.json()
            status = data.get("status_code", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram media {media_id} failed processing: {data}")
        except Exception as e:
            # Status endpoint might not be immediately available; keep polling
            pass
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
        print(f"    Media ID: {media_id}, waiting for processing…")
        wait_for_media_ready(media_id)
        child_ids.append(media_id)
        time.sleep(10)

    # Give Instagram significant time to finalize all media before carousel assembly
    print("  Finalizing media …")
    time.sleep(15)

    print("  Assembling carousel …")
    # Retry carousel assembly if it fails (media might still be processing)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            carousel = ig_post(f"{IG_BIZ_ID}/media", {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
            })
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    Carousel assembly failed (attempt {attempt + 1}/{max_retries}), retrying in 10s…")
                time.sleep(10)
            else:
                raise

    # Wait for carousel to be ready for publishing
    print("  Preparing for publishing …")
    time.sleep(10)

    print("  Publishing …")
    # Retry publishing if it fails (carousel might still be processing)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            published = ig_post(f"{IG_BIZ_ID}/media_publish", {
                "creation_id": carousel["id"],
            })
            return published["id"]
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    Publishing failed (attempt {attempt + 1}/{max_retries}), retrying in 10s…")
                time.sleep(10)
            else:
                raise


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
        # Always clean up GitHub Pages
        print("\n🧹  Removing images from GitHub Pages …")
        cleanup_github_pages(date)

        # Only delete local images if KEEP_IMAGES is not set
        if not KEEP_IMAGES:
            delete_local_images(img_paths)
        else:
            print("  Keeping local images in ig/ folder (KEEP_IMAGES=1)")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
