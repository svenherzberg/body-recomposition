```markdown
# body-recomposition — Logs, Parser & Summaries

Kurz: Dieses Repo sammelt tägliche Protokolle (Markdown), rechnet Nährwerte aus und erzeugt zusammengefasste Artefakte (Markdown, Excel, Grafiken) via GitHub Actions.

Wichtige Ordner
- `protocol/` — deine täglichen Protokolle (empfohlen: `YYYY-MM-DD.md` oder in Unterordnern)
- `data/foods.yaml` — Lebensmittel‑Datenbank (per 100 g) mit `aliases`
- `scripts/` — Parser und Aggregatoren (`parse_logs.py`, `aggregate_protocol.py`, `plot_metrics.py`)
- `outputs/` — generierte Artefakte (wird von Actions hochgeladen)

Frontmatter / Header‑Konvention (empfohlen)
- Verwende YAML‑Frontmatter oben in der Datei oder einen Kopfblock mit `key: value`-Zeilen.
- Felder (empfohlen): `date` (ISO `YYYY-MM-DD`), `weight_kg`, `bodyfat_pct`, `target_calories`, `target_protein_g`, `target_fat_g`, `target_carbs_g`, `actual_*`, `sleep` (z. B. `7:24`), `comment`.
- Einheitsempfehlung: Zahlen mit Dezimalpunkt (z. B. `70.9`). Der Parser toleriert Komma und verschiedene Einheiten und normalisiert sie.

Wie lokal ausführen
1. Python‑Umgebung einrichten (empfohlen):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r scripts/requirements.txt
```

2. Parser (generiert `outputs/data/summary.json`):

```bash
python scripts/parse_logs.py
```

3. Aggregiere Protocol‑Header (generiert `outputs/protocol_summary.md` und `outputs/protocol_summary.xlsx`):

```bash
python scripts/aggregate_protocol.py
```

GitHub Actions
- Workflow: `.github/workflows/generate-summaries.yml`
- Trigger: Push auf `logs/**`, `data/**`, `protocol/**` und geplanter Tageslauf.
- Artefakte: `outputs/` werden als `body-summaries` hochgeladen (Retention: 90 Tage).

Artefakte herunterladen
- Web UI: Repository → Actions → Workflow Run → Artifacts → Download
- GH CLI: z. B. `gh run list --workflow generate-summaries.yml` und `gh run download <run-id> --name body-summaries`

Weiteres
- Wenn du möchtest, kann der Workflow geändert werden, um Grafiken zu committen, in GitHub Pages zu veröffentlichen oder ein Release zu erstellen. Das kann Commit‑Loops erzeugen — ich empfehle zuerst Artefakte.

Wenn du konkrete Feld‑Namen bevorzugst (z. B. `weight_kg` genau so), sag Bescheid — ich kann Validierung/Schema‑Checks hinzufügen.
Exporting daily meals
---------------------

To extract daily meal sections from the markdown protocol and logs and produce a
single combined markdown file (and a PDF in CI), run:

```bash
python3 scripts/export_meals_pdf.py --root protocol --include-logs
```

A GitHub Action workflow `.github/workflows/export_meals_pdf.yml` is included and
will create `outputs/meals_combined.md` and (if pandoc + wkhtmltopdf are installed)
`outputs/meals_combined.pdf` and upload them as workflow artifacts.

Ein-Kommando (alles erzeugen)
------------------------------

Wenn du alle Artefakte auf einmal lokal oder in einem Codespace erzeugen willst,
verwende das mitgelieferte Wrapper-Skript `scripts/update_all.sh`. Es führt die
Einzelschritte in der richtigen Reihenfolge aus und generiert:

- `outputs/protocol_summary.md` und `outputs/protocol_summary.xlsx`
- `outputs/data/summary.json` und `outputs/data/missing_foods.json`
- `outputs/meals_combined.md` und (falls `pandoc` + `wkhtmltopdf` installiert sind)
	`outputs/meals_combined.pdf`
- `outputs/weekly_meal_protocol/CW_*.md` und (falls Tools vorhanden) `CW_*.pdf`
- `outputs/graphs/*.png`

Beispiel:

```bash
chmod +x scripts/update_all.sh
./scripts/update_all.sh
```

Hinweis: In Codespaces/Devcontainers ist `pandoc` + `wkhtmltopdf` normalerweise
vorinstalliert (siehe `.devcontainer`), sodass PDFs erzeugt werden. Falls die
Tools nicht verfügbar sind, überspringt das Skript die PDF-Erzeugung und schreibt
nur die Markdown‑Artefakte.

