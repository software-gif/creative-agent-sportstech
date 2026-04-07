# Ad Library Scraper

> Scraped Facebook Ad Library via Apify und analysiert Winner Ads basierend auf Impressionen und Laufzeit.

## Problem
Die Facebook Ad Library lässt sich nicht manuell effizient analysieren. Wir brauchen automatisiert alle Ads einer Brand, sortiert nach Performance, um Winner-Patterns zu identifizieren.

## Trigger
Wenn eine neue Brand analysiert werden soll oder regelmäßig (wöchentlich) um neue Ads zu erfassen.

## Inputs
| Parameter    | Typ    | Pflicht | Default        | Beschreibung                     |
|--------------|--------|---------|----------------|----------------------------------|
| --page-id    | string | nein    | aus brand.json | Facebook Page ID der Brand       |
| --max-ads    | int    | nein    | 0 (alle)       | Maximale Anzahl Ads zum Scrapen  |
| --output-dir | string | nein    | winners/       | Verzeichnis für Output           |

## Outputs
- `winners/ads_raw.json` — Alle gescrapten Ads (Rohdaten von Apify)
- `winners/ads_analyzed.json` — Ads mit berechnetem Winner Score, sortiert nach Score
- `winners/summary.json` — Top Winners, Format-Verteilung, Angle-Patterns

## Scripts
- `scripts/main.py` — Orchestriert den gesamten Workflow: Apify Call → Daten speichern → Analyse → Winner Score
- Nutzt Apify Actor: `curious_coder/facebook-ads-library-scraper`

## Ausführung

```bash
python3 .claude/skills/ad-library-scraper/scripts/main.py
python3 .claude/skills/ad-library-scraper/scripts/main.py --max-ads 50
```

## Dependencies
- Python 3
- `requests` (pip)
- `python-dotenv` (pip)
- Apify API Key in `.env`

## Beispiele

**Alle Ads scrapen:**
```bash
python3 .claude/skills/ad-library-scraper/scripts/main.py
```

**Nur Top 20 Ads:**
```bash
python3 .claude/skills/ad-library-scraper/scripts/main.py --max-ads 20
```

## Fehlerbehandlung
- **Kein API Key:** Fehlermeldung mit Verweis auf `.env`
- **Apify Timeout:** Default Timeout 120s, Retry-Option
- **Ungültige Page ID:** Prüft ob Ergebnisse zurückkommen
- **Rate Limiting:** Apify handhabt das intern

## Verbindungen
- Liest `brand.json` für Page ID
- Output wird von `angle-generator` Skill verwendet
- Referenziert `meta-andromeda` Knowledge für Winner-Score-Logik
