import csv
import os
from collections import defaultdict

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

# ========== 原始数据 ==========

hot_search_weekly = [
    ("穿搭", 1020.5, False),
    ("夏季穿搭", 391.6, True),
    ("春季穿搭", 374.1, False),
    ("lululenmon", 303.0, True),
    ("裙子", 285.1, True),
    ("夏天穿搭", 280.4, True),
    ("短袖", 273.4, True),
    ("韩系穿搭", 234.0, False),
    ("穿搭风格", 210.2, False),
    ("睡衣", 209.9, False),
    ("海边穿搭", 198.9, False),
    ("包包推荐", 196.8, False),
    ("lv包包", 191.2, False),
    ("连衣裙", 182.3, True),
    ("外套", 175.2, True),
    ("夏季穿搭推荐", 174.2, True),
    ("春天穿搭", 159.1, False),
    ("拉夫劳伦", 158.9, False),
    ("高跟鞋", 157.9, True),
    ("吊带", 152.7, False),
    ("鞋子推荐女", 152.5, False),
    ("阿迪达斯外套", 151.7, True),
    ("裤子", 150.6, True),
    ("鞋子", 149.2, True),
    ("包包", 148.6, False),
    ("优衣库", 146.3, True),
    ("lululemon", 145.4, False),
    ("旗袍", 145.3, True),
    ("五一穿搭", 144.0, False),
    ("裙子推荐", 142.4, True),
    ("洞洞鞋", 134.8, True),
    ("crocs洞洞鞋", 132.0, True),
    ("jk", 127.6, True),
    ("春夏穿搭", 127.4, False),
    ("帽子", 124.5, True),
    ("内衣", 122.8, False),
    ("牛仔裤", 122.5, False),
    ("男生穿搭", 122.3, False),
    ("香奈儿", 122.2, False),
    ("睡衣推荐夏天", 120.8, False),
    ("双肩包", 120.7, False),
    ("穿搭早春", 120.6, False),
    ("洞洞鞋推荐", 119.2, True),
    ("鬼冢虎", 119.1, True),
    ("衣服", 117.3, False),
    ("衬衫", 116.3, True),
    ("风衣穿搭", 113.2, True),
    ("半身裙", 112.7, True),
    ("衬衫穿搭", 110.8, True),
    ("短袖t恤推荐女", 110.8, True),
]

topic_daily_raw = [
    ("ootd", 3811.5, 16000),
    ("生活美学", 3769.7, 24000),
    ("氛围感", 3045.0, 9586),
    ("韩系穿搭", 2920.2, 23000),
    ("夏季穿搭", 2563.4, 20000),
    ("ootd每日穿搭", 2315.3, 8250),
    ("审美积累", 2224.7, 5962),
    ("小个子穿搭", 2180.7, 15000),
    ("显瘦穿搭", 2080.3, 12000),
    ("穿搭", 2076.2, 2893),
    ("通勤穿搭", 1854.2, 15000),
    ("每日穿搭", 1718.8, 7111),
    ("穿搭", 1647.4, 12000),
    ("夏日穿搭", 1642.3, 17000),
    ("春夏穿搭", 1471.6, 5995),
    ("时尚", 1459.0, 1243),
    ("日常穿搭", 1426.4, 5926),
    ("松弛感穿搭", 1398.3, 11000),
    ("微胖穿搭", 1342.3, 6007),
    ("ootdinspo", 1292.3, 5816),
    ("氛围感穿搭", 1223.7, 7880),
    ("温柔穿搭", 969.4, 3961),
    ("梨形身材", 955.9, 2810),
    ("气质穿搭", 932.0, 5315),
    ("五一出游", 860.0, 1955),
    ("连衣裙", 857.3, 2696),
    ("早春穿搭", 777.5, 3031),
    ("短袖", 758.5, 6511),
    ("穿搭灵感", 755.3, 2935),
    ("旗袍", 751.2, 2914),
    ("夏天穿搭", 728.0, 5822),
    ("高级感穿搭", 703.4, 7278),
    ("健身穿搭", 688.2, 4101),
    ("穿搭分享", 675.5, 3492),
    ("平价穿搭", 672.8, 3087),
    ("春季穿搭", 671.7, 3724),
    ("穿搭技巧", 664.0, 1329),
    ("穿搭bot", 655.6, 4013),
    ("方圆脸", 647.7, 752),
    ("不费力的穿搭", 647.5, 3804),
    ("汉服", 645.5, 3553),
    ("韩系", 634.9, 2497),
    ("每天一个穿搭灵感", 629.3, 3030),
    ("OOTD", 615.8, 6000),
    ("梨形身材穿搭", 614.2, 5535),
    ("ootd穿搭", 605.2, 3443),
    ("日系穿搭", 600.4, 81),
    ("东方美学", 599.9, 3338),
    ("女装", 583.4, 1467),
    ("时尚穿搭", 583.2, 3120),
    ("今天穿什么香", 571.9, 3454),
    ("出游穿搭", 569.6, 2124),
    ("colorwalk", 568.1, 1634),
    ("约会穿搭", 552.9, 4318),
    ("慵懒感穿搭", 551.9, 3254),
    ("lolita", 548.0, 2351),
    ("衬衫", 547.8, 3567),
    ("国风", 545.2, 2406),
    ("浅春系穿搭", 545.1, 4368),
    ("今天穿什么", 541.1, 3044),
    ("穿搭合集", 531.3, 669),
    ("休闲穿搭", 525.8, 2199),
]

