# Key Visual Generator

> Composites Character + Product + Room into a final lifestyle photograph. The core generation skill that combines all elements into one coherent image via Gemini.

## Problem
Character Builder, Room Builder, and Product Images exist as separate elements. The Key Visual Generator brings them together into a single, photorealistic lifestyle image — a person using a Sportstech product in a beautiful interior environment.

## Trigger
When the user wants to generate a lifestyle image. This is the main generation skill.

## Workflow

### Phase 1: Gather References
Claude collects the inputs:
- **Product**: Reference images from Supabase (`products/<handle>/`)
- **Character**: Either a saved Character (from character-builder) or a new description
- **Environment**: Either a saved Room (from room-builder), a preset from `room_prompts.json`, or a freestyle description
- **Camera Settings**: From `lifestyle_variance.json` camera_presets or custom

### Phase 2: Build the Composite Prompt
Claude constructs a precision compositing prompt following the Weavy pattern:

```
You are a precision compositing engine. Your task is to synthesize distinct visual inputs into a single coherent frame.

Identity: Strictly adhere to the facial and physical features of the subject in [Character Reference].
Product Accuracy: The [product] must be a literal recreation of [Product References]; do not simplify or genericize its design.
Environment: Use the spatial geometry, lighting direction, and color palette of [Room Reference].

Constraint: Do not introduce any elements not present in the references.
Integration: Blend seamlessly while maintaining correct product usage pose.
```

### Phase 3: Generate via Gemini
Send the composite prompt + all reference images (product cutouts, character refs, room refs) to Gemini 2.0 Flash Image Generation.

### Phase 4: Store Result
Upload generated image to Supabase Storage and create a `creatives` record with all metadata.

## Ausführung

### Quick (no pre-built character/room)
```
"Erstelle ein Lifestyle-Bild: Frau, 30, athletisch, nutzt den F37s Pro im Scandinavian Wohnzimmer"
```
Claude builds character + room description inline and generates.

### Full Pipeline (with references)
```
"Key Visual: Character c1234, Room r5678, Produkt F37s Pro, 3/4 angle, 50mm, f/4"
```

```bash
python3 .claude/skills/key-visual/scripts/main.py \
  --product "f37s-pro" \
  --character-id "c1234" \
  --environment-id "r5678" \
  --room-preset "scandinavian" \
  --shot-size "Wide" \
  --camera-angle "Eye level" \
  --character-angle "3/4 angle" \
  --lens "50mm" \
  --depth-of-field "f/4" \
  --format "9:16"
```

### Batch Mode
```bash
python3 .claude/skills/key-visual/scripts/main.py \
  --product "f37s-pro" \
  --room-preset "scandinavian" \
  --batch 5 \
  --vary "model,camera_angle,lens"
```
Generates 5 images with different models and camera settings.

## Prompt Construction Rules

### Product Accuracy (CRITICAL)
- Read `product_knowledge.json` for the product's `must_match` and `must_avoid` rules
- Send ALL product reference images to Gemini (up to 8)
- Include explicit instruction: "The [product] must be a literal recreation of the reference images; do not simplify or genericize its design."

### Character Integration
- If character-id provided: send headshot + full body as reference
- If inline description: describe age, gender, physique, skin, hair, expression, clothes
- Include correct usage pose from `product_knowledge.json` → `correct_usage_poses`

### Environment Integration
- If room preset: use prompt from `room_prompts.json`
- If environment-id: use saved room prompt
- Include lighting, furniture, materials from the room description

### Camera Settings
- Place camera instruction EARLY in the prompt
- Use professional terminology: focal length, aperture, camera position
- Reference `lifestyle_variance.json` camera_presets for standard setups

### Quality Standards
- Output must look like professional photography shot on Hasselblad
- Soft, natural lighting — no high contrast
- Person must be using the product correctly (check correct_usage_poses)
- Product branding (SPORTSTECH logo) must be visible and correct

## Output
- Image in Supabase Storage: `creatives/<batch_id>/<creative_id>.png`
- Creative record in `creatives` table with:
  - product_id, character_id, environment_id
  - All camera settings (shot_size, camera_angle, lens, depth_of_field)
  - environment_style, creative_type="lifestyle"
  - generation_mode="raw" (no text overlays)

## Verbindungen
- Uses output from `character-builder` (character references)
- Uses output from `room-builder` (environment references)
- Uses product references from Supabase Storage
- Output can be input for `multishot` (camera variations) and `color-variant`
- Results appear in real-time on the Board UI
