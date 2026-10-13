# JSON 单词卡片数据结构 · 设计与使用指南

本文档定义本项目采用的 JSON 数据格式，适用于存储不同级别英语学习卡片（如 Pre A1、A1、人教版等）。每个文件可包含一个或多个主题。文件命名体现级别和内容范围，便于管理和扩展。

---

## 1. 文件命名规则

JSON 文件命名格式为：

```
PREFIX-GROUP-THEME1_THEME2_THEMEN.json
```

**级别前缀**（参考 CEFR 或教材体系）：

| 前缀     | 含义               | 示例                                      |
|----------|--------------------|-------------------------------------------|
| `pre-a1` | Pre A1 / 初级      | `pre-a1-animals_and_food.json`            |
| `a1`     | A1 / 基础          | `a1-stuff_blabla.json`                    |
| `renjiao7` | 人教版七年级       | `renjiao7-unit_1.json`                    |

**主题组描述**：简短概括文件包含的主题，用下划线分隔。例如 `animals_and_food`、`home_body_clothes_colours`、`school_sports_toys_transport`。

**优点**：
- 一目了然知道文件所属级别和内容范围。
- `build_wordlist.py`、`build_letter_word_shuffle.py` 和 `build_letter_word_fill_half.py` 直接读取 JSON，不依赖旧 HTML 或主题专用脚本。
- `PREFIX-GROUP-` 是文件名中最后一个连字符之前的前缀；主题组名称位于其后。

---

## 2. 文件内部结构

每个 JSON 文件顶层是一个对象，键为主题 ID，值为该主题的元数据和卡片列表。一个文件可以包含多个主题，例如：

```json
{
  "animals": {
    "id": "animals",
    "kind": "flashcard",
    "title": "Animals",
    "title_cn": "动物",
    "css_class": "animals",
    "level": "pre-a1",
    "cards": [ ... ]
  },
  "food_and_drink": {
    "id": "food_and_drink",
    "kind": "flashcard",
    "title": "Food & drink",
    "title_cn": "食物与饮料",
    "css_class": "food",
    "level": "pre-a1",
    "cards": [ ... ]
  }
}
```

### 主题级字段说明

| 字段        | 类型   | 必填 | 说明                                                   |
|-------------|--------|------|--------------------------------------------------------|
| `id`        | string | 是   | 主题唯一标识，建议与键名一致，用于程序引用             |
| `kind`      | string | 是   | 卡片类型：`"flashcard"`（单词卡）或 `"fill_in"`（填字卡） |
| `title`     | string | 是   | 英文标题，显示在页面或 section 标题                     |
| `title_cn`  | string | 否   | 中文副标题                                               |
| `css_class` | string | 否   | 对应 HTML 中的 CSS 类名，用于差异化样式                 |
| `level`     | string | 是   | 级别标识，如 `"pre-a1"`、`"a1"`，用于命名和统计       |
| `cards`     | array  | 是   | 该主题下的所有单词卡片对象                               |

---

## 3. 卡片条目结构

每个卡片对象代表 **一个单词的一个特定词性义项**。不同词性或不同主题下的同一单词视为不同卡片。

```json
{
  "id": "fish_animals_n",
  "word": "fish",
  "pos": "n",
  "ipa": "/fɪʃ/",
  "meaning_cn": "鱼",
  "example_en": "The fish can swim.",
  "example_cn": "鱼会游泳。"
}
```

### 字段说明

| 字段          | 类型   | 必填 | 说明                                                         |
|---------------|--------|------|--------------------------------------------------------------|
| `id`          | string | 是   | 全局唯一标识符，格式见下文                                   |
| `word`        | string | 是   | 英文单词（可含空格、斜线等，如实记录）                       |
| `pos`         | string | 是   | 词性缩写，如 `"n"`, `"v"`, `"adj"`, `"adv"`。**不允许数组**，一个卡片只对应一个词性 |
| `ipa`         | string | 是   | 国际音标（英式发音）                                         |
| `meaning_cn`  | string | 是   | 中文释义（简洁，不加标点）                                   |
| `example_en`  | string | 是   | 英文例句（首字母大写，句末加句号）                           |
| `example_cn`  | string | 是   | 例句的中文翻译                                               |

### id 命名规则

格式：`{单词标识}_{主题ID}_{词性}`

- **单词标识**：小写单词，多词用下划线连接（如 `polar_bear`）。特殊写法如 `mouse / mice` 简化为 `mouse_mice`。
- **主题ID**：与主题级 `id` 一致（如 `animals`、`food`）。
- **词性**：小写缩写（`n`、`v`、`adj` 等）。

示例：
- `fish_animals_n` — 动物主题下的 fish（名词，鱼）
- `fish_food_n` — 食物主题下的 fish（名词，鱼肉）
- `drink_food_n` — 食物主题下的 drink（名词，饮料）
- `drink_food_v` — 食物主题下的 drink（动词，喝）

**注意**：`id` 必须全局唯一（至少在同一文件内唯一，建议跨文件也唯一以避免合并冲突）。

