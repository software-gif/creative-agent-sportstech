#!/usr/bin/env python3
"""Prompt Generator — Context Loader.

Reads all knowledge files and prints a structured context summary
for Claude to use when generating creative prompts.

Usage:
    python3 .claude/skills/prompt-generator/scripts/context_loader.py [--product HANDLE] [--count N] [--format FORMAT] [--style STYLE] [--type TYPE]

Claude then uses this context to generate unique prompts in the exact
JSON format expected by the Creative Producer.
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))


def load_json(path):
    """Load a JSON file, return empty dict if not found."""
    full_path = os.path.join(PROJECT_ROOT, path)
    if os.path.exists(full_path):
        with open(full_path) as f:
            return json.load(f)
    return {}


def get_product_images(handle):
    """List available product images for a handle."""
    img_dir = os.path.join(PROJECT_ROOT, "products", "images", handle)
    if not os.path.exists(img_dir):
        return []
    return sorted([f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.png', '.webp'))])


def main():
    parser = argparse.ArgumentParser(description="Prompt Generator — Context Loader")
    parser.add_argument("--product", default=None,
                        help="Product handle (default: hero product from brand.json)")
    parser.add_argument("--count", type=int, default=6, help="Number of prompts to generate (default: 6)")
    parser.add_argument("--format", default="mix", choices=["4:5", "9:16", "mix"],
                        help="Format: 4:5 (Feed), 9:16 (Story), or mix (default: mix)")
    parser.add_argument("--style", default="on_brand", choices=["on_brand", "off_brand", "mix"],
                        help="Creative style (default: on_brand)")
    parser.add_argument("--type", default="lifestyle", choices=["lifestyle", "product_static", "mix"],
                        help="Creative type (default: lifestyle)")
    parser.add_argument("--season", default="sommer", help="Season (default: sommer)")
    parser.add_argument("--angle", default=None, help="Specific angle to use (default: random from angles.json)")
    args = parser.parse_args()

    # Load all knowledge
    product_knowledge = load_json("branding/product_knowledge.json")
    lifestyle_variance = load_json("branding/lifestyle_variance.json")
    brand = load_json("branding/brand.json")
    brand_guidelines = load_json("branding/brand_guidelines.json")
    meta_bp = load_json("branding/meta_creative_best_practices.json")
    angles = load_json("angles/angles.json")

    # Get product-specific knowledge
    products = product_knowledge.get("products", {})
    product_info = products.get(args.product, {})

    # Get available images
    images = get_product_images(args.product)

    # Resolve default product from brand.json hero if not specified
    if args.product is None:
        priority = brand.get("priority_products", {})
        args.product = priority.get("hero", "")
        if not args.product:
            products_list = brand.get("products", [])
            args.product = products_list[0]["handle"] if products_list else "unknown"

    # Determine product_category from handle
    # Build category map dynamically from brand.json products
    category_map = {}
    for p in brand.get("products", []):
        handle = p.get("handle", "")
        # Use handle as category, replacing hyphens with underscores
        category_map[handle] = handle.replace("-", "_")
    product_category = category_map.get(args.product, args.product.replace("-", "_"))

    # Print context for Claude
    print("=" * 70)
    print("PROMPT GENERATOR — CONTEXT FOR CLAUDE")
    print("=" * 70)

    print(f"\n📋 TASK: Generate {args.count} unique creative prompts")
    print(f"   Product: {product_info.get('name', args.product)}")
    print(f"   Category: {product_category}")
    print(f"   Format: {args.format}")
    print(f"   Style: {args.style}")
    print(f"   Type: {args.type}")
    print(f"   Season: {args.season}")
    if args.angle:
        print(f"   Angle: {args.angle}")
    print(f"   Product image: products/images/{args.product}/0.jpg")
    print(f"   Available images: {', '.join(images)}")

    print(f"\n{'─' * 70}")
    print("📦 PRODUCT KNOWLEDGE:")
    print(json.dumps(product_info, indent=2, ensure_ascii=False)[:3000])

    print(f"\n{'─' * 70}")
    print("🎭 VARIANCE POOLS:")
    print(f"   Models: {len(lifestyle_variance.get('models', []))}")
    for m in lifestyle_variance.get("models", []):
        print(f"     - {m['id']}: {m['description']}")
    print(f"   Poses: {len(lifestyle_variance.get('poses', {}))}")
    for k, v in lifestyle_variance.get("poses", {}).items():
        print(f"     - {k}: {v['description']}")
    print(f"   Settings: {len(lifestyle_variance.get('settings', {}))}")
    for k, v in lifestyle_variance.get("settings", {}).items():
        print(f"     - {k}: {v.get('prompt_snippet', '')[:60]}...")
    print(f"   Outfits: {len(lifestyle_variance.get('outfits_summer', []))}")

    print(f"\n{'─' * 70}")
    print("🎯 ANGLES:")
    angle_data = angles.get("angles", {})
    if args.angle and args.angle in angle_data:
        angle_info = {args.angle: angle_data[args.angle]}
    else:
        angle_info = angle_data
    for angle_name, angle_detail in angle_info.items():
        print(f"\n   {angle_name}:")
        for sub in angle_detail.get("sub_angles", []):
            hooks = sub.get("hook_suggestions", [])
            hook_preview = hooks[0] if hooks else ""
            print(f"     - {sub['name']}: {hook_preview}")

    print(f"\n{'─' * 70}")
    print("🎨 BRAND COLORS:")
    colors = brand_guidelines.get("colors", {})
    for k, v in colors.items():
        if not k.endswith("_notes"):
            print(f"   {k}: {v}")

    print(f"\n{'─' * 70}")
    print("📏 META BEST PRACTICES:")
    rules = meta_bp.get("prompt_injection_rules", {})
    for r in rules.get("always_include", []):
        print(f"   ✓ {r}")

    print(f"\n{'─' * 70}")
    print("🎯 TARGET AUDIENCE:")
    ta = brand.get("target_audience", {})
    print(f"   {ta.get('description', '')}")

    print(f"\n{'=' * 70}")
    print("INSTRUCTIONS FOR CLAUDE:")
    print("=" * 70)
    print(f"""
