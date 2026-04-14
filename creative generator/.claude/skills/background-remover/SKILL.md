# Background Remover

> Normalizes product reference images so they all have transparent backgrounds. Reads originals from `products/<handle>/`, writes cutouts to `products/<handle>/cutouts/`. Key-visual prefers `cutouts/` when present.

## Why
Gemini composites better when product references are cleanly isolated — no white-background pixels leaking into the generated scene as context. Our uploaded references are a mix: some are true alpha PNGs, most are RGB/opaque RGBA (white background). This skill normalizes them.

## How it works
1. Lists every object under `products/<handle>/` in Supabase Storage
2. Downloads each image
3. Skips if it already has meaningful alpha transparency (alpha < 250 somewhere)
4. Otherwise runs `rembg` (u2net model, CPU, offline)
5. Uploads the transparent PNG back to `products/<handle>/cutouts/<same-filename>.png`

Originals are never touched. Key-visual's `get_product_images` checks `cutouts/` first and falls back to the original path.

## Usage
```bash
# Process a single product
python3 .claude/skills/background-remover/scripts/main.py --product woodpad-pro

# Process all products
python3 .claude/skills/background-remover/scripts/main.py --all

# Dry run — report what would happen without uploading
python3 .claude/skills/background-remover/scripts/main.py --product woodpad-pro --dry-run
```

## Model
Uses rembg's default `u2net` model (~170MB, downloads on first run). Good general-purpose segmentation for product photos. If quality is insufficient for a specific product, swap via `--model isnet-general-use` or similar.
