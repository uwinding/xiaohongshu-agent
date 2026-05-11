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

| 痛点 | 描述 | 机会 |
|------|------|------|
| **内容生产门槛高** | 真人博主需要拍摄、修图、写文案，单篇内容耗时2-3小时 | AI 自动化可降低 90% 生产时间 |
| **人设一致性难维持** | 真人博主体型/肤色/风格固定，难以覆盖多元受众 | AI 虚拟博主可定制人设，精准匹配细分人群 |
| **选品效率低** | 博主手动筛选商品、搭配试穿，匹配效率差 | Agent 自动匹配商品库，按人设推荐搭配 |
| **数据反馈慢** | 真人凭经验调整内容策略，缺乏系统数据驱动 | PerformanceTracker 自动追踪效果，数据驱动优化 |
| **大码/小个子人群被忽视** | 主流穿搭博主以标准身材为主，大码/小个子用户缺乏参考 | 精准切入细分人群，信任度高，转化率更好 |

### 1.2 细分赛道选择：女装 + 大码/小个子 + 特定风格

- **大码女装**：淘宝/小红书大码女装年增速 30%+，用户强需求但优质内容供给不足
- **小个子穿搭**：155cm 以下用户是小红书穿搭搜索高频词，"小个子显高"笔记互动率高
- **特定风格**：法式/韩系/国潮/通勤等风格标签有利于建立差异化人设

### 1.3 竞品参考

| 产品 | 定位 | 差异化 |
|------|------|--------|
| Ribbi | 通用创意 AI Agent，多技能模块 | 我们的 Agent 聚焦单一垂直赛道，深度更深 |
| 小红书AI创作工具 | 平台内置AI辅助写文案 | 不具备穿搭理解能力，无法端到端生成图文 |
| 淘宝AI试穿 | 电商侧虚拟试穿 | 不产出小红书风格内容，缺乏社交传播属性 |

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

### 3.1 Pipeline 6 步流程

```
[1/6] 加载博主人设 (Persona)
          │
[2/6] TrendRadar — 趋势分析
       │ 读 strategy_full.csv → 按人设匹配 → 三流输出
       │
       ├── product_hints ──────────┐
       ├── style_directions ───────┤
       └── topic_tags ─────────────┤
                                    ▼
[3/6] ProductMatcher — 商品匹配
       │ 三层匹配：品类趋势 × 风格兼容 × 人设体型
       │ → 排除风格冲突的商品，优先趋势品类
       │
       ▼
[4/6] OutfitComposer — 穿搭方案生成
       │ 趋势风格方向驱动，生成 outfit + pos/neg prompt + scene
       │
       ▼
[5/6] ImageGenerator — AI 生图（SKU 级保真）
       │ 参考商品图(img2img) + 固定 seed + 竖图尺寸(1024x1536)
       │
       ▼
[6/6] ContentWriter — 文案写作
       │ 穿搭描述 + 商品链接 + topic_tags 热门话题标签
       │
       ▼
  输出：完整穿搭图文 (标题 + 正文 + 3-4张图 + 商品标记 + 话题标签)
```

### 3.2 Skill 模块总览

```
┌──────────────────────────────────────────────────────────────────┐
│                       AI 穿搭博主 Agent                           │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    GenerationPipeline                      │    │
│  │  1.Load  →  2.TrendRadar  →  3.ProductMatcher             │    │
│  │         →  4.OutfitComposer  →  5.ImageGenerator           │    │
│  │         →  6.ContentWriter                                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │TrendRadar│  │Product   │  │Outfit    │  │Image     │         │
│  │ 趋势雷达  │  │Matcher   │  │Composer  │  │Generator │         │
│  │CSV读取   │  │ 三层匹配  │  │ 风格驱动  │  │图生图保真 │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                   │
│  ┌──────────┐  ┌────────────────────────────────────┐            │
│  │Content   │  │  PerformanceTracker                 │            │
│  │Writer    │  │  数据追踪 + 反馈优化                  │            │
│  │标签多维  │  └────────────────────────────────────┘            │
│  └──────────┘                                                    │
│                                                                   │
├───────────────────────────────────────────────────────────────────┤
│                Python FastAPI 调度编排层                           │
├───────────────────────────────────────────────────────────────────┤
│          SQLite 存储  │  本地文件系统（图片存储）                    │
├───────────────────────────────────────────────────────────────────┤
│  DeepSeek-v4 (LLM)  │  Seedream 4.5 (生图, 支持图生图)          │
├───────────────────────────────────────────────────────────────────┤
│   离线趋势数据 (strategy_full.csv)  │  商品库 (products.csv)       │
│   三源CSV → 生成分析 → 84关键词    │  style字段 → 风格过滤        │
└───────────────────────────────────────────────────────────────────┘
```

