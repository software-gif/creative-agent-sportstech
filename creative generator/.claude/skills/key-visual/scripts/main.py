#!/usr/bin/env python3
"""Key Visual Generator — Composites Character + Product + Room into lifestyle photograph.

The core generation skill that combines all reference elements into one coherent
lifestyle image via Gemini, then stores the result in Supabase.

Usage:
    python3 .claude/skills/key-visual/scripts/main.py \
        --product "f37s-pro" \
        --room-preset "scandinavian" \
        --character-description "A woman aged 30, athletic build, dark hair in ponytail" \
        --pose "Running on the treadmill, dynamic pose" \
        --shot-size "Wide" \
        --camera-angle "Eye level" \
        --lens "50mm" \
        --depth-of-field "f/4" \
        --format "9:16" \
        --prompt "Full composite prompt from Claude"
"""

import argparse
import base64
import json
import os
import random
import subprocess
import sys
import uuid
from datetime import datetime

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-image-preview")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

VALID_CAMERA_ANGLES = ["Eye level", "Slightly above", "High angle", "Slightly below", "Low angle", "Ground level"]
VALID_CHARACTER_ANGLES = ["Front facing", "3/4 angle", "Profile", "Over the shoulder", "Back view"]


def get_supabase_headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def get_brand_id():
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/brands?slug=eq.sportstech&select=id",
        headers=get_supabase_headers(),
    )
    resp.raise_for_status()
    brands = resp.json()
    if not brands:
        sys.exit("ERROR: No brand 'sportstech' found.")
    return brands[0]["id"]


def list_storage_files(prefix, limit=50):
    """List files in Supabase Storage."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"prefix": prefix, "limit": limit},
    )
    if resp.status_code != 200:
        return []
    return [f for f in resp.json() if f.get("name") and not f["name"].startswith(".")]


def download_image(url):
    """Download image and return base64 data + mime type."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = base64.b64encode(resp.content).decode()
            content_type = resp.headers.get("content-type", "image/png")
            if "jpeg" in content_type or "jpg" in content_type:
                mime = "image/jpeg"
            else:
                mime = "image/png"
            return {"data": data, "mime": mime}
    except Exception:
        pass
    return None


MAX_PRODUCT_REFERENCES = 12  # upper bound to keep the request payload sane
MAX_USAGE_REFERENCES = 5     # how many real-user photos to include per generation


