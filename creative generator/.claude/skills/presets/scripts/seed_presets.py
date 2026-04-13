#!/usr/bin/env python3
"""Seed the creative_presets table with 8 curated starter presets.

Idempotent: existing slugs are skipped, not overwritten.

Each seed combines a product with a hand-picked room (from room_prompts.json)
and a thoughtful camera setup. Character is left on auto_rotate so the model
pool in lifestyle_variance.json gets used.
"""

import json
import os
import sys

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


SEED_PRESETS = [
    {
        "slug": "f37s-scandi-morning",
        "name": "F37s Pro — Scandi Morning Run",
        "description": "Treadmill running session in a bright Scandi-minimalist living room. Morning natural light, model rotation across the pool for diversity.",
        "product_handle": "f37s-pro",
        "room_preset": "scandi_minimal",
        "character_mode": "auto_rotate",
        "pose": "Running at moderate pace on the treadmill, arms relaxed, focused forward gaze. Body and face point toward the display console.",
        "shot_size": "Wide",
        "camera_angle": "Eye level",
        "character_angle": "3/4 angle",
        "lens": "35mm",
        "depth_of_field": "f/4",
        "format": "9:16",
        "default_count": 3,
        "tags": ["scandinavian", "morning", "treadmill", "cardio", "bright"],
    },
    {
        "slug": "woodpad-walnut-study",
        "name": "WoodPad Pro — Walnut Study Workday",
        "description": "Walking pad under a standing desk in a modern walnut-accent study. Casual productivity, work-from-home context.",
        "product_handle": "woodpad-pro",
        "room_preset": "walnut_accent_study",
        "character_mode": "auto_rotate",
        "pose": "Walking at a slow, comfortable pace on the walking pad, looking slightly down toward a laptop on the standing desk. Relaxed shoulders.",
        "shot_size": "Medium Shot",
        "camera_angle": "Eye level",
        "character_angle": "3/4 angle",
        "lens": "50mm",
        "depth_of_field": "f/2.8",
        "format": "9:16",
        "default_count": 3,
        "tags": ["walking_pad", "home_office", "study", "productivity", "warm"],
    },
    {
        "slug": "aquaelite-japandi-serene",
        "name": "AquaElite — Japandi Wellness Row",
        "description": "Rowing machine session in a serene Japandi room with a mid-century sideboard. Meditative, wellness-forward atmosphere.",
        "product_handle": "aqua-elite",
        "room_preset": "japandi_bookcase",
        "character_mode": "auto_rotate",
        "pose": "Seated on the rowing machine mid-stroke, back straight, arms pulling toward the torso, legs partially extended. Focused calm expression.",
        "shot_size": "Wide",
        "camera_angle": "Eye level",
        "character_angle": "Profile",
        "lens": "50mm",
        "depth_of_field": "f/4",
        "format": "9:16",
        "default_count": 3,
        "tags": ["japandi", "wellness", "rowing", "serene", "morning"],
    },
    {
        "slug": "sbike-loft-golden",
        "name": "sBike — Industrial Loft Golden Hour",
        "description": "Indoor cycling intensity against an urban loft backdrop at golden hour. Dynamic, high-energy training vibe.",
        "product_handle": "sbike",
        "room_preset": "urban_loft_golden",
        "character_mode": "auto_rotate",
        "pose": "Intense pedaling on the sBike, leaning slightly forward into the handlebars, focused determined expression, sweat on brow.",
        "shot_size": "Medium Shot",
        "camera_angle": "Slightly above",
        "character_angle": "3/4 angle",
        "lens": "50mm",
        "depth_of_field": "f/2.8",
        "format": "9:16",
        "default_count": 3,
        "tags": ["industrial", "evening", "cycling", "intense", "moody"],
    },
    {
        "slug": "scross-penthouse-skyline",
        "name": "sCross — Penthouse Skyline Workout",
        "description": "Crosstrainer session in a luxury penthouse with urban skyline view. Premium, aspirational, daylight.",
        "product_handle": "scross",
        "room_preset": "luxury_penthouse",
        "character_mode": "auto_rotate",
        "pose": "Full cross-training motion on the sCross — arms and legs in opposing rhythm, upper body upright, confident focused expression.",
        "shot_size": "Wide",
        "camera_angle": "Eye level",
        "character_angle": "3/4 angle",
        "lens": "35mm",
        "depth_of_field": "f/4",
        "format": "9:16",
        "default_count": 3,
        "tags": ["luxury", "modern", "crosstrainer", "premium", "skyline"],
    },
    {
        "slug": "sgym-pro-industrial-lift",
        "name": "sGym Pro — Industrial Home Gym Lift",
        "description": "Power station strength training in a high-end industrial home gym. Wood paneling, concrete floor, strong dramatic light.",
        "product_handle": "sgym-pro",
        "room_preset": "industrial_home_gym",
        "character_mode": "model_pool",
        "model_pool_id": "m4",
        "pose": "Seated shoulder press on the sGym Pro station, back pressed firmly against the pad, arms pushing overhead, focused intense expression.",
        "shot_size": "Wide",
        "camera_angle": "Slightly below",
        "character_angle": "3/4 angle",
        "lens": "35mm",
        "depth_of_field": "f/2.8",
        "format": "9:16",
        "default_count": 3,
        "tags": ["industrial", "strength", "power_station", "moody", "dramatic"],
    },
    {
        "slug": "sxm200-moody-squat",
        "name": "SXM200 — Moody Lounge Squat Session",
        "description": "Smith machine squats in a moody twilight lounge with charcoal walls. Dark, cinematic, serious training tone.",
        "product_handle": "sxm200",
        "room_preset": "moody_lounge",
        "character_mode": "auto_rotate",
        "pose": "Mid-squat on the SXM200 Smith Machine, barbell across upper back, thighs parallel to the floor, focused intense expression.",
        "shot_size": "Wide",
        "camera_angle": "Ground level",
        "character_angle": "Front facing",
        "lens": "24mm",
        "depth_of_field": "f/5.6",
        "format": "9:16",
        "default_count": 3,
        "tags": ["moody", "strength", "smith_machine", "evening", "cinematic"],
    },
    {
        "slug": "svibe-japandi-morning",
        "name": "sVibe — Japandi Morning Vibration",
        "description": "Vibration plate wellness session in a bright japandi room with mid-century sideboard. Calm, mindful, morning light.",
        "product_handle": "svibe",
        "room_preset": "japandi_sideboard",
        "character_mode": "auto_rotate",
        "pose": "Standing upright on the sVibe vibration plate in a relaxed athletic stance, arms slightly forward for balance, calm focused expression.",
        "shot_size": "Medium Shot",
        "camera_angle": "Eye level",
        "character_angle": "3/4 angle",
        "lens": "50mm",
        "depth_of_field": "f/4",
        "format": "9:16",
        "default_count": 3,
        "tags": ["japandi", "wellness", "vibration_plate", "morning", "calm"],
    },
]