### 3.3 架构设计原则

- **趋势驱动**：TrendRadar 输出三流数据（选品/风格/标签），全程引导下游 Skill 决策
- **风格一致性**：商品 `style` 字段 → ProductMatcher 过滤 → OutfitComposer 创作 → 全链路风格统一
- **SKU 保真**：商品图作为参考输入 Seedream 图生图，靠近真实商品外观
- **模块化**：每个 Skill 独立可测、可替换，遵循 BaseSkill 统一接口
- **轻量化**：MVP 不引入 LangChain 等重框架，纯 Python 函数串联

---

## 4. 六大 Skill 详细设计

### 4.1 TrendRadar — 趋势雷达

**职责**：从 `data/strategy_full.csv` 读取预计算趋势数据，按博主人设匹配过滤，按 `recommend_for` 字段分流给三个下游 Skill（ProductMatcher / OutfitComposer / ContentWriter）。

> **实现方式**：趋势数据由 `scripts/comprehensive_analysis.py` 从三个源 CSV 离线计算生成，TrendRadar 不再依赖在线爬虫。

#### 数据源（离线处理 → strategy_full.csv）

| 数据源 | CSV 文件 | 频次 | 信号含义 | 适合指导 |
|--------|---------|------|---------|---------|
| **热词榜**（搜索指数 + 飙升标记） | `source_hot_search.csv` | 周 | **需求信号** — 用户在主动搜什么 | 商品选品、品类覆盖 |
| **话题增量榜**（浏览量 + 参与人数） | `source_topic_inc.csv` | 日 | **动量信号** — 什么内容正在起势 | 风格方向、早期趋势发现 |
| **话题总量榜**（浏览量 + 参与人数） | `source_topic_total.csv` | 日 | **存量信号** — 什么内容已被大量消费 | 赛道规模评估、成熟度判断 |

> PM 更新流程：从灰豚数据/千瓜导出三个榜单 → 覆盖 `data/source_*.csv` → 运行 `python scripts/comprehensive_analysis.py` → `strategy_full.csv` 自动更新

#### 趋势生命周期模型（双维度判定）

由 `comprehensive_analysis.py` 计算，同时考虑增量占比和总量规模：

| 阶段 | 增量占比 | 总量浏览量 | 信号特征 |
|------|---------|-----------|---------|
| **爆发期** | > 1.5% | > 500亿 | 高增长 + 大市场，最佳切入窗口 |
| **增长期** | 0.5 ~ 1.5% | 100 ~ 500亿 | 稳定增长，适合抢占风格标签 |
| **萌芽期** | > 0.5%（或仅有增量） | < 100亿 | 早期趋势，可试探性布局 |
| **成熟期** | < 0.5% | > 100亿 | 市场饱和，竞争激烈 |
| **需求期** | 无增量数据 | 仅有搜索量 | 有搜索需求但缺内容供给，选品机会 |
| **观察** | 仅有总量数据 | 有总量 | 存量市场，需观察增量信号 |

#### 判定公式

```
增量占比(%) = 增量浏览量(万) ÷ 总量浏览量(万) × 100

参与率(%) = 参与人数(万) ÷ 浏览量(万) × 100
  → 衡量话题互动黏性，> 0.05% 为高参与率

竞争度(%) = 该词浏览量 ÷ 同子类总浏览量 × 100
  → < 10% 为竞争分散(蓝海)，> 30% 为竞争集中(红海)
```

#### recommend_for 路由逻辑

`strategy_full.csv` 中每条关键词的 `recommend_for` 字段决定其下游路由：

| recommend_for | 路由目标 | 分类依据 |
|--------------|---------|---------|
| **选品** | ProductMatcher | 品类参考词、或 search_index > 100w |
| **综合** | ProductMatcher + ContentWriter | 选品词同时有高增量和高参与率 |
| **风格** | OutfitComposer | 风格/人群/概念分类（不受 lifecycle 限制），以及增长/萌芽期的季节/场景词 |
| **标签** | ContentWriter | 灵感类、观察期的场景词等 |

