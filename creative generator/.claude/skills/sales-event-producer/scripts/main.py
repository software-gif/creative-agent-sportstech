#!/usr/bin/env python3
"""Sales Event Producer — Generates Sales Event Static Ads.

Builds structured JSON prompts for sales event creatives and passes them
to the creative-producer engine for Gemini generation + Supabase upload.
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))


def load_configs():
    """Load brand, guidelines, and sales events configs."""
    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    guidelines_path = os.path.join(PROJECT_ROOT, "branding", "brand_guidelines.json")
    events_path = os.path.join(PROJECT_ROOT, "config", "sales_events.json")

    for p, name in [(brand_path, "brand.json"), (guidelines_path, "brand_guidelines.json"), (events_path, "sales_events.json")]:
        if not os.path.exists(p):
            print(f"Error: {name} not found at {p}")
            sys.exit(1)

    with open(brand_path) as f:
        brand = json.load(f)
    with open(guidelines_path) as f:
        guidelines = json.load(f)
    with open(events_path) as f:
        events = json.load(f)

    return brand, guidelines, events


def find_product(brand, product_handle):
    """Find product by handle in brand.json."""
    for p in brand["products"]:
        if p["handle"] == product_handle:
            return p
    print(f"Error: Product '{product_handle}' not found. Available: {[p['handle'] for p in brand['products']]}")
    sys.exit(1)


def find_event(events, event_id):
    """Find event by ID in sales_events.json."""
    for e in events["events"]:
        if e["id"] == event_id:
            return e
    print(f"Error: Event '{event_id}' not found. Available: {[e['id'] for e in events['events']]}")
    sys.exit(1)


def build_prompt(product, event, guidelines, brand, args, variant_num):
    """Build a single creative-producer compatible JSON prompt."""
    # Determine background style
    is_clean = args.background_style == "clean"
    event_colors = event["colors"]

    if is_clean:
        bg_desc = event.get("clean_background_hint", "Clean minimalist background")
        bg_type = "solid_color"
    else:
        bg_desc = event.get("themed_background_hint", "Event-themed background")
        bg_type = "photo_scene"

    # Select benefits (3)
    if args.benefits:
        benefits = args.benefits[:3]
    else:
        benefits = product["benefits"][:3]

    # Headline
    headline = args.headline or f"{event['name']} Sale"

    # Sub-headline
    sub_headline = args.sub_headline or "Bis zu 50% Rabatt"

    # CTA
    cta = args.cta or "Jetzt sparen"

    # Product image path (first image, color variants use same freisteller)
    product_image = f"products/images/{product['handle']}/0.jpg"

    # Build the prompt JSON (creative-producer compatible)
    prompt = {
        "meta": {
            "angle": "Offer",
            "sub_angle": f"{event['name']} — {product['name']}",
            "variant": variant_num,
            "scene_type": "positive",
            "format": "9:16",
            "resolution": {"width": 1080, "height": 1920}
        },
        "canvas": {
            "background": {
                "type": bg_type,
                "primary_color": event_colors["primary"],
                "secondary_color": event_colors.get("secondary"),
                "gradient_direction": "top_to_bottom" if not is_clean else None,
                "scene_description": bg_desc if bg_type == "photo_scene" else None,
                "texture_description": None,
                "opacity": 1.0
            },
            "lighting": {
                "type": "studio" if is_clean else "soft_natural",
                "direction": "frontal",
                "warmth": "warm",
                "intensity": "medium",
                "shadows": "subtle"
            },
            "color_mood": {
                "palette": [event_colors["primary"], event_colors["secondary"], event_colors["accent"], "#FFFFFF"],
                "mood": f"{event['name']} sale, premium, urgent",
                "saturation": "vibrant" if not is_clean else "natural",
                "contrast": "high"
            }
        },
        "layout": {
            "type": "three_zone_vertical",
            "zones": {
                "top": {
                    "height_percent": 25,
                    "content": "headline",
                    "background": None
                },
                "middle": {
                    "height_percent": 45,
                    "content": "product_hero"
                },
                "bottom": {
                    "height_percent": 30,
                    "content": "cta_price"
                }
            },
            "margins": {"outer": "medium", "inner_gap": "normal"},
            "alignment": "center"
        },
        "product": {
            "source_image": product_image,
            "display_mode": "single_hero",
            "position": {"x": "center", "y": "center"},
            "scale": 0.55,
            "rotation": 0,
            "perspective": "slight_angle",
            "shadow": {"type": "drop_shadow", "intensity": "medium", "direction": "below"},
            "surface": None,
            "decorative_elements": []
        },
        "text_overlays": [
            {
                "role": "headline",
                "content": headline,
                "position": {"x": "center", "y": "upper_third"},
                "style": {
                    "font_family": "sans_bold",
                    "font_weight": "bold",
                    "font_size": "xl",
                    "color": "#FFFFFF" if event_colors["primary"] in ("#000000", "#212121", "#1A1A1A", "#0D1B2A") else event_colors["primary"],
                    "letter_spacing": "normal",
                    "text_transform": "none",
                    "line_height": 1.2,
                    "max_width_percent": 85,
                    "text_align": "center"
                },
                "decoration": {"background": None, "shadow": "subtle"},
                "emphasis_words": [],
                "emphasis_style": {}
            },
            {
                "role": "subheadline",
                "content": sub_headline,
                "position": {"x": "center", "y": "lower_third"},
                "style": {
                    "font_family": "sans_modern",
                    "font_weight": "semibold",
                    "font_size": "lg",
                    "color": event_colors.get("accent", "#FFD700"),
                    "letter_spacing": "normal",
                    "text_transform": "none",
                    "line_height": 1.3,
                    "max_width_percent": 80,
                    "text_align": "center"
                },
                "decoration": {},
                "emphasis_words": [],
                "emphasis_style": {}
            },
            {
                "role": "cta",
                "content": cta,
                "position": {"x": "center", "y": "lower_third", "offset_y_percent": 5},
                "style": {
                    "font_family": "sans_bold",
                    "font_weight": "bold",
                    "font_size": "md",
                    "color": "#FFFFFF",
                    "letter_spacing": "wide",
                    "text_transform": "uppercase",
                    "line_height": 1.0,
                    "max_width_percent": 60,
                    "text_align": "center"
                },
                "decoration": {
                    "background": event_colors.get("accent", "#EBC23E"),
                    "background_padding": "normal",
                    "background_shape": "rounded"
                },
                "emphasis_words": [],
                "emphasis_style": {}
            }
        ],
        "visual_elements": {
            "badges": [],
            "dividers": [],
            "icons": ["checkmark"] * min(len(benefits), 3),
            "shapes": []
        },
        "brand_elements": {
            "logo": {
                "visible": True,
                "position": "top_center",
                "size": "medium",
                "color_mode": "auto"
            },
            "brand_colors_usage": f"Event-Farben ({event['name']}): {event_colors['primary']}, {event_colors['accent']}. Brand-Akzent für CTA.",
            "trust_signals": brand.get("trust_signals", [])[:2]
        },
        "generation_instructions": {
            "style_reference": f"Premium {event['name']} sale ad for smart accessories brand. Clean, modern, product-focused. Font: Poppins Bold. {event['name']} seasonal elements {'minimal' if is_clean else 'prominent'}.",
            "must_include": [
                f"The {product['name']} product clearly visible",
                f"Headline text: \"{headline}\"",
                f"3 benefits with checkmark icons: {', '.join(benefits[:3])}",
                f"CTA button: \"{cta}\"",
                f"Sub-headline: \"{sub_headline}\"",
                "Safe zone layout: main content in center 1:1 area of 9:16 format"
            ],
            "must_avoid": [
                "Any brand logo text — will be composited in post-processing",
                "Cluttered or messy backgrounds",
                "More than one product",
                "Inventing product features not listed",
                "Content outside the 1:1 safe zone area (keep main info centered)"
            ],
            "quality_notes": "4K quality, no watermarks, no AI artifacts, photorealistic product rendering. Poppins Bold font for all text.",
            "text_rendering_notes": "All German text correctly spelled. Clean typography. Benefits should have small checkmark or icon before each. No overlapping text."
        }
    }

    # Add benefits as additional text overlays
    for i, benefit in enumerate(benefits[:3]):
        prompt["text_overlays"].append({
            "role": "badge",
            "content": f"✓ {benefit}",
            "position": {"x": "center", "y": "lower_third", "offset_y_percent": -(10 + i * 5)},
            "style": {
                "font_family": "sans_modern",
                "font_weight": "medium",
                "font_size": "sm",
                "color": "#FFFFFF",
                "text_align": "left",
                "max_width_percent": 75,
                "letter_spacing": "normal",
                "text_transform": "none",
                "line_height": 1.4
            },
            "decoration": {},
            "emphasis_words": [],
            "emphasis_style": {}
        })

    return {
        "prompt": prompt,
        "product_image": product_image
    }


def main():
    parser = argparse.ArgumentParser(description="Sales Event Producer — Build prompts for sales event creatives")
    parser.add_argument("--product", required=True, help="Product handle (smart-wallet-3-0, tracker-karte, essential-sling-bag)")
    parser.add_argument("--event", required=True, help="Event ID from sales_events.json")
    parser.add_argument("--background-style", choices=["clean", "themed"], default="clean", help="Background style")
    parser.add_argument("--headline", default=None, help="Fixed headline text")
    parser.add_argument("--sub-headline", default=None, help="Offer/sub-headline text")
    parser.add_argument("--cta", default=None, help="CTA button text")
    parser.add_argument("--benefits", nargs=3, default=None, help="3 benefits to show")
    parser.add_argument("--color", default=None, help="Product color variant")
    parser.add_argument("--num-variants", type=int, default=3, help="Number of variants to generate")
    parser.add_argument("--output", default=None, help="Output path for prompts JSON")
    args = parser.parse_args()

    brand, guidelines, events_config = load_configs()
    product = find_product(brand, args.product)
    event = find_event(events_config, args.event)

    print(f"Sales Event Producer")
    print(f"  Product: {product['name']}")
    print(f"  Event: {event['name']}")
    print(f"  Style: {args.background_style}")
    print(f"  Variants: {args.num_variants}")

    # Build prompts for each variant
    prompts = []
    for v in range(1, args.num_variants + 1):
        prompt_data = build_prompt(product, event, guidelines, brand, args, v)
        prompts.append(prompt_data)

    # Save prompts JSON
    output_path = args.output or os.path.join(PROJECT_ROOT, "creatives", f"sales_{event['id']}_{product['handle']}_prompts.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

    print(f"\nPrompts saved: {output_path}")
    print(f"Run creative-producer with: python3 .claude/skills/creative-producer/scripts/main.py --prompts-file {os.path.relpath(output_path, PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
