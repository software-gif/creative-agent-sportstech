# Presets

> Erstellt, verwaltet und führt wiederverwendbare Lifestyle-Bild-Presets aus. Ein Preset ist ein benanntes Rezept aus Product × Room × Character × Camera, das per `run <slug>` die Key-Visual-Generation auslöst.

## Problem

Ohne Presets muss jede Generation manuell parametrisiert werden — Produkt, Raum, Character, Kamera, Pose, Format. Das ist repetitiv für wiederkehrende Szenarien (z.B. "F37s Pro im Scandi-Wohnzimmer, Morgenstimmung, auto-rotating Models"). Außerdem gehen bewährte Kombinationen nach einer Session verloren, wenn sie nicht festgehalten werden.

Presets lösen das: **Bausteine** (aus dem Randomizer-Konzept vom Weekly Call) werden zu einem Rezept zusammengefasst, in Supabase gespeichert und per Command wieder aufgerufen.

## Trigger

- User sagt: *"Leg mir ein Preset für F37s im Scandi-Raum an"* → `create`
- User sagt: *"Zeig mir alle Walking-Pad Presets"* → `list --product woodpad-pro`
- User sagt: *"Generiere 10 Bilder mit dem AquaElite-Japandi Preset"* → `run aquaelite-japandi-wellness --count 10`
- Andere Skills können `run` programmatisch aufrufen

## Inputs

Subcommands: `list`, `show`, `create`, `update`, `delete`, `run`

### `list [--product HANDLE] [--tag TAG]`
| Parameter   | Typ    | Pflicht | Default | Beschreibung                   |
|-------------|--------|---------|---------|--------------------------------|
| --product   | string | nein    | -       | Filter nach product_handle     |
| --tag       | string | nein    | -       | Filter nach Tag                |

### `show <slug>`
| Parameter | Typ    | Pflicht | Default | Beschreibung |
|-----------|--------|---------|---------|--------------|
| slug      | string | ja      | -       | Preset slug  |

### `create`
| Parameter               | Typ    | Pflicht | Default       | Beschreibung                                                |
|-------------------------|--------|---------|---------------|-------------------------------------------------------------|
| --slug                  | string | ja      | -             | kebab-case ID (einzigartig pro Brand)                       |
| --name                  | string | ja      | -             | Display-Name                                                |
| --description           | string | nein    | -             | Kurzbeschreibung                                            |
| --product               | string | ja      | -             | Produkt-Handle (muss in product_knowledge.json existieren)  |
| --room-preset           | string | nein    | -             | Raum-ID aus room_prompts.json                               |
| --room-description      | string | nein    | -             | Freitext-Override für Raum                                  |
| --character-mode        | string | nein    | `auto_rotate` | `auto_rotate` \| `fixed` \| `description` \| `model_pool`   |
| --character-id          | uuid   | nein    | -             | Character-UUID (nur bei `fixed`)                            |
| --character-description | string | nein    | -             | Freitext-Beschreibung (nur bei `description`)               |
| --model-pool-id         | string | nein    | -             | ID aus lifestyle_variance.json (nur bei `model_pool`)       |
| --pose                  | string | nein    | -             | Pose-Beschreibung; default: erster Usage-Pose aus product_knowledge |
| --shot-size             | string | nein    | `Wide`        | Wide / Medium / Close Up / etc.                             |
| --camera-angle          | string | nein    | `Eye level`   | High / Low / Eye level / Slightly above / Ground level      |
| --character-angle       | string | nein    | `3/4 angle`   | Front / Profile / 3/4 / Back                                |
| --lens                  | string | nein    | `50mm`        | 14mm — 200mm                                                |
| --depth-of-field        | string | nein    | `f/4`         | f/1.2 — f/16                                                |
| --format                | string | nein    | `9:16`        | 9:16 / 1:1 / 16:9 / 4:5                                     |
| --default-count         | int    | nein    | `3`           | Anzahl Bilder pro Run                                       |
| --tags                  | string | nein    | -             | Komma-separiert (z.B. `scandinavian,morning,female`)        |

### `update <slug> [same flags as create]`
Beliebige Felder ändern. Nur übergebene Flags werden gesetzt.

### `delete <slug>`
Löscht das Preset. Kein Soft-Delete.

### `run <slug> [--count N] [--dry-run]`
Führt das Preset aus: lädt es aus Supabase, ruft `key-visual/scripts/main.py` mit den gespeicherten Parametern auf, inkrementiert `run_count` und setzt `last_run_at`.

| Parameter | Typ  | Pflicht | Default         | Beschreibung                                           |
|-----------|------|---------|-----------------|--------------------------------------------------------|
| slug      | str  | ja      | -               | Preset slug                                            |
| --count   | int  | nein    | `default_count` | Anzahl Bilder überschreibt das Preset-Default          |
| --dry-run | flag | nein    | false           | Zeigt den zusammengebauten key-visual Aufruf, führt ihn aber nicht aus |

## Outputs

