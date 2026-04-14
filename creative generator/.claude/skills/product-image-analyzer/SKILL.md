# Product Image Analyzer

> Builds a metadata catalog of every product reference image so `key-visual` can pick the right references for a given shot instead of random-sampling.

## Why
We have 50+ render cutouts per product across multiple colour variants and camera angles. Random sampling hits detail shots (back-end controls, front console, side rails) only some of the time, which is why product accuracy keeps drifting on specific features.

This skill analyses every image once with Gemini 2.5 Flash Vision, writes a machine-readable catalog, and leaves it in `branding/product_references/<handle>.json`. `key-visual`'s smart selector then reads the catalog and chooses references that match the target camera angle, include the right colour variant, and cover the must-match features.

## What gets extracted per image

```json
{
  "path": "renders/woodpad-pro/cutouts/17.png",
  "camera_angle": "back_3_4_low",
  "framing": "detail_close_up",
  "variant": "wood_light",
  "visible_parts": ["back_controls", "power_port", "end_cap", "side_rail"],
  "detail_richness": 9,
  "key_features": "Shows the three rear control buttons and cable port at high detail."
}
```

## Usage
```bash
# Analyze one product (skips images that already have catalog entries)
python3 .claude/skills/product-image-analyzer/scripts/main.py --product woodpad-pro

# Analyze all products
python3 .claude/skills/product-image-analyzer/scripts/main.py --all

# Force re-analysis (ignore cache)
python3 .claude/skills/product-image-analyzer/scripts/main.py --product woodpad-pro --refresh
```

## Output
`branding/product_references/<handle>.json` — catalog keyed by storage path. Idempotent: rerunning only analyses paths not yet in the catalog.

## Cost
~$0.001 per image × ~135 total images = ~$0.14 one-off. After that it's free until new product images are uploaded.
