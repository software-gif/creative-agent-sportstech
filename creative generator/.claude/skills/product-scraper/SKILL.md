# Product Scraper

> Scraped Produktdaten und Bilder aus dem Shopify Store der Brand via Shopify JSON API.

## Problem
Für die Creative-Generierung brauchen wir aktuelle Produktdaten (Namen, Preise, Beschreibungen) und hochauflösende Produktbilder. Manuelles Herunterladen ist zeitaufwändig und fehleranfällig.

## Trigger
Einmalig beim Setup einer neuen Brand, danach bei Sortimentsänderungen.

## Inputs
| Parameter    | Typ    | Pflicht | Default        | Beschreibung                      |
|--------------|--------|---------|----------------|-----------------------------------|
| --shop-url   | string | nein    | aus brand.json | Shopify Store URL                 |
| --output-dir | string | nein    | products/      | Verzeichnis für Output            |
| --skip-images| flag   | nein    | false          | Nur Daten, keine Bilder laden     |

## Outputs
- `products/products.json` — Alle Produktdaten (Name, Preis, Typ, Beschreibung, Bild-Pfade)
- `products/images/<handle>/` — Produktbilder pro Produkt in Originalqualität

## Scripts
- `scripts/main.py` — Ruft Shopify JSON API ab, speichert Daten, downloadet Bilder.

## Ausführung

```bash
python3 .claude/skills/product-scraper/scripts/main.py
python3 .claude/skills/product-scraper/scripts/main.py --skip-images
```

## Dependencies
- Python 3
- `requests` (pip)
- `python-dotenv` (pip)

## Beispiele

**Alles scrapen:**
```bash
python3 .claude/skills/product-scraper/scripts/main.py
```

**Nur Daten ohne Bilder:**
```bash
python3 .claude/skills/product-scraper/scripts/main.py --skip-images
```

## Fehlerbehandlung
- **Shop nicht erreichbar:** Timeout mit Fehlermeldung
- **Keine Shopify JSON API:** Fehlermeldung wenn `/products.json` nicht existiert
- **Bild-Download fehlgeschlagen:** Überspringt einzelne Bilder, loggt Fehler

## Verbindungen
- Liest `brand.json` für Shop URL
- Output wird von `creative-producer` Skill verwendet (Produktbilder als Input)
