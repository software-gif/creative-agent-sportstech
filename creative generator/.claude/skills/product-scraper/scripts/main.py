#!/usr/bin/env python3
"""Product Scraper — Fetches product data and images from Shopify store."""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip3 install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' not installed. Run: pip3 install python-dotenv")
    sys.exit(1)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))


def load_config():
    """Load brand.json."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    if not os.path.exists(brand_path):
        print(f"Error: brand.json not found at {brand_path}")
        sys.exit(1)

    with open(brand_path) as f:
        brand = json.load(f)

    return brand


def fetch_all_products(shop_url):
    """Fetch all products via Shopify JSON API (paginated)."""
    all_products = []
    page = 1
    base_url = shop_url.rstrip("/")

    while True:
        url = f"{base_url}/products.json?limit=250&page={page}"
        print(f"  Fetching page {page}...")

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        products = resp.json().get("products", [])
        if not products:
            break

        all_products.extend(products)
        page += 1

    return all_products


def download_product_images(products, images_dir):
    """Download all product images in original quality."""
    downloaded = 0
    skipped = 0
    failed = 0

    for product in products:
        handle = product["handle"]
        product_dir = os.path.join(images_dir, handle)
        os.makedirs(product_dir, exist_ok=True)

        for idx, image in enumerate(product.get("images", [])):
            src = image.get("src", "")
            if not src:
                continue

            filename = f"{idx}.jpg"
            filepath = os.path.join(product_dir, filename)

            if os.path.exists(filepath):
                skipped += 1
                continue

            try:
                r = requests.get(src, timeout=30)
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(r.content)
                downloaded += 1
            except Exception as e:
                print(f"  Failed: {handle}/{filename}: {e}")
                failed += 1

    print(f"Images: {downloaded} downloaded, {skipped} already existed, {failed} failed")


def process_products(raw_products, images_dir, shop_url):
    """Extract relevant data from raw Shopify product data."""
    processed = []
    base_url = shop_url.rstrip("/")

    for p in raw_products:
        handle = p["handle"]
        images = p.get("images", [])
        variants = p.get("variants", [])
        price = variants[0]["price"] if variants else None

        local_images = []
        for idx in range(len(images)):
            path = os.path.join(images_dir, handle, f"{idx}.jpg")
            if os.path.exists(path):
                local_images.append(path)

        processed.append({
            "handle": handle,
            "title": p.get("title", ""),
            "product_type": p.get("product_type", ""),
            "vendor": p.get("vendor", ""),
            "price": price,
            "tags": p.get("tags", []),
            "image_count": len(images),
            "local_images": local_images,
            "url": f"{base_url}/products/{handle}",
        })

    return processed


def main():
    parser = argparse.ArgumentParser(description="Product Scraper")
    parser.add_argument("--shop-url", help="Shopify store URL (default: from brand.json)")
    parser.add_argument("--output-dir", default="products", help="Output directory")
    parser.add_argument("--skip-images", action="store_true", help="Skip image downloads")
    args = parser.parse_args()

    brand = load_config()
    shop_url = args.shop_url or brand.get("shop_url")
    if not shop_url:
        print("Error: No shop_url provided and none found in brand.json")
        sys.exit(1)

    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Fetch products
    print(f"Fetching products from {shop_url}...")
    raw_products = fetch_all_products(shop_url)
    print(f"Found {len(raw_products)} products.")

    # 2. Download images
    if not args.skip_images:
        print(f"\nDownloading product images (original quality)...")
        os.makedirs(images_dir, exist_ok=True)
        download_product_images(raw_products, images_dir)

    # 3. Process and save
    processed = process_products(raw_products, images_dir, shop_url)

    products_path = os.path.join(output_dir, "products.json")
    with open(products_path, "w") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {products_path}")

    # 4. Summary
    types = {}
    for p in processed:
        t = p["product_type"] or "Uncategorized"
        types[t] = types.get(t, 0) + 1

    print(f"\n{'='*60}")
    print(f"Product Scraper Summary")
    print(f"{'='*60}")
    print(f"Total Products: {len(processed)}")
    print(f"With Images: {sum(1 for p in processed if p['local_images'])}")
    print(f"\nCategories:")
    for t, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
