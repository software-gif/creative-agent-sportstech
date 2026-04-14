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


def resolve_product_handle(creative):
    """Figure out the real product handle for a creative.

    The DB `product_category` column is a coarse Shopware category
    (e.g. `power_station` is shared between sgym-pro AND hgx50), so
    using it alone ambiguates products. `prompt_json.product` is the
    exact handle passed to key-visual at generation time — that's the
    authoritative value. Fall back to the category-to-handle map for
    older creatives that don't have prompt_json yet.
    """
    prompt_json = creative.get("prompt_json") or {}
    handle = prompt_json.get("product")
    if handle:
        return handle
    category_to_handle = {
        "treadmill": "f37s-pro", "walking_pad": "woodpad-pro", "speedbike": "sbike",
        "ergometer": "x150", "crosstrainer": "scross", "rowing_machine": "aqua-elite",
        "power_station": "sgym-pro", "smith_machine": "sxm200", "vibration_plate": "svibe",
    }
    category = creative.get("product_category", "")
    return category_to_handle.get(category, category)


def _list_prefix(prefix, limit):
    key = SUPABASE_ANON_KEY
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"prefix": prefix, "limit": limit},
    )
    if resp.status_code != 200:
        return []
    return [f for f in resp.json() if f.get("name") and not f["name"].endswith("/")]


def _download_refs(files, prefix, limit=3):
    images = []
    for f in files[:limit]:
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{prefix}/{f['name']}"
        b64 = download_image_b64(url)
        if b64:
            ext = f["name"].rsplit(".", 1)[-1].lower()
            images.append({"data": b64, "mime": f"image/{'png' if ext == 'png' else 'jpeg'}"})
    return images


def get_product_refs(handle):
    """Get 2-3 transparent cutouts (the judge's product ground truth)."""
    files = _list_prefix(f"renders/{handle}/cutouts/", limit=10)
    if files:
        return _download_refs(files, f"renders/{handle}/cutouts", limit=3)
    # Fallback to Shopware thumbs for products without cutouts
    files = _list_prefix(f"products/{handle}/", limit=10)
    return _download_refs(files, f"products/{handle}", limit=3)


def get_lifestyle_refs(handle, limit=3):
    """Get real usage photos so the judge can verify pose, usage, branding
    placement, and subtle details that don't show up on clean cutouts."""
    files = _list_prefix(f"lifestyle/{handle}/", limit=20)
    if not files:
        return []
    # Prefer the first few — they're usually the canonical marketing shots
    return _download_refs(files, f"lifestyle/{handle}", limit=limit)


def load_product_knowledge(handle):
    path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("products", {}).get(handle, {})


