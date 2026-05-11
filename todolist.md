# AI 穿搭博主 Agent — 待办清单

> 更新：2026-05-11 ｜ 状态：TrendRadar 策略层已完成，工程优化 + PM 内容层待推进

---

## 一、已完成

| 工作项 | 产出 |
|--------|------|
| strategy_full.csv 数据处理修复（6 个 Bug） | `scripts/comprehensive_analysis.py` |
| 生命周期双维度判定 + 优先级调优 | 高优 1→7, 中优 16→21 |
| recommend_for 路由修复（风格/人群不降级） | 风格路由 20→43 |
| 源数据外置为 3 个可更新 CSV | `data/source_*.csv` |
| TrendRadar 重写（读 CSV → 三流输出） | `app/skills/trend_radar.py` |
| Pipeline 六步流程（TrendRadar 接入主链路） | `app/pipeline.py` |
| ProductMatcher 三层匹配（品类×风格×体型） | `app/skills/product_matcher.py` |
| OutfitComposer 趋势风格驱动 | `app/skills/outfit_composer.py` |
| ImageGenerator SKU 级保真（img2img + seed） | `app/skills/image_generator.py` |
| ContentWriter 全维度标签（topic_tags） | `app/skills/content_writer.py` |
| Product 模型新增 style 字段 | `app/models.py` + `data/products.csv` |
| 设计文档全面更新 | `AI穿搭博主Agent-项目设计文档.md` |
| 全部测试通过 | 33/33 |

---

## 二、产品经理待办

### P0 — 本周

#### 1. 商品库扩充（3 → 30+ 件）

编辑 `data/products.csv`，必填字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 商品名称 | `"高腰A字西装裙 通勤显瘦"` |
| category | 品类 | `裙装 / 裤装 / 上衣 / 外套 / 配饰` |
| price | 价格 | `199` |
| brand | 品牌 | `"某品牌"` |
| size_available | 可选尺码 | `"XL-4XL"` |
| source_url | 商品链接 | `https://...` |
| attributes | JSON | `{"color":"黑色","fabric":"西装料","fit":"A字"}` |
| style | 风格标签 | `"通勤/职场"` `"法式/田园"` `"温柔/韩系"` |
| images | JSON 数组 | `["https://img.example.com/1.jpg","..."]` |

**参考选品方向**（基于 strategy_full 高优品类）：裙子/短袖/连衣裙/外套/裤子/旗袍

**覆盖要求**：上装 8-10 / 下装 6-8 / 连衣裙 6-8 / 外套 4-6 / 配饰 4-6

**style 标签填写规范**：必须与 TrendRadar 的趋势方向对齐：

| 趋势方向 | style 应填值 | 适用商品 |
|---------|-------------|---------|
| 通勤穿搭 | `通勤/职场` | 西装裤、衬衫、一步裙、西装外套 |
| 温柔穿搭 | `温柔/女性化` | 针织衫、蕾丝上衣、A字裙、雪纺衫 |
| 高级感穿搭 | `高级感/简约` | 真丝衬衫、羊绒衫、缎面裙 |
| 韩系穿搭 | `韩系` | 宽松卫衣、直筒裤、格纹裙 |
| 法式优雅 | `法式` | 碎花裙、条纹衫、茶歇裙 |
| 休闲穿搭 | `休闲/街头` | 牛仔裤、T恤、运动鞋、卫衣 |
| 新中式 | `中式/国风` | 旗袍、汉服改良款、盘扣上衣 |
| 显瘦穿搭 | `显瘦/遮肉` | 深色阔腿裤、A字裙、V领上衣 |

> 一个商品可以有多个风格，用 `/` 分隔。商品图(images)是 ImageGenerator 图生图的参考输入，**必须上传真实商品白底图**。

#### 2. 博主形象一致性 — 英文 Avatar Prompt + 面部参考图

**当前问题**：`avatar_desc: "圆脸、温柔杏眼、长发微卷、暖白皮、气质优雅、微笑自然"` 仅 16 个中文字，Seedream 底层是英文模型，中文效果差；seed 相同只能让输出"相似"不能保证"同一张脸"。

**解决路径**：英文精细 Prompt → 批量生成 → 人工挑选 → 面部参考图锚定。

| 步骤 | 负责 | 产出物 | 说明 |
|------|------|--------|------|
| 1. 写英文 Avatar Prompt | PM | `data/avatar_prompts/xiaolu_xuejie.txt` | 300+ 词，含面部/发型/肤色/体型/表情/禁止项 |
| 2. 批量生成候选图 | 工程师 | 20+ 张候选图 | 纯文生图，固定 seed，变化 prompt 微调 |
| 3. 挑选最佳面部 | PM | `data/avatar_refs/xiaolu_xuejie.png` | 从 20+ 张中选一张最符合人设的 |
| 4. 面部锚定生图 | 工程师 | ImageGenerator 双参考图模式 | 面部参考图 + 商品参考图同时传入 Seedream |

