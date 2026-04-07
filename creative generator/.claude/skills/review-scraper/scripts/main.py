#!/usr/bin/env python3
"""Review Scraper — Scraped Trustpilot Reviews via __NEXT_DATA__ extraction."""

import argparse
import json
import math
import os
import re
import sys
import time

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


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

REVIEWS_PER_PAGE = 20


def load_config():
    """Load brand.json."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    if not os.path.exists(brand_path):
        print(f"Error: brand.json not found at {brand_path}")
        sys.exit(1)

    with open(brand_path) as f:
        brand = json.load(f)

    return brand


def fetch_page(trustpilot_url, page):
    """Fetch a single page of reviews from Trustpilot."""
    # Ensure we use the German subdomain for 20 reviews per page
    url = trustpilot_url.rstrip("/")
    if "de.trustpilot.com" not in url:
        url = url.replace("www.trustpilot.com", "de.trustpilot.com")

    page_url = f"{url}?page={page}"

    resp = requests.get(page_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    html = resp.text
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None, None, 0

    data = json.loads(match.group(1))
    pp = data.get("props", {}).get("pageProps", {})

    business = pp.get("businessUnit", {})
    reviews = pp.get("reviews", [])

    return business, reviews, len(reviews)


def extract_review(raw):
    """Extract relevant fields from a raw review."""
    consumer = raw.get("consumer", {})
    dates = raw.get("dates", {})

    return {
        "rating": raw.get("rating"),
        "title": raw.get("headline", ""),
        "text": raw.get("text", ""),
        "author": consumer.get("displayName", ""),
        "date": dates.get("publishedDate", ""),
        "language": raw.get("language", ""),
        "is_verified": raw.get("isVerified", False),
    }


def generate_summary(reviews, business):
    """Generate review summary with rating distribution."""
    total = len(reviews)

    # Rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        rating = r.get("rating", 0)
        if rating in distribution:
            distribution[rating] += 1

    # Separate positive and negative
    negative = [r for r in reviews if r["rating"] <= 2]
    positive = [r for r in reviews if r["rating"] >= 4]
    neutral = [r for r in reviews if r["rating"] == 3]

    return {
        "business_name": business.get("displayName", ""),
        "trust_score": business.get("trustScore"),
        "stars": business.get("stars"),
        "total_reviews_on_platform": business.get("numberOfReviews"),
        "total_reviews_scraped": total,
        "rating_distribution": distribution,
        "negative_count": len(negative),
        "neutral_count": len(neutral),
        "positive_count": len(positive),
        "negative_reviews": negative,
        "positive_reviews": positive,
    }


def main():
    parser = argparse.ArgumentParser(description="Review Scraper")
    parser.add_argument("--trustpilot-url", help="Trustpilot URL (default: from brand.json)")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages (0 = all)")
    parser.add_argument("--output-dir", default="reviews", help="Output directory")
    args = parser.parse_args()

    brand = load_config()
    trustpilot_url = args.trustpilot_url or brand.get("trustpilot_url")
    if not trustpilot_url:
        print("Error: No trustpilot_url provided and none found in brand.json")
        sys.exit(1)

    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Fetch first page to get total count
    print(f"Scraping reviews from {trustpilot_url}...")
    business, first_reviews, count = fetch_page(trustpilot_url, 1)

    if not business:
        print("Error: Could not fetch reviews. Trustpilot may be blocking.")
        sys.exit(1)

    total_on_platform = business.get("numberOfReviews", 0)
    total_pages = math.ceil(total_on_platform / REVIEWS_PER_PAGE)

    if args.max_pages > 0:
        total_pages = min(total_pages, args.max_pages)

    print(f"Total reviews on Trustpilot: {total_on_platform}")
    print(f"Pages to scrape: {total_pages}")

    # 2. Collect all reviews
    all_reviews = [extract_review(r) for r in first_reviews]
    print(f"  Page 1: {len(first_reviews)} reviews")

    for page in range(2, total_pages + 1):
        time.sleep(2)  # Rate limiting
        _, reviews, count = fetch_page(trustpilot_url, page)
        if not reviews:
            print(f"  Page {page}: no data, stopping.")
            break
        all_reviews.extend([extract_review(r) for r in reviews])
        print(f"  Page {page}: {count} reviews (total: {len(all_reviews)})")

    # 3. Save raw reviews
    raw_path = os.path.join(output_dir, "reviews_raw.json")
    with open(raw_path, "w") as f:
        json.dump(all_reviews, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {raw_path}")

    # 4. Summary
    summary = generate_summary(all_reviews, business)

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved: {summary_path}")

    # 5. Print results
    dist = summary["rating_distribution"]
    print(f"\n{'='*60}")
    print(f"Review Scraper Summary — {summary['business_name']}")
    print(f"{'='*60}")
    print(f"Trust Score: {summary['trust_score']} | Stars: {summary['stars']}")
    print(f"Scraped: {summary['total_reviews_scraped']} / {summary['total_reviews_on_platform']}")
    print(f"\nRating Distribution:")
    for stars in [5, 4, 3, 2, 1]:
        bar = "█" * dist[stars]
        print(f"  {stars}★ {bar} {dist[stars]}")
    print(f"\nPositive (4-5★): {summary['positive_count']}")
    print(f"Neutral  (3★):   {summary['neutral_count']}")
    print(f"Negative (1-2★): {summary['negative_count']}")


if __name__ == "__main__":
    main()
