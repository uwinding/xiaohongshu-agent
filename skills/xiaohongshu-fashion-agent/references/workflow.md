# 项目工作流参考

## 仓库地图

- `app/pipeline.py`：端到端生成编排。
- `app/skills/trend_radar.py`：按博主人设筛选趋势。
- `app/trend_sources.py`：趋势源 CSV 归一化和关键词分类。
- `app/skills/product_matcher.py`：商品评分和搭配商品组合选择。
- `app/skills/outfit_composer.py`：穿搭描述、场景、正向/反向生图提示词。
- `app/skills/image_generator.py`：外部图片 API 调用和图片落盘。
- `app/skills/content_writer.py`：本地小红书文案生成。
- `app/skills/performance_tracker.py`：本地表现总结。
- `app/routes/`：FastAPI JSON 接口。
- `app/templates/`：管理后台 HTML 页面。
- `scripts/process_trends.py`：把趋势源表归一化为检查用 CSV。
- `scripts/seed.py`：初始化博主人设和商品数据。
- `tests/`：单元、路由、集成和 skill 测试。

## 端到端运行

1. 初始化数据库和样例数据：`python3 scripts/seed.py`
2. 校验趋势源表：`python3 scripts/process_trends.py`
3. 启动服务：`uvicorn app.main:app --reload`
4. 调用生成接口：`POST /api/generate`，参数包括 `persona_id`，可选 `product_ids`、`style`、`scene`、`num_images`
5. 通过后台页面或 `/api/posts` 审核草稿。

## Agent 优化循环

优化工作流质量时：

1. 先定位薄弱或失败阶段，不要一开始重写整条链路。
2. 保持 `SkillResult(success, data, error, metadata)` 约定。
3. 除非同步更新调用方和测试，否则保持 skill 间接口稳定。
4. 在改动同层补充或调整测试。
5. skill 改动跑 `pytest -q tests/test_skills/...`，路由改动跑 `pytest -q tests/test_routes.py`，交付前跑 `pytest -q`。

## 生文策略

当前执行 skill 的 agent 负责文本推理。不要重新引入必需的 `llm_api_key`、`llm_base_url` 或 `llm_model` 配置用于：

- 商品匹配
- 穿搭方案
- 小红书文案
- 表现分析

可以优化确定性启发式、模板、排序逻辑和生图 prompt 组装。如果需要更自然的表达，把编辑策略写入本地 skill 逻辑或参考文档。

## 路由测试注意事项

当前环境中，FastAPI 同步路由或同步 generator dependency 可能通过 anyio worker-thread portal 卡住。优先保持：

- 路由函数使用 `async def`
- `get_db` 使用 async generator
- 测试 fixture 使用 `httpx.ASGITransport`，避免 `fastapi.testclient.TestClient` 卡住
