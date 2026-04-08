#!/usr/bin/env python3
"""Image Describer — Analyzes product images and generates detailed visual descriptions.

Run once per product, results are cached in branding/product_descriptions/{handle}.txt
and reused by all generation skills for maximum product accuracy.

Usage:
    python3 .claude/skills/image-describer/scripts/main.py --product f37s-pro
    python3 .claude/skills/image-describer/scripts/main.py --all
    python3 .claude/skills/image-describer/scripts/main.py --product f37s-pro --force
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

DESCRIPTIONS_DIR = os.path.join(PROJECT_ROOT, "branding", "product_descriptions")


def list_storage_files(prefix, limit=50):
    key = SUPABASE_ANON_KEY
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"prefix": prefix, "limit": limit},
    )
    if resp.status_code != 200:
        return []
    return [f for f in resp.json() if f.get("name") and not f["name"].startswith(".")]


def download_image_b64(url):
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
    except Exception:
        pass
    return None


def load_product_knowledge(handle):
    path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("products", {}).get(handle, {})


def get_all_product_handles():
    path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return list(data.get("products", {}).keys())


def describe_product(handle, force=False):
    """Analyze product images and generate detailed description."""
    # Check cache
    os.makedirs(DESCRIPTIONS_DIR, exist_ok=True)
    cache_path = os.path.join(DESCRIPTIONS_DIR, f"{handle}.txt")

    if os.path.exists(cache_path) and not force:
        with open(cache_path) as f:
            cached = f.read()
        if len(cached) > 500:
            print(f"  {handle}: Using cached description ({len(cached)} chars)")
            return cached

    pk = load_product_knowledge(handle)
    product_name = pk.get("name", handle)

    # Load Freisteller images
    files = list_storage_files(f"products/{handle}/")
    if not files:
        print(f"  {handle}: No reference images found!")
        return ""

    print(f"  {handle}: Analyzing {len(files)} reference images...")

    # Build multimodal request — send up to 6 best images
    parts = []
    for f in sorted(files, key=lambda x: x.get("name", ""))[:6]:
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/products/{handle}/{f['name']}"
        b64 = download_image_b64(url)
        if b64:
            ext = f["name"].rsplit(".", 1)[-1].lower()
            mime = f"image/{'png' if ext == 'png' else 'jpeg'}"
            parts.append({"inline_data": {"mime_type": mime, "data": b64}})

    # Also send lifestyle examples for context on human interaction
    lifestyle_files = list_storage_files(f"lifestyle/{handle}/", limit=3)
    for f in sorted(lifestyle_files, key=lambda x: x.get("name", ""))[:2]:
        url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/lifestyle/{handle}/{f['name']}"
        b64 = download_image_b64(url)
        if b64:
            ext = f["name"].rsplit(".", 1)[-1].lower()
            mime = f"image/{'png' if ext == 'png' else 'jpeg'}"
            parts.append({"inline_data": {"mime_type": mime, "data": b64}})

    n_product = min(len(files), 6)
    n_lifestyle = min(len(lifestyle_files), 2)

    # Get how_it_works from product knowledge
    how_it_works = pk.get("how_it_works", {})
    how_text = ""
    if how_it_works:
        how_text = f"\nKNOWN PRODUCT INFO:\n"
        for k, v in how_it_works.items():
            if isinstance(v, str):
                how_text += f"- {k}: {v}\n"
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    how_text += f"- {k2}: {v2}\n"

    parts.append({
        "text": f"""You are an expert product analyst for fitness equipment photography.

The first {n_product} images show the {product_name} (cutout/product shots on white background).
{f'The last {n_lifestyle} images show the product being used by real people in a room setting.' if n_lifestyle > 0 else ''}
{how_text}

Analyze ALL reference images and write an OBSESSIVELY DETAILED visual description of the {product_name}. This description will be injected into an AI image generation prompt to recreate this EXACT product. If any detail is missing or wrong, the generated image will be unusable.

Cover EVERY one of these aspects:

1. OVERALL SHAPE & SILHOUETTE: Exact form factor, proportions, height relative to a human, width, depth. Is it compact, massive, sleek, bulky?

2. BODY COLOR & FINISH: Primary color (be exact — matte black, glossy black, dark gray?), secondary colors, accent colors. Finish type (matte, satin, glossy, textured).

3. DISPLAY/SCREEN: Exact size, position on the machine, shape (rectangular, rounded?), bezel color, what's shown on screen, angle of the screen.

4. HANDLEBARS/GRIPS: Shape, color, position. Are they straight, curved, drop-bar style? Where do they connect to the body? Any controls ON the handlebars?

5. CONTROLS & BUTTONS: Every button visible — colors (red, green?), positions, shapes. Safety key (color, position, attached cord?).

6. BRANDING & TEXT: EXACT text visible on the product ("SPORTSTECH", model name, etc.), where each text appears, font color, font style.

7. LED ACCENTS: Where are LED strips/lights? What color(s)? Do they follow the body shape? Are they always on or reactive?

8. MATERIALS & TEXTURES: What parts are metal, plastic, rubber, fabric, wood? Surface texture (smooth, ribbed, perforated?).

9. STRUCTURAL DETAILS: How parts connect, visible joints, cables, rails, wheels, folding mechanisms.

10. HUMAN INTERACTION: Based on the lifestyle images and product knowledge — which direction does the person FACE when using this? Where do feet go? Where do hands go? What is the correct body posture? What would look WRONG?

Write ONE CONTINUOUS DENSE PARAGRAPH with ALL details. No headers, no bullet points, no markdown — just a single block of text describing every visual aspect. This will be directly injected into an image generation prompt."""
    })

    try:
        resp = requests.post(TEXT_ENDPOINT, json={
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 6000},
        }, timeout=90)
        resp.raise_for_status()
        result = resp.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        if text and len(text) > 200:
            # Cache it
            with open(cache_path, "w") as f:
                f.write(text)
            print(f"  {handle}: Generated and cached ({len(text)} chars)")
            return text
        else:
            print(f"  {handle}: Description too short ({len(text)} chars)")
            return ""

    except Exception as e:
        print(f"  {handle}: ERROR — {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Image Describer — Product Analysis")
    parser.add_argument("--product", default=None, help="Product handle to analyze")
    parser.add_argument("--all", action="store_true", help="Analyze all products")
    parser.add_argument("--force", action="store_true", help="Force re-analysis (ignore cache)")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")

    print("=" * 60)
    print("IMAGE DESCRIBER — Product Analysis")
    print("=" * 60)

    if args.all:
        handles = get_all_product_handles()
        print(f"  Analyzing {len(handles)} products...")
        for handle in handles:
            describe_product(handle, force=args.force)
    elif args.product:
        describe_product(args.product, force=args.force)
    else:
        print("ERROR: Provide --product <handle> or --all")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"Descriptions cached in: {DESCRIPTIONS_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