> **关键规则**：风格/人群类关键词始终路由到「风格」，不因生命周期阶段降级。例如 `高级感穿搭`（萌芽期）、`休闲穿搭`（观察期）仍输出给 OutfitComposer 做风格方向。

#### TrendRadar 输出结构

读取 `strategy_full.csv` → 按博主人设的 `style_tags` 和 `body_type` 匹配相关行 → 按 `recommend_for` 分流输出：

```json
{
  "product_hints": [
    {"keyword": "短袖", "priority": "高", "search_index_w": 273.4, "lifecycle": "萌芽期", "action": "优先备货：短袖..."}
  ],
  "style_directions": [
    {"keyword": "通勤穿搭", "priority": "中", "inc_ratio": 1.04, "lifecycle": "增长期", "action": "穿搭方向：通勤穿搭..."},
    {"keyword": "高级感穿搭", "priority": "中", "inc_ratio": 0.58, "lifecycle": "萌芽期"}
  ],
  "topic_tags": [
    {"keyword": "夏季穿搭", "priority": "高", "category": "季节"},
    {"keyword": "微胖穿搭", "priority": "中", "category": "人群"},
    {"keyword": "韩系穿搭", "priority": "中", "category": "风格"},
    {"keyword": "裙子", "priority": "高", "category": "品类参考"}
  ],
  "trend_summary": "当前最佳窗口：夏季穿搭（增长期，搜索846w，增占比0.86%）；高优选品：短袖/裙子/连衣裙..."
}
```

> **ContentWriter 标签策略**：`topic_tags` 不限于 `recommend_for="标签"` 的词，而是返回**所有匹配博主人设的高优先级关键词**（包含风格/人群/选品/标签各类），确保 ContentWriter 能从多维度获选题灵感。

#### 人设匹配规则

| 博主人设 | 体型/风格 | 自动匹配关键词 |
|----------|----------|--------------|
| 小鹿学姐 | 大码/法式/通勤 | 微胖穿搭、通勤穿搭、显瘦穿搭、温柔穿搭、高级感穿搭 |
| 米米姐姐 | 小个子/韩系/甜美 | 小个子穿搭、韩系穿搭、甜妹、梨形身材 |
| 七七学姐 | 学生/平价/休闲 | 平价穿搭、休闲穿搭、女大学生、不费力的穿搭 |

#### 数据文件

`data/strategy_full.csv` — 84个穿搭相关关键词的三榜合并分析表，由 `scripts/comprehensive_analysis.py` 生成。

| 关键字段 | 说明 |
|---------|------|
| keyword | 归一化后的热词 |
| category | 季节/风格/场景/人群/概念/灵感/品类参考 |
| lifecycle | 生命周期阶段（双维度判定） |
| search_index_w | 搜索指数（万），0 表示无搜索数据 |
| inc_ratio_pct | 增量占比(%)，衡量增长动能 |
| competition_pct | 竞争度(%)，同子类中的浏览量占比 |
| priority | 高/中/低（综合评分 ≥5 为高，≥3 为中） |
| recommend_for | 下游路由：选品/风格/标签/综合 |

### 4.2 ProductMatcher — 商品匹配

**职责**：三层匹配（品类趋势 × 风格兼容性 × 人设体型），从商品库中为博主筛选最合适的搭配商品组合。

**设计目的**：解决"选出的商品单品无法搭配出趋势风格"的问题。每件服饰单品都有自身的风格属性（如碎花裙=田园风），不能适配所有穿搭方向。通过引入 `style` 字段和三层匹配，确保选出的商品可以用于 OutfitComposer 创作目标风格。

#### 三层匹配模型

```
输入商品列表
      │
      ▼
第一层：品类趋势匹配（来自 TrendRadar.product_hints）
  商品品类命中趋势品类（如"裙子"在热搜） → match_score +2
  商品品类无搜索需求 → match_score -1
      │
      ▼
第二层：风格兼容性匹配（来自 TrendRadar.style_directions）← 新增
  商品 style 标签与趋势风格方向兼容 → match_score +2
  商品 style 标签与所有趋势方向冲突 → 排除（硬约束）
  双重匹配（一个商品适配多个趋势方向）→ match_score +1
      │
      ▼
第三层：人设体型匹配（已有逻辑）
  版型/尺码/避雷标签 → 硬约束，不满足直接排除
  大码：A字/直筒/阔腿、V领/方领、深色/纯色、避紧身/横条纹/低腰
  小个子：高腰线、短款/九分、同色系、避过长/oversized
      │
      ▼
输出：product_set（按 match_score 排序的搭配组合）
```

