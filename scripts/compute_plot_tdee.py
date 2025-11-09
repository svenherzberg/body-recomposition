#!/usr/bin/env python3
"""Compute rolling TDEE estimates from `outputs/data/summary.json` and plot them.

Writes:
- `outputs/data/tdee.json` (summary + raw estimates)
- `outputs/graphs/tdee.png`

Method:
- For each day (window end) compute over a rolling window (default 14 days):
  - require at least two weight measurements in the window to compute ΔW
  - compute mean(actual_calories) over window
  - daily_energy_change = (ΔW * 7700) / days_between_weights
  - TDEE = mean(actual_calories) - daily_energy_change

Smoothed series: 7-day rolling mean of the point estimates.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FN = ROOT / "outputs" / "data" / "summary.json"
TDEE_JSON = ROOT / "outputs" / "data" / "tdee.json"
TDEE_PNG = ROOT / "outputs" / "graphs" / "tdee.png"


def load_summary() -> pd.DataFrame:
    data = json.loads(SUMMARY_FN.read_text(encoding="utf-8"))
    rows: List[dict] = []
    for item in data:
        date = item.get("date")
        meta = item.get("meta", {})
        weight = meta.get("weight")
        actual_cal = meta.get("actual_calories")
        rows.append({"date": date, "weight": weight, "actual_calories": actual_cal})
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def compute_tdee(df: pd.DataFrame, window_days: int = 14) -> pd.DataFrame:
    # Create a date-indexed series that covers all dates in range
    idx = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    # reindex the original data to full daily range
    df_indexed = df.set_index("date").reindex(idx)
    df_full = pd.DataFrame(index=idx)
    df_full["weight"] = df_indexed.get("weight")
    df_full["actual_calories"] = df_indexed.get("actual_calories")

    estimates = []
    half_window = window_days - 1
    for end in df_full.index:
        start = end - pd.Timedelta(days=window_days - 1)
        window = df_full.loc[start:end]
        # need at least two non-null weight values to compute delta
        w = window["weight"].dropna()
        ac = window["actual_calories"].dropna()
        if len(w) >= 2 and len(ac) >= 1:
            first_date = w.index[0]
            last_date = w.index[-1]
            days = (last_date - first_date).days
            if days <= 0:
                continue
            delta_w = float(w.iloc[-1] - w.iloc[0])
            mean_cal = float(ac.mean())
            daily_change = (delta_w * 7700.0) / days
            tdee = mean_cal - daily_change
            estimates.append({"date": end.date().isoformat(), "tdee": tdee, "window_start": first_date.date().isoformat(), "window_end": last_date.date().isoformat(), "mean_cal": mean_cal, "delta_w": delta_w, "days": days})

    est_df = pd.DataFrame(estimates)
    if est_df.empty:
        raise SystemExit("Not enough data to compute TDEE estimates: need at least two weight measurements and calorie data.")
    est_df["date"] = pd.to_datetime(est_df["date"])
    est_df = est_df.sort_values("date").reset_index(drop=True)
    # smooth
    est_df["tdee_smooth"] = est_df["tdee"].rolling(window=7, min_periods=1, center=True).mean()
    return est_df


def write_outputs(est_df: pd.DataFrame) -> None:
    TDEE_JSON.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for r in est_df.to_dict(orient="records"):
        # ensure primitives only
        records.append({
            "date": r.get("date").isoformat() if hasattr(r.get("date"), "isoformat") else r.get("date"),
            "tdee": float(r.get("tdee")),
            "tdee_smooth": float(r.get("tdee_smooth")) if r.get("tdee_smooth") is not None else None,
            "window_start": r.get("window_start"),
            "window_end": r.get("window_end"),
            "mean_cal": float(r.get("mean_cal")),
            "delta_w": float(r.get("delta_w")),
            "days": int(r.get("days")),
        })
    out = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "n_estimates": int(len(records)),
        "tdee_mean": float(est_df["tdee"].mean()),
        "tdee_median": float(est_df["tdee"].median()),
        "estimates": records,
    }
    TDEE_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")


def plot(est_df: pd.DataFrame) -> None:
    TDEE_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(est_df["date"], est_df["tdee"], marker="o", linestyle="", alpha=0.45, label="estimate")
    ax.plot(est_df["date"], est_df["tdee_smooth"], color="C1", linewidth=2.0, label="7-day smooth")
    ax.axhline(est_df["tdee"].mean(), color="gray", linestyle="--", label=f"mean {est_df['tdee'].mean():.0f} kcal")
    ax.axhline(est_df["tdee"].median(), color="brown", linestyle=":", label=f"median {est_df['tdee'].median():.0f} kcal")
    ax.set_ylabel("TDEE (kcal/day)")
    ax.set_title("Estimated TDEE over time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    ax.legend()
    fig.tight_layout()
    plt.savefig(TDEE_PNG)
    plt.close(fig)


def main() -> int:
    df = load_summary()
    est_df = compute_tdee(df, window_days=14)
    write_outputs(est_df)
    plot(est_df)
    print(f"Wrote {TDEE_JSON}")
    print(f"Wrote {TDEE_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
