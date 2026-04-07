# Product Upload

> Interaktiver Workflow zum Hinzufügen neuer Produkte. Fragt nach Produktname, lädt Freisteller-Bilder hoch, scraped die Produktseite für Kontext, und speichert alles in Supabase.

## Trigger
Wenn der User ein neues Produkt zum Creative Agent hinzufügen will.

## Workflow

### Schritt 1: Produkt-Info abfragen
Claude fragt interaktiv:
1. **Produktname** — z.B. "F37s Pro", "sBike", "WoodPad Pro"
2. **Produkt-Handle** — URL-freundlicher Slug (z.B. "f37s-pro")
3. **Kategorie** — treadmill, speedbike, ergometer, crosstrainer, rowing_machine, power_station, smith_machine, vibration_plate, walking_pad
4. **Produktseiten-URL** — z.B. "https://www.sportstech.de/laufband/f37s-pro"
5. **Verfügbare Farben** — z.B. ["black", "silver"]

### Schritt 2: Freisteller-Bilder hochladen
User gibt Pfade zu den Freisteller-Bildern (einzelne Dateien oder ZIP).
Claude lädt alle Bilder nach Supabase Storage hoch: `products/<handle>/0.png`, `1.png`, etc.

### Schritt 3: Produktseite scrapen
Claude ruft die Produktseiten-URL ab und extrahiert:
- Preis
- Technische Spezifikationen
- Features und Benefits
- Wie das Produkt benutzt wird
- Was das Produkt aussieht (für AI-Generierung)

### Schritt 4: Product Knowledge erstellen
Claude erstellt einen Eintrag in `product_knowledge.json` mit:
- `appearance` — Wie sieht das Produkt aus?
- `how_it_works` — Wie wird es benutzt?
- `correct_usage_poses` — Korrekte Posen für Lifestyle-Shots
- `ai_generation_rules` — `must_match` und `must_avoid` für Gemini
- `reference_images` — Pfade zu den Referenzbildern

### Schritt 5: In Supabase speichern
- Produkt-Record in `products` Tabelle
- Bild-Records in `product_images` Tabelle

## Ausführung

```
User: "Ich möchte ein neues Produkt hinzufügen"
Claude: "Wie heißt das Produkt?"
User: "VP500 Vibrationsplatte"
Claude: "Handle? (z.B. vp500)"
User: "vp500"
Claude: "Kategorie?"
User: "vibration_plate"
Claude: "Produktseiten-URL?"
User: "https://www.sportstech.de/vibrationsplatte/vp500"
Claude: "Wo liegen die Freisteller-Bilder? (Pfad zu Dateien oder ZIP)"
User: "/Users/johannes/Downloads/VP500_Freisteller.zip"
```

Claude erledigt dann automatisch:
1. ZIP entpacken
2. Bilder nach Supabase hochladen
3. Produktseite scrapen
4. Product Knowledge JSON erstellen
5. Datenbank-Einträge erstellen
6. Bestätigung mit Übersicht

## Für ZIPs
ZIP-Dateien werden automatisch entpackt. Unterstützte Bildformate: .png, .jpg, .jpeg

## Script
```bash
python3 .claude/skills/product-upload/scripts/main.py \
  --handle "vp500" \
  --name "VP500 Vibrationsplatte" \
  --category "vibration_plate" \
  --url "https://www.sportstech.de/vibrationsplatte/vp500" \
  --colors '["black"]' \
  --images "/path/to/image1.png" "/path/to/image2.png"
```

## Verbindungen
- Output wird von `key-visual` als Produktreferenz genutzt
- Bilder werden in `product_knowledge.json` referenziert
- Product-Record wird mit `creatives` Tabelle verknüpft
