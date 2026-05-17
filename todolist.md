# AI 穿搭博主 Agent - 待办清单

> 更新：2026-05-17  
> 当前状态：已完成趋势源重构、生文链路本地化、项目级 skill 封装、路由测试修复。全量测试 `33 passed`。

---

## 一、已完成

| 工作项 | 产出 |
|--------|------|
| 项目级 Agent Skill 封装 | `skills/xiaohongshu-fashion-agent/` |
| Skill 中文文档 | `SKILL.md`、`references/workflow.md`、`references/trend-data-contract.md` |
| 趋势源读取重构 | `app/trend_sources.py` |
| TrendRadar 从三张源表读取趋势 | `app/skills/trend_radar.py` |
| 废弃 `strategy_full.csv` 主流程依赖 | `scripts/process_trends.py` 改为归一化检查脚本 |
| 生文链路取消必需文本模型 API | `ProductMatcher`、`OutfitComposer`、`ContentWriter`、`PerformanceTracker` |
| 配置移除文本模型必需项 | `app/config.py` |
| Pipeline 适配本地 skill 逻辑 | `app/pipeline.py` |
| 路由测试卡住问题修复 | async route、async `get_db`、`httpx.ASGITransport` 测试 fixture |
| 全量测试通过 | `pytest -q`，33 passed |

---

## 二、P0 待办

### 1. 商品库扩充到 30+ 件

编辑 `data/products.csv`，重点补充：

| 字段 | 要求 |
|------|------|
| `name` | 商品名称具体可识别 |
| `category` | 上衣、下装、裙装、外套、鞋包配饰等 |
| `attributes` | 至少包含颜色、材质、版型 |
| `style` | 与趋势方向一致，如法式、通勤、韩系、温柔、显瘦 |
| `images` | 真实商品参考图，供图生图使用 |

建议覆盖：

- 上装 8-10 件
- 下装 6-8 件
- 连衣裙/半身裙 6-8 件
- 外套 4-6 件
- 鞋包配饰 4-6 件

### 2. 博主形象一致性

当前 `avatar_desc` 对图片模型约束较弱。需要补充：

- `data/avatar_prompts/{persona_name}.txt`：英文精细人设 prompt
- `data/avatar_refs/{persona_name}.png`：面部参考图
- `BloggerPersona` 或配置中增加 `avatar_ref`
- `ImageGenerator` 支持面部参考图 + 商品参考图策略

### 3. 趋势采集适配器

当前运行时只要求三张源表：

- `data/source_hot_search.csv`
- `data/source_topic_total.csv`
- `data/source_topic_inc.csv`

下一步可以新增爬虫或手工导入适配器，但输出必须保持这三张表的字段契约。

### 4. 文案质量优化

生文不再调用独立文本模型 API，优化方向应放在本地策略：

- 建立 `docs/content_style_guide.md`
- 建立 `data/banned_words.txt`
- 采集真实优秀笔记样本，提炼标题结构、正文结构、标签组合
- 将规则沉淀到 `ContentWriter` 或 skill reference，而不是重新引入必需 LLM API

### 5. 审核标准文档

新增文档：

- `docs/image_quality_checklist.md`
- `docs/content_quality_checklist.md`
- `docs/outfit_quality_checklist.md`

用于人工审核和后续自动评分。

---

## 三、P1 待办

### 1. 新增博主人设

在 `data/persona.yaml` 基础上扩展：

| 人设 | 体型 | 风格 | 目标人群 |
|------|------|------|----------|
| 小鹿学姐 | 大码 XL-2XL | 法式/通勤/温柔 | 微胖职场女性 |
| 米米姐姐 | 小个子 153cm | 韩系/甜美/显高 | 小个子学生/职场 |
| 七七学姐 | 标准微胖 | 平价/休闲/国潮 | 学生党/预算有限 |

每个人设需要包含：

- `style_tags`
- `tone_of_voice`
- 英文 `avatar_desc`
- `content_focus`
- `avoid_tags`
- `avatar_ref`

### 2. ImageGenerator 并发和候选图筛选

目标：

- 多张图并发生成，减少等待时间。
- 生成多于需求数量的候选图。
- 增加基础质量筛选后再返回 `num_images` 张。

### 3. Pipeline 声明式配置

新增 `config/pipeline.yaml`，让步骤顺序、输入映射和可开关能力可配置。

### 4. 管理后台增强

建议增加：

- 生成过程日志
- 趋势命中解释
- 商品匹配理由展示
- 人工审核备注
- 一键重新生成文案/图片

### 5. 表现反馈闭环

完善 `PerformanceTracker`：

- 按风格、人群、品类聚合表现。
- 反向影响下一轮 trend/product/content 排序。
- 在后台展示推荐调整建议。

---

## 四、长期方向

1. 小红书趋势爬虫：只负责采集和落三张源表。
2. 多博主矩阵：不同 persona 对应不同商品池和内容策略。
3. 自动发布：接入发布前审核队列和发布记录。
4. A/B 测试：标题、首图、标签组合多版本比较。
5. 内容资产库：沉淀高表现图文模板和失败案例。