**Avatar Prompt 模板**（英文，需覆盖以下维度）：

```
Subject: A 25-30 year old Chinese female fashion blogger.
Face: round face shape, soft warm brown almond-shaped eyes with gentle epicanthic fold,
  straight nose with rounded tip, medium-full lips with defined cupid's bow,
  soft jawline, slight double chin (natural for plus-size face).
Hair: long dark brown hair, loose natural waves, center part, soft volume,
  falling past shoulders to mid-back.
Skin: Fitzpatrick type III, warm undertone, clear complexion, natural dewy finish.
Body: 165cm, plus-size (XL-2XL), pear-shaped silhouette, fuller arms and thighs,
  wider hips, defined waist, confident posture.
Expression: warm gentle smile, approachable, relaxed, natural eye contact with camera.
Style: elegant French-inspired fashion, sophisticated yet accessible.

Photography: full-body shot, natural daylight, urban street or cafe background,
  fashion blogger OOTD aesthetic, 1024x1536 portrait, high-definition.

Negative: skinny, thin face, sharp jawline, different person, inconsistent face,
  deformed hands, extra fingers, extra limbs, distorted body proportions,
  blurry, low quality, overexposed, western facial features, heavy makeup.
```

#### 3. 趋势数据定期更新

**流程**：每周从灰豚数据/千瓜导出三个榜单 → 覆盖 `data/source_*.csv` → 运行 `python scripts/comprehensive_analysis.py` → `strategy_full.csv` 自动更新。

**三个源文件**：

#### 4. ContentWriter 文案风格采集与分析

**当前问题**：生成的文案 AI 味重，"姐妹们""绝绝子""闭眼入"等词已过时，广告感强。需要从真实小红书笔记中学习当前流行的文案风格。

**目标**：抓取特定赛道高赞博主笔记 → 提炼文案特征 → 构建 Few-shot → 模型模仿真人风格。

**采集策略**：

| 赛道 | 搜索关键词 | 采集数量 | 筛选标准 |
|------|-----------|---------|---------|
| 大码穿搭 | `大码穿搭` `微胖显瘦` `微胖女生穿搭` | 20 篇 | 点赞 > 500，非纯广告，文案有真实分享感 |
| 小个子穿搭 | `小个子穿搭` `155cm穿搭` `小个子显高` | 20 篇 | 同上 |
| 通勤穿搭 | `通勤穿搭` `职场穿搭` `上班穿什么` | 20 篇 | 同上 |
| 法式穿搭 | `法式穿搭` `法式优雅` `氛围感穿搭` | 10 篇 | 同上 |
| 韩系穿搭 | `韩系穿搭` `韩系简约` `ins风穿搭` | 10 篇 | 同上 |

**提炼维度**：

| 维度 | 需要分析的内容 |
|------|--------------|
| 标题公式 | 标题长度/是否用 emoji/数字占比/疑问句 vs 陈述句/常用模板 |
| 正文结构 | 开头句式(最常用的 3 种)/正文分段方式/结尾互动话术 |
| 高频词 | 当前真实博主常用的词（不是"绝绝子"那种 2023 年 AI 味词） |
| 标签组合 | 每篇带几个标签/标签类别比例（风格:人群:品类:泛流量） |
| 人设差异 | 大码博主 vs 小个子博主的语气差异（用词/态度/互动方式） |
| AI 味特征 | 过度使用哪些句式会暴露 AI 生成（如"这不得冲？""谁懂啊"） |

**产出物**：

| 序号 | 产出物 | 说明 |
|------|--------|------|
| 1 | `data/reference_posts/赛道名/` | 原始笔记（截图或复制文本） |
| 2 | `docs/content_style_guide.md` | 文案特征提炼 + 标题公式库 |
| 3 | `data/banned_words.txt` | AI 高频禁用词清单 |
| 4 | `docs/few_shot_examples.md` | 3-5 篇精选样本，结构化后作为 Few-shot |

**采集方式**：

| 方式 | 依赖 | 说明 |
|------|------|------|
| PM 手动复制 | 无 | 直接在小红书 App/Web 搜索 → 复制高赞笔记正文 → 粘贴到文件 |
| 工程师爬虫 | Playwright/DP | 自动化采集（见 §四 爬虫优化方向） |

#### 5. 内容质量标准文档

图片质量 Checklist / 文案质量 Checklist / 穿搭合理性 Checklist / 通过/驳回标准

### P1 — 下周