# ========== 品类分类 ==========

categories_classification = {
    "短袖": "上装", "衬衫": "上装", "T恤": "上装", "吊带": "上装",
    "短袖t恤推荐女": "上装",
    "裤子": "下装", "牛仔裤": "下装", "半身裙": "下装",
    "连衣裙": "裙装", "裙子": "裙装", "裙子推荐": "裙装", "旗袍": "裙装",
    "外套": "外套", "阿迪达斯外套": "外套", "风衣穿搭": "外套",
    "睡衣": "内衣家居", "睡衣推荐夏天": "内衣家居", "内衣": "内衣家居",
    "鞋子": "鞋", "鞋子推荐女": "鞋", "高跟鞋": "鞋",
    "洞洞鞋": "鞋", "洞洞鞋推荐": "鞋", "crocs洞洞鞋": "鞋", "鬼冢虎": "鞋",
    "包包": "包", "包包推荐": "包", "lv包包": "包", "双肩包": "包",
    "帽子": "配饰",
    "lululenmon": "品牌", "lululemon": "品牌", "拉夫劳伦": "品牌",
    "优衣库": "品牌", "香奈儿": "品牌", "阿迪达斯外套": "品牌",
    "jk": "风格品类", "汉服": "风格品类", "lolita": "风格品类",
    "衣服": "泛品类", "女装": "泛品类",
}

# ========== 话题分类 ==========

topics_classification = {
    "夏季穿搭": "季节", "夏季穿搭推荐": "季节", "夏天穿搭": "季节",
    "春季穿搭": "季节", "春天穿搭": "季节", "春夏穿搭": "季节",
    "夏日穿搭": "季节", "早春穿搭": "季节", "穿搭早春": "季节",
    "浅春系穿搭": "季节",
    "海边穿搭": "场景", "五一穿搭": "场景", "通勤穿搭": "场景",
    "健身穿搭": "场景", "出游穿搭": "场景", "约会穿搭": "场景",
    "五一出游": "场景", "colorwalk": "场景",
    "韩系穿搭": "风格", "韩系": "风格", "松弛感穿搭": "风格",
    "温柔穿搭": "风格", "气质穿搭": "风格", "高级感穿搭": "风格",
    "慵懒感穿搭": "风格", "日系穿搭": "风格", "东方美学": "风格",
    "国风": "风格", "休闲穿搭": "风格", "不费力的穿搭": "风格",
    "氛围感穿搭": "风格", "甜妹": "风格",
    "小个子穿搭": "人群", "微胖穿搭": "人群", "梨形身材": "人群",
    "梨形身材穿搭": "人群", "方圆脸": "人群",
    "显瘦穿搭": "概念", "显瘦上衣": "概念", "氛围感": "概念",
    "生活美学": "概念", "审美积累": "概念", "今天穿什么香": "概念",
    "高级感穿搭": "概念", "平价穿搭": "概念",
    "穿搭灵感": "灵感", "穿搭技巧": "灵感", "穿搭分享": "灵感",
    "每天一个穿搭灵感": "灵感", "今天穿什么": "灵感", "穿搭合集": "灵感",
    "穿搭风格": "灵感", "穿搭bot": "灵感",
}

# ========== 仅保留 typo 归一化 ==========
typo_map = {
    "lululenmon": "lululemon",
    "不费力的穿撘": "不费力的穿搭",
}

