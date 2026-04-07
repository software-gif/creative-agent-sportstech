#!/usr/bin/env python3
"""Competitor Cloner — Generates EB versions of competitor ad designs.

Takes a competitor ad image as style reference and generates a new version
with EB product and benefits via Gemini image generation.
"""

import argparse
import base64
import json
import os
import sys
import uuid
import time
from datetime import datetime

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

GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_configs():
    """Load brand config and guidelines."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    guidelines_path = os.path.join(PROJECT_ROOT, "branding", "brand_guidelines.json")

    with open(brand_path) as f:
        brand = json.load(f)
    with open(guidelines_path) as f:
        guidelines = json.load(f)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    return brand, guidelines, api_key


def find_product(brand, handle):
    """Find product by handle."""
    for p in brand["products"]:
        if p["handle"] == handle:
            return p
    print(f"Error: Product '{handle}' not found.")
    sys.exit(1)


def encode_image(path):
    """Base64 encode an image file."""
    if not os.path.exists(path):
        print(f"Error: Image not found: {path}")
        return None, None
    ext = os.path.splitext(path)[1].lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, mime


def download_image(url, dest_dir):
    """Download an image from URL to local path."""
    os.makedirs(dest_dir, exist_ok=True)
    filename = f"competitor_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(dest_dir, filename)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(resp.content)
    return filepath


def build_clone_prompt(competitor_image_path, product_image_path, product, brand, benefits, headline, args):
    """Build Gemini API payload for competitor cloning."""

    # Encode both images
    comp_data, comp_mime = encode_image(competitor_image_path)
    prod_data, prod_mime = encode_image(product_image_path)

    if not comp_data:
        print("Error: Could not encode competitor image")
        sys.exit(1)
    if not prod_data:
        print("Error: Could not encode product image")
        sys.exit(1)

    # Build prompt text
    benefits_text = "\n".join(f"  - {b}" for b in benefits[:3])

    prompt_text = f"""You are recreating an advertisement. I'm providing two images:

1. FIRST IMAGE: A competitor's ad design. Use this ONLY as a STYLE and LAYOUT reference.
   Clone the visual concept, layout arrangement, color scheme approach, and overall aesthetic.
   Do NOT copy any text, logos, products, or branding from this image.

2. SECOND IMAGE: The actual product to feature in the new ad. Use this exact product.

CREATE A NEW AD with these specifications:

PRODUCT: {product['name']} by Essentialbag
- Show ONLY the product from the second image
- Display it prominently, similar positioning as in the reference ad

BENEFITS (replace any competitor benefits with these):
{benefits_text}

HEADLINE: "{headline}"

