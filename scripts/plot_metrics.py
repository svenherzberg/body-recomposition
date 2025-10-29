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
            'status': meta.get('status') if isinstance(meta, dict) else None,
            # macros (grams)
            'consumed_protein_g': float(item.get('consumed', {}).get('protein_g', 0)),
            'consumed_fat_g': float(item.get('consumed', {}).get('fat_g', 0)),
            'consumed_carbs_g': float(item.get('consumed', {}).get('carbs_g', 0)),
            'target_protein_g': to_float(meta.get('target_protein_g') or meta.get('target_protein') or meta.get('target_protein_g')),
            'target_fat_g': to_float(meta.get('target_fat_g') or meta.get('target_fat') or meta.get('target_fat_g')),
            'target_carbs_g': to_float(meta.get('target_carbs_g') or meta.get('target_carbs') or meta.get('target_carbs_g')),
            'actual_protein_g': to_float(meta.get('actual_protein_g') or meta.get('actual_protein') or meta.get('actual_protein_g')),
            'actual_fat_g': to_float(meta.get('actual_fat_g') or meta.get('actual_fat') or meta.get('actual_fat_g')),
            'actual_carbs_g': to_float(meta.get('actual_carbs_g') or meta.get('actual_carbs') or meta.get('actual_carbs_g')),
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
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(df['date'], df['weight_kg'], marker='o', linestyle='-', label='Weight (kg)')
    if len(df) >= 3:
        df['w_ma'] = df['weight_kg'].rolling(window=7, min_periods=1).mean()
        ax.plot(df['date'], df['w_ma'], linestyle='--', label='7-day MA')
    ax.set_xlabel('Date')
    ax.set_ylabel('Weight (kg)')
    ax.set_title('Weight over time')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, 'weight.png')
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)


# status annotations removed per user request


def plot_bodyfat(df):
    if df['bodyfat_pct'].notna().sum() == 0:
        print('No bodyfat data to plot')
        return
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(df['date'], df['bodyfat_pct'], marker='o', linestyle='-', color='C1')
    ax.set_xlabel('Date')
    ax.set_ylabel('Bodyfat (%)')
    ax.set_title('Bodyfat over time')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, 'bodyfat.png')
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)


def plot_calories(df):
    if df['consumed_kcal'].notna().sum() == 0 and df['target_calories'].notna().sum() == 0:
        print('No calorie data to plot')
        return
    fig, ax = plt.subplots(figsize=(10,4))
    x = df['date']
    width = 0.6
    # consumed (kcal) intentionally hidden per user request
    if df['target_calories'].notna().sum() > 0:
        ax.plot(x, df['target_calories'], marker='o', color='C0', label='Target kcal')
    if df['actual_calories'].notna().sum() > 0:
        ax.plot(x, df['actual_calories'], marker='x', color='C3', label='Actual (scale)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Calories (kcal)')
    ax.set_title('Calories: consumed vs target')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, 'calories.png')
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)


def _plot_macro(df, consumed_col, target_col, actual_col, ylabel, outname):
    # if there's no consumed and no target, skip
    if df[consumed_col].notna().sum() == 0 and df[target_col].notna().sum() == 0 and df[actual_col].notna().sum() == 0:
        print('No data to plot for', outname)
        return
    fig, ax = plt.subplots(figsize=(10,4))
    x = df['date']
    width = 0.6
    ax.bar(x, df[consumed_col], width=width, label=f'Consumed ({ylabel})', color='C2')
    if df[target_col].notna().sum() > 0:
        ax.plot(x, df[target_col], marker='o', color='C0', label=f'Target ({ylabel})')
    if df[actual_col].notna().sum() > 0:
        ax.plot(x, df[actual_col], marker='x', color='C3', label='Actual (scale)')
    ax.set_xlabel('Date')
    ax.set_ylabel(ylabel)
    ax.set_title(f'{ylabel}: consumed vs target')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, outname)
    fig.savefig(out)
    plt.close(fig)
    print('Wrote', out)


def plot_protein(df):
    _plot_macro(df, 'consumed_protein_g', 'target_protein_g', 'actual_protein_g', 'Protein (g)', 'protein.png')


def plot_fat(df):
    _plot_macro(df, 'consumed_fat_g', 'target_fat_g', 'actual_fat_g', 'Fat (g)', 'fat.png')


def plot_carbs(df):
    _plot_macro(df, 'consumed_carbs_g', 'target_carbs_g', 'actual_carbs_g', 'Carbs (g)', 'carbs.png')


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
    # macros
    plot_protein(df)
    plot_fat(df)
    plot_carbs(df)


if __name__ == '__main__':
    main()
