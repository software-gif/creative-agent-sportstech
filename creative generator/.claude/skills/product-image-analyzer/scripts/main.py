#!/usr/bin/env python3
"""Product Image Analyzer — builds a Gemini-vision-backed catalog of every
product reference image so key-visual can pick the right references
instead of random-sampling.

Usage:
    python3 .claude/skills/product-image-analyzer/scripts/main.py --product woodpad-pro
    python3 .claude/skills/product-image-analyzer/scripts/main.py --all
    python3 .claude/skills/product-image-analyzer/scripts/main.py --product woodpad-pro --refresh
"""

import argparse
import base64
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

TEXT_MODEL = "gemini-2.5-flash"
TEXT_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}"

CATALOG_DIR = os.path.join(PROJECT_ROOT, "branding", "product_references")

ALL_PRODUCTS = [
    "aqua-elite", "f37s-pro", "hgx50", "sbike", "scross",
    "sgym-pro", "svibe", "sxm200", "woodpad-pro", "x150",
]

CAMERA_ANGLE_ENUM = [
    "front",
    "front_3_4",
    "profile_left",
    "profile_right",
    "back_3_4",
    "back",
    "top_down",
    "low_angle",
    "high_angle",
    "eye_level_side",
    "hero_overview",
]

FRAMING_ENUM = [
    "full_product",
    "three_quarter",
    "detail_close_up",
    "extreme_detail",
]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "camera_angle": {"type": "string", "enum": CAMERA_ANGLE_ENUM},
        "framing": {"type": "string", "enum": FRAMING_ENUM},
        "variant": {
            "type": "string",
            "description": "Colour/material variant visible — e.g. wood_light, wood_dark, black, grey, red, default",
        },
        "visible_parts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Product parts clearly visible and usable as reference",
        },
        "detail_richness": {
            "type": "integer",
            "description": "0-10 — how much fine detail is recoverable from this image",
        },
        "key_features": {
            "type": "string",
            "description": "One-line note about what makes this particular image uniquely useful",
        },
    },
    "required": ["camera_angle", "framing", "variant", "visible_parts", "detail_richness", "key_features"],
}


def get_supabase_headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def list_cutouts(product):
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives",
        headers=get_supabase_headers(),
        json={"prefix": f"renders/{product}/cutouts/", "limit": 200},
    )
    if resp.status_code != 200:
        print(f"  ERROR listing cutouts: {resp.status_code} {resp.text[:200]}")
        return []
    return sorted(
        [
            f"renders/{product}/cutouts/{f['name']}"
            for f in resp.json()
            if f.get("name") and not f["name"].endswith("/")
        ]
    )


def download_b64(storage_path):
    url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{storage_path}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode()
    except Exception as e:
        print(f"    download error: {e}")
    return None


def load_product_knowledge(product):
    path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("products", {}).get(product, {})


def analyse_image(storage_path, pk):
    img_b64 = download_b64(storage_path)
    if not img_b64:
        return None

    product_name = pk.get("name", "product")
    must_match = pk.get("ai_generation_rules", {}).get("must_match", [])

    prompt = f"""You are cataloging one reference image of the {product_name} for an AI lifestyle-image pipeline.

Analyse the image and return structured metadata that will later be used to pick the best references for a given shot. Be precise:

- camera_angle: where the camera is relative to the product.
- framing: how much of the product is in frame, and at what zoom level.
- variant: which colour/material version is shown (wood_light, wood_dark, black, grey, red, default, etc.). Be consistent across images of the same colour.
- visible_parts: explicit list of product parts/components/features that are clearly visible enough to be useful as reference (e.g. back_controls, power_port, front_console, display_screen, side_rail, end_cap, branding_logo, handlebar, flywheel, seat, pedals, cable_tower).
- detail_richness: 0-10 — 10 means tiny elements like screws, buttons, and text are all legible; 0 means the image is a blurry silhouette.
- key_features: one sentence about what makes this specific image uniquely useful as a reference (e.g. "Only image showing the rear control panel buttons in full detail").

Product rules to keep in mind when deciding what counts as a meaningful visible part:
{chr(10).join('- ' + r for r in must_match[:10])}"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1500,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }

    try:
        resp = requests.post(TEXT_ENDPOINT, json=payload, timeout=60)
        resp.raise_for_status()
        text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return json.loads(text)
    except Exception as e:
        print(f"    analyse error: {e}")
        return None


def catalog_path(product):
    return os.path.join(CATALOG_DIR, f"{product}.json")


def load_catalog(product):
    path = catalog_path(product)
    if not os.path.exists(path):
        return {"product": product, "images": {}}
    with open(path) as f:
        return json.load(f)


def save_catalog(product, catalog):
    os.makedirs(CATALOG_DIR, exist_ok=True)
    with open(catalog_path(product), "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def process_product(product, refresh=False):
    print(f"\n=== {product} ===")
    pk = load_product_knowledge(product)
    if not pk:
        print(f"  WARN: no product_knowledge entry for {product}, analysing anyway")

    paths = list_cutouts(product)
    if not paths:
        print("  no cutouts found — run background-remover first")
        return (0, 0, 0)

    catalog = load_catalog(product)
    existing = catalog["images"]

    to_analyse = paths if refresh else [p for p in paths if p not in existing]
    print(f"  total: {len(paths)} cutouts, {len(to_analyse)} to analyse, {len(existing) if not refresh else 0} cached")

    analysed = 0
    errors = 0
    for i, storage_path in enumerate(to_analyse, start=1):
        fname = storage_path.rsplit("/", 1)[-1]
        print(f"  [{i}/{len(to_analyse)}] {fname}", end=" ")
        result = analyse_image(storage_path, pk)
        if result is None:
            print("→ error")
            errors += 1
            continue
        existing[storage_path] = result
        summary = f"{result.get('camera_angle','?')} · {result.get('variant','?')} · detail {result.get('detail_richness','?')}"
        print(f"→ {summary}")
        analysed += 1
        # Light pacing so we don't slam the API
        time.sleep(0.2)

    catalog["images"] = existing
    save_catalog(product, catalog)
    print(f"  saved {len(existing)} entries to {catalog_path(product)}")
    return (analysed, len(existing) - analysed, errors)


def main():
    parser = argparse.ArgumentParser(description="Product Image Analyzer")
    parser.add_argument("--product", default=None, help="Product handle (e.g. woodpad-pro)")
    parser.add_argument("--all", action="store_true", help="Process all products")
    parser.add_argument("--refresh", action="store_true", help="Re-analyse images already in the catalog")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")
    if not args.product and not args.all:
        sys.exit("Provide --product <handle> or --all")

    products = ALL_PRODUCTS if args.all else [args.product]

    print("=" * 60)
    print("PRODUCT IMAGE ANALYZER")
    print(f"  Products: {len(products)}")
    print(f"  Refresh:  {args.refresh}")
    print("=" * 60)

    totals = [0, 0, 0]
    for product in products:
        a, c, e = process_product(product, refresh=args.refresh)
        totals[0] += a
        totals[1] += c
        totals[2] += e

    print(f"\n{'=' * 60}")
    print(f"DONE: {totals[0]} analysed, {totals[1]} cached, {totals[2]} errors")
    print("=" * 60)


if __name__ == "__main__":
    main()
