---
name: xiaohongshu-fashion-agent
description: "运营、维护和优化小红书 AI 虚拟穿搭博主项目。用于 Codex 需要管理本仓库端到端工作流时：接入趋势源 CSV、趋势排序、商品匹配、穿搭方案、生图提示词/图片生成、小红书文案、表现分析、FastAPI 路由、测试修复，以及将项目演进为 agent 驱动的 skill 工作流。"
---

# 小红书穿搭博主 Agent

## 快速定位

把本仓库视为一个由 AI Agent 运营的内容生产系统，目标是为虚拟小红书穿搭博主生成可审核的图文草稿。

核心运行路径：

1. `TrendRadar` 读取趋势源文件。
2. `ProductMatcher` 按人设和趋势选择商品。
3. `OutfitComposer` 生成穿搭描述和生图提示词。
4. `ImageGenerator` 调用配置好的图片 API。
5. `ContentWriter` 生成小红书标题、正文、话题标签和商品标签。
6. `PerformanceTracker` 汇总内容表现。

生文能力由当前执行本 skill 的 agent 和仓库内本地逻辑完成。不要重新引入必需的文本模型 API 配置，除非用户明确要求。生图仍可使用 `image_*` 配置。

## 开始工作前

修改代码前优先查看：

- `app/pipeline.py`
- `app/skills/*.py`
- `app/trend_sources.py`
- `scripts/process_trends.py`
- `tests/`

需要更完整的项目工作流时，读取 [references/workflow.md](references/workflow.md)。需要趋势源字段契约时，读取 [references/trend-data-contract.md](references/trend-data-contract.md)。

## 运营工作流

当用户要求运行或优化 agent 工作流时：

1. 用 `python3 scripts/process_trends.py` 校验趋势源。
2. 对改动范围运行定向测试。
3. 可行时用 `pytest -q` 运行全量测试。
4. 除非用户要求持久化，不要把 `data/trends_normalized.csv` 这类检查产物纳入提交。
5. 保持三张趋势源表契约稳定，确保未来爬虫只替换采集层，不影响 `TrendRadar`。

## 实现规则

- 文本类 skill 保持本地确定性逻辑：`ProductMatcher`、`OutfitComposer`、`ContentWriter`、`PerformanceTracker` 返回结构化 `SkillResult`，不依赖外部文本模型 API。
- 趋势边界保持清晰：适配器/爬虫写入源 CSV；`app/trend_sources.py` 归一化；`TrendRadar` 按人设排序并输出给下游。
- pipeline 输出保持稳定：post、outfit、images、trend 字段需兼容当前路由和模板。
- skill 或 route 改动先跑局部测试，再跑 `pytest -q`。
- 如果路由测试在当前环境卡住，优先检查同步 FastAPI handler 或同步 generator dependency 是否进入 anyio worker-thread 路径。
