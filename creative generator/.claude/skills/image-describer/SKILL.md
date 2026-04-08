# Image Describer

> Analyzes product reference images using Gemini text model and generates ultra-detailed visual descriptions. Run ONCE per product, results are cached and reused by all generation skills.

## Problem
AI image generation models (Gemini/Nano Banana Pro) don't accurately recreate products from reference images alone. They need an extremely detailed TEXT description of every visual element — colors, shapes, proportions, materials, displays, buttons, LEDs, branding.

## How It Works
1. Takes ALL Freisteller (cutout) images for a product from Supabase
2. Sends them to Gemini 2.5 Flash (text model, NOT image generation)
3. Gemini analyzes every detail and generates a comprehensive description
4. Description is cached in `branding/product_descriptions/{handle}.txt`
5. The key-visual and other generation skills read this cached description

## What Gets Analyzed
For each product, the describer extracts:
- **Shape & Silhouette** — exact form from every angle, proportions
- **Colors** — primary body, accents, LEDs, screen bezels, rails
- **Display** — size, position, shape, content shown, border
- **Controls** — buttons (colors, positions), knobs, safety features
- **Branding** — EXACT text, font, position, color of all logos
- **Materials** — metal, plastic, rubber, wood. Matte/glossy finish
- **LED Accents** — where, what color, how they follow the body shape
- **Unique Features** — what makes THIS product different from generic equipment
- **Human Interaction** — where hands go, where feet go, body orientation, which direction the person faces

## Usage
```bash
# Analyze a single product
python3 .claude/skills/image-describer/scripts/main.py --product f37s-pro

# Analyze ALL products
python3 .claude/skills/image-describer/scripts/main.py --all

# Force re-analyze (ignore cache)
python3 .claude/skills/image-describer/scripts/main.py --product f37s-pro --force
```

## Output
- Cached description: `branding/product_descriptions/{handle}.txt`
- ~3000-6000 characters of obsessively detailed visual description
- Used by key-visual, multishot, and other generation skills

## Trigger
Run this ONCE when a new product is uploaded. After that, the description is cached and automatically picked up by generation skills.