def load_reference_catalog(product_handle):
    """Load the vision-analyzed catalog produced by product-image-analyzer.

    Returns a dict keyed by storage_path → metadata, or None if the catalog
    hasn't been built yet (in which case callers fall back to random sampling).
    """
    path = os.path.join(PROJECT_ROOT, "branding", "product_references", f"{product_handle}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("images", {}) or None
    except Exception as e:
        print(f"  WARN: failed to load reference catalog: {e}")
        return None


def map_target_to_catalog_angles(image_camera_angle, image_character_angle):
    """Map the generator's (camera_angle, character_angle) pair to the set of
    catalog camera_angle values that are acceptable matches for the target."""
    relevant = set()
    char_map = {
        "Front facing":     {"front", "front_3_4"},
        "3/4 angle":        {"front_3_4"},
        "Profile":          {"profile_left", "profile_right", "eye_level_side"},
        "Over the shoulder":{"back_3_4"},
        "Back view":        {"back", "back_3_4"},
        "Top View":         {"top_down"},
    }
    relevant.update(char_map.get(image_character_angle, {"front_3_4"}))

    pitch_map = {
        "Low angle":      {"low_angle"},
        "Ground level":   {"low_angle"},
        "Slightly below": {"low_angle"},
        "High angle":     {"high_angle", "top_down"},
        "Slightly above": {"high_angle"},
    }
    relevant.update(pitch_map.get(image_camera_angle, set()))
    return relevant


def dominant_variant(catalog):
    from collections import Counter
    counts = Counter(m.get("variant") for m in catalog.values() if m.get("variant"))
    return counts.most_common(1)[0][0] if counts else None


def select_smart_references(catalog, target_angles, target_variant, max_count=MAX_PRODUCT_REFERENCES):
    """Pick reference paths from the catalog based on target angle + variant.

    Layered strategy:
      1. 1-2 overview / hero shots (full product context)
      2. 2-3 shots with a matching target camera_angle
      3. 2-3 high-detail close-ups (for must-match features like back buttons)
      4. Fill remaining slots with angle diversity (different angles not yet used)
    Always filters to a single variant so Gemini isn't averaging two product
    colours together.
    """
    if not catalog:
        return []

    # Filter by variant — either the one explicitly requested or the dominant
    # one in the catalog (so a woodpad-pro key-visual doesn't mix wood + black).
    variant = target_variant or dominant_variant(catalog)
    candidates = {
        p: m for p, m in catalog.items() if not variant or m.get("variant") == variant
    }
    if not candidates:
        candidates = dict(catalog)  # fallback if filter eliminated everything

    by_detail = lambda p: candidates[p].get("detail_richness", 0)
    selected = []

    def take(paths, limit):
        for p in paths:
            if len(selected) >= max_count:
                return
            if p not in selected and len(selected) < max_count:
                selected.append(p)
                if len([x for x in selected if x in paths]) >= limit:
                    return

    # 1. Overview / hero
    overviews = sorted(
        [p for p, m in candidates.items()
         if m.get("camera_angle") == "hero_overview"
         or m.get("framing") == "full_product"],
        key=by_detail,
        reverse=True,
    )
    take(overviews, 2)

    # 2. Matching target angle
    angle_matches = sorted(
        [p for p, m in candidates.items()
         if m.get("camera_angle") in target_angles and p not in selected],
        key=by_detail,
        reverse=True,
    )
    take(angle_matches, 3)

    # 3. Detail close-ups (must-match features)
    details = sorted(
        [p for p, m in candidates.items()
         if m.get("framing") in ("detail_close_up", "extreme_detail")
         and p not in selected],
        key=by_detail,
        reverse=True,
    )
    take(details, 3)

    # 4. Angle diversity — fill with different camera angles not already used
    used_angles = {candidates[p].get("camera_angle") for p in selected}
    diverse = sorted(
        [p for p, m in candidates.items()
         if p not in selected and m.get("camera_angle") not in used_angles],
        key=by_detail,
        reverse=True,
    )
    for p in diverse:
        if len(selected) >= max_count:
            break
        selected.append(p)

    # 5. Final fill — just top by detail richness
    if len(selected) < max_count:
        leftover = sorted(
            [p for p in candidates if p not in selected],
            key=by_detail,
            reverse=True,
        )
        for p in leftover:
            if len(selected) >= max_count:
                break
            selected.append(p)

    return [(p, candidates[p]) for p in selected[:max_count]]


def get_product_images(product_handle):
    """Fetch product reference images: high-res render cutouts first,
    Shopware thumbnails as a colour anchor, and real-user usage photos
    as a distinct pose/usage reference.

    - `renders/<handle>/cutouts/` → transparent CGI cutouts, the geometric
      ground truth. Produced by the background-remover skill.
    - `products/<handle>/` → small Shopware listing thumbnails (~200px),
      low-priority colour anchor.
    - `lifestyle/<handle>/` → real photos of a person using the product.
      Previously disabled because Gemini was copying the photographer's
      camera angle / person / clothing straight into the output. Now
      re-enabled but explicitly labelled in the prompt as POSE-ONLY
      references, and the SCENE SETUP / HARD FAILURES block in the
      compositing prompt overrides any stray attempts at copying.
    """
    images = []

    # 1. Render cutouts (high-res, transparent PNGs from background-remover)
    cutout_files = list_storage_files(f"renders/{product_handle}/cutouts/")
    print(f"  Render cutouts: {len(cutout_files)} found")
    for f in sorted(cutout_files, key=lambda x: x.get("name", "")):
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/renders/{product_handle}/cutouts/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"render_cutout/{f['name']}", "type": "render_cutout"})

    # 2. Raw renders (fallback when cutouts are missing — never run rembg)
    if not cutout_files:
        render_files = list_storage_files(f"renders/{product_handle}/")
        print(f"  Renders (raw fallback): {len(render_files)} found")
        for f in sorted(render_files, key=lambda x: x.get("name", "")):
            url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/renders/{product_handle}/{f['name']}"
            img = download_image(url)
            if img:
                images.append({**img, "name": f"render/{f['name']}", "type": "render"})

    # 3. Shopware thumbnails as a lightweight extra (colour anchor)
    thumb_files = list_storage_files(f"products/{product_handle}/")
    print(f"  Shopware thumbs: {len(thumb_files)} found")
    for f in sorted(thumb_files, key=lambda x: x.get("name", "")):
        if f.get("name") == "cutouts":
            continue
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/products/{product_handle}/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"thumb/{f['name']}", "type": "thumb"})

    # 4. Lifestyle examples — real usage photos, labelled as POSE-ONLY refs
    #    in the prompt. Critical for products with sparse render coverage
    #    (sxm200, hgx50, svibe) where Gemini otherwise can't tell what the
    #    product does or how a person physically interacts with it.
    lifestyle_files = list_storage_files(f"lifestyle/{product_handle}/")
    print(f"  Lifestyle examples: {len(lifestyle_files)} found")
    for f in sorted(lifestyle_files, key=lambda x: x.get("name", "")):
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/lifestyle/{product_handle}/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"lifestyle/{f['name']}", "type": "lifestyle"})

    return images


