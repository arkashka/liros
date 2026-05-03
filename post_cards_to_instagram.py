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
    result = subprocess.run(
        ["git", "-C", str(BASE), *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr,
        )


def git_commit_if_changes(message: str) -> bool:
    """Commit staged changes; return False (and don't fail) if nothing is staged."""
    result = subprocess.run(
        ["git", "-C", str(BASE), "diff", "--cached", "--quiet"],
    )
    if result.returncode == 0:
        print(f"  Nothing to commit ({message!r}) — skipping")
        return False
    git("commit", "-m", message)
    return True


def list_tracked_in_ig() -> list[str]:
    """Return repo-relative paths of files currently tracked under ig/ at HEAD."""
    result = subprocess.run(
        ["git", "-C", str(BASE), "ls-tree", "-r", "--name-only", "HEAD", "--", IG_IMG_SUBDIR],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def git_push(branch: str = "main") -> None:
    """Push to origin/<branch>; if rejected due to non-fast-forward, rebase and retry once."""
    try:
        git("push", "origin", branch)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "")
        if any(s in stderr for s in ("rejected", "fetch first", "non-fast-forward")):
            print("  Remote has new commits — rebasing local commit on top …")
            git("pull", "--rebase", "origin", branch)
            git("push", "origin", branch)
        else:
            raise


def clear_ig_on_github(keep=None) -> int:
    """git-rm every tracked file under ig/, optionally keeping certain filenames.
    Returns the number of files staged for deletion."""
    keep = keep or set()
    tracked = list_tracked_in_ig()
    stale = [t for t in tracked if Path(t).name not in keep]
    if stale:
        # --ignore-unmatch keeps us from failing if a path is already gone from the
        # working tree (we still want the deletion staged in the index).
        git("rm", "-f", "--ignore-unmatch", "--", *stale)
    return len(stale)


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

    # Find carousel images (case-insensitive, any format)
    # Look for files matching *arousel* (catches carousel/Carousel/CAROUSEL etc)
    all_files = list(IG_IMG_DIR.glob("*arousel*.jpg"))
    all_files += list(IG_IMG_DIR.glob("*arousel*.jpeg"))
    all_files += list(IG_IMG_DIR.glob("*arousel*.png"))
    all_files += list(IG_IMG_DIR.glob("*AROUSEL*.jpg"))
    all_files += list(IG_IMG_DIR.glob("*AROUSEL*.jpeg"))
    all_files += list(IG_IMG_DIR.glob("*AROUSEL*.png"))
    img_files = sorted(set(all_files))  # Remove duplicates and sort
    if not img_files:
        sys.exit(f"No carousel*.jpg images found in {IG_IMG_DIR}")

    print(f"\n📸  Posting {len(img_files)} carousel images to Instagram\n")

    # Ensure ig/ exists locally — it will be created on GitHub once we add files into it
    IG_IMG_DIR.mkdir(parents=True, exist_ok=True)

    # If ig/ on GitHub has anything that isn't part of this upload, wipe it first
    print("🌐  Preparing ig/ on GitHub …")
    new_filenames = {p.name for p in img_files}
    removed = clear_ig_on_github(keep=new_filenames)
    if removed:
        print(f"  Removed {removed} stale file(s) from ig/")

    # Stage the new carousel images
    git("add", *[str(p) for p in img_files])

    committed = git_commit_if_changes("temp: refresh ig/ for carousel posting")
    if committed:
        print("  New images committed — pushing to GitHub Pages …")
    else:
        print("  No new commit needed — pushing any unpushed local commits …")
    git_push("main")
    print("  Pushed to GitHub Pages ✓")

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
        # Remove images from GitHub and locally, but keep the ig/ folder via .gitkeep
        print("\n🧹  Removing carousel images from ig/ …")
        removed = clear_ig_on_github(keep={".gitkeep"})
        # Delete local image files
        if IG_IMG_DIR.exists():
            for p in IG_IMG_DIR.iterdir():
                if p.is_file() and p.name != ".gitkeep":
                    p.unlink(missing_ok=True)
        # Ensure ig/ exists locally and add .gitkeep so the empty folder persists on GitHub
        IG_IMG_DIR.mkdir(parents=True, exist_ok=True)
        gitkeep = IG_IMG_DIR / ".gitkeep"
        gitkeep.touch(exist_ok=True)
        git("add", "--", str(IG_IMG_DIR))
        if git_commit_if_changes("temp: remove carousel images"):
            git_push("main")
            print(f"  Removed {removed} image(s); ig/ folder kept on GitHub Pages")
        else:
            print("  Nothing to clean up")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
