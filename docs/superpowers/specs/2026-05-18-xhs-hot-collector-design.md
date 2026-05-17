# XHS 热点内容采集器设计文档

> 2026-05-18 | 基于用户设计文档 + 代码库调研后的落地设计

---

## 1. 范围

在 `app/collector/` 下实现一个轻量级小红书网页版数据采集模块，输出到 CSV / JSON / SQLite。

### 1.1 当前版本

- 输入关键词，搜索小红书
- 筛选：图文 + 一周内
- 提取：顶部热词 + 笔记文案 + 笔记 tag + 元信息（标题/作者/发布时间/互动数）
- 去重：note_id 主键 + content_hash 辅助
- 输出：CSV + JSON + SQLite（3 张新表：collector_note / collector_snapshot / collector_task）

### 1.2 后续 Phase

- 批量关键词（keywords.yaml）
- 定时调度（APScheduler）
- 热词频次 / tag 频次统计
- 趋势报告

---

## 2. 决策记录

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 代码位置 | `app/collector/` 独立子包 | 与 MediaCrawler 解耦；与 app 层共用一个 SQLite |
| API vs Playwright 筛选 | 优先 API 参数 (note_type=2, sort=time_filtered) | 更稳定、更快 |
| 正文抽取 | BeautifulSoup + lxml | 已在依赖中，无需引入 crawl4ai |
| 输出 | CSV + JSON + SQLite 三路 | 文件便于人工查看，SQLite 便于查询和后续分析 |
| 与 MediaCrawler 关系 | 参考 X-S 签名和 API endpoint，代码独立 | 避免版本耦合 |

---

## 3. 模块结构

```
app/collector/
├── __init__.py
├── config.py            # CollectorConfig (pydantic-settings)
├── exceptions.py        # LoginExpired, NoteNotFound, RateLimitError
├── browser.py           # Playwright 生命周期、登录态持久化
├── client.py            # XHS API 封装（签名、搜索、详情）
├── search.py            # 搜索逻辑：API 调用 + 热词提取 + 笔记列表
├── note_detail.py       # 详情页：正文、tag、元信息抽取
├── extractor.py         # HTML 文本抽取 + 正文清洗
├── dedup.py             # note_id + content_hash 去重
├── store.py             # CSV / JSON / SQLite 三路输出
├── runner.py            # 整条链路编排
├── scheduler.py         # 定时任务（Phase 2）
└── models.py            # SQLAlchemy 模型
```

---

## 4. 核心流程

```
Config 加载 → Browser 启动 → 登录态恢复/扫码登录
  → XHS Client 创建（cookie + X-S 签名）
  → 搜索循环 (每个 keyword):
       POST /api/sns/web/v1/search/notes
         params: keyword, note_type=2 (图文), sort=4 (time_filtered)
       ├→ 热词: items[model_type="hot_query"]
       └→ 笔记列表: items[model_type="note"]
            ├→ 获取详情: POST /api/sns/web/v1/feed
            ├→ 正文解析 (BS4) + tag 提取 + 清洗
            ├→ 去重 (note_id)
            └→ 落库 + 写文件
       └→ 翻页 (has_more=true, 最多 N 条)
```

### 4.1 关键 API

| 步骤 | Method | URI | 关键参数 |
|------|--------|-----|---------|
| 搜索 | POST | `/api/sns/web/v1/search/notes` | `keyword`, `note_type=2`, `sort=4`, `page_size=20` |
| 笔记详情 | POST | `/api/sns/web/v1/feed` | `source_note_id`, `xsec_token`, `extra.need_body_topic=1` |
| 登录检查 | GET | `/api/sns/web/v1/user/selfinfo` | cookie 中的 web_session |

### 4.2 流程控制

- 单 keyword 最多 50 条笔记
- 详情并发 2-3 个，间隔 1-3 秒
- 搜索页间隔 3-5 秒
- 失败重试 3 次

---

## 5. 数据模型

### 5.1 collector_note（笔记主表）