#### 数据格式

**商品库新增 `style` 字段**（`data/products.csv`）：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| style | String | 风格标签，多个用 `/` 分隔 | `"通勤/职场"` `"法式/田园"` `"温柔/韩系"` |

> PM 填写的 style 值需与 TrendRadar 的趋势风格方向对齐，支持模糊匹配。

| 维度 | 描述 |
|------|------|
| **输入** | 商品列表（含 style）、博主人设、`product_hints`（趋势品类）、`style_directions`（趋势风格） |
| **处理逻辑** | LLM 在 trend 上下文中执行三层匹配 → 每件商品标注 match_score + trend_bonus + 淘汰理由 |
| **输出** | `{ product_set: [...], overall_match_score, style_match, trend_alignment: "命中X/Y趋势品类" }` |
| **PM 交付物** | ProductMatcher System Prompt、商品 style 标签规范、体型穿搭规则库 |

### 4.3 OutfitComposer — 穿搭合成

**职责**：根据匹配商品、博主人设和趋势风格方向，创作穿搭方案并生成 AI 生图 Prompt。

**设计目的**：替代之前"盲猜"风格的 scene/style 参数。由 TrendRadar 输出的 `style_directions` 驱动穿搭风格选择，确保生成内容的风格紧跟小红书当前趋势。

#### 风格方向选择策略

```
输入 style_directions
      │
      ▼
优先级排序：
  1. 竞争度最低的增长期方向（蓝海优先抢占）→ 权重最高
  2. 与博主原生风格标签重叠的方向 → 权重其次
  3. 高竞争度的成熟期方向 → 权重最低
      │
      ▼
合成最终方向：
  趋势方向 × 博主原生标签 × 商品风格
  例：通勤穿搭(趋势) × 法式优雅(博主) × 温柔系(博主)
      → "法式通勤温柔系"
      │
      ▼
自动生成 scene：
  从趋势方向中衍生场景描述
  通勤 → "高层写字楼走廊/晨光柔和"
  法式 → "梧桐树下的咖啡馆/暖色调"
      │
      ▼
生成 pos_prompt（英文）：
  必须包含趋势风格关键词 + 博主一致性描述 + 品类描述
```

| 维度 | 描述 |
|------|------|
| **输入** | `product_set`（已过滤风格冲突）、博主人设、`style_directions`（趋势风格方向） |
| **处理逻辑** | 从 style_directions 中按优先级选 1-2 个方向 → 结合博主原生风格合成 → 自动推导 scene → 生成中英文 Prompt |
| **输出** | `{ outfit_desc, pos_prompt, neg_prompt, scene, style_direction: "通勤穿搭×温柔穿搭" }` |
| **PM 交付物** | OutfitComposer System Prompt、风格方向匹配规则、场景模板库 |

### 4.4 ImageGenerator — SKU 级保真图片生成

**职责**：调用 Seedream 图生图 API，以商品参考图为输入，生成博主穿着该商品的穿搭照片。保证博主形象一致性（固定 seed）+ 服装接近真实商品外观（img2img）。

**设计目的**：这是项目的核心重点之一。通用文生图模型无法精确还原特定 SKU 的服装细节（花纹、材质、版型）。通过 Seedream 的「参考图 + 文本提示词」能力，商品图作为视觉参考，文本 Prompt 描述穿搭场景和博主形象，结合固定 seed 维持博主面容一致。

#### 图生图流程

```
商品参考图（来自 products.csv 的 images 字段）
      │
      ▼
_encode_ref_image(): URL/本地路径 → base64 data URL
      │
      ▼
Seedream API:
  POST images/generations
  {
    "model": "doubao-seedream-4-5-251128",
    "prompt": "A plus-size woman wearing a blue floral dress...",
    "n": 1,
    "size": "1024x1536",
    "image": "data:image/png;base64,...",   ← 参考图
    "seed": 123456789,                       ← 固定种子（按博主人设）
    "watermark": false
  }
      │
      ▼
seed 管理：
  seed = hash(persona_name) → 同博主多篇笔记复用
  → 博主面容跨次生成保持一致
      │
      ▼
批量生成：逐张调用（每次 n=1, 保证质量）
  单篇生成 3-4 张，每张可传不同参考图
```

