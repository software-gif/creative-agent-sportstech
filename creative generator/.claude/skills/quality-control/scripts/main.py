#!/usr/bin/env python3
"""Quality Control Agent — Auto-reviews generated creatives for product accuracy and pose correctness.

Usage:
    python3 .claude/skills/quality-control/scripts/main.py --creative CR-0015
    python3 .claude/skills/quality-control/scripts/main.py --review-all
    python3 .claude/skills/quality-control/scripts/main.py --batch <batch_id>
"""

import argparse
import base64
import json
import os
import sys

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

TEXT_MODEL = "gemini-2.5-flash"
TEXT_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}"


def get_supabase_headers():
    key = SUPABASE_ANON_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def get_creative(short_id=None, creative_id=None):
    headers = get_supabase_headers()
    if short_id:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/creatives?short_id=eq.{short_id}&select=*", headers=headers)
    else:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/creatives?id=eq.{creative_id}&select=*", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None


def get_unreviewed_creatives():
    headers = get_supabase_headers()
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/creatives?rating=is.null&status=eq.generated&select=*&order=created_at.desc&limit=20",
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def get_batch_creatives(batch_id):
    headers = get_supabase_headers()
    resp = requests.get(f"{SUPABASE_URL}/rest/v1/creatives?batch_id=eq.{batch_id}&select=*", headers=headers)
    resp.raise_for_status()
    return resp.json()


def download_image_b64(url):
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
    except Exception:
        pass
    return None


def get_product_refs(product_category):
    """Get 2-3 product reference images for comparison."""
    # Map category to handle
    category_to_handle = {
        "treadmill": "f37s-pro", "walking_pad": "woodpad-pro", "speedbike": "sbike",
        "ergometer": "x150", "crosstrainer": "scross", "rowing_machine": "aqua-elite",
        "power_station": "sgym-pro", "smith_machine": "sxm200", "vibration_plate": "svibe",
    }
    handle = category_to_handle.get(product_category, product_category)

    key = SUPABASE_ANON_KEY
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"prefix": f"products/{handle}/", "limit": 3},
    )
    if resp.status_code != 200:
        return []

    images = []
    for f in resp.json()[:3]:
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/products/{handle}/{f['name']}"
        b64 = download_image_b64(url)
        if b64:
            ext = f["name"].rsplit(".", 1)[-1].lower()
            images.append({"data": b64, "mime": f"image/{'png' if ext == 'png' else 'jpeg'}"})
    return images


def load_product_knowledge(product_category):
    category_to_handle = {
        "treadmill": "f37s-pro", "walking_pad": "woodpad-pro", "speedbike": "sbike",
        "ergometer": "x150", "crosstrainer": "scross", "rowing_machine": "aqua-elite",
        "power_station": "sgym-pro", "smith_machine": "sxm200", "vibration_plate": "svibe",
    }
    handle = category_to_handle.get(product_category, product_category)
    path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("products", {}).get(handle, {})


