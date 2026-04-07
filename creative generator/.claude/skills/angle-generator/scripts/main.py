#!/usr/bin/env python3
"""Angle Generator — Prepares review + winner data for Claude to generate Ad Angles."""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))


def load_brand():
    """Load brand.json."""
    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    if not os.path.exists(brand_path):
        print("Error: brand.json not found.")
        sys.exit(1)
    with open(brand_path) as f:
        return json.load(f)


def load_reviews():
    """Load scraped reviews."""
    raw_path = os.path.join(PROJECT_ROOT, "reviews", "reviews_raw.json")
    if not os.path.exists(raw_path):
        print("Error: reviews/reviews_raw.json not found. Run review-scraper first.")
        sys.exit(1)
    with open(raw_path) as f:
        return json.load(f)


def load_winners():
    """Load winner ad analysis."""
    path = os.path.join(PROJECT_ROOT, "winners", "ads_analyzed.json")
    if not os.path.exists(path):
        print("Warning: winners/ads_analyzed.json not found. Proceeding without winner data.")
        return []
    with open(path) as f:
        return json.load(f)


def prepare_summary(brand, reviews, winners):
    """Prepare a structured summary for Claude to analyze."""
    negative = [r for r in reviews if r["rating"] <= 2]
    positive = [r for r in reviews if r["rating"] >= 4]
    neutral = [r for r in reviews if r["rating"] == 3]

    # Sort by rating (worst first for negative, best first for positive)
    negative.sort(key=lambda r: r["rating"])
    positive.sort(key=lambda r: -r["rating"])

    def format_reviews(review_list, max_count=40):
        formatted = []
        for r in review_list[:max_count]:
            text = (r.get("text") or r.get("comments") or "").strip()
            title = (r.get("title") or "").strip()
            if text or title:
                entry = f"[{r['rating']}★]"
                if title:
                    entry += f" {title}:"
                entry += f" {text[:400]}"
                formatted.append(entry)
        return "\n".join(formatted)

    # Winner ads summary (static ads only)
    static_winners = [w for w in winners if w.get("display_format") in ("IMAGE", "DCO")]
    static_winners.sort(key=lambda w: -w.get("winner_score", 0))
    winner_lines = []
    for w in static_winners[:15]:
        body = w.get("body_text", "")[:250]
        title = w.get("title", "")[:100]
        score = w.get("winner_score", 0)
        fmt = w.get("display_format", "")
        winner_lines.append(f"[Score: {score}, {fmt}] {title} — {body}")

    summary = {
        "brand": {
            "name": brand.get("name", ""),
            "category": brand.get("category", ""),
            "shop_url": brand.get("shop_url", ""),
            "target_market": brand.get("target_market", ""),
        },
        "review_stats": {
            "total": len(reviews),
            "negative": len(negative),
            "neutral": len(neutral),
            "positive": len(positive),
        },
        "negative_reviews": format_reviews(negative),
        "positive_reviews": format_reviews(positive),
        "neutral_reviews": format_reviews(neutral),
        "winner_ads": "\n".join(winner_lines),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="Angle Generator — Data Preparation")
    parser.add_argument("--output-dir", default="angles", help="Output directory")
    parser.add_argument("--summary-only", action="store_true", help="Only output the summary, don't create angles.json")
    args = parser.parse_args()

    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Load all data
    print("Loading brand data...")
    brand = load_brand()
    print(f"  Brand: {brand.get('name', '')}")

    print("Loading reviews...")
    reviews = load_reviews()
    print(f"  {len(reviews)} reviews loaded")

    print("Loading winner ads...")
    winners = load_winners()
    print(f"  {len(winners)} winner ads loaded")

    # Prepare summary
    summary = prepare_summary(brand, reviews, winners)

    # Save summary for reference
    summary_path = os.path.join(output_dir, "review_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSaved review summary: {summary_path}")

    # Print summary to stdout for Claude to read
    print(f"\n{'='*60}")
    print(f"BRAND: {summary['brand']['name']} ({summary['brand']['category']})")
    print(f"REVIEWS: {summary['review_stats']['total']} total "
          f"({summary['review_stats']['negative']} negative, "
          f"{summary['review_stats']['neutral']} neutral, "
          f"{summary['review_stats']['positive']} positive)")
    print(f"WINNER ADS: {len(winners)} static ads analyzed")
    print(f"{'='*60}")

    print(f"\n--- NEGATIVE REVIEWS ({summary['review_stats']['negative']}) ---")
    print(summary["negative_reviews"][:3000])

    print(f"\n--- POSITIVE REVIEWS ({summary['review_stats']['positive']}) ---")
    print(summary["positive_reviews"][:3000])

    print(f"\n--- NEUTRAL REVIEWS ({summary['review_stats']['neutral']}) ---")
    print(summary["neutral_reviews"][:1500])

    print(f"\n--- TOP WINNER ADS ---")
    print(summary["winner_ads"][:2000])

    print(f"\n{'='*60}")
    print("Data preparation complete.")
    print(f"Claude should now analyze this data and generate: {output_dir}/angles.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