def _headers():
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    if not SUPABASE_URL or not key:
        sys.exit("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY not set in .env")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def get_brand_id():
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/brands?slug=eq.sportstech&select=id",
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        sys.exit("ERROR: Brand 'sportstech' not found.")
    return rows[0]["id"]


def existing_slugs(brand_id):
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/creative_presets",
        headers=_headers(),
        params={"brand_id": f"eq.{brand_id}", "select": "slug"},
        timeout=15,
    )
    if resp.status_code == 404:
        sys.exit(
            "ERROR: Table 'creative_presets' does not exist. "
            "Run migrations/002_creative_presets.sql in Supabase first."
        )
    resp.raise_for_status()
    return {r["slug"] for r in resp.json()}


def insert_preset(brand_id, preset):
    body = {**preset, "brand_id": brand_id}
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/creative_presets",
        headers={**_headers(), "Prefer": "return=representation"},
        json=body,
        timeout=15,
    )
    if resp.status_code >= 400:
        print(f"  FAIL {preset['slug']}: {resp.status_code} {resp.text[:200]}")
        return False
    print(f"  ✓ {preset['slug']}")
    return True


def main():
    print("Seeding creative_presets...")
    brand_id = get_brand_id()
    existing = existing_slugs(brand_id)

    if existing:
        print(f"  Found {len(existing)} existing preset(s), will skip those.")

    created = 0
    skipped = 0
    for preset in SEED_PRESETS:
        if preset["slug"] in existing:
            print(f"  - {preset['slug']} (exists, skipped)")
            skipped += 1
            continue
        if insert_preset(brand_id, preset):
            created += 1

    print(f"\nDone. Created: {created}, Skipped: {skipped}, Total in table: {created + len(existing)}")


if __name__ == "__main__":
    main()
