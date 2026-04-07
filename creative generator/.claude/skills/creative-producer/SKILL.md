# Creative Producer

> Generiert Static Ads via Gemini 3.1 Flash Image Generation basierend auf Ad Angles, Brand Guidelines und Produktbildern. Inkl. Multi-Layer Compositor (Logo, Social Proof, Payment Icons). Unterstützt On-Brand UND Off-Brand/Ugly Ads sowie 2-Step Workflow (Raw + Composited).

## Problem
Manuell Static Ads zu erstellen ist zeitaufwändig und erfordert Design-Expertise. Der Creative Producer automatisiert die Generierung von brand-konformen UND off-brand Static Ads basierend auf der Andromeda-Diversification-Logik. Off-Brand/Ugly Ads konvertieren auf Meta deutlich besser — der Agent kann das, was der Kunde als ehemaliger Creative Director selbst nicht schafft.

## Trigger
Nachdem Prompts (von sales-event-producer, competitor-cloner oder manuell) erstellt wurden.

## Workflow

### 2-Step Workflow (empfohlen von Kunde)
**Step 1 — Raw Image:** Lifestyle-/Produktbild OHNE Text-Overlay generieren. Andre kann diese Rohbilder auch für Produktgalerie, Social Media etc. weiterverwenden.
**Step 2 — Composited:** Text-Overlay + Compositor-Elemente (Logo, Social Proof etc.) auf das Raw Image anwenden.

### Ablauf
1. JSON-Prompts werden übergeben (von sales-event-producer, competitor-cloner oder manuell)
2. Script sendet JSON-Prompt + Produktbild an Gemini 3.1 Flash
3. **Raw Image** wird gespeichert (generation_mode: "raw")
4. **Composited Version** wird erstellt: Text-Overlay via Gemini + Multi-Layer Compositor (Logo, Social Proof, Payment Icons)
5. Upload nach Supabase Storage + DB Update
6. Creatives erscheinen live im Board

### Creative Styles
- **on_brand** — Brand-Fonts (Lora Bold + Assistant Medium), CI-Farben, clean Layout, premium
- **off_brand** — Ugly Ads / Native-Look. Keine CI-Fonts, freie Farben, organisch, wie UGC. Konvertiert BESSER auf Meta.

## Inputs
- JSON-Prompts-Datei (von anderen Skills oder manuell erstellt)
- `--brand-id` (optional, auto-detected)
- `--raw-only` (optional, generiert nur Raw Images ohne Text-Overlay)
- Produktbilder in `products/images/<handle>/`
- Overlay-Assets in `branding/`:
  - `logo_dark.png` / `logo_white.png` — Brand Logo
  - `social_proof.png` — Trust Badge (optional)
  - `payment_icons.png` — Payment Methods (optional)
  - `color_variants.png` — Farbpunkte (optional)

## Outputs
- **Raw Images** → Supabase Storage `creatives/{brand_id}/{batch_id}/raw/` (ohne Text/Overlays)
- **Composited Creatives** → Supabase Storage `creatives/{brand_id}/{batch_id}/` (mit Text + Overlays)
- DB-Einträge in `creatives` Tabelle mit `status='done'`, `image_url`, `storage_path`, `creative_style`
- Lokales Backup in `creatives/<batch_id>/`
- `manifest.json` pro Batch

## Formate
- **4:5** (1536×1920) — Feed
- **9:16** (1080×1920) — Story (mit 1:1 Safe Zone)

## Multi-Layer Compositor
Nach der Gemini-Generierung werden folgende Overlays automatisch composited (wenn die Dateien existieren):

1. **Logo** — Auto-Detect: dunkles Logo auf hellem Hintergrund, weißes auf dunklem
2. **Social Proof** — Trust Badge (z.B. "⭐ 4.8 | 500+ zufriedene Kunden")
3. **Payment Icons** — PayPal, Visa, Mastercard etc.
4. **Farbvarianten** — Kleine Kreise mit verfügbaren Farben

Alle Overlays sind optional — wenn die PNG-Datei nicht existiert, wird sie übersprungen.

## Scripts
- `scripts/main.py` — Orchestrierung: Gemini API Call, Compositor, Supabase Upload
- `scripts/prompt_schema.json` — JSON-Prompt-Schema (Single Source of Truth)

## Ausführung
```bash
# Direkt mit Prompts-Datei (generiert Raw + Composited)
python3 .claude/skills/creative-producer/scripts/main.py --prompts-file creatives/prompts.json

# Nur Raw Images (ohne Text-Overlay, ohne Compositor)
python3 .claude/skills/creative-producer/scripts/main.py --prompts-file creatives/prompts.json --raw-only

# Brand-ID wird automatisch aus DB gelesen (nur 1 Brand)
```

## Dependencies
- Python 3
- `requests` (pip)
- `python-dotenv` (pip)
- `Pillow` (pip) — für Compositor
- Gemini API Key in `.env` (`GEMINI_API_KEY`)
- Supabase Credentials in `.env`

## Wichtige Regeln für Bild-Prompts

### Produkt NICHT in negativen Szenen
Bei Szenen die etwas Negatives kommunizieren darf das beworbene Produkt NIEMALS im Bild erscheinen. `scene_type: "negative"` blockt automatisch das Produktbild.

### Nur echte Produktvarianten
Zeige nur Produktfarben die in `brand.json` existieren.

### Safe Zone (9:16 Format)
Hauptcontent (Produkt, Headline, Benefits, CTA) im mittleren 1:1 Bereich. Logo oben, Social Proof unten — außerhalb der 1:1 Zone.

### Schriftart
**On-Brand:** Lora Bold für Headlines (Serif, edel), Assistant Medium für Body (Sans-Serif, klar). Immer deutsch.
**Off-Brand:** Freie Schriftwahl — System-Fonts, handschriftliche Fonts, einfache Sans-Serif. Kein CI-Font.

## Verbindungen
- Wird von `sales-event-producer` und `competitor-cloner` als Engine genutzt
- Liest Output von `angle-generator`, `product-scraper`, `ad-library-scraper`
- Referenziert `meta-andromeda` Knowledge
- Liest `branding/brand_guidelines.json`
