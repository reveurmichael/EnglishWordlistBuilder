# 字母变成单词练习规则

本项目只在 `wordlist` 文件夹内工作。练习只从 `data/*.json` 读取；生成前先完整校验数据，不从旧 HTML/PDF 反向解析。

## 入口、前缀与可复现性

完整乱序：

```bash
python3 build_letter_word_shuffle.py data/pre-a1-animals_and_food.json --seed 42 --pdf
```

输出前缀为 `字母变单词-全部填写-`。每张卡按“中文释义 + POS、IPA、作答槽、字母提示”排列；作答槽留空，提示区域给出答案所含的全部字母（含重复字母），顺序由 seed 控制。

填写一半：

```bash
python3 build_letter_word_fill_half.py data/pre-a1-animals_and_food.json --seed 58310472 --pdf
```

输出前缀为 `字母变单词-填写一半-`，文件名必须包含 seed，例如 `字母变单词-填写一半-pre-a1-animals_and_food-58310472.html`。seed 控制每张卡提供哪些字母及缺失字母提示的顺序；相同 seed、数据和比例必须生成相同练习。

两个入口支持多个 JSON、`--theme THEME_ID`、`--output-dir DIR`、`--name SLUG` 和可选的 `--shuffle-words`。默认不打乱卡片顺序；开启后只在每个主题内部打乱，不改变主题先后，答案表必须使用同一顺序。Streamlit 对三种输出都把显示的同一个 seed 加入文件名。默认输出目录为 `output/`。

填写一半比例可用 `--short-min`、`--short-max`、`--long-min`、`--long-max` 覆盖配置：

```bash
python3 build_letter_word_fill_half.py data/pre-a1-animals_and_food.json --short-min 0.4 --short-max 0.6 --long-min 0.6 --long-max 0.9 --pdf
```

## 内容规则

- 每张卡按“中文释义和词性同一行 → IPA → 拼写任务 → 可选字母提示”排序。POS 是小号斜体文字，格式如 `n.`、`v.`、`adj.`，不得做成徽章。
- 字母位置必须使用固定宽度槽，不用下划线字符串。已给字母显示在槽中；缺失字母留空并显示清晰的下划线。
- 多词答案在词间使用明显加宽的空隙，空隙至少为普通字母间隔的两倍；字母行不换行。长词可动态适配卡片宽度，但不能把一个词拆成多行。
- 所有字母（包括重复字母）都要有对应位置。空格和标点不算填写字母，不显示为待填写槽。
- 填写一半短词默认给出约三分之一至一半字母；6 个及以上字母的长词默认给出 60%–90%。
- 除单字母词外，任何单词至少留两个字母待填；长词比例很高时也遵守此下限。单字母词可全部给出。
- 填写一半提示仅包含缺失字母，并保留重复次数；提示不得出现已给出的字母实例。
- 提示字母和已展示字母必须保留 JSON 中的英文大小写；不得自动统一转为小写。
- 每个主题的练习卡片后紧跟按该主题分组的 `答案 · Answer key`，默认生成；CLI 可用 `--no-answer-key` 关闭，Streamlit 提供同样选项。标题和主题名放在同一紧凑行，答案文字使用小字号。答案必须对应实际练习顺序和采用的主拼写。
- 斜线或括号表示的词形由 `answer_word()` 取主拼写；对于如 `mouse / mice` 这类不规则变化，若要同时考查两种形式，应在数据中拆成独立卡片，避免单一答案与多个 IPA 不匹配。

## 卡片与分页

- 英文字母和单词优先使用本地 Andika：`fonts/Andika-Regular.ttf`、`fonts/Andika-Bold.ttf`。
- 练习卡保持两列自然块流：`.grid` 为 `display: block`，每张 `.card` 为 `inline-block`。避免 CSS Grid/Flex 作为整行卡片容器，因为 WeasyPrint 可能把整行作为分页单位。
- 每张卡必须有 `break-inside: avoid` 和 `page-break-inside: avoid`；用紧凑卡片高度节约纸张，不以整页空白换取防拆分。
- 不使用固定页高、手动换页符或 JavaScript 预分页。每个主题保持连续，不按固定卡片数预拆页面。
- 每个练习 HTML 的主标题和说明只在文件开头出现一次，不在每个主题重复。WeasyPrint running element 在主题跨页时把当前主题的短标题显示在 PDF 页顶。
- 每张 card 都设置本主题的 CSS named string 标记；PDF 页眉使用 named string 的 `first` 值，必须显示本页最先出现的 card 对应主题标题，使用小号蓝色字体；后一张卡或下一页主题不得覆盖本页页眉。
- 打印单位优先用 `pt`、`mm`。打印样式提高 POS、IPA、边框和空格线的对比度。

## 数据校验

JSON schema 见 `SKILL_JSON_SCHEMA.md`。CLI 和 Streamlit 必须使用 `common.py` 的共享校验逻辑。主题键与 `id` 一致，必填字段非空且类型正确，卡片 ID 在所选数据内唯一；验证失败时禁止写 HTML、PDF 或更改 JSON。