#### 6. 新博主人设设计

在 `data/persona.yaml` 基础上新增 2 个人设：

| 人设 | 体型 | 风格 | 对标人群 |
|------|------|------|---------|
| 小鹿学姐（已有） | 大码 XL-2XL | 法式/通勤/温柔 | 微胖职场女性 |
| 米米姐姐（新） | 小个子 153cm | 韩系/甜美/显高 | 小个子学生/职场 |
| 七七学姐（新） | 标准微胖 | 平价/休闲/国潮 | 学生党/预算有限 |

每位人设需包含：style_tags(3-5个)、tone_of_voice、avatar_desc(英文 300+ 词，见 Avatar Prompt 模板)、content_focus、avoid_tags、面部参考图

#### 7. 积累 5-10 篇高质量 Demo，准备面试汇报

汇总内容：趋势分析报告 + 商品匹配结果 + 穿搭方案 + 生成图片 + 文案 + 数据追踪模拟

---

## 三、工程师待办

### P0 — 本周

#### 1. ImageGenerator 博主面部一致性

| 子任务 | 说明 |
|--------|------|
| **1a. 面部参考图模式** | 在 Persona 或 config 中增加 `avatar_ref` 图片路径；ImageGenerator 将 `avatar_ref` 作为 img2img 参考传入 Seedream（与商品图 `reference_images` 区分通道） |
| **1b. 双参考图策略** | 如果 Seedream 支持多参考图 → 面部图 + 商品图同时传入；如果不支持 → 优先用面部参考图 + Prompt 详细描述服装 |
| **1c. Avatar Prompt 加载** | `ImageGenerator._build_prompt()` 改为从 `data/avatar_prompts/{persona_name}.txt` 加载英文精细 Prompt，替代当前的 `avatar_desc` 简单拼接 |

#### 2. Prompt 外置化

将所有 Skill 的 System Prompt 从 `.py` 常量移到 `prompts/` 目录 YAML 文件。

```
prompts/
├── trend_radar.yaml
├── product_matcher.yaml
├── outfit_composer.yaml
├── image_generator.yaml
├── content_writer.yaml
└── performance_tracker.yaml
```

YAML 格式：
```yaml
name: product_matcher
system_prompt: |
  你是小红书穿搭商品匹配专家...
user_prompt_template: |
  请根据以下信息匹配...
```

实现要点：
- 每个 Skill `__init__` 时从对应 YAML 加载
- YAML 不存在时回退到代码中的默认 Prompt
- 支持环境变量指定 prompts 目录路径

#### 3. ImageGenerator 并发生成

当前逐张生成（3 张图串行 = 3×30s），改为 `asyncio.gather` 并发：

```
当前：for i in range(3): generate() → 90s
优化：await asyncio.gather(generate(), generate(), generate()) → 30s
```

#### 4. ImageGenerator 过多生成供挑选

```python
def execute(num_images=3, ...):
    generated = await _generate_images(N=max(num_images*2, 5))
    selected = _pick_best(generated, top_n=num_images)
    return selected
```

### P1 — 下周

#### 5. ContentWriter Few-Shot 注入

| 子任务 | 说明 |
|--------|------|
| 加载参考样本 | 从 `data/reference_posts/{赛道}/*.txt` 加载 PM 提供的样本，注入 System Prompt 末尾作为 Few-shot |
| 人设专属 Prompt | 支持 `prompts/content_writer_{persona_name}.yaml`，有则用专属版 |
| 禁用词过滤 | 加载 `data/banned_words.txt`，作为 System Prompt 内的 neg_prompt 或后处理过滤 |

#### 6. docker-compose 环境变量对齐

`docker-compose.yml` 中 `OPENAI_API_KEY`/`OPENAI_BASE_URL` 改为 `LLM_API_KEY`/`LLM_BASE_URL`/`IMAGE_API_KEY`/`IMAGE_BASE_URL`/`IMAGE_MODEL`/`LLM_MODEL`，与 `config.py` 对齐。

#### 7. Pipeline 声明式配置

```yaml
# config/pipeline.yaml
steps:
  - skill: trend_radar
    params: {persona_style_tags: "{{persona.style_tags}}"}
  - skill: product_matcher
    params: {products: "{{products}}", product_hints: "{{step.trend_radar.product_hints}}"}
  - skill: outfit_composer
    params: {style_directions: "{{step.trend_radar.style_directions}}"}
  - skill: image_generator
    params: {reference_images: "{{product_images}}", avatar_ref: "{{persona.avatar_ref}}"}
  - skill: content_writer
    params: {topic_tags: "{{step.trend_radar.topic_tags}}"}
```

#### 8. PerformanceTracker 接入 Pipeline