#### 三层保真策略

| 层级 | 保真要求 | 实现方式 | 当前可实现 |
|------|---------|---------|-----------|
| **风格层** | 画面体现趋势风格方向 | Prompt 写入风格关键词 | ✅ |
| **品类层** | 品类大致匹配（连衣裙/阔腿裤） | Prompt 描述品类 | ✅ |
| **SKU 层** | 服装接近真实商品外观 | 参考图 img2img | ✅ Seedream 支持 |
| **精确层** | 100% 还原 SKU 细节 | LoRA 微调 / 换装模型 | ❌ V2.0 |

#### 降级策略

```
有参考图 → 图生图模式（img2img + prompt）
无参考图 → 纯文生图模式（prompt only）
文生图失败 → 返回错误 + 详细日志
```

| 维度 | 描述 |
|------|------|
| **输入** | `pos_prompt`、`neg_prompt`、`persona_avatar`、`reference_images`（商品参考图 URL 列表）、`persona_name`（用于 seed）、`num_images` |
| **处理逻辑** | 加载首张有效参考图 → 计算 persona seed → 调用 Seedream img2img → 下载图片 → 本地存储 |
| **输出** | `{ image_paths: [...], num_generated, prompt_used, seed }` |
| **一致性策略** | seed = hash(persona_name)，同博主可跨次生成同一面容；竖图尺寸 1024x1536 |
| **工程师实现要点** | OpenAI 兼容 API 通过 `extra_body` 传 `image` 和 `seed`；参考图加载支持 URL + 本地路径 + base64 |

### 4.5 ContentWriter — 文案写作

**职责**：根据穿搭方案、商品信息和趋势数据，生成小红书风格图文文案。

| 维度 | 描述 |
|------|------|
| **输入** | 穿搭描述 `outfit_desc`、商品列表、博主人设、`topic_tags`（TrendRadar 输出的全维度热门标签，含风格/人群/选品/标签各类） |
| **处理逻辑** | LLM 生成小红书爆款风格的标题 → 正文（穿搭心得+单品亮点+购买理由） → 从 `topic_tags` 中选取最匹配的话题标签 → 商品标记信息 |
| **输出** | `{ title: string, content: string, hashtags: [], product_tags: [{name, url}] }` |
| **文案风格** | 口语化、亲切感、emoji点缀、像真人分享而非营销号；大码强调"显瘦""自信"，小个子强调"显高""比例" |
| **话题标签策略** | 不限于单一类别：从 TrendRadar 提供的 `topic_tags` 中，按优先级选取风格标签（如 #高级感穿搭）+ 人群标签（如 #微胖穿搭）+ 品类标签（如 #连衣裙）组合使用，每篇 5-8 个标签 |
| **PM 交付物** | ContentWriter System Prompt、文案风格规范、爆款标题公式库、话题标签策略 |

### 4.6 PerformanceTracker — 数据追踪

**职责**：追踪已发布内容的表现数据，生成优化建议反馈给其他 Skill。

| 维度 | 描述 |
|------|------|
| **输入** | 笔记ID、手动录入/模拟的数据（MVP阶段不接入小红书官方API） |
| **处理逻辑** | 记录互动数据 → 分析哪些风格/话题/时间段表现好 → LLM 生成优化建议 |
| **输出** | `{ performance_report: {}, optimization_suggestions: [] }` |
| **反馈链路** | 风格偏好 → 影响 TrendRadar 权重；时间偏好 → 影响发布时间策略；商品转化 → 影响 ProductMatcher 选品偏好 |
| **PM 交付物** | 效果评估指标体系、优化策略规则、数据看板设计需求 |

---

## 5. 技术栈

