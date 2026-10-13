"""Streamlit UI for validating data and building wordlist materials."""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

import streamlit as st

from common import (
    ROOT,
    collect_statistics,
    data_files,
    load_config,
    load_json_file,
    load_topics,
    render_fill_half,
    render_shuffle,
    render_wordlist,
    save_config,
    slug_for_paths,
    validate_payload,
    write_pdf,
)


def json_path(name: str) -> Path:
    return ROOT / "data" / name


def output_file(html_text: str, filename: str, make_pdf: bool, config: dict) -> tuple[Path, Path | None]:
    output_dir = Path(config.get("output_dir", "output"))
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / filename
    html_path.write_text(html_text, encoding="utf-8")
    pdf_path = html_path.with_suffix(".pdf") if make_pdf else None
    if pdf_path:
        write_pdf(html_path, pdf_path, config)
    return html_path, pdf_path


st.set_page_config(page_title="English Wordlist Builder", layout="wide")
st.title("English Wordlist Builder")
config = load_config()

with st.sidebar:
    st.header("Configuration")
    font_options = ["Andika", "Arial", "Comic Sans MS"]
    current_font = config.get("font_family", "Andika")
    config["font_family"] = st.selectbox("Card font", font_options, index=font_options.index(current_font) if current_font in font_options else 0)
    config["output_dir"] = st.text_input("Output folder", str(config.get("output_dir", "output")))
    config["short_min"] = st.number_input("Short word given-letter minimum", 0.0, 1.0, float(config["short_min"]), 0.01)
    config["short_max"] = st.number_input("Short word given-letter maximum", 0.0, 1.0, float(config["short_max"]), 0.01)
    config["long_min"] = st.number_input("Long word given-letter minimum", 0.0, 1.0, float(config["long_min"]), 0.01)
    config["long_max"] = st.number_input("Long word given-letter maximum", 0.0, 1.0, float(config["long_max"]), 0.01)
    if st.button("Save configuration"):
        if not (0 < config["short_min"] <= config["short_max"] <= 1 and 0 < config["long_min"] <= config["long_max"] <= 1):
            st.error("Ratio values must satisfy 0 < min <= max <= 1")
        else:
            save_config(config)
            st.success("Saved config.yml")

files = data_files()
if not files:
    st.error("No JSON files found in data/")
    st.stop()

tab_generate, tab_stats, tab_preview, tab_manage, tab_add = st.tabs(["Generate HTML / PDF", "Stats · 数据统计", "Preview JSON", "Manage JSON", "Add JSON"])

