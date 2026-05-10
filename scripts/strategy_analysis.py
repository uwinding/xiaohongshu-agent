import csv
import os
from collections import defaultdict

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")


def read_csv(filename):
    path = os.path.join(data_dir, filename)
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def n(val):
    if val == "" or val is None:
        return 0
    return float(val)

# topic_views_w 单位是"万"，topic_participants 是原始人数
# 参与率(%) = participants / (views_w * 10000) * 100 = participants / (views_w * 100)
def engagement(tv_w, tp):
    if tv_w <= 0 or tp <= 0:
        return 0
    return round(tp / (tv_w * 100), 2)


# ========== 话题词策略表 ==========

topics = read_csv("trends_topics.csv")

# 计算每个子类的总浏览量
cat_totals = defaultdict(float)
for r in topics:
    cat_totals[r["sub_category"]] += n(r["topic_views_w"])

# 每个子类的词数量（用于竞争度辅助判断）
cat_counts = defaultdict(int)
for r in topics:
    cat_counts[r["sub_category"]] += 1

strategy_topics = []
for r in topics:
    kw = r["keyword"]
    sc = r["sub_category"]
    tv = n(r["topic_views_w"])
    tp = n(r["topic_participants"])
    si = n(r["search_index_w"])

    # 参与率 (%) = 参与人数 / (浏览量(万) × 10000) × 100
    engagement_rate = engagement(tv, tp)

    # 竞争度：该词浏览量占同子类总浏览量的比例 (%)
    cat_total = cat_totals[sc]
    competition = round(tv / cat_total * 100, 1) if cat_total > 0 else 0

    # 供需比：搜索指数 / 话题浏览量（同是万单位，无量纲）
    supply_demand = round(si / tv, 3) if si > 0 and tv > 0 else 0

    # ---- 策略判定逻辑 ----

    signals = []
    priority = "低"

    if r["is_surging"] == "是":
        signals.append("搜索飙升中")

    if si > 200:
        signals.append(f"搜索需求强({si}w)")

    # 参与率判定（小红书典型参与率 0.02%~0.15%）
    if engagement_rate > 0.1:
        signals.append("参与率高")
    elif engagement_rate > 0.05:
        signals.append("参与率中等")
    elif engagement_rate > 0 and engagement_rate <= 0.05:
        signals.append("参与率偏低")

    # 竞争度判定
    if competition < 10:
        signals.append("竞争分散(蓝海)")
    elif competition > 30:
        signals.append("竞争集中(红海)")

    # 供需关系
    if si > 0 and tv > 0:
        if supply_demand > 0.1:
            signals.append("供不应求")
        elif supply_demand < 0.05:
            signals.append("供需平衡")

    # 综合优先级
    score = 0
    if r["is_surging"] == "是":
        score += 3
    if si > 300:
        score += 2
    elif si > 100:
        score += 1
    if engagement_rate > 0.1:
        score += 2
    elif engagement_rate > 0.05:
        score += 1
    if competition < 10:
        score += 2
    elif competition < 20:
        score += 1
    if tv > 2000:
        score += 2
    elif tv > 1000:
        score += 1

    if score >= 6:
        priority = "高"
    elif score >= 3:
        priority = "中"
    else:
        priority = "低"

    # 写文案建议
    rec = ""
    if sc == "风格":
        rec = f"穿搭风格方向：{kw}，用于 {f'搜索飙升+' if r['is_surging'] == '是' else ''}参与率{engagement_rate}%"
    elif sc == "季节":
        rec = f"季节性选题，配合当季推送，参与率{engagement_rate}%"
    elif sc == "场景":
        rec = f"场景化穿搭内容：{kw}，适用于特定场景选题"
    elif sc == "人群":
        rec = f"定向人群标签：{kw}，精准触达对应粉丝群体"
    elif sc == "概念":
        rec = f"概念类内容方向：{kw}，打造差异化内容"
    elif sc == "灵感":
        rec = f"日常内容灵感，稳定输出频率"

    strategy_topics.append({
        "keyword": kw,
        "sub_category": sc,
        "search_index_w": r["search_index_w"],
        "topic_views_w": r["topic_views_w"],
        "topic_participants": r["topic_participants"],
        "参与率(%)": engagement_rate,
        "竞争度(%)": competition,
        "供需比": supply_demand if supply_demand > 0 else "",
        "is_surging": r["is_surging"],
        "信号": " | ".join(signals) if signals else "-",
        "策略建议": rec,
        "优先级": priority,
    })

strategy_topics.sort(key=lambda r: (
    {"高": 0, "中": 1, "低": 2}.get(r["优先级"], 3),
    -(n(r["topic_views_w"]) + n(r["search_index_w"]))
))


# ========== 品类词策略表 ==========

cats = read_csv("trends_categories.csv")

# 子类总搜索指数
cat_search_totals = defaultdict(float)
for r in cats:
    cat_search_totals[r["sub_category"]] += n(r["search_index_w"])

cat_topic_totals_cat = defaultdict(float)
for r in cats:
    cat_topic_totals_cat[r["sub_category"]] += n(r["topic_views_w"])

