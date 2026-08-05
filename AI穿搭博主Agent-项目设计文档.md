# AI 虚拟穿搭博主 Agent - 项目设计文档

> **项目定位**：面向小红书平台，通过 AI Agent 实现虚拟穿搭博主自动生成穿搭图文并发布，完成带货流量变现。  
> **项目类型**：AI产品经理面试实战项目  
> **工期**：3周 MVP（2人协作）  
> **参考产品**：Ribbi（多模块自进化创意 AI Agent）

---

## 目录

1. [赛道痛点分析](#1-赛道痛点分析)
2. [产品定位与目标](#2-产品定位与目标)
3. [系统架构总览](#3-系统架构总览)
4. [六大 Skill 详细设计](#4-六大-skill-详细设计)
5. [技术栈](#5-技术栈)
6. [数据模型与数据流](#6-数据模型与数据流)
7. [工作拆分（PM vs 工程师）](#7-工作拆分pm-vs-工程师)
8. [项目排期（3周）](#8-项目排期3周)
9. [与 Ribbi 的对比与优化点](#9-与-ribbi-的对比与优化点)
10. [面试展示策略](#10-面试展示策略)
11. [风险与后续规划](#11-风险与后续规划)

---

## 1. 赛道痛点分析

### 1.1 小红书穿搭赛道现状

| 痛点              | 描述                          | 机会                               |
| --------------- | --------------------------- | -------------------------------- |
| **内容生产门槛高**     | 真人博主需要拍摄、修图、写文案，单篇内容耗时2-3小时 | AI 自动化可降低 90% 生产时间               |
| **人设一致性难维持**    | 真人博主体型/肤色/风格固定，难以覆盖多元受众     | AI 虚拟博主可定制人设，精准匹配细分人群            |
| **选品效率低**       | 博主手动筛选商品、搭配试穿，匹配效率差         | Agent 自动匹配商品库，按人设推荐搭配            |
| **数据反馈慢**       | 真人凭经验调整内容策略，缺乏系统数据驱动        | PerformanceTracker 自动追踪效果，数据驱动优化 |
| **大码/小个子人群被忽视** | 主流穿搭博主以标准身材为主，大码/小个子用户缺乏参考  | 精准切入细分人群，信任度高，转化率更好              |

### 1.2 细分赛道选择：女装 + 大码/小个子 + 特定风格

- **大码女装**：淘宝/小红书大码女装年增速 30%+，用户强需求但优质内容供给不足
- **小个子穿搭**：155cm 以下用户是小红书穿搭搜索高频词，"小个子显高"笔记互动率高
- **特定风格**：法式/韩系/国潮/通勤等风格标签有利于建立差异化人设

### 1.3 竞品参考

| 产品        | 定位                  | 差异化                     |
| --------- | ------------------- | ----------------------- |
| Ribbi     | 通用创意 AI Agent，多技能模块 | 我们的 Agent 聚焦单一垂直赛道，深度更深 |
| 小红书AI创作工具 | 平台内置AI辅助写文案         | 不具备穿搭理解能力，无法端到端生成图文     |
| 淘宝AI试穿    | 电商侧虚拟试穿             | 不产出小红书风格内容，缺乏社交传播属性     |

---

## 2. 产品定位与目标

### 2.1 产品一句话定义

**一个能自动生成小红书穿搭图文并追踪效果的 AI 虚拟博主 Agent。**

### 2.2 核心用户价值

- **对博主**：零拍摄成本、24小时内容生产、数据驱动优化
- **对用户**：获得符合自身体型/风格的穿搭参考，所见即可买
- **对商家**：精准带货渠道，AI博主可批量覆盖多个细分人群

### 2.3 MVP 目标

- 输入商品链接或商品库，Agent 自动产出完整小红书穿搭图文（标题+正文+3-5张图+商品标记）
- 支持一个完整的虚拟博主人设（大码或小个子特定风格）
- 简单的 Web 管理后台（查看/审核/触发生成）
- Docker 一键部署，可演示完整链路

### 2.4 变现模式

小红书店铺带货佣金：内容挂商品链接，用户点击购买后获取佣金分成。

---

## 3. 系统架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                       AI 穿搭博主 Agent                           │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │TrendRadar│  │Product   │  │Outfit    │  │Image     │         │
│  │ 趋势雷达  │  │Matcher   │  │Composer  │  │Generator │         │
│  │          │  │ 商品匹配  │  │ 穿搭合成  │  │ 图片生成  │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                   │
│  ┌──────────┐  ┌────────────────────────────────────┐            │
│  │Content   │  │  PerformanceTracker                 │            │
│  │Writer    │  │  数据追踪 + 反馈优化                  │            │
│  │ 文案写作  │  └────────────────────────────────────┘            │
│  └──────────┘                                                    │
│                                                                   │
├───────────────────────────────────────────────────────────────────┤
│                Python FastAPI 调度编排层                           │
├───────────────────────────────────────────────────────────────────┤
│          SQLite 存储  │  本地文件系统（图片存储）                    │
├───────────────────────────────────────────────────────────────────┤
│   GPT-4o / Claude (LLM)   │   DALL-E / Gemini (多模态生图)        │
├───────────────────────────────────────────────────────────────────┤
│       小红书数据源  │  商品库（淘宝/小红书店铺链接）                 │
└───────────────────────────────────────────────────────────────────┘
```

### 架构设计原则

- **模块化**：每个 Skill 独立可测、可替换，类似 Ribbi 的 Skill 系统
- **轻量化**：MVP 不引入 LangChain 等重框架，纯 Python 函数串联
- **可观测**：每个 Skill 的输出有标准化日志，便于调试和效果评估
- **一致性**：虚拟博主人设（Persona）贯穿所有 Skill，保证内容风格统一

---

## 4. 六大 Skill 详细设计

### 4.1 TrendRadar — 趋势雷达

**职责**：基于小红书 collector 自采样数据识别账号可用的穿搭趋势，输出给 ProductMatcher、OutfitComposer 和 ContentWriter。当前已废弃灰豚/千瓜三张手工趋势表和 `strategy_full.csv` 主链路。

> **实现方式**：collector 持续采集小红书搜索热词和笔记表现观察 → `scripts/collector_to_trends.py` 聚合为 `data/source_collector_trends.csv` → `TrendRadar` 读取该文件并按热度、增长、置信度、证据量和人设相关性综合排序。

#### 数据源（collector observation → source_collector_trends.csv）

| 数据层 | 文件/表 | 说明 | 用途 |
| ------ | ------ | ---- | ---- |
| 热词观察 | `collector_hotword_observation` | 每次搜索接口返回的 `hot_query`，可选 DOM tab 热词 | 判断搜索相关词是否反复出现 |
| 笔记观察 | `collector_note_observation` | 每次采集看到的笔记互动表现、发布时间、标签 | 计算内容互动强度和近期增长 |
| 素材库 | `collector_note` | 去重后的笔记正文、作者、互动数 | 内容样本沉淀，不直接代表趋势频次 |
| 聚合趋势表 | `data/source_collector_trends.csv` | 自采样趋势唯一正式输入源 | TrendRadar 读取 |
| 检查表 | `data/trends_normalized.csv` | TrendRadar 读取后的归一化检查输出 | 调试和人工复核 |

> **定位说明**：自采样数据不能代表全平台真实搜索指数或话题浏览量，但可以反映“当前监控词池内，哪些穿搭方向在升温”，适合账号选题、选品和标签决策。

#### Collector 采集逻辑

当前 collector 支持两类采集：

1. **基础种子词采集**：读取 `data/keywords.yaml`，如 `穿搭`、`通勤穿搭`、`夏季穿搭`。
2. **扩展关键词采集**：读取搜索页“综合”旁边的 DOM 关键词，取前 10 个逐个二次采集，并全局按 `note_id` 去重。

优化后的推荐命令：

```bash
python3 -m app.collector \
  --keywords-file data/keywords.yaml \
  --max-notes 80 \
  --sorts time_filtered,general,popularity_descending \
  --recent-days 7 \
  --top-per-metric 10 \
  --page-hotwords \
  --expand-page-hotwords 10
```

| 参数 | 说明 |
| ---- | ---- |
| `--sorts` | 同一关键词用多个小红书搜索排序拉大候选池，再按 `note_id` 去重 |
| `--recent-days 7` | 只让最近 7 天笔记参与 Top 排名 |
| `--top-per-metric 10` | 分别取点赞 Top10、评论 Top10、收藏 Top10，并合并去重 |
| `--page-hotwords` | 通过 Playwright 读取页面 DOM 热词 |
| `--expand-page-hotwords 10` | 对前 10 个 DOM 关键词二次采集 |

> **接口策略**：如果小红书接口不稳定暴露“按赞/评/藏排序”，不要硬编码猜测参数。当前采用“多搜索排序拉候选池 + 抓详情后本地按赞/评/藏重排”的策略，更可控。

#### 数据处理逻辑

`scripts/collector_to_trends.py` 从观察表聚合趋势，输出字段：

| 字段 | 说明 |
| ---- | ---- |
| `keyword` | 归一化后的趋势词 |
| `category` | 品类/季节/场景/风格/人群/灵感/话题 |
| `heat_score` | 当前热度，来自热词排名分 + 笔记互动加权 |
| `growth_score` | 近期增长，当前按最近窗口互动和热词重复出现估算 |
| `confidence` | 置信度，衡量证据是否足够，不等同于热度 |
| `evidence_count` | 证据数量，热词观察数 + 去重笔记数 |
| `source` | 数据来源，如 `api_hot_query`、`dom_tab`、`note_observation` |
| `observed_date` | 聚合日期 |

互动加权：

```
engagement_score = like_count + collect_count * 2 + comment_count * 3
```

置信度由四类证据构成：

| 证据 | 含义 |
| ---- | ---- |
| 样本量 | 观察次数和笔记数是否足够 |
| 种子词覆盖 | 是否从多个监控词入口出现 |
| 来源多样性 | 是否同时来自 API 热词、DOM 热词、笔记标签 |
| 连续性 | 是否多次观察到，而不是单篇爆文噪声 |

#### 离题过滤

聚合时会过滤不适合女生穿搭博主账号的母婴/儿童/孕产词，例如：

```
宝宝、宝妈、母婴、亲子、儿童、童装、婴儿、幼儿、小朋友、孕妈、孕期、纸尿裤
```

避免小红书搜索中的泛流量词污染穿搭趋势。

#### TrendRadar 综合评分

TrendRadar 不再只看是否命中人设词，而是综合：

```
final_score =
  heat_component
  + growth_component
  + persona_relevance
  + confidence_component
  + evidence_component
  + category_adjustment
```

关键策略：

- **品类词**：不强制命中人设，否则会漏掉短裤、半身裙、防晒衣等选品趋势。
- **风格/场景/人群词**：必须与人设相关，避免内容方向跑偏。
- **低置信度词**：可以保留为观察项，但不作为主方向。
- **高热单篇词**：若证据数少、来源单一，需要降权。

#### TrendRadar 输出结构

```json
{
  "product_hints": [
    {
      "keyword": "半身裙穿搭",
      "category": "品类",
      "heat_score": 280.0,
      "confidence": 0.289,
      "evidence_count": 4,
      "source": "api_hot_query"
    }
  ],
  "style_directions": [
    {
      "keyword": "通勤穿搭",
      "category": "场景",
      "heat_score": 1390.9,
      "growth_score": 1061.9,
      "confidence": 0.535,
      "persona_relevance": 5
    },
    {
      "keyword": "韩系穿搭",
      "category": "风格",
      "confidence": 0.456
    }
  ],
  "topic_tags": [
    {"keyword": "夏日穿搭", "category": "季节"},
    {"keyword": "微胖穿搭", "category": "人群"},
    {"keyword": "穿搭合集", "category": "灵感"}
  ],
  "trend_summary": "趋势分析：基于 collector 自采样趋势，选品优先半身裙穿搭，内容方向优先通勤穿搭。"
}
```

#### 数据刷新流程

1. 刷新小红书登录态：`data/storage_state.json` 或 `XHS_COOKIE`。
2. 运行 collector 写入 observation 表。
3. 运行 `python3 scripts/collector_to_trends.py` 生成 `data/source_collector_trends.csv`。
4. 运行 `python3 scripts/process_trends.py` 生成检查表 `data/trends_normalized.csv`。
5. `GenerationPipeline` 中的 TrendRadar 自动读取最新趋势文件。

### 4.2 ProductMatcher — 商品匹配

**职责**：输入商品链接或商品库，根据博主人设和趋势数据，推荐搭配商品组合。

| 维度         | 描述                                                                     |
| ---------- | ---------------------------------------------------------------------- |
| **输入**     | 商品链接/商品CSV、博主人设、可选趋势上下文                                                |
| **处理逻辑**   | 解析商品属性（品类/颜色/版型/尺码） → LLM 根据人设+体型约束筛选 → 组合上下装+配饰 → 检查搭配合理性             |
| **输出**     | `{ product_set: [{name, url, category, reason}], match_score: float }` |
| **关键约束**   | 大码：优先 A字/直筒/阔腿版型、深色显瘦、V领拉长脖颈；小个子：高腰线、短款、同色系延长视觉                        |
| **PM 交付物** | ProductMatcher System Prompt、体型穿搭规则库、商品匹配示例                            |

### 4.3 OutfitComposer — 穿搭合成

**职责**：根据匹配的搭配商品，合成完整穿搭方案，生成用于AI生图的 Prompt。

| 维度               | 描述                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------- |
| **输入**           | 匹配商品组合 `product_set`、博主人设、场景/风格标签                                                   |
| **处理逻辑**         | LLM 基于商品属性 + 体型约束 + 风格标签 → 生成穿搭场景描述 → 转换为生图Prompt（正面描述 + 反向排除）                      |
| **输出**           | `{ outfit_desc: string, pos_prompt: string, neg_prompt: string, scene: string }`    |
| **生图 Prompt 结构** | `"一位[体型]女性博主，穿着[穿搭描述]，[场景背景]，[光线/氛围]，小红书OOTD风格，全身照/半身照，高清写实 --no 畸形手指, 面部崩坏, 商品变形"` |
| **PM 交付物**       | OutfitComposer System Prompt、Prompt 模板库、优质生图示例集                                     |

### 4.4 ImageGenerator — 图片生成

**职责**：调用多模态大模型 API 生成虚拟博主穿搭图片，保证人设一致性。

| 维度          | 描述                                                                 |
| ----------- | ------------------------------------------------------------------ |
| **输入**      | `pos_prompt`、`neg_prompt`、博主人设（参考图/描述）、生成数量                        |
| **处理逻辑**    | 拼接人设一致性描述 → 调用 DALL-E 3 / Gemini → 下载图片 → 本地存储 → 基础质量检查（分辨率/内容安全）  |
| **输出**      | `{ images: [local_path, ...], gen_metadata: {model, time, cost} }` |
| **一致性策略**   | 在 Prompt 中固定博主的面部特征描述、发型、肤色、体型比例；使用种子（seed）参数维持风格一致性               |
| **成本控制**    | 单次生成 3-5 张图，MVP 阶段预估单篇成本 $0.5-1.5                                  |
| **PM 交付物**  | 生图质量 CheckList、博主形象一致性规范、图片风格参考板                                   |
| **工程师实现要点** | DALL-E/Gemini API 封装；图片下载与本地存储；批量生成与重试机制                           |

### 4.5 ContentWriter — 文案写作

**职责**：根据穿搭方案、商品信息和趋势数据，生成小红书风格图文文案。

| 维度         | 描述                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------- |
| **输入**     | 穿搭描述 `outfit_desc`、商品列表、博主人设、`topic_tags`（TrendRadar 输出的全维度热门标签，含风格/人群/选品/标签各类）                          |
| **处理逻辑**   | LLM 生成小红书爆款风格的标题 → 正文（穿搭心得+单品亮点+购买理由） → 从 `topic_tags` 中选取最匹配的话题标签 → 商品标记信息                              |
| **输出**     | `{ title: string, content: string, hashtags: [], product_tags: [{name, url}] }`                          |
| **文案风格**   | 口语化、亲切感、emoji点缀、像真人分享而非营销号；大码强调"显瘦""自信"，小个子强调"显高""比例"                                                    |
| **话题标签策略** | 不限于单一类别：从 TrendRadar 提供的 `topic_tags` 中，按优先级选取风格标签（如 #高级感穿搭）+ 人群标签（如 #微胖穿搭）+ 品类标签（如 #连衣裙）组合使用，每篇 5-8 个标签 |
| **PM 交付物** | ContentWriter System Prompt、文案风格规范、爆款标题公式库、话题标签策略                                                        |

### 4.6 PerformanceTracker — 数据追踪

**职责**：追踪已发布内容的表现数据，生成优化建议反馈给其他 Skill。

| 维度         | 描述                                                                    |
| ---------- | --------------------------------------------------------------------- |
| **输入**     | 笔记ID、手动录入/模拟的数据（MVP阶段不接入小红书官方API）                                     |
| **处理逻辑**   | 记录互动数据 → 分析哪些风格/话题/时间段表现好 → LLM 生成优化建议                                |
| **输出**     | `{ performance_report: {}, optimization_suggestions: [] }`            |
| **反馈链路**   | 风格偏好 → 影响 TrendRadar 权重；时间偏好 → 影响发布时间策略；商品转化 → 影响 ProductMatcher 选品偏好 |
| **PM 交付物** | 效果评估指标体系、优化策略规则、数据看板设计需求                                              |

---

## 5. 技术栈

| 层            | 选型                          | 说明                       |
| ------------ | --------------------------- | ------------------------ |
| **后端框架**     | Python 3.11+ / FastAPI      | 异步支持好，适合 API 编排，工程师熟悉    |
| **文本生成**    | 本地规则化 Skill，保留 OpenAI-compatible LLMClient 兼容层 | 商品匹配、穿搭方案、文案生成当前不强依赖外部文本模型 |
| **图片生成**     | OpenAI-compatible Images API | 多模态生图服务直出，MVP 不引入 ComfyUI |
| **数据存储**     | SQLite                      | 轻量零运维，后期可迁移 PostgreSQL   |
| **图片存储**     | 本地文件系统                      | MVP 够用，按日期/笔记ID 组织目录     |
| **前端(管理后台)** | FastAPI + Jinja2 模板         | 极简 Web 页面，不引入前后端分离       |
| **趋势采集**     | httpx + xhshow 签名 + Playwright | API 采集搜索/详情，Playwright 用于扫码登录和 DOM 热词 |
| **趋势处理**     | collector observation + CSV 聚合 | `collector_to_trends.py` 输出 `source_collector_trends.csv` |
| **部署**       | Docker + docker compose     | 一键启动，面试演示友好              |

### 不选用的技术（MVP 阶段）

| 技术                         | 不选原因                     |
| -------------------------- | ------------------------ |
| LangChain / LlamaIndex     | 过度工程化，简单函数串联即可           |
| ComfyUI / Stable Diffusion | 需要 GPU，部署复杂，MVP 用 API 直出 |
| Redis / Celery             | 不需要异步任务队列，MVP 同步调用即可     |
| React / Vue 前端             | 管理后台用模板渲染足够              |
| PostgreSQL                 | SQLite 对单机 MVP 完全够用      |

---

## 6. 数据模型与数据流

### 6.1 核心数据模型

```
┌─────────────────────────────────────────────────────┐
│                   BloggerPersona                     │
│  name, age_range, body_type, size_category           │
│  style_tags[], tone_of_voice, avatar_ref             │
└────────────────────────┬────────────────────────────┘
                         │ 1:N
                         ▼
┌─────────────────────────────────────────────────────┐
│                    GeneratedPost                     │
│  outfit_ref, images[], title, content               │
│  hashtags[], product_tags[], status                  │
│  created_at, published_at                            │
└──────────────────┬──────────────┬───────────────────┘
                   │ 1:1          │ 1:1
                   ▼              ▼
┌──────────────────────┐  ┌──────────────────────────┐
│       Outfit         │  │    PostPerformance        │
│  products[]          │  │  likes, comments, shares  │
│  description         │  │  click_rate               │
│  style_tags[]        │  │  publish_date             │
│  body_type_suit.     │  │                           │
└──────┬───────────────┘  └───────────────────────────┘
       │ N:N
       ▼
┌─────────────────────────────────────────────────────┐
│                     Product                          │
│  name, category, price, brand, size_available        │
│  source_url, attributes{}, images[]                  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              CollectorTask / CollectorNote           │
│  keyword, status, notes_found, notes_saved           │
│  note_id, title, content_clean, author, metrics      │
└────────────────────────┬────────────────────────────┘
                         │ 1:N
                         ▼
┌─────────────────────────────────────────────────────┐
│        CollectorHotwordObservation / NoteObservation │
│  seed_keyword, hotword, rank, source, observed_at    │
│  note_id, like_count, collect_count, comment_count   │
└────────────────────────┬────────────────────────────┘
                         │ aggregate
                         ▼
┌─────────────────────────────────────────────────────┐
│           source_collector_trends.csv                │
│  keyword, category, heat_score, growth_score         │
│  confidence, evidence_count, source, observed_date   │
└─────────────────────────────────────────────────────┘
```

### 6.2 数据流向

```
[外部输入]                      [Agent PipeLine]                       [输出]

商品库 ───┐
          ├──▶ ProductMatcher ──▶ OutfitComposer ──▶ ImageGenerator ──┐
collector ─▶ source_collector_trends.csv ─▶ TrendRadar ──────────────┘
          │          │                    │                  │
          │          └── trends_normalized.csv（检查表）       │
                                                                       │
博主人设 ◀────────────────────────────────────────────────────┘         │
                                                                       │
                                                                       ▼
                                                               ContentWriter
                                                                       │
                                                                       ▼
                                                              [人工审核页面]
                                                                       │
                                                            发布 ◀─────┘
                                                                       │
                                                              PerformanceTracker
                                                                       │
                                                              反馈 ◀──┘
```

### 6.3 主要 API 接口设计

| 方法    | 路径                      | 说明               |
| ----- | ----------------------- | ---------------- |
| POST  | `/api/generate`         | 按人设、商品、风格/场景参数触发完整生成流程 |
| GET   | `/api/posts`            | 获取生成内容列表（支持状态筛选） |
| GET   | `/api/posts/{id}`       | 查看单篇生成详情         |
| PATCH | `/api/posts/{id}`       | 审核通过/驳回/修改内容     |
| GET   | `/api/trends`           | 查看数据库内趋势记录（当前 TrendRadar 主要读取 CSV） |
| GET   | `/`                     | 管理后台页面           |

---

## 7. 工作拆分（PM vs 工程师）

### 7.1 产品经理（你）负责

| 工作项                    | 产出物                                                  | 工作量  |
| ---------------------- | ---------------------------------------------------- | ---- |
| **赛道分析文档**             | 小红书穿搭赛道竞品分析、用户画像、痛点总结                                | 2天   |
| **博主人设设计**             | 虚拟博主完整人设卡（姓名/年龄/体型/风格/口吻/参考形象）                       | 1天   |
| **Prompt Engineering** | 6个Skill的System Prompt + Few-shot示例 + 输出JSON Schema定义 | 3天   |
| **体型穿搭规则库**            | 大码/小个子的穿搭约束规则（版型/颜色/比例/避坑）                           | 1天   |
| **商品库设计**              | 商品筛选标准、搭配规则、初始商品种子库（20+件）                            | 1.5天 |
| **内容策略规范**             | 文案风格指南、标题公式库、话题标签策略、发布时间建议                           | 1天   |
| **质量审核标准**             | 生图质量CheckList、内容审核维度、通过/驳回标准                         | 0.5天 |
| **效果评估体系**             | KPI定义（互动率/点击率/转化率）、优化策略规则                            | 0.5天 |
| **面试汇报文档**             | PRD摘要、项目汇报PPT、Demo演示脚本                               | 2天   |

### 7.2 工程师负责

| 工作项                  | 产出物                                     | 工作量  |
| -------------------- | --------------------------------------- | ---- |
| **项目脚手架**            | FastAPI项目结构、SQLite数据模型定义、配置文件、环境变量模板    | 1天   |
| **LLM API 封装层**      | 统一的LLM调用类（支持GPT-4o/Claude切换）、重试/超时机制    | 1天   |
| **Collector + TrendRadar代码** | 小红书搜索/详情采集、observation 落库、趋势聚合、TrendRadar 综合评分 | 2天 |
| **ProductMatcher代码** | 商品属性解析 + 本地规则评分 + 搭配合理性校验              | 1.5天 |
| **OutfitComposer代码** | 本地穿搭合成 + 生图 Prompt生成 + JSON结构化输出          | 1天   |
| **ImageGenerator代码** | DALL-E/Gemini API封装、图片下载存储、批量生成、基础质量检查  | 1.5天 |
| **ContentWriter代码**  | 本地文案生成 + 话题标签自动匹配 + 商品标记格式化            | 1天   |
| **Pipeline编排**       | Skill串联调度 + 中间结果缓存 + 错误处理与回退            | 1天   |
| **管理后台页面**           | FastAPI+Jinja2 页面：内容列表、详情查看、审核操作、手动触发生成 | 2天   |
| **SQLite CRUD**      | 所有数据模型的增删改查接口                           | 1天   |
| **Docker部署**         | Dockerfile + docker-compose + 启动脚本      | 0.5天 |
| **联调测试**             | 与PM联调Prompt效果、全链路测试                     | 1天   |

### 7.3 协作重叠区

- API Key 申请与管理（GPT-4o/DALL-E/Gemini 等）
- 每个 Skill 的 Prompt 调优（PM写初版 → 工程师接入 → 联调迭代）
- 全链路效果验收（PM定义标准 → 工程师修复问题）

---

## 8. 项目排期（3周）

### Week 1：基础搭建 + 前半链路

| 天              | PM                         | 工程师                                    |
| -------------- | -------------------------- | -------------------------------------- |
| Day 1-2        | 赛道分析文档                     | 项目脚手架 + SQLite数据模型                     |
| Day 3          | 博主人设设计                     | LLM API封装层 + 配置文件                      |
| Day 3-4        | 趋势词池 + 标签策略 + 过滤规则     | Collector 采集 + 趋势聚合 + TrendRadar 评分 |
| Day 4-5        | ProductMatcher Prompt + 规则 | ProductMatcher 代码                      |
| **Week 1 里程碑** | ✅ 赛道文档 + 人设卡完成             | ✅ 脚手架 + TrendRadar + ProductMatcher 可跑 |

### Week 2：核心内容生成链路

| 天              | PM                          | 工程师                         |
| -------------- | --------------------------- | --------------------------- |
| Day 1-2        | OutfitComposer Prompt + 模板库 | OutfitComposer 代码           |
| Day 2-3        | ImageGen 质量标准 + 参考板         | ImageGenerator API封装 + 图片存储 |
| Day 3-4        | ContentWriter Prompt + 文案指南 | ContentWriter 代码            |
| Day 4-5        | 商品库建设 + 审核标准                | Pipeline串联 + SQLite CRUD    |
| **Week 2 里程碑** | ✅ 完整Prompt体系 + 商品库          | ✅ 端到端生成链路跑通                 |

### Week 3：闭环收尾 + 展示准备

| 天              | PM                           | 工程师                   |
| -------------- | ---------------------------- | --------------------- |
| Day 1          | PerformanceTracker 策略 + 指标体系 | PerformanceTracker 代码 |
| Day 1-2        | 内容审核 + 效果验收                  | 管理后台页面                |
| Day 3          | 面试汇报文档                       | Docker部署              |
| Day 3-4        | Demo演示脚本                     | 联调 + Bug修复            |
| Day 4-5        | 文档最终整理                       | 最终优化                  |
| **Week 3 里程碑** | ✅ 完整项目文档 + Demo              | ✅ Docker一键部署 + 管理后台可用 |

---

## 9. 与 Ribbi 的对比与优化点

### 9.1 Ribbi 的核心特点

Ribbi 是一个 **"Self-Evolving Creative AI Agent"**，其核心设计理念：

- **多技能模块化**：Creators 可以组合不同 Skill 完成复杂创意任务
- **社交与电商打通**：从趋势发现 → 内容生成 → 发布追踪 → 效果优化，全链路覆盖
- **自进化学习**：根据使用数据和效果反馈，持续优化内容质量

### 9.2 本项目借鉴 Ribbi 的设计

| Ribbi 特点     | 本项目对应设计                                    |
| ------------ | ------------------------------------------ |
| 模块化 Skill 系统 | 6个独立 Skill，每个可独立调用和替换                      |
| 社交内容生成       | ContentWriter + ImageGenerator 产出小红书图文     |
| 电商产品图生成      | ProductMatcher + OutfitComposer 实现商品到穿搭的转化 |
| 效果追踪优化       | PerformanceTracker 闭环反馈                    |
| 人设一致性        | BloggerPersona 贯穿全链路                       |

### 9.3 相比 Ribbi 的差异化优化

| 维度        | Ribbi        | 本项目                     |
| --------- | ------------ | ----------------------- |
| **定位**    | 通用创意 AI 平台   | 垂直穿搭赛道，深度更深             |
| **人设一致性** | 依赖 Prompt 描述 | 系统性 Persona 体系 + 穿搭规则库  |
| **体型适配**  | 无特殊处理        | 大码/小个子专属穿搭约束逻辑          |
| **电商深度**  | 通用商品图生成      | 从选品→搭配→生图→文案→带货，完整闭环    |
| **数据反馈**  | 通用性能追踪       | 穿搭专属指标体系（互动率×风格标签×商品转化） |

---

## 10. 面试展示策略

### 10.1 产品经理面试可讲的故事线

1. **市场洞察**："我发现了小红书穿搭赛道的一个结构化机会——大码和小个子用户的内容需求远大于供给…"
2. **产品设计**："我设计了6个Skill模块化的Agent架构，每个Skill都有明确的输入输出和价值定位…"
3. **协作能力**："我和工程师拆分了工作边界，我负责Prompt和策略，他负责工程实现，3周完成MVP…"
4. **数据驱动**："PerformanceTracker形成了数据闭环，Agent可以根据发布效果自我优化…"
5. **商业价值**："这是一个可直接变现的系统——内容挂商品链接赚佣金，ROI可量化…"

### 10.2 Demo 展示要点

- **Docker 一键启动**，全程无需复杂环境配置
- **Web 管理后台** 展示内容审核流程
- **端到端演示**：输入一个商品链接 → 1-2分钟产出完整穿搭图文
- **展示效果数据**（可模拟）：对比不同风格的互动率差异

### 10.3 面试官常见问题的准备

| 问题         | 回答要点                                       |
| ---------- | ------------------------------------------ |
| 为什么不做真人博主？ | 成本优势（零拍摄、24h生产）、可复制（多账号矩阵）、精准可控（人设+数据驱动）   |
| 和竞品差异在哪？   | Ribbi是通用平台，我们是垂直赛道深度Agent；体型穿搭约束是核心壁垒      |
| 如何保证内容质量？  | 人工审核环节 + PerformanceTracker反馈 + Prompt持续迭代 |
| 技术难点在哪？    | 虚拟博主形象一致性控制、穿搭合理性与体型约束的平衡、小红书反爬策略          |
| 下一步规划？     | 多账号矩阵、ComfyUI替代API降低成本、接入小红书开放平台API        |

---

## 11. 风险与后续规划

### 11.1 MVP 阶段的风险

| 风险           | 等级  | 应对策略                         |
| ------------ | --- | ---------------------------- |
| 小红书反爬策略      | 中   | MVP阶段可手动复制热搜数据，或使用RSS/第三方数据源 |
| 图片生成质量不稳定    | 中   | 增加生图质量自动检测 + 每次多生成几张供人工挑选    |
| 虚拟博主形象不够一致   | 中   | 固定Prompt中的面部描述模板 + 使用seed参数  |
| LLM API 调用失败 | 低   | 重试机制 + 降级策略（换模型）             |
| 项目延期         | 低   | 3周预留 buffer，第3周后半段为缓冲期       |

### 11.2 后续迭代方向（V1.0+）

| 阶段         | 目标       | 核心功能                           |
| ---------- | -------- | ------------------------------ |
| V1.0 (MVP) | 单博主单链路跑通 | 6个Skill + 管理后台，本期交付            |
| V1.5       | 质量与效率提升  | ComfyUI自部署降成本、多博主人物一致性模型（LoRA） |
| V2.0       | 多账号矩阵    | 支持多个虚拟博主（不同人设/体型/风格），批量内容生产    |
| V2.5       | 全自动运营    | 定时自动生成发布、A/B测试不同风格、智能选品        |
| V3.0       | SaaS化    | 多租户、创作者工具平台、对接小红书开放API         |

---

## 附录

### A. 目录结构（工程师脚手架）

```
xiaohongshu-agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI 入口
│   ├── config.py              # 配置管理
│   ├── models.py              # SQLite 数据模型
│   ├── database.py            # DB 连接与初始化
│   ├── skills/                # 六大 Skill 模块
│   │   ├── __init__.py
│   │   ├── base.py            # Skill 基类
│   │   ├── trend_radar.py
│   │   ├── product_matcher.py
│   │   ├── outfit_composer.py
│   │   ├── image_generator.py
│   │   ├── content_writer.py
│   │   └── performance_tracker.py
│   ├── pipeline.py            # Skill 编排调度
│   ├── trend_sources.py       # collector 趋势源读取与分类
│   ├── collector/             # 小红书采集器
│   │   ├── client.py          # XHS API 签名请求
│   │   ├── runner.py          # 采集编排、多排序候选池、去重
│   │   ├── ranking.py         # 一周内赞/评/藏 TopN 筛选
│   │   ├── candidates.py      # 多排序候选池合并
│   │   ├── browser.py         # Playwright 扫码登录
│   │   └── store.py           # observation 落库与导出
│   ├── llm_client.py          # LLM API 封装
│   ├── routes/                # API 路由
│   │   ├── __init__.py
│   │   ├── generate.py
│   │   ├── posts.py
│   │   └── trends.py
│   └── templates/             # 管理后台页面模板
│       ├── base.html
│       ├── index.html
│       ├── post_detail.html
│       └── trends.html
├── tests/                     # 测试
├── scripts/
│   ├── collector_to_trends.py # observation 聚合为 source_collector_trends.csv
│   └── process_trends.py      # TrendRadar 输入检查表导出
├── data/                      # 商品库CSV、persona、collector 趋势输出
│   ├── source_collector_trends.csv
│   └── trends_normalized.csv
├── storage/                   # 生成的图片
│   └── images/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### B. 关键 API Key 清单

| 服务 | 用途 | 获取方式 |
| ---- | ---- | ---- |
| OpenAI-compatible Images API | 虚拟博主穿搭图片生成 | OpenAI 或兼容图片模型服务 |
| 小红书登录态 | collector API 采集和扫码刷新 `storage_state.json` | Playwright 扫码登录或 `XHS_COOKIE` |
| OpenAI-compatible Chat API（可选） | 兼容旧脚本/后续增强，不是当前生文必需项 | OpenAI 或兼容文本模型服务 |

> 当前 ProductMatcher、OutfitComposer、ContentWriter、PerformanceTracker 均为本地策略实现；图片生成仍需要 `IMAGE_API_KEY / IMAGE_BASE_URL / IMAGE_MODEL`。

### C. 虚拟博主人设模板

```yaml
name: "小鹿学姐"        # 小红书风格的昵称
age_range: "25-30"
body_type: "大码"       # 或 "小个子(155cm)"
size_category: "XL-2XL" # 或 "XS-S"
height: "165cm"         # 小个子设为 "152cm"
style_tags:
  - "法式优雅"
  - "通勤穿搭"
  - "温柔系"
tone_of_voice: "亲切温柔，像闺蜜推荐，常用'姐妹们''绝绝子'"
avatar_desc: >
  圆脸、温柔杏眼、长发微卷、暖白皮、
  气质优雅、微笑自然
content_focus:
  - "大码显瘦穿搭"
  - "微胖女生职场穿搭"
  - "法式氛围感搭配"
avoid_tags:
  - "紧身包臀"
  - "低腰"
  - "横条纹"
```

---

> **文档版本**: v1.0  
> **最后更新**: 2026-04-28  
> **作者**: AI产品经理实战项目  
> **工程师协作方**: Python全栈工程师