Hinweis zu `--include-logs`
--------------------------

Das Skript `export_meals_pdf.py` unterstützt die Option `--include-logs`, die
zusätzlich zu den Dateien unter `--root` noch Markdown-Dateien aus dem Ordner
`logs/daily/` (relativ zum Parent von `--root`) einliest. Praktische Punkte:

- Pfad: Wenn du `--root protocol` übergibst, sucht das Skript außerdem in
	`protocol/../logs/daily/` (also `logs/daily/` neben `protocol/`).
- Deduplizierung: Gefundene Dateipfade werden vor dem Verarbeiten dedupliziert
	(nach aufgelöstem Pfad). Wenn die gleichen Inhalte also sowohl in `protocol/`
	als auch in `logs/daily/` liegen, werden doppelte Pfade nicht doppelt ausgegeben.
- Warum nutzen: Verwende `--include-logs`, wenn du ältere Einträge oder eine
	getrennte Log‑Historie in `logs/daily/` hast und beide Quellen in der Ausgabe
	zusammengeführt werden sollen.
- Vorsicht: `scripts/update_all.sh` ruft das Wrapper-Skript standardmäßig ohne
	`--include-logs` auf. Falls du beim zentralen One‑liner auch die Logs mit
	einbeziehen willst, rufe `export_meals_pdf.py` manuell mit `--include-logs`
	oder passe `scripts/update_all.sh` an.

Beispiel (inkl. Logs):

```bash
python3 scripts/export_meals_pdf.py --root protocol --include-logs --out-md outputs/meals_combined.md --out-pdf outputs/meals_combined.pdf
```
```
# body-recomposition — Logs, Parser & Summaries

Kurz: Dieses Repo sammelt tägliche Protokolle (Markdown), rechnet Nährwerte aus und erzeugt zusammengefasste Artefakte (Markdown, Excel, Grafiken) via GitHub Actions.

Wichtige Ordner
- `protocol/` — deine täglichen Protokolle (empfohlen: `YYYY-MM-DD.md` oder in Unterordnern)
- `data/foods.yaml` — Lebensmittel‑Datenbank (per 100 g) mit `aliases`
- `scripts/` — Parser und Aggregatoren (`parse_logs.py`, `aggregate_protocol.py`, `plot_metrics.py`)
- `outputs/` — generierte Artefakte (wird von Actions hochgeladen)

Frontmatter / Header‑Konvention (empfohlen)
- Verwende YAML‑Frontmatter oben in der Datei oder einen Kopfblock mit `key: value`-Zeilen.
- Felder (empfohlen): `date` (ISO `YYYY-MM-DD`), `weight_kg`, `bodyfat_pct`, `target_calories`, `target_protein_g`, `target_fat_g`, `target_carbs_g`, `actual_*`, `sleep` (z. B. `7:24`), `comment`.
- Einheitsempfehlung: Zahlen mit Dezimalpunkt (z. B. `70.9`). Der Parser toleriert Komma und verschiedene Einheiten und normalisiert sie.

Wie lokal ausführen
1. Python‑Umgebung einrichten (empfohlen):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r scripts/requirements.txt
```

2. Parser (generiert `outputs/data/summary.json`):

```bash
python scripts/parse_logs.py
```

3. Aggregiere Protocol‑Header (generiert `outputs/protocol_summary.md` und `outputs/protocol_summary.xlsx`):

```bash
python scripts/aggregate_protocol.py
```

GitHub Actions
- Workflow: `.github/workflows/generate-summaries.yml`
- Trigger: Push auf `logs/**`, `data/**`, `protocol/**` und geplanter Tageslauf.
- Artefakte: `outputs/` werden als `body-summaries` hochgeladen (Retention: 90 Tage).

Artefakte herunterladen
- Web UI: Repository → Actions → Workflow Run → Artifacts → Download
- GH CLI: z. B. `gh run list --workflow generate-summaries.yml` und `gh run download <run-id> --name body-summaries`

Weiteres
- Wenn du möchtest, kann der Workflow geändert werden, um Grafiken zu committen, in GitHub Pages zu veröffentlichen oder ein Release zu erstellen. Das kann Commit‑Loops erzeugen — ich empfehle zuerst Artefakte.

Wenn du konkrete Feld‑Namen bevorzugst (z. B. `weight_kg` genau so), sag Bescheid — ich kann Validierung/Schema‑Checks hinzufügen.
