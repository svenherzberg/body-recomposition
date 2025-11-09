#!/usr/bin/env python3
"""
Minimal parser for daily logs. Supports:
- YAML frontmatter (preferred) or simple key:value header
- Meal lines like "25 g oats" or "125 g Uncle Bens Vollkornreis"
- Fuzzy matching against `data/foods.yaml` aliases using difflib

Outputs:
- outputs/data/summary.json (list of days with metadata + consumed nutrients)
- outputs/data/missing_foods.json (items that couldn't be matched)
"""
import os
import re
import json
import yaml
import frontmatter
from glob import glob
from difflib import get_close_matches
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'data')
PROTOCOL_DIR = os.path.join(ROOT, 'protocol')
LOG_DIR = os.path.join(ROOT, 'logs', 'daily')
OUT_DIR = os.path.join(ROOT, 'outputs', 'data')
os.makedirs(OUT_DIR, exist_ok=True)


def load_foods(path):
    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    foods = raw or {}
    slug_by_alias = {}
    all_aliases = []
    for slug, entry in foods.items():
        aliases = entry.get('aliases', [])
        # include slug itself and the name
        aliases.append(slug)
        aliases.append(entry.get('name',''))
        for a in aliases:
            if not a:
                continue
            key = a.lower()
            slug_by_alias[key] = slug
            all_aliases.append(key)
    return foods, slug_by_alias, sorted(set(all_aliases))