- **create/update:** JSON-Ausgabe des gespeicherten Presets (inkl. `id`, `created_at`).
- **list:** Tabelle mit Slug, Name, Product, Room, Tags, `run_count`.
- **show:** Vollständiges Preset als JSON.
- **delete:** Bestätigung oder Fehler.
- **run:** Delegiert an `key-visual` — Bilder landen wie gewohnt in Supabase Storage + `creatives` Tabelle. Das Preset selbst bekommt `run_count++` und neues `last_run_at`.

Storage: Alle Preset-Daten leben in der Supabase-Tabelle `creative_presets` (siehe `migrations/002_creative_presets.sql`).

## Scripts

- `scripts/main.py` — Einziger Einstiegspunkt. Subcommand-Router der alle Operationen gegen die Supabase REST API ausführt und für `run` per `subprocess` auf `key-visual/scripts/main.py` delegiert.
- `scripts/seed_presets.py` — Seedet 8 kuratierte Start-Presets (idempotent — bestehende Slugs werden übersprungen).

## Ausführung

Erstes Setup (einmalig):

1. Migration in Supabase SQL Editor ausführen:
   ```
   migrations/002_creative_presets.sql
   ```
2. Seeds einspielen:
   ```bash
   python3 .claude/skills/presets/scripts/seed_presets.py
   ```

Danach regulär:

```bash
# Alle Presets anzeigen
python3 .claude/skills/presets/scripts/main.py list

# Nur Treadmill-Presets
python3 .claude/skills/presets/scripts/main.py list --product f37s-pro

# Detail
python3 .claude/skills/presets/scripts/main.py show f37s-scandi-morning

# Neues Preset
python3 .claude/skills/presets/scripts/main.py create \
  --slug woodpad-study-morning \
  --name "WoodPad Pro — Walnut Study Morning" \
  --product woodpad-pro \
  --room-preset walnut_accent_study \
  --tags walking_pad,study,morning

# Ausführen (nutzt default_count)
python3 .claude/skills/presets/scripts/main.py run f37s-scandi-morning

# Ausführen mit Override
python3 .claude/skills/presets/scripts/main.py run f37s-scandi-morning --count 10

# Dry-run: zeigt nur das kommando das abgeschickt würde
python3 .claude/skills/presets/scripts/main.py run f37s-scandi-morning --dry-run
```

## Dependencies

- Python 3 + `requests` + `python-dotenv` (bereits in anderen Skills verwendet)
- Supabase Zugriff via `.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (oder `SUPABASE_ANON_KEY`)
- `key-visual` Skill muss existieren und lauffähig sein (für `run` Subcommand)

## Beispiele

**Minimal-Preset anlegen:**
```bash
python3 .claude/skills/presets/scripts/main.py create \
  --slug aquaelite-japandi-serene \
  --name "AquaElite Japandi Serene" \
  --product aqua-elite \
  --room-preset japandi_bookcase
```

**Preset mit model-pool + vollständiger Camera:**
```bash
python3 .claude/skills/presets/scripts/main.py create \
  --slug sgym-industrial-lift \
  --name "sGym Pro Industrial Lift" \
  --product sgym-pro \
  --room-preset industrial_home_gym \
  --character-mode model_pool \
  --model-pool-id m4 \
  --pose "Seated shoulder press on the sGym Pro station, back straight, focused expression" \
  --shot-size Wide \
  --camera-angle "Slightly below" \
  --character-angle "3/4 angle" \
  --lens 35mm \
  --depth-of-field f/2.8 \
  --format 9:16 \
  --tags industrial,strength,power_station,moody \
  --default-count 5
```

## Fehlerbehandlung

- **Preset-Slug existiert bereits (create):** Fehler, kein Overwrite. User muss `update` benutzen.
- **Unknown room-preset:** Warnung, aber akzeptiert (das key-visual Script prüft das zur Laufzeit).
- **Unknown product_handle:** Vorab-Check gegen `product_knowledge.json` — hart ablehnen.
- **Invalid character_mode:** CHECK-Constraint der Tabelle wirft Fehler.
- **Supabase unerreichbar:** Script bricht mit klarer Meldung ab, kein partieller State.
- **run: key-visual Script fehlt:** Script bricht ab, `run_count` wird NICHT erhöht.
- **run: key-visual liefert non-zero Exit:** Fehler wird durchgereicht, `run_count` wird NICHT erhöht.

## Verbindungen

- **Abhängig von:** `key-visual` (für `run`), `brands` + `creative_presets` Supabase-Tabellen, `branding/product_knowledge.json`, `branding/room_prompts.json`, `branding/lifestyle_variance.json`
- **Nutzt:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` aus `.env`
- **Schreibt:** `creative_presets` Tabelle; indirekt über `run` auch `creatives` (via key-visual)
- **Liest:** `product_knowledge.json` (Validierung, Default-Pose), `room_prompts.json` (Validierung), `lifestyle_variance.json` (Validierung model_pool_id)