with tab_generate:
    st.header("Generate")
    selected_names = st.multiselect("Data JSON files", [p.name for p in files], default=[files[0].name])
    selected_paths = [json_path(name) for name in selected_names]
    all_topics: list[dict] = []
    if selected_paths:
        try:
            all_topics = load_topics(selected_paths)
        except Exception as exc:
            st.error(f"Data validation failed: {exc}")
    topic_ids = [topic["id"] for topic in all_topics]
    selected_topic_ids = st.multiselect("Themes (empty means all)", topic_ids)
    st.markdown("**Output types**")
    make_wordlist = st.checkbox("Word list (单词表)", value=False)
    make_shuffle = st.checkbox("All shuffled letters (字母变单词-全部填写)", value=False)
    make_fill_half = st.checkbox("Fill half (字母变单词-填写一半)", value=True)
    exercise_selected = make_shuffle or make_fill_half
    include_answer_key = st.checkbox(
        "Include answer keys (字母变单词包含答案)",
        value=True,
        disabled=not exercise_selected,
    )
    if "fill_seed" not in st.session_state:
        st.session_state["fill_seed"] = str(secrets.randbelow(900_000_000) + 100_000_000)
    if st.button("New random seed"):
        st.session_state["fill_seed"] = str(secrets.randbelow(900_000_000) + 100_000_000)
    cols = st.columns([2, 1, 2])
    seed = cols[0].text_input("Output seed", key="fill_seed")
    valid_seed = re.fullmatch(r"[A-Za-z0-9]+", seed.strip()) is not None
    shuffle_words = cols[1].checkbox("Shuffle word order (仅练习)", value=False, disabled=not exercise_selected)
    make_pdf = cols[2].checkbox("Also create PDF", value=True)
    name = st.text_input("Output name slug (optional)", "")
    projected_slug = slug_for_paths(selected_paths, seed, name) if selected_paths and valid_seed else "<level_group_seed>"
    projected_files = []
    if make_wordlist:
        projected_files.append(f"单词表-{projected_slug}")
    if make_shuffle:
        projected_files.append(f"字母变单词-全部填写-{projected_slug}")
    if make_fill_half:
        projected_files.append(f"字母变单词-填写一半-{projected_slug}")
    st.markdown("**Projected files**")
    if projected_files:
        for stem in projected_files:
            st.code(f"{config.get('output_dir', 'output')}/{stem}.html" + (f"\n{config.get('output_dir', 'output')}/{stem}.pdf" if make_pdf else ""), language=None)
    else:
        st.caption("Select at least one output type.")

    if st.button("Generate selected outputs", type="primary", disabled=not selected_paths or not (make_wordlist or make_shuffle or make_fill_half)):
        try:
            topics = load_topics(selected_paths, set(selected_topic_ids) if selected_topic_ids else None)
            if not valid_seed:
                raise ValueError("Use letters and numbers only for the seed")
            slug = slug_for_paths(selected_paths, seed, name)
            products: list[tuple[str, str]] = []
            if make_wordlist:
                products.append((f"单词表-{slug}.html", render_wordlist(topics, config)))
            if make_shuffle:
                products.append((f"字母变单词-全部填写-{slug}.html", render_shuffle(topics, config, seed, shuffle_words, include_answer_key)))
            if make_fill_half:
                products.append((f"字母变单词-填写一半-{slug}.html", render_fill_half(topics, config, seed, shuffle_words, include_answer_key)))
            for filename, content in products:
                html_path, pdf_path = output_file(content, filename, make_pdf, config)
                st.success(f"Created {html_path}")
                if pdf_path:
                    st.caption(f"PDF: {pdf_path}")
                st.download_button(f"Download {html_path.name}", html_path.read_bytes(), html_path.name, "text/html", key=f"html-{filename}")
                if pdf_path:
                    st.download_button(f"Download {pdf_path.name}", pdf_path.read_bytes(), pdf_path.name, "application/pdf", key=f"pdf-{filename}")
        except Exception as exc:
            st.exception(exc)

