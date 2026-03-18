#!/usr/bin/env python3
"""
Generate data/weekly_news.json from RSS feeds (main world news of the last 7 days).
Run periodically (e.g. weekly): python utils/generate_weekly_news.py

Uses only the standard library (no pip install). Output is written to
data/weekly_news.json; the main app loads it in the "Main news of the week" section.

Optional: put extra entries in data/weekly_news_manual.json (same array format);
they are merged into the output. Useful if RSS fails (e.g. SSL on some systems).
"""

import json
import os
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple


# RSS feed URL -> display name
FEEDS = {
    "https://feeds.bbci.co.uk/news/world/rss.xml": "BBC News",
    "https://feeds.reuters.com/reuters/worldNews": "Reuters",
}

USER_AGENT = "EscalationWeeklyNews/1.0 (compatible; Python)"
DAYS_BACK = 7
MAX_ITEMS = 30


def parse_rfc2822(s: str) -> Optional[datetime]:
    """Parse RFC 2822 date (e.g. 'Mon, 16 Mar 2026 12:00:00 GMT')."""
    if not s or not s.strip():
        return None
    s = s.strip()
    # Replace trailing GMT/UTC with +0000 for %z
    s = re.sub(r"\s+GMT\s*$", " +0000", s, flags=re.I)
    s = re.sub(r"\s+UTC\s*$", " +0000", s, flags=re.I)
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S +0000",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            if fmt.endswith("Z"):
                return datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _make_ssl_context() -> ssl.SSLContext:
    """Use default context; if SSL verification is broken (e.g. macOS), allow skip via env."""
    if os.environ.get("ESCALATION_INSECURE_SSL") == "1":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def fetch_feed(url: str, source_name: str) -> Tuple[List[dict], Optional[str]]:
    items = []
    err = None
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15, context=_make_ssl_context()) as resp:
            tree = ET.parse(resp)
    except Exception as e:
        err = str(e)
        # Retry once without SSL verification (e.g. macOS with missing certs)
        if "CERTIFICATE" in err.upper() or "SSL" in err.upper():
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                    tree = ET.parse(resp)
                err = None
            except Exception as e2:
                err = str(e2)
        if err:
            return items, err
    root = tree.getroot()
    # RSS 2.0: <rss><channel><item>... (namespace can make tag {ns}channel)
    channel = root.find("channel")
    if channel is None:
        # Some feeds use default namespace
        for child in root:
            if child.tag.endswith("channel") or child.tag == "channel":
                channel = child
                break
        if channel is None:
            channel = root
    for item in channel.findall("item"):
        # Handle namespaced tags: {http://...}title -> take text
        def text_of(el):
            if el is None:
                return ""
            return (el.text or "").strip()

        title_el = item.find("title") or next((c for c in item if (c.tag or "").endswith("title")), None)
        link_el = item.find("link") or next((c for c in item if (c.tag or "").endswith("link")), None)
        pub_el = (
            item.find("pubDate") or item.find("published")
            or item.find("{http://purl.org/dc/elements/1.1/}date")
            or next((c for c in item if "date" in (c.tag or "") or "pub" in (c.tag or "").lower()), None)
        )
        title = text_of(title_el)
        link = text_of(link_el)
        if not title and not link:
            continue
        pub_dt = None
        if pub_el is not None and (pub_el.text or "").strip():
            pub_dt = parse_rfc2822((pub_el.text or "").strip())
        items.append({
            "title": title or "Untitled",
            "url": link or "#",
            "source": source_name,
            "date": pub_dt.strftime("%Y-%m-%d") if pub_dt else "",
            "_dt": pub_dt,
        })
    return items, None


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "weekly_news.json"

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    all_items = []  # type: List[dict]
    fetch_errors = []  # type: List[str]

    for url, source_name in FEEDS.items():
        items_from_feed, fetch_err = fetch_feed(url, source_name)
        if fetch_err:
            fetch_errors.append(f"{source_name}: {fetch_err}")
        for row in items_from_feed:
            dt = row.pop("_dt", None)
            if dt is not None and dt < cutoff:
                continue
            all_items.append(row)

    # Optional: merge manually curated items (e.g. if RSS fails due to SSL/network)
    manual_path = data_dir / "weekly_news_manual.json"
    if manual_path.exists():
        try:
            with open(manual_path, encoding="utf-8") as f:
                manual = json.load(f)
            if isinstance(manual, list):
                for item in manual:
                    if isinstance(item, dict) and (item.get("title") or item.get("url")):
                        item = {k: v for k, v in item.items() if k != "_dt"}
                        all_items.append(item)
        except (json.JSONDecodeError, OSError):
            pass

    # Sort by date descending (most recent first); items without date go last
    def sort_key(x):
        d = x.get("date") or ""
        return (0 if d else 1, d)

    all_items.sort(key=sort_key, reverse=True)

    # Normalise: ensure each item has title, url, source, date (no _dt)
    for item in all_items:
        item.pop("_dt", None)
        item.setdefault("title", "")
        item.setdefault("url", "")
        item.setdefault("source", "")
        item.setdefault("date", "")

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for item in all_items:
        u = (item.get("url") or "").strip()
        if u and u != "#" and u not in seen_urls:
            seen_urls.add(u)
            unique.append(item)

    result = unique[:MAX_ITEMS]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(result)} items to {out_path}")
    if len(result) == 0 and fetch_errors:
        print("RSS fetch failed (e.g. SSL certificate issue on this system):", file=sys.stderr)
        for msg in fetch_errors:
            print(f"  {msg}", file=sys.stderr)
        print("You can: add entries to data/weekly_news_manual.json and run this script again, or fix SSL (e.g. run 'Install Certificates.command' for Python on macOS).", file=sys.stderr)


if __name__ == "__main__":
    main()
