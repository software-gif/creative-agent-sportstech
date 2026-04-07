# Angle Generator

> Generiert Ad Angles und Sub-Angles basierend auf Reviews und Winner-Analyse. Claude analysiert die Daten direkt — kein externes LLM nötig.

## Problem
Manuell Ad Angles aus hunderten Reviews abzuleiten ist zeitaufwändig und subjektiv. Der Angle Generator bereitet die Daten auf und Claude leitet daraus spezifische, authentische Angles ab — basierend auf der Meta Andromeda Diversification-Logik.

## Trigger
Nachdem Review Scraper und Ad Library Scraper gelaufen sind.

## Workflow
1. `scripts/main.py` liest Reviews, Winner-Ads und Brand-Daten
2. Script erstellt eine strukturierte Zusammenfassung (`angles/review_summary.json`)
3. Claude analysiert die Daten und generiert `angles/angles.json` direkt

## Inputs
| Parameter    | Typ    | Pflicht | Default  | Beschreibung                     |
|--------------|--------|---------|----------|----------------------------------|
| --output-dir | string | nein    | angles/  | Verzeichnis für Output           |

Liest automatisch:
- `reviews/reviews_raw.json` — Kundenstimmen
- `winners/ads_analyzed.json` — Winner Ad Patterns
- `brand.json` — Brand-Kontext

## Outputs
- `angles/review_summary.json` — Aufbereitete Daten für Analyse
- `angles/angles.json` — Alle generierten Angles mit Sub-Angles und Review-Belegen

## Scripts
- `scripts/main.py` — Liest alle Datenquellen, bereitet strukturierte Zusammenfassung auf.

## Ausführung

```bash
# 1. Daten aufbereiten
python3 .claude/skills/angle-generator/scripts/main.py

# 2. Claude generiert angles.json basierend auf der Zusammenfassung
```

## Output-Format (angles.json)

```json
{
  "brand": "Brandname",
  "angles": [
    {
      "angle": "Problem/Pain",
      "emoji": "🔥",
      "type": "core",
      "sub_angles": [
        {
          "name": "Kurzer Name",
          "description": "Was genau der Pain Point ist",
          "review_evidence": "Direktes Zitat aus echtem Review",
          "hook_suggestion": "Konkreter Hook-Text für eine Static Ad",
          "review_rating": 1
        }
      ]
    }
  ]
}
```

## Angle-Kategorien (7 total)
- **Core (3):** Problem/Pain 🔥, Benefit ✨, Proof ✅
- **Scaling (4):** Curiosity 🔮, Education 📚, Story 💜, Offer 🏷️
- Pro Angle: 5-8 spezifische Sub-Angles, belegt durch echte Reviews

## Dependencies
- Python 3
- Keine externen Packages nötig (nur stdlib: json, os, sys, argparse)

## Verbindungen
- Liest Output von `review-scraper` und `ad-library-scraper`
- Referenziert `meta-andromeda` Knowledge für Angle-Hierarchie
- Output wird von `creative-producer` Skill verwendet
