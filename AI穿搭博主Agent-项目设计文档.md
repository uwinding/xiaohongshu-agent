# AI 虚拟穿搭博主 Agent - 项目设计文档

> 项目定位：面向小红书平台的虚拟穿搭博主 Agent，由 AI 主动管理趋势、选品、搭配、生图、文案和效果反馈，生成可审核的穿搭图文草稿。

---

## 1. 当前产品定义

本项目不是单纯的内容生成脚本，而是一个可被 AI Agent 接管的垂直工作流。仓库内已经包含项目级 skill：

- `skills/xiaohongshu-fashion-agent/SKILL.md`
- `skills/xiaohongshu-fashion-agent/references/workflow.md`
- `skills/xiaohongshu-fashion-agent/references/trend-data-contract.md`

Agent 接入后，应按 skill 文档主动完成：

1. 校验趋势源数据。
2. 按博主人设分析趋势。
3. 从商品库选择搭配商品。
4. 生成穿搭方案和生图提示词。
5. 调用图片生成能力。
6. 生成小红书文案、话题标签和商品标签。
7. 追踪内容表现并给出下一轮优化方向。

---

## 2. 系统架构

### 2.1 六步 Pipeline

```text
[1/6] 加载博主人设 Persona
        |
[2/6] TrendRadar 趋势分析
        | 读取三张趋势源表 -> 归一化 -> 按人设匹配
        | 输出 product_hints / style_directions / topic_tags
        |
[3/6] ProductMatcher 商品匹配
        | 趋势品类 × 风格兼容 × 体型约束 × 避雷标签
        |
[4/6] OutfitComposer 穿搭方案
        | 输出 outfit_desc / pos_prompt / neg_prompt / scene
        |
[5/6] ImageGenerator 图片生成
        | 商品参考图 + 人设描述 + 图片 API
        |
[6/6] ContentWriter 文案生成
        | 标题 + 正文 + hashtags + product_tags
        |
输出：GeneratedPost 草稿 + Outfit + 图片路径 + 趋势上下文
```

### 2.2 模块职责

| 模块 | 文件 | 当前职责 |
|------|------|----------|
| Pipeline | `app/pipeline.py` | 串联六步生成流程，写入 Outfit 和 GeneratedPost |
| TrendSources | `app/trend_sources.py` | 读取三张趋势源 CSV，统一数值单位、分类、计算热度/增长分 |
| TrendRadar | `app/skills/trend_radar.py` | 按人设筛选趋势，输出选品、风格、话题三类信号 |
| ProductMatcher | `app/skills/product_matcher.py` | 本地评分选择 2-4 件搭配商品 |
| OutfitComposer | `app/skills/outfit_composer.py` | 本地生成穿搭描述、场景和英文生图提示词 |
| ImageGenerator | `app/skills/image_generator.py` | 调用图片 API，支持商品参考图和固定人设 seed |
| ContentWriter | `app/skills/content_writer.py` | 本地生成小红书标题、正文、标签和商品标记 |
| PerformanceTracker | `app/skills/performance_tracker.py` | 本地汇总互动表现和下一轮建议 |
| FastAPI Routes | `app/routes/` | 提供生成、帖子、趋势接口 |

---

## 3. 趋势数据方案

### 3.1 已弃用方案

以下方案已弃用，不再作为当前主流程：

- 从灰豚/千瓜手动导出后生成 `strategy_full.csv`
- 依赖 `scripts/comprehensive_analysis.py` 生成预计算策略表
- `TrendRadar` 直接读取 `strategy_full.csv`

### 3.2 当前方案：三张趋势源表

未来无论是手动导入还是爬虫采集，都只需要写入 `data/` 下三张源表。

| 文件 | 字段 | 含义 |
|------|------|------|
| `source_hot_search.csv` | `keyword,search_index_w,is_surging` | 热词榜，代表主动搜索需求 |
| `source_topic_total.csv` | `keyword,views,participants` | 话题总量榜，代表存量内容规模 |
| `source_topic_inc.csv` | `keyword,views,participants` | 话题增量榜，代表近期增长动能 |

