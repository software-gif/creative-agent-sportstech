# Color Variant Generator

> Ändert die Farbe/das Material eines Produkts in einem bestehenden Bild, während die Szene, das Model und alle anderen Elemente identisch bleiben. Bewahrt Materialtreue (z.B. Holzmaserung bleibt sichtbar).

## Problem
Sportstech-Produkte gibt es in mehreren Farben/Materialien (z.B. Rudergerät in Natur-Holz und Schwarz). Anstatt jede Szene komplett neu zu generieren, wird ein bestehendes Bild genommen und nur die Produktfarbe geändert.

## Trigger
Wenn der User ein bestehendes Creative in einer anderen Produktfarbe haben will. Wird NACH dem Key Visual oder Creative Producer aufgerufen.

## Workflow

### Phase 1: Source Image + Target Color
Der User gibt an:
- **Source**: Ein bestehendes Creative (ID oder Pfad)
- **Target Color**: Die gewünschte neue Farbe (z.B. "black", "gray", "wood-natural")
- **Material Instructions**: Spezielle Anweisungen zur Materialtreue

### Phase 2: Prompt Construction
Claude baut den Color-Variant-Prompt:

```
Given the provided image, keep the [product] untouched, just change its color to [target_color].
Make sure to:
Other instruction: [material_instructions]
Logo: [logo_instructions]
```

### Spezielle Material-Regeln

**Holz → Schwarz (Rowing Machine):**
```
The real, rich, natural wood grain should remain.
The wood texture should be vivid and pronounced, with deep, intricate patterns.
Enhance the contrast and depth of the wood grain to make it stand out,
but ensure it remains authentic and true to real wood.
Sportstech logo should be black metallic.
```

**Allgemein:**
- Material-Texturen müssen erhalten bleiben (Holz bleibt Holz, nur Farbe ändert sich)
- Logo-Farbe muss zum neuen Produkt passen
- Szene, Beleuchtung, Model bleiben EXAKT gleich
- Nur das Produkt ändert die Farbe

### Phase 3: Image Generation
Das Source-Bild + der Color-Variant-Prompt werden an Gemini gesendet. Gemini generiert das neue Bild mit geänderter Produktfarbe.

## Ausführung

Der User sagt Claude was er will, z.B.:
- "Ändere die Farbe der Rudermaschine zu Schwarz" (mit bestehendem Bild)
- "Color Variant: Walking Pad in Gray statt Black"
- "Gleiche Szene, aber Laufband in Silber"

```bash
python3 .claude/skills/color-variant/scripts/main.py \
  --source-image "creatives/batch123/001.png" \
  --product "rowing-machine" \
  --target-color "black" \
  --material-instructions "The real, rich, natural wood grain should remain..." \
  --logo-instructions "Sportstech logo should be black metallic"
```

## Output
- Neues Bild in Supabase Storage mit `color_variant` Tag
- Neuer Creative-Record in `creatives` Tabelle verknüpft mit dem Original

## Material-Treue Regeln

### Holz-Produkte (Rowing Machine)
- Holzmaserung MUSS sichtbar bleiben, auch bei Farbwechsel zu Schwarz
- Textur muss "vivid and pronounced" sein mit "deep, intricate patterns"
- Kontrast und Tiefe der Maserung verstärken, aber authentisch halten

### Metall-Produkte (Treadmill, Smith Machine)
- Metall-Finish beibehalten (matt, glänzend, gebürstet)
- Reflexionen und Lichtbrechung an die neue Farbe anpassen

### Logo-Regeln
- Logo-Farbe muss zum neuen Produkt passen
- Auf schwarzem Produkt: "black metallic" oder "silver metallic"
- Auf hellem Produkt: "red" (Standard Sportstech Rot)

## Verbindungen
- Input: Bestehendes Creative aus `creatives` Tabelle
- Output: Neues Creative mit `color_variant` Feld
- Nutzt Produkt-Farboptionen aus `branding/product_knowledge.json`
