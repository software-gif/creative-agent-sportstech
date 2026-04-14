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


def get_product_images(product_handle):
    """Fetch product reference images: high-res render cutouts first, then
    whatever Shopware thumbnails we have as a lightweight extra.

    The primary source is `renders/<handle>/cutouts/` — those were produced
    by the background-remover skill from the 1500-4096px CGI renders and
    are by far the most useful references Gemini has for matching product
    geometry, materials, and branding.

    The `products/<handle>/` folder contains small Shopware thumbnails
    (often ~200px). They're kept as a low-priority fallback — they can
    still contribute color information without bloating the payload.

    Lifestyle examples are intentionally NOT fetched here. Gemini weights
    images higher than text, so lifestyle refs showing people in the wrong
    orientation caused pose-direction regressions (see commit 9eb82b5).
    Lifestyle context is provided via the cached Image Describer text.
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

    # 3. Shopware thumbnails as a lightweight extra (color anchor)
    thumb_files = list_storage_files(f"products/{product_handle}/")
    print(f"  Shopware thumbs: {len(thumb_files)} found")
    for f in sorted(thumb_files, key=lambda x: x.get("name", "")):
        if f.get("name") == "cutouts":
            continue
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/products/{product_handle}/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"thumb/{f['name']}", "type": "thumb"})

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
    # thumbs are low-res (~200px) and only contribute color information.
    render_cutouts = [img for img in product_images if img.get("type") == "render_cutout"]
    raw_renders = [img for img in product_images if img.get("type") == "render"]
    thumbs = [img for img in product_images if img.get("type") == "thumb"]

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
            image_camera_angle = args.camera_angle or random.choice(VALID_CAMERA_ANGLES)
            image_character_angle = args.character_angle or random.choice(VALID_CHARACTER_ANGLES)
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
            # Prefer the transparent high-res render cutouts; fall back to raw
            # renders when no cutouts exist; append small Shopware thumbs last
            # as a color anchor. Cap total references to MAX_PRODUCT_REFERENCES
            # so the request payload stays reasonable.
            primary_refs = render_cutouts or raw_renders
            # Shuffle so multi-image batches don't always see the same order —
            # Gemini tends to weight earlier images more heavily.
            primary_sampled = random.sample(primary_refs, min(len(primary_refs), MAX_PRODUCT_REFERENCES - min(3, len(thumbs))))
            thumb_sampled = thumbs[:MAX_PRODUCT_REFERENCES - len(primary_sampled)]
            selected_refs = primary_sampled + thumb_sampled

            for img in selected_refs:
                parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

            n_product = len(selected_refs)
            product_refs = ", ".join([f"Image {j+1}" for j in range(n_product)])
            ref_source = "high-resolution transparent CGI renders" if render_cutouts else "product renders"

            parts.append({
                "text": (
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
            })

            # Character references — these are the ONLY other images sent alongside
            # product cutouts. Lifestyle example refs are never appended here; see
            # get_product_images() for the rationale.
            for img in character_images:
                parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

            # === COMPOSITING PROMPT — SCENE SETUP FIRST (person + camera + display physics) ===
            prompt_text = f"""Generate a photorealistic lifestyle photograph of a person using the {product_name}.

{'=' * 40}
SCENE SETUP (strictly enforced — violations make the image unusable):

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
