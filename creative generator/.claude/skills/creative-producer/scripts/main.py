#!/usr/bin/env python3
"""Creative Producer — Generates Static Ads via Gemini 3.1 Flash Image Generation.

Uploads results directly to Supabase Storage and tracks creatives in the database.
"""

import argparse
import atexit
import base64
import io
import json
import os
import signal
import random
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-image-preview")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Process lock file to prevent concurrent runs
LOCK_FILE = os.path.join(PROJECT_ROOT, "creatives", ".generation.lock")


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

class SupabaseClient:
    """Minimal Supabase REST + Storage client using requests."""

    def __init__(self, url, anon_key, service_role_key=None):
        self.url = url.rstrip("/")
        self.storage_url = f"{self.url}/storage/v1"
        self.rest_url = f"{self.url}/rest/v1"
        # Use service role key if available (bypasses RLS), otherwise anon key
        self.key = service_role_key or anon_key
        self.headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def insert_creative(self, row):
        """INSERT into creatives table, return the inserted row."""
        resp = requests.post(
            f"{self.rest_url}/creatives",
            headers=self.headers,
            json=row,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()[0]

    def update_creative(self, creative_id, updates):
        """UPDATE a creative row by id."""
        resp = requests.patch(
            f"{self.rest_url}/creatives?id=eq.{creative_id}",
            headers=self.headers,
            json=updates,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, bucket, path, file_bytes, content_type="image/png"):
        """Upload a file to Supabase Storage."""
        headers = {
            "apikey": self.headers["apikey"],
            "Authorization": self.headers["Authorization"],
            "Content-Type": content_type,
        }
        resp = requests.post(
            f"{self.storage_url}/object/{bucket}/{path}",
            headers=headers,
            data=file_bytes,
            timeout=60,
        )
        # If file exists, try upsert (409 Conflict or 400 Bad Request)
        if resp.status_code in (400, 409):
            headers["x-upsert"] = "true"
            resp = requests.post(
                f"{self.storage_url}/object/{bucket}/{path}",
                headers=headers,
                data=file_bytes,
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json()

    def get_public_url(self, bucket, path):
        """Get the public URL for a storage object."""
        return f"{self.url}/storage/v1/object/public/{bucket}/{path}"

    def get_single_brand_id(self):
        """Fetch the first (only) brand from the brands table."""
        resp = requests.get(
            f"{self.rest_url}/brands?select=id&limit=1",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            print("Error: No brand found in brands table. Insert one first:")
            print("  INSERT INTO brands (name) VALUES ('YourBrand');")
            sys.exit(1)
        return rows[0]["id"]


def init_supabase():
    """Initialize Supabase client from env vars."""
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not anon_key:
        print("Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        sys.exit(1)

    return SupabaseClient(url, anon_key, service_key)


# ---------------------------------------------------------------------------
# Process lock
# ---------------------------------------------------------------------------

def acquire_process_lock():
    """Prevent multiple generation processes from running simultaneously."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                lock_data = json.load(f)
            pid = lock_data.get("pid", 0)
            try:
                os.kill(pid, 0)
                print(f"ERROR: Another generation is already running (PID {pid}).")
                print(f"If this is wrong, delete {LOCK_FILE}")
                sys.exit(1)
            except OSError:
                print(f"Stale lock from dead process {pid} — cleaning up")
                os.unlink(LOCK_FILE)
        except (json.JSONDecodeError, KeyError):
            os.unlink(LOCK_FILE)

    with open(LOCK_FILE, "w") as f:
        json.dump({"pid": os.getpid(), "started": datetime.now().isoformat()}, f)


def release_process_lock():
    """Release the process lock."""
    try:
        os.unlink(LOCK_FILE)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Image encoding + Gemini prompt building
# ---------------------------------------------------------------------------

def load_config():
    """Load .env and return API key."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("Error: GEMINI_API_KEY not set in .env")
        sys.exit(1)
    return api_key


def encode_image(image_path):
    """Read and base64-encode an image file."""
    if not os.path.exists(image_path):
        print(f"Warning: Image not found: {image_path}")
        return None, None

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, mime_type


def load_lifestyle_variance():
    """Load lifestyle variance pool for diverse creative generation."""
    lv_path = os.path.join(PROJECT_ROOT, "branding", "lifestyle_variance.json")
    if os.path.exists(lv_path):
        with open(lv_path) as f:
            return json.load(f)
    return None


def inject_lifestyle_variance(ad_prompt_json):
    """Auto-inject variance into lifestyle prompts for model/pose/setting diversity."""
    meta = ad_prompt_json.get("meta", {})
    if meta.get("creative_type") != "lifestyle":
        return ""

    lv = load_lifestyle_variance()
    if not lv:
        return ""

    # Pick random model
    model = random.choice(lv.get("models", []))
    model_text = model.get("prompt_snippet", "")

    # Pick random pose
    poses = lv.get("poses", {})
    pose_key = random.choice(list(poses.keys()))
    pose = poses[pose_key]
    pose_text = pose.get("prompt_snippet", "")

    # Pick random outfit
    outfits = lv.get("outfits_summer", [])
    outfit = random.choice(outfits) if outfits else ""

    # Pick random setting based on environment
    env = meta.get("environment", "wohnzimmer")
    settings = lv.get("settings", {})
    env_settings = [k for k in settings if k.startswith(env or "wohnzimmer")]
    if not env_settings:
        env_settings = list(settings.keys())
    setting_key = random.choice(env_settings)
    setting = settings[setting_key]
    setting_text = setting.get("prompt_snippet", "")
    furniture = setting.get("furniture", "a sofa")

    # Replace {setting_furniture} placeholder in pose
    pose_text = pose_text.replace("{setting_furniture}", furniture)

    variance_text = f"""
LIFESTYLE VARIANCE (use these SPECIFIC details for this creative — make it UNIQUE):
- MODEL: {model_text}
- POSE: {pose_text}
- OUTFIT: {outfit}
- SETTING: {setting_text}
- IMPORTANT: Make this person look UNIQUE and DIFFERENT from other creatives. Vary hair, face, body type, expression, pose.
"""
    print(f"  Variance: {model.get('id', '?')}, {pose_key}, {setting_key}, {outfit[:30]}...")
    return variance_text


def build_gemini_prompt(ad_prompt_json, product_image_path):
    """Build the Gemini API request payload from a JSON prompt + product image."""

    meta = ad_prompt_json["meta"]
    canvas = ad_prompt_json["canvas"]
    layout = ad_prompt_json["layout"]
    product = ad_prompt_json["product"]
    text_overlays = ad_prompt_json["text_overlays"]
    visual_elements = ad_prompt_json.get("visual_elements", {})
    brand_elements = ad_prompt_json.get("brand_elements", {})
    gen_instructions = ad_prompt_json["generation_instructions"]

    # --- SCENE TYPE GUARD ---
    scene_type = meta.get("scene_type", "positive")
    is_negative_scene = scene_type == "negative"

    if is_negative_scene:
        image_data = None
        mime_type = None
        print(f"  ⚠ NEGATIVE SCENE: Product image BLOCKED (scene_type=negative)")
    else:
        image_data, mime_type = encode_image(product_image_path)

    logo_visible = brand_elements.get('logo', {}).get('visible', False)

    # Load product details from product_knowledge.json (primary) or brand.json (fallback)
    product_detail_text = ""
    try:
        pk_path = os.path.join(PROJECT_ROOT, "branding", "product_knowledge.json")
        brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
        if os.path.exists(pk_path):
            with open(pk_path) as pf:
                pk_data = json.load(pf)
            product_details = pk_data.get("products", {})
        elif os.path.exists(brand_path):
            with open(brand_path) as bf:
                brand_data = json.load(bf)
            product_details = brand_data.get("product_details", {})
            # Try to match product from image path
            for handle, details in product_details.items():
                if handle in product_image_path:
                    # Support both product_knowledge.json and brand.json formats
                    appearance = details.get('appearance', {})
                    how_it_works = details.get('how_it_works', {})
                    size_refs = details.get('size_references', {})
                    ai_rules = details.get('ai_generation_rules', {})
                    usage_poses = details.get('correct_usage_poses', details.get('usage_poses', []))

                    # Build appearance text
                    if isinstance(appearance, dict):
                        app_text = appearance.get('summary', details.get('exact_appearance', ''))
                        two_tone = appearance.get('two_tone_wood', {})
                        if two_tone:
                            app_text += f"\n  HANDLES: {two_tone.get('handles', '')}"
                            app_text += f"\n  MIDDLE: {two_tone.get('middle', '')}"
                        if appearance.get('grooves'):
                            app_text += f"\n  GROOVES: {appearance['grooves']}"
                        if appearance.get('flex'):
                            app_text += f"\n  FLEX: {appearance['flex']}"
                        dims = f"{appearance.get('length', '')} lang, {appearance.get('diameter', '')} Durchmesser"
                    else:
                        app_text = details.get('exact_appearance', '')
                        dims = details.get('dimensions', '')

                    # Build size reference
                    size_text = ""
                    if isinstance(size_refs, dict):
                        for k, v in size_refs.items():
                            size_text += f"\n  - {v}"
                    else:
                        size_text = details.get('size_reference', '')

                    # Build usage poses
                    pose_lines = []
                    for pose in usage_poses:
                        if isinstance(pose, dict):
                            name = pose.get('name', pose.get('body_part', ''))
                            desc = pose.get('description', pose.get('position', ''))
                            pose_lines.append(f"  - {name}: {desc}")
                    usage_text = "\n".join(pose_lines) if pose_lines else ""

                    # Build must_avoid from ai_generation_rules or common_ai_mistakes
                    mistakes = ai_rules.get('must_avoid', details.get('common_ai_mistakes', []))
                    must_match = ai_rules.get('must_match', [])

                    product_detail_text = f"""
CRITICAL PRODUCT REFERENCE — you MUST match this exactly:
- Product: {details.get('name', '')}
- Appearance: {app_text}
- Dimensions: {dims}
- Size references: {size_text}

HOW THE PRODUCT IS USED:
- Principle: {how_it_works.get('principle', '')}
- Grip: {how_it_works.get('grip', '')}
- Motion: {how_it_works.get('motion', '')}
- Surface contact: {how_it_works.get('surface_contact', '')}
- Flex in action: {how_it_works.get('flex_in_action', how_it_works.get('flex_feature', ''))}

CORRECT USAGE POSES:
{usage_text}

MUST MATCH (mandatory product features):
{chr(10).join('- ' + m for m in must_match)}

COMMON AI MISTAKES TO AVOID:
{chr(10).join('- ' + m for m in mistakes)}

SPELLING: All German text MUST be spelled correctly. Double-check every word.
"""
                    break
    except Exception:
        pass

    # Load Do's & Don'ts from brand.json (health claims etc.)
    dos_donts_text = ""
    try:
        brand_path_dd = os.path.join(PROJECT_ROOT, "branding", "brand.json")
        if os.path.exists(brand_path_dd):
            with open(brand_path_dd) as ddf:
                brand_dd = json.load(ddf)
            donts = brand_dd.get("dos_and_donts", {}).get("donts", [])
            if donts:
                dos_donts_text = "\nHEALTH CLAIM RULES (MANDATORY — legal requirement):\n"
                dos_donts_text += "\n".join(f"- {d}" for d in donts)
                dos_donts_text += "\nUse ONLY: 'fördert', 'unterstützt', 'kann helfen', 'Wohlbefinden'. NEVER: 'heilt', 'beseitigt', 'therapiert', 'Schmerzfrei' (use 'Entspannung' instead).\n"
    except Exception:
        pass

    # Load Meta Creative Best Practices
    meta_bp_text = ""
    try:
        bp_path = os.path.join(PROJECT_ROOT, "branding", "meta_creative_best_practices.json")
        if os.path.exists(bp_path):
            with open(bp_path) as bpf:
                bp_data = json.load(bpf)
            rules = bp_data.get("prompt_injection_rules", {})
            always = rules.get("always_include", [])
            creative_style = meta.get("creative_style", "on_brand")
            style_rules = rules.get(f"for_{creative_style}", [])
            all_rules = always + style_rules
            if all_rules:
                meta_bp_text = "\nMETA AD PERFORMANCE RULES (follow these for maximum ad performance):\n"
                meta_bp_text += "\n".join(f"- {r}" for r in all_rules) + "\n"
    except Exception:
        pass

    # Inject lifestyle variance for model/pose/setting diversity
    variance_text = inject_lifestyle_variance(ad_prompt_json)

    prompt_text = f"""Generate a professional static advertisement image with the following exact specifications.

FORMAT: {meta['format']} aspect ratio, {meta['resolution']['width']}x{meta['resolution']['height']} pixels.
{product_detail_text}{dos_donts_text}{meta_bp_text}{variance_text}
STYLE: {gen_instructions['style_reference']}

BACKGROUND:
- Type: {canvas['background']['type']}
- Primary color: {canvas['background']['primary_color']}"""

    if canvas['background'].get('secondary_color'):
        prompt_text += f"\n- Secondary color: {canvas['background']['secondary_color']}"
        prompt_text += f"\n- Gradient direction: {canvas['background'].get('gradient_direction', 'top_to_bottom')}"
    if canvas['background'].get('scene_description'):
        prompt_text += f"\n- Scene: {canvas['background']['scene_description']}"
    if canvas['background'].get('texture_description'):
        prompt_text += f"\n- Texture: {canvas['background']['texture_description']}"

    prompt_text += f"""

LIGHTING:
- Type: {canvas['lighting']['type']}
- Direction: {canvas['lighting']['direction']}
- Warmth: {canvas['lighting']['warmth']}
- Intensity: {canvas['lighting']['intensity']}
- Shadows: {canvas['lighting']['shadows']}

COLOR MOOD:
- Palette: {', '.join(canvas['color_mood']['palette'])}
- Mood: {canvas['color_mood']['mood']}
- Saturation: {canvas['color_mood']['saturation']}
- Contrast: {canvas['color_mood']['contrast']}

LAYOUT:
- Type: {layout['type']}
- Top zone ({layout['zones']['top']['height_percent']}%): {layout['zones']['top']['content']}"""

    if layout['zones']['top'].get('background'):
        prompt_text += f" on {layout['zones']['top']['background']} background"

    prompt_text += f"""
- Middle zone ({layout['zones']['middle']['height_percent']}%): {layout['zones']['middle']['content']}
- Bottom zone ({layout['zones']['bottom']['height_percent']}%): {layout['zones']['bottom']['content']}
- Alignment: {layout['alignment']}
- Outer margins: {layout['margins']['outer']}

PRODUCT PLACEMENT:"""

    if is_negative_scene:
        prompt_text += f"""
IMPORTANT: This is a NEGATIVE/PROBLEM scene. Do NOT show the advertised product.
- Show ONLY generic, unbranded, no-name products — no visible brand names, logos, or recognizable designs.
- The product shown should look cheap, generic, or worn out — representing the COMPETITOR/PROBLEM, not our brand.
- Position: {product['position']['x']} horizontally, {product['position']['y']} vertically
- Scale: {product['scale']} (relative to canvas)
- Perspective: {product['perspective']}
"""
    else:
        prompt_text += f"""
- Display the provided product image as: {product['display_mode']}
- Position: {product['position']['x']} horizontally, {product['position']['y']} vertically
- Scale: {product['scale']} (relative to canvas)
- Rotation: {product['rotation']} degrees
- Perspective: {product['perspective']}
- Shadow: {product['shadow']['type']}, {product['shadow']['intensity']} intensity
"""

    if not is_negative_scene and product.get('surface'):
        prompt_text += f"- Surface: {product['surface']}\n"
    if not is_negative_scene and product.get('decorative_elements'):
        elements = [e for e in product['decorative_elements'] if e]
        if elements:
            prompt_text += f"- Decorative elements: {', '.join(elements)}\n"

    prompt_text += "\nTEXT OVERLAYS (render ONLY the text content below — correct German spelling, clean typography):\n"
    prompt_text += "CRITICAL RULES FOR TEXT:\n"
    prompt_text += "1. Only render the actual text content provided below. Do NOT render font names, sizes, colors, CSS values, or technical specifications.\n"
    prompt_text += "2. Render each text EXACTLY ONCE. Do NOT duplicate any text line. If you see 'Dieser Holzstab hat alles verändert', render it ONE time only.\n"
    prompt_text += "3. Use correct German characters: ä, ö, ü, ß — NOT ae, oe, ue.\n"
    for i, overlay in enumerate(text_overlays, 1):
        style = overlay['style']
        font_desc = style['font_family']
        if 'italic' in str(style.get('font_weight', '')):
            font_desc += " italic"
        if 'bold' in str(style.get('font_weight', '')):
            font_desc += " bold"

        size_desc = "large" if "4" in str(style.get('font_size', '')) else "medium" if "2" in str(style.get('font_size', '')) else "small"

        prompt_text += f"\n  Text {i} ({overlay['role']}):\n"
        prompt_text += f"  - Render this text: \"{overlay['content']}\"\n"
        prompt_text += f"  - Place at: {overlay['position']['x']}, {overlay['position']['y']}\n"
        prompt_text += f"  - Style: {font_desc}, {size_desc} size, {style['color']} color\n"
        prompt_text += f"  - Alignment: {style['text_align']}\n"

        if overlay.get('emphasis_words'):
            words = [w for w in overlay['emphasis_words'] if w]
            if words:
                emphasis_color = overlay.get('emphasis_style', {}).get('color', '')
                prompt_text += f"  - Make these words stand out: {', '.join(words)}"
                if emphasis_color:
                    prompt_text += f" (in {emphasis_color})"
                prompt_text += "\n"

    badges = visual_elements.get('badges', [])
    if badges:
        prompt_text += "\nBADGES/BUTTONS:\n"
        for badge in badges:
            prompt_text += f"  - {badge['type']}: \"{badge['text']}\" at {badge['position']['x']},{badge['position']['y']}"
            prompt_text += f" — {badge['style']['shape']} shape, bg:{badge['style']['background_color']}, text:{badge['style']['text_color']}\n"

    if logo_visible:
        logo = brand_elements['logo']
        prompt_text += f"\nLOGO SPACE: Leave clean empty space at {logo['position']} (approximately 15% width, 4% height) for logo placement in post-processing. Do NOT render any logo text or wordmark — the real logo will be composited later.\n"

    if brand_elements.get('trust_signals'):
        signals = [s for s in brand_elements['trust_signals'] if s]
        if signals:
            prompt_text += f"\nTRUST SIGNALS (small text at bottom): {' | '.join(signals)}\n"

    must_include = [m for m in gen_instructions['must_include'] if 'logo' not in m.lower() and 'wordmark' not in m.lower()]
    prompt_text += f"\nMUST INCLUDE: {', '.join(must_include)}\n"
    must_avoid = gen_instructions['must_avoid'] + [
        "Do NOT render any brand logo or wordmark text — it will be added in post-processing",
        "dirty or messy backgrounds, crumbs, dirty socks, cluttered surfaces, unwashed dishes — keep backgrounds clean and tidy even for casual/authentic styles",
        "inventing product colors or variants that don't exist — only show the exact product provided",
    ]
    if is_negative_scene:
        must_avoid += [
            "ANY branded product, ANY recognizable brand name or logo — this is a negative/problem scene, show ONLY generic unbranded items",
            "ANY reference to the advertised brand — the product shown must look like a cheap competitor, NOT the advertised product",
        ]
    prompt_text += f"MUST AVOID: {', '.join(must_avoid)}\n"
    prompt_text += f"\nQUALITY: {gen_instructions['quality_notes']}\n"
    prompt_text += f"TEXT RENDERING: {gen_instructions['text_rendering_notes']}\n"

    parts = []
    if image_data and not is_negative_scene:
        # Multi-reference system: send up to 5 product images for maximum accuracy
        reference_descriptions = [
            ("REFERENCE 1 — PRODUCT OVERVIEW: This shows the EXACT product. Note TWO DIFFERENT WOOD COLORS: DARK chocolate-brown handles on both ends + LIGHT honey/cream grooved segments in the middle. Proportions: 1/5 dark — 3/5 light — 1/5 dark. SLIM stick (3-4cm diameter, 52cm long)."),
        ]
        parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})
        parts.append({"text": reference_descriptions[0] + "\n\n"})

        # Add additional reference images from product directory
        product_dir = os.path.dirname(product_image_path)
        if not os.path.isabs(product_dir):
            product_dir = os.path.join(PROJECT_ROOT, product_dir)

        extra_refs = [
            ("3.jpg", "REFERENCE 2 — FLEX/BEND VIEW: Shows the stick BENDING. Note the clear TWO-TONE contrast: DARK handles vs LIGHT grooved middle. This is the key visual feature."),
            ("2.jpg", "REFERENCE 3 — USAGE ON THIGH: Shows correct usage on a thigh. Note the SIZE relative to a human leg — the stick is about as long as the distance from hip to knee. Both hands grip the DARK handles."),
            ("1.jpg", "REFERENCE 4 — USAGE ON NECK: Shows correct neck application from BEHIND. Both hands on DARK handles, grooved middle on bare neck. Note proportions vs human shoulders."),
            ("4.jpg", "REFERENCE 5 — USAGE CONTEXT: Shows the product being used in a real setting. Note the slim proportions and two-tone wood colors."),
        ]

        ref_count = 1
        for ref_file, ref_desc in extra_refs:
            ref_path = os.path.join(product_dir, ref_file)
            if os.path.exists(ref_path) and ref_count < 5:
                ref_data, ref_mime = encode_image(ref_path)
                if ref_data:
                    parts.append({"inline_data": {"mime_type": ref_mime, "data": ref_data}})
                    parts.append({"text": ref_desc + "\n\n"})
                    ref_count += 1

        # Add engraving close-up reference if available
        engraving_path = os.path.join(PROJECT_ROOT, "branding", "engraving_closeup.png")
        creative_type = meta.get("creative_type", "product_static")
        product_cat = meta.get("product_category", "")
        # Check if product has engraving (brand-specific, configured in product_knowledge.json)
        has_engraving = os.path.exists(engraving_path)
        if has_engraving:
            eng_data, eng_mime = encode_image(engraving_path)
            if eng_data:
                parts.append({"inline_data": {"mime_type": eng_mime, "data": eng_data}})
                if creative_type == "lifestyle":
                    parts.append({
                        "text": "ENGRAVING REFERENCE: The product has brand engraving as shown in the reference. In this LIFESTYLE image, hands should naturally grip the product — covering the engraving area where possible.\n\n"
                    })
                else:
                    parts.append({
                        "text": "ENGRAVING REFERENCE: This close-up shows the brand engraving on the product. Reproduce this engraving EXACTLY as shown — match the font style, size, and placement. It MUST be clearly visible in your generated image.\n\n"
                    })
                ref_count += 1
                print(f"  Added engraving reference ({creative_type})")

        # Add brand logo as reference if logo should be visible
        logo_config = brand_elements.get("logo", {})
        if logo_config.get("visible"):
            logo_variant = "logo_dark.png" if logo_config.get("color_mode") != "light" else "logo_white.png"
            logo_path = os.path.join(PROJECT_ROOT, "branding", logo_variant)
            if os.path.exists(logo_path):
                logo_data, logo_mime = encode_image(logo_path)
                if logo_data:
                    logo_pos = logo_config.get("position", "top_center")
                    parts.append({"inline_data": {"mime_type": logo_mime, "data": logo_data}})
                    parts.append({
                        "text": f"BRAND LOGO REFERENCE: Place this EXACT logo at {logo_pos} of the image. Reproduce the logo EXACTLY as shown — same font, same proportions, same style. Do NOT invent a different logo — use this exact reference.\n\n"
                    })
                    ref_count += 1
                    print(f"  Added logo reference ({logo_variant}, {logo_pos})")

        if ref_count > 1:
            print(f"  Multi-reference: {ref_count} product images sent to Gemini")
        parts.append({
            "text": f"YOU HAVE {ref_count} REFERENCE IMAGES ABOVE. The product in your generated image MUST match these references EXACTLY — same two-tone colors, same slim proportions, same grooved texture, and the engraving on the right handle. If a logo reference is included, place it exactly as instructed. Study all references carefully before generating.\n\n"
        })
    elif is_negative_scene:
        parts.append({
            "text": "IMPORTANT: This is a NEGATIVE scene showing a PROBLEM. Do NOT use any branded or recognizable product. Show only generic, unbranded items. No brand names, no logos, no recognizable product designs.\n\n"
        })

    parts.append({"text": prompt_text})

    fmt = ad_prompt_json["meta"]["format"]
    aspect_map = {"4:5": "4:5", "9:16": "9:16", "1:1": "1:1", "16:9": "16:9"}
    aspect_ratio = aspect_map.get(fmt, "4:5")

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": 0.8,
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": "4K"
            }
        },
    }

    return payload


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------

