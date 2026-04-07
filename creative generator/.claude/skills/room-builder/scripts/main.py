#!/usr/bin/env python3
"""Room / Environment Builder — Generates consistent interior scenes with multi-angle coverage.

Creates a room and generates 4-5 camera angle variations, stored in Supabase
as environment references for lifestyle compositing.

Usage:
    python3 .claude/skills/room-builder/scripts/main.py \
        --preset "japandi_wellness" \
        --prompts "prompt1*prompt2*prompt3*prompt4" \
        --name "Japandi Forest View"

    python3 .claude/skills/room-builder/scripts/main.py \
        --description "A serene high-end minimalist wellness room..." \
        --prompts "prompt1*prompt2*prompt3*prompt4" \
        --name "Custom Wellness Room"
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
        print("ERROR: No brand 'sportstech' found.")
        sys.exit(1)
    return brands[0]["id"]


def load_preset(preset_name):
    """Load environment preset from lifestyle_variance.json."""
    variance_path = os.path.join(PROJECT_ROOT, "branding", "lifestyle_variance.json")
    if not os.path.exists(variance_path):
        return None
    with open(variance_path) as f:
        data = json.load(f)
    envs = data.get("environments", {})
    return envs.get(preset_name)


def generate_image(prompt_text, label, attempt=1):
    """Send prompt to Gemini and return image bytes."""
    print(f"\n  Generating {label} (attempt {attempt})...")

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
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
            print(f"  WARNING: No candidates for {label}")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                img_data = part["inlineData"]["data"]
                mime = part["inlineData"].get("mimeType", "image/png")
                ext = "png" if "png" in mime else "jpg"
                return base64.b64decode(img_data), ext

        print(f"  WARNING: No image in response for {label}")
        return None

    except Exception as e:
        print(f"  ERROR generating {label}: {e}")
        if attempt < 3:
            return generate_image(prompt_text, label, attempt + 1)
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
    else:
        print(f"  Upload error ({resp.status_code}): {resp.text[:200]}")
        return None


def save_environment_to_db(env_data):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/environments",
        headers={**get_supabase_headers(), "Prefer": "return=representation"},
        json=env_data,
    )
    resp.raise_for_status()
    return resp.json()[0]


def main():
    parser = argparse.ArgumentParser(description="Room / Environment Builder")
    parser.add_argument("--preset", default=None, help="Environment preset name from lifestyle_variance.json")
    parser.add_argument("--description", default=None, help="Custom room description (if not using preset)")
    parser.add_argument("--name", required=True, help="Name for this environment")
    parser.add_argument("--style", default=None, help="Interior style label")
    parser.add_argument("--prompts", required=True, help="4-5 angle prompts separated by *")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    brand_id = get_brand_id()
    env_id = str(uuid.uuid4())

    # Resolve room description
    room_description = args.description
    style = args.style

    if args.preset:
        preset = load_preset(args.preset)
        if preset:
            room_description = room_description or preset.get("prompt_snippet", "")
            style = style or preset.get("name", args.preset)
            print(f"  Using preset: {args.preset} ({style})")
        else:
            print(f"  WARNING: Preset '{args.preset}' not found, using description")

    if not room_description:
        print("ERROR: Provide --preset or --description")
        sys.exit(1)

    print("=" * 60)
    print("ROOM / ENVIRONMENT BUILDER")
    print("=" * 60)
    print(f"  Name: {args.name}")
    print(f"  Style: {style or 'Custom'}")
    print(f"  Environment ID: {env_id}")
    print(f"  Description: {room_description[:120]}...")

    # Parse angle prompts
    prompts = [p.strip() for p in args.prompts.split("*") if p.strip()]
    if len(prompts) < 3:
        print(f"ERROR: Expected 3-5 angle prompts, got {len(prompts)}")
        sys.exit(1)

    # Generate and upload each angle
    reference_images = []
    for i, prompt in enumerate(prompts):
        label = f"angle_{i+1}"
        print(f"\n{'─' * 40}")
        print(f"Angle {i+1}/{len(prompts)}")
        print(f"Prompt: {prompt[:150]}...")

        result = generate_image(prompt, label)
        if result is None:
            print(f"  FAILED: Could not generate {label}")
            continue

        img_bytes, ext = result
        storage_path = f"environments/{env_id}/{label}.{ext}"
        url = upload_to_supabase(img_bytes, storage_path, ext)

        if url:
            reference_images.append({
                "angle": i + 1,
                "storage_path": storage_path,
                "public_url": url,
                "prompt": prompt,
            })
            print(f"  Uploaded: {storage_path}")
        else:
            print(f"  FAILED: Could not upload {label}")

    # Save environment to database
    env_data = {
        "id": env_id,
        "brand_id": brand_id,
        "name": args.name,
        "style": style,
        "description": room_description,
        "room_prompt": room_description,
        "angle_prompts": [p for p in prompts],
        "reference_images": reference_images,
        "metadata": {
            "preset": args.preset,
            "num_angles": len(prompts),
            "generated_at": datetime.utcnow().isoformat(),
        },
    }

    saved = save_environment_to_db(env_data)
    print(f"\n{'=' * 60}")
    print(f"ENVIRONMENT SAVED: {saved['id']}")
    print(f"  Name: {saved['name']}")
    print(f"  Style: {saved.get('style', 'Custom')}")
    print(f"  Angles: {len(reference_images)} generated")
    for ref in reference_images:
        print(f"    Angle {ref['angle']}: {ref['storage_path']}")
    print(f"{'=' * 60}")

    # Save manifest locally
    manifest_dir = os.path.join(PROJECT_ROOT, "environments")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, f"{env_id}.json")
    with open(manifest_path, "w") as f:
        json.dump(env_data, f, indent=2, ensure_ascii=False)
    print(f"\nManifest saved: {manifest_path}")


if __name__ == "__main__":
    main()
