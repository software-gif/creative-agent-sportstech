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


def get_product_images(product_handle):
    """Fetch ALL product reference images: Freisteller + Renders + best Lifestyle examples."""
    images = []

    # 1. ALL Freisteller (cutout images — most important for product accuracy)
    freisteller_files = list_storage_files(f"products/{product_handle}/")
    print(f"  Freisteller: {len(freisteller_files)} found")
    for f in sorted(freisteller_files, key=lambda x: x.get("name", "")):
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/products/{product_handle}/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"freisteller/{f['name']}", "type": "freisteller"})

    # 2. Renders (3D renders — great for product shape/detail)
    render_files = list_storage_files(f"renders/{product_handle}/", limit=8)
    print(f"  Renders: {len(render_files)} found (using up to 8)")
    for f in sorted(render_files, key=lambda x: x.get("name", ""))[:8]:
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/renders/{product_handle}/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"render/{f['name']}", "type": "render"})

    # 3. Lifestyle examples (show how product looks in real settings — up to 4)
    lifestyle_files = list_storage_files(f"lifestyle/{product_handle}/", limit=4)
    print(f"  Lifestyle examples: {len(lifestyle_files)} found (using up to 4)")
    for f in sorted(lifestyle_files, key=lambda x: x.get("name", ""))[:4]:
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/lifestyle/{product_handle}/{f['name']}"
        img = download_image(url)
        if img:
            images.append({**img, "name": f"lifestyle/{f['name']}", "type": "lifestyle_example"})

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


