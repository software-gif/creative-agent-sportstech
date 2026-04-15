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
        "text": f"""You are a STRICT quality inspector reviewing an AI-generated lifestyle photograph for a paid Meta ad campaign. Anything less than photographically believable gets rejected. You are NOT grading on a curve — if you notice any issue, lower the score accordingly.

[Image 1 to {n_refs}] = REFERENCE product images (ground truth — how the product should look)
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

EVALUATE THE GENERATED IMAGE AGAINST THESE CRITERIA. Be strict — if anything looks even slightly off, drop the score. A passing image (8+) must be fully believable as a real photograph.

HARD FAILURES — any of these means overall = 0, pass = false, regardless of other criteria:
- PERSON IS NOT PHYSICALLY USING THE EQUIPMENT. Feet must be ON the walking/running surface, hands must be ON the handles of a bike/rower/crosstrainer, body must be ON the vibration plate. If the person is standing next to, behind, or in front of the equipment instead of on it, this is an automatic overall = 0 and pass = false. The same applies if the person's feet are on the floor next to the walking pad while they use a laptop at a standing desk — that is not usage, that is the product being decorative.
- The wrong product is shown (e.g. a tall treadmill with handrails when the brief says flat walking pad).
- The product is grossly distorted (bent, melted, floating, double-sized).

If none of the hard failures apply, continue scoring:

1. PRODUCT ACCURACY (0-10)
   - Does the product match the reference images EXACTLY? Shape, colors, display panel position/size, handlebars, buttons, LEDs, branding.
   - Proportions of the product vs. the user (e.g. is the walking surface the right width for two feet?).
   - Wood/material finish matches reference intensity.
   - Side panel and end-cap details (roller mounts, small visible holes/screws, front console) must be consistent with references — Gemini tends to smooth these away, penalize when they are absent or wrong.

2. POSE & USAGE CORRECTNESS (0-10) — MOST IMPORTANT
   - Is the person using the equipment the way a real user would? Shoes on equipment that demands shoes (treadmills, walking pads, crosstrainers)? Hands gripping where they should grip?
   - Body mechanics: weight distribution makes sense, joints bend naturally, stance matches the activity.
   - Facing direction consistent with the product's display/console orientation.
   - Person's weight is clearly on the equipment, not on the surrounding floor.
   - If the user is barefoot on a walking pad, treadmill, or crosstrainer → score max 5.
   - Awkward, stiff, or unnatural posture → score max 6.

3. SCENE GEOMETRY & PERSPECTIVE (0-10)
   - Do all objects (desks, monitors, chairs, shelves, plants, windows) sit on consistent floor and wall planes? Nothing should be rotated or tilted relative to its expected orientation.
   - A computer monitor should face the user squarely. A desk should be parallel to the wall or at a deliberate consistent angle. If a monitor, desk, shelf, or any object looks twisted/tilted/floating compared to the rest of the scene → score max 5.
   - Perspective lines of furniture should be internally consistent — no M.C. Escher effects.

4. TECHNICAL QUALITY (0-10)
   - Extra or missing fingers, limbs, distorted faces, warped text.
   - Lighting consistency: shadows go the right direction, light sources are plausible.
   - Composition looks like a professional photograph, not a render.

5. OVERALL SCORE (0-10)
   - This is your final verdict: would you ship this image in a paid ad without retouching?
   - 9-10: ship as-is, no issues
   - 8: ship-worthy, 1 minor nitpick
   - 7: usable only for testing, visible issue
   - 6 or below: reject, retry

List EVERY issue you notice, even minor ones. An image with zero issues is rare — be honest. "pass" = overall >= 7."""
    })

    try:
        resp = requests.post(TEXT_ENDPOINT, json={
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4000,
                # Gemini 2.5 Flash thinking tokens count against the cap and
                # were truncating the JSON response mid-string. QC is a
                # structured evaluation — no chain-of-thought needed.
                "thinkingConfig": {"thinkingBudget": 0},
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "product_accuracy": {"type": "integer"},
                        "pose_correctness": {"type": "integer"},
                        "technical_quality": {"type": "integer"},
                        "overall": {"type": "integer"},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "pass": {"type": "boolean"},
                    },
                    "required": ["product_accuracy", "pose_correctness", "technical_quality", "overall", "issues", "pass"],
                },
            },
        }, timeout=60)
        resp.raise_for_status()
        text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return json.loads(text)

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


def delete_creative(creative):
    """Delete a creative from both storage and the database.

    Used by --delete-on-fail so auto-QC can prune bad images before
    they reach the board, instead of leaving the agent to decide.
    """
    headers = get_supabase_headers()
    storage_path = creative.get("storage_path")
    if storage_path:
        try:
            requests.delete(
                f"{SUPABASE_URL}/storage/v1/object/creatives/{storage_path}",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}"},
                timeout=15,
            )
        except Exception as e:
            print(f"  WARN: storage delete failed: {e}")
    try:
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/creatives?id=eq.{creative['id']}",
            headers=headers,
            timeout=15,
        )
    except Exception as e:
        print(f"  WARN: db delete failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Quality Control Agent")
    parser.add_argument("--creative", default=None, help="Creative short_id (e.g. CR-0015)")
    parser.add_argument("--creative-id", default=None, help="Creative UUID (alternative to --creative)")
    parser.add_argument("--review-all", action="store_true", help="Review all unreviewed creatives")
    parser.add_argument("--batch", default=None, help="Review all creatives in a batch")
    parser.add_argument("--delete-on-fail", action="store_true", help="Delete creatives that score below threshold")
    parser.add_argument("--threshold", type=int, default=7, help="Pass threshold for overall score (default 7)")
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
    elif args.creative_id:
        cr = get_creative(creative_id=args.creative_id)
        if cr:
            creatives = [cr]
        else:
            sys.exit(f"Creative {args.creative_id} not found")
    elif args.review_all:
        creatives = get_unreviewed_creatives()
        print(f"  Found {len(creatives)} unreviewed creatives")
    elif args.batch:
        creatives = get_batch_creatives(args.batch)
        print(f"  Found {len(creatives)} creatives in batch")
    else:
        sys.exit("Provide --creative, --creative-id, --review-all, or --batch")

    passed = 0
    failed = 0

    for creative in creatives:
        review = review_creative(creative)
        if not review:
            continue

        short_id = creative.get("short_id", creative["id"][:8])
        overall = review.get("overall", 0)
        is_pass = overall >= args.threshold
        issues = review.get("issues", [])

        # Print result
        status = "PASS" if is_pass else "FAIL"
        color = "\033[92m" if is_pass else "\033[91m"
        reset = "\033[0m"

        print(f"  {color}{status}{reset} {short_id}: {overall}/10")
        print(f"    Product: {review.get('product_accuracy', '?')}/10 | Pose: {review.get('pose_correctness', '?')}/10 | Quality: {review.get('technical_quality', '?')}/10")
        if issues:
            for issue in issues:
                print(f"    - {issue}")

        notes = "; ".join(issues) if issues else "No issues found"
        if is_pass or not args.delete_on_fail:
            update_creative_rating(creative["id"], overall, notes)
        else:
            print(f"  DELETING {short_id} (score {overall} < threshold {args.threshold})")
            delete_creative(creative)

        if is_pass:
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(creatives)}")
    print(f"{'=' * 60}")

    # Non-zero exit when any creative failed — lets key-visual's auto-qc
    # subprocess distinguish pass from fail by return code alone.
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