| 层 | 选型 | 说明 |
|---|------|------|
| **后端框架** | Python 3.11+ / FastAPI | 异步支持好，适合 API 编排 |
| **LLM** | DeepSeek-v4-flash (via opencode.ai) | 统一处理文案、穿搭合成、趋势分析 |
| **图片生成** | doubao-seedream-4-5-251128 (火山方舟) | 支持文生图 + 图生图（img2img），实现 SKU 级保真 |
| **数据存储** | SQLite (SQLAlchemy ORM) | 轻量零运维，后期可迁移 PostgreSQL |
| **图片存储** | 本地文件系统 | 按日期目录组织，MVP 够用 |
| **前端(管理后台)** | FastAPI + Jinja2 模板 | 极简 Web 页面，不引入前后端分离 |
| **趋势分析** | 离线计算 (Python 脚本) | 三个源 CSV → comprehensive_analysis.py → strategy_full.csv |
| **部署** | Docker + docker compose | 一键启动 |

### 不选用的技术（MVP 阶段）

| 技术 | 不选原因 |
|------|---------|
| LangChain / LlamaIndex | 过度工程化，简单函数串联即可 |
| ComfyUI / Stable Diffusion | 需要 GPU，部署复杂，Seedream API 替代 |
| Redis / Celery | 不需要异步任务队列，MVP 同步调用即可 |
| React / Vue 前端 | 管理后台用模板渲染足够 |
| PostgreSQL | SQLite 对单机 MVP 完全够用 |

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
│  source_url, attributes{}, style, images[]           │
└─────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │     Trend        │
                    │ keyword, category│
                    │ hot_score, date   │
                    └──────────────────┘
```

### 6.2 数据流向

```
                         ┌──────────────────────────────┐
                         │  strategy_full.csv (84关键词)  │  ← 离线计算
                         │  product_hints / style_directions / topic_tags
                         └──────────────┬───────────────┘
                                        │
                                        ▼
[外部输入]                      [Agent Pipeline — 6步骤]                   [输出]

商品库(products.csv) ──┐
  style + images        │
                        ├──→ [1] 加载博主
博主人设(persona.yaml) ─┘        │
                                  ▼
                         [2] TrendRadar
                           │  读 CSV → 按人设匹配
                           │  输出三流数据
                           │
                  ┌────────┼────────┐
                  │        │        │
          product_hints  style_    topic_tags
                  │    directions     │
                  ▼        │          │
                         [3] ProductMatcher
                           │  三层匹配（品类×风格×体型）
                           │  排除风格冲突商品
                           ▼
                         [4] OutfitComposer
                           │  趋势方向驱动穿搭创作
                           │  生成 outfit + prompt + scene
                           ▼
                    ┌──────┴──────┐
                    │ 商品参考图    │
                    ▼              │
                         [5] ImageGenerator
                           │  img2img → SKU级保真
                           │  固定seed → 面容一致
                           │  竖图1024x1536
                           ▼
                         [6] ContentWriter ────────────▶ 小红书图文
                           │  topic_tags → 多维标签        (标题+正文+图片+商品标记)
                           │  文字描述精确商品
                           ▼
                      [人工审核页面]
                           │
                     发布 ◀─┘
                           │
                    [PerformanceTracker]
                           │
                     反馈优化 ◀──┘
```

### 6.3 主要 API 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate` | 提交商品链接，触发完整生成流程 |
| GET | `/api/posts` | 获取生成内容列表（支持状态筛选） |
| GET | `/api/posts/{id}` | 查看单篇生成详情 |
| PATCH | `/api/posts/{id}` | 审核通过/驳回/修改内容 |
| GET | `/api/trends` | 查看最新趋势数据 |
| POST | `/api/trends/refresh` | 手动刷新趋势数据 |
| GET | `/api/performance/{id}` | 查看单篇发布效果 |
| GET | `/` | 管理后台页面 |

---

## 7. 工作拆分（PM vs 工程师）

### 7.1 产品经理（你）负责

| 工作项 | 产出物 | 工作量 |
|--------|--------|--------|
| **赛道分析文档** | 小红书穿搭赛道竞品分析、用户画像、痛点总结 | 2天 |
| **博主人设设计** | 虚拟博主完整人设卡（姓名/年龄/体型/风格/口吻/参考形象） | 1天 |
| **Prompt Engineering** | 6个Skill的System Prompt + Few-shot示例 + 输出JSON Schema定义 | 3天 |
| **体型穿搭规则库** | 大码/小个子的穿搭约束规则（版型/颜色/比例/避坑） | 1天 |
| **商品库设计** | 商品筛选标准、搭配规则、初始商品种子库（20+件） | 1.5天 |
| **内容策略规范** | 文案风格指南、标题公式库、话题标签策略、发布时间建议 | 1天 |
| **质量审核标准** | 生图质量CheckList、内容审核维度、通过/驳回标准 | 0.5天 |
| **效果评估体系** | KPI定义（互动率/点击率/转化率）、优化策略规则 | 0.5天 |
| **面试汇报文档** | PRD摘要、项目汇报PPT、Demo演示脚本 | 2天 |

