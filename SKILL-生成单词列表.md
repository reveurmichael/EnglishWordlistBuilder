# 单词表生成规则

本项目只在 `wordlist` 文件夹内工作。`data/*.json` 是唯一词汇来源；Python 读取并校验 JSON，生成 HTML，需要时调用 WeasyPrint 生成 PDF。

## 入口与命名

普通词表：

```bash
python3 build_wordlist.py data/pre-a1-animals_and_food.json --pdf
```

输出为 `单词表-<slug>.html` 和同名 PDF。可同时传多个 JSON，或用 `--theme THEME_ID` 选择主题；`--output-dir DIR` 和 `--name SLUG` 可覆盖输出位置和名称。默认输出目录是 `output/`。

完整乱序练习使用 `build_letter_word_shuffle.py`，前缀必须是 `字母变单词-全部填写-`。填写一半练习使用 `build_letter_word_fill_half.py`，前缀必须是 `字母变单词-填写一半-`，文件名含 seed。两个练习入口都支持 `--shuffle-words`，默认保留 JSON 中的词序；填写比例由 `config.yml` 或本次运行参数控制。

Streamlit 为每次生成显示一个 seed，并将同一个 seed 加入所选每种输出的文件名：`<level>_<group>_<seed>`。单级别多文件合并时 group 使用 `merged`，不同级别混选时 level 使用 `mixed`。级别内部保留连字符（如 `pre-a1`），级别后的字段用下划线分隔。

## 数据校验

- 所有生成、预览、合并和新增 JSON 的入口都必须先验证数据，再继续处理。
- 顶层必须是非空 JSON object；主题键必须与主题 `id` 相同，主题和卡片必填字段、字符串类型、非空值都要检查。
- 每个文件内主题 ID 和卡片 ID 必须唯一；加载多个 JSON 时卡片 ID 也必须跨文件唯一。
- 合并前检查主题 ID 和卡片 ID 冲突；冲突时停止，不写入文件。
- 新增 JSON 只在完整校验通过且目标文件名尚不存在时写入 `data/`。
- 不提供 JSON 重命名功能。合并 JSON 的目标是保留 A、将 B 合并进 A 并移除 B。

## 词表卡片

- 卡片内容顺序为：Andika 英文单词、IPA、中文释义与词性同一行、英文例句和中文翻译。
- 词性紧跟中文释义，显示为小号斜体缩写并带句点（例如 `n.`、`v.`、`adj.`）；不使用徽章或背景色。
- 英文单词使用 `fonts/Andika-Regular.ttf` 和 `fonts/Andika-Bold.ttf` 本地字体，字号醒目；IPA 使用易读的小号字体。
- 英文例句应短、自然，适合中文母语的初学者和低龄学习者。

## HTML 与 PDF 布局

- 每个主题在 HTML 中保持一个连续 section，不按固定卡片数或主题预先拆页。
- 卡片使用自然块流两列布局：`.grid { display: block; font-size: 0; }`，`.card` 为 `inline-block`。不改成 CSS Grid/Flex 卡片行，避免 WeasyPrint 将整行作为分页单位。
- 每张卡同时设置 `break-inside: avoid` 和 `page-break-inside: avoid`，避免单卡跨页；不使用固定页高、硬编码分页符或 JavaScript 预分页。
- 用 WeasyPrint running element 将当前主题英文标题重复显示在该主题所跨 PDF 页面的顶部。主题仍在正文中显示一次。
- 每张 card 都设置本主题的 CSS named string 标记，并使用 `string(topicHeader, first)`；每个 PDF 页顶部显示本页最先出现的 card 对应主题标题，不使用后一张卡或下一页主题覆盖页眉。页眉使用小号蓝色字体。
- 标题区保持简洁，避免在运行页眉、主标题和副标题重复同一长文本。
- 练习总标题和说明在每个 HTML 文件开头只出现一次。开启答案时，每个主题的答案紧随该主题练习卡片之后，使用小号紧凑标题；答案默认开启，CLI 可通过 `--no-answer-key` 关闭。
- CSS 优先用 `pt`、`mm` 等打印单位；打印时 POS、IPA、卡片边框和填空线需保持足够对比度。

## 配置与 Streamlit

```yaml
output_dir: output
font_family: Andika
pdf_command: weasyprint
short_min: 0.333333
short_max: 0.5
long_min: 0.6
long_max: 0.9
```

`common.py` 是共享数据加载、校验、渲染、统计和 PDF 转换实现。Streamlit 使用独立 tabs：生成 HTML/PDF、Stats · 数据统计、预览 JSON、管理 JSON、新增 JSON。统计页与生成页共享当前选中的 JSON 文件，显示卡片/词数、唯一词、词频、词性、长度以及填写一半的已给/待填字母统计。生成区以三个默认勾选的复选框选择词表、完整乱序和填写一半，可在一次操作中生成多个类型，并在生成前预览目标文件名；seed 应显示给用户并用于对应输出。答案页默认开启，可手动关闭。JSON 重命名界面不提供。
