# Review Scraper

> Scraped Trustpilot Reviews direkt via Web Scraping und extrahiert Kundenstimmen für Ad Angle Generierung.

## Problem
Für authentische Ad Angles brauchen wir echte Kundenstimmen. Manuelles Durchlesen von Trustpilot ist zeitaufwändig. Negative Konkurrenz-Reviews liefern Pain Points, die der Markt tatsächlich hat.

## Trigger
Beim Setup einer neuen Brand und regelmäßig für neue Reviews.

## Inputs
| Parameter      | Typ    | Pflicht | Default           | Beschreibung                        |
|----------------|--------|---------|-------------------|-------------------------------------|
| --trustpilot-url | string | nein  | aus brand.json    | Trustpilot Review URL               |
| --max-pages    | int    | nein    | 0 (alle)          | Maximale Seiten zum Scrapen         |
| --output-dir   | string | nein    | reviews/          | Verzeichnis für Output              |

## Outputs
- `reviews/reviews_raw.json` — Alle Reviews mit Rating, Text, Datum, Autor
- `reviews/summary.json` — Zusammenfassung: Rating-Verteilung, häufige Themen

## Scripts
- `scripts/main.py` — Scraped Trustpilot via __NEXT_DATA__ JSON Extraction mit Paginierung.

## Ausführung

```bash
python3 .claude/skills/review-scraper/scripts/main.py
python3 .claude/skills/review-scraper/scripts/main.py --max-pages 5
```

## Dependencies
- Python 3
- `requests` (pip)
- `python-dotenv` (pip)

## Fehlerbehandlung
- **Trustpilot blockt:** Retry mit Delay
- **Keine Reviews:** Warnung ausgeben
- **Rate Limiting:** 2s Pause zwischen Seiten

## Verbindungen
- Liest `brand.json` für Trustpilot URL
- Output wird von `angle-generator` Skill verwendet