### 7.2 工程师负责

| 工作项 | 产出物 | 工作量 |
|--------|--------|--------|
| **项目脚手架** | FastAPI项目结构、SQLite数据模型定义、配置文件、环境变量模板 | 1天 |
| **LLM API 封装层** | 统一的LLM调用类（支持GPT-4o/Claude切换）、重试/超时机制 | 1天 |
| **TrendRadar代码** | 小红书搜索页爬虫 + LLM趋势分析调用 + 数据存储 | 1.5天 |
| **ProductMatcher代码** | 商品属性解析 + LLM匹配逻辑 + 搭配合理性校验 | 1.5天 |
| **OutfitComposer代码** | LLM穿搭合成 + Prompt生成 + JSON结构化输出 | 1天 |
| **ImageGenerator代码** | DALL-E/Gemini API封装、图片下载存储、批量生成、基础质量检查 | 1.5天 |
| **ContentWriter代码** | LLM文案生成 + 话题标签自动匹配 + 商品标记格式化 | 1天 |
| **Pipeline编排** | Skill串联调度 + 中间结果缓存 + 错误处理与回退 | 1天 |
| **管理后台页面** | FastAPI+Jinja2 页面：内容列表、详情查看、审核操作、手动触发生成 | 2天 |
| **SQLite CRUD** | 所有数据模型的增删改查接口 | 1天 |
| **Docker部署** | Dockerfile + docker-compose + 启动脚本 | 0.5天 |
| **联调测试** | 与PM联调Prompt效果、全链路测试 | 1天 |

### 7.3 协作重叠区

- API Key 申请与管理（GPT-4o/DALL-E/Gemini 等）
- 每个 Skill 的 Prompt 调优（PM写初版 → 工程师接入 → 联调迭代）
- 全链路效果验收（PM定义标准 → 工程师修复问题）

---

## 8. 项目排期（3周）

### Week 1：基础搭建 + 前半链路

| 天 | PM | 工程师 |
|----|-----|--------|
| Day 1-2 | 赛道分析文档 | 项目脚手架 + SQLite数据模型 |
| Day 3 | 博主人设设计 | LLM API封装层 + 配置文件 |
| Day 3-4 | TrendRadar Prompt + 规则 | TrendRadar 爬虫 + LLM调用 |
| Day 4-5 | ProductMatcher Prompt + 规则 | ProductMatcher 代码 |
| **Week 1 里程碑** | ✅ 赛道文档 + 人设卡完成 | ✅ 脚手架 + TrendRadar + ProductMatcher 可跑 |

### Week 2：核心内容生成链路

| 天 | PM | 工程师 |
|----|-----|--------|
| Day 1-2 | OutfitComposer Prompt + 模板库 | OutfitComposer 代码 |
| Day 2-3 | ImageGen 质量标准 + 参考板 | ImageGenerator API封装 + 图片存储 |
| Day 3-4 | ContentWriter Prompt + 文案指南 | ContentWriter 代码 |
| Day 4-5 | 商品库建设 + 审核标准 | Pipeline串联 + SQLite CRUD |
| **Week 2 里程碑** | ✅ 完整Prompt体系 + 商品库 | ✅ 端到端生成链路跑通 |

### Week 3：闭环收尾 + 展示准备

| 天 | PM | 工程师 |
|----|-----|--------|
| Day 1 | PerformanceTracker 策略 + 指标体系 | PerformanceTracker 代码 |
| Day 1-2 | 内容审核 + 效果验收 | 管理后台页面 |
| Day 3 | 面试汇报文档 | Docker部署 |
| Day 3-4 | Demo演示脚本 | 联调 + Bug修复 |
| Day 4-5 | 文档最终整理 | 最终优化 |
| **Week 3 里程碑** | ✅ 完整项目文档 + Demo | ✅ Docker一键部署 + 管理后台可用 |

---

