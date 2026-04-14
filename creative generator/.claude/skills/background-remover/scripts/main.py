#!/usr/bin/env python3
"""Background Remover — normalizes product reference images to transparent PNGs.

Reads originals from `products/<handle>/` in Supabase Storage, runs rembg on
anything that doesn't already have real alpha transparency, writes the result
into `products/<handle>/cutouts/<filename>.png`. Originals are never touched.

Usage:
    python3 .claude/skills/background-remover/scripts/main.py --product woodpad-pro
    python3 .claude/skills/background-remover/scripts/main.py --all
    python3 .claude/skills/background-remover/scripts/main.py --product woodpad-pro --dry-run
"""

import argparse
import io
import os
import sys

import requests
from dotenv import load_dotenv
from PIL import Image
from rembg import remove, new_session

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

ALL_PRODUCTS = [
    "aqua-elite", "f37s-pro", "hgx50", "sbike", "scross",
    "sgym-pro", "svibe", "sxm200", "woodpad-pro", "x150",
]

# Prefixes we know about. `renders/` holds the high-resolution CGI assets
# (1500-4096px) that are actually useful as product references — that is
# our primary target. `products/` in practice holds small Shopware
# thumbnails (often ~200px), which we keep as a secondary source.
SOURCES = ("renders", "products")


def get_headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def list_source_images(source, product):
    """List files directly under <source>/<product>/ (excluding cutouts/)."""
    headers = {**get_headers(), "Content-Type": "application/json"}
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/list/creatives",
        headers=headers,
        json={"prefix": f"{source}/{product}/", "limit": 200},
    )
    if resp.status_code != 200:
        print(f"  ERROR listing {source}/{product}: {resp.status_code} {resp.text[:200]}")
        return []
    return [
        f["name"]
        for f in resp.json()
        if f.get("name") and not f["name"].endswith("/") and f["name"] != "cutouts"
    ]


def download_image(storage_path):
    url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{storage_path}"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.content


def upload_png(storage_path, png_bytes):
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/creatives/{storage_path}",
        headers={**get_headers(), "Content-Type": "image/png", "x-upsert": "true"},
        data=png_bytes,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        print(f"    upload error ({resp.status_code}): {resp.text[:200]}")
        return False
    return True


def already_transparent(img_bytes):
    """True if the image has an alpha channel with at least some transparency.

    We call 250 (out of 255) the cutoff — anything above is effectively opaque
    and the image still has a white/solid background baked in.
    """
    try:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode != "RGBA":
            return False
        alpha = img.split()[-1]
        min_alpha, _ = alpha.getextrema()
        return min_alpha < 250
    except Exception:
        return False


def process_product(source, product, session, dry_run=False):
    print(f"\n=== {source}/{product} ===")
    files = list_source_images(source, product)
    if not files:
        print("  no files found")
        return (0, 0, 0)

    processed = 0
    skipped = 0
    errors = 0

    for fname in files:
        src_path = f"{source}/{product}/{fname}"
        # Target filename — always .png, strip the original extension.
        base = fname.rsplit(".", 1)[0]
        dst_path = f"{source}/{product}/cutouts/{base}.png"

        print(f"  {fname}", end=" ")
        img_bytes = download_image(src_path)
        if img_bytes is None:
            print("→ download failed")
            errors += 1
            continue

        if already_transparent(img_bytes):
            print("→ already transparent, copying as-is")
            if not dry_run:
                upload_png(dst_path, img_bytes)
            skipped += 1
            continue

        try:
            out_bytes = remove(img_bytes, session=session)
        except Exception as e:
            print(f"→ rembg error: {e}")
            errors += 1
            continue

        if dry_run:
            print("→ would upload (dry run)")
        else:
            ok = upload_png(dst_path, out_bytes)
            print("→ uploaded" if ok else "→ UPLOAD FAILED")
            if not ok:
                errors += 1
                continue
        processed += 1

    print(f"  summary: {processed} processed, {skipped} already transparent, {errors} errors")
    return (processed, skipped, errors)


def main():
    parser = argparse.ArgumentParser(description="Background Remover")
    parser.add_argument("--product", default=None, help="Product handle (e.g. woodpad-pro)")
    parser.add_argument("--all", action="store_true", help="Process all products")
    parser.add_argument("--source", default="renders", choices=["renders", "products", "both"],
                        help="Which storage prefix to process (default: renders — the high-res CGI assets)")
    parser.add_argument("--dry-run", action="store_true", help="Don't upload, just report")
    parser.add_argument("--model", default="u2net", help="rembg model name (default u2net)")
    args = parser.parse_args()

    if not SUPABASE_URL:
        sys.exit("ERROR: SUPABASE_URL not set")

    if not args.product and not args.all:
        sys.exit("Provide --product <handle> or --all")

    products = ALL_PRODUCTS if args.all else [args.product]
    sources = SOURCES if args.source == "both" else (args.source,)

    print("=" * 60)
    print("BACKGROUND REMOVER")
    print(f"  Products: {len(products)}")
    print(f"  Sources:  {', '.join(sources)}")
    print(f"  Model:    {args.model}")
    print(f"  Dry run:  {args.dry_run}")
    print("=" * 60)

    # Re-use a single rembg session to avoid reloading the model per image.
    session = new_session(args.model)

    totals = [0, 0, 0]
    for product in products:
        for source in sources:
            p, s, e = process_product(source, product, session, dry_run=args.dry_run)
            totals[0] += p
            totals[1] += s
            totals[2] += e

    print(f"\n{'=' * 60}")
    print(f"DONE: {totals[0]} processed, {totals[1]} already transparent, {totals[2]} errors")
    print("=" * 60)


if __name__ == "__main__":
    main()