Now generate {args.count} unique creative prompts as a JSON array.

Each prompt must follow the EXACT schema used by the Creative Producer:
- product_image: "products/images/{args.product}/0.jpg"
- meta: angle, sub_angle, variant, scene_type, creative_style, creative_type, season, environment, product_category, generation_mode, format, resolution
- canvas: background, lighting, color_mood
- layout: zones
- product: display_mode, position, scale, rotation, perspective, shadow
- text_overlays: [{{"role": "headline", "content": "...", "position": ..., "style": ...}}, {{"role": "subheadline", ...}}]
- visual_elements: badges
- brand_elements: logo, trust_signals
- generation_instructions: style_reference, must_include, must_avoid, quality_notes, text_rendering_notes

CRITICAL RULES:
1. Every prompt must have a UNIQUE model description (age, hair, build — all different)
2. Every prompt must have a DIFFERENT pose from the proven poses above
3. Every prompt must have a DIFFERENT setting/environment
4. Every prompt must have a DIFFERENT headline/hook
5. Product accuracy instructions must be in EVERY prompt
6. Resolutions: 4:5 = 1440x1800, 9:16 = 1440x2560
7. product_category: "{product_category}"
8. All text in correct German with umlauts (ä, ö, ü, ß)
9. Each text line rendered EXACTLY ONCE — no duplicates
10. ONLY proven poses — no weird body positions

Save the output as: creatives/prompts.json
Then run: python3 .claude/skills/creative-producer/scripts/main.py --prompts-file creatives/prompts.json
""")


if __name__ == "__main__":
    main()
