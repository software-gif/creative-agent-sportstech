# Room / Environment Builder

> Erstellt konsistente Interior-Szenen mit Multi-Angle Coverage. Generiert einen Raum und dann 4-5 verschiedene Kamerawinkel davon — als Basis für Lifestyle-Compositing.

## Problem
Jeder Gemini-Call generiert einen leicht anderen Raum. Für konsistente Kampagnen braucht man denselben Raum aus verschiedenen Winkeln. Der Room Builder erstellt eine Szene und generiert dann Coverage aus verschiedenen Perspektiven.

## Trigger
Wenn der User ein neues Environment/Raum-Setting für Lifestyle-Shots erstellen will. Wird VOR dem Key Visual Compositing aufgerufen.

## Workflow

### Phase 1: Room Definition
Der User beschreibt den Raum oder wählt einen Preset:

**Presets (aus brand_guidelines.json):**
- `scandinavian` — Hell, luftig, Holz, große Fenster
- `loft_industrial` — Exposed brick, hohe Decken, Metall
- `german_modern` — Clean, weiß, minimalistisch
- `japandi_wellness` — Venetian Plaster, Mikrozement, Holzbalken
- `home_office` — Stehschreibtisch, Monitor, Walking Pad Kontext
- `dark_evening` — Spät-Nachmittag, warmes Licht

**Oder Freestyle:** User gibt eigene Raumbeschreibung.

### Phase 2: Room Prompt Generation
Claude generiert einen detaillierten Room-Prompt als "Ground Truth" und dann 4-5 Kamerawinkel davon.

### LLM System Prompt für Room Angles
```
You are an expert Director of Photography and Visual Continuity Specialist.
Your specific area of expertise is "Coverage" — generating multiple distinct
camera angles of a single static scene without altering the visual reality.

You must output exactly 4 prompts.
Separate each one with *.
NO conversational filler, NO markdown, NO explanations.

Rules:
- Subject Consistency: All furniture, props, lighting IDENTICAL across all shots
- Environment Consistency: Location, lighting, time of day IDENTICAL
- Variation: ONLY camera position, lens, distance, and angle change
- Zero Additions: No new objects not in the original description
- Zero Deletions: No removed elements
- Style Lock: Same aesthetic in all prompts
```

### Phase 3: Image Generation
Alle 4-5 Prompts werden an Gemini gesendet (Raum OHNE Person). Die Ergebnisse werden als Environment-Referenzen gespeichert.

## Ausführung

Der User sagt Claude was er will, z.B.:
- "Erstelle einen Scandinavian-Raum für Walking Pad Shots"
- "Room Builder: Japandi Wellness Room mit Blick auf Wald"
- "Baue ein Loft-Environment für die Rudermaschine"
- Freestyle: "Ein helles modernes Penthouse mit Panoramafenster über der Stadt"

```bash
python3 .claude/skills/room-builder/scripts/main.py \
  --preset "japandi_wellness" \
  --prompts "prompt1*prompt2*prompt3*prompt4" \
  --name "Japandi Forest View"
```

Oder mit Custom-Beschreibung:
```bash
python3 .claude/skills/room-builder/scripts/main.py \
  --description "A serene, high-end minimalist wellness room..." \
  --prompts "prompt1*prompt2*prompt3*prompt4" \
  --name "Custom Wellness Room"
```

## Output
- 4-5 Bilder in Supabase Storage: `environments/{env_id}/angle_1.png`, etc.
- Environment-Record in `environments` Tabelle
- Environment-ID wird für Key Visual Compositing verwendet

## Angle-Generierung Regeln

### Kamera-Perspektiven (aus Weavy)
Aus diesen Kategorien 4-5 auswählen:
- **Eye Level** — Geradeaus auf Augenhöhe
- **Low Angle / Worm's Eye** — Von unten nach oben, betont Raumhöhe
- **High Angle** — Von oben nach unten, zeigt Raumlayout
- **Profile / Side** — Strikt seitlich, parallel zu einer Wand
- **Bird's Eye / Top Down** — Direkt von oben, geometrisches Layout
- **Frontal** — Geradeaus auf eine Wand/Fenster gerichtet

### Konsistenz-Regeln
- Alle Möbel bleiben an EXAKT derselben Position (relative zum Raum)
- Beleuchtung identisch in allen Shots
- Farben, Texturen, Materialien identisch
- Tageszeit identisch
- Kein neues Objekt, kein entferntes Objekt

### Prompt-Qualität
- Kamera-Instruktion am ANFANG des Prompts (damit Angle zuerst gerendert wird)
- Alle visuellen Anchor-Beschreibungen (Farben, Texturen, Licht) in JEDEM Prompt wiederholen
- Professionelle Kamera-Terminologie verwenden (Brennweite, Blende, etc.)

## Verbindungen
- Output wird zusammen mit Character + Product zum Key Visual composited
- Gespeichert in Supabase `environments` Tabelle
- Liest Environment-Presets aus `branding/lifestyle_variance.json`
