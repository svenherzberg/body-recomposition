#!/usr/bin/env python3
"""Write a short markdown summary with key TDEE metrics based on outputs/data/tdee.json.

Creates: outputs/tdee_summary.md
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TDEE_JSON = ROOT / "outputs" / "data" / "tdee.json"
OUT_MD = ROOT / "outputs" / "tdee_summary.md"


def load():
    j = json.loads(TDEE_JSON.read_text(encoding="utf-8"))
    return j


def fmt_date(s: str) -> str:
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return s


def main():
    data = load()
    estimates = data.get("estimates", [])
    if not estimates:
        print("No TDEE estimates found in", TDEE_JSON)
        return 2

    n = data.get("n_estimates", len(estimates))
    tdee_mean = data.get("tdee_mean")
    tdee_median = data.get("tdee_median")

    # period: earliest window_start to latest window_end
    starts = [e.get("window_start") for e in estimates if e.get("window_start")]
    ends = [e.get("window_end") for e in estimates if e.get("window_end")]
    period_start = fmt_date(min(starts)) if starts else None
    period_end = fmt_date(max(ends)) if ends else None

    last = estimates[-1]
    last_date = fmt_date(last.get("date"))
    last_tdee = last.get("tdee")
    last_mean_cal = last.get("mean_cal")
    last_delta_w = last.get("delta_w")

    recommend_surplus = int(round(tdee_mean + 300)) if tdee_mean else None
    recommend_cut = int(round(tdee_mean - 500)) if tdee_mean else None

    parts = ["# TDEE Zusammenfassung\n"]
    parts.append(f"**Bereich der Schätzung:** {period_start} — {period_end}\n")
    parts.append(f"**Anzahl Estimates:** {n}\n")
    parts.append("\n")
    parts.append("## Kennzahlen\n")
    parts.append(f"- Mittlere geschätzte TDEE: **{int(round(tdee_mean))} kcal/Tag**\n")
    parts.append(f"- Median geschätzte TDEE: **{int(round(tdee_median))} kcal/Tag**\n")
    parts.append("\n")
    parts.append("## Letzte Schätzung\n")
    parts.append(f"- Datum: {last_date}\n")
    parts.append(f"- Geschätzter TDEE: **{int(round(last_tdee))} kcal/Tag**\n")
    parts.append(f"- Mittlere recorded Calories im Fenster: {int(round(last_mean_cal))} kcal/Tag\n")
    parts.append(f"- Gewichtsänderung im Fenster: {last_delta_w:+.2f} kg\n")
    parts.append("\n")
    parts.append("## Empfehlung (Faustregel)\n")
    parts.append("- Für moderaten Muskelaufbau: TDEE + ~250–500 kcal/Tag\n")
    if recommend_surplus:
        parts.append(f"  - Vorschlag: **{recommend_surplus} kcal/Tag** (≈ TDEE + 300)\n")
    parts.append("- Für langsamen Fettverlust: TDEE − ~300–600 kcal/Tag\n")
    if recommend_cut:
        parts.append(f"  - Beispiel Ziel (stärkeres Defizit): **{recommend_cut} kcal/Tag**\n")
    parts.append("\n")
    parts.append("## Hinweise zur Methodik\n")
    parts.append("- Schätzung basiert auf Gewichtsdifferenzen über Zeit + gemessenen `actual_calories`.\n")
    parts.append("- 1 kg Körpergewicht ≈ 7700 kcal (vereinfachende Annahme). Kurzfristige Schwankungen (Wasser, Glykogen) können die Schätzung verfälschen.\n")
    parts.append("- Empfehlung: längere Beobachtungsdauer (4+ Wochen) und sorgfältige Kalorienprotokollierung für robustere Werte.\n")

    OUT_MD.write_text("\n".join(parts), encoding="utf-8")
    print("Wrote", OUT_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
