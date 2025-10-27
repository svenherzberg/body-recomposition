#!/usr/bin/env python3
"""
Aggregate YAML-like header key:value blocks from all files under `protocol/` into a single
Markdown table sorted by filename (date). Writes `outputs/protocol_summary.md`.

Behavior:
- For each `protocol/**/*.md` file, try to load YAML frontmatter via python-frontmatter.
- If no frontmatter, parse top header lines as key:value pairs until first blank line.
- The table columns are: `file` plus the union of all keys found (sorted).
"""
import os
import re
import frontmatter
from glob import glob
from collections import OrderedDict


def normalize_value(v, key=None):
    """Normalize a header value:
    - convert comma decimal to dot
    - strip units like kcal, g, cm
    - convert time 'HH:MM' to decimal hours (rounded to 2 decimals)
    - return numeric values as plain numbers (no unit), else return original string
    """
    if v is None:
        return ''
    s = str(v).strip()
    if not s:
        return ''
    s = s.strip('"\'')
    # time hh:mm -> decimal hours
    m = re.match(r'^(?P<h>\d{1,2}):(?P<m>\d{1,2})$', s)
    if m:
        h = int(m.group('h'))
        mm = int(m.group('m'))
        dec = h + mm / 60.0
        # format with 2 decimals, drop .00
        if abs(dec - round(dec)) < 1e-9:
            return str(int(round(dec)))
        return f"{dec:.2f}"
    # number with optional unit
    m2 = re.match(r'^[^0-9+-]*?(?P<num>[+-]?[0-9]+[\.,]?[0-9]*)(?:\s*(?P<unit>[%a-zA-Z]+))?$', s)
    if m2:
        num = m2.group('num').replace(',', '.')
        try:
            f = float(num)
        except Exception:
            return s
        # for percentages or counts, return integer if whole
        if abs(f - round(f)) < 1e-9:
            return str(int(round(f)))
        return str(round(f, 2))
    # fallback: return original string
    return s

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROTOCOL_DIR = os.path.join(ROOT, 'protocol')
OUT_DIR = os.path.join(ROOT, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)


def parse_header_kv_from_text(text):
    meta = OrderedDict()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            break
        if ':' in line:
            k, v = line.split(':', 1)
            key = k.strip()
            val = v.strip()
            # normalize numeric commas to dots for consistency
            val = val.replace(',', '.')
            meta[key] = val
    return meta


def load_file_meta(path):
    try:
        post = frontmatter.load(path)
        if post.metadata:
            return OrderedDict((k, str(v)) for k, v in post.metadata.items())
    except Exception:
        pass
    # fallback: parse top header section until blank line
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    # handle files that use non-standard delimiter lines (e.g. '⸻' or '---')
    lines = text.splitlines()
    # skip leading blank lines
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        first = lines[i].strip()
        # delimiter if line contains only punctuation/symbols (like ---- or ⸻)
        if re.match(r'^[^\w\s]+$', first):
            # find closing delimiter
            j = i + 1
            while j < len(lines):
                if lines[j].strip() and re.match(r'^[^\w\s]+$', lines[j].strip()):
                    # header is lines between i and j
                    header_block = '\n'.join(lines[i+1:j])
                    return parse_header_kv_from_text(header_block)
                j += 1
    # fallback: parse from top until blank line
    return parse_header_kv_from_text(text)


def gather_protocol_metas():
    files = sorted(glob(os.path.join(PROTOCOL_DIR, '**', '*.md'), recursive=True))
    rows = []
    keys = []
    for p in files:
        rel = os.path.relpath(p, ROOT)
        meta = load_file_meta(p)
        # normalize keys (map common variants to canonical names)
        normalized = OrderedDict()
        for k, v in meta.items():
            lk = k.strip().lower().replace(' ', '_')
            # mapping of common header names to canonical keys
            mapping = {
                'weight': 'weight_kg',
                'weight_kg': 'weight_kg',
                'bodyfat': 'bodyfat_pct',
                'bodyfat_percentage': 'bodyfat_pct',
                'water_percentage': 'water_pct',
                'muscle_percentage': 'muscle_pct',
                'bones': 'bones_pct',
                'target_calories': 'target_calories',
                'calories': 'target_calories',
                'target_protein': 'target_protein_g',
                'target_protein_g': 'target_protein_g',
                'target_fat': 'target_fat_g',
                'target_fat_g': 'target_fat_g',
                'target_carbs': 'target_carbs_g',
                'target_carbs_g': 'target_carbs_g',
                'actual_calories': 'actual_calories',
                'actual_protein': 'actual_protein_g',
                'actual_fat': 'actual_fat_g',
                'actual_carbs': 'actual_carbs_g',
                'abdgirth': 'abdgirth_cm',
                'abdgirth_cm': 'abdgirth_cm',
                'sleep': 'sleep',
                'steps': 'steps',
                'comment': 'comment',
                'date': 'date',
            }
            canon = mapping.get(lk, lk)
            normalized[canon] = str(v)

        # ensure a parsed date field exists (from frontmatter or filename)
        parsed_date = ''
        if 'date' in normalized and normalized['date']:
            parsed_date = normalized['date']
        else:
            # try extract yyyy-mm-dd from filename
            m = re.search(r"(\d{4}-\d{2}-\d{2})", rel)
            if m:
                parsed_date = m.group(1)
        if parsed_date:
            normalized['date'] = parsed_date

        # normalize values (numbers: comma->dot, strip units; sleep: hh:mm -> decimal hours)
        for k, v in list(normalized.items()):
            normalized[k] = normalize_value(v, key=k)

        rows.append((rel, normalized))
        for k in normalized.keys():
            if k not in keys:
                keys.append(k)

    # enforce preferred column order: date first, then file, then known keys
    preferred = [
        'date', 'weight_kg', 'bodyfat_pct', 'water_pct', 'muscle_pct', 'bones_pct',
        'target_calories', 'target_protein_g', 'target_fat_g', 'target_carbs_g',
        'actual_calories', 'actual_protein_g', 'actual_fat_g', 'actual_carbs_g',
        'abdgirth_cm', 'sleep', 'steps', 'comment'
    ]
    # include any other keys that were found but not in preferred
    remaining = [k for k in keys if k not in preferred]
    ordered_keys = [k for k in preferred if k in keys] + sorted(remaining)
    # sort rows by date if possible (ISO yyyy-mm-dd), newest last
    def row_date_key(item):
        rel, meta = item
        d = meta.get('date', '')
        return d or rel

    rows_sorted = sorted(rows, key=row_date_key)
    return rows_sorted, ordered_keys


def write_markdown_table(rows, keys, outpath):
    # header: file + keys
    header_cols = ['file'] + keys
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('# Protocol headers summary\n\n')
        f.write('Generated from `protocol/` files. Columns are the union of header keys found.\n\n')
        # header row
        f.write('| ' + ' | '.join(header_cols) + ' |\n')
        f.write('| ' + ' | '.join(['---'] * len(header_cols)) + ' |\n')
        for rel, meta in rows:
            vals = []
            for k in keys:
                v = meta.get(k, '')
                # escape pipes
                v = str(v).replace('|', '\\|')
                vals.append(v)
            f.write('| ' + ' | '.join([rel] + vals) + ' |\n')


def main():
    rows, keys = gather_protocol_metas()
    out = os.path.join(OUT_DIR, 'protocol_summary.md')
    write_markdown_table(rows, keys, out)
    print('Wrote', out)


if __name__ == '__main__':
    main()
