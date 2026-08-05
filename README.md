# AI 穿搭博主 Agent

小红书 AI 虚拟穿搭博主，自动生成穿搭图文内容。

## 快速启动

1. 复制环境配置：
   
   ```bash
   cp .env.example .env
   # 如需真实生图，编辑 .env 填入 IMAGE_API_KEY / IMAGE_BASE_URL / IMAGE_MODEL
   ```

2. 安装依赖：
   
   ```bash
   pip install -e ".[dev]"
   ```

3. 初始化数据：
   
   ```bash
   python scripts/seed.py
   ```

4. 启动服务：
   
   ```bash
   uvicorn app.main:app --reload
   ```

5. 访问管理后台: http://localhost:8000

## Docker 启动

```bash
docker compose up -d
```

## API 文档

启动后访问 http://localhost:8000/docs (Swagger UI)

## 项目结构

```
xiaohongshu-agent/
├── app/
│   ├── skills/        # 6个Skill模块
│   ├── routes/        # API路由
│   ├── templates/     # 管理后台页面
│   ├── trend_sources.py # 趋势源表归一化
│   ├── pipeline.py    # 流程编排
│   └── main.py        # 入口
├── tests/
├── data/              # 商品库+博主人设
├── storage/images/    # 生成的图片
└── docker-compose.yml
```

## 趋势数据工作流

`TrendRadar` 已废弃灰豚/千瓜三张手工趋势表，只读取 collector 自采样趋势：

1. 运行小红书 collector，写入热词观察和笔记表现观察表。
2. 运行 `python3 scripts/collector_to_trends.py` 生成 `data/source_collector_trends.csv`。
3. `TrendRadar` 基于 `heat_score`、`growth_score`、`confidence`、`evidence_count` 和账号人设相关性筛选穿搭趋势。

推荐采集命令：

```bash
python3 -m app.collector --keywords-file data/keywords.yaml --max-notes 80 --sorts time_filtered,general,popularity_descending --recent-days 7 --top-per-metric 10 --page-hotwords --expand-page-hotwords 10
```

含义：

- `--recent-days 7`: 只保留最近 7 天笔记参与 Top 排名。
- `--top-per-metric 10`: 分别取点赞、评论、收藏 Top10，并按 `note_id` 去重。
- `--sorts time_filtered,general,popularity_descending`: 对同一关键词用多个搜索排序拉大候选池，再本地按赞/评/藏重排。
- `--page-hotwords --expand-page-hotwords 10`: 读取搜索页“综合”旁边的前 10 个关键词，并逐个二次采集。

可运行 `python3 scripts/process_trends.py` 生成 `data/trends_normalized.csv` 用于检查当前 TrendRadar 输入。

## 生文工作流

商品匹配、穿搭方案、文案生成、表现分析均由当前 skill 代码的本地 agent 逻辑完成，不再配置或调用独立文本模型 API。图片生成仍使用 `image_*` 配置。

## 运行测试

```bash
pytest -v
```
