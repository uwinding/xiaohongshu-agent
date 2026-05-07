# AI 穿搭博主 Agent — 项目进度分析与待办清单

> 生成时间：2026-05-07　｜　项目状态：MVP 核心工程已完成，内容/策略层需补齐

---

## 一、四大核心问题分析与优化策略

### 1. TrendRadar 爬取实现与优化方向

**当前实现**（`app/scraper.py` + `app/skills/trend_radar.py`）：

```
requests.get("https://www.xiaohongshu.com/search_result?keyword=穿搭")
    → BeautifulSoup CSS 选择器 .note-item/.feeds-page
    → 提取标题文本
    → 喂给 LLM 做趋势分析
```

| 问题 | 根因 | 影响 |
|------|------|------|
| 爬虫 100% 返回空 | 小红书是 React SPA + 强反爬（Cookie/滑块验证/JS 混淆），`requests` 根本拿不到搜索页 DOM | TrendRadar 实际上**从未成功获取过数据** |
| CSS 选择器已失效 | `.note-item`、`.feeds-page` 是旧版小红书类名，当前页面类名完全不同 | 即使绕过反爬也拿不到内容 |
| 异常被静默吞掉 | `except Exception: return []`，不打印日志 | 问题长期不可见 |
| TrendRadar 降级返回 "暂无趋势数据" | 设计如此，但让整个 Skill 形同虚设 | Pipeline 中趋势分析完全缺失 |

**优化方向（分阶段）**：

| 阶段 | 方案 | 成本 | 效果 |
|------|------|------|------|
| **MVP 本周** | **不爬取。PM 手动整理趋势关键词/热词到 CSV，TrendRadar 读取本地数据** | 零 | 可控、可用 |
| **V1.5** | 工程师用 Playwright + 注入真实 Cookie（从浏览器导出） | 中 | 可获取真实热门笔记标题，但维护成本高 |
| **V2.0** | 接入第三方小红书数据 API（如新榜、千瓜） | 需付费 | 稳定可靠 |

> **当前最佳策略**：承认爬虫不可靠，**由 PM 作为领域专家直接充当"趋势雷达"**，整理趋势数据 → 输入 CSV → 工程师让 TrendRadar 从文件读数据。

**对应待办**：
- **PM**：整理 10-20 条当前小红书穿搭热搜词/趋势方向到 `data/trends.csv`（格式：keyword, hot_score, category, date）
- **工程师**：将 `TrendRadar.execute()` 改为优先读本地 CSV，爬虫作为可选增强；接入 Pipeline 主链路

---

### 2. 虚拟博主形象一致性与生图策略改进

**当前实现**（`app/skills/image_generator.py` + `data/persona.yaml`）：

```
avatar_desc (纯文本): "圆脸、温柔杏眼、长发微卷、暖白皮、气质优雅、微笑自然"
    ↓
_build_prompt(): "Subject: {avatar_desc}. " + outfit_prompt
    ↓
Seedream API (text-to-image, 单张生成, 无 seed)
    ↓
结果：每一张图的脸都不一样，服装细节不稳定
```

| 问题 | 根因 | 影响 |
|------|------|------|
| **脸部不统一** | 纯文本描述无法保证跨次生成同一张脸 | 同一位博主每次生成的"人"都不同 |
| **服装不可控** | 靠 Prompt 描述服装，AI 会"自由发挥" | 生成的服装与商品信息不一致 |
| **未使用 seed 参数** | `_generate_images` 没有传 `seed` | 即使同一 Prompt 多次调用，结果也不同 |
| **avatar_desc 太简单** | 只有一句中文描述，信息量不足 | Seedream（底层 Flux）的英文 Prompt 能力远强于中文 |
| **未利用参考图** | Seedream 支持 `image` 参数做图生图参考 | 没有利用 |

**优化策略 - 三步走**：

> 目标：每篇笔记的博主**脸和身材固定**，穿着变化源自商品搭配而非凭空想象。

| 步骤 | 方案 | 产出物 | 负责 |
|------|------|--------|------|
| **Step 1: Avatar 精细化** | 为每个人设设计一份详尽的英文 Appearance Prompt（300+ 词），固定：面部特征 / 发型 / 肤色 / 身高体型比例 / 禁用词 / 一致性关键词 | `data/avatar_prompts/{name}.txt` | **PM** 设计文案，工程师提供 Prompt 模板 |
| **Step 2: 参考图锚定** | 先稳定生图参数（seed、指导权重），然后用一致 Prompt 产出一组同一个人脸的图 | `data/avatar_refs/{name}.png`（参考图像） | **工程师** |
| **Step 3: 图生图链路** | Pipeline 改为：商品图 + 博主人设 → 参考图上叠加穿搭（图生图 / ControlNet / IP-Adapter） | 新的 `ImageGenerator` 逻辑 | **工程师** |