def get_character_images(character_id):
    """Fetch character reference images from Supabase."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/characters?id=eq.{character_id}&select=headshot_path,full_body_front_path,full_body_profile_path",
        headers=get_supabase_headers(),
    )
    if resp.status_code != 200 or not resp.json():
        return []

    char = resp.json()[0]
    images = []
    for path_key in ["headshot_path", "full_body_front_path", "full_body_profile_path"]:
        path = char.get(path_key)
        if path:
            url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{path}"
            img_resp = requests.get(url, timeout=30)
            if img_resp.status_code == 200:
                data = base64.b64encode(img_resp.content).decode()
                images.append({"data": data, "mime": "image/png", "name": path_key})
    return images


def load_cached_product_description(product_handle):
    """Load pre-generated product description from Image Describer cache."""
    cache_path = os.path.join(PROJECT_ROOT, "branding", "product_descriptions", f"{product_handle}.txt")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            text = f.read()
        if len(text) > 200:
            print(f"  Product description: {len(text)} chars (cached)")
            return text
    print(f"  WARNING: No cached description for {product_handle}. Run: python3 .claude/skills/image-describer/scripts/main.py --product {product_handle}")
    return ""


def load_room_preset(preset_name):
    """Load room prompt from room_prompts.json."""
    path = os.path.join(PROJECT_ROOT, "branding", "room_prompts.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    for room in data.get("rooms", []):
        if room["id"] == preset_name:
            return room["prompt"]
    return None


def load_models_pool():
    """Load the models pool from lifestyle_variance.json for auto-rotation."""
    path = os.path.join(PROJECT_ROOT, "branding", "lifestyle_variance.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("models", [])


def get_random_model(models_pool, index=0):
    """Pick a model from the pool, rotating through them."""
    if not models_pool:
        return None
    return models_pool[index % len(models_pool)]


def load_product_knowledge(product_handle):
    """Load product-specific AI rules."""
    path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("products", {}).get(product_handle, {})


def generate_image(parts, attempt=1):
    """Send multi-part prompt to Gemini and return image bytes."""
    print(f"  Generating (attempt {attempt})...")

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": 1.0,
        },
    }

    try:
        resp = requests.post(GEMINI_ENDPOINT, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            print("  WARNING: No candidates returned")
            return None

        resp_parts = candidates[0].get("content", {}).get("parts", [])
        for part in resp_parts:
            if "inlineData" in part:
                img_bytes = base64.b64decode(part["inlineData"]["data"])
                mime = part["inlineData"].get("mimeType", "image/png")
                ext = "png" if "png" in mime else "jpg"
                return img_bytes, ext

        print("  WARNING: No image in response")
        return None

    except Exception as e:
        print(f"  ERROR: {e}")
        if attempt < 3:
            return generate_image(parts, attempt + 1)
        return None


def upload_to_supabase(image_bytes, path, ext="png"):
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/creatives/{path}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": f"image/{ext}"},
        data=image_bytes,
    )
    if resp.status_code in (200, 201):
        return f"{SUPABASE_URL}/storage/v1/object/public/creatives/{path}"
    print(f"  Upload error ({resp.status_code}): {resp.text[:200]}")
    return None


def save_creative_to_db(creative_data):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/creatives",
        headers={**get_supabase_headers(), "Prefer": "return=representation"},
        json=creative_data,
    )
    resp.raise_for_status()
    return resp.json()[0]


def main():
    parser = argparse.ArgumentParser(description="Key Visual Generator")
    parser.add_argument("--product", required=True, help="Product handle")
    parser.add_argument("--character-id", default=None, help="Character UUID from character-builder")
    parser.add_argument("--character-description", default=None, help="Inline character description")
    parser.add_argument("--environment-id", default=None, help="Environment UUID from room-builder")
    parser.add_argument("--room-preset", default=None, help="Room preset ID from room_prompts.json")
    parser.add_argument("--room-description", default=None, help="Inline room description")
    parser.add_argument("--pose", default=None, help="Usage pose description")
    parser.add_argument("--shot-size", default="Wide")
    parser.add_argument("--camera-angle", default=None,
                        help=f"One of: {', '.join(VALID_CAMERA_ANGLES)}. Omit to rotate randomly per image.")
    parser.add_argument("--character-angle", default=None,
                        help=f"One of: {', '.join(VALID_CHARACTER_ANGLES)}. Omit to rotate randomly per image.")
    parser.add_argument("--lens", default="50mm")
    parser.add_argument("--depth-of-field", default="f/4")
    parser.add_argument("--format", default="9:16")
    parser.add_argument("--prompt", default=None, help="Full composite prompt from Claude (overrides auto-build)")
    parser.add_argument("--count", type=int, default=1, help="Number of images to generate")
    parser.add_argument("--variant", default=None,
                        help="Product color/material variant (e.g. wood_light, black). If unset, defaults to the dominant variant in the catalog.")
    parser.add_argument("--auto-qc", action="store_true",
                        help="Run quality-control on each generated image and retry on failure.")
    parser.add_argument("--qc-retries", type=int, default=2,
                        help="Max retries per image when --auto-qc is enabled (default 2, so up to 3 attempts total).")
    parser.add_argument("--qc-threshold", type=int, default=7,
                        help="Minimum QC score (0-10) to accept the image (default 7).")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")

    brand_id = get_brand_id()
    batch_id = str(uuid.uuid4())

    print("=" * 60)
    print("KEY VISUAL GENERATOR")
    print("=" * 60)
    print(f"  Product: {args.product}")
    print(f"  Camera: {args.shot_size} | {args.camera_angle or 'auto-rotate'} | {args.lens} | {args.depth_of_field}")
    print(f"  Position: {args.character_angle or 'auto-rotate'}")
    print(f"  Format: {args.format}")
    print(f"  Count: {args.count}")
    print(f"  Batch: {batch_id}")

    # Load product knowledge
    pk = load_product_knowledge(args.product)
    product_name = pk.get("name", args.product)

    # Fetch product reference images
    print(f"\n  Loading product references for {args.product}...")
    product_images = get_product_images(args.product)
    print(f"  Found {len(product_images)} reference images")

    # Fetch character references
    character_images = []
    if args.character_id:
        print(f"  Loading character {args.character_id}...")
        character_images = get_character_images(args.character_id)
        print(f"  Found {len(character_images)} character references")

    # Resolve room prompt
    room_prompt = args.room_description
    if args.room_preset and not room_prompt:
        room_prompt = load_room_preset(args.room_preset)
        if room_prompt:
            print(f"  Using room preset: {args.room_preset}")

    # Pre-select best images by type. Render cutouts are the high-quality
    # geometric anchors (transparent PNGs, 1500-4096px). Raw renders are a
    # fallback for products where the bg-remover hasn't run yet. Shopware
    # thumbs are low-res (~200px) and only contribute colour information.
    # Lifestyle examples are real photos of people using the product and
    # teach Gemini usage semantics — labelled POSE-ONLY in the prompt.
    render_cutouts = [img for img in product_images if img.get("type") == "render_cutout"]
    raw_renders = [img for img in product_images if img.get("type") == "render"]
    thumbs = [img for img in product_images if img.get("type") == "thumb"]
    lifestyle_refs = [img for img in product_images if img.get("type") == "lifestyle"]

    # Load catalog + attach metadata to every downloaded cutout. With a
    # catalog we can do deterministic smart selection per attempt; without
    # one we still have random sampling as fallback.
    reference_catalog = load_reference_catalog(args.product)
    if reference_catalog:
        print(f"  Catalog: {len(reference_catalog)} entries — smart selection enabled")
        # The catalog keys are storage_paths like
        # "renders/woodpad-pro/cutouts/17.png". Match by filename.
        by_filename = {}
        for path, meta in reference_catalog.items():
            fn = path.rsplit("/", 1)[-1]
            by_filename[fn] = (path, meta)
        for img in render_cutouts:
            # img["name"] looks like "render_cutout/17.png" from get_product_images
            fn = img.get("name", "").rsplit("/", 1)[-1]
            if fn in by_filename:
                img["catalog_path"] = by_filename[fn][0]
                img["catalog_meta"] = by_filename[fn][1]
    else:
        print("  Catalog: none — using random sampling fallback")

    # === STEP 1: LOAD CACHED PRODUCT DESCRIPTION (from Image Describer skill) ===
    product_description_ai = load_cached_product_description(args.product)

    # === MODEL ROTATION — pick different models for batch generation ===
    models_pool = load_models_pool()
    if models_pool and not args.character_description and not args.character_id:
        print(f"  Model rotation: {len(models_pool)} models available")

    # Path to the quality-control skill (for --auto-qc subprocess calls)
    qc_script = os.path.join(SCRIPT_DIR, "..", "..", "quality-control", "scripts", "main.py")
    max_attempts = (args.qc_retries + 1) if args.auto_qc else 1

    # Generate N images
    for i in range(args.count):
        print(f"\n{'─' * 40}")
        print(f"Image {i + 1}/{args.count}")

        # Auto-rotate model if no specific character given. Kept outside the
        # retry loop so multiple attempts for the same image slot reuse the
        # same model — re-rolling camera angle per attempt is enough variance.
        character_desc = args.character_description
        if not character_desc and not args.character_id and models_pool:
            model = get_random_model(models_pool, i)
            character_desc = model["prompt_snippet"]
            print(f"  Auto-model: {model['description']}")

        accepted = False
        for attempt in range(1, max_attempts + 1):
            if max_attempts > 1:
                print(f"  Attempt {attempt}/{max_attempts}")

            # Auto-rotate camera angle per attempt when not explicitly set. On
            # retries this gives Gemini a fresh angle to try — often the fix
            # for a pose/geometry failure.
            #
            # For sparse-reference products (where we only have renders from a
            # single viewpoint), product_knowledge can override the global pool
            # via ai_generation_rules.allowed_camera_angles / allowed_character_angles
            # so the retry loop never rolls a shot Gemini has no ground truth for.
            camera_pool = pk.get("ai_generation_rules", {}).get("allowed_camera_angles") or VALID_CAMERA_ANGLES
            character_pool = pk.get("ai_generation_rules", {}).get("allowed_character_angles") or VALID_CHARACTER_ANGLES
            image_camera_angle = args.camera_angle or random.choice(camera_pool)
            image_character_angle = args.character_angle or random.choice(character_pool)
            if not args.camera_angle or not args.character_angle:
                print(f"  Camera rotation: {image_camera_angle} / {image_character_angle}")

            # === PROVEN APPROACH (CR-005 to CR-007 worked well) ===
            # Product cutouts FIRST → Lifestyle for style → Character → Compositing prompt
            parts = []

            must_match = pk.get("ai_generation_rules", {}).get("must_match", [])
            must_avoid = pk.get("ai_generation_rules", {}).get("must_avoid", [])
            how_it_works = pk.get("how_it_works", {})

            pose = args.pose
            pose_camera_angle = ""
            if pk.get("correct_usage_poses"):
                if not pose:
                    pose = pk["correct_usage_poses"][0].get("position", "")
                pose_camera_angle = pk["correct_usage_poses"][0].get("camera_angle", "")

            # Product-specific pose camera (e.g. "3/4 from behind-side") encodes the
            # only viewpoint that keeps the display on the user's side. Overrides the
            # rotated/per-image character angle unless the user passed a pose override.
            effective_character_angle = pose_camera_angle or image_character_angle

            # Get direction info if available
            direction = how_it_works.get("direction", "")

            # GROUP 1: Product references (ground truth for product accuracy).
            # When a catalog is available we do deterministic smart selection:
            # variant-filter first, then mix overview + target-angle + detail
            # close-ups + angle diversity. Without a catalog we fall back to
            # random sampling from the downloaded cutouts.
            selected_refs = []
            slot_labels = []

            if reference_catalog and render_cutouts:
                target_angles = map_target_to_catalog_angles(image_camera_angle, image_character_angle)
                smart_choices = select_smart_references(
                    reference_catalog,
                    target_angles,
                    target_variant=getattr(args, "variant", None),
                    max_count=MAX_PRODUCT_REFERENCES,
                )
                # Resolve smart choices back to the downloaded image dicts
                catalog_to_img = {
                    img.get("catalog_path"): img
                    for img in render_cutouts
                    if img.get("catalog_path")
                }
                for path, meta in smart_choices:
                    img = catalog_to_img.get(path)
                    if img is None:
                        continue
                    selected_refs.append(img)
                    slot_labels.append(
                        f"{meta.get('camera_angle', '?')}"
                        f" · {meta.get('framing', '?')}"
                        f" · {meta.get('variant', '?')}"
                        f" · detail {meta.get('detail_richness', '?')}"
                    )
                print(f"  Smart selection: {len(selected_refs)} refs "
                      f"(variant={getattr(args, 'variant', None) or dominant_variant(reference_catalog)}, "
                      f"target_angles={sorted(target_angles)})")

            if not selected_refs:
                # Fallback: random sampling over whatever primary refs we have
                primary_refs = render_cutouts or raw_renders
                primary_sampled = random.sample(
                    primary_refs,
                    min(len(primary_refs), MAX_PRODUCT_REFERENCES - min(3, len(thumbs))),
                )
                thumb_sampled = thumbs[:MAX_PRODUCT_REFERENCES - len(primary_sampled)]
                selected_refs = primary_sampled + thumb_sampled

            for img in selected_refs:
                parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

            n_product = len(selected_refs)
            product_refs = ", ".join([f"Image {j+1}" for j in range(n_product)])
            ref_source = "high-resolution transparent CGI renders" if render_cutouts else "product renders"

            # If we have slot labels from smart selection, tell Gemini exactly
            # what each image is for so it can weight them appropriately.
            if slot_labels:
                slot_description = "\n".join(
                    f"  - Image {j+1}: {lbl}" for j, lbl in enumerate(slot_labels)
                )
                ref_explanation = (
                    f"[{product_refs}] = PRODUCT SHAPE REFERENCE for the {product_name} "
                    f"({n_product} curated {ref_source}, deterministically chosen to cover the "
                    f"target shot). Per-image roles:\n{slot_description}\n\n"
                    f"Use these images to match the exact geometry, proportions, colors, "
                    f"materials, wood grain, branding text, and every visible detail of the "
                    f"product. Treat them as the ground truth for what the product looks like. "
                    f"Pay close attention to the detail close-ups — those show features "
                    f"(back-end controls, front console, side rails, end caps) that often get "
                    f"smoothed away. DO NOT copy the camera angle, composition, or orientation "
                    f"of the references — those are marketing shots. The final image uses a "
                    f"COMPLETELY DIFFERENT camera position defined in the SCENE SETUP section "
                    f"of the prompt below.\n\n"
                )
            else:
                ref_explanation = (
                    f"[{product_refs}] = PRODUCT SHAPE REFERENCE for the {product_name} "
                    f"({n_product} {ref_source}). Use these images ONLY to match the exact "
                    f"geometry, proportions, colors, materials, wood grain, branding text, "
                    f"and every visible detail of the product. Treat these as the ground "
                    f"truth for what the product looks like. DO NOT copy the camera angle, "
                    f"composition, orientation, or which side of the product faces the "
                    f"camera — those are marketing shots with the display/front artificially "
                    f"facing the viewer. The final image uses a COMPLETELY DIFFERENT camera "
                    f"position defined in the SCENE SETUP section of the prompt below.\n\n"
                )

            parts.append({"text": ref_explanation})

            # GROUP 2: Usage/lifestyle references. Real photos of a person
            # using this product. These are what make the difference for
            # sparse-reference products (sxm200, hgx50, svibe) — Gemini
            # learns HOW the product is physically used, not just what it
            # looks like. Labelled explicitly so Gemini doesn't copy the
            # photographer's camera, the model, or the background.
            usage_sampled = random.sample(
                lifestyle_refs, min(len(lifestyle_refs), MAX_USAGE_REFERENCES)
            ) if lifestyle_refs else []
            if usage_sampled:
                usage_start = n_product + 1
                usage_end = n_product + len(usage_sampled)
                usage_slot = (
                    f"Image {usage_start}"
                    if usage_start == usage_end
                    else f"Images {usage_start}-{usage_end}"
                )
                for img in usage_sampled:
                    parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})
                parts.append({
                    "text": (
                        f"[{usage_slot}] = USAGE REFERENCES — real photos of people using the "
                        f"{product_name}. These are here so you understand HOW the product is "
                        f"physically used: where the feet stand, where the hands grip, where "
                        f"the weight rests, and what a believable training posture looks like "
                        f"on this specific machine.\n\n"
                        f"COPY from these images:\n"
                        f"  - the pose, body mechanics, and stance\n"
                        f"  - the exact contact points between the person and the product "
                        f"(feet, hands, seat, shoulders, etc.)\n"
                        f"  - the fact that the person is ACTIVELY using the product\n\n"
                        f"DO NOT COPY from these images:\n"
                        f"  - the camera angle (that is defined by the SCENE SETUP below)\n"
                        f"  - the specific person shown (face, body type, ethnicity, clothing "
                        f"— those are defined by the PERSON section below)\n"
                        f"  - the lighting, background, room, or any decor\n"
                        f"  - any product details that disagree with the PRODUCT SHAPE "
                        f"REFERENCE images above — those come first\n"
                        f"  - any product variant (colour, material) that disagrees with the "
                        f"PRODUCT SHAPE REFERENCE — stay consistent with that variant\n\n"
                        f"Treat these as pose references for a choreographer, not as photos "
                        f"to imitate.\n\n"
                    )
                })

            # Character references — the last image group before the prompt.
            for img in character_images:
                parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

            # === COMPOSITING PROMPT — SCENE SETUP FIRST (person + camera + display physics) ===
            prompt_text = f"""Generate a photorealistic lifestyle photograph of a person ACTIVELY USING the {product_name}. The person must be physically on/at the equipment, with their weight supported by it — not standing next to it while doing something else.

