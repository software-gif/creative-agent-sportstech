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

GEMINI_MODEL = "gemini-2.0-flash-preview-image-generation"
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


def get_product_images(product_handle, max_images=6):
    """Fetch product reference images from Supabase Storage."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    resp = requests.get(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives/products/{product_handle}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    if resp.status_code != 200:
        return []

    files = sorted(resp.json(), key=lambda f: f.get("name", ""))[:max_images]
    images = []
    for f in files:
        img_url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/products/{product_handle}/{f['name']}"
        img_resp = requests.get(img_url, timeout=30)
        if img_resp.status_code == 200:
            data = base64.b64encode(img_resp.content).decode()
            ext = f["name"].rsplit(".", 1)[-1].lower()
            mime = f"image/{'png' if ext == 'png' else 'jpeg'}"
            images.append({"data": data, "mime": mime, "name": f["name"]})
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

    # Generate N images
    for i in range(args.count):
        print(f"\n{'─' * 40}")
        print(f"Image {i + 1}/{args.count}")

        # Build multimodal parts
        parts = []

        # Add product reference images
        for img in product_images:
            parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

        # Add product accuracy instruction
        parts.append({
            "text": f"PRODUCT REFERENCE: The {product_name} must be a literal recreation of the reference images above. Do not simplify or genericize its design. Every detail must match.\n\n"
        })

        # Add character references
        for img in character_images:
            parts.append({"inline_data": {"mime_type": img["mime"], "data": img["data"]}})

        if character_images:
            parts.append({
                "text": "CHARACTER REFERENCE: Strictly adhere to the facial and physical features of this subject. Preserve identity, skin tone, hair, and build.\n\n"
            })

        # Add the main prompt
        if args.prompt:
            prompt_text = args.prompt
        else:
            # Auto-build prompt
            must_match = pk.get("ai_generation_rules", {}).get("must_match", [])
            must_avoid = pk.get("ai_generation_rules", {}).get("must_avoid", [])
            pose = args.pose
            if not pose and pk.get("correct_usage_poses"):
                pose = pk["correct_usage_poses"][0].get("position", "")

            prompt_text = f"""Generate a photorealistic lifestyle photograph.

SCENE: {room_prompt or 'A bright, modern living room with natural light.'}

PERSON: {args.character_description or 'An athletic person'} using the {product_name}.
POSE: {pose or f'Using the {product_name} correctly'}

CAMERA: {args.shot_size} shot, {args.camera_angle}, {args.character_angle} character angle, {args.lens} lens, {args.depth_of_field} aperture. Shot on Hasselblad.

PRODUCT RULES:
{chr(10).join('- ' + r for r in must_match[:5])}

MUST AVOID:
{chr(10).join('- ' + r for r in must_avoid[:5])}

LIGHTING: Soft, natural interior lighting. No high contrast. Professional photography quality.
OUTPUT: Photorealistic, 8K quality, no text overlays, no watermarks.
FORMAT: {args.format} aspect ratio."""

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