# 词条黑名单（直接从话题表删除）
topic_blacklist = {
    "穿搭", "ootd", "ootd每日穿搭", "ootdinspo", "OOTD", "ootd穿搭",
    "每日穿搭", "日常穿搭", "时尚", "时尚穿搭",
    "男生穿搭",
}


# ========== 构建 ==========

topic_lookup = {}
for kw, views, participants in topic_daily_raw:
    topic_lookup[kw] = (views, participants)


def build_table(classification, blacklist=None):
    merged = {}
    seen = set()

    def add(raw_kw, search_idx=0, surging=False):
        kw = typo_map.get(raw_kw, raw_kw)
        if kw not in classification:
            return
        if blacklist and kw in blacklist:
            return
        if kw in seen:
            if search_idx > 0:
                merged[kw]["search_index_w"] = (merged[kw]["search_index_w"] or 0) + search_idx
                if surging:
                    merged[kw]["is_surging"] = "是"
            # also accumulate topic data if raw_kw not yet accounted
            if raw_kw in topic_lookup and raw_kw != kw:
                tv, tp = topic_lookup[raw_kw]
                merged[kw]["topic_views_w"] = (merged[kw]["topic_views_w"] or 0) + tv
                merged[kw]["topic_participants"] = (merged[kw]["topic_participants"] or 0) + tp
            return
        seen.add(kw)

        sub_cat = classification.get(kw, "其他")
        total_search = search_idx
        is_surging = surging

        total_tv = 0
        total_tp = 0
        checked = set()
        for k in [raw_kw, kw]:
            if k not in checked and k in topic_lookup:
                tv, tp = topic_lookup[k]
                total_tv += tv
                total_tp += tp
                checked.add(k)

        sources = []
        if total_search > 0:
            sources.append("热搜")
        if total_tv > 0:
            sources.append("话题")

        merged[kw] = {
            "keyword": kw,
            "search_index_w": round(total_search, 1) if total_search > 0 else "",
            "topic_views_w": round(total_tv, 1) if total_tv > 0 else "",
            "topic_participants": total_tp if total_tp > 0 else "",
            "source": "/".join(sources) if sources else "热搜",
            "sub_category": sub_cat,
            "is_surging": "是" if is_surging else "",
        }

    for kw, idx, surge in hot_search_weekly:
        add(kw, idx, surge)
    for kw, _, _ in topic_daily_raw:
        add(kw)

    return list(merged.values())


cat_records = build_table(categories_classification)
topic_records = build_table(topics_classification, blacklist=topic_blacklist)


# ========== 季节话题去重：同义组只保留热度最高的一个 ==========

def heat(r):
    si = r["search_index_w"] if isinstance(r["search_index_w"], (int, float)) else 0
    tv = r["topic_views_w"] if isinstance(r["topic_views_w"], (int, float)) else 0
    return max(si, tv)

seasonal_dedup_groups = [
    {"夏季穿搭", "夏天穿搭", "夏日穿搭", "夏季穿搭推荐"},
    {"春季穿搭", "春天穿搭"},
    {"早春穿搭", "穿搭早春"},
]

topic_idx = {r["keyword"]: r for r in topic_records}
to_drop = set()
for group in seasonal_dedup_groups:
    present = [kw for kw in group if kw in topic_idx]
    if len(present) <= 1:
        continue
    best = max(present, key=lambda kw: heat(topic_idx[kw]))
    for kw in present:
        if kw != best:
            to_drop.add(kw)

if to_drop:
    print(f"季节去重移除: {to_drop}")
topic_records = [r for r in topic_records if r["keyword"] not in to_drop]


def sort_key(r):
    si = r["search_index_w"] if isinstance(r["search_index_w"], (int, float)) else 0
    tv = r["topic_views_w"] if isinstance(r["topic_views_w"], (int, float)) else 0
    return -(max(si, tv))


cat_records.sort(key=sort_key)
topic_records.sort(key=sort_key)


def write_csv(filename, records, fields):
    filepath = os.path.join(data_dir, filename)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    print(f"✅ {filename}  ({len(records)} 行)")
    sub_cats = defaultdict(int)
    for r in records:
        sub_cats[r["sub_category"]] += 1
    for sc, count in sorted(sub_cats.items(), key=lambda x: -x[1]):
        print(f"   ├ {sc}: {count}")


fields = ["keyword", "search_index_w", "topic_views_w", "topic_participants", "source", "sub_category", "is_surging"]

print("=== 品类词表 ===")
write_csv("trends_categories.csv", cat_records, fields)
print()
print("=== 话题词表 ===")
write_csv("trends_topics.csv", topic_records, fields)
