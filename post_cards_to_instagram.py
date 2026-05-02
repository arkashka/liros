#!/usr/bin/env python3
"""
post_cards_to_instagram.py

Posts pre-generated carousel images from the ig/ folder to Instagram.
Finds all carousel*.{jpg,jpeg,png} images, uploads them, and assembles them into a carousel.

Setup
-----
Export these env vars (or put them in a .env file and source it):
  IG_ACCESS_TOKEN   — long-lived Instagram Graph API token (60-day expiry)
  IG_BUSINESS_ID    — Instagram Business Account ID
  CAPTION           — (optional) carousel caption, defaults to "#Hapi"

Usage
-----
  python3 post_cards_to_instagram.py                    # uses default caption
  python3 post_cards_to_instagram.py "Custom caption"   # custom caption
"""

import os, sys, time, requests, subprocess
from pathlib import Path
from requests.exceptions import HTTPError

# ── Config ────────────────────────────────────────────────────────────────────
BASE          = Path("/Users/areznik/Documents/Claude/Projects/LiRoS")
SITE          = "https://arkashka.github.io/liros"
IG_IMG_SUBDIR = "ig"
IG_IMG_DIR    = BASE / IG_IMG_SUBDIR

IG_TOKEN      = os.environ.get("IG_ACCESS_TOKEN", "")
IG_BIZ_ID     = os.environ.get("IG_BUSINESS_ID", "")
CAPTION       = os.environ.get("CAPTION", "#Hapi")

IG_API        = "https://graph.facebook.com/v20.0"


# ── GitHub Pages hosting ──────────────────────────────────────────────────────
def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(BASE), *args], check=True,
                   capture_output=True, text=True)


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
    except HTTPError:
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
    caption = sys.argv[1] if len(sys.argv) > 1 else CAPTION

    if not IG_TOKEN or not IG_BIZ_ID:
        sys.exit(
            "Error: IG_ACCESS_TOKEN and IG_BUSINESS_ID must be set.\n"
            "  export IG_ACCESS_TOKEN='your_token'\n"
            "  export IG_BUSINESS_ID='your_business_id'"
        )

    # Find carousel images (jpg, jpeg, png)
    img_files = sorted(
        list(IG_IMG_DIR.glob("carousel*.jpg")) +
        list(IG_IMG_DIR.glob("carousel*.jpeg")) +
        list(IG_IMG_DIR.glob("carousel*.png"))
    )
    if not img_files:
        sys.exit(f"No carousel*.jpg images found in {IG_IMG_DIR}")

    print(f"\n📸  Posting {len(img_files)} carousel images to Instagram\n")

    # Ensure images are committed and pushed
    print("🌐  Ensuring images are on GitHub Pages …")
    git("add", *[str(p) for p in img_files])
    git("commit", "-m", f"temp: carousel images for posting")
    git("push", "origin", "main")
    print("  Pushed to GitHub Pages")

    try:
        # Wait for GitHub Pages to propagate
        image_urls = [f"{SITE}/{IG_IMG_SUBDIR}/{p.name}" for p in img_files]
        print()
        for url in image_urls:
            wait_for_url(url)

        # Post carousel
        print("\n📲  Posting to Instagram …")
        post_id = post_carousel(image_urls, caption)
        print(f"\n✅  Posted! Instagram media ID: {post_id}")

    finally:
        # Always clean up, even if posting failed
        print("\n🧹  Removing images from GitHub Pages …")
        for p in img_files:
            p.unlink(missing_ok=True)
        git("add", str(IG_IMG_DIR))
        git("commit", "-m", f"temp: remove carousel images")
        git("push", "origin", "main")
        print("  Cleaned up images from GitHub Pages")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