---

## 4. 设计原则与理由

### 4.1 数据与逻辑分离
- JSON 只存数据（单词、音标、释义、例句），不包含渲染逻辑。
- Python 构建脚本负责读取、校验、渲染 HTML/PDF。
- 修改一个单词只需编辑 JSON，不动代码。

### 4.2 每个词性独立一条
- 不同词性往往有不同释义和例句（如 `fish` 动物 vs 鱼肉；`drink` 饮料 vs 喝）。
- 合并会导致释义混杂、例句矛盾，不利于学习者理解。
- 独立条目使每张卡片聚焦一个明确语义，符合认知规律。

### 4.3 词性标注不可省略
- 词性是英语学习的基础信息，影响用法、搭配和语法。
- 为后续功能（按词性分类复习、语法分析）提供数据基础。
- 早期忽略会造成后期大量返工。

### 4.4 主题分组便于管理
- 每个文件可包含多个主题，按级别和内容范围划分。
- 添加新主题只需在对应文件追加或新建文件。
- 构建脚本可按文件或主题增量生成。

### 4.5 文件命名体现级别
- 级别前缀使数据层次清晰，便于构建脚本根据级别选择不同的渲染策略（如字体大小、排版密度）。
- 支持多级别共存，便于对比和升级。

---

## 5. 使用与维护

### 5.1 创建新文件
1. 确定级别和主题组，按命名规则创建 `.json` 文件。
2. 编写主题级元数据。
3. 为每个单词的每个词性义项创建独立卡片，确保 `id` 唯一。
4. 运行校验脚本检查必填字段和 `id` 重复。

### 5.2 修改现有数据
- 直接编辑对应 JSON 文件。
- 如果单词出现在多个主题中，分别编辑各主题的卡片。
- 若需更改词性，应拆分为独立卡片并更新 `id`。
- 每次生成、预览、新增或合并前都要执行共享校验：JSON 顶层为非空对象，主题键与主题 `id` 一致，必填字段类型正确且非空，主题和卡片 ID 不重复。
- 多文件一起生成时，卡片 ID 在所选文件之间也必须唯一。校验失败时不得生成文件或改动原 JSON。
- Streamlit 新增 JSON 必须完整校验且目标文件名不存在才写入；合并前检查主题和卡片 ID 冲突。

---

## 6. 注意事项

- **不要** 在 JSON 中存储样式信息（字体、颜色等）。样式由 CSS 和渲染模板控制。
- **不要** 使用数组形式的 `pos`。一个卡片只对应一个词性。若单词在同一主题下有多个词性，请拆分为多条卡片。
- **例句** 应简单，适合对应级别水平，避免复杂从句。
- **音标** 使用 IPA 标准英式发音，可从权威词典获取。
- POS 在 HTML 中以小号斜体缩写显示，紧跟中文释义并带句点；不使用徽章样式。
- 单词表和练习的英文大字使用本地 Andika 字体文件。PDF 使用 WeasyPrint running element 在每个主题所在的物理页顶部显示主题标题。
- 练习的填空字母使用固定宽度槽，不能用不等宽下划线字符串；多词短语保留词间隔，空格和标点不作为填空。
- 每份练习末尾提供按主题分组的答案表。
- **文件命名** 中的级别前缀应与主题级 `level` 字段保持一致。

---

## 7. 完整示例

`pre-a1-animals_and_food.json` 部分内容：

```json
{
  "animals": {
    "id": "animals",
    "kind": "flashcard",
    "title": "Animals",
    "title_cn": "动物",
    "css_class": "animals",
    "level": "pre-a1",
    "cards": [
      { "id": "cat_animals_n", "word": "cat", "pos": "n", "ipa": "/kæt/", "meaning_cn": "猫", "example_en": "My cat is black.", "example_cn": "我的猫是黑色的。" },
      { "id": "dog_animals_n", "word": "dog", "pos": "n", "ipa": "/dɒɡ/", "meaning_cn": "狗", "example_en": "The dog can run.", "example_cn": "狗会跑。" }
    ]
  },
  "food_and_drink": {
    "id": "food_and_drink",
    "kind": "flashcard",
    "title": "Food & drink",
    "title_cn": "食物与饮料",
    "css_class": "food",
    "level": "pre-a1",
    "cards": [
      { "id": "apple_food_n", "word": "apple", "pos": "n", "ipa": "/ˈæpl/", "meaning_cn": "苹果", "example_en": "I eat an apple.", "example_cn": "我吃一个苹果。" },
      { "id": "drink_food_n", "word": "drink", "pos": "n", "ipa": "/drɪŋk/", "meaning_cn": "饮料", "example_en": "What is your favourite drink?", "example_cn": "你最喜欢的饮料是什么？" },
      { "id": "drink_food_v", "word": "drink", "pos": "v", "ipa": "/drɪŋk/", "meaning_cn": "喝", "example_en": "Drink some water.", "example_cn": "喝一些水。" }
    ]
  }
}
```