`app/trend_sources.py` 负责：

- 合并相同关键词。
- 解析 `w`、`亿`、逗号数字等格式。
- 识别是否飙升。
- 按关键词规则归类为品类、风格、场景、季节、人群、灵感或普通话题。
- 计算 `heat_score` 和 `growth_score`。

`scripts/process_trends.py` 可生成 `data/trends_normalized.csv` 供人工检查，该文件不是运行时必需数据。

---

## 4. 生文策略

当前生文不再配置或调用独立文本模型 API。文本类能力由当前执行项目 skill 的 AI Agent 及仓库内本地逻辑完成。

不应重新引入必需的：

- `llm_api_key`
- `llm_base_url`
- `llm_model`

涉及模块：

- `ProductMatcher`
- `OutfitComposer`
- `ContentWriter`
- `PerformanceTracker`

图片生成仍可通过 `image_api_key`、`image_base_url`、`image_model` 配置外部图片 API。

---

## 5. 数据模型

| 模型 | 用途 |
|------|------|
| `BloggerPersona` | 虚拟博主人设、体型、风格、语气、头像描述、避雷标签 |
| `Product` | 商品库，含品类、价格、品牌、属性、风格、图片 |
| `Outfit` | 一次穿搭方案，含商品 ID、描述、生图提示词和场景 |
| `GeneratedPost` | 生成的小红书草稿，含图片、标题、正文、标签和状态 |
| `PostPerformance` | 发布后的互动数据 |
| `Trend` | 后台趋势展示用模型 |

---

## 6. API 与后台

| 路径 | 说明 |
|------|------|
| `POST /api/generate` | 触发生成流程 |
| `GET /api/posts` | 查看帖子草稿 |
| `PATCH /api/posts/{post_id}` | 更新帖子状态或内容 |
| `GET /api/trends` | 查看趋势记录 |
| `GET /` | 管理后台首页 |
| `GET /post/{post_id}` | 帖子详情页 |
| `GET /trends` | 趋势页 |

路由和数据库依赖已改为 async 形式，避免当前测试环境中 anyio 同步线程池路径卡住。

---

## 7. 测试策略

当前全量测试已通过：

```bash
pytest -q
# 33 passed
```

测试覆盖：

- 数据模型
- 六个 skill
- Pipeline 集成
- FastAPI 路由
- 趋势源读取和归一化

路由测试使用 `httpx.ASGITransport`，避免 `fastapi.testclient.TestClient` 在当前环境卡住。

---

## 8. 后续规划

### P0

1. 扩充商品库到 30+ 件，补足风格、属性和真实商品图。
2. 增加博主英文 Avatar Prompt 和面部参考图，提升人设一致性。
3. 设计爬虫适配器，把小红书趋势数据落到三张源表。
4. 优化本地文案策略，降低模板感和过时口语。
5. 增加图片质量、文案质量、穿搭合理性审核标准。

### P1

1. 新增 2-3 个博主人设，覆盖小个子、学生党、通勤党等人群。
2. 支持 avatar_ref 与商品参考图的双参考图策略。
3. ImageGenerator 并发生成和候选图筛选。
4. Pipeline 声明式配置。
5. 管理后台增加趋势解释、生成过程日志和人工审核备注。

---

## 9. 当前设计原则

- Agent 优先：项目以 skill 形式暴露工作流，让 AI 可以主动维护和执行。
- 趋势源稳定：爬虫、手工导入、第三方数据都统一落三张源表。
- 生文本地化：不依赖独立文本模型 API，避免配置和成本复杂化。
- 图片能力外置：生图仍通过专门图片模型/API 完成。
- 模块可替换：每个 skill 独立输入输出，便于后续替换策略。
- 测试闭环：每次工作流改动必须能通过全量测试。