def review_creative(creative):
    """Send generated image + product refs to Gemini for quality review."""
    short_id = creative.get("short_id", creative["id"][:8])
    storage_path = creative.get("storage_path", "")
    handle = resolve_product_handle(creative)

    print(f"\n  Reviewing {short_id} ({handle})...")

    # Download the generated image
    gen_url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{storage_path}"
    gen_b64 = download_image_b64(gen_url)
    if not gen_b64:
        print(f"  SKIP: Could not download generated image")
        return None

    # Get two kinds of ground truth: clean product cutouts (geometry,
    # colours, branding) and real usage photos (pose, logo placement,
    # details that clean cutouts smooth away).
    product_refs = get_product_refs(handle)
    lifestyle_refs = get_lifestyle_refs(handle, limit=3)

    # Get product knowledge
    pk = load_product_knowledge(handle)
    must_match = pk.get("ai_generation_rules", {}).get("must_match", [])
    must_avoid = pk.get("ai_generation_rules", {}).get("must_avoid", [])
    how_it_works = pk.get("how_it_works", {})

    # Build review prompt
    parts = []

    # Group 1: product cutouts
    for img in product_refs:
        parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

    # Group 2: lifestyle usage photos
    for img in lifestyle_refs:
        parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

    # Group 3: the generated image we're reviewing
    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": gen_b64}})

    n_product = len(product_refs)
    n_lifestyle = len(lifestyle_refs)
    n_refs = n_product + n_lifestyle

    # Slot labels for the prompt
    if n_product and n_lifestyle:
        product_slot = f"1-{n_product}"
        lifestyle_slot = f"{n_product+1}-{n_refs}"
        groups_desc = (
            f"[Images {product_slot}] = CLEAN PRODUCT REFERENCES — transparent cutouts showing "
            f"the product geometry, colours, branding, buttons, LEDs, and all details.\n"
            f"[Images {lifestyle_slot}] = REAL USAGE PHOTOS — real people using this product the "
            f"way it's meant to be used. Use these to verify: the pose, where the branding/logo "
            f"sits, the exact contact points, and any subtle details the clean cutouts don't show."
        )
    elif n_product:
        groups_desc = (
            f"[Images 1-{n_product}] = CLEAN PRODUCT REFERENCES — transparent cutouts showing "
            f"the product geometry, colours, branding, buttons, LEDs, and all details."
        )
    else:
        groups_desc = f"[Images 1-{n_refs}] = PRODUCT REFERENCES"

    parts.append({
        "text": f"""You are a STRICT quality inspector reviewing an AI-generated lifestyle photograph for a paid Meta ad campaign. Anything less than photographically believable gets rejected. You are NOT grading on a curve — if you notice any issue, lower the score accordingly.

{groups_desc}
[Image {n_refs + 1}] = GENERATED lifestyle image to review

Product: {pk.get('name', handle)}
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

- THE WRONG PRODUCT is shown (e.g. a tall treadmill with handrails when the brief says flat walking pad).

- ANATOMICAL IMPOSSIBILITY on the person: twisted or bent-the-wrong-way joints, legs rotated 180° from where the hips face, extra or missing fingers, melting faces, limbs fused with the equipment, impossibly long arms, feet pointing backwards relative to the hips, knees bending sideways. If a real human body could not physically assume the pose shown, that is a hard failure.

- PHYSICAL / MECHANICAL IMPOSSIBILITY on the equipment: a cable, rope, or chain that floats unconnected in mid-air, a handle that the person holds but is not attached to any cable or bar, a pulley with no cable through it, a weight stack floating with no connection, a barbell not aligned with the rails it's supposed to slide along, or any load-bearing element that doesn't physically connect to what it should. If a mechanical engineer would say "this cannot work", that is a hard failure.

- DUPLICATED OR MIRRORED GEOMETRY on the product: two pulleys where the references show one, a doubled console, a second display that shouldn't exist, a cable splitting into two where it should be continuous. If a feature appears twice in the generated image but only once in the references, that is a hard failure.

- THE PRODUCT is grossly distorted (bent, melted, floating, double-sized, proportions that don't match references).

If none of the hard failures apply, continue scoring:

1. PRODUCT ACCURACY (0-10)
   - Does the product match the CLEAN PRODUCT REFERENCES exactly? Shape, colours, display panel position/size, handlebars, buttons, LEDs.
   - Does the BRANDING placement match the usage photos? The SPORTSTECH logo should only appear where it appears in the references — not invented on additional panels or in places the real product doesn't have it.
   - Are there any decorative elements on the product (fake LED bars, red dots, extra buttons, phantom panels) that do NOT appear in ANY of the references? If yes, penalize.
   - Proportions of the product vs. the user.
   - Wood/material finish matches reference intensity.
   - Side panel and end-cap details (roller mounts, small visible holes/screws, front console) must be consistent with references — Gemini tends to smooth these away, penalise when they are absent or wrong.

2. POSE & USAGE CORRECTNESS (0-10) — MOST IMPORTANT
   - Compare the pose in the generated image against the REAL USAGE PHOTOS. Does the person use the equipment the same way? Same grip? Same contact points? Same body mechanics?
   - If the usage photos show people doing a specific movement (seated cable pulldown, squatting under a barbell, rowing, walking) and the generated image shows something DIFFERENT or awkward, that's a usage failure — max 5.
   - Shoes on equipment that demands shoes (treadmills, walking pads, crosstrainers, strength stations)? Barefoot on those → max 5.
   - Facing direction consistent with the product's display/console orientation.
   - Person's weight is clearly on the equipment, not on the surrounding floor.
   - Awkward, stiff, or unnatural posture → max 6.

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
