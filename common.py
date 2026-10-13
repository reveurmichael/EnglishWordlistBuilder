"""Shared data loading, HTML rendering, and PDF conversion for the wordlist app."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_CONFIG = {
    "output_dir": "output",
    "font_family": "Andika",
    "pdf_command": "weasyprint",
    "short_min": 0.333333,
    "short_max": 0.5,
    "long_min": 0.6,
    "long_max": 0.9,
}


def load_config(path: str | Path = ROOT / "config.yml") -> dict:
    """Load the intentionally small flat YAML config without requiring PyYAML."""
    config = DEFAULT_CONFIG.copy()
    path = Path(path)
    if not path.exists():
        return config
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        value = value.strip("'\"")
        if key in {"short_min", "short_max", "long_min", "long_max"}:
            config[key] = float(value)
        else:
            config[key] = value
    return config


def save_config(config: dict, path: str | Path = ROOT / "config.yml") -> None:
    path = Path(path)
    keys = list(DEFAULT_CONFIG)
    lines = [f"{key}: {config.get(key, DEFAULT_CONFIG[key])}" for key in keys]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def data_files() -> list[Path]:
    return sorted(DATA_DIR.glob("*.json"))


def _validate_topic(topic: dict, source: Path) -> None:
    if not isinstance(topic, dict):
        raise ValueError(f"{source}: each topic must be an object")
    required_topic = {"id", "kind", "title", "level", "cards"}
    missing = required_topic - topic.keys()
    if missing:
        raise ValueError(f"{source}: topic {topic.get('id', '<unknown>')} missing {sorted(missing)}")
    for field in ("id", "kind", "title"):
        if not isinstance(topic[field], str) or not topic[field].strip():
            raise ValueError(f"{source}: topic {topic['id']} needs a non-empty string for {field}")
    for field in ("title_cn", "css_class", "level"):
        if field in topic and not isinstance(topic[field], str):
            raise ValueError(f"{source}: topic {topic['id']} field {field} must be a string")
    if not isinstance(topic["cards"], list):
        raise ValueError(f"{source}: topic {topic['id']} cards must be a list")
    required_card = {"id", "word", "pos", "ipa", "meaning_cn", "example_en", "example_cn"}
    for card in topic["cards"]:
        if not isinstance(card, dict):
            raise ValueError(f"{source}: every card in topic {topic['id']} must be an object")
        missing = required_card - card.keys()
        if missing:
            raise ValueError(f"{source}: card {card.get('id', '<unknown>')} missing {sorted(missing)}")
        for field in required_card:
            if not isinstance(card[field], str) or not card[field].strip():
                raise ValueError(f"{source}: card {card['id']} needs a non-empty string for {field}")


def load_json_file(path: str | Path) -> dict:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top level must be an object of topics")
    return validate_payload(payload, path)


def validate_payload(payload: object, source: str | Path = "JSON") -> dict:
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"{source}: top level must be a non-empty object of topics")
    topic_ids: set[str] = set()
    card_ids: set[str] = set()
    for key, topic in payload.items():
        _validate_topic(topic, Path(source))
        if topic["id"] != key:
            raise ValueError(f"{source}: topic key {key!r} must match topic id {topic['id']!r}")
        if topic["id"] in topic_ids:
            raise ValueError(f"{source}: duplicate topic id {topic['id']!r}")
        topic_ids.add(topic["id"])
        for card in topic["cards"]:
            if card["id"] in card_ids:
                raise ValueError(f"{source}: duplicate card id {card['id']!r}")
            card_ids.add(card["id"])
    return payload


def load_topics(paths: list[str | Path], selected_topics: set[str] | None = None) -> list[dict]:
    topics: list[dict] = []
    seen_ids: set[str] = set()
    seen_topic_ids: set[str] = set()
    for raw_path in paths:
        source = Path(raw_path)
        payload = load_json_file(source)
        for topic in payload.values():
            if selected_topics and topic["id"] not in selected_topics:
                continue
            if topic["id"] in seen_topic_ids:
                raise ValueError(f"Duplicate topic id across selected data: {topic['id']}")
            seen_topic_ids.add(topic["id"])
            copied = dict(topic)
            copied["source_file"] = source.name
            copied.setdefault("title_cn", "")
            copied.setdefault("css_class", copied["id"])
            cards = []
            for card in topic["cards"]:
                if card["id"] in seen_ids:
                    raise ValueError(f"Duplicate card id across selected data: {card['id']}")
                seen_ids.add(card["id"])
                cards.append(dict(card))
            copied["cards"] = cards
            topics.append(copied)
    if not topics:
        raise ValueError("No topics selected")
    return topics


def slug_for_paths(
    paths: list[str | Path],
    seed: str | int | None = None,
    custom_name: str | None = None,
) -> str:
    paths = [Path(path) for path in paths]
    levels: set[str] = set()
    for path in paths:
        payload = load_json_file(path)
        levels.update({
            topic["level"].strip().lower()
            for topic in payload.values()
            if isinstance(topic.get("level"), str) and topic["level"].strip()
        })
    level = next(iter(levels)) if len(levels) == 1 else ("mixed" if levels else "english")
    if custom_name and custom_name.strip():
        group = custom_name
    elif len(paths) > 1:
        group = "merged"
    elif paths:
        group = paths[0].stem
        if group.startswith(level + "-"):
            group = group[len(level) + 1 :]
    else:
        group = "wordlist"
    group = re.sub(r"[^A-Za-z0-9]+", "_", group).strip("_").lower() or "wordlist"
    slug = f"{level}_{group}"
    if seed is not None:
        seed_slug = re.sub(r"[^A-Za-z0-9]+", "_", str(seed)).strip("_")
        if not seed_slug:
            raise ValueError("Seed must contain at least one letter or digit")
        slug += f"_{seed_slug}"
    return slug


def resolve_font(config: dict) -> tuple[str, str]:
    family = str(config.get("font_family", "Andika"))
    if family == "Andika":
        regular = (ROOT / "fonts" / "Andika-Regular.ttf").as_uri()
        bold = (ROOT / "fonts" / "Andika-Bold.ttf").as_uri()
        return family, f'@font-face {{ font-family: "Andika"; src: url("{regular}") format("truetype"); font-weight: 400; }}\n@font-face {{ font-family: "Andika"; src: url("{bold}") format("truetype"); font-weight: 700; }}'
    safe = re.sub(r"[^A-Za-z0-9 ,'-]", "", family) or "Arial"
    return safe, ""


def css(config: dict, exercise: bool = False) -> str:
    family, font_face = resolve_font(config)
    if exercise:
        card_body = ".card-head { display: flex; align-items: baseline; gap: 2mm; } .meaning { font-size: 11.5pt; line-height: 1.15; font-weight: 700; } .ipa { font-family: Arial, sans-serif; font-size: 9.5pt; color: #4a5568; margin-top: 1mm; } .blanks { display: flex; flex-wrap: nowrap; align-items: flex-end; gap: 1.2mm; margin-top: 2mm; white-space: nowrap; overflow: hidden; } .slot { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 4.5mm; width: 4.5mm; height: 6.5mm; font: 700 13pt/1 \"Andika\", cursive; color: #1a202c; } .slot.blank { border-bottom: .7pt solid #4a5568; color: #b6c2cf; } .word-gap { flex: 0 0 6mm; width: 6mm; } .hint { font-family: \"Andika\", cursive; font-size: 10pt; color: #2b6cb0; margin-top: 1.5mm; } .hint-label { font-family: Arial, sans-serif; color: #718096; font-size: 8.5pt; margin-right: 1mm; }"
    else:
        card_body = ".word { font-family: \"Andika\", cursive; font-size: 15pt; line-height: 1.02; font-weight: 700; color: #1a202c; overflow-wrap: anywhere; } .ipa { font-family: Arial, sans-serif; font-size: 9.5pt; color: #4a5568; margin-top: .8mm; } .card-head { display: flex; align-items: baseline; gap: 2mm; margin-top: .8mm; } .meaning { font-size: 10.5pt; line-height: 1.2; font-weight: 600; } .example { font-size: 9.5pt; line-height: 1.18; color: #4a5568; margin-top: 1mm; } .en { color: #2b6cb0; font-style: italic; } .cn { color: #718096; margin-left: 1.5mm; }"
    return f'''{font_face}
@page {{ size: A4; margin: 18mm 10mm 9mm; @top-center {{ content: string(topicHeader, first); color: #2b6cb0; font: 600 8pt/1 Arial, sans-serif; }} }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; font-family: "PingFang SC", "Microsoft YaHei", Arial, sans-serif; color: #1f2937; }}
.page {{ margin-bottom: 4mm; }}
.running-title {{ display: none; }}
.card-topic-marker {{ string-set: topicHeader content(text); position: absolute; width: 0; height: 0; overflow: hidden; font-size: 0; }}
.title {{ text-align: center; font-size: 17pt; font-weight: 800; color: #2b6cb0; margin: 0 0 1.5mm; }}
.subtitle {{ text-align: center; font-size: 9.5pt; color: #718096; margin: 0 0 2.5mm; }}
.section-title {{ display: flex; align-items: baseline; gap: 3mm; border-bottom: 1.5pt solid #bee3f8; margin: 0 0 2mm; padding-bottom: 1mm; break-after: avoid; }}
.section-title strong {{ font-size: 14pt; color: #2c5282; }} .section-title span {{ font-size: 10pt; color: #718096; }}
.grid {{ display: block; font-size: 0; }}
.card {{ display: inline-block; vertical-align: top; width: calc(50% - 2mm); margin: 0 4mm 1.7mm 0; font-size: 10pt; border: .6pt solid #cbd5e0; border-radius: 2mm; padding: 2.2mm 3mm 2mm; min-height: 24mm; background: #fff; break-inside: avoid; page-break-inside: avoid; }}
.card:nth-child(even) {{ margin-right: 0; }}
.pos {{ font: italic 600 9pt/1 Arial, sans-serif; color: #4a5568; white-space: nowrap; }}
.food .section-title {{ border-color: #c6f6d5; }} .food .section-title strong {{ color: #276749; }}
.leisure .section-title {{ border-color: #c6f6d5; }} .leisure .section-title strong {{ color: #276749; }}
.toys .section-title {{ border-color: #feebc8; }} .toys .section-title strong {{ color: #9c4221; }}
.transport .section-title {{ border-color: #e9d8fd; }} .transport .section-title strong {{ color: #6b46c1; }}
.key-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1mm 4mm; font: 600 10pt/1.35 "Andika", cursive; color: #2d3748; }}
.key-grid span {{ break-inside: avoid; }}
.answer-block {{ margin: 1mm 0 3mm; break-inside: avoid; page-break-inside: avoid; }}
.answer-heading {{ display: flex; align-items: baseline; gap: 2mm; margin-bottom: .5mm; color: #4a5568; font: 600 8pt/1.2 Arial, sans-serif; }}
.answer-heading strong {{ font-size: 8.5pt; color: #2d3748; }}
.answer-block .key-grid {{ display: flex; flex-wrap: wrap; column-gap: 4mm; font: 600 8.5pt/1.3 "Andika", cursive; }}
.answer-block .key-grid span {{ white-space: nowrap; }}
.document-heading {{ margin: 0 0 3mm; }}
{card_body}
@media print {{ .pos {{ color: #000; }} .ipa {{ color: #4a5568; }} .card {{ border-color: #a0aec0; }} .slot.blank {{ border-bottom-color: #2d3748; }} }}
'''


def base_document(title: str, stylesheet: str, body: str) -> str:
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>{stylesheet}</style></head><body>{body}</body></html>'


def theme_class(topic: dict) -> str:
    return re.sub(r"[^a-z0-9_-]", "", topic.get("css_class", "theme").lower()) or "theme"


def display_pos(pos: str) -> str:
    return pos.strip().rstrip(".") + "."


def topic_marker(title: str) -> str:
    # Callers pass the already escaped display title so the named string renders text, not entities.
    return f'<span class="card-topic-marker">{title}</span>'


def render_wordlist(topics: list[dict], config: dict) -> str:
    pieces = []
    for topic in topics:
        cls = theme_class(topic)
        title = html.escape(topic["title"])
        pieces.append(f'<section class="page {cls}"><div class="running-title">{title}</div><h1 class="title">英语单词表</h1><p class="subtitle">{title}（{html.escape(topic["title_cn"])}）</p><div class="section-title"><strong>{title}</strong><span>{html.escape(topic["title_cn"])}</span></div><div class="grid">')
        for card in topic["cards"]:
            pieces.append(f'<div class="card">{topic_marker(title)}<div class="word">{html.escape(card["word"])}</div><div class="ipa">{html.escape(card["ipa"])}</div><div class="card-head"><span class="meaning">{html.escape(card["meaning_cn"])}</span><span class="pos">{html.escape(display_pos(card["pos"]))}</span></div><div class="example"><span class="en">{html.escape(card["example_en"])}</span><span class="cn">{html.escape(card["example_cn"])}</span></div></div>')
        pieces.append("</div></section>")
    return base_document("英语单词表", css(config), "".join(pieces))


def answer_word(word: str) -> str:
    return re.split(r"\s*/\s*|\s*\(", word, maxsplit=1)[0].strip()


def answer_ipa(card: dict) -> str:
    """Use the first pronunciation when the displayed word has variant forms."""
    return re.split(r"\s+(?=/)", card["ipa"].strip(), maxsplit=1)[0]


def shuffle_letters(word: str, rng: Random) -> list[str]:
    letters = [c for c in word if c.isalpha()]
    if len(letters) > 1:
        original = letters[:]
        rng.shuffle(letters)
        if letters == original:
            letters = letters[1:] + letters[:1]
    return letters


def blank_slots(word: str) -> str:
    parts = re.split(r"(\s+)", word)
    rendered = []
    for part in parts:
        if part.isspace():
            rendered.append('<span class="word-gap"></span>')
        else:
            rendered.extend('<span class="slot blank"></span>' if char.isalpha() else html.escape(char) for char in part)
    return ''.join(rendered)


def fill_slots(pattern: list[tuple[str, bool]]) -> str:
    rendered = []
    for char, given in pattern:
        if char.isspace():
            rendered.append('<span class="word-gap"></span>')
        elif char.isalpha():
            state = "given" if given else "blank"
            rendered.append(f'<span class="slot {state}">{html.escape(char) if given else ""}</span>')
        else:
            rendered.append(html.escape(char))
    return ''.join(rendered)


def render_shuffle(
    topics: list[dict],
    config: dict,
    seed: int | str = 0,
    shuffle_words: bool = False,
    answer_key: bool = True,
) -> str:
    rng = Random(seed)
    pieces = []
    pieces.append('<header class="document-heading"><h1 class="title">字母变单词 · 全部填写</h1><p class="subtitle">看中文和音标，写出英文单词</p></header>')
    for topic in topics:
        title = html.escape(topic["title"])
        cls = theme_class(topic)
        pieces.append(f'<section class="page {cls}"><div class="running-title">{title}</div><div class="section-title"><strong>{title}</strong><span>{html.escape(topic["title_cn"])}</span></div><div class="grid">')
        cards = list(topic["cards"])
        if shuffle_words:
            Random(f"{seed}:{topic['id']}:order").shuffle(cards)
        for card in cards:
            word = answer_word(card["word"])
            letters = shuffle_letters(word, rng)
            slots = blank_slots(word)
            hint = " ".join(letters)
            pieces.append(f'<div class="card">{topic_marker(title)}<div class="card-head"><span class="meaning">{html.escape(card["meaning_cn"])}</span><span class="pos">{html.escape(display_pos(card["pos"]))}</span></div><div class="ipa">{html.escape(answer_ipa(card))}</div><div class="blanks">{slots}</div><div class="hint"><span class="hint-label">字母提示：</span>{html.escape(hint)}</div></div>')
        pieces.append("</div></section>")
        if answer_key:
            pieces.append(answer_section(topic, cards))
    return base_document("字母变单词-全部填写", css(config, exercise=True), "".join(pieces))


def fill_pattern(word: str, rng: Random, config: dict) -> tuple[list[tuple[str, bool]], list[str]]:
    letters = [c for c in word if c.isalpha()]
    if len(letters) <= 1:
        given = set()
    else:
        lo, hi = ((config["long_min"], config["long_max"]) if len(letters) >= 6 else (config["short_min"], config["short_max"]))
        count = min(len(letters) - 2, max(0, round(len(letters) * rng.uniform(lo, hi))))
        positions = list(range(len(letters)))
        rng.shuffle(positions)
        given = set(positions[:count])
    pattern, missing, index = [], [], 0
    for char in word:
        if char.isalpha():
            if index in given:
                pattern.append((char, True))
            else:
                pattern.append((char, False))
                missing.append(char)
            index += 1
        elif char == " ":
            pattern.append((" ", True))
        else:
            pattern.append((char, True))
    rng.shuffle(missing)
    return pattern, missing


def word_tokens(word: str) -> list[str]:
    """Return lowercase English word tokens while preserving source text elsewhere."""
    return re.findall(r"[A-Za-z]+", answer_word(word).lower())


def collect_statistics(topics: list[dict], config: dict, seed: str | int = "0") -> dict:
    cards = [card for topic in topics for card in topic["cards"]]
    tokens = [token for card in cards for token in word_tokens(card["word"])]
    frequency = Counter(tokens)
    pos_counts = Counter(card["pos"].strip().rstrip(".").lower() for card in cards)
    total_letters = sum(sum(char.isalpha() for char in answer_word(card["word"])) for card in cards)
    given_letters = 0
    blank_letters = 0
    for index, card in enumerate(cards):
        pattern, _ = fill_pattern(answer_word(card["word"]), Random(f"{seed}:{card['id']}:{index}"), config)
        given_letters += sum(given and char.isalpha() for char, given in pattern)
        blank_letters += sum((not given) and char.isalpha() for char, given in pattern)
    card_count = len(cards)
    token_count = len(tokens)
    return {
        "card_count": card_count,
        "token_count": token_count,
        "unique_token_count": len(frequency),
        "top_words": frequency.most_common(10),
        "pos_counts": pos_counts,
        "total_letters": total_letters,
        "average_tokens_per_card": token_count / card_count if card_count else 0,
        "average_unique_tokens_per_card": len(frequency) / card_count if card_count else 0,
        "average_letters_per_card": total_letters / card_count if card_count else 0,
        "average_letters_per_token": total_letters / token_count if token_count else 0,
        "average_given_letters_per_token": given_letters / token_count if token_count else 0,
        "average_blank_letters_per_token": blank_letters / token_count if token_count else 0,
        "given_letters": given_letters,
        "blank_letters": blank_letters,
        "given_ratio": given_letters / total_letters if total_letters else 0,
        "blank_ratio": blank_letters / total_letters if total_letters else 0,
        "average_given_letters_per_card": given_letters / card_count if card_count else 0,
        "average_blank_letters_per_card": blank_letters / card_count if card_count else 0,
    }


def answer_section(topic: dict, cards: list[dict]) -> str:
    title = html.escape(topic["title"])
    answers = ''.join(f'<span>{html.escape(answer_word(card["word"]))}</span>' for card in cards)
    return f'<div class="answer-block">{topic_marker(title)}<div class="answer-heading"><span>答案 · Answer key</span><strong>{title}</strong></div><div class="key-grid">{answers}</div></div>'


def render_fill_half(
    topics: list[dict],
    config: dict,
    seed: str,
    shuffle_words: bool = False,
    answer_key: bool = True,
) -> str:
    pieces = []
    pieces.append('<header class="document-heading"><h1 class="title">字母变单词 · 填写一半</h1><p class="subtitle">看中文和音标，补全单词</p></header>')
    for topic in topics:
        title = html.escape(topic["title"])
        cls = theme_class(topic)
        pieces.append(f'<section class="page {cls}"><div class="running-title">{title}</div><div class="section-title"><strong>{title}</strong><span>{html.escape(topic["title_cn"])}</span></div><div class="grid">')
        cards = list(topic["cards"])
        if shuffle_words:
            Random(f"{seed}:{topic['id']}:order").shuffle(cards)
        for index, card in enumerate(cards):
            word = answer_word(card["word"])
            pattern, hint = fill_pattern(word, Random(f"{seed}:{card['id']}:{index}"), config)
            slots = fill_slots(pattern)
            pieces.append(f'<div class="card">{topic_marker(title)}<div class="card-head"><span class="meaning">{html.escape(card["meaning_cn"])}</span><span class="pos">{html.escape(display_pos(card["pos"]))}</span></div><div class="ipa">{html.escape(answer_ipa(card))}</div><div class="blanks">{slots}</div><div class="hint"><span class="hint-label">字母提示：</span>{html.escape(" ".join(hint))}</div></div>')
        pieces.append("</div></section>")
        if answer_key:
            pieces.append(answer_section(topic, cards))
    return base_document("字母变单词-填写一半", css(config, exercise=True), "".join(pieces))


def write_pdf(html_path: str | Path, pdf_path: str | Path, config: dict) -> Path:
    command = shutil.which(str(config.get("pdf_command", "weasyprint")))
    if not command:
        raise RuntimeError("PDF command not found. Install WeasyPrint or set pdf_command in config.yml.")
    html_path, pdf_path = Path(html_path), Path(pdf_path)
    subprocess.run([command, str(html_path), str(pdf_path)], check=True)
    return pdf_path
