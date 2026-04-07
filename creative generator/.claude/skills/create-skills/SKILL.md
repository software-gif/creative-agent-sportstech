# Create Skills

> Scaffoldet neue Skills mit vollständiger Ordnerstruktur und validiertem SKILL.md Template.

## Problem
Neue Skills manuell anzulegen ist fehleranfällig und führt zu inkonsistenten Strukturen. Ohne einheitliches Template fehlen wichtige Sektionen oder die Dokumentation ist unvollständig.

## Trigger
Wenn ein neuer Skill erstellt werden soll — entweder manuell per CLI oder durch Claude Agent.

## Inputs
| Parameter     | Typ    | Pflicht | Default        | Beschreibung                     |
|---------------|--------|---------|----------------|----------------------------------|
| --name        | string | ja      | -              | Skill-Name in kebab-case         |
| --description | string | ja      | -              | Ein-Satz-Beschreibung des Skills |
| --base-path   | string | nein    | .claude/skills | Basis-Verzeichnis für Skills     |

## Outputs
- `skills/<name>/SKILL.md` — Skill-Dokumentation nach validiertem Template mit Planungs-Prompts
- `skills/<name>/scripts/main.py` — Einstiegspunkt-Script mit Grundstruktur

## Scripts
- `scripts/create_skill.py` — Erstellt Ordnerstruktur, generiert SKILL.md mit Template + eingebetteten Planungsfragen, legt Starter-Script an. **Single Source of Truth** für das Template.

## Ausführung

```bash
python3 .claude/skills/create-skills/scripts/create_skill.py --name "my-skill" --description "Kurze Beschreibung"
```

## Dependencies
- Python 3 (keine externen Pakete)

## Beispiele

**Minimal:**
```bash
python3 .claude/skills/create-skills/scripts/create_skill.py --name "scrape-leads" --description "Scraped Leads von einer Ziel-Website"
```

**Ergebnis:**
```
skills/scrape-leads/
├── SKILL.md          # Vorausgefüllt mit Template + Planungsfragen als Kommentare
└── scripts/
    └── main.py       # Grundgerüst mit main() Funktion
```

## Fehlerbehandlung
- **Skill existiert bereits:** Überschreibt keine bestehenden Dateien, gibt Warnung aus.
- **Ungültiger Name:** Muss kebab-case sein (Kleinbuchstaben, Bindestriche). Gibt Fehlermeldung.
- **Fehlende Pflichtparameter:** argparse gibt automatisch Fehlermeldung aus.

## Verbindungen
- Jeder neue Skill im Projekt wird durch diesen Skill erstellt.
- Das generierte Template enthält eingebettete Planungsfragen (aus dem ehemaligen Fragebogen), damit nichts vergessen wird.
