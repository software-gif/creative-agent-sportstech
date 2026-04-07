# Multishot Generator

> Nimmt ein bestehendes Key Visual und generiert Variationen mit verschiedenen Kameraeinstellungen. Gleiche Szene, gleiches Model, gleiches Produkt — nur Kamera-Parameter ändern sich.

## Problem
Ein einzelnes Key Visual reicht nicht für eine Kampagne. Man braucht denselben Shot aus verschiedenen Winkeln, Brennweiten und Schärfetiefen. Der Multishot Generator erstellt diese Variationen automatisch.

## Trigger
Wenn der User von einem bestehenden Creative mehrere Kamera-Variationen haben will. Wird NACH dem Key Visual oder Creative Producer aufgerufen.

## Workflow

### Phase 1: Source + Variables
Der User gibt an:
- **Source Image**: Bestehendes Creative (ID oder Pfad)
- **Kamera-Variablen**: Eine oder mehrere der folgenden Parameter ändern

### Kamera-Variablen (aus Weavy Workflows)

| Variable | Optionen |
|----------|----------|
| **Shot Size** | Extreme Wide, Wide, Medium Shot, Close Up, Extreme Close Up, Bird's Eye |
| **Camera Angle** | Eye level, Slightly above, High angle, Slightly below, Low angle, Ground level, Keep the Same |
| **Character Angle** | Front facing, 3/4 angle, Profile, Over the shoulder, Back view, Top View, Keep the Same |
| **Lenses** | 14mm, 24mm, 35mm, 50mm, 85mm, 135mm, 200mm, Keep the Same |
| **Depth of Field** | f/1.2, f/1.8, f/2.8, f/4, f/5.6, f/8, f/16, Keep the Same |

**Plus optionale Zusatz-Anweisungen:**
- **Model Detail**: z.B. "Let the model touch the display of the treadmill"
- **Other Instructions**: z.B. "The Walking Pad must be a literal recreation of the reference images"

### Phase 2: Prompt Construction
```
Keep the scene, the character and the product the same as in Image 1, but change those variables to:
Camera Control: {character_angle}
Shot Size: {shot_size}
Camera Angle: {camera_angle}
Character Angle: {character_angle}
Lenses: {lens}
Depth of Field: {depth_of_field}
Other instructions: {other_instructions}
Model Detail: {model_detail}
```

### Phase 3: Image Generation
Source-Bild + Multishot-Prompt werden an Gemini gesendet.

## Ausführung

Der User sagt Claude was er will, z.B.:
- "Multishot: Ground Level, 24mm, f/5.6 — gleiches Bild"
- "Mach 3 Variationen: Close Up f/1.8, Bird's Eye f/8, Over the Shoulder 85mm"
- "Gleiche Szene aber Low Angle, Front Facing, 14mm"

```bash
python3 .claude/skills/multishot/scripts/main.py \
  --source-image "creatives/batch123/001.png" \
  --shot-size "Extreme Close Up" \
  --camera-angle "Ground level" \
  --character-angle "Front facing" \
  --lens "50mm" \
  --depth-of-field "f/8" \
  --other-instructions "The Walking Pad must be a literal recreation of the reference images" \
  --model-detail "Let the model touch the display"
```

Oder Batch-Mode für mehrere Variationen:
```bash
python3 .claude/skills/multishot/scripts/main.py \
  --source-image "creatives/batch123/001.png" \
  --batch '[
    {"shot_size": "Close Up", "lens": "85mm", "depth_of_field": "f/1.8"},
    {"shot_size": "Bird'\''s Eye", "camera_angle": "High angle", "lens": "24mm", "depth_of_field": "f/8"},
    {"shot_size": "Wide", "camera_angle": "Ground level", "lens": "14mm", "depth_of_field": "f/5.6"}
  ]'
```

## Output
- Neue Bilder in Supabase Storage
- Neue Creative-Records mit allen Kamera-Settings als Metadaten
- Verknüpfung mit Source Creative über `batch_id`

## Variablen-Logik

### "Keep the Same"
Wenn eine Variable auf "Keep the Same" steht, wird sie nicht im Prompt erwähnt → Gemini behält den Wert aus dem Source-Bild bei.

### Empfohlene Kombinationen
- **Produktdetail**: Extreme Close Up + 85mm + f/1.8 + Over the shoulder
- **Raumübersicht**: Wide + 24mm + f/8 + Bird's Eye / High angle
- **Dramatisch**: Wide + Ground level + 14mm + f/5.6 + Front facing
- **Intim**: Medium Shot + Eye level + 50mm + f/2.8 + 3/4 angle
- **Display-Interaktion**: Close Up + Slightly above + Over the shoulder + 50mm + f/4

## Verbindungen
- Input: Bestehendes Creative aus `creatives` Tabelle oder lokaler Pfad
- Output: Neue Creatives mit Kamera-Settings in `creatives` Tabelle
- Kamera-Presets aus `branding/lifestyle_variance.json`
