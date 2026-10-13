# English Wordlist Builder

Create Chinese-English word lists and spelling worksheets for Chinese-speaking learners. The same Python renderers produce HTML and, optionally, PDF through WeasyPrint. English headwords use the local Andika font.

## Requirements

- Python 3
- WeasyPrint for PDF output
- Streamlit only when using the web interface

## Generate files

Run these commands from this folder:

```bash
python3 build_wordlist.py data/pre-a1-animals_and_food.json --pdf
python3 build_letter_word_shuffle.py data/pre-a1-animals_and_food.json --seed 42 --pdf
python3 build_letter_word_fill_half.py data/pre-a1-animals_and_food.json --seed 58310472 --pdf
```

Files are written to `output/` by default. Streamlit includes the displayed seed in every output filename. Filename prefixes are:

- `单词表-`
- `字母变单词-全部填写-`
- `字母变单词-填写一半-` (includes its random seed)

Use `--theme THEME_ID` to select topics, `--name SLUG` to set the output name, and `--output-dir DIR` to choose another destination. Exercise scripts accept `--shuffle-words`; answer keys are on by default and can be disabled with `--no-answer-key`. The fill-half script accepts `--short-min`, `--short-max`, `--long-min`, and `--long-max` to change the given-letter ratios.

## Streamlit

```bash
streamlit run streamlit_app.py
```

The app has tabs for generating files, viewing statistics for the selected JSON files, previewing JSON, managing/merging JSON, and adding validated JSON. The generation tab shows projected filenames before writing outputs; the statistics tab stays synchronized with its selected files.

## Data and settings

JSON structure and validation rules are described in [SKILL_JSON_SCHEMA.md](SKILL_JSON_SCHEMA.md). Generation conventions are in [SKILL-生成单词列表.md](SKILL-生成单词列表.md) and [SKILL-单词练习-字母变成单词.md](SKILL-单词练习-字母变成单词.md). Each topic includes a required level field. Adjust output directory, font, PDF command, and default fill ratios in `config.yml`.