在 `pipeline.run()` 生成 Post 后调用 `self.performance_tracker.execute()`。当前 DB 无真实 PostPerformance 数据，接入后框架就位。

#### 9. 缺失 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trends/refresh` | 触发重新读取 strategy_full.csv |
| GET | `/api/performance/{id}` | 查看单篇效果报告 |

### P2 — 后续

#### 10. Pipeline 错误处理增强

单步失败降级策略：TrendRadar 失败 → 跳过趋势信号，退化为无趋势模式；ImageGen 失败 → 重试 2 次；其他失败 → 终止 Pipeline

#### 11. GitHub Actions CI

自动测试 + 覆盖率报告

---

## 四、小红书爬虫优化方向

爬虫用于两个场景：(A) 采集博主文案做 Few-shot；(B) 获取实时热搜数据补充 strategy_full。

### 为什么 requests.get() 不可行

| 原因 | 说明 |
|------|------|
| React SPA | 小红书搜索页是客户端渲染，HTML 源码几乎是空的，`requests.get()` 拿不到笔记 DOM |
| 强反爬 | Cookie 验证、滑块验证码、JS 混淆、请求签名（xs/xs-common 等 header） |
| 动态选择器 | CSS 类名每次构建随机变化，`.note-item` 等旧版选择器早已失效 |

### 优化方案（从易到难）

| 方案 | 技术 | 成本 | 可靠度 | 适用场景 |
|------|------|------|--------|---------|
| **A. 浏览器操控** | Playwright / DrissionPage | 中 | 高 | 采集文案做 Few-shot（低频，量小） |
| **B. 浏览器操控 + Cookie** | Playwright + 从真实浏览器导出 Cookie | 中 | 高 | 同上，绕过登录态 |
| **C. 第三方数据 API** | 新榜/千瓜/灰豚数据 API | 付费 | 很高 | 趋势数据日常更新（已用 strategy_full 替代） |
| **D. 手机端抓包** | mitmproxy + iOS/Android 代理 | 高 | 高 | 获取真实 API 返回的 JSON（非 HTML） |
| **E. RPA 框架** | browser-use / crawlee | 低(封装好) | 中 | 自动化采集，自带反检测 |

### 推荐路线

```
Phase 1 (当前): 不爬。strategy_full.csv 已满足趋势需求，PM 手动采集文案参考样本
Phase 2 (ContentWriter): Playwright + Cookie 注入 → 按搜索词批量采集笔记正文
Phase 3 (实时趋势): 评估第三方 API 成本 → 决定是否接入
```

### Phase 2 技术要点

```python
# Playwright 采集小红书搜索页笔记标题+正文+点赞数
from playwright.sync_api import sync_playwright

def scrape_xhs(keyword: str, count: int = 20) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 可能需要非headless
        context = browser.new_context(
            storage_state="cookies.json",  # 从浏览器导出
            viewport={"width": 390, "height": 844},  # 手机尺寸
            user_agent="Mozilla/5.0 ... Mobile ..."
        )
        page = context.new_page()
        page.goto(f"https://www.xiaohongshu.com/search_result?keyword={keyword}")
        # 等渲染 + 滚动加载 + 解析
        ...
```

**关键注意事项**：
- Cookie 需要从真实登录的浏览器导出（Chrome DevTools → Application → Cookies → 导出）
- Cookie 有效期通常 1-3 天，需定期更换
- 请求频率需模拟真人（间隔 3-5s），否则触发验证码
- 优先爬笔记**正文文本**，图片和视频暂不下载（降低复杂度和存储成本）

---

## 五、协作节奏

### 本周 (May 12-18)

```
PM 侧：
  Day1: 撰写英文 Avatar Prompt（小鹿学姐 300+ 词）
  Day1-3: 商品库扩充到 30+ 件（含商品白底图 + style 标签）
  Day2-3: 手动采集大码/通勤赛道高赞笔记 20 篇（做 ContentWriter Few-shot 素材）
  Day4: 趋势数据三个源 CSV 首次更新
  Day5: 从批量生图中挑选小鹿学姐面部参考图

工程师侧：
  Day1: ImageGenerator 面部参考图模式 + 双参考图策略
  Day2: Prompt 外置化（6 个 Skill 的 YAML）
  Day3: ImageGenerator 并发 + 过多生成
  Day4: docker-compose 环境变量对齐
  Day5: 联调全链路（加 PM 的新 Prompt 和商品跑一次完整 Pipeline）
```

### Git 分支建议

```
main              — 稳定
eng/image-v2      — ImageGenerator 面部一致性 + 并发
eng/prompts       — Prompt 外置化
eng/crawler       — 小红书爬虫
pm/products       — PM 商品库扩充
```