BRAND STYLE:
- Font: Poppins Bold for headlines, Poppins Medium for body
- Brand colors: Dark/Black primary (#282828), Gold accent (#EBC23E)
- Premium, clean, modern feel
- All text in GERMAN

LAYOUT:
- Follow the same general layout concept as the reference ad
- 9:16 format (1080x1920)
- Keep main content in the center 1:1 safe zone area
- Leave space at top for logo (will be added in post-processing)
- Leave space at bottom for social proof elements

MUST INCLUDE:
- The exact product from the second image
- The headline text
- 3 benefits with icons/checkmarks
- A CTA button area

MUST AVOID:
- Any competitor branding, logos, or product
- Any brand logo or wordmark text (will be composited later)
- Inventing product features not listed above
- Cluttered backgrounds
- More than one product

QUALITY: 4K, photorealistic product rendering, clean typography, no AI artifacts.
"""

    # Build API payload
    parts = [
        {"inline_data": {"mime_type": comp_mime, "data": comp_data}},
        {"text": "Above is the REFERENCE ad design. Clone its visual style and layout concept, but NOT its content.\n\n"},
        {"inline_data": {"mime_type": prod_mime, "data": prod_data}},
        {"text": "Above is the PRODUCT to feature in the new ad. Use this exact product.\n\n"},
        {"text": prompt_text}
    ]

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": 0.8,
            "imageConfig": {
                "aspectRatio": "9:16",
                "imageSize": "4K"
            }
        }
    }

    return payload


def call_gemini(api_key, payload, max_retries=3):
    """Call Gemini API and return generated image data."""
    url = GEMINI_URL.format(model=GEMINI_MODEL)

    for attempt in range(max_retries):
        try:
            print(f"  Calling Gemini API (attempt {attempt + 1})...")
            resp = requests.post(url, params={"key": api_key}, json=payload, timeout=180)
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print("  Warning: No candidates")
                continue

            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return inline["data"], inline.get("mimeType") or inline.get("mime_type", "image/png")

            print("  Warning: No image in response")
            for part in parts:
                if "text" in part:
                    print(f"  Gemini: {part['text'][:300]}")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  HTTP Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Competitor Cloner — Clone competitor ads with EB branding")
    parser.add_argument("--competitor-image", required=True, help="Path or URL to competitor ad image")
    parser.add_argument("--product", required=True, help="EB product handle")
    parser.add_argument("--benefits", nargs="*", default=None, help="3 EB benefits (default: from brand.json)")
    parser.add_argument("--headline", default=None, help="Headline text (default: auto from product)")
    parser.add_argument("--keep-headline", action="store_true", help="Adapt competitor headline instead of generating new")
    parser.add_argument("--color", default=None, help="Product color variant")
    parser.add_argument("--num-variants", type=int, default=2, help="Number of variants")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    brand, guidelines, api_key = load_configs()
    product = find_product(brand, args.product)

    # Resolve competitor image
    comp_image = args.competitor_image
    if comp_image.startswith("http"):
        print(f"Downloading competitor image: {comp_image}")
        tmp_dir = os.path.join(PROJECT_ROOT, "competitors", "tmp")
        comp_image = download_image(comp_image, tmp_dir)

    if not os.path.exists(comp_image):
        comp_image = os.path.join(PROJECT_ROOT, comp_image)
    if not os.path.exists(comp_image):
        print(f"Error: Competitor image not found: {args.competitor_image}")
        sys.exit(1)

    # Resolve product image
    product_image = os.path.join(PROJECT_ROOT, "products", "images", product["handle"], "0.jpg")
    if not os.path.exists(product_image):
        # Try png
        product_image = os.path.join(PROJECT_ROOT, "products", "images", product["handle"], "0.png")
    if not os.path.exists(product_image):
        print(f"Error: Product image not found for {product['handle']}")
        sys.exit(1)

    # Benefits
    benefits = args.benefits[:3] if args.benefits else product["benefits"][:3]

    # Headline
    headline = args.headline or f"{product['name']} — Dein smarter Alltagsbegleiter"

    # Output dir
    batch_id = str(uuid.uuid4())[:8]
    output_dir = args.output_dir or os.path.join(PROJECT_ROOT, "creatives", f"clone_{batch_id}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nCompetitor Cloner")
    print(f"  Competitor: {os.path.basename(comp_image)}")
    print(f"  Product: {product['name']}")
    print(f"  Benefits: {benefits}")
    print(f"  Headline: {headline}")
    print(f"  Variants: {args.num_variants}")

    results = []
    for v in range(1, args.num_variants + 1):
        print(f"\n[Variant {v}/{args.num_variants}]")
        payload = build_clone_prompt(comp_image, product_image, product, brand, benefits, headline, args)
        image_data, mime_type = call_gemini(api_key, payload)

        if image_data:
            ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime_type, "png")
            filename = f"clone_{product['handle']}_v{v}.{ext}"
            filepath = os.path.join(output_dir, filename)

            image_bytes = base64.standard_b64decode(image_data)
            with open(filepath, "wb") as f:
                f.write(image_bytes)

            print(f"  Saved: {filename} ({len(image_bytes) / 1024:.0f} KB)")
            results.append({"variant": v, "filename": filename, "path": filepath})
        else:
            print(f"  FAILED: No image generated")

    # Save manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "competitor_image": os.path.basename(comp_image),
        "product": product["handle"],
        "headline": headline,
        "benefits": benefits,
        "results": results
    }
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"DONE: {len(results)}/{args.num_variants} variants generated")
    print(f"Output: {output_dir}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