{'=' * 40}
SCENE SETUP (strictly enforced — violations make the image unusable):

0. PRODUCT CONTACT (NON-NEGOTIABLE):
The person must be in active physical contact with the {product_name}. Their feet must be on the walking/running/stepping surface, or their body on the seat/saddle/plate, or their hands on the handles/bar. The product is NOT a decorative floor accessory that the person happens to be standing beside. If the person is on the wood/tile/rug floor next to the product, the image is unusable.

1. PERSON ORIENTATION:
{direction}
{how_it_works.get('principle', '')}
{how_it_works.get('position', '')}

2. CAMERA FRAMING:
{effective_character_angle}

3. DISPLAY / CONSOLE ORIENTATION (physical law):
The {product_name}'s display screen has exactly ONE side with the interface and it ALWAYS faces the user. The camera position in (2) determines what the camera can see:
- When the camera is behind or beside the user, the display faces AWAY from the camera. We see only the back edge of the console. No screen interface is visible in the frame.
- The user's face and the screen interface CANNOT both be visible in the same frame. This combination is physically impossible — never generate it.
{'=' * 40}

PERSON: {character_desc or args.character_description or 'An athletic person in dark fitness clothing'}
POSE: {pose}

ENVIRONMENT: {room_prompt or 'A bright modern living room with warm oak floors, large windows, sheer curtains, natural light.'}

