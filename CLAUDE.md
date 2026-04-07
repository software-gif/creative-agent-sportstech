# Sportstech Creative Agent

> AI-powered Lifestyle Image Generator for Sportstech — generates photorealistic interior lifestyle shots of fitness equipment using Gemini, managed via Supabase.

## What This Is

A Creative Agent that generates **lifestyle interior photographs** of Sportstech fitness equipment. People using products in realistic home environments — Scandinavian living rooms, industrial lofts, Japandi wellness spaces, home gyms.

**This is NOT an ad creator.** No text overlays, no headlines, no CTAs, no compositor. Pure lifestyle photography.

## Architecture

```
├── board/                    # Next.js 16 — Creative Board UI (view, filter, save)
├── creative generator/       # Python skills + branding data
│   ├── .claude/skills/       # 15 modular skills
│   ├── branding/             # Brand data, product knowledge, room prompts
│   └── .env                  # API keys (not in git)
└── migrations/               # Supabase schema
```

## Tech Stack

- **AI Image Generation:** Google Gemini 2.0 Flash Preview
- **Database + Storage:** Supabase (project: qezyrkarmeaonenspeth, Frankfurt)
- **Frontend:** Next.js 16 + React 19 + Tailwind CSS 4
- **Platform:** Shopware 6 (sportstech.de)

## 4-Phase Lifestyle Pipeline

Based on Weavy Workflows from Clemente (Creative Lead):

1. **Character Builder** → Consistent model identity (headshot, full body front, profile)
2. **Room Builder** → Interior scene with multi-angle coverage
3. **Key Visual** → Composite character + product + room → lifestyle image
4. **Multishot** → Camera angle variations + color variants

## Products (10)

Walking Pad: WoodPad Pro | Treadmill: F37s Pro | Speedbike: sBike | Ergometer: X150 | Crosstrainer: sCross | Rowing Machine: AquaElite | Power Station: sGym Pro, HGX50 | Smith Machine: SXM200 | Vibration Plate: sVibe

All products have Freisteller (reference images) + Lifestyle Examples + Renders in Supabase Storage.

## Key Rules

- **Lifestyle only** — No text on images, no overlays, no ad layouts
- **Product accuracy** — Products must be EXACT recreations of reference images, never simplified
- **Correct usage** — People must use equipment correctly (correct poses, body mechanics)
- **Full diversity** — Any age, gender, body type, skin tone — no restrictions
- **Soft lighting** — No high contrast, natural interior lighting
- **Camera system** — 6 angles (Close-Up, Over-Shoulder, Bird's Eye, Eye-Level, Wide, Worm's Eye) × 5 positions (Front, Profile, 3/4 Front, 3/4 Back, Back)

## Environment Variables

```bash
# creative generator/.env
SUPABASE_URL=https://qezyrkarmeaonenspeth.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...  # For backend operations
GEMINI_API_KEY=...
```

## Team

- **Clemente Pesce** — Creative Lead @ Sportstech
- **Florian Deil** — Strategy/PM @ Sportstech
- **Lingesvar** — 3D/Asset Production @ Sportstech
- **Johannes Hoser** — Developer @ Scalemaker