**Seedream 可用能力**（当前 API 已在用但未充分利用）：

- `seed` 参数 — 同 seed 同 prompt → 高度相似的结果
- `size` 参数 — 已用 "2K"，但可固定为具体比例 "1024x1536"（小红书竖图）
- `extra_body` 中的风格控制参数
- 可用 **group generation** 或 **batch** 模式并发生成多张

**生图流程重构**：

```
当前：Prompt 拼接 → 单张 API 调用 → 下载
改进：
1. 加载 Avatar Prompt（精细英文描述）+ seed 值
2. 组合穿搭商品描述，描述每件衣服的具体外观
3. 调用 Seedream，n=3, seed=固定值, 竖图尺寸
4. 跑一次后在 DB 保存 seed -> 同一博主后续全用这个 seed
5. 可选：多生成几张（5-8张），让 PM 挑选最好的 3 张
```

**对应待办**：
- **PM**：为每个人设撰写详尽的英文 Avatar Prompt（需包含：面部特征/发型/肤色/身高/体型/风格关键词/neg prompt），筛选或描述参考图
- **工程师**：生成流程升级 — 支持 seed 持久化、竖图尺寸固定、人设 Prompt 模板加载、并发批量生成

---

### 3. ContentWriter 文案改进

**当前实现**（`app/skills/content_writer.py`）：

```
SYSTEM_PROMPT 关键词：
  "姐妹们" "绝绝子" "冲" "闭眼入" "氛围感" "谁穿谁好看"
  口语化、亲切感、像闺蜜推荐、emoji点缀
```

| 问题 | 根因 | 影响 |
|------|------|------|
| **用词过时** | 这些词是 2023 年左右小红书爆款的典型特征，当前（2024-2025）已被用户反感 | 文本一眼假，像 AI 写的"假博主" |
| **广告味太重** | 默认套路："这不得冲？""谁穿谁好看""闭眼入" | 用户天然排斥硬广口吻 |
| **无人设差异** | 不管是大码博主还是小个子博主，语气差不多 | 缺乏人格化 |
| **没有真实参考样本** | Prompt 里只有通用指令，没有注入真实优质笔记风格 | 生成内容 AI 味浓，缺乏真人感 |
| **零 shot** | 直接丢 JSON 商品数据，没有 few-shot 示例 | 输出格式和风格不稳定 |

**2024-2025 小红书文案趋势特征**：

- 去"营销号化"：不用浮夸语气，更偏向**真实分享**、个人体验
- 信息密度高：单篇包含多个知识点 / 避坑点
- "反焦虑"叙事：不制造身材焦虑，强调"不同身材都能穿"
- 结构清晰：正文分点列 Tips + 结尾互动引导
- 封面标题公式已变：从 "绝绝子这穿搭绝了" → "大码女生通勤穿搭|一衣多穿5天不重样"

**优化策略**：

| 方向 | 做法 | 负责 |
|------|------|------|
| **抓取真实参考样本** | PM 在小红书找 10-20 篇同赛道高质量笔记，提炼文案结构、常用话术、标题公式 | **PM** |
| **构建 Few-Shot Prompt** | 将 3-5 篇参考样本接入 ContentWriter 的 System Prompt（脱敏 + 结构化） | **PM** 提供样本，**工程师** 实现注入 |
| **人设差异化 Prompt** | 每个人设一套独立的 ContentWriter Prompt，固化口吻差异 | **PM** |
| **追加"反 AI 味"规则** | System Prompt 中明令禁止某些 AI 高频词，要求更像真人 | **PM** |
| **文案模板库** | 为常见场景（新品测评/一衣多穿/避坑指南）预设计文风模板 | **PM** 设计，**工程师** 实现模板选择 |

**对应待办**：
- **PM**：制定文案改进策略（见上表 4 个方向的具体内容）
- **工程师**：ContentWriter 支持 few-shot 注入 + 人设专属 Prompt 文件加载 + 模板选择机制

---

### 4. 工程架构优化建议

**当前架构评估**（整体设计良好，以下为改进建议，非必须推翻重做）：

```
app/
├── skills/              # 6 个 Skill，每个独立可测 ✅
├── pipeline.py          # 串联编排 ✅
├── routes/              # API 层 ✅
└── llm_client.py        # LLM 封装 ✅
```

