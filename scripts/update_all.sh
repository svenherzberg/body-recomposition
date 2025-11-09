#!/usr/bin/env bash
set -euo pipefail

# Central runner to regenerate all outputs from protocol markdown files.
# Usage: scripts/update_all.sh
# Optional: set PYTHON to use a different python interpreter, e.g. PYTHON=python3.11 ./scripts/update_all.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

echo "[update_all] ROOT=$ROOT"

echo "[update_all] Running aggregate_protocol.py -> protocol_summary.md/.xlsx"
"$PYTHON" "$ROOT/scripts/aggregate_protocol.py"

echo "[update_all] Running parse_logs.py -> outputs/data/summary.json"
"$PYTHON" "$ROOT/scripts/parse_logs.py"

echo "[update_all] Running export_meals_pdf.py -> outputs/meals_combined.md & weekly files"
"$PYTHON" "$ROOT/scripts/export_meals_pdf.py" --root "$ROOT/protocol" --out-md "$ROOT/outputs/meals_combined.md"

echo "[update_all] Running plot_metrics.py -> outputs/graphs/*.png"
"$PYTHON" "$ROOT/scripts/plot_metrics.py"

echo "[update_all] Done. Outputs are in $ROOT/outputs/"

exit 0
