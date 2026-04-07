# Prompt Generator

> Generiert dynamisch einzigartige Creative-Prompts per LLM (Claude). Jeder Prompt ist ein Unikat — unbegrenzte Varianz für Lifestyle & Product Creatives.

## Problem
Fixe Prompt-Templates führen zu repetitiven Creatives. 12 vordefinierte Posen sind schnell erschöpft. Der Prompt Generator nutzt Claude als LLM um immer neue, einzigartige Kombinationen zu erstellen — basierend auf dem was funktioniert.

## Trigger
Wenn der User neue Creatives generieren will. Wird VOR dem Creative Producer aufgerufen.

## Workflow
1. Claude liest alle Knowledge-Dateien (Produktwissen, Angles, Varianz-Pools, Meta Best Practices)
2. Claude generiert N einzigartige Prompts im exakten JSON-Format des Creative Producers
3. Jeder Prompt hat eine einzigartige Kombination aus: Model, Pose, Setting, Outfit, Angle, Hook
4. Output wird als `creatives/prompts.json` gespeichert
5. Creative Producer wird mit `--prompts-file creatives/prompts.json` aufgerufen

## Ausführung

Der User sagt Claude was er will, z.B.:
- "Generiere 10 Lifestyle Creatives für [Produkt], On-Brand, Sommer, 4:5"
- "Mach 5 Off-Brand Ugly Ads für [Produkt], 9:16 Story"
- "Erstelle 8 Creatives: 4x Lifestyle On-Brand, 4x Off-Brand, Mix aus Feed und Story"

Claude liest dann:
```
branding/product_knowledge.json    → Produktwissen
branding/lifestyle_variance.json   → Varianz-Pools (Models, Posen, Settings, Outfits)
branding/brand.json                → Brand, Target Audience, Winning Angles
branding/brand_guidelines.json     → Farben, Fonts, Styles
branding/meta_creative_best_practices.json → Meta Performance Rules
angles/angles.json                 → Ad Angles mit Hooks
```

Und generiert die Prompts nach diesem Schema:

## Prompt-Generierung Regeln

### Varianz sicherstellen
- JEDER Prompt muss ein EINZIGARTIGES Model beschreiben (Alter, Haarfarbe, Haarlänge, Körperbau, Hautton — alles variieren)
- JEDE Pose muss ANDERS sein — nicht zweimal dieselbe Pose im Batch
- JEDES Setting muss sich unterscheiden oder zumindest anders beschrieben sein
- JEDER Hook/Headline muss einzigartig sein
- Nutze die Pools in lifestyle_variance.json als INSPIRATION, aber erfinde auch NEUE Kombinationen

### Was funktioniert (bewährt)
- Verschiedene natürliche Posen aus `lifestyle_variance.json`
- Blick in die Kamera (Testimonial-Style)
- Verschiedene Environments aus `lifestyle_variance.json`
- Warmes Licht, natürliche Atmosphäre
- Produkt wird korrekt benutzt wie in `product_knowledge.json` beschrieben

### Was NICHT funktioniert (vermeiden)
- Unrealistische Posen oder falsche Produktnutzung
- Settings die nicht zur Zielgruppe passen
- Fehler die in `product_knowledge.json` unter `must_avoid` stehen

### Produkt-Accuracy
- IMMER `product_knowledge.json` lesen und die dort definierten Regeln beachten
- IMMER `must_match` Anforderungen in den Prompt übernehmen
- IMMER `must_avoid` Fehler explizit ausschließen
- IMMER die korrekte Anwendungspose aus `correct_usage_poses` nutzen

### Text-Overlays
- NUR Headline + Subheadline (maximal)
- Headline: 3-5 Wörter, Benefit-driven
- Subheadline: 3-5 Wörter
- Korrekte deutsche Rechtschreibung mit Umlauten
- Jeder Text EXAKT EINMAL

### Output-Format
Exaktes JSON-Format wie in `scripts/prompt_schema.json` definiert. Jeder Prompt enthält:
- meta (angle, sub_angle, variant, scene_type, creative_style, creative_type, season, environment, product_category, generation_mode, format, resolution)
- canvas (background, lighting, color_mood)
- layout (zones)
- product (display_mode, position, scale)
- text_overlays (headline + subheadline)
- visual_elements
- brand_elements
- generation_instructions (style_reference, must_include, must_avoid, quality_notes, text_rendering_notes)

## Verbindungen
- Output wird von `creative-producer` als Input genutzt
- Liest `product_knowledge.json`, `lifestyle_variance.json`, `brand.json`, `angles.json`, `meta_creative_best_practices.json`