strategy_cats = []
for r in cats:
    kw = r["keyword"]
    sc = r["sub_category"]
    tv = n(r["topic_views_w"])
    si = n(r["search_index_w"])

    # 参与率 (品类词的话题参与率，只有同时有话题数据的词才有)
    tp = n(r["topic_participants"])
    engagement_rate = engagement(tv, tp)

    # 搜索竞争度：该词搜索指数占同子类总搜索指数比例 (%)
    cat_s_total = cat_search_totals[sc]
    search_share = round(si / cat_s_total * 100, 1) if cat_s_total > 0 else 0

    # 供给热度：话题浏览量 - 反映该品类在小红书的内容供给
    supply_score = ""
    if tv > 0:
        if tv > 1000:
            supply_score = "内容供给充足"
        elif tv > 300:
            supply_score = "内容供给中等"
        else:
            supply_score = "内容供给较少"

    # 选品策略
    signals = []
    priority = "低"

    if r["is_surging"] == "是":
        signals.append("搜索飙升，优先备货")
    if si > 200:
        signals.append(f"强需求品类({si}w)")
    elif si > 100:
        signals.append(f"中等需求({si}w)")

    if sc in ("品牌", "风格品类", "泛品类"):
        rec = f"参考方向：{kw}，关注其在小红书的种草趋势"
    elif si > 200 and r["is_surging"] == "是":
        rec = f"强烈建议备货：{kw}，搜索飙升+强需求"
    elif si > 100:
        rec = f"建议备货：{kw}，需求稳定"
    else:
        rec = f"可备选：{kw}，需求适中"

    # 优先级
    score = 0
    if r["is_surging"] == "是":
        score += 3
    if si > 300:
        score += 2
    elif si > 100:
        score += 1
    if tv > 500:
        score += 1

    if score >= 4:
        priority = "高"
    elif score >= 2:
        priority = "中"
    else:
        priority = "低"

    strategy_cats.append({
        "keyword": kw,
        "sub_category": sc,
        "search_index_w": r["search_index_w"],
        "topic_views_w": r["topic_views_w"],
        "参与率(%)": engagement_rate if engagement_rate > 0 else "",
        "搜索集中度(%)": search_share,
        "内容供给": supply_score if supply_score else "仅有搜索数据",
        "is_surging": r["is_surging"],
        "信号": " | ".join(signals) if signals else "-",
        "策略建议": rec,
        "优先级": priority,
    })

strategy_cats.sort(key=lambda r: (
    {"高": 0, "中": 1, "低": 2}.get(r["优先级"], 3),
    -(n(r["search_index_w"]) + n(r["topic_views_w"]))
))


# ========== 写入 ==========

def write_csv(filename, records, fieldnames):
    path = os.path.join(data_dir, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(r)
    print(f"✅ {filename}  ({len(records)} 行)")

    # 打印优先级分布
    pri_counts = defaultdict(int)
    for r in records:
        pri_counts[r["优先级"]] += 1
    for p in ["高", "中", "低"]:
        print(f"   ├ 优先级[{p}]: {pri_counts.get(p, 0)}")


topic_fields = [
    "keyword", "sub_category", "search_index_w", "topic_views_w",
    "topic_participants", "参与率(%)", "竞争度(%)", "供需比",
    "is_surging", "信号", "策略建议", "优先级"
]

cat_fields = [
    "keyword", "sub_category", "search_index_w", "topic_views_w",
    "参与率(%)", "搜索集中度(%)", "内容供给",
    "is_surging", "信号", "策略建议", "优先级"
]

print("=" * 60)
print("【话题策略表】")
print("=" * 60)
write_csv("strategy_topics.csv", strategy_topics, topic_fields)

print()
print("=" * 60)
print("【品类策略表】")
print("=" * 60)
write_csv("strategy_categories.csv", strategy_cats, cat_fields)

# ========== 控制台摘要 ==========
print()
print("=" * 60)
print("策略摘要")
print("=" * 60)

high_topics = [r for r in strategy_topics if r["优先级"] == "高"]
medium_topics = [r for r in strategy_topics if r["优先级"] == "中"]
print(f"\n话题 - 高优先级({len(high_topics)}个)：")
for r in high_topics[:10]:
    print(f"  {r['keyword']} ({r['sub_category']}) | 参与率{r['参与率(%)']}% 竞争度{r['竞争度(%)']}% | {r['信号']}")

print(f"\n话题 - 中优先级({len(medium_topics)}个)：")
for r in medium_topics[:10]:
    print(f"  {r['keyword']} ({r['sub_category']}) | 参与率{r['参与率(%)']}% 竞争度{r['竞争度(%)']}% | {r['信号']}")

high_cats = [r for r in strategy_cats if r["优先级"] == "高"]
medium_cats = [r for r in strategy_cats if r["优先级"] == "中"]
print(f"\n品类 - 高优先级({len(high_cats)}个)：")
for r in high_cats:
    print(f"  {r['keyword']} ({r['sub_category']}) | 搜索{r['search_index_w']}w | {r['信号']}")

print(f"\n品类 - 中优先级({len(medium_cats)}个)：")
for r in medium_cats:
    print(f"  {r['keyword']} ({r['sub_category']}) | 搜索{r['search_index_w']}w | {r['信号']}")
