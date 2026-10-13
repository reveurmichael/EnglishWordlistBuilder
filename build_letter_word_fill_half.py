"""Build a seeded partial-letter exercise from JSON data."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path

from common import ROOT, load_config, load_topics, render_fill_half, slug_for_paths, write_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 字母变单词-填写一半 exercise.")
    parser.add_argument("data", nargs="+", type=Path)
    parser.add_argument("--theme", action="append", dest="themes")
    parser.add_argument("--seed", default=None)
    parser.add_argument("--shuffle-words", action="store_true", help="Shuffle card order within each topic")
    parser.add_argument("--no-answer-key", action="store_true", help="Omit the per-topic answer key")
    parser.add_argument("--short-min", type=float)
    parser.add_argument("--short-max", type=float)
    parser.add_argument("--long-min", type=float)
    parser.add_argument("--long-max", type=float)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    config = load_config()
    for key, value in (("short_min", args.short_min), ("short_max", args.short_max), ("long_min", args.long_min), ("long_max", args.long_max)):
        if value is not None:
            config[key] = value
    if not (0 < config["short_min"] <= config["short_max"] <= 1 and 0 < config["long_min"] <= config["long_max"] <= 1):
        parser.error("ratio values must satisfy 0 < min <= max <= 1")
    paths = [path if path.is_absolute() else ROOT / path for path in args.data]
    topics = load_topics(paths, set(args.themes or []))
    seed = str(args.seed if args.seed is not None else secrets.randbelow(900_000_000) + 100_000_000)
    output_dir = args.output_dir or Path(config.get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = args.name or slug_for_paths(paths)
    html_path = output_dir / f"字母变单词-填写一半-{slug}-{seed}.html"
    html_path.write_text(render_fill_half(topics, config, seed, args.shuffle_words, not args.no_answer_key), encoding="utf-8")
    print(html_path)
    if args.pdf:
        pdf_path = html_path.with_suffix(".pdf")
        write_pdf(html_path, pdf_path, config)
        print(pdf_path)


if __name__ == "__main__":
    main()