with tab_stats:
    st.header("Stats · 数据统计")
    st.caption("Statistics use the Data JSON files currently selected in Generate HTML / PDF.")
    if not selected_paths:
        st.info("Select at least one Data JSON file in Generate HTML / PDF.")
    elif not all_topics:
        st.error("The selected JSON data is not valid.")
    else:
        stats = collect_statistics(all_topics, config, seed)
        metric_cols = st.columns(4)
        metric_cols[0].metric("Cards · 卡片", stats["card_count"])
        metric_cols[1].metric("Word tokens · 单词总数", stats["token_count"])
        metric_cols[2].metric("Unique words · 不重复单词", stats["unique_token_count"])
        metric_cols[3].metric("Letters · 字母总数", stats["total_letters"])
        st.subheader("Word frequency · 单词频率")
        st.dataframe(
            [{"Word · 单词": word, "Count · 次数": count} for word, count in stats["top_words"]],
            hide_index=True,
            use_container_width=True,
        )
        st.subheader("Averages · 平均值")
        average_cols = st.columns(4)
        average_cols[0].metric("Words per card · 每卡词数", f'{stats["average_tokens_per_card"]:.2f}')
        average_cols[1].metric("Unique words per card · 每卡不重复词数", f'{stats["average_unique_tokens_per_card"]:.2f}')
        average_cols[2].metric("Letters per card · 每卡字母数", f'{stats["average_letters_per_card"]:.2f}')
        average_cols[3].metric("Letters per word · 每词字母数", f'{stats["average_letters_per_token"]:.2f}')
        st.subheader("Parts of speech · 词性")
        pos_total = sum(stats["pos_counts"].values()) or 1
        st.dataframe(
            [{"POS · 词性": pos, "Cards · 卡片数": count, "Share · 占比": f'{count / pos_total:.1%}'} for pos, count in sorted(stats["pos_counts"].items())],
            hide_index=True,
            use_container_width=True,
        )
        st.subheader("Fill-half estimate · 填写一半估算")
        fill_cols = st.columns(4)
        fill_cols[0].metric("Given letters · 已给字母", stats["given_letters"])
        fill_cols[1].metric("Blank letters · 待填字母", stats["blank_letters"])
        fill_cols[2].metric("Given ratio · 已给比例", f'{stats["given_ratio"]:.1%}')
        fill_cols[3].metric("Blank ratio · 待填比例", f'{stats["blank_ratio"]:.1%}')
        st.caption(
            f'每卡平均已给 {stats["average_given_letters_per_card"]:.2f} 个字母，'
            f'待填 {stats["average_blank_letters_per_card"]:.2f} 个字母；'
            f'每词平均已给 {stats["average_given_letters_per_token"]:.2f} 个，'
            f'待填 {stats["average_blank_letters_per_token"]:.2f} 个；'
            f'估算使用当前 seed 和填写比例配置。'
        )

with tab_preview:
    st.header("Preview JSON")
    manage_file = st.selectbox("JSON file", [p.name for p in files], key="preview_file")
    try:
        managed = load_json_file(json_path(manage_file))
        st.success(f"Valid JSON: {len(managed)} topics")
        st.json(managed)
    except Exception as exc:
        st.error(f"Invalid JSON: {exc}")

with tab_manage:
    st.header("Manage JSON")
    merge_a = st.selectbox("Merge source A (kept)", [p.name for p in files], key="merge_a")
    merge_b = st.selectbox("Merge source B (removed)", [p.name for p in files], key="merge_b")
    if st.button("Merge B into A"):
        try:
            if merge_a == merge_b:
                raise ValueError("Choose two different files")
            a_path, b_path = json_path(merge_a), json_path(merge_b)
            a_data = validate_payload(load_json_file(a_path), merge_a)
            b_data = validate_payload(load_json_file(b_path), merge_b)
            duplicate_topics = set(a_data) & set(b_data)
            duplicate_cards = {card["id"] for topic in a_data.values() for card in topic["cards"]} & {card["id"] for topic in b_data.values() for card in topic["cards"]}
            if duplicate_topics or duplicate_cards:
                raise ValueError(f"Duplicate topic ids: {sorted(duplicate_topics)}; duplicate card ids: {sorted(duplicate_cards)}")
            a_data.update(b_data)
            validate_payload(a_data, merge_a)
            a_path.write_text(json.dumps(a_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            b_path.unlink()
            st.success(f"Merged {merge_b} into {merge_a}; B was removed. Refresh the page.")
        except Exception as exc:
            st.error(str(exc))

with tab_add:
    st.header("Add JSON data")
    new_filename = st.text_input("New JSON filename", placeholder="pre-a1-new_topic.json")
    pasted_json = st.text_area("Paste JSON", height=360, placeholder='{"topic": {"id": "topic", "kind": "flashcard", "title": "Topic", "level": "pre-a1", "cards": []}}')
    if st.button("Validate and add JSON"):
        try:
            if not new_filename.strip().endswith(".json") or Path(new_filename).name != new_filename.strip():
                raise ValueError("Enter a plain filename ending in .json")
            target = json_path(new_filename.strip())
            if target.exists():
                raise ValueError(f"File already exists: {target.name}")
            payload = validate_payload(json.loads(pasted_json), new_filename.strip())
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            st.success(f"Validated and added {target.name}. Refresh the page to load it.")
        except Exception as exc:
            st.error(str(exc))