| 字段 | 类型 | 说明 |
|------|------|------|
| note_id | TEXT PK | 小红书笔记 ID |
| title | TEXT | 标题 |
| content_raw | TEXT | 原始正文 |
| content_clean | TEXT | 清洗后正文 |
| content_hash | TEXT | SHA256 哈希（去重用） |
| author_id | TEXT | 作者 ID |
| author_name | TEXT | 作者昵称 |
| publish_time | TEXT | 发布时间（毫秒时间戳转 ISO） |
| like_count | INTEGER | 点赞数 |
| collect_count | INTEGER | 收藏数 |
| comment_count | INTEGER | 评论数 |
| note_type | TEXT | "normal" / "video" |
| source_url | TEXT | 笔记链接 |
| created_at | TEXT | 入库时间 |
| updated_at | TEXT | 更新时间 |

### 5.2 collector_snapshot（采集快照）

| 字段 | 类型 | 说明 |
|------|------|------|
| snapshot_id | TEXT PK | UUID |
| task_id | TEXT FK | 关联 collector_task |
| note_id | TEXT | 笔记 ID |
| keyword | TEXT | 搜索关键词 |
| hotwords_json | TEXT | 热词 JSON |
| tags_json | TEXT | tag JSON |
| crawled_at | TEXT | 采集时间 |

### 5.3 collector_task（任务表）

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | TEXT PK | UUID |
| keyword | TEXT | 搜索关键词 |
| note_type | TEXT | "image_text" |
| sort | TEXT | "time_filtered" |
| status | TEXT | "running" / "done" / "failed" |
| notes_found | INTEGER | 发现笔记数 |
| notes_saved | INTEGER | 保存笔记数 |
| start_time | TEXT | 开始时间 |
| end_time | TEXT | 结束时间 |
| error_msg | TEXT | 错误信息 |

---

## 6. 去重策略

- `note_id`：主键唯一去重，已存在则跳过
- `content_hash`：标准化工本后 SHA256，辅助识别内容相同的笔记
  - 标准化规则：去空白、去连续换行、小写化

---

## 7. CSV 输出字段

`keyword, note_id, title, author_name, publish_time, content_clean, tags(hotwords, like_count, source_url, crawled_at`

---

## 8. JSON 输出结构

```json
{
  "keyword": "穿搭",
  "crawled_at": "2026-05-18T10:00:00",
  "hotwords": ["夏季", "韩里韩气"],
  "notes_count": 20,
  "notes": [
    {
      "note_id": "xxx",
      "title": "夏季通勤穿搭",
      "author_name": "xxx",
      "publish_time": "2026-05-17",
      "content_clean": "...",
      "tags": ["#夏季穿搭", "#通勤"],
      "like_count": 1234,
      "source_url": "https://www.xiaohongshu.com/explore/xxx"
    }
  ]
}
```

---

## 9. 错误处理

| 场景 | 处理 |
|------|------|
| 登录态失效 | 重新扫码登录，保存 storage_state.json |
| API 返回空 | 重试 3 次，仍失败则记录 error_msg |
| 笔记不存在 | 跳过，记录 warning 日志 |
| 触发风控/验证码 | 日志输出提示手动验证 |
| 网络超时 | 重试 2 次，间隔 5 秒 |

---

## 10. 与现有系统集成

- `app/models.py`：不修改现有表，3 张新表在 `app/collector/models.py` 中定义
- `app/main.py` 的 `init_db()`：增加 collector 表的创建
- TrendRadar：后续可从 `collector_note` 和 `collector_snapshot` 读取热词频次做趋势分析
- 配置：`app/collector/config.py` 独立管理采集参数

---

## 11. 配置文件

### config.py

```python
class CollectorConfig(BaseSettings):
    headless: bool = True
    max_concurrency: int = 3
    retry_times: int = 3
    page_timeout: int = 30000
    max_notes_per_keyword: int = 50
    storage_state_path: str = "data/storage_state.json"
    output_dir: str = "data/output"
    keywords: list[str] = ["穿搭"]
    note_type: str = "image_text"
    sort: str = "time_filtered"
```

---

## 12. 实现顺序

1. `config.py` + `exceptions.py` + `models.py` — 基础设施
2. `browser.py` — 浏览器启动/登录态
3. `client.py` — XHS API 签名与请求
4. `search.py` — 搜索 + 热词提取
5. `note_detail.py` + `extractor.py` — 详情页解析
6. `dedup.py` + `store.py` — 去重 + 存储
7. `runner.py` — 链路编排
8. 集成测试 + 功能测试