def call_gemini(api_key, payload, max_retries=3):
    """Call Gemini API and return the generated image data."""
    url = GEMINI_URL.format(model=GEMINI_MODEL)

    for attempt in range(max_retries):
        try:
            print(f"  Calling Gemini API (attempt {attempt + 1})...")
            resp = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"  Warning: No candidates in response")
                continue

            parts = candidates[0].get("content", {}).get("parts", [])

            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return inline["data"], inline.get("mimeType") or inline.get("mime_type", "image/png")

            print(f"  Warning: No image in response parts")
            for part in parts:
                if "text" in part:
                    print(f"  Gemini text response: {part['text'][:500]}")
            feedback = data.get("promptFeedback", {})
            if feedback:
                print(f"  Prompt feedback: {feedback}")
            finish = candidates[0].get("finishReason", "")
            if finish:
                print(f"  Finish reason: {finish}")

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


# ---------------------------------------------------------------------------
# Logo compositing (in-memory, before upload)
# ---------------------------------------------------------------------------

def get_region_brightness(img, x, y, w, h):
    """Calculate average brightness of a region in the image."""
    region = img.crop((x, y, x + w, y + h)).convert("RGB")
    pixels = list(region.getdata())
    if not pixels:
        return 128
    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)
    return 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b


def composite_logo_in_memory(image_bytes, logo_position, logo_color_mode, logo_size="small"):
    """Composite the logo onto the image in memory. Returns modified image bytes (PNG)."""
    if not HAS_PIL:
        print("  Warning: PIL not installed, skipping logo compositing")
        return image_bytes

    logo_dark_path = os.path.join(PROJECT_ROOT, "branding", "logo_dark.png")
    logo_white_path = os.path.join(PROJECT_ROOT, "branding", "logo_white.png")

    if not os.path.exists(logo_dark_path):
        print(f"  Warning: Logo not found: {logo_dark_path}")
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        img_w, img_h = img.size

        size_map = {"small": 0.22, "medium": 0.25, "large": 0.30}
        logo_scale = size_map.get(logo_size, 0.22)

        margin_x = int(img_w * 0.04)
        margin_y = int(img_h * 0.03)

        logo_tmp = Image.open(logo_dark_path).convert("RGBA")
        logo_ratio = logo_tmp.height / logo_tmp.width
        new_logo_w = int(img_w * logo_scale)
        new_logo_h = int(new_logo_w * logo_ratio)

        pos_map = {
            "top_left": (margin_x, margin_y),
            "top_center": ((img_w - new_logo_w) // 2, margin_y),
            "top_right": (img_w - new_logo_w - margin_x, margin_y),
            "bottom_center": ((img_w - new_logo_w) // 2, img_h - new_logo_h - margin_y),
            "bottom_right": (img_w - new_logo_w - margin_x, img_h - new_logo_h - margin_y),
        }
        pos = pos_map.get(logo_position, pos_map["top_center"])

        brightness = get_region_brightness(img, pos[0], pos[1], new_logo_w, new_logo_h)

        if brightness > 160:
            chosen_logo_path = logo_dark_path
            chosen_mode = "dark"
        else:
            chosen_logo_path = logo_white_path if os.path.exists(logo_white_path) else logo_dark_path
            chosen_mode = "light" if os.path.exists(logo_white_path) else "dark"

        logo = Image.open(chosen_logo_path).convert("RGBA")
        logo = logo.resize((new_logo_w, new_logo_h), Image.LANCZOS)

        img.paste(logo, pos, logo)

        # Export as PNG bytes
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        print(f"  Logo composited ({chosen_mode} on brightness={brightness:.0f}, {logo_position})")
        return buf.getvalue()

    except Exception as e:
        print(f"  Warning: Logo compositing failed: {e}")
        return image_bytes


def composite_overlay_in_memory(image_bytes, overlay_path, position="bottom_center", scale=0.3):
    """Composite a PNG overlay (social proof, payment icons, etc.) onto the image."""
    if not HAS_PIL:
        return image_bytes

    overlay_full_path = os.path.join(PROJECT_ROOT, overlay_path) if not os.path.isabs(overlay_path) else overlay_path
    if not os.path.exists(overlay_full_path):
        print(f"  Overlay not found: {overlay_path} — skipping")
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        img_w, img_h = img.size

        overlay = Image.open(overlay_full_path).convert("RGBA")
        ov_ratio = overlay.height / overlay.width
        new_ov_w = int(img_w * scale)
        new_ov_h = int(new_ov_w * ov_ratio)
        overlay = overlay.resize((new_ov_w, new_ov_h), Image.LANCZOS)

        margin_x = int(img_w * 0.04)
        margin_y = int(img_h * 0.02)

        pos_map = {
            "top_center": ((img_w - new_ov_w) // 2, margin_y),
            "bottom_center": ((img_w - new_ov_w) // 2, img_h - new_ov_h - margin_y),
            "bottom_left": (margin_x, img_h - new_ov_h - margin_y),
            "bottom_right": (img_w - new_ov_w - margin_x, img_h - new_ov_h - margin_y),
        }
        pos = pos_map.get(position, pos_map["bottom_center"])

        img.paste(overlay, pos, overlay)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        print(f"  Overlay composited: {os.path.basename(overlay_path)} at {position}")
        return buf.getvalue()
    except Exception as e:
        print(f"  Warning: Overlay compositing failed ({overlay_path}): {e}")
        return image_bytes


def composite_all_overlays(image_bytes, ad_prompt):
    """Apply all compositor overlays: logo, social proof, payment icons, etc."""
    brand_elements = ad_prompt.get("brand_elements", {})

    # 1. Logo — skip compositor if logo was sent as reference to Gemini (AI renders it directly)
    logo_config = brand_elements.get("logo", {})
    if logo_config.get("visible"):
        # Logo reference was sent to Gemini — it renders the logo itself, no compositor needed
        print(f"  Logo: rendered by Gemini (reference image sent), skipping compositor")

    # 2. Social proof overlay (if file exists)
    social_proof_path = os.path.join(PROJECT_ROOT, "branding", "social_proof.png")
    if os.path.exists(social_proof_path):
        image_bytes = composite_overlay_in_memory(
            image_bytes, social_proof_path,
            position="bottom_center", scale=0.5
        )

    # 3. Payment icons overlay (if file exists)
    payment_path = os.path.join(PROJECT_ROOT, "branding", "payment_icons.png")
    if os.path.exists(payment_path):
        # Position slightly above social proof
        image_bytes = composite_overlay_in_memory(
            image_bytes, payment_path,
            position="bottom_center", scale=0.4
        )

    # 4. Color variants overlay (if file exists)
    colors_path = os.path.join(PROJECT_ROOT, "branding", "color_variants.png")
    if os.path.exists(colors_path):
        image_bytes = composite_overlay_in_memory(
            image_bytes, colors_path,
            position="bottom_center", scale=0.25
        )

    return image_bytes


# ---------------------------------------------------------------------------
# Single ad generation + upload
# ---------------------------------------------------------------------------

def generate_single_ad(api_key, sb, brand_id, batch_id, prompt_data, index, creative_id, raw_only=False):
    """Generate a single ad, composite logo, upload to Supabase Storage, update row."""
    ad_prompt = prompt_data["prompt"]
    product_image = prompt_data["product_image"]
    meta = ad_prompt["meta"]
    creative_style = meta.get("creative_style", "on_brand")
    generation_mode = meta.get("generation_mode", "both")
    if raw_only:
        generation_mode = "raw"
    hook_text = next(
        (t["content"] for t in ad_prompt.get("text_overlays", []) if t["role"] == "headline"),
        ""
    )

    print(f"\n[{index}] {meta['angle']} > {meta['sub_angle']} (v{meta['variant']}, {meta['format']})")

    # Resolve product image path
    img_path = os.path.join(PROJECT_ROOT, product_image)
    if not os.path.exists(img_path):
        print(f"  Error: Product image not found: {img_path}")
        sb.update_creative(creative_id, {"status": "failed"})
        return None

    # For raw mode, create a stripped prompt without text overlays
    if generation_mode == "raw":
        raw_prompt = dict(ad_prompt)
        raw_prompt["text_overlays"] = []
        raw_prompt["brand_elements"] = {}
        raw_prompt["visual_elements"] = {}
        payload = build_gemini_prompt(raw_prompt, img_path)
    else:
        payload = build_gemini_prompt(ad_prompt, img_path)

    image_data, mime_type = call_gemini(api_key, payload)

    if not image_data:
        print(f"  FAILED: No image generated")
        sb.update_creative(creative_id, {"status": "failed"})
        return None

    # Decode image
    image_bytes = base64.standard_b64decode(image_data)

    # Save raw version before compositing (for 'both' mode)
    raw_image_bytes = image_bytes

    # Composite all overlays only if not raw-only
    if generation_mode != "raw":
        image_bytes = composite_all_overlays(image_bytes, ad_prompt)

    # Build filename (ASCII-safe, no umlauts)
    def ascii_slug(s):
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
        for k, v in replacements.items():
            s = s.replace(k, v)
        return s.lower().replace("/", "_").replace(" ", "_").replace("-", "_")

    angle_slug = ascii_slug(meta["angle"])
    sub_angle_slug = ascii_slug(meta["sub_angle"])
    variant = meta["variant"]
    fmt = meta["format"].replace(":", "x")
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    ext = ext_map.get(mime_type, "png")
    filename = f"{index:03d}_{angle_slug}_{sub_angle_slug}_v{variant}_{fmt}.{ext}"

    # Upload to Supabase Storage
    storage_path = f"{brand_id}/{batch_id}/{filename}"
    content_type = mime_type or "image/png"

    try:
        sb.upload_file("creatives", storage_path, image_bytes, content_type)
        image_url = sb.get_public_url("creatives", storage_path)
        print(f"  Uploaded: {storage_path} ({len(image_bytes) / 1024:.0f} KB)")
    except Exception as e:
        print(f"  Upload failed: {e}")
        sb.update_creative(creative_id, {"status": "failed"})
        return None

    # Also upload raw version for 'both' mode
    if generation_mode == "both" and raw_image_bytes != image_bytes:
        raw_storage_path = f"{brand_id}/{batch_id}/raw/{filename}"
        try:
            sb.upload_file("creatives", raw_storage_path, raw_image_bytes, content_type)
            print(f"  Raw uploaded: {raw_storage_path}")
        except Exception as e:
            print(f"  Raw upload failed (non-critical): {e}")

    # Update creative row → done
    updates = {
        "status": "done",
        "storage_path": storage_path,
        "image_url": image_url,
    }
    if creative_style:
        updates["creative_style"] = creative_style
    sb.update_creative(creative_id, updates)
    print(f"  Creative updated: image live!")

    # Also save locally as backup
    local_dir = os.path.join(PROJECT_ROOT, "creatives", str(batch_id))
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    return {
        "index": index,
        "filename": filename,
        "storage_path": storage_path,
        "image_url": image_url,
        "angle": meta["angle"],
        "sub_angle": meta["sub_angle"],
        "variant": meta["variant"],
        "format": meta["format"],
        "hook_text": hook_text,
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def generate_ads(api_key, sb, brand_id, prompts, raw_only=False):
    """Generate all ads in parallel with Supabase tracking."""
    batch_id = str(uuid.uuid4())
    print(f"Batch ID: {batch_id}")

    # Step 1: Insert ALL placeholders into Supabase at once
    creative_ids = []
    for i, prompt_data in enumerate(prompts, 1):
        ad_prompt = prompt_data["prompt"]
        meta = ad_prompt["meta"]
        hook_text = next(
            (t["content"] for t in ad_prompt.get("text_overlays", []) if t["role"] == "headline"),
            ""
        )

        row = {
            "brand_id": brand_id,
            "batch_id": batch_id,
            "angle": meta["angle"],
            "sub_angle": meta["sub_angle"],
            "variant": meta["variant"],
            "format": meta["format"],
            "hook_text": hook_text,
            "status": "generating",
            "is_saved": False,
            "creative_style": meta.get("creative_style", "on_brand"),
            "creative_type": meta.get("creative_type", "product_static"),
            "season": meta.get("season", "evergreen"),
            "environment": meta.get("environment"),
            "product_category": meta.get("product_category"),
        }

        try:
            inserted = sb.insert_creative(row)
            creative_ids.append(inserted["id"])
            print(f"  Placeholder [{i}]: {meta['angle']} > {meta['sub_angle']}")
        except Exception as e:
            print(f"  Error inserting placeholder [{i}]: {e}")
            creative_ids.append(None)

    print(f"All {len(prompts)} placeholders inserted into Supabase")

    # Step 2: Generate all ads in parallel
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "batch_id": batch_id,
        "brand_id": brand_id,
        "total_prompts": len(prompts),
        "successful": 0,
        "failed": 0,
        "ads": []
    }

    max_workers = min(5, len(prompts))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, (prompt_data, creative_id) in enumerate(zip(prompts, creative_ids), 1):
            if creative_id is None:
                manifest["failed"] += 1
                continue
            future = executor.submit(
                generate_single_ad,
                api_key, sb, brand_id, batch_id, prompt_data, i, creative_id, raw_only
            )
            futures[future] = i

        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                if result:
                    manifest["successful"] += 1
                    manifest["ads"].append(result)
                else:
                    manifest["failed"] += 1
            except Exception as e:
                print(f"  Error in ad {idx}: {e}")
                manifest["failed"] += 1

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Creative Producer — Static Ad Generation")
    parser.add_argument("--prompts-file", required=True, help="Path to JSON file with ad prompts")
    parser.add_argument("--brand-id", default=None, help="Brand UUID (auto-detected if omitted)")
    parser.add_argument("--output-dir", default=None, help="Local backup directory (optional)")
    parser.add_argument("--raw-only", action="store_true", help="Generate only raw images without text overlays or compositor")
    args = parser.parse_args()

    # Prevent concurrent runs
    acquire_process_lock()
    atexit.register(release_process_lock)

    def handle_signal(sig, frame):
        print(f"\nInterrupted (signal {sig}) — cleaning up...")
        release_process_lock()
        sys.exit(1)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    api_key = load_config()
    sb = init_supabase()

    # Auto-detect brand if not provided
    if args.brand_id:
        try:
            uuid.UUID(args.brand_id)
        except ValueError:
            print(f"Error: --brand-id must be a valid UUID, got: {args.brand_id}")
            sys.exit(1)
        brand_id = args.brand_id
    else:
        brand_id = sb.get_single_brand_id()
        print(f"Auto-detected brand: {brand_id}")

    # Load prompts
    with open(args.prompts_file) as f:
        prompts = json.load(f)

    if not isinstance(prompts, list):
        prompts = [prompts]

    print(f"Loaded {len(prompts)} ad prompts")
    print(f"Brand: {brand_id}")

    # Generate
    manifest = generate_ads(api_key, sb, brand_id, prompts, raw_only=args.raw_only)

    # Save manifest locally
    batch_dir = os.path.join(PROJECT_ROOT, "creatives", manifest["batch_id"])
    os.makedirs(batch_dir, exist_ok=True)
    manifest_path = os.path.join(batch_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE: {manifest['successful']} generated, {manifest['failed']} failed")
    print(f"Batch: {manifest['batch_id']}")
    print(f"Manifest: {manifest_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