def describe_product_from_images(product_images, product_name):
    """Step 1: Use Gemini TEXT to analyze product images and generate ultra-detailed description."""
    print("  Running Image Describer on product references...")

    parts = []
    for img in product_images[:4]:
        parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

    parts.append({
        "text": f"""Analyze these reference images of the {product_name} fitness equipment in extreme detail.

Describe EVERY visual detail you can see:
1. EXACT shape and silhouette from every visible angle
2. EXACT colors — primary body color, accent colors, LED colors, screen colors
3. Materials — metal, plastic, rubber, fabric. Matte or glossy finish?
4. Display/screen — size, position, what's shown on it, border color
5. Branding — EXACT text, font style, position, color of logos/text
6. Buttons/controls — colors, positions, shapes
7. Unique design features — LED strips, accent lines, specific curves
8. Proportions — relative sizes of parts (e.g., "the display is about 1/4 the width of the machine")
9. Structural details — how parts connect, visible joints, cables, rails

Output a single dense paragraph with ALL details. This description will be used to recreate this EXACT product in an AI-generated image. Be obsessively precise."""
    })

    # Use text model for analysis (not image generation)
    text_model = "gemini-2.5-flash"
    text_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{text_model}:generateContent?key={GEMINI_API_KEY}"

    try:
        resp = requests.post(text_endpoint, json={
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000},
        }, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if text:
            print(f"  Image Describer: {len(text)} chars generated")
            return text
    except Exception as e:
        print(f"  Image Describer failed: {e}")

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
    parser.add_argument("--camera-angle", default="Eye level")
    parser.add_argument("--character-angle", default="3/4 angle")
    parser.add_argument("--lens", default="50mm")
    parser.add_argument("--depth-of-field", default="f/4")
    parser.add_argument("--format", default="9:16")
    parser.add_argument("--prompt", default=None, help="Full composite prompt from Claude (overrides auto-build)")
    parser.add_argument("--count", type=int, default=1, help="Number of images to generate")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")

    brand_id = get_brand_id()
    batch_id = str(uuid.uuid4())

    print("=" * 60)
    print("KEY VISUAL GENERATOR")
    print("=" * 60)
    print(f"  Product: {args.product}")
    print(f"  Camera: {args.shot_size} | {args.camera_angle} | {args.lens} | {args.depth_of_field}")
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

    # Pre-select best images by type
    freisteller = [img for img in product_images if img.get("type") == "freisteller"]
    renders = [img for img in product_images if img.get("type") == "render"]
    lifestyle_refs = [img for img in product_images if img.get("type") == "lifestyle_example"]

    # === STEP 1: IMAGE DESCRIBER — analyze product before generating ===
    product_description_ai = describe_product_from_images(freisteller, product_name)

    # === MODEL ROTATION — pick different models for batch generation ===
    models_pool = load_models_pool()
    if models_pool and not args.character_description and not args.character_id:
        print(f"  Model rotation: {len(models_pool)} models available")

    # Generate N images
    for i in range(args.count):
        print(f"\n{'─' * 40}")
        print(f"Image {i + 1}/{args.count}")

        # Auto-rotate model if no specific character given
        character_desc = args.character_description
        if not character_desc and not args.character_id and models_pool:
            model = get_random_model(models_pool, i)
            character_desc = model["prompt_snippet"]
            print(f"  Auto-model: {model['description']}")

        # === NEW LOGIC: Lifestyle first → Product details → Person ===
        # Priority order:
        # 1. Lifestyle examples (show product + human interaction + room = the TARGET)
        # 2. Product cutouts (for exact product details)
        # 3. Character references (if available)
        parts = []

        must_match = pk.get("ai_generation_rules", {}).get("must_match", [])
        must_avoid = pk.get("ai_generation_rules", {}).get("must_avoid", [])
        how_it_works = pk.get("how_it_works", {})

        pose = args.pose
        if not pose and pk.get("correct_usage_poses"):
            pose = pk["correct_usage_poses"][0].get("position", "")

        # STEP A: Lifestyle examples FIRST — these show the COMPLETE picture
        # (correct product in room with person using it correctly)
        best_lifestyle = lifestyle_refs[:3]
        for img in best_lifestyle:
            parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

        n_lifestyle = len(best_lifestyle)
        if n_lifestyle > 0:
            lifestyle_refs_str = ", ".join([f"Image {j+1}" for j in range(n_lifestyle)])
            parts.append({
                "text": f"[{lifestyle_refs_str}] These are REAL LIFESTYLE PHOTOGRAPHS of the {product_name} in use. Study these carefully — they show:\n- The CORRECT appearance of the product in a room setting\n- How a REAL PERSON interacts with this equipment (correct body position, posture, foot placement)\n- The correct SCALE and PROPORTIONS of the product relative to a human\n- The style and quality level your output must match\n\n"
            })

        # STEP B: Product cutouts — for exact product details
        best_freisteller = freisteller[:4]
        for img in best_freisteller:
            parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

        n_product = len(best_freisteller)
        if n_product > 0:
            product_refs_str = ", ".join([f"Image {n_lifestyle+j+1}" for j in range(n_product)])
            parts.append({
                "text": f"[{product_refs_str}] These are PRODUCT CUTOUTS showing the exact {product_name} design details on a white background. The product in your generated image must be a LITERAL RECREATION of these — every color, LED strip, display, button, and branding element must match EXACTLY.\n\n"
            })

        # STEP C: Character references (if available)
        for img in character_images:
            parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

        n_character = len(character_images)
        if n_character > 0:
            char_refs_str = ", ".join([f"Image {n_lifestyle+n_product+j+1}" for j in range(n_character)])
            parts.append({
                "text": f"[{char_refs_str}] CHARACTER REFERENCE — preserve this person's identity exactly.\n\n"
            })

        # === MAIN PROMPT — structured by priority ===
        prompt_text = f"""Create a professional lifestyle photograph. You are a precision compositing engine.

STEP 1 — PRODUCT IN ROOM:
Place the {product_name} in this environment: {room_prompt or 'A bright modern living room with warm oak floors, large windows, natural light.'}
The product must be a LITERAL RECREATION of the reference cutout images. Do not simplify or genericize ANY part of its design.

PRODUCT DETAILS (from AI analysis of reference images):
{product_description_ai}

STEP 2 — HUMAN INTERACTION:
{character_desc or args.character_description or 'An athletic person in dark fitness clothing'} is using the {product_name}.
{f'How this product works: {how_it_works.get("principle", "")}' if how_it_works.get('principle') else ''}
{f'Correct body position: {how_it_works.get("position", "")}' if how_it_works.get('position') else ''}
Specific pose: {pose}

CRITICAL — Look at the lifestyle reference images above. The person must interact with the product EXACTLY like the people in those reference photos:
- Feet must be PHYSICALLY ON the equipment (on the belt, on the pedals, on the seat)
- Hands must be in a REALISTIC position (on handlebars, swinging naturally, gripping handles)
- Body weight must be supported by the equipment, not floating or hovering
- The person must look like they are genuinely USING the equipment mid-workout, captured candidly
- Study the body angles, foot positions, and hand placements in the lifestyle reference images and REPLICATE that level of realism

STEP 3 — CAMERA & QUALITY:
{args.shot_size}, {args.camera_angle}, {args.character_angle}, {args.lens}, {args.depth_of_field}. Shot on Hasselblad.
Soft natural interior lighting. No harsh contrast. {args.format} aspect ratio. No text or watermarks.
Output must look like a high-end commercial fitness photograph — not AI-generated."""

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
            "camera_angle": args.camera_angle,
            "character_angle": args.character_angle,
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

    print(f"\n{'=' * 60}")
    print(f"BATCH COMPLETE: {batch_id}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
