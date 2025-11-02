#!/usr/bin/env python3
"""
Collect meal sections from markdown files under `protocol/` (and optionally `logs/daily/`),
order entries by date, and produce a single combined Markdown and (optionally) PDF file.

Writes `outputs/meals_combined.md` and - if `pandoc` + `wkhtmltopdf` are available -
`outputs/meals_combined.pdf`.

This script is suitable to be run in CI and is accompanied by a GitHub Action workflow
that installs the system tools and runs the script.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from datetime import datetime
# glob is not used directly but kept for possible future expansion
# (we use Path.glob today)
from glob import glob
from pathlib import Path
from typing import List, Tuple

import frontmatter


MEAL_KEYS = ["Frühstück", "Mittagessen", "Abendessen", "Snacks"]
# Match either a bold inline header like **🍛 Mittagessen** or an ATX heading like
# ## 🍛 Mittagessen. Capture the inner header text as 'header'. We'll filter the
# captured headers against MEAL_KEYS to allow flexible variants (emoji, casing,
# surrounding punctuation).
MEAL_RE = re.compile(r"^\s*(?:\*\*(?P<h1>.+?)\*\*|#{1,6}\s*(?P<h2>.+?))\s*$", flags=re.I | re.M)


def find_markdown_files(root: Path, include_logs: bool = True) -> List[Path]:
    files = sorted(root.glob("**/*.md"))
    if include_logs:
        log_dir = root.parent / "logs" / "daily"
        if log_dir.exists():
            files += sorted(log_dir.glob("*.md"))
    # ensure unique and sorted
    unique = []
    seen = set()
    for p in files:
        s = str(p.resolve())
        if s not in seen:
            seen.add(s)
            unique.append(p)
    return unique


def parse_date_from_meta_or_filename(post, path: Path) -> str:
    # try frontmatter date
    date_val = None
    for key in ("date", "Date", "datetime"):
        if key in post.metadata:
            date_val = str(post.metadata[key])
            break
    if date_val:
        # try parse common formats, otherwise return raw
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(date_val, fmt)
                return dt.date().isoformat()
            except Exception:
                pass
        # fallback: extract yyyy-mm-dd if present
        m = re.search(r"(\d{4}-\d{2}-\d{2})", date_val)
        if m:
            return m.group(1)
        return date_val
    # otherwise try filename
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if m:
        return m.group(1)
    # fallback to file mtime
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def parse_date_value(date_str: str):
    """Try to parse a date string into a datetime.date. Return None if parsing fails."""
    if not date_str:
        return None
    # If it's already ISO-like, try fromisoformat
    try:
        # fromisoformat accepts YYYY-MM-DD and more
        return datetime.fromisoformat(date_str).date()
    except Exception:
        pass
    # try common formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue
    # fallback: extract yyyy-mm-dd
    m = re.search(r"(\d{4}-\d{2}-\d{2})", str(date_str))
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def extract_meal_sections(content: str) -> List[Tuple[str, str]]:
    """Return list of (header, section_text) in the order they appear."""
    matches = list(MEAL_RE.finditer(content))
    if not matches:
        # if no bold/ATX matches found, we will attempt to detect plain-line
        # headers like "Frühstück" (a single line containing only the meal
        # name). Continue — we'll still collect matches from the plain-line pass
        # below.
        matches = []
    sections = []
    # We only want headers that reference known meal keys; allow small variations
    # (emoji, bold vs heading, extra whitespace). Normalize by lowercasing and
    # checking for the meal keyword as substring.
    def is_meal_header(h: str) -> bool:
        s = h.lower()
        for key in MEAL_KEYS:
            if key.lower() in s:
                return True
        return False
    # Collect header positions from bold/ATX matches first
    # headers will be a list of tuples (start_pos, end_pos, header_text)
    headers: List[Tuple[int, int, str]] = []
    for m in matches:
        header = (m.group('h1') or m.group('h2') or '').strip()
        if header and is_meal_header(header):
            headers.append((m.start(), m.end(), header))

    # Also detect plain-line headers: lines that contain the meal word and
    # otherwise only punctuation/whitespace (e.g. "Frühstück" on its own line).
    if True:
        line_offsets = []
        off = 0
        for line in content.splitlines(True):
            line_offsets.append((off, line))
            off += len(line)

        for off, line in line_offsets:
            stripped = line.strip()
            if not stripped:
                continue
            # check for any meal key as whole word
            for key in MEAL_KEYS:
                if re.search(rf"\b{re.escape(key)}\b", stripped, flags=re.I):
                    rem = re.sub(rf"\b{re.escape(key)}\b", "", stripped, flags=re.I).strip()
                    if not rem or re.match(r'^[\W_\s]*$', rem):
                        # start is the line offset, end is offset + length of line
                        headers.append((off, off + len(line), stripped))
                    break

    # sort headers by position and produce sections between them
    headers = sorted(headers, key=lambda t: t[0])
    # deduplicate nearby/identical headers (same line captured twice via two
    # detection strategies). Keep the first occurrence when positions are very
    # close or normalized header text matches.
    deduped: List[Tuple[int, int, str]] = []
    last_pos = None
    last_norm = None
    for start_pos, end_pos, header in headers:
        norm = re.sub(r"[^0-9a-z]+", "", header.lower())
        if last_pos is not None and abs(start_pos - last_pos) < 4:
            # too close to previous header — skip
            continue
        if last_norm is not None and norm == last_norm:
            continue
        deduped.append((start_pos, end_pos, header))
        last_pos = start_pos
        last_norm = norm
    headers = deduped
    for i, (start_pos, end_pos, header) in enumerate(headers):
        # content starts after the header's end position
        start = end_pos
        end = headers[i + 1][0] if i + 1 < len(headers) else len(content)
        section = content[start:end].strip()
        section = section.strip('\n')
        sections.append((header, section))
    return sections


def load_file(path: Path) -> Tuple[str, List[Tuple[str, str]]]:
    try:
        post = frontmatter.load(path)
        content = post.content
    except Exception:
        # fallback: read file and remove YAML-like header
        text = path.read_text(encoding="utf-8")
        # remove frontmatter blocks between lines that are only punctuation
        # or between '---' lines
        if text.lstrip().startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                content = parts[2].lstrip('\n')
            else:
                content = text
        else:
            content = text
        post = frontmatter.loads("""---\n---\n""") if False else type("P", (), {"metadata": {}})()

    date = parse_date_from_meta_or_filename(post, path)
    sections = extract_meal_sections(content)
    return date, sections


def build_combined_md(entries: List[Tuple[str, Path, List[Tuple[str, str]]]]) -> str:
    parts = ["# Combined daily meals\n"]
    for date, path, sections in entries:
        # Show only the date as the daily header (do not include the file path/title).
        parts.append(f"## {date}\n")

        if not sections:
            parts.append("_No recognized meal sections found._\n\n")
            continue

        # Consolidate multiple detected headers that map to the same canonical
        # meal (e.g. '**Mittagessen**' and 'Mittagessen' or '### 🍛 Mittagessen')
        # into a single section per meal. Preserve unmatched sections in order.
        meals = {k: [] for k in MEAL_KEYS}
        others: List[Tuple[str, str]] = []

        for header, section in sections:
            matched = False
            for key in MEAL_KEYS:
                if key.lower() in header.lower():
                    meals[key].append(section.strip())
                    matched = True
                    break
            if not matched:
                others.append((header, section.strip()))

        # Output meals in preferred order, but only once per meal
        for key in MEAL_KEYS:
            blocks = meals.get(key)
            if blocks:
                parts.append(f"### {key}\n")
                for b in blocks:
                    parts.append(b.rstrip() + "\n\n")

        # Output any unmatched sections (preserve their original header text)
        for header, section in others:
            parts.append(f"### {header}\n")
            parts.append(section.rstrip() + "\n\n")
    return "\n".join(parts)


def build_day_md(date: str, sections: List[Tuple[str, str]]) -> str:
    """Build markdown for a single day (date header + meal sections)."""
    parts = [f"## {date}\n"]
    if not sections:
        parts.append("_No recognized meal sections found._\n\n")
        return "\n".join(parts)

    meals = {k: [] for k in MEAL_KEYS}
    others: List[Tuple[str, str]] = []
    for header, section in sections:
        matched = False
        for key in MEAL_KEYS:
            if key.lower() in header.lower():
                meals[key].append(section.strip())
                matched = True
                break
        if not matched:
            others.append((header, section.strip()))

    for key in MEAL_KEYS:
        blocks = meals.get(key)
        if blocks:
            parts.append(f"### {key}\n")
            for b in blocks:
                parts.append(b.rstrip() + "\n\n")

    for header, section in others:
        parts.append(f"### {header}\n")
        parts.append(section.rstrip() + "\n\n")

    return "\n".join(parts)


def write_weekly_files(items: List[Tuple[str, Path, List[Tuple[str, str]]]], out_dir: Path) -> None:
    """Write one markdown file per calendar week containing that week's days.

    Filenames follow: CW_<week>_<start_iso>_<Month>_to_<end_iso>_<Month>.md
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for date_str, path, sections in items:
        d = parse_date_value(date_str)
        if not d:
            # skip entries without a parseable date
            continue
        year, week, _ = d.isocalendar()
        groups[(year, week)].append((d, date_str, path, sections))

    out_dir.mkdir(parents=True, exist_ok=True)
    for (year, week), rows in sorted(groups.items()):
        # sort rows ascending by date
        rows_sorted = sorted(rows, key=lambda r: r[0])
        start = rows_sorted[0][0]
        end = rows_sorted[-1][0]
        start_iso = start.isoformat()
        end_iso = end.isoformat()
        # Filename should not include month names; keep ISO dates only
        filename = f"CW_{week}_{start_iso}_to_{end_iso}.md"
        path_out = out_dir / filename
        # build content: week header + days in ascending order
        content_parts = [f"# Calendar week {week} ({start_iso} — {end_iso})\n"]
        for d_obj, date_str, p, sections in rows_sorted:
            content_parts.append(build_day_md(date_str, sections))

        path_out.write_text("\n".join(content_parts), encoding='utf-8')
        print(f"Wrote weekly file: {path_out}")


