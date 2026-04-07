#!/usr/bin/env python3
"""Scaffolds a new skill in .claude/skills/ with validated SKILL.md template.

This script is the SINGLE SOURCE OF TRUTH for the skill template.
The template includes embedded planning prompts (from the validated Fragebogen)
as HTML comments to guide the author through all important decisions.
"""

import argparse
import os
import re
import sys


def validate_name(name: str) -> bool:
    """Validates that name is kebab-case."""
    return bool(re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name))


def generate_skill_md(name: str, description: str, skill_dir: str) -> str:
    """Generates a SKILL.md following the validated template."""
    title = name.replace("-", " ").title()
    return f"""# {title}

> {description}

## Problem
<!--
  - Welches Problem löst dieser Skill?
  - Warum existiert er? Was ist der Pain Point ohne ihn?
-->
TODO: Beschreibe das Problem.

## Trigger
<!--
  - Wann soll der Skill ausgelöst werden?
  - Wer nutzt ihn? (Claude Agent, Mensch, beides?)
-->
TODO: Definiere Trigger-Bedingungen.

## Inputs
<!--
  - Welche Pflicht-Inputs braucht der Skill?
  - Welche optionalen Inputs gibt es? Was sind die Defaults?
  - Gibt es Validierungsregeln? (Min/Max, Regex, erlaubte Werte)
  - Woher kommen die Inputs? (User-Eingabe, andere Skills, API, Dateien)
-->
| Parameter | Typ | Pflicht | Default | Beschreibung |
|-----------|-----|---------|---------|--------------|
| TODO      |     |         |         |              |

## Outputs
<!--
  - Was produziert der Skill? (Dateien, Text, JSON, Ordnerstruktur)
  - Wo wird der Output gespeichert?
  - In welchem Format?
  - Gibt es Erfolgs- und Fehlermeldungen?
-->
TODO: Definiere Outputs.

## Scripts
<!--
  - Welche Scripts werden benötigt? Was macht jedes einzeln?
  - In welcher Reihenfolge werden sie ausgeführt?
  - Welche externen Dependencies brauchen sie? (pip packages, APIs)
  - Gibt es Environment-Variablen oder Secrets?
-->
- `scripts/main.py` — Hauptlogik, Einstiegspunkt.

## Ausführung
<!--
  - Gibt es Voraussetzungen vor der Ausführung? (Setup-Steps)
  - Kann der Skill parallel mit anderen laufen?
  - Gibt es einen Dry-Run / Preview-Modus?
-->
```bash
python3 {skill_dir}/scripts/main.py
```

## Dependencies
- Python 3

## Beispiele
<!--
  - Minimal-Beispiel: Einfachster Aufruf
  - Vollständiges Beispiel: Alle Parameter genutzt
  - Was passiert bei leerem Input?
-->
**Minimal:**
```bash
python3 {skill_dir}/scripts/main.py
```

## Fehlerbehandlung
<!--
  - Was sind die häufigsten Fehlerquellen?
  - Wie soll bei fehlenden Inputs reagiert werden?
  - Gibt es Retry-Logik?
-->
TODO: Definiere Fehlerbehandlung.

## Verbindungen
<!--
  - Hängt der Skill von anderen Skills ab?
  - Welche Skills bauen auf diesem auf?
  - Greift der Skill auf externe APIs oder Services zu?
  - Welche Dateien/Ordner liest oder schreibt der Skill?
-->
Keine.
"""


def generate_main_py(name: str) -> str:
    """Generates a starter main.py script."""
    title = name.replace("-", " ").title()
    return f'''#!/usr/bin/env python3
"""{title} skill."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="{title}")
    # TODO: Add arguments
    args = parser.parse_args()

    # TODO: Implement skill logic
    print(f"{title}: not yet implemented")


if __name__ == "__main__":
    main()
'''


def create_skill(name: str, description: str, base_path: str = ".claude/skills"):
    if not validate_name(name):
        print(f"Error: '{name}' is not valid kebab-case (e.g. 'my-skill-name').")
        sys.exit(1)

    skill_dir = os.path.join(base_path, name)
    scripts_dir = os.path.join(skill_dir, "scripts")

    if os.path.exists(skill_dir):
        print(f"Warning: '{skill_dir}' already exists. Skipping to avoid overwrite.")
        sys.exit(0)

    os.makedirs(scripts_dir, exist_ok=True)

    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_md_path, "w") as f:
        f.write(generate_skill_md(name, description, skill_dir))

    main_py_path = os.path.join(scripts_dir, "main.py")
    with open(main_py_path, "w") as f:
        f.write(generate_main_py(name))

    print(f"Created skill: {skill_dir}")
    print(f"  - {skill_md_path}")
    print(f"  - {main_py_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new skill")
    parser.add_argument("--name", required=True, help="Skill name (kebab-case)")
    parser.add_argument("--description", required=True, help="Short skill description")
    parser.add_argument("--base-path", default=".claude/skills", help="Base skills directory")
    args = parser.parse_args()

    create_skill(args.name, args.description, args.base_path)