| 维度 | 当前 | 建议 | 理由 |
|------|------|------|------|
| **架构风格** | Skill + Pipeline | **保持现状**，不做大的架构变动 | 模块化很好，符合 Ribbi 对标意图，MVP 阶段过度重构是浪费 |
| **Prompt 管理** | 硬编码在 `.py` 文件中 | **外置到 `prompts/` 目录**（YAML/TOML） | PM 改 Prompt 不需要懂 Python，不需要改代码 |
| **Skill 注册** | `pipeline.py` 手动 `import` + 手动初始化 | 可选：添加 `SkillRegistry` 装饰器模式 | 当前只有 6 个 Skill，手动注册够用；扩展时再做 |
| **Pipeline 编排** | 硬编码的 5 步顺序执行 | 可考虑**声明式 Pipeline**（YAML 定义步骤和执行顺序） | 方便 PM 调整流程（如加 Step、调顺序） |
| **生图流程** | 单线程逐个生成 | 改为**并发批量** | 3 张图逐张等 30 秒 → 并发 3 次一起等 30 秒 |
| **配置管理** | `.env` + pydantic-settings | 保持，增加 `config/prompts.yaml` 集中管理 Prompt 路径 | 避免配置散落 |

**架构演进路线（建议）**：

```
本周 (MVP):  保持现有架构，只做「Prompt 外置」+「ImageGenerator 升级」
V1.5:        Pipeline 声明式配置 + Skill 注册表 + 并发生图
V2.0:        如果 Skill 数量 > 10，考虑引入 DAG 编排（Airflow/Prefect 太重，用简单 DAG）
```

**不推荐做的事**：
- 不引入 LangChain / LlamaIndex（太重）
- 不引入消息队列（MVP 不需要异步分发）
- 不拆分成前后端分离项目（管理后台用 Jinja2 够用）
- 不引入向量数据库 / RAG（会偏离"Skill 模块化"的设计亮点）

> **一句话总结**：当前架构作为 MVP 足够优秀，不要为了"看起来复杂"而做工程上的过度设计。唯一必须改的是 **Prompt 外置**（让 PM 能独立迭代 Prompt）。

**对应待办**：
- **工程师**：将 6 个 Skill 的 System Prompt 从 `.py` 抽到 `prompts/*.yaml`，Pipeline 从 YAML 加载
- **工程师**：ImageGenerator 改为并发生成
- **工程师**：Pipeline 支持声明式配置（YAML 定义步骤列表，不写死）
- **PM**：无独立架构任务，专注 Prompt 内容

---

## 二、产品经理待办

### P0 — 本周必须完成

#### 1. 人设 Avatar Prompt 精细化（配合 Q2 生图策略）

为每个虚拟博主产出一份详尽的英文 Appearance Prompt 文件，确保生图时面容和身材一致。

**模板参考**（工程师提供 Prompt 模板结构）：
```
Subject: A [age_range] Chinese female fashion blogger, [body_type] body type,
height [height]cm, [face_shape], [eye_shape] warm brown eyes, [hair_style],
[skin_tone] skin, [expression], [posture_description].

She wears: {outfit_description}.

Photography: full-body shot, front-facing, natural daylight, urban street
background, high-definition, Xiaohongshu OOTD style, 1024x1536 aspect ratio.

Negative: distorted face, extra limbs, deformed hands, wrong proportions,
blurry, low quality, distorted clothing, different person, inconsistent face.
```

**产出物**：`data/avatar_prompts/` 目录下，每个人设一个 `.txt` 文件
- `xiaolu_xuejie.txt`（小鹿学姐，大码，目前已有人设）
- `mimi_jiejie.txt`（小个子博主，待新增人设）
- `pingjia_xuesheng.txt`（学生党博主，待新增人设）

#### 2. 文案体系重构（配合 Q3）

| 子任务 | 说明 | 产出物 |
|--------|------|--------|
| **2a. 收集真实参考样本** | 在小红书搜 "大码穿搭" "小个子穿搭" "通勤穿搭" 各找 5-10 篇高赞笔记，截取标题+正文。注意选**非广告**、**文案自然**、**互动高**的 | `data/reference_posts/` 目录下的样本集 |
| **2b. 提炼文案特征** | 分析样本共性：标题结构（几字？用不用emoji？）、正文开头/结尾套路、分段方式、话题标签组合规律 | `docs/content_style_guide.md` |
| **2c. 重新设计 System Prompt** | 基于样本结论，为每个 ContentWriter 的 System Prompt 注入"反 AI 味"规则和新文案标准 | 新版 Prompt（先在笔记里写好，再由工程师接入） |
| **2d. 定义禁用词清单** | 列出禁止出现的 AI 高频词：绝绝子/闭眼入/冲冲冲/谁穿谁好看/尊嘟假嘟 等 | `data/banned_words.txt` |

