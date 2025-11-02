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
