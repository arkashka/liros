#!/usr/bin/env python3
"""
LiRoS update_stories.py
Reads /tmp/liros_new_pull.json (compact format written by the scheduled task),
expands it into full pull objects, updates regions.json and topics.json,
and regenerates both RSS feeds.

Compact input format:
{
  "date": "YYYY-MM-DD",
  "stories": {
    "af-1": {"title": "...", "summary": "...", "source": "...", "url": "...", "date": "YYYY-MM-DD"},
    ...
  },
  "regions": {
    "Africa": ["af-1", "af-2", "af-3"],
    ...
  },
  "topics": {
    "Economy & Business": ["eb-1", "eb-2", "eb-3"],
    ...
  }
}

Stories shared between a region and a topic are written once in "stories"
and referenced by ID from both "regions" and "topics".
"""

import json, os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime

BASE = "/Users/areznik/Documents/Claude/Projects/LiRoS"
SITE = "https://arkashka.github.io/liros"
TMP  = "/tmp/liros_new_pull.json"

REGION_META = {
    "Africa":        {"emoji": "🌍", "color": "#FF6B35", "tagline": "A continent rising with energy and hope"},
    "Asia":          {"emoji": "🌏", "color": "#FFB700", "tagline": "Ancient wisdom, modern breakthroughs"},
    "Europe":        {"emoji": "🌍", "color": "#44BBA4", "tagline": "Green, resilient, and reaching for the future"},
    "North America": {"emoji": "🌎", "color": "#E94F8B", "tagline": "Bold dreams, bigger firsts"},
    "South America": {"emoji": "🌎", "color": "#3B82F6", "tagline": "Nature's guardian, culture's champion"},
    "Oceania":       {"emoji": "🌏", "color": "#10B981", "tagline": "Islands of partnership and discovery"},
    "Antarctica":    {"emoji": "🧊", "color": "#94A3B8", "tagline": "The frozen frontier of human knowledge"},
}

TOPIC_META = {
    "Economy & Business":    {"emoji": "📈", "color": "#FF6B35", "tagline": "Innovation and growth fueling global prosperity"},
    "Science & Technology":  {"emoji": "🚀", "color": "#FFB700", "tagline": "Pushing the boundaries of human ingenuity"},
    "Environment & Climate": {"emoji": "🌿", "color": "#44BBA4", "tagline": "Restoring the balance of our natural world"},
    "Health & Wellness":     {"emoji": "✨", "color": "#E94F8B", "tagline": "Nurturing the mind, body, and spirit"},
    "Society & Culture":     {"emoji": "🤝", "color": "#3B82F6", "tagline": "The vibrant threads of human connection"},
    "Entertainment & Arts":  {"emoji": "🎨", "color": "#10B981", "tagline": "Stories and visions that move the soul"},
    "Sports & Leisure":      {"emoji": "🏆", "color": "#94A3B8", "tagline": "The joy of movement and the spirit of play"},
    "Pets & Wildlife":       {"emoji": "🐾", "color": "#8B5CF6", "tagline": "Every creature, wild and close to home"},
}


def expand_pull(new_pull, bucket_key, meta_dict):
    """Expand compact pull into full pull object with metadata and story objects."""
    stories = new_pull["stories"]
    date    = new_pull["date"]
    bucket  = {}
    for name, ids in new_pull[bucket_key].items():
        meta = meta_dict.get(name, {})
        bucket[name] = {
            "emoji":   meta.get("emoji", ""),
            "color":   meta.get("color", "#888888"),
            "tagline": meta.get("tagline", ""),
            "stories": [stories[sid] for sid in ids if sid in stories],
        }
    return {"date": date, bucket_key: bucket}


def update_file(main_path, history_path, new_pull, max_pulls=3):
    """Prepend new_pull, keep max_pulls, archive overflow to history file."""
    data = json.load(open(main_path)) if os.path.exists(main_path) else {"pulls": []}
    data["pulls"].insert(0, new_pull)
    if len(data["pulls"]) > max_pulls:
        overflow = data["pulls"][max_pulls:]
        data["pulls"] = data["pulls"][:max_pulls]
        hist = json.load(open(history_path)) if os.path.exists(history_path) else {"pulls": []}
        hist["pulls"].extend(overflow)
        json.dump(hist, open(history_path, "w"), indent=2, ensure_ascii=False)
    json.dump(data, open(main_path, "w"), indent=2, ensure_ascii=False)
    return data


def rfc822(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")


def build_feed(title, description, self_url, items):
    rss = Element("rss", version="2.0", **{"xmlns:atom": "http://www.w3.org/2005/Atom"})
    ch  = SubElement(rss, "channel")
    SubElement(ch, "title").text         = title
    SubElement(ch, "link").text          = SITE
    SubElement(ch, "description").text   = description
    SubElement(ch, "language").text      = "en"
    SubElement(ch, "lastBuildDate").text = rfc822(items[0]["date"]) if items else ""
    atom = SubElement(ch, "atom:link")
    atom.set("href", self_url)
    atom.set("rel",  "self")
    atom.set("type", "application/rss+xml")
    for it in items:
        item = SubElement(ch, "item")
        SubElement(item, "title").text       = it["title"]
        SubElement(item, "link").text        = it["url"]
        SubElement(item, "guid", isPermaLink="true").text = it["url"]
        SubElement(item, "pubDate").text     = rfc822(it["date"])
        SubElement(item, "description").text = it["summary"]
        SubElement(item, "category").text    = it["category"]
    xml = minidom.parseString(tostring(rss, encoding="unicode")).toprettyxml(indent="  ")
    # Strip the extra XML declaration that toprettyxml prepends
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + "\n".join(xml.split("\n")[1:])


def main():
    if not os.path.exists(TMP):
        raise FileNotFoundError(f"Compact pull file not found: {TMP}")

    new_pull = json.load(open(TMP))
    date     = new_pull["date"]
    n_stories = len(new_pull["stories"])
    print(f"Loaded pull for {date} — {n_stories} unique stories")

    regions_pull = expand_pull(new_pull, "regions", REGION_META)
    topics_pull  = expand_pull(new_pull, "topics",  TOPIC_META)

    r_data = update_file(f"{BASE}/regions.json", f"{BASE}/regions_history.json", regions_pull)
    t_data = update_file(f"{BASE}/topics.json",  f"{BASE}/topics_history.json",  topics_pull)

    r_items = [
        {**s, "category": region, "date": s.get("date") or pull["date"]}
        for pull in r_data["pulls"]
        for region, data in pull["regions"].items()
        for s in data["stories"]
    ]
    t_items = [
        {**s, "category": topic, "date": s.get("date") or pull["date"]}
        for pull in t_data["pulls"]
        for topic, data in pull["topics"].items()
        for s in data["stories"]
    ]

    open(f"{BASE}/feed-regions.xml", "w").write(
        build_feed(
            "Hapi — Happy News by Region",
            "Uplifting stories from every corner of the world, organised by region.",
            f"{SITE}/feed-regions.xml",
            r_items,
        )
    )
    open(f"{BASE}/feed-topics.xml", "w").write(
        build_feed(
            "Hapi — Happy News by Topic",
            "Uplifting stories from around the world, organised by topic.",
            f"{SITE}/feed-topics.xml",
            t_items,
        )
    )

    print(f"Updated regions.json ({len(r_items)} RSS items) and topics.json ({len(t_items)} RSS items)")


if __name__ == "__main__":
    main()