PRODUCT DETAILS (shape, colors, and materials — composition is defined in SCENE SETUP above):
{product_description_ai}

MANDATORY product accuracy:
{chr(10).join('- ' + r for r in must_match)}

FORBIDDEN:
{chr(10).join('- ' + r for r in must_avoid)}

Technical: {args.shot_size}, {image_camera_angle}, {args.lens}, {args.depth_of_field}. Hasselblad. Soft natural lighting. {args.format} aspect ratio. No text/watermarks. Professional fitness photography."""

            parts.append({"text": prompt_text})

            # Generate
            result = generate_image(parts)
            if result is None:
                print(f"  FAILED: Could not generate image {i + 1}")
                continue

            img_bytes, ext = result
            creative_id = str(uuid.uuid4())
            storage_path = f"creatives/{batch_id}/{creative_id}.{ext}"
            url = upload_to_supabase(img_bytes, storage_path, ext)

            if not url:
                local_dir = os.path.join(PROJECT_ROOT, "creatives", batch_id)
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, f"{creative_id}.{ext}")
                with open(local_path, "wb") as f:
                    f.write(img_bytes)
                print(f"  Saved locally: {local_path}")

            # Save to database
            creative_data = {
                "id": creative_id,
                "brand_id": brand_id,
                "batch_id": batch_id,
                "storage_path": storage_path,
                "prompt_text": prompt_text,
                "prompt_json": {
                    "product": args.product,
                    "character_id": args.character_id,
                    "character_description": args.character_description,
                    "environment_id": args.environment_id,
                    "room_preset": args.room_preset,
                    "pose": args.pose,
                },
                "shot_size": args.shot_size,
                "camera_angle": image_camera_angle,
                "character_angle": effective_character_angle,
                "lens": args.lens,
                "depth_of_field": args.depth_of_field,
                "creative_type": "lifestyle",
                "format": args.format,
                "generation_model": GEMINI_MODEL,
                "generation_mode": "raw",
                "environment_style": args.room_preset,
                "product_category": pk.get("product_category", args.product),
                "character_id": args.character_id,
                "environment_id": args.environment_id,
                "status": "generated",
            }

            # Remove None values
            creative_data = {k: v for k, v in creative_data.items() if v is not None}

            saved = save_creative_to_db(creative_data)
            print(f"  SAVED: {saved['id']}")
            if url:
                print(f"  URL: {url}")

            if not args.auto_qc:
                accepted = True
                break

            # Run QC inline. --delete-on-fail drops the creative from DB +
            # storage when the score is under threshold, so on a FAIL we can
            # just loop back and regenerate from scratch with a fresh angle.
            print(f"  Running QC (threshold {args.qc_threshold})...")
            qc_proc = subprocess.run(
                [
                    sys.executable, qc_script,
                    "--creative-id", creative_id,
                    "--delete-on-fail",
                    "--threshold", str(args.qc_threshold),
                ],
                capture_output=True, text=True,
            )
            sys.stdout.write(qc_proc.stdout)
            if qc_proc.stderr:
                sys.stderr.write(qc_proc.stderr)

            if qc_proc.returncode == 0:
                accepted = True
                break
            print(f"  QC rejected image (attempt {attempt}/{max_attempts}), retrying…")

        if not accepted:
            print(f"  WARN: Image slot {i + 1} exhausted {max_attempts} attempts without passing QC")

    print(f"\n{'=' * 60}")
    print(f"BATCH COMPLETE: {batch_id}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