def run_pandoc(md_in: Path, pdf_out: Path) -> bool:
    # Prefer to ask pandoc to create the PDF directly while avoiding LaTeX by
    # specifying a non-LaTeX pdf-engine. The most portable option here is
    # `wkhtmltopdf` which produces PDFs from HTML; pandoc can call it via
    # `--pdf-engine=wkhtmltopdf`. If that's not available, fall back to
    # generating HTML then calling wkhtmltopdf explicitly.
    pandoc = shutil.which("pandoc")
    wkhtmltopdf = shutil.which("wkhtmltopdf")
    if not pandoc:
        print("pandoc not found; skipping PDF generation.")
        return False

    # If wkhtmltopdf is present, ask pandoc to use it as the pdf engine so
    # pandoc won't require a LaTeX engine.
    if wkhtmltopdf:
        try:
            subprocess.check_call([pandoc, str(md_in), "-s", "--pdf-engine=wkhtmltopdf", "-o", str(pdf_out)])
            return True
        except subprocess.CalledProcessError as e:
            print("pandoc (with wkhtmltopdf engine) failed:", e)
            # fall through to try html -> wkhtmltopdf manual pipeline

    # If we reach here, either wkhtmltopdf wasn't available to pandoc or the
    # direct route failed. Try producing HTML first then converting to PDF if
    # wkhtmltopdf is available.
    if wkhtmltopdf:
        html_tmp = md_in.with_suffix(".html")
        try:
            subprocess.check_call([pandoc, str(md_in), "-s", "-o", str(html_tmp)])
            subprocess.check_call([wkhtmltopdf, str(html_tmp), str(pdf_out)])
            html_tmp.unlink(missing_ok=True)
            return True
        except subprocess.CalledProcessError as e:
            print("Error while running pandoc/wkhtmltopdf pipeline:", e)
            try:
                html_tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return False

    # No suitable PDF engine available; do not attempt LaTeX-based PDF generation
    print("wkhtmltopdf not found; skipping PDF generation to avoid LaTeX dependency.")
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="protocol", help="Root folder to scan for protocol markdown files")
    p.add_argument("--include-logs", action="store_true", help="Also include files from logs/daily/")
    p.add_argument("--out-md", default="outputs/meals_combined.md")
    p.add_argument("--out-pdf", default="outputs/meals_combined.pdf")
    args = p.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"Root folder {root} does not exist. Exiting.")
        return 2

    md_out = Path(args.out_md)
    pdf_out = Path(args.out_pdf)
    os.makedirs(md_out.parent, exist_ok=True)

    files = find_markdown_files(root, include_logs=args.include_logs)
    items = []
    for f in files:
        date, sections = load_file(f)
        items.append((date, f, sections))

    # sort by parsed date (newest first). If parsing fails, fall back to filename.
    items_sorted = sorted(
        items,
        key=lambda t: (
            parse_date_value(t[0]) or datetime.min.date(),
            str(t[1])
        ),
        reverse=True,
    )

    combined = build_combined_md(items_sorted)
    md_out.write_text(combined, encoding="utf-8")
    print(f"Wrote combined markdown to {md_out}")

    # also write weekly files (one markdown per calendar week)
    try:
        weekly_dir = Path(md_out.parent) / 'weekly_meal_protocol'
        write_weekly_files(items_sorted, weekly_dir)
    except Exception as e:
        print('Could not write weekly files:', e)

    ok = run_pandoc(md_out, pdf_out)
    if ok:
        print(f"Wrote PDF to {pdf_out}")
        return 0
    else:
        print("PDF not created. To create it locally or in CI, install pandoc and wkhtmltopdf.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
