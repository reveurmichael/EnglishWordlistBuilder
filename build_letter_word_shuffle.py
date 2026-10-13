"""Build a complete shuffled-letter exercise from JSON data."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, load_config, load_topics, render_shuffle, slug_for_paths, write_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 字母变单词-全部填写- shuffled exercise.")
    parser.add_argument("data", nargs="+", type=Path)
    parser.add_argument("--theme", action="append", dest="themes")
    parser.add_argument("--seed", default="0", help="Seed for letter and optional card-order shuffling")
    parser.add_argument("--shuffle-words", action="store_true", help="Shuffle card order within each topic")
    parser.add_argument("--no-answer-key", action="store_true", help="Omit the per-topic answer key")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    config = load_config()
    paths = [path if path.is_absolute() else ROOT / path for path in args.data]
    topics = load_topics(paths, set(args.themes or []))
    output_dir = args.output_dir or Path(config.get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = args.name or slug_for_paths(paths)
    html_path = output_dir / f"字母变单词-全部填写-{slug}.html"
    html_path.write_text(render_shuffle(topics, config, args.seed, args.shuffle_words, not args.no_answer_key), encoding="utf-8")
    print(html_path)
    if args.pdf:
        pdf_path = html_path.with_suffix(".pdf")
        write_pdf(html_path, pdf_path, config)
        print(pdf_path)


if __name__ == "__main__":
    main()
