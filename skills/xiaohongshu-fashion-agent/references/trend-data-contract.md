# 趋势数据契约

## 源文件

所有趋势采集方式，包括后续爬虫，都应把数据写入 `data/` 下的三张 CSV。

### `source_hot_search.csv`

必需字段：

- `keyword`：趋势关键词。
- `search_index_w`：搜索指数，单位为万。
- `is_surging`：是否飙升，支持 `1`、`true`、`yes`、`y`、`是`。

### `source_topic_total.csv`

必需字段：

- `keyword`：话题关键词。
- `views`：话题总浏览量，支持普通数字、`w` 和 `亿`。
- `participants`：总参与人数，支持逗号、普通数字、`w` 和 `亿`。

### `source_topic_inc.csv`

必需字段：

- `keyword`：话题关键词。
- `views`：增量浏览量。
- `participants`：增量参与人数。

## 归一化逻辑

`app/trend_sources.py` 会按关键词合并三张源表、分类关键词，并计算：

- `heat_score`：搜索指数、缩放后的总浏览量、增量浏览量三者取最大。
- `growth_score`：增量浏览量 + 参与人数增长加权 + 飙升加分。

`scripts/process_trends.py` 会写出 `data/trends_normalized.csv` 供人工检查。该文件是检查产物，不是运行时必需源。

## 下游输出

`TrendRadar.execute()` 返回：

- `product_hints`：给商品匹配使用的品类/商品趋势。
- `style_directions`：给穿搭方案使用的风格、场景、季节、人群趋势。
- `topic_tags`：给小红书文案使用的话题标签。
- `trend_summary`：简短中文趋势摘要。
- `matched_count`：与当前博主人设相关的趋势数量。

除非同步更新 pipeline、路由、测试和 agent 文档，否则不要改变这些 key。
