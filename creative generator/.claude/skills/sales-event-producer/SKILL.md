# Sales Event Producer

> Generiert Static Ads für Sales Events (Black Friday, Weihnachten, Ostern etc.) via Gemini Image Generation. Zwei Styles: Clean Aesthetic oder Event-themed Hintergrund.

## Problem
Für jedes Sales Event müssen schnell viele Creatives in konsistentem Style produziert werden. Manuell ist das pro Event 2-3 Tage Arbeit. Dieser Skill automatisiert die Generierung auf Basis von Produkt, Event und Offer.

## Trigger
Wenn ein Sales Event ansteht und Creatives benötigt werden. User gibt Produkt, Event und Offer-Details an.

## Workflow
1. User wählt: Produkt (Smart Wallet / Tracker Karte / Sling Bag), Sales Event, Hintergrund-Stil
2. User gibt Headline ein (oder lässt KI generieren mit Angle-Input)
3. User wählt Sub-Headline (Offer) und CTA aus Liste oder gibt neue ein
4. Claude baut pro Creative einen JSON-Prompt mit:
   - Event-spezifischen Farben und Hintergrund
   - Produkt-Freisteller als Referenz
   - 3 Benefits mit Icons
   - Headline, Sub-Headline, CTA
   - Safe Zone Layout (9:16 mit 1:1 Content-Area)
5. Script generiert via Gemini + Compositor (Logo, Social Proof, Payment Icons)
6. Upload nach Supabase, erscheint im Board

## Inputs

### Vom User (pro Batch)
| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| product | string | ja | Produkt-Handle: `smart-wallet-3-0`, `tracker-karte`, `essential-sling-bag` |
| event | string | ja | Event-ID aus `config/sales_events.json` |
| background_style | string | ja | `clean` oder `themed` |
| headline | string | nein | Feste Headline. Wenn leer: KI generiert Varianten |
| headline_angle | string | nein | Angle für KI-Headline-Generierung (z.B. "Kompaktheit", "Sicherheit") |
| sub_headline | string | nein | Offer-Text (z.B. "Bis zu 50% Rabatt"). Default aus Event-Config |
| cta | string | nein | CTA-Text. Default: "Jetzt sparen" |
| benefits_selection | list | nein | 3 Benefits aus Produkt-Benefits-Liste. Default: erste 3 |
| num_variants | int | nein | Anzahl Varianten (Default: 3) |
| color | string | nein | Produktfarbe (Default: Designer-Schwarz) |

### Automatisch gelesen
- `branding/brand.json` — Produkt-Benefits, Farben, Trust Signals
- `branding/brand_guidelines.json` — Fonts, Farben, Layout-Regeln, Safe Zone
- `config/sales_events.json` — Event-Farben, Hintergrund-Hints, Default Offers
- `products/images/<handle>/` — Produktbilder

## Outputs
- Generierte Creatives → Supabase Storage + Board
- Lokales Backup in `creatives/<batch_id>/`
- `manifest.json` pro Batch

## Format
- **9:16** (1080×1920) — Story/Reel Format
- **Safe Zone:** Content im mittleren 1:1 Bereich (1080×1080)
  - Logo oben (außerhalb 1:1)
  - Social Proof / Payment Icons unten (außerhalb 1:1)

## Creative-Aufbau (von oben nach unten)
```
┌─────────────────────────┐
│         LOGO            │  ← Außerhalb Safe Zone
├─────────────────────────┤
│                         │
│       HEADLINE          │  ← Safe Zone Start
│                         │
│    ┌─────────────┐      │
│    │   PRODUKT   │      │
│    │   (Hero)    │      │
│    └─────────────┘      │
│                         │
│  ✓ Benefit 1            │
│  ✓ Benefit 2            │
│  ✓ Benefit 3            │
│                         │
│   [ CTA BUTTON ]        │
│    Sub-Headline         │  ← Safe Zone Ende
│                         │
├─────────────────────────┤
│  ⭐ Social Proof        │  ← Außerhalb Safe Zone
│  💳 Payment Icons       │
│  ● ● ● Farbvarianten   │
└─────────────────────────┘
```

## Headline-Generierung (wenn nicht manuell)
Claude generiert 3-5 Headline-Varianten basierend auf:
- Dem gewählten Produkt und seinen Benefits
- Dem Angle-Input des Users
- Dem Sales Event Kontext
- Brand Voice (premium, direkt, deutsch)

Beispiele:
- "Das schlankste Smart Wallet" (Benefit)
- "Nie wieder Kartenchaos" (Problem/Pain)
- "Warum 50.000+ Kunden gewechselt haben" (Proof)

## Scripts
- `scripts/main.py` — Generiert Prompt-JSON, ruft creative-producer auf
- Nutzt `creative-producer/scripts/main.py` als Engine

## Ausführung
Wird durch Claude gesteuert:
1. Claude liest Inputs + Config
2. Claude baut JSON-Prompts (1 pro Variante)
3. Claude ruft `creative-producer/scripts/main.py` mit den Prompts auf

## Dependencies
- Alle Dependencies von `creative-producer`
- `config/sales_events.json`
- `branding/brand.json` + `brand_guidelines.json`
- Produktbilder in `products/images/`

## Verbindungen
- Nutzt `creative-producer` als Generation-Engine
- Liest `brand.json` für Produkt-Benefits
- Liest `config/sales_events.json` für Event-Kontext
- Referenziert `meta-andromeda` für Diversification-Logik
