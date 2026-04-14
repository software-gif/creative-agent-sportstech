#!/usr/bin/env python3
"""Multishot Generator — Creates camera angle variations of an existing image.

Takes a source key visual and generates variations with different camera settings
(shot size, angle, lens, depth of field) while keeping scene, model, and product identical.

Usage:
    # Single shot
    python3 .claude/skills/multishot/scripts/main.py \
        --source-image "creatives/batch123/001.png" \
        --shot-size "Extreme Close Up" \
        --camera-angle "Ground level" \
        --lens "50mm" \
        --depth-of-field "f/8"

    # Batch mode
    python3 .claude/skills/multishot/scripts/main.py \
        --source-image "creatives/batch123/001.png" \
        --batch '[{"shot_size": "Close Up", "lens": "85mm", "depth_of_field": "f/1.8"}]'
"""

import argparse
import base64
import json
import os
import subprocess
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

VALID_SHOT_SIZES = ["Extreme Wide", "Wide", "Medium Shot", "Close Up", "Extreme Close Up", "Bird's Eye"]
VALID_CAMERA_ANGLES = ["Eye level", "Slightly above", "High angle", "Slightly below", "Low angle", "Ground level"]
VALID_CHARACTER_ANGLES = ["Front facing", "3/4 angle", "Profile", "Over the shoulder", "Back view", "Top View"]
VALID_LENSES = ["14mm", "24mm", "35mm", "50mm", "85mm", "135mm", "200mm"]
VALID_DOF = ["f/1.2", "f/1.8", "f/2.8", "f/4", "f/5.6", "f/8", "f/16"]


def get_supabase_headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


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


def encode_image(path):
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = f"image/{'png' if ext == 'png' else 'jpeg'}"
    return data, mime


def download_from_supabase(storage_path):
    url = f"{SUPABASE_URL}/storage/v1/object/public/creatives/{storage_path}"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        tmp_path = os.path.join(PROJECT_ROOT, ".tmp_multishot_source.png")
        with open(tmp_path, "wb") as f:
            f.write(resp.content)
        return tmp_path
    return None


def build_multishot_prompt(settings):
    """Build the multishot prompt from camera settings.

    Phrased as an imperative re-rendering directive — Gemini 3 Flash
    otherwise over-weights composition consistency and ignores soft
    "Camera Angle: X" labels, which is why Clemente's earlier batches
    all came out on the same eye-level angle.
    """
    changes = []
    if settings.get("shot_size") and settings["shot_size"] != "Keep the Same":
        changes.append(f"shot size becomes **{settings['shot_size']}**")
    if settings.get("camera_angle") and settings["camera_angle"] != "Keep the Same":
        changes.append(
            f"camera vertical angle becomes **{settings['camera_angle']}** "
            f"(the camera physically moves to this vertical position relative to the subject — "
            f"do not keep the original angle)"
        )
    if settings.get("character_angle") and settings["character_angle"] != "Keep the Same":
        changes.append(
            f"character orientation to camera becomes **{settings['character_angle']}** "
            f"(rotate the character's body relative to the lens — "
            f"do not keep the original orientation)"
        )
    if settings.get("lens") and settings["lens"] != "Keep the Same":
        changes.append(f"lens becomes **{settings['lens']}**")
    if settings.get("depth_of_field") and settings["depth_of_field"] != "Keep the Same":
        changes.append(f"depth of field becomes **{settings['depth_of_field']}**")

    lines = [
        "Re-render the exact same scene shown in Image 1 as a NEW photograph from a different viewpoint.",
        "",
        "IDENTICAL across both images (must not change):",
        "- The character (same person, same clothing, same hair, same build)",
        "- The product (same model, same color, same placement in the room)",
        "- The room, furniture, decor, lighting, time of day, mood",
        "- The character's activity and pose (same motion, same body mechanics)",
        "",
        "DIFFERENT in the new render — you MUST change these, not approximate them:",
    ]
    for change in changes:
        lines.append(f"- {change}")

    lines += [
        "",
        "Treat this as a physical second camera capturing the same moment from a new position.",
        "The viewer should instantly recognize it as the same scene, but from a clearly different camera setup.",
        "Do NOT produce a near-duplicate of Image 1 — the requested camera change must be visually obvious.",
    ]

    if settings.get("other_instructions"):
        lines.append("")
        lines.append(f"Additional: {settings['other_instructions']}")
    if settings.get("model_detail"):
        lines.append(f"Model detail: {settings['model_detail']}")

    return "\n".join(lines)