## 9. 与 Ribbi 的对比与优化点

### 9.1 Ribbi 的核心特点

Ribbi 是一个 **"Self-Evolving Creative AI Agent"**，其核心设计理念：

- **多技能模块化**：Creators 可以组合不同 Skill 完成复杂创意任务
- **社交与电商打通**：从趋势发现 → 内容生成 → 发布追踪 → 效果优化，全链路覆盖
- **自进化学习**：根据使用数据和效果反馈，持续优化内容质量

### 9.2 本项目借鉴 Ribbi 的设计

| Ribbi 特点 | 本项目对应设计 |
|------------|---------------|
| 模块化 Skill 系统 | 6个独立 Skill，每个可独立调用和替换 |
| 社交内容生成 | ContentWriter + ImageGenerator 产出小红书图文 |
| 电商产品图生成 | ProductMatcher + OutfitComposer 实现商品到穿搭的转化 |
| 效果追踪优化 | PerformanceTracker 闭环反馈 |
| 人设一致性 | BloggerPersona 贯穿全链路 |

### 9.3 相比 Ribbi 的差异化优化

| 维度 | Ribbi | 本项目 |
|------|-------|--------|
| **定位** | 通用创意 AI 平台 | 垂直穿搭赛道，深度更深 |
| **人设一致性** | 依赖 Prompt 描述 | 系统性 Persona 体系 + 穿搭规则库 |
| **体型适配** | 无特殊处理 | 大码/小个子专属穿搭约束逻辑 |
| **电商深度** | 通用商品图生成 | 从选品→搭配→生图→文案→带货，完整闭环 |
| **数据反馈** | 通用性能追踪 | 穿搭专属指标体系（互动率×风格标签×商品转化） |

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

| 问题 | 回答要点 |
|------|---------|
| 为什么不做真人博主？ | 成本优势（零拍摄、24h生产）、可复制（多账号矩阵）、精准可控（人设+数据驱动） |
| 和竞品差异在哪？ | Ribbi是通用平台，我们是垂直赛道深度Agent；体型穿搭约束是核心壁垒 |
| 如何保证内容质量？ | 人工审核环节 + PerformanceTracker反馈 + Prompt持续迭代 |
| 技术难点在哪？ | 虚拟博主形象一致性控制、穿搭合理性与体型约束的平衡、小红书反爬策略 |
| 下一步规划？ | 多账号矩阵、ComfyUI替代API降低成本、接入小红书开放平台API |

---

## 11. 风险与后续规划

### 11.1 MVP 阶段的风险

| 风险 | 等级 | 应对策略 |
|------|------|---------|
| 小红书反爬策略 | 中 | MVP阶段可手动复制热搜数据，或使用RSS/第三方数据源 |
| 图片生成质量不稳定 | 中 | 增加生图质量自动检测 + 每次多生成几张供人工挑选 |
| 虚拟博主形象不够一致 | 中 | 固定Prompt中的面部描述模板 + 使用seed参数 |
| LLM API 调用失败 | 低 | 重试机制 + 降级策略（换模型） |
| 项目延期 | 低 | 3周预留 buffer，第3周后半段为缓冲期 |

### 11.2 后续迭代方向（V1.0+）

| 阶段 | 目标 | 核心功能 |
|------|------|---------|
| V1.0 (MVP) | 单博主单链路跑通 | 6个Skill + 管理后台，本期交付 |
| V1.5 | 质量与效率提升 | ComfyUI自部署降成本、多博主人物一致性模型（LoRA） |
| V2.0 | 多账号矩阵 | 支持多个虚拟博主（不同人设/体型/风格），批量内容生产 |
| V2.5 | 全自动运营 | 定时自动生成发布、A/B测试不同风格、智能选品 |
| V3.0 | SaaS化 | 多租户、创作者工具平台、对接小红书开放API |

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
├── data/                      # 商品库CSV、初始数据
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
|------|------|---------|
| OpenAI API | GPT-4o (文案+穿搭) + DALL-E 3 (生图) | platform.openai.com |
| 或 Google AI | Gemini (文案、趋势、生图) | aistudio.google.com |
| 或 Anthropic | Claude (文案+穿搭) | console.anthropic.com |

> MVP 阶段推荐全用一家（如 OpenAI）减少接入复杂度。如果成本敏感，可用 Gemini 替代（免费额度充足）。

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
