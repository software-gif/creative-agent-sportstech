# Character Builder

> Erstellt konsistente Model-Identitäten für Lifestyle-Shots. Generiert 3 Referenzbilder (Headshot, Full Body Front, Full Body Profile) die als Basis für alle weiteren Shots dienen.

## Problem
AI-generierte Bilder erzeugen bei jeder Generation eine neue Person. Für konsistente Kampagnen braucht man dasselbe Model über mehrere Shots hinweg. Der Character Builder erstellt eine Model-Identität die als Referenz für alle weiteren Generierungen dient.

## Trigger
Wenn der User ein neues Model/Character für eine Kampagne erstellen will. Wird VOR dem Creative Producer oder Key Visual Generator aufgerufen.

## Workflow

### Phase 1: Character Definition
Der User gibt Model-Parameter an (oder Claude fragt interaktiv):
- **Gender**: Male / Female / Non-binary
- **Age**: Alter in Jahren
- **Height**: Größe
- **Physique**: z.B. "Soft medium build", "Athletic lean", "Approachable sporty"
- **Skin type / Race**: z.B. "Fair Nordic", "Dark African", "Racially ambiguous"
- **Hairstyle**: z.B. "Straightened natural hair in tight ponytail", "Short brown bob"
- **Expression**: z.B. "Slight smile", "Determined focused", "Calm confident"
- **Clothes**: z.B. "Training clothes", "Black cropped top and shorts"
- **Background**: Standardmäßig `#f8f8f8` (Studio-grau)

### Phase 2: Prompt Generation
Claude generiert exakt 3 Prompts, getrennt durch `*`:

**Text 1 — Headshot Portrait:**
Studio-Headshot mit allen Character-Details. Soft even lighting, clean background.

**Text 2 — Full Body Front:**
Ganzkörper-Portrait von vorne. Muss Identität und Beleuchtung aus Text 1 bewahren.
- Outfit anwenden (z.B. "black cropped top and tight form-fitting short shorts")
- Kopf und Füße NICHT abschneiden
- Weite Rahmung

**Text 3 — Full Body Profile:**
Ganzkörper-Seitenansicht. Muss Identität aus Text 1 bewahren.
- Gleiches Outfit wie Text 2
- Seitliche Kamera, nicht abgeschnitten

### Phase 3: Image Generation
Alle 3 Prompts werden an Gemini gesendet. Die Ergebnisse werden in Supabase gespeichert (`characters` Tabelle).

## Ausführung

Der User sagt Claude was er will, z.B.:
- "Erstelle ein weibliches Model, 30 Jahre, athletisch, dunkle Haut"
- "Baue einen männlichen Character: 45, graue Haare, kräftig, europäisch"
- "Character Builder: Female, 25, slim, Asian, long black hair, energetic"

Claude generiert die 3 Prompts und ruft dann das Script auf:

```bash
python3 .claude/skills/character-builder/scripts/main.py \
  --gender "Female" \
  --age 30 \
  --height "5ft 8 inches" \
  --physique "Soft, Medium build" \
  --skin "darkish skin, racially ambiguous" \
  --hairstyle "straightened natural hair, shoulder length, in a tight back ponytail" \
  --expression "slight smile" \
  --clothes "Training Clothes" \
  --background "#f8f8f8" \
  --prompts "prompt1*prompt2*prompt3"
```

## Output
- 3 Bilder in Supabase Storage: `characters/{character_id}/headshot.png`, `full_body_front.png`, `full_body_profile.png`
- Character-Record in `characters` Tabelle mit allen Parametern
- Character-ID wird für spätere Key Visual Generation verwendet

## Prompt-Generierung Regeln

### LLM System Prompt
```
You are going to receive a subject. Your job is to propose 3 different prompts that describe the same exact model, each in a different camera angle.

Separate each one with "*".
Don't use "*" in any other place.
Output only prompts.
```

### Prompt-Qualität
- Jeder Prompt muss ALLE physischen Details enthalten (Redundanz ist gewollt für Konsistenz)
- Studio-Lighting in allen 3 Prompts identisch
- Background in allen 3 Prompts identisch
- Outfit-Details exakt gleich in Text 2 und Text 3
- Text 1 referenziert als "image reference" für Text 2 und 3

### Must-Do
- Full Body Shots müssen Kopf BIS Füße zeigen — kein Cropping
- Identität (Gesicht, Hautton, Haarfarbe) muss über alle 3 Shots konsistent sein
- Physique-Beschreibung präzise: "approachable sporty — athletic, strong, and real, showing muscle engagement and natural definition"

## Verbindungen
- Output wird von `creative-producer` als Character-Referenz genutzt
- Output wird von `room-builder` + Key Visual Compositing verwendet
- Gespeichert in Supabase `characters` Tabelle