def review_creative(creative):
    """Send generated image + product refs to Gemini for quality review."""
    short_id = creative.get("short_id", creative["id"][:8])
    product_cat = creative.get("product_category", "")
    storage_path = creative.get("storage_path", "")

    print(f"\n  Reviewing {short_id} ({product_cat})...")

    # Download the generated image
    gen_url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{storage_path}"
    gen_b64 = download_image_b64(gen_url)
    if not gen_b64:
        print(f"  SKIP: Could not download generated image")
        return None

    # Get product reference images
    ref_images = get_product_refs(product_cat)

    # Get product knowledge
    pk = load_product_knowledge(product_cat)
    must_match = pk.get("ai_generation_rules", {}).get("must_match", [])
    must_avoid = pk.get("ai_generation_rules", {}).get("must_avoid", [])
    how_it_works = pk.get("how_it_works", {})

    # Build review prompt
    parts = []

    # Reference images first
    for img in ref_images:
        parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

    # Generated image
    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": gen_b64}})

    n_refs = len(ref_images)
    parts.append({
        "text": f"""You are a quality control inspector for AI-generated fitness lifestyle photographs.

[Image 1 to {n_refs}] = REFERENCE product images (ground truth — how the product SHOULD look)
[Image {n_refs + 1}] = GENERATED lifestyle image to review

Product: {pk.get('name', product_cat)}
Product rules that MUST be correct:
{chr(10).join('- ' + r for r in must_match)}

Things that MUST NOT happen:
{chr(10).join('- ' + r for r in must_avoid)}

How this product is used:
{how_it_works.get('principle', '')}
{how_it_works.get('position', '')}
{how_it_works.get('direction', '')}

REVIEW THE GENERATED IMAGE. Check:
1. PRODUCT ACCURACY (0-10): Does the product in the generated image match the reference images? Check: shape, colors, display position/size, handlebars, buttons, LEDs, branding text, proportions.
2. POSE CORRECTNESS (0-10): Is the person using the equipment correctly? Check: facing the right direction, feet in correct position, hands in right place, natural body mechanics.
3. TECHNICAL QUALITY (0-10): Professional photo quality? Check: no AI artifacts, no impossible geometry, realistic lighting, no distortions, no extra limbs/fingers.
4. OVERALL SCORE (0-10): Overall usability for commercial purposes.

Respond in this EXACT JSON format only:
{{"product_accuracy": 7, "pose_correctness": 8, "technical_quality": 9, "overall": 8, "issues": ["display has wrong shape", "LED strip missing on left side"], "pass": true}}

Set "pass" to true if overall >= 7, false otherwise. List ALL specific issues found. Be strict — this is for commercial use."""
    })

    try:
        resp = requests.post(TEXT_ENDPOINT, json={
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1500},
        }, timeout=60)
        resp.raise_for_status()
        text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        # Parse JSON from response — handle various formats
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        # Find JSON object in response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        review = json.loads(text)
        return review

    except json.JSONDecodeError:
        print(f"  Could not parse review response: {text[:200]}")
        return None
    except Exception as e:
        print(f"  Review error: {e}")
        return None


def update_creative_rating(creative_id, rating, notes):
    headers = get_supabase_headers()
    resp = requests.patch(
        f"{SUPABASE_URL}/rest/v1/creatives?id=eq.{creative_id}",
        headers=headers,
        json={"rating": rating, "notes": notes},
    )
    return resp.status_code in (200, 204)


def main():
    parser = argparse.ArgumentParser(description="Quality Control Agent")
    parser.add_argument("--creative", default=None, help="Creative short_id (e.g. CR-0015)")
    parser.add_argument("--review-all", action="store_true", help="Review all unreviewed creatives")
    parser.add_argument("--batch", default=None, help="Review all creatives in a batch")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")

    print("=" * 60)
    print("QUALITY CONTROL AGENT")
    print("=" * 60)

    creatives = []
    if args.creative:
        cr = get_creative(short_id=args.creative)
        if cr:
            creatives = [cr]
        else:
            sys.exit(f"Creative {args.creative} not found")
    elif args.review_all:
        creatives = get_unreviewed_creatives()
        print(f"  Found {len(creatives)} unreviewed creatives")
    elif args.batch:
        creatives = get_batch_creatives(args.batch)
        print(f"  Found {len(creatives)} creatives in batch")
    else:
        sys.exit("Provide --creative, --review-all, or --batch")

    passed = 0
    failed = 0

    for creative in creatives:
        review = review_creative(creative)
        if not review:
            continue

        short_id = creative.get("short_id", creative["id"][:8])
        overall = review.get("overall", 0)
        is_pass = review.get("pass", False)
        issues = review.get("issues", [])

        # Update in DB
        notes = "; ".join(issues) if issues else "No issues found"
        update_creative_rating(creative["id"], overall, notes)

        # Print result
        status = "PASS" if is_pass else "FAIL"
        color = "\033[92m" if is_pass else "\033[91m"
        reset = "\033[0m"

        print(f"  {color}{status}{reset} {short_id}: {overall}/10")
        print(f"    Product: {review.get('product_accuracy', '?')}/10 | Pose: {review.get('pose_correctness', '?')}/10 | Quality: {review.get('technical_quality', '?')}/10")
        if issues:
            for issue in issues:
                print(f"    - {issue}")

        if is_pass:
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(creatives)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
