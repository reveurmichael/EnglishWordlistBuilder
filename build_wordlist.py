"""Build a data-driven Chinese-English word-list HTML and optional PDF."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, load_config, load_topics, render_wordlist, slug_for_paths, write_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 单词表- HTML/PDF from JSON data.")
    parser.add_argument("data", nargs="+", type=Path, help="JSON files in data/ or explicit paths")
    parser.add_argument("--theme", action="append", dest="themes", help="Theme id; repeat for multiple themes")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--name", help="Output slug without prefix or extension")
    parser.add_argument("--pdf", action="store_true", help="Also convert HTML to PDF")
    args = parser.parse_args()
    config = load_config()
    paths = [path if path.is_absolute() else ROOT / path for path in args.data]
    topics = load_topics(paths, set(args.themes or []))
    output_dir = args.output_dir or Path(config.get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = args.name or slug_for_paths(paths)
    html_path = output_dir / f"单词表-{slug}.html"
    html_path.write_text(render_wordlist(topics, config), encoding="utf-8")
    print(html_path)
    if args.pdf:
        pdf_path = html_path.with_suffix(".pdf")
        write_pdf(html_path, pdf_path, config)
        print(pdf_path)


if __name__ == "__main__":
    main()