#### 3. 商品库扩充（3 → 30+ 件）

编辑 `data/products.csv`，覆盖：上装 8-10 / 下装 6-8 / 连衣裙 6-8 / 外套 4-6 / 配饰 4-6

每件必填：name, category, price, brand, size_available, source_url, attributes(JSON: fit/color/fabric/style)

**参考选品方向**：淘宝/拼多多大码女装热销款、小红书爆款同款

### P1 — 下周

#### 4. 新增 2-3 个博主人设

基于当前 `data/persona.yaml` 小鹿学姐的模板格式，新增：

| 人设名 | 体型 | 风格 | 统一 Avatar Prompt |
|--------|------|------|-------------------|
| 小鹿学姐（已有） | 大码 XL-2XL | 法式优雅/通勤 | 见 P0-1 |
| 米米姐姐（新） | 小个子 153cm | 韩系/甜美/显高 | 见 P0-1 |
| 七七学姐（新） | 标准微胖 | 平价学生/休闲 | 见 P0-1 |

#### 5. 趋势数据手动整理

在小红书搜穿搭相关热搜词 → 整理为 `data/trends.csv`
格式：`keyword, hot_score(1-10), category, date`
支持：TrendRadar 直接读此文件替代爬虫。

#### 6. 内容质量标准文档

定义：图片质量 Checklist / 文案质量 Checklist / 穿搭合理性 Checklist / 通过/驳回标准

### P2 — 后续

#### 7. 积累 5-10 篇高质量 Demo 内容，准备面试汇报材料

---

## 三、工程师待办

### P0 — 本周必须完成

#### 1. [修] 修复 ImageGenerator 测试失败

**文件**：`tests/test_skills/test_image_generator.py`
**根因**：`_generate_images()` 循环逻辑导致实际生成 4 张而非 2 张
**方案**：修正 `_generate_images()` 逻辑，改为 `for i in range(num):` 只生成 `num` 张，确保代码行为正确。

#### 2. [增] 生图链路升级（配合 Q2）

| 子任务 | 说明 |
|--------|------|
| **2a. Seed 持久化** | 为每个人设在 `BloggerPersona` 表加 `seed` 字段，第一次生成后保存 seed，后续复用。确保同一个人设跨次生成 face 一致 |
| **2b. Avatar Prompt 外置加载** | `ImageGenerator` 从 `data/avatar_prompts/{persona_name}.txt` 加载精细英文 Prompt，替代当前简单的 `avatar_desc` 拼接 |
| **2c. 尺寸固定** | 生图 `size` 固定为 `"1024x1536"`（小红书竖图比例），不再用通配 `"2K"` |
| **2d. 并发批量生成** | `_generate_images()` 改为并发调用（`asyncio.gather` 或 `concurrent.futures`），3 张图并发等待而非逐张等 30 秒 |
| **2e. 过多生成供挑选** | 支持 `num_images=N` 参数，实际生成 `N*2` 张（或 `N, max(N*2, 5)`），让 PM 手动筛选最好的保留 |

#### 3. [修] Prompt 外置化（配合 Q4 架构优化）

**核心改动**：将所有 Skill 的 System Prompt 从 `.py` 常量中移到 `prompts/` 目录下的 YAML 文件。

**目录结构**：
```
prompts/
├── trend_radar.yaml
├── product_matcher.yaml
├── outfit_composer.yaml
├── image_generator.yaml
├── content_writer.yaml
└── performance_tracker.yaml
```

**YAML 格式**：
```yaml
name: content_writer
system_prompt: |
  你是小红书穿搭文案写手...
user_prompt_template: |
  请根据以下信息生成一篇小红书穿搭笔记...
  ...
```

**实现要点**：
- 每个 Skill 的 `__init__` 或 `execute` 时从对应 YAML 加载
- 支持环境变量或配置文件指定 prompts 目录路径
- 保持向后兼容：YAML 不存在时回退到代码中的默认 Prompt

#### 4. [修] TrendRadar 接入 Pipeline + 数据来源改造（配合 Q1）

| 子任务 | 说明 |
|--------|------|
| **4a. 改为读本地 CSV** | `TrendRadar.execute()` 优先从 `data/trends.csv` 加载趋势数据；爬虫降级为可选的后备方案 |
| **4b. 接入 Pipeline** | 在 `pipeline.run()` 的 `[1/5]` 加载 Persona 后调用 `self.trend_radar.execute(style_tags=persona.style_tags)`，趋势结果传入 ProductMatcher/OutfitComposer 上下文 |
| **4c. 日志改进** | scraper 失败时打印 warning 日志（而非静默吞掉），帮助 PM 感知数据源状态 |

