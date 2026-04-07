#!/usr/bin/env python3
"""Ad Library Scraper — Scraped Facebook Ad Library via Apify, berechnet Winner Score.
Downloads all static ad images locally (original quality) to avoid Meta CDN expiry."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip3 install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' not installed. Run: pip3 install python-dotenv")
    sys.exit(1)


# Find project root (where brand.json lives)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

APIFY_ACTOR = "curious_coder~facebook-ads-library-scraper"
APIFY_BASE_URL = "https://api.apify.com/v2"


def load_config():
    """Load .env and brand.json."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    api_key = os.getenv("APIFY_API_KEY")
    if not api_key:
        print("Error: APIFY_API_KEY not found in .env")
        sys.exit(1)

    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    if not os.path.exists(brand_path):
        print(f"Error: brand.json not found at {brand_path}")
        sys.exit(1)

    with open(brand_path) as f:
        brand = json.load(f)

    return api_key, brand


def scrape_ads(api_key, page_id, max_ads=0):
    """Call Apify actor to scrape Facebook Ad Library (active + inactive).
    Uses async run + polling to avoid HTTP timeouts."""
    import time

    ad_library_url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country=DE"
        f"&is_targeted_country=false&media_type=all"
        f"&search_type=page&sort_data[direction]=desc"
        f"&sort_data[mode]=total_impressions"
        f"&view_all_page_id={page_id}"
    )

    payload = {
        "urls": [{"url": ad_library_url}],
    }
    if max_ads > 0:
        payload["maxAds"] = max_ads

    print(f"Scraping ALL ads for page {page_id} (all formats, sorted by impressions)...")
    print(f"Max ads: {'all' if max_ads == 0 else max_ads}")

    # 1. Start async run
    run_url = f"{APIFY_BASE_URL}/acts/{APIFY_ACTOR}/runs"
    run_resp = requests.post(
        run_url,
        params={"token": api_key},
        json=payload,
        timeout=30,
    )
    run_resp.raise_for_status()
    run_data = run_resp.json()["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]
    print(f"Started Apify run: {run_id}")

    # 2. Poll until finished
    status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    while True:
        time.sleep(5)
        status_resp = requests.get(status_url, params={"token": api_key}, timeout=15)
        status_resp.raise_for_status()
        status = status_resp.json()["data"]["status"]
        print(f"  Status: {status}")
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if status != "SUCCEEDED":
        print(f"Error: Apify run ended with status {status}")
        sys.exit(1)

    # 3. Fetch results from dataset
    items_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
    items_resp = requests.get(items_url, params={"token": api_key}, timeout=120)
    items_resp.raise_for_status()

    ads = items_resp.json()
    print(f"Scraped {len(ads)} ads.")
    return ads


def download_static_images(ads, output_dir):
    """Download original quality images from all static ads (IMAGE + DCO formats)."""
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0
    local_paths = {}  # ad_archive_id -> [local_paths]

    for ad in ads:
        snapshot = ad.get("snapshot", {})
        display_format = snapshot.get("display_format", "")

        if display_format not in ("IMAGE", "DCO"):
            continue

        ad_id = ad.get("ad_archive_id", "unknown")
        ad_paths = []

        # Collect all image URLs: from images[] (IMAGE format) and cards[] (DCO format)
        image_urls = []
        for img in snapshot.get("images", []):
            url = img.get("original_image_url", "")
            if url:
                image_urls.append(url)
        for card in snapshot.get("cards", []):
            url = card.get("original_image_url", "")
            if url:
                image_urls.append(url)

        for idx, url in enumerate(image_urls):
            filename = f"{ad_id}_{idx}.jpg" if len(image_urls) > 1 else f"{ad_id}.jpg"
            filepath = os.path.join(assets_dir, filename)

            if os.path.exists(filepath):
                ad_paths.append(filepath)
                skipped += 1
                continue

            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(r.content)
                ad_paths.append(filepath)
                downloaded += 1
            except Exception as e:
                print(f"  Failed to download {ad_id}_{idx}: {e}")
                failed += 1

        if ad_paths:
            local_paths[ad_id] = ad_paths

    print(f"Static ad images: {downloaded} downloaded, {skipped} already existed, {failed} failed")
    return local_paths


def calculate_winner_score(ad):
    """Calculate a winner score based on available signals.

    Signals used:
    - active_days: How long the ad has been running (longer = better performance)
    - is_active: Currently active ads score higher
    - collation_count: Number of variations (more = scaling)
    - publisher_platform: Multi-platform = higher reach
    """
    score = 0

    # Active days (strongest signal — ads that run long are profitable)
    start_str = ad.get("start_date_formatted", "")
    if start_str:
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            active_days = (datetime.now() - start).days
            score += min(active_days, 365)
        except ValueError:
            pass

    # Currently active bonus
    if ad.get("is_active"):
        score += 50

    # Collation count (multiple variations = brand is scaling this ad)
    collation = ad.get("collation_count") or 1
    score += min(collation * 10, 100)

    # Multi-platform bonus
    platforms = ad.get("publisher_platform", [])
    score += len(platforms) * 5

    return score


def analyze_ads(ads, local_paths):
    """Analyze ads and calculate winner scores."""
    analyzed = []
    for ad in ads:
        snapshot = ad.get("snapshot", {})
        display_format = snapshot.get("display_format", "UNKNOWN")
        body_text = snapshot.get("body", {}).get("text", "") if isinstance(snapshot.get("body"), dict) else ""
        cta_text = snapshot.get("cta_text", "")
        images = snapshot.get("images", [])
        videos = snapshot.get("videos", [])
        ad_id = ad.get("ad_archive_id", "")

        analyzed.append({
            "ad_archive_id": ad_id,
            "ad_library_url": ad.get("ad_library_url", ""),
            "page_name": ad.get("page_name", snapshot.get("page_name", "")),
            "is_active": ad.get("is_active", False),
            "start_date": ad.get("start_date_formatted", ""),
            "end_date": ad.get("end_date_formatted", ""),
            "display_format": display_format,
            "body_text": body_text[:500],
            "cta_text": cta_text,
            "link_url": snapshot.get("link_url", ""),
            "title": snapshot.get("title", ""),
            "link_description": snapshot.get("link_description", ""),
            "collation_count": ad.get("collation_count", 1),
            "publisher_platforms": ad.get("publisher_platform", []),
            "image_urls": [img.get("original_image_url", "") for img in images],
            "video_urls": [vid.get("video_hd_url", "") or vid.get("video_sd_url", "") for vid in videos],
            "local_image_paths": local_paths.get(ad_id, []),
            "winner_score": calculate_winner_score(ad),
        })

    # Sort by winner score descending
    analyzed.sort(key=lambda x: x["winner_score"], reverse=True)
    return analyzed


def generate_summary(analyzed):
    """Generate summary statistics."""
    total = len(analyzed)
    active = sum(1 for a in analyzed if a["is_active"])
    static_count = sum(1 for a in analyzed if a["display_format"] in ("IMAGE", "DCO"))
    static_with_images = sum(1 for a in analyzed if a["local_image_paths"])

    # Format distribution
    formats = {}
    for a in analyzed:
        fmt = a["display_format"]
        formats[fmt] = formats.get(fmt, 0) + 1

    # Top 10 static winners (only IMAGE format)
    static_winners = [a for a in analyzed if a["display_format"] in ("IMAGE", "DCO")][:10]

    # Top 10 overall winners
    top_winners = analyzed[:10]

    return {
        "total_ads": total,
        "active_ads": active,
        "static_ads": static_count,
        "static_ads_with_local_images": static_with_images,
        "format_distribution": formats,
        "top_10_winners_overall": [
            {
                "ad_archive_id": w["ad_archive_id"],
                "ad_library_url": w["ad_library_url"],
                "display_format": w["display_format"],
                "winner_score": w["winner_score"],
                "body_text": w["body_text"][:200],
                "start_date": w["start_date"],
                "is_active": w["is_active"],
                "local_image_paths": w["local_image_paths"],
            }
            for w in top_winners
        ],
        "top_10_static_winners": [
            {
                "ad_archive_id": w["ad_archive_id"],
                "ad_library_url": w["ad_library_url"],
                "winner_score": w["winner_score"],
                "body_text": w["body_text"][:200],
                "start_date": w["start_date"],
                "is_active": w["is_active"],
                "local_image_paths": w["local_image_paths"],
            }
            for w in static_winners
        ],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Ad Library Scraper")
    parser.add_argument("--page-id", help="Facebook Page ID (default: from brand.json)")
    parser.add_argument("--max-ads", type=int, default=0, help="Max ads to scrape (0 = all)")
    parser.add_argument("--output-dir", default="winners", help="Output directory")
    args = parser.parse_args()

    api_key, brand = load_config()
    page_id = args.page_id or brand.get("facebook_page_id")
    if not page_id:
        print("Error: No page_id provided and none found in brand.json")
        sys.exit(1)

    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Scrape (active + inactive)
    ads_raw = scrape_ads(api_key, page_id, args.max_ads)

    # 2. Save raw data
    raw_path = os.path.join(output_dir, "ads_raw.json")
    with open(raw_path, "w") as f:
        json.dump(ads_raw, f, indent=2, ensure_ascii=False)
    print(f"Saved raw data: {raw_path}")

    # 3. Download static ad images (original quality)
    print("\nDownloading static ad images (original quality)...")
    local_paths = download_static_images(ads_raw, output_dir)

    # 4. Analyze
    analyzed = analyze_ads(ads_raw, local_paths)

    analyzed_path = os.path.join(output_dir, "ads_analyzed.json")
    with open(analyzed_path, "w") as f:
        json.dump(analyzed, f, indent=2, ensure_ascii=False)
    print(f"Saved analysis: {analyzed_path}")

    # 5. Summary
    summary = generate_summary(analyzed)

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved summary: {summary_path}")

    # 6. Print results
    print(f"\n{'='*60}")
    print(f"Ad Library Analysis")
    print(f"{'='*60}")
    print(f"Total Ads: {summary['total_ads']}")
    print(f"Active Ads: {summary['active_ads']}")
    print(f"Static Ads: {summary['static_ads']} ({summary['static_ads_with_local_images']} images saved)")
    print(f"Format Distribution: {json.dumps(summary['format_distribution'], indent=2)}")
    print(f"\nTop 5 Static Ad Winners:")
    for i, w in enumerate(summary["top_10_static_winners"][:5], 1):
        print(f"  {i}. Score: {w['winner_score']} | Active: {w['is_active']}")
        print(f"     {w['body_text'][:100]}...")
        print(f"     Images: {w['local_image_paths']}")
        print(f"     {w['ad_library_url']}")


if __name__ == "__main__":
    main()