def generate_multishot(source_path, prompt_text, label, attempt=1):
    """Send source image + multishot prompt to Gemini."""
    print(f"\n  Generating {label} (attempt {attempt})...")

    img_data, img_mime = encode_image(source_path)
    if not img_data:
        print(f"  ERROR: Could not read source: {source_path}")
        return None

    parts = [
        {"inline_data": {"mime_type": img_mime, "data": img_data}},
        {"text": prompt_text},
    ]

    payload = {
        "contents": [{"parts": parts}],
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
            print(f"  WARNING: No candidates for {label}")
            return None

        resp_parts = candidates[0].get("content", {}).get("parts", [])
        for part in resp_parts:
            if "inlineData" in part:
                img_bytes = base64.b64decode(part["inlineData"]["data"])
                mime = part["inlineData"].get("mimeType", "image/png")
                ext = "png" if "png" in mime else "jpg"
                return img_bytes, ext

        return None

    except Exception as e:
        print(f"  ERROR: {e}")
        if attempt < 3:
            return generate_multishot(source_path, prompt_text, label, attempt + 1)
        return None


def upload_to_supabase(image_bytes, path, ext="png"):
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
        return f"{SUPABASE_URL}/storage/v1/object/public/creatives/{path}"
    print(f"  Upload error ({resp.status_code}): {resp.text[:200]}")
    return None


def save_creative_to_db(creative_data):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/creatives",
        headers={**get_supabase_headers(), "Prefer": "return=representation"},
        json=creative_data,
    )
    resp.raise_for_status()
    return resp.json()[0]