#### 5. [修] ContentWriter 支持 Few-Shot 注入（配合 Q3）

| 子任务 | 说明 |
|--------|------|
| **5a. 加载参考样本** | ContentWriter 的 System Prompt 支持从 `data/reference_posts/*.txt` 加载 PM 提供的样本，作为 Few-Shot 示例注入（放在 System Prompt 末尾） |
| **5b. 人设专属 Prompt** | 每个人设支持独立的 `prompts/content_writer_{persona_name}.yaml`，有则用专属版，无则用默认版 |
| **5c. 禁用词过滤** | 加载 `data/banned_words.txt`，作为 neg_prompt 或后处理过滤词 |

#### 6. [修] docker-compose 环境变量匹配

将 `docker-compose.yml` 中的 `OPENAI_API_KEY`/`OPENAI_BASE_URL` 改为 `LLM_API_KEY`/`LLM_BASE_URL`/`IMAGE_API_KEY`/`IMAGE_BASE_URL`/`IMAGE_MODEL`/`LLM_MODEL`，与 `config.py` 对齐。

### P1 — 下周

#### 7. [修] PerformanceTracker 接入 Pipeline

在 `pipeline.run()` 生成 Post 后调用 `self.performance_tracker.execute()`。当前 DB 无真实 `PostPerformance` 数据，返回"暂无数据"属正常，接入后框架就位，后续数据进来就能自动分析。

#### 8. [增] 实现缺失 API 端点

- `POST /api/trends/refresh` — 触发 TrendRadar 刷新（读本地 CSV 或跑爬虫）
- `GET /api/performance/{id}` — 查看单篇效果报告

#### 9. [增] Pipeline 声明式配置（配合 Q4）

将 `pipeline.run()` 的硬编码 5 步流程改为从 YAML 配置加载步骤列表：

```yaml
# config/pipeline.yaml
steps:
  - skill: trend_radar
    params: {style_tags: "{{persona.style_tags}}"}
  - skill: product_matcher
    params: {products: "{{products}}", persona: "{{persona}}"}
  - skill: outfit_composer
    params: {product_set: "{{step.product_matcher.product_set}}", persona: "{{persona}}"}
  ...
```

#### 10. [增] 爬虫升级

使用 Playwright/DrissionPage 替换 `requests`，或引入 browser-use 自动操控浏览器。

### P2 — 后续

#### 11. Pipeline 错误处理增强（降级/跳过/重试）

#### 12. GitHub Actions CI（自动测试 + 覆盖率）

---

## 四、协作节奏（建议）

### 本周冲刺（May 5-11）

```
PM 侧：
  Day1-2: Avatar Prompt 撰写（3个人设）+ 小红书样本收集（20篇）
  Day3-4: 文案风格分析 + 新版 ContentWriter Prompt 草稿
  Day4-5: 商品库 + 趋势数据录入

工程师侧：
  Day1: 修复测试 + 环境变量
  Day2: Prompt 外置化 + Avatar Prompt 加载
  Day3: ImageGenerator 升级（seed/并发/尺寸）
  Day4: TrendRadar 接入 Pipeline + CSV 模式
  Day5: ContentWriter Few-Shot 注入 + 联调 PM 写的新 Prompt
```

### 沟通方式

- 每日 5 分钟同步：各自进度 + 阻塞
- Prompt 联调：PM 写 Prompt 文本 → 工程师放到文件 → 一起跑生成看结果
- 每周五验收：跑一次全链路，评审输出质量

### Git 分支建议

```
main          — 稳定，可直接运行
eng/image-v2  — 工程师生图升级分支
eng/prompts   — 工程师 Prompt 外置化分支
pm/content    — PM Prompt/数据文件分支
```

---

## 五、FAQ

| 问题 | 回答 |
|------|------|
| 当前 LLM 模型？ | DeepSeek-v4-flash（opencode.ai） |
| 当前生图模型？ | doubao-seedream-4-5-251128（火山方舟） |
| 启动命令？ | `pip install -e ".[dev]" && python scripts/seed.py && uvicorn app.main:app --reload` |
| 管理后台？ | http://localhost:8000 |
| API 文档？ | http://localhost:8000/docs |
| 测试状态？ | 30/31 通过（1 个 ImageGenerator 测试失败） |
| 设计文档？ | `AI穿搭博主Agent-项目设计文档.md` |
