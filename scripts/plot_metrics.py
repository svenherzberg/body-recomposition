#!/usr/bin/env python3
"""
Generate simple plots from outputs/data/summary.json:
- weight over time (with optional rolling mean)
- bodyfat over time
- calories eaten (consumed) vs target/actual

Outputs: PNG files in outputs/graphs/
"""
import os
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_SUMMARY = os.path.join(ROOT, 'outputs', 'data', 'summary.json')
OUT_DIR = os.path.join(ROOT, 'outputs', 'graphs')
os.makedirs(OUT_DIR, exist_ok=True)


def load_summary(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    rows = []
    for item in data:
        meta = item.get('meta', {})
        date = item.get('date') or meta.get('date')
        try:
            dt = datetime.fromisoformat(date)
        except Exception:
            dt = None
        rows.append({
            'date': dt,
            'weight_kg': to_float(meta.get('weight_kg') or meta.get('weight') or meta.get('⸻weight')),
            'bodyfat_pct': to_float(meta.get('bodyfat_pct') or meta.get('bodyfat_percentage')),
            'target_calories': to_float(meta.get('target_calories')),
            'actual_calories': to_float(meta.get('actual_calories')),
            'consumed_kcal': float(item.get('consumed', {}).get('kcal', 0)),
        })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=['date']).sort_values('date')
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    return df


def to_float(v):
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return None


def plot_weight(df):
    if df['weight_kg'].notna().sum() == 0:
        print('No weight data to plot')
        return
    plt.figure(figsize=(8,4))
    plt.plot(df['date'], df['weight_kg'], marker='o', linestyle='-', label='Weight (kg)')
    if len(df) >= 3:
        df['w_ma'] = df['weight_kg'].rolling(window=7, min_periods=1).mean()
        plt.plot(df['date'], df['w_ma'], linestyle='--', label='7-day MA')
    plt.xlabel('Date')
    plt.ylabel('Weight (kg)')
    plt.title('Weight over time')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'weight.png')
    plt.savefig(out)
    plt.close()
    print('Wrote', out)


def plot_bodyfat(df):
    if df['bodyfat_pct'].notna().sum() == 0:
        print('No bodyfat data to plot')
        return
    plt.figure(figsize=(8,4))
    plt.plot(df['date'], df['bodyfat_pct'], marker='o', linestyle='-', color='C1')
    plt.xlabel('Date')
    plt.ylabel('Bodyfat (%)')
    plt.title('Bodyfat over time')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'bodyfat.png')
    plt.savefig(out)
    plt.close()
    print('Wrote', out)


def plot_calories(df):
    if df['consumed_kcal'].notna().sum() == 0 and df['target_calories'].notna().sum() == 0:
        print('No calorie data to plot')
        return
    plt.figure(figsize=(10,4))
    x = df['date']
    width = 0.6
    plt.bar(x, df['consumed_kcal'], width=width, label='Consumed (kcal)', color='C2')
    if df['target_calories'].notna().sum() > 0:
        plt.plot(x, df['target_calories'], marker='o', color='C0', label='Target kcal')
    if df['actual_calories'].notna().sum() > 0:
        plt.plot(x, df['actual_calories'], marker='x', color='C3', label='Actual (scale)')
    plt.xlabel('Date')
    plt.ylabel('Calories (kcal)')
    plt.title('Calories: consumed vs target')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'calories.png')
    plt.savefig(out)
    plt.close()
    print('Wrote', out)


def main():
    if not os.path.exists(DATA_SUMMARY):
        print('Summary file not found:', DATA_SUMMARY)
        return
    df = load_summary(DATA_SUMMARY)
    if df.empty:
        print('No data in summary')
        return
    plot_weight(df)
    plot_bodyfat(df)
    plot_calories(df)


if __name__ == '__main__':
    main()
