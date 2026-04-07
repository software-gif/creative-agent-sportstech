#!/usr/bin/env python3
"""Product Upload — Uploads product images and data to Supabase.

Usage:
    python3 .claude/skills/product-upload/scripts/main.py \
        --handle "vp500" \
        --name "VP500 Vibrationsplatte" \
        --category "vibration_plate" \
        --url "https://www.sportstech.de/vibrationsplatte/vp500" \
        --colors '["black"]' \
        --price 299.00 \
        --images "/path/to/img1.png" "/path/to/img2.png"

    # Or with a ZIP:
    python3 .claude/skills/product-upload/scripts/main.py \
        --handle "vp500" \
        --name "VP500 Vibrationsplatte" \
        --category "vibration_plate" \
        --zip "/path/to/VP500.zip"
"""

import argparse
import glob
import json
import os
import sys
import tempfile
import zipfile

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


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


def extract_zip(zip_path):
    """Extract ZIP and return list of image paths."""
    tmp_dir = tempfile.mkdtemp(prefix="product_upload_")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)

    images = sorted([
        f for f in glob.glob(os.path.join(tmp_dir, "**/*"), recursive=True)
        if os.path.isfile(f)
        and f.lower().endswith((".jpg", ".jpeg", ".png"))
        and "__MACOSX" not in f
        and ".DS_Store" not in f
    ])
    return images


def main():
    parser = argparse.ArgumentParser(description="Product Upload")
    parser.add_argument("--handle", required=True, help="Product handle/slug")
    parser.add_argument("--name", required=True, help="Product display name")
    parser.add_argument("--category", required=True, help="Product category")
    parser.add_argument("--url", default=None, help="Product page URL")
    parser.add_argument("--colors", default="[]", help="JSON array of colors")
    parser.add_argument("--price", type=float, default=None, help="Price in EUR")
    parser.add_argument("--images", nargs="*", default=[], help="Image file paths")
    parser.add_argument("--zip", default=None, help="ZIP file with images")
    parser.add_argument("--metadata", default="{}", help="Additional metadata as JSON")
    args = parser.parse_args()

    if not SUPABASE_URL:
        sys.exit("ERROR: SUPABASE_URL not set")

    brand_id = get_brand_id()
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY

    print("=" * 60)
    print("PRODUCT UPLOAD")
    print("=" * 60)
    print(f"  Handle: {args.handle}")
    print(f"  Name: {args.name}")
    print(f"  Category: {args.category}")

    # Resolve images
    image_paths = list(args.images)
    if args.zip:
        print(f"\n  Extracting ZIP: {args.zip}")
        zip_images = extract_zip(args.zip)
        image_paths.extend(zip_images)
        print(f"  Found {len(zip_images)} images in ZIP")

    if not image_paths:
        print("WARNING: No images provided")

    # Create product record
    colors = json.loads(args.colors) if isinstance(args.colors, str) else args.colors
    metadata = json.loads(args.metadata) if isinstance(args.metadata, str) else args.metadata
    if args.url:
        metadata["url"] = args.url

    product = {
        "brand_id": brand_id,
        "handle": args.handle,
        "name": args.name,
        "category": args.category,
        "price": args.price,
        "colors": colors,
        "metadata": metadata,
    }

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/products",
        headers={**get_supabase_headers(), "Prefer": "return=representation"},
        json=product,
    )
    resp.raise_for_status()
    product_id = resp.json()[0]["id"]
    print(f"\n  Product created: {product_id}")

    # Upload images
    uploaded = 0
    for i, img_path in enumerate(image_paths):
        ext = "jpg" if img_path.lower().endswith((".jpg", ".jpeg")) else "png"
        mime = f"image/{'jpeg' if ext == 'jpg' else 'png'}"
        storage_path = f"products/{args.handle}/{i}.{ext}"

        with open(img_path, "rb") as f:
            r = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/creatives/{storage_path}",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": mime},
                data=f.read(),
            )

        if r.status_code in (200, 201):
            requests.post(
                f"{SUPABASE_URL}/rest/v1/product_images",
                headers={**get_supabase_headers(), "Prefer": "return=minimal"},
                json={
                    "product_id": product_id,
                    "storage_path": storage_path,
                    "image_type": "reference",
                    "sort_order": i,
                },
            )
            uploaded += 1
            print(f"  [{i}] Uploaded: {storage_path}")
        else:
            print(f"  [{i}] FAILED: {r.status_code} {os.path.basename(img_path)}")

    print(f"\n{'=' * 60}")
    print(f"PRODUCT UPLOAD COMPLETE")
    print(f"  Product ID: {product_id}")
    print(f"  Handle: {args.handle}")
    print(f"  Images: {uploaded}/{len(image_paths)} uploaded")
    print(f"  Storage: products/{args.handle}/")
    print(f"\n  Next steps:")
    print(f"  1. Add entry to branding/product_knowledge.json")
    print(f"  2. Generate lifestyle images with /key-visual --product {args.handle}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