def resolve_parent_id(source_image, explicit_id):
    """Resolve the parent Key Visual creative this variant derives from.

    Explicit --source-creative-id always wins. Otherwise we look the source
    up by storage_path so the agent can just pass the same path it gave
    --source-image and the parent gets linked automatically. Returns None
    on no match (orphan — filterable later).
    """
    if explicit_id:
        return explicit_id
    if not source_image:
        return None
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/creatives",
            headers=get_supabase_headers(),
            params={"storage_path": f"eq.{source_image}", "select": "id", "limit": 1},
        )
        if resp.ok:
            rows = resp.json()
            if rows:
                return rows[0]["id"]
    except Exception as e:
        print(f"  WARN: parent_id lookup failed: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Multishot Generator")
    parser.add_argument("--source-image", required=True, help="Source image path")
    parser.add_argument("--shot-size", default=None, choices=VALID_SHOT_SIZES + ["Keep the Same"])
    parser.add_argument("--camera-angle", default=None, choices=VALID_CAMERA_ANGLES + ["Keep the Same"])
    parser.add_argument("--character-angle", default=None, choices=VALID_CHARACTER_ANGLES + ["Keep the Same"])
    parser.add_argument("--lens", default=None, choices=VALID_LENSES + ["Keep the Same"])
    parser.add_argument("--depth-of-field", default=None, choices=VALID_DOF + ["Keep the Same"])
    parser.add_argument("--other-instructions", default=None)
    parser.add_argument("--model-detail", default=None)
    parser.add_argument("--batch", default=None, help="JSON array of settings for batch generation")
    parser.add_argument("--source-creative-id", default=None)
    parser.add_argument("--auto-qc", dest="auto_qc", action="store_true", default=True,
                        help="Run quality-control on each generated shot and retry on failure. Default: on.")
    parser.add_argument("--no-qc", dest="auto_qc", action="store_false",
                        help="Skip the QC loop. Use sparingly.")
    parser.add_argument("--qc-retries", type=int, default=2,
                        help="Max retries per shot when auto-qc is on (default 2).")
    parser.add_argument("--qc-threshold", type=int, default=7,
                        help="Minimum QC score (0-10) to accept a shot (default 7).")
    args = parser.parse_args()

    qc_script = os.path.join(SCRIPT_DIR, "..", "..", "quality-control", "scripts", "main.py")
    max_attempts = (args.qc_retries + 1) if args.auto_qc else 1

    if not GEMINI_API_KEY:
        sys.exit("ERROR: GEMINI_API_KEY not set")

    brand_id = get_brand_id()
    batch_id = str(uuid.uuid4())
    parent_id = resolve_parent_id(args.source_image, args.source_creative_id)
    if parent_id:
        print(f"  Parent Key Visual: {parent_id}")
    else:
        print(f"  WARN: No parent Key Visual resolved — variant will be orphaned")

    # Resolve source image
    source_path = args.source_image
    if not os.path.exists(source_path):
        downloaded = download_from_supabase(source_path)
        if downloaded:
            source_path = downloaded
        else:
            alt_path = os.path.join(PROJECT_ROOT, source_path)
            if os.path.exists(alt_path):
                source_path = alt_path
            else:
                sys.exit(f"ERROR: Source image not found: {args.source_image}")

    # Build shot list
    if args.batch:
        shots = json.loads(args.batch)
    else:
        shots = [{
            "shot_size": args.shot_size,
            "camera_angle": args.camera_angle,
            "character_angle": args.character_angle,
            "lens": args.lens,
            "depth_of_field": args.depth_of_field,
            "other_instructions": args.other_instructions,
            "model_detail": args.model_detail,
        }]

    print("=" * 60)
    print("MULTISHOT GENERATOR")
    print("=" * 60)
    print(f"  Source: {args.source_image}")
    print(f"  Batch ID: {batch_id}")
    print(f"  Shots: {len(shots)}")

    # Attempt to resolve the parent's product handle so the QC judge uses
    # the correct must_match rules. parent_id gives us the creative row.
    parent_product_handle = None
    if parent_id:
        try:
            pr = requests.get(
                f"{SUPABASE_URL}/rest/v1/creatives",
                headers=get_supabase_headers(),
                params={"id": f"eq.{parent_id}", "select": "prompt_json,product_category"},
            )
            if pr.ok and pr.json():
                pj = pr.json()[0].get("prompt_json") or {}
                parent_product_handle = pj.get("product")
        except Exception:
            pass

    results = []
    for i, settings in enumerate(shots):
        label = f"shot_{i+1}"
        prompt = build_multishot_prompt(settings)

        print(f"\n{'─' * 40}")
        print(f"Shot {i+1}/{len(shots)}")
        print(f"  Settings: {json.dumps({k:v for k,v in settings.items() if v}, ensure_ascii=False)}")

        accepted_id = None
        for attempt in range(1, max_attempts + 1):
            if max_attempts > 1:
                print(f"  Attempt {attempt}/{max_attempts}")

            result = generate_multishot(source_path, prompt, label, attempt)
            if result is None:
                print(f"  FAILED: {label}")
                continue

            img_bytes, ext = result
            creative_id = str(uuid.uuid4())
            storage_path = f"multishots/{batch_id}/{label}_a{attempt}.{ext}"
            url = upload_to_supabase(img_bytes, storage_path, ext)

            if not url:
                local_dir = os.path.join(PROJECT_ROOT, "creatives", "multishots", batch_id)
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, f"{label}_a{attempt}.{ext}")
                with open(local_path, "wb") as f:
                    f.write(img_bytes)
                print(f"  Saved locally: {local_path}")

            creative_data = {
                "id": creative_id,
                "brand_id": brand_id,
                "batch_id": batch_id,
                "parent_id": parent_id,
                "storage_path": storage_path,
                "prompt_text": prompt,
                "prompt_json": {
                    "source_image": args.source_image,
                    "settings": settings,
                    # Inherit the parent's product handle so QC loads the
                    # right must_match / must_avoid rules.
                    "product": parent_product_handle,
                },
                "shot_size": settings.get("shot_size"),
                "camera_angle": settings.get("camera_angle"),
                "character_angle": settings.get("character_angle"),
                "lens": settings.get("lens"),
                "depth_of_field": settings.get("depth_of_field"),
                "creative_type": "multishot",
                "generation_model": GEMINI_MODEL,
                "status": "generated",
            }

            saved = save_creative_to_db(creative_data)
            print(f"  Saved: {saved['id']}")

            if not args.auto_qc:
                accepted_id = saved["id"]
                results.append(saved)
                break

            print(f"  Running QC (threshold {args.qc_threshold})...")
            qc_proc = subprocess.run(
                [
                    sys.executable, qc_script,
                    "--creative-id", creative_id,
                    "--delete-on-fail",
                    "--threshold", str(args.qc_threshold),
                ],
                capture_output=True, text=True,
            )
            sys.stdout.write(qc_proc.stdout)
            if qc_proc.stderr:
                sys.stderr.write(qc_proc.stderr)
            if qc_proc.returncode == 0:
                accepted_id = saved["id"]
                results.append(saved)
                break
            print(f"  QC rejected {label} (attempt {attempt}/{max_attempts}), retrying…")

        if not accepted_id:
            print(f"  WARN: {label} exhausted {max_attempts} attempts without passing QC")

    print(f"\n{'=' * 60}")
    print(f"MULTISHOT BATCH COMPLETE: {batch_id}")
    print(f"  Generated: {len(results)}/{len(shots)}")
    for r in results:
        settings_str = " | ".join(filter(None, [r.get("shot_size"), r.get("camera_angle"), r.get("lens"), r.get("depth_of_field")]))
        print(f"    {r['id']}: {settings_str}")
    print(f"{'=' * 60}")

    # Structured result for agent chaining
    print("RESULT_JSON " + json.dumps({
        "batch_id": batch_id,
        "parent_id": parent_id,
        "creatives": [
            {"id": r["id"], "storage_path": r.get("storage_path"), "creative_type": "multishot"}
            for r in results
        ],
    }))

    # Cleanup
    tmp = os.path.join(PROJECT_ROOT, ".tmp_multishot_source.png")
    if os.path.exists(tmp):
        os.remove(tmp)


if __name__ == "__main__":
    main()