def to_number(s):
    if s is None:
        return None
    s = str(s).strip()
    s = s.replace(',', '.')
    m = re.search(r"[0-9]+\.?[0-9]*", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_header_kv(text):
    meta = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            break
        if ':' in line:
            k, v = line.split(':', 1)
            key = k.strip().lower().replace(' ', '_')
            meta[key] = v.strip()
    # normalize some known keys
    mapping = {
        'weight': 'weight_kg',
        'bodyfat_percentage': 'bodyfat_pct',
        'target_calories': 'target_calories',
    }
    for old, new in mapping.items():
        if old in meta:
            meta[new] = to_number(meta[old])
    # convert numeric-looking fields
    for k in list(meta.keys()):
        if re.search(r"\d", str(meta[k])):
            n = to_number(meta[k])
            if n is not None:
                meta[k] = n
    return meta


def parse_food_line(line):
    # strip bullets and whitespace
    line = line.strip()
    line = re.sub(r'^[-\*]\s*', '', line)
    # expectation: '<qty> g <name>' or '<qty>g <name>'
    m = re.match(r'^(?P<qty>[0-9]+[\.,]?[0-9]*)\s*(?P<unit>g|gramm|g\.)?\s+(?P<name>.+)$', line, re.I)
    if m:
        qty = to_number(m.group('qty'))
        name = m.group('name').strip()
        return qty, 'g', name
    # fallback: try to find a number anywhere
    m2 = re.search(r'(?P<qty>[0-9]+[\.,]?[0-9]*)', line)
    if m2:
        qty = to_number(m2.group('qty'))
        name = line[m2.end():].strip()
        if name:
            return qty, None, name
    return None


def match_food(name, slug_by_alias, aliases_list, threshold=0.6):
    key = name.lower()
    # direct alias match
    if key in slug_by_alias:
        return slug_by_alias[key], 1.0
    # try tokens (last word)
    tokens = [t.strip() for t in re.split(r'[ ,\-_/]+', key) if t]
    for t in reversed(tokens):
        if t in slug_by_alias:
            return slug_by_alias[t], 0.9
    # fuzzy match against aliases_list
    matches = get_close_matches(key, aliases_list, n=3, cutoff=threshold)
    if matches:
        best = matches[0]
        return slug_by_alias.get(best), 0.8
    return None, 0.0


def compute_nutrients(qty_g, food_entry):
    factor = (qty_g or 0) / 100.0
    return {
        'kcal': round(food_entry.get('kcal_per_100g', 0) * factor, 2),
        'protein_g': round(food_entry.get('protein_g_per_100g', 0) * factor, 2),
        'carbs_g': round(food_entry.get('carbs_g_per_100g', 0) * factor, 2),
        'fat_g': round(food_entry.get('fat_g_per_100g', 0) * factor, 2),
    }


def process_file(path, foods, slug_by_alias, aliases_list):
    post = None
    used_fallback_text = None
    try:
        post = frontmatter.load(path)
    except Exception:
        # fall back to manual read
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        used_fallback_text = text
        post = frontmatter.loads('---\n---\n' + text)

    meta = post.metadata or {}
    # normalize frontmatter keys to lowercase with underscores so downstream code can find them
    if isinstance(meta, dict) and meta:
        meta = {str(k).strip().lower().replace(' ', '_'): v for k, v in meta.items()}
    # normalize frontmatter keys to lowercase with underscores so downstream code can find them
    if isinstance(meta, dict) and meta:
        meta = {str(k).strip().lower().replace(' ', '_'): v for k, v in meta.items()}
    if not meta and used_fallback_text is not None:
        # try parse header KV style (the file you provided)
        meta = parse_header_kv(used_fallback_text)
        # remove header block (lines up to first blank line) from content to avoid parsing header lines as foods
        lines = used_fallback_text.splitlines()
        header_end = 0
        for i, L in enumerate(lines):
            if not L.strip():
                header_end = i
                break
        # content after header
        remainder = '\n'.join(lines[header_end+1:])
        post.content = remainder

    date = meta.get('date') or os.path.basename(path).replace('.md', '')
    # ensure numeric normalization (convert numeric-looking strings to numbers)
    for k, v in list(meta.items()):
        if isinstance(v, str):
            num = to_number(v)
            if num is not None:
                meta[k] = num

    consumed = defaultdict(float)
    missing = []
    # extract a Status/Agenda section from content: look for a heading 'Status' or 'Agenda' and collect following non-empty lines
    status_text = None
    for line in post.content.splitlines():
        # detect a heading like 'Status' or 'Agenda' (standalone line)
        if line.strip().lower() in ('status', 'agenda'):
            # collect subsequent non-empty lines until next blank line or next heading starting with '**' or '#'
            buf = []
            collect = False
            for L in post.content.splitlines()[post.content.splitlines().index(line)+1:]:
                s = L.strip()
                if not s:
                    break
                if s.startswith('#') or s.startswith('**'):
                    break
                buf.append(s)
            if buf:
                # join lines and keep short (first 120 chars)
                status_text = ' '.join(buf).strip()
                if len(status_text) > 120:
                    status_text = status_text[:117] + '...'
            break
    if status_text:
        meta['status'] = status_text

    for line in post.content.splitlines():
        if not line.strip():
            continue
        # accept list lines and plain lines
        parsed = parse_food_line(line)
        if not parsed:
            continue
        qty, unit, name = parsed
        if qty is None or name is None:
            continue
        # match food
        slug, score = match_food(name, slug_by_alias, aliases_list)
        if not slug:
            missing.append({'file': os.path.basename(path), 'line': line.strip(), 'name': name})
            continue
        entry = foods.get(slug)
        if not entry:
            missing.append({'file': os.path.basename(path), 'line': line.strip(), 'name': name})
            continue
        nutrients = compute_nutrients(qty, entry)
        for k, v in nutrients.items():
            consumed[k] += v

    result = {
        'file': os.path.basename(path),
        'date': date,
        'meta': meta,
        'consumed': {k: round(v, 2) for k, v in consumed.items()}
    }
    return result, missing


def main():
    foods, slug_by_alias, aliases_list = load_foods(os.path.join(DATA_DIR, 'foods.yaml'))
    summary = []
    all_missing = []
    # read all markdown files under protocol/ recursively
    files = sorted(glob(os.path.join(PROTOCOL_DIR, '**', '*.md'), recursive=True))
    if not files:
        print('No protocol files found in', PROTOCOL_DIR)
    for path in files:
        res, missing = process_file(path, foods, slug_by_alias, aliases_list)
        summary.append(res)
        all_missing.extend(missing)

    out_summary = os.path.join(OUT_DIR, 'summary.json')
    with open(out_summary, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    out_missing = os.path.join(OUT_DIR, 'missing_foods.json')
    with open(out_missing, 'w', encoding='utf-8') as f:
        json.dump(all_missing, f, ensure_ascii=False, indent=2)

    print('Wrote', out_summary)
    print('Wrote', out_missing, 'missing count=', len(all_missing))


if __name__ == '__main__':
    main()
