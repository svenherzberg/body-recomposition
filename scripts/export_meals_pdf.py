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
MEAL_RE = re.compile(r"^\s*\*\*(?P<header>.*?(Frühstück|Mittagessen|Abendessen|Snacks).*?)\*\*\s*$", flags=re.I | re.M)


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


def extract_meal_sections(content: str) -> List[Tuple[str, str]]:
    """Return list of (header, section_text) in the order they appear."""
    matches = list(MEAL_RE.finditer(content))
    if not matches:
        return []
    sections = []
    for i, m in enumerate(matches):
        header = m.group("header").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[start:end].strip()
        # clean up leading/trailing blank lines
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
        # show a compact path: try to make it relative to the repo cwd, but fall back to the
        # raw path string if that's not possible (some paths may already be relative strings)
        try:
            display_path = path.relative_to(Path.cwd())
        except Exception:
            display_path = path
        parts.append(f"## {date} — {display_path}\n")
        if not sections:
            parts.append("_No recognized meal sections found._\n")
            parts.append("\n")
            continue
        for header, section in sections:
            parts.append(f"### {header}\n")
            # Ensure consistent spacing
            parts.append(section.rstrip() + "\n\n")
    return "\n".join(parts)


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

    # sort by ISO-like date (strings) then filename
    items_sorted = sorted(items, key=lambda t: (t[0] or "", str(t[1])))

    combined = build_combined_md(items_sorted)
    md_out.write_text(combined, encoding="utf-8")
    print(f"Wrote combined markdown to {md_out}")

    ok = run_pandoc(md_out, pdf_out)
    if ok:
        print(f"Wrote PDF to {pdf_out}")
        return 0
    else:
        print("PDF not created. To create it locally or in CI, install pandoc and wkhtmltopdf.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
