#!/usr/bin/env python3
"""Color Variant Generator — Changes product color in an existing image.

Takes a source image and regenerates it with the product in a different
color/material while preserving the scene, model, and all other elements.

Usage:
    python3 .claude/skills/color-variant/scripts/main.py \
        --source-image "path/to/source.png" \
        --product "rowing-machine" \
        --target-color "black" \
        --material-instructions "The real, rich, natural wood grain should remain..." \
        --logo-instructions "Sportstech logo should be black metallic"
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

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-preview-image-generation")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

# Default material instructions per product type
DEFAULT_MATERIAL_INSTRUCTIONS = {
    "rowing-machine": {
        "wood_to_black": "The real, rich, natural wood grain should remain. The wood texture should be vivid and pronounced, with deep, intricate patterns. Enhance the contrast and depth of the wood grain to make it stand out, but ensure it remains authentic and true to real wood.",
        "logo": "Sportstech logo should be black metallic.",
    },
    "walking-pad": {
        "default": "Keep the surface texture and material finish authentic.",
        "logo": "Sportstech logo should match the new color scheme.",
    },
    "treadmill-f75": {
        "default": "Keep the metallic finish and surface textures authentic.",
        "logo": "Sportstech logo should remain red on silver parts.",
    },
}


def get_supabase_headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


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


def encode_image(path):
    """Read and base64-encode a local image file."""
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = f"image/{'png' if ext == 'png' else 'jpeg'}"
    return data, mime


def download_from_supabase(storage_path):
    """Download an image from Supabase storage to a temp file."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{storage_path}"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        tmp_path = os.path.join(PROJECT_ROOT, ".tmp_color_variant_source.png")
        with open(tmp_path, "wb") as f:
            f.write(resp.content)
        return tmp_path
    return None


def generate_color_variant(source_image_path, prompt_text, attempt=1):
    """Send source image + color variant prompt to Gemini."""
    print(f"\n  Generating color variant (attempt {attempt})...")

    img_data, img_mime = encode_image(source_image_path)
    if not img_data:
        print(f"  ERROR: Could not read source image: {source_image_path}")
        return None

    parts = [
        {"inline_data": {"mime_type": img_mime, "data": img_data}},
        {"text": prompt_text},
    ]

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": 1.0,
        },
    }

    try:
        resp = requests.post(GEMINI_ENDPOINT, json=payload, timeout=120)
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
            return generate_color_variant(source_image_path, prompt_text, attempt + 1)
        return None


def upload_to_supabase(image_bytes, path, ext="png"):
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": f"image/{ext}",
    }
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/creatives/{path}",
        headers=headers,
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
    parser = argparse.ArgumentParser(description="Color Variant Generator")
    parser.add_argument("--source-image", required=True, help="Path to source image (local or Supabase storage path)")
    parser.add_argument("--product", required=True, help="Product handle (e.g. rowing-machine)")
    parser.add_argument("--target-color", required=True, help="Target color (e.g. black, gray, wood-natural)")
    parser.add_argument("--material-instructions", default=None, help="Custom material preservation instructions")
    parser.add_argument("--logo-instructions", default=None, help="Logo color/style instructions")
    parser.add_argument("--keep-scene", action="store_true", default=True, help="Keep scene and character the same")
    parser.add_argument("--source-creative-id", default=None, help="Source creative ID from Supabase")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")

    brand_id = get_brand_id()

    # Resolve source image path
    source_path = args.source_image
    if not os.path.exists(source_path):
        # Try as Supabase storage path
        print(f"  Source not found locally, trying Supabase: {source_path}")
        downloaded = download_from_supabase(source_path)
        if downloaded:
            source_path = downloaded
        else:
            # Try with PROJECT_ROOT prefix
            alt_path = os.path.join(PROJECT_ROOT, source_path)
            if os.path.exists(alt_path):
                source_path = alt_path
            else:
                sys.exit(f"ERROR: Source image not found: {args.source_image}")

    # Build material instructions
    material_inst = args.material_instructions
    logo_inst = args.logo_instructions

    if not material_inst:
        product_defaults = DEFAULT_MATERIAL_INSTRUCTIONS.get(args.product, {})
        color_key = f"wood_to_{args.target_color}" if "wood" in args.product else "default"
        material_inst = product_defaults.get(color_key, product_defaults.get("default", ""))

    if not logo_inst:
        product_defaults = DEFAULT_MATERIAL_INSTRUCTIONS.get(args.product, {})
        logo_inst = product_defaults.get("logo", "Sportstech logo should match the new color scheme.")

    # Build the prompt
    product_name = args.product.replace("-", " ").title()
    prompt = f"""Given the provided image, keep the {product_name} untouched, just change its color to {args.target_color}.
Make sure to:
Other instruction: {material_inst}
Logo: {logo_inst}"""

    print("=" * 60)
    print("COLOR VARIANT GENERATOR")
    print("=" * 60)
    print(f"  Product: {args.product}")
    print(f"  Target Color: {args.target_color}")
    print(f"  Source: {source_path}")
    print(f"  Prompt: {prompt[:200]}...")

    # Generate
    result = generate_color_variant(source_path, prompt)
    if result is None:
        sys.exit("FAILED: Could not generate color variant")

    img_bytes, ext = result
    creative_id = str(uuid.uuid4())
    storage_path = f"color_variants/{creative_id}.{ext}"
    url = upload_to_supabase(img_bytes, storage_path, ext)

    if not url:
        # Save locally as fallback
        local_dir = os.path.join(PROJECT_ROOT, "creatives", "color_variants")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, f"{creative_id}.{ext}")
        with open(local_path, "wb") as f:
            f.write(img_bytes)
        print(f"  Saved locally: {local_path}")
        storage_path = f"creatives/color_variants/{creative_id}.{ext}"

    # Save to database
    creative_data = {
        "id": creative_id,
        "brand_id": brand_id,
        "storage_path": storage_path,
        "prompt_text": prompt,
        "prompt_json": {
            "source_image": args.source_image,
            "source_creative_id": args.source_creative_id,
            "target_color": args.target_color,
            "material_instructions": material_inst,
            "logo_instructions": logo_inst,
        },
        "creative_type": "color_variant",
        "color_variant": args.target_color,
        "generation_model": GEMINI_MODEL,
        "status": "generated",
    }

    saved = save_creative_to_db(creative_data)
    print(f"\n{'=' * 60}")
    print(f"COLOR VARIANT SAVED: {saved['id']}")
    print(f"  Color: {args.target_color}")
    print(f"  Storage: {storage_path}")
    if url:
        print(f"  URL: {url}")
    print(f"{'=' * 60}")

    # Cleanup temp file
    tmp = os.path.join(PROJECT_ROOT, ".tmp_color_variant_source.png")
    if os.path.exists(tmp):
        os.remove(tmp)


if __name__ == "__main__":
    main()
