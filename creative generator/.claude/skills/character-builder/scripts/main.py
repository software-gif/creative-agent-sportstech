#!/usr/bin/env python3
"""Character Builder — Generates consistent model identity across 3 reference shots.

Creates Headshot, Full Body Front, and Full Body Profile images using Gemini,
then stores them in Supabase for use as reference in lifestyle shots.

Usage:
    python3 .claude/skills/character-builder/scripts/main.py \
        --gender "Female" --age 30 --height "5ft 8 inches" \
        --physique "Soft, Medium build" --skin "darkish skin, racially ambiguous" \
        --hairstyle "straightened natural hair, shoulder length, in a tight back ponytail" \
        --expression "slight smile" --clothes "Training Clothes" \
        --prompts "prompt1*prompt2*prompt3"
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

SHOT_NAMES = ["headshot", "full_body_front", "full_body_profile"]


def get_supabase_headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def get_brand_id():
    """Get the Sportstech brand ID from Supabase."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/brands?slug=eq.sportstech&select=id",
        headers=get_supabase_headers(),
    )
    resp.raise_for_status()
    brands = resp.json()
    if not brands:
        print("ERROR: No brand 'sportstech' found. Run the migration first.")
        sys.exit(1)
    return brands[0]["id"]


def generate_image(prompt_text, shot_name, attempt=1):
    """Send prompt to Gemini and return image bytes."""
    print(f"\n  Generating {shot_name} (attempt {attempt})...")

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
            print(f"  WARNING: No candidates returned for {shot_name}")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                img_data = part["inlineData"]["data"]
                mime = part["inlineData"].get("mimeType", "image/png")
                ext = "png" if "png" in mime else "jpg"
                return base64.b64decode(img_data), ext

        print(f"  WARNING: No image in response for {shot_name}")
        return None

    except Exception as e:
        print(f"  ERROR generating {shot_name}: {e}")
        if attempt < 3:
            return generate_image(prompt_text, shot_name, attempt + 1)
        return None


def upload_to_supabase(image_bytes, path, ext="png"):
    """Upload image to Supabase Storage."""
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
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{path}"
        return public_url
    else:
        print(f"  Upload error ({resp.status_code}): {resp.text[:200]}")
        return None


def save_character_to_db(character_data):
    """Insert character record into Supabase."""
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/characters",
        headers={**get_supabase_headers(), "Prefer": "return=representation"},
        json=character_data,
    )
    resp.raise_for_status()
    return resp.json()[0]


def main():
    parser = argparse.ArgumentParser(description="Character Builder")
    parser.add_argument("--gender", required=True)
    parser.add_argument("--age", type=int, required=True)
    parser.add_argument("--height", default="average")
    parser.add_argument("--physique", default="athletic")
    parser.add_argument("--skin", default="")
    parser.add_argument("--hairstyle", default="")
    parser.add_argument("--expression", default="natural smile")
    parser.add_argument("--clothes", default="Training Clothes")
    parser.add_argument("--background", default="#f8f8f8")
    parser.add_argument("--prompts", required=True, help="3 prompts separated by *")
    parser.add_argument("--name", default=None, help="Optional character name")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)
    if not SUPABASE_URL:
        print("ERROR: SUPABASE_URL not set in .env")
        sys.exit(1)

    brand_id = get_brand_id()
    character_id = str(uuid.uuid4())

    print("=" * 60)
    print("CHARACTER BUILDER")
    print("=" * 60)
    print(f"  Gender: {args.gender}")
    print(f"  Age: {args.age}")
    print(f"  Physique: {args.physique}")
    print(f"  Skin: {args.skin}")
    print(f"  Hair: {args.hairstyle}")
    print(f"  Expression: {args.expression}")
    print(f"  Clothes: {args.clothes}")
    print(f"  Character ID: {character_id}")

    # Parse the 3 prompts
    prompts = [p.strip() for p in args.prompts.split("*") if p.strip()]
    if len(prompts) != 3:
        print(f"ERROR: Expected 3 prompts separated by *, got {len(prompts)}")
        sys.exit(1)

    # Generate and upload each shot
    paths = {}
    for i, (prompt, shot_name) in enumerate(zip(prompts, SHOT_NAMES)):
        print(f"\n{'─' * 40}")
        print(f"Shot {i+1}/3: {shot_name}")
        print(f"Prompt: {prompt[:120]}...")

        result = generate_image(prompt, shot_name)
        if result is None:
            print(f"  FAILED: Could not generate {shot_name}")
            continue

        img_bytes, ext = result
        storage_path = f"characters/{character_id}/{shot_name}.{ext}"
        url = upload_to_supabase(img_bytes, storage_path, ext)

        if url:
            paths[shot_name] = storage_path
            print(f"  Uploaded: {storage_path}")
        else:
            print(f"  FAILED: Could not upload {shot_name}")

    # Save character to database
    character_data = {
        "id": character_id,
        "brand_id": brand_id,
        "name": args.name or f"{args.gender} {args.age}y {args.physique}",
        "gender": args.gender,
        "age": args.age,
        "height": args.height,
        "physique": args.physique,
        "skin_type": args.skin,
        "hairstyle": args.hairstyle,
        "expression": args.expression,
        "clothes": args.clothes,
        "headshot_path": paths.get("headshot"),
        "full_body_front_path": paths.get("full_body_front"),
        "full_body_profile_path": paths.get("full_body_profile"),
        "prompt_data": {
            "prompts": prompts,
            "background": args.background,
            "generated_at": datetime.utcnow().isoformat(),
        },
    }

    saved = save_character_to_db(character_data)
    print(f"\n{'=' * 60}")
    print(f"CHARACTER SAVED: {saved['id']}")
    print(f"  Name: {saved['name']}")
    print(f"  Headshot: {paths.get('headshot', 'FAILED')}")
    print(f"  Full Body Front: {paths.get('full_body_front', 'FAILED')}")
    print(f"  Full Body Profile: {paths.get('full_body_profile', 'FAILED')}")
    print(f"{'=' * 60}")

    # Save manifest locally
    manifest_dir = os.path.join(PROJECT_ROOT, "characters")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, f"{character_id}.json")
    with open(manifest_path, "w") as f:
        json.dump(character_data, f, indent=2, ensure_ascii=False)
    print(f"\nManifest saved: {manifest_path}")


if __name__ == "__main__":
    main()
