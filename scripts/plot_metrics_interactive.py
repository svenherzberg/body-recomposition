#!/usr/bin/env python3
"""
Generate interactive Plotly HTML reports from outputs/data/summary.json.

Creates:
- outputs/graphs/weight.html
- outputs/graphs/bodyfat.html
- outputs/graphs/calories.html

These are standalone self-contained HTML files (plotly.js embedded).
"""
import os
import json
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_SUMMARY = os.path.join(ROOT, 'outputs', 'data', 'summary.json')
OUT_DIR = os.path.join(ROOT, 'outputs', 'graphs')
os.makedirs(OUT_DIR, exist_ok=True)


def to_float(v):
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return None


def load_df(path):
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
    return df


def write_html(fig, filename):
    out = os.path.join(OUT_DIR, filename)
    # embed the full plotly.js into the HTML so the file works offline
    pio.write_html(fig, file=out, full_html=True, include_plotlyjs=True)
    print('Wrote', out)


def interactive_weight(df):
    if df['weight_kg'].notna().sum() == 0:
        print('No weight data')
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['weight_kg'], mode='lines+markers', name='Weight (kg)'))
    if len(df) >= 3:
        df['w_ma'] = df['weight_kg'].rolling(window=7, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=df['date'], y=df['w_ma'], mode='lines', name='7-day MA'))
    fig.update_layout(title='Weight over time', xaxis_title='Date', yaxis_title='Weight (kg)', template='plotly_white')
    write_html(fig, 'weight.html')


def interactive_bodyfat(df):
    if df['bodyfat_pct'].notna().sum() == 0:
        print('No bodyfat data')
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['bodyfat_pct'], mode='lines+markers', name='Bodyfat (%)', marker=dict(color='orange')))
    fig.update_layout(title='Bodyfat over time', xaxis_title='Date', yaxis_title='Bodyfat (%)', template='plotly_white')
    write_html(fig, 'bodyfat.html')


def interactive_calories(df):
    if df['consumed_kcal'].notna().sum() == 0 and df['target_calories'].notna().sum() == 0:
        print('No calories data')
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['date'], y=df['consumed_kcal'], name='Consumed (kcal)', marker_color='lightseagreen'))
    if df['target_calories'].notna().sum() > 0:
        fig.add_trace(go.Scatter(x=df['date'], y=df['target_calories'], mode='lines+markers', name='Target kcal', marker=dict(color='red')))
    if df['actual_calories'].notna().sum() > 0:
        fig.add_trace(go.Scatter(x=df['date'], y=df['actual_calories'], mode='lines+markers', name='Actual (scale)', marker=dict(symbol='x')))
    fig.update_layout(title='Calories: consumed vs target', xaxis_title='Date', yaxis_title='kcal', template='plotly_white')
    write_html(fig, 'calories.html')


def main():
    if not os.path.exists(DATA_SUMMARY):
        print('Summary file not found:', DATA_SUMMARY)
        return
    df = load_df(DATA_SUMMARY)
    if df.empty:
        print('No data')
        return
    interactive_weight(df)
    interactive_bodyfat(df)
    interactive_calories(df)


if __name__ == '__main__':
    main()
