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

`TrendRadar` 不再依赖灰豚/千瓜导出的 `strategy_full.csv`。后续无论是手工导入还是爬虫采集，只需要落三张源表：

- `data/source_hot_search.csv`: `keyword,search_index_w,is_surging`
- `data/source_topic_total.csv`: `keyword,views,participants`
- `data/source_topic_inc.csv`: `keyword,views,participants`

可运行 `python scripts/process_trends.py` 生成 `data/trends_normalized.csv` 用于检查归一化结果。

## 生文工作流

商品匹配、穿搭方案、文案生成、表现分析均由当前 skill 代码的本地 agent 逻辑完成，不再配置或调用独立文本模型 API。图片生成仍使用 `image_*` 配置。

## 运行测试

```bash
pytest -v
```
