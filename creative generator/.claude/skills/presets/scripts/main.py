#!/usr/bin/env python3
"""Presets skill — manages reusable lifestyle image generation recipes.

A preset bundles product × room × character × camera into a named recipe
stored in Supabase (`creative_presets` table). Subcommands cover the full
lifecycle: list, show, create, update, delete, run.

`run` delegates to key-visual/scripts/main.py with the stored parameters.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(SKILLS_DIR, "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

KEY_VISUAL_SCRIPT = os.path.join(SKILLS_DIR, "key-visual", "scripts", "main.py")
BRANDING_DIR = os.path.join(PROJECT_ROOT, "branding")

VALID_CHARACTER_MODES = {"auto_rotate", "fixed", "description", "model_pool"}


# ======================================================================
# Supabase helpers
# ======================================================================

def _headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    if not SUPABASE_URL or not key:
        sys.exit("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY not set in .env")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def get_brand_id(slug="sportstech"):
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/brands?slug=eq.{slug}&select=id",
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        sys.exit(f"ERROR: No brand '{slug}' found in Supabase.")
    return rows[0]["id"]


def rest_get(path, params=None):
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_headers(),
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def rest_post(path, body):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={**_headers(), "Prefer": "return=representation"},
        json=body,
        timeout=15,
    )
    if resp.status_code >= 400:
        sys.exit(f"ERROR: Supabase POST {path} → {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def rest_patch(path, body):
    resp = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={**_headers(), "Prefer": "return=representation"},
        json=body,
        timeout=15,
    )
    if resp.status_code >= 400:
        sys.exit(f"ERROR: Supabase PATCH {path} → {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def rest_delete(path):
    resp = requests.delete(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_headers(),
        timeout=15,
    )
    if resp.status_code >= 400:
        sys.exit(f"ERROR: Supabase DELETE {path} → {resp.status_code}: {resp.text[:400]}")
    return True


# ======================================================================
# Validation helpers
# ======================================================================

def load_product_knowledge():
    path = os.path.join(BRANDING_DIR, "product_knowledge.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f).get("products", {})


def load_room_prompts():
    path = os.path.join(BRANDING_DIR, "room_prompts.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f).get("rooms", [])


def load_model_pool_ids():
    path = os.path.join(BRANDING_DIR, "lifestyle_variance.json")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        data = json.load(f)
    return {m["id"] for m in data.get("models", [])}


def validate_preset_fields(fields, creating=False):
    """Sanity-check fields before hitting the DB. creating=True enforces required."""
    errors = []
    products = load_product_knowledge()
    rooms = {r["id"] for r in load_room_prompts()}
    model_ids = load_model_pool_ids()

    if creating:
        for req in ("slug", "name", "product_handle"):
            if not fields.get(req):
                errors.append(f"Missing required field: {req}")

    handle = fields.get("product_handle")
    if handle and handle not in products:
        errors.append(
            f"Unknown product_handle '{handle}'. "
            f"Valid: {', '.join(sorted(products.keys()))}"
        )

    room = fields.get("room_preset")
    if room and room not in rooms:
        print(f"  WARNING: room_preset '{room}' not found in room_prompts.json (accepting anyway)")

    mode = fields.get("character_mode")
    if mode and mode not in VALID_CHARACTER_MODES:
        errors.append(f"Invalid character_mode '{mode}'. Valid: {sorted(VALID_CHARACTER_MODES)}")

    if mode == "model_pool":
        mpid = fields.get("model_pool_id")
        if mpid and mpid not in model_ids:
            errors.append(
                f"Unknown model_pool_id '{mpid}'. Valid: {sorted(model_ids)}"
            )

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)


# ======================================================================
# Subcommands
# ======================================================================

def cmd_list(args):
    brand_id = get_brand_id()
    params = {
        "brand_id": f"eq.{brand_id}",
        "select": "slug,name,product_handle,room_preset,tags,default_count,run_count,last_run_at",
        "order": "slug.asc",
    }
    if args.product:
        params["product_handle"] = f"eq.{args.product}"
    if args.tag:
        params["tags"] = f"cs.{{{args.tag}}}"

    rows = rest_get("creative_presets", params)
    if not rows:
        print("No presets found.")
        return

    print(f"\n{'SLUG':<32} {'PRODUCT':<15} {'ROOM':<22} {'RUNS':<5} NAME")
    print("─" * 110)
    for r in rows:
        slug = r["slug"][:31]
        product = (r.get("product_handle") or "-")[:14]
        room = (r.get("room_preset") or "-")[:21]
        runs = str(r.get("run_count") or 0)
        name = r.get("name", "")
        print(f"{slug:<32} {product:<15} {room:<22} {runs:<5} {name}")
    print(f"\n{len(rows)} preset(s)")


def cmd_show(args):
    brand_id = get_brand_id()
    rows = rest_get(
        "creative_presets",
        {"brand_id": f"eq.{brand_id}", "slug": f"eq.{args.slug}", "select": "*"},
    )
    if not rows:
        sys.exit(f"ERROR: No preset with slug '{args.slug}'")
    print(json.dumps(rows[0], indent=2, ensure_ascii=False))


def _fields_from_args(args, creating):
    """Extract preset fields from argparse namespace. None values are dropped."""
    tags_raw = getattr(args, "tags", None)
    tags = None
    if tags_raw is not None:
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    fields = {
        "slug": getattr(args, "slug", None),
        "name": getattr(args, "name", None),
        "description": getattr(args, "description", None),
        "product_handle": getattr(args, "product", None),
        "room_preset": getattr(args, "room_preset", None),
        "room_description": getattr(args, "room_description", None),
        "character_mode": getattr(args, "character_mode", None),
        "character_id": getattr(args, "character_id", None),
        "character_description": getattr(args, "character_description", None),
        "model_pool_id": getattr(args, "model_pool_id", None),
        "pose": getattr(args, "pose", None),
        "shot_size": getattr(args, "shot_size", None),
        "camera_angle": getattr(args, "camera_angle", None),
        "character_angle": getattr(args, "character_angle", None),
        "lens": getattr(args, "lens", None),
        "depth_of_field": getattr(args, "depth_of_field", None),
        "format": getattr(args, "format", None),
        "default_count": getattr(args, "default_count", None),
        "tags": tags,
    }
    # Drop None so update doesn't nullify unspecified fields
    fields = {k: v for k, v in fields.items() if v is not None}
    validate_preset_fields(fields, creating=creating)
    return fields


def cmd_create(args):
    brand_id = get_brand_id()
    fields = _fields_from_args(args, creating=True)

    existing = rest_get(
        "creative_presets",
        {"brand_id": f"eq.{brand_id}", "slug": f"eq.{fields['slug']}", "select": "id"},
    )
    if existing:
        sys.exit(
            f"ERROR: Preset '{fields['slug']}' already exists for this brand. "
            f"Use `update` to modify it."
        )

    fields["brand_id"] = brand_id
    created = rest_post("creative_presets", fields)
    print("Created preset:")
    print(json.dumps(created[0], indent=2, ensure_ascii=False))


def cmd_update(args):
    brand_id = get_brand_id()

    if args.new_slug:
        print("ERROR: Renaming slugs is not supported — delete + recreate instead.")
        sys.exit(1)

    old_slug = args.old_slug
    fields = _fields_from_args(args, creating=False)
    if not fields:
        sys.exit("ERROR: No fields to update. Pass at least one flag.")

    existing = rest_get(
        "creative_presets",
        {"brand_id": f"eq.{brand_id}", "slug": f"eq.{old_slug}", "select": "id"},
    )
    if not existing:
        sys.exit(f"ERROR: No preset with slug '{old_slug}'")

    updated = rest_patch(
        f"creative_presets?brand_id=eq.{brand_id}&slug=eq.{old_slug}",
        fields,
    )
    print("Updated preset:")
    print(json.dumps(updated[0], indent=2, ensure_ascii=False))


def cmd_delete(args):
    brand_id = get_brand_id()
    existing = rest_get(
        "creative_presets",
        {"brand_id": f"eq.{brand_id}", "slug": f"eq.{args.slug}", "select": "id,name"},
    )
    if not existing:
        sys.exit(f"ERROR: No preset with slug '{args.slug}'")

    rest_delete(f"creative_presets?brand_id=eq.{brand_id}&slug=eq.{args.slug}")
    print(f"Deleted preset: {args.slug} ({existing[0]['name']})")


def cmd_run(args):
    brand_id = get_brand_id()
    rows = rest_get(
        "creative_presets",
        {"brand_id": f"eq.{brand_id}", "slug": f"eq.{args.slug}", "select": "*"},
    )
    if not rows:
        sys.exit(f"ERROR: No preset with slug '{args.slug}'")
    preset = rows[0]

    if not os.path.exists(KEY_VISUAL_SCRIPT):
        sys.exit(f"ERROR: key-visual script not found at {KEY_VISUAL_SCRIPT}")

    count = args.count or preset.get("default_count") or 3

    cmd = [
        "python3", KEY_VISUAL_SCRIPT,
        "--product", preset["product_handle"],
        "--shot-size", preset.get("shot_size") or "Wide",
        "--camera-angle", preset.get("camera_angle") or "Eye level",
        "--character-angle", preset.get("character_angle") or "3/4 angle",
        "--lens", preset.get("lens") or "50mm",
        "--depth-of-field", preset.get("depth_of_field") or "f/4",
        "--format", preset.get("format") or "9:16",
        "--count", str(count),
    ]

    if preset.get("room_preset"):
        cmd += ["--room-preset", preset["room_preset"]]
    if preset.get("room_description"):
        cmd += ["--room-description", preset["room_description"]]
    if preset.get("pose"):
        cmd += ["--pose", preset["pose"]]

    mode = preset.get("character_mode", "auto_rotate")
    if mode == "fixed" and preset.get("character_id"):
        cmd += ["--character-id", preset["character_id"]]
    elif mode == "description" and preset.get("character_description"):
        cmd += ["--character-description", preset["character_description"]]
    elif mode == "model_pool" and preset.get("model_pool_id"):
        # key-visual expects a description; we translate model_pool_id → snippet
        model_ids = _load_model_pool_snippets()
        snippet = model_ids.get(preset["model_pool_id"])
        if snippet:
            cmd += ["--character-description", snippet]

    print(f"→ Running preset '{args.slug}' ({count} image(s))")
    print(f"  Command: {' '.join(repr(c) if ' ' in c else c for c in cmd)}")

    if args.dry_run:
        print("  (dry-run — not executing)")
        return

    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"ERROR: key-visual exited with code {result.returncode}")

    rest_patch(
        f"creative_presets?brand_id=eq.{brand_id}&slug=eq.{args.slug}",
        {
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "run_count": (preset.get("run_count") or 0) + 1,
        },
    )
    print(f"✓ Run complete. run_count now {(preset.get('run_count') or 0) + 1}")


def _load_model_pool_snippets():
    path = os.path.join(BRANDING_DIR, "lifestyle_variance.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return {m["id"]: m.get("prompt_snippet", "") for m in data.get("models", [])}


# ======================================================================
# Argparse wiring
# ======================================================================

def _add_preset_field_flags(sp, require_create=False):
    """Shared flag set used by create + update."""
    sp.add_argument("--name", required=require_create)
    sp.add_argument("--description")
    sp.add_argument("--product", required=require_create, help="Product handle")
    sp.add_argument("--room-preset")
    sp.add_argument("--room-description")
    sp.add_argument("--character-mode", choices=sorted(VALID_CHARACTER_MODES))
    sp.add_argument("--character-id")
    sp.add_argument("--character-description")
    sp.add_argument("--model-pool-id")
    sp.add_argument("--pose")
    sp.add_argument("--shot-size")
    sp.add_argument("--camera-angle")
    sp.add_argument("--character-angle")
    sp.add_argument("--lens")
    sp.add_argument("--depth-of-field")
    sp.add_argument("--format")
    sp.add_argument("--default-count", type=int)
    sp.add_argument("--tags", help="Comma-separated tags")


def main():
    parser = argparse.ArgumentParser(
        description="Manage and run lifestyle image presets (Product × Room × Character × Camera)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # list
    p_list = sub.add_parser("list", help="List all presets")
    p_list.add_argument("--product", help="Filter by product handle")
    p_list.add_argument("--tag", help="Filter by tag")

    # show
    p_show = sub.add_parser("show", help="Show one preset")
    p_show.add_argument("slug")

    # create
    p_create = sub.add_parser("create", help="Create a new preset")
    p_create.add_argument("--slug", required=True)
    _add_preset_field_flags(p_create, require_create=True)

    # update (positional slug renamed to old_slug internally to stay compatible with _fields_from_args)
    p_update = sub.add_parser("update", help="Update an existing preset")
    p_update.add_argument("old_slug", help="Slug of preset to update")
    p_update.add_argument("--new-slug", help="(unsupported — use delete + recreate)")
    _add_preset_field_flags(p_update, require_create=False)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a preset")
    p_delete.add_argument("slug")

    # run
    p_run = sub.add_parser("run", help="Execute a preset via key-visual")
    p_run.add_argument("slug")
    p_run.add_argument("--count", type=int, help="Override default_count")
    p_run.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "show": cmd_show,
        "create": cmd_create,
        "update": cmd_update,
        "delete": cmd_delete,
        "run": cmd_run,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
