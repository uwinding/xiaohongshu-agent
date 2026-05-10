import csv
import os
import re
from collections import defaultdict

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")


# ========== 原始数据 ==========

def _read_source_csv(filename, defaults):
    """Read source data from CSV file, fallback to hardcoded defaults."""
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        rows = []
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append([v.strip() for v in row.values()])
        return rows
    return defaults


_HOT_SEARCH_DEFAULTS = [
    ("穿搭", "1020.5", "False"), ("夏季穿搭", "391.6", "True"), ("春季穿搭", "374.1", "False"),
    ("lululenmon", "303.0", "True"), ("裙子", "285.1", "True"), ("夏天穿搭", "280.4", "True"),
    ("短袖", "273.4", "True"), ("韩系穿搭", "234.0", "False"), ("穿搭风格", "210.2", "False"),
    ("睡衣", "209.9", "False"), ("海边穿搭", "198.9", "False"), ("包包推荐", "196.8", "False"),
    ("lv包包", "191.2", "False"), ("连衣裙", "182.3", "True"), ("外套", "175.2", "True"),
    ("夏季穿搭推荐", "174.2", "True"), ("春天穿搭", "159.1", "False"), ("拉夫劳伦", "158.9", "False"),
    ("高跟鞋", "157.9", "True"), ("吊带", "152.7", "False"), ("鞋子推荐女", "152.5", "False"),
    ("阿迪达斯外套", "151.7", "True"), ("裤子", "150.6", "True"), ("鞋子", "149.2", "True"),
    ("包包", "148.6", "False"), ("优衣库", "146.3", "True"), ("lululemon", "145.4", "False"),
    ("旗袍", "145.3", "True"), ("五一穿搭", "144.0", "False"), ("裙子推荐", "142.4", "True"),
    ("洞洞鞋", "134.8", "True"), ("crocs洞洞鞋", "132.0", "True"), ("jk", "127.6", "True"),
    ("春夏穿搭", "127.4", "False"), ("帽子", "124.5", "True"), ("内衣", "122.8", "False"),
    ("牛仔裤", "122.5", "False"), ("男生穿搭", "122.3", "False"), ("香奈儿", "122.2", "False"),
    ("睡衣推荐夏天", "120.8", "False"), ("双肩包", "120.7", "False"), ("穿搭早春", "120.6", "False"),
    ("洞洞鞋推荐", "119.2", "True"), ("鬼冢虎", "119.1", "True"), ("衣服", "117.3", "False"),
    ("衬衫", "116.3", "True"), ("风衣穿搭", "113.2", "True"), ("半身裙", "112.7", "True"),
    ("衬衫穿搭", "110.8", "True"), ("短袖t恤推荐女", "110.8", "True"),
]

_TOPIC_INC_DEFAULTS = [
    ("星联联", "11.5亿", "3,480"),
    ("浪漫生活的记录者", "4.0亿", "10.0w"),
    ("ootd", "2.8亿", "8.6w"),
    ("羊毛羊绒大衣", "2.8亿", "1,270"),
    ("生活美学", "2.8亿", "12.3w"),
    ("氛围感", "2.8亿", "5.3w"),
    ("fyp", "2.6亿", "7.6w"),
    ("记录吧就现在", "2.5亿", "6.7w"),
    ("韩系穿搭", "2.4亿", "10.4w"),
    ("小红书市集春上新", "2.3亿", "12.0w"),
    ("我的日常", "2.0亿", "3,191"),
    ("来拍照了", "2.0亿", "2.2w"),
    ("ootd每日穿搭", "2.0亿", "3.7w"),
    ("穿搭", "1.9亿", "8,446"),
    ("显瘦穿搭", "1.8亿", "7.0w"),
    ("小个子穿搭", "1.7亿", "7.5w"),
    ("夏季穿搭", "1.7亿", "9.8w"),
    ("我的穿搭公式", "1.7亿", "1,871"),
    ("笔记灵感", "1.6亿", "1.6w"),
    ("审美积累", "1.6亿", "4.5w"),
    ("howto过春天", "1.6亿", "3.6w"),
    ("春夏穿搭", "1.5亿", "5.1w"),
    ("拍照姿势", "1.5亿", "2.5w"),
    ("微胖女孩的夏天", "1.4亿", "1,516"),
    ("日常文案", "1.4亿", "3.8w"),
    ("通勤穿搭", "1.4亿", "8.5w"),
    ("穿搭", "1.3亿", "6.7w"),
    ("海外生活", "1.3亿", "2.9w"),
    ("每日穿搭", "1.3亿", "1.8w"),
    ("测评", "1.2亿", "6,963"),
    ("秋冬穿搭2024高级感", "1.2亿", "3,040"),
    ("二次元秋日瞬间", "1.2亿", "2,528"),
    ("见到明星了", "1.2亿", "750"),
    ("夏日穿搭", "1.1亿", "9.3w"),
    ("日常穿搭", "1.1亿", "3.2w"),
    ("小红书618攻略", "1.1亿", "2.8w"),
    ("微胖穿搭", "1.1亿", "4.6w"),
    ("韩剧安娜穿搭", "1.1亿", "462"),
    ("ootdinspo", "1.0亿", "3.6w"),
    ("colorwalk", "1.0亿", "2.1w"),
    ("拍照", "1.0亿", "2.1w"),
    ("氛围感穿搭", "9936.8w", "4.5w"),
    ("时尚", "9756.5w", "4,203"),
    ("分享", "9616.7w", "2.0w"),
    ("松弛感穿搭", "9003.8w", "6.3w"),
    ("早春穿搭", "8843.8w", "4.3w"),
    ("春季穿搭", "8286.0w", "3.5w"),
    ("宝藏新品", "8077.6w", "4,223"),
    ("女大学生", "8005.1w", "8,427"),
    ("梨形身材", "7910.6w", "1.8w"),
    ("购物分享", "7851.4w", "1.6w"),
    ("五一出游穿搭", "7606.8w", "6.1w"),
    ("社会实验", "7444.5w", "1,695"),
    ("温柔穿搭", "7102.7w", "2.0w"),
    ("气质穿搭", "6874.1w", "1.8w"),
    ("连衣裙", "6804.9w", "1.0w"),
    ("分享我的日常", "6799.8w", "2.4w"),
    ("外扩", "6544.7w", "1,394"),
    ("汉服", "6453.2w", "2.7w"),
    ("穿搭灵感", "6289.1w", "1.6w"),
    ("穿搭bot", "6208.3w", "2.5w"),
    ("Tina面料测评", "6178.5w", "217"),
    ("平价好物", "6165.7w", "3.2w"),
    ("模特", "6106.0w", "1.5w"),
    ("冷皮暖皮", "6033.5w", "528"),
    ("平价穿搭", "5986.1w", "1.4w"),
    ("安娜温图尔", "5895.1w", "1,275"),
    ("短袖", "5760.7w", "3.5w"),
    ("闲鱼", "5738.1w", "4,382"),
    ("古早味", "5653.8w", "2.0w"),
    ("高级感穿搭", "5651.0w", "3.2w"),
    ("甜妹", "5647.8w", "1.2w"),
    ("ootd穿搭", "5524.2w", "2.1w"),
    ("不费力的穿搭", "5460.6w", "2.4w"),
    ("小红书RFL时尚轻单", "5438.6w", "1.9w"),
    ("当然要记录啊", "5343.8w", "5,519"),
    ("夏天穿搭", "5323.0w", "3.4w"),
    ("妈妈", "5322.1w", "4,320"),
    ("友好市集", "5296.8w", "11.8w"),
    ("女装", "5282.9w", "5,673"),
    ("神仙裙子", "5237.3w", "1.1w"),
    ("每天一个穿搭灵感", "5219.3w", "1.9w"),
    ("东方美学", "5154.7w", "2.0w"),
    ("健身穿搭", "5122.1w", "2.6w"),
    ("新春市集", "5117.4w", "7,232"),
    ("方圆脸", "5058.5w", "6,456"),
    ("OOTD", "5043.4w", "4.0w"),
    ("吃我一波lolita安利", "4978.9w", "2.7w"),
    ("牛仔裤", "4978.4w", "1.8w"),
    ("漂眉毛", "4959.9w", "923"),
    ("韩系", "4932.9w", "1.4w"),
    ("我的春天时刻", "4913.9w", "1.5w"),
    ("今天穿什么", "4908.6w", "2.0w"),
    ("女生", "4901.4w", "3,354"),
    ("浅春系穿搭", "4899.4w", "2.4w"),
    ("国风", "4887.8w", "8,461"),
    ("好看短剧", "4792.2w", "1,984"),
    ("穿搭技巧", "4712.1w", "7,270"),
    ("今天穿什么香", "4668.8w", "9,991"),
    ("穿搭分享", "4655.4w", "2.2w"),
]

_TOPIC_TOTAL_DEFAULTS = [
    ("笔记灵感", "2497.2亿", "4402.8w"),
    ("每日穿搭", "1212.2亿", "3684.9w"),
    ("我的日常", "1143.9亿", "2734.7w"),
    ("浪漫生活的记录者", "1006.1亿", "2881.8w"),
    ("穿搭", "859.3亿", "2005.6w"),
    ("日常穿搭", "748.9亿", "1968.1w"),
    ("ootd每日穿搭", "619.8亿", "1888.8w"),
    ("来拍照了", "549.1亿", "857.6w"),
    ("显瘦穿搭", "528.8亿", "1284.6w"),
    ("氛围感", "497.5亿", "966.1w"),
    ("小个子穿搭", "472.2亿", "1362.7w"),
    ("记录吧就现在", "460.4亿", "1414.5w"),
    ("秋冬穿搭", "444.6亿", "1156.4w"),
    ("Ootd", "375.8亿", "861.1w"),
    ("热门", "353.9亿", "391.7w"),
    ("ootd", "316.3亿", "936.5w"),
    ("拍照", "308.7亿", "875.7w"),
    ("测评", "284.5亿", "174.0w"),
    ("fyp", "279.0亿", "609.0w"),
    ("拍照姿势", "267.9亿", "375.4w"),
    ("今天穿什么香", "259.9亿", "805.4w"),
    ("韩系穿搭", "252.0亿", "1030.0w"),
    ("气质穿搭", "241.4亿", "755.4w"),
    ("海外生活", "217.1亿", "174.5w"),
    ("我的平价好物", "214.5亿", "391.0w"),
    ("夏日穿搭", "210.8亿", "742.1w"),
    ("生活美学", "208.8亿", "1144.2w"),
    ("微胖穿搭", "204.8亿", "370.6w"),
    ("时尚", "196.8亿", "362.3w"),
    ("购物分享", "193.4亿", "306.8w"),
    ("分享", "191.4亿", "359.5w"),
    ("夏季穿搭", "178.8亿", "748.7w"),
    ("女大学生", "177.9亿", "272.5w"),
    ("女生", "176.5亿", "143.4w"),
    ("尝试一个新look", "176.0亿", "417.3w"),
    ("小红书", "171.3亿", "496.6w"),
    ("每日分享", "160.6亿", "539.1w"),
    ("审美积累", "157.5亿", "427.8w"),
    ("笔记灵感", "156.5亿", "252.7w"),
    ("秋季穿搭", "151.3亿", "516.7w"),
    ("梨形身材", "151.1亿", "259.6w"),
    ("连衣裙", "142.1亿", "402.9w"),
    ("微胖女孩穿搭", "141.0亿", "214.3w"),
    ("温柔穿搭", "137.6亿", "405.9w"),
    ("想记录下此刻", "137.3亿", "2147.6w"),
    ("小个子女生穿搭", "135.8亿", "219.4w"),
    ("通勤穿搭", "134.7亿", "558.6w"),
    ("1年1度购物狂欢", "134.4亿", "1240.9w"),
    ("时尚穿搭", "133.9亿", "604.9w"),
    ("甜妹", "133.3亿", "277.5w"),
    ("国风", "127.8亿", "328.1w"),
    ("早春穿搭", "126.9亿", "336.5w"),
    ("汉服", "126.3亿", "410.2w"),
    ("羽绒服", "125.1亿", "258.4w"),
    ("显瘦神裤", "125.0亿", "395.0w"),
    ("春季穿搭", "124.6亿", "382.8w"),
    ("妈妈", "117.2亿", "88.5w"),
    ("新中式", "113.6亿", "504.5w"),
    ("氛围感穿搭", "111.8亿", "404.5w"),
    ("模特", "110.0亿", "222.2w"),
    ("韩系穿搭分享", "108.6亿", "259.1w"),
    ("辣妹穿搭", "107.6亿", "251.4w"),
    ("薯队长", "107.2亿", "280.9w"),
    ("我的开箱日常", "105.4亿", "209.7w"),
    ("复古穿搭", "102.2亿", "363.3w"),
    ("牛仔裤", "101.3亿", "322.5w"),
    ("平价好物", "100.5亿", "392.5w"),
    ("裤子", "100.2亿", "345.7w"),
    ("宝藏店铺", "99.8亿", "496.4w"),
    ("方圆脸", "99.0亿", "99.6w"),
    ("高级感穿搭", "97.1亿", "472.6w"),
    ("平价穿搭", "96.0亿", "220.2w"),
    ("休闲穿搭", "95.6亿", "282.9w"),
    ("职场通勤穿搭", "95.5亿", "194.2w"),
    ("生日", "93.3亿", "257.2w"),
    ("梨形身材穿搭", "89.4亿", "227.0w"),
    ("辣妹", "88.6亿", "182.7w"),
    ("身材", "88.2亿", "68.4w"),
    ("夏天", "87.0亿", "264.6w"),
    ("海边拍照", "86.8亿", "184.4w"),
    ("初秋穿搭", "85.6亿", "168.4w"),
    ("日常文案", "83.2亿", "307.9w"),
    ("好搭的裤子", "83.0亿", "258.6w"),
    ("私藏店铺", "80.5亿", "323.9w"),
    ("神仙裙子", "80.0亿", "171.5w"),
    ("大大方方做自己", "79.8亿", "187.2w"),
    ("平价", "79.4亿", "178.9w"),
    ("服装测评", "79.1亿", "67.6w"),
    ("裤子种草", "78.9亿", "287.8w"),
    ("这个模板有点东西", "78.7亿", "1847.3w"),
    ("约会穿搭", "78.4亿", "216.9w"),
    ("毛衣", "78.2亿", "241.9w"),
    ("穿搭", "77.5亿", "202.0w"),
    ("外套", "76.3亿", "277.6w"),
    ("旗袍", "75.7亿", "225.4w"),
    ("感谢小红书平台我要上热门", "74.8亿", "163.6w"),
    ("大衣", "74.7亿", "137.6w"),
    ("小红书涨粉", "73.8亿", "195.0w"),
    ("高个子穿搭", "73.5亿", "128.2w"),
    ("复古", "73.2亿", "289.2w"),
]

hot_search_raw = _read_source_csv("source_hot_search.csv", _HOT_SEARCH_DEFAULTS)
topic_inc_raw = _read_source_csv("source_topic_inc.csv", _TOPIC_INC_DEFAULTS)
topic_total_raw = _read_source_csv("source_topic_total.csv", _TOPIC_TOTAL_DEFAULTS)

hot_search = [(kw, float(idx), surge == "True") for kw, idx, surge in hot_search_raw]
topic_inc = [(kw, v, p) for kw, v, p in topic_inc_raw]
topic_total = [(kw, v, p) for kw, v, p in topic_total_raw]

# ========== 单位解析 ==========

def parse_views(s):
    s = s.strip()
    if "亿" in s:
        return round(float(s.replace("亿", "")) * 10000, 1)
    elif "w" in s.lower():
        return round(float(s.lower().replace("w", "")), 1)
    else:
        return round(float(s), 1)

def parse_participants(s):
    s = s.strip().replace(",", "")
    if "w" in s.lower():
        return round(float(s.lower().replace("w", "")), 1)
    else:
        return round(float(s) / 10000, 4)


# ========== 分类与归一化 ==========

topics_classification = {
    "夏季穿搭": "季节", "夏天穿搭": "季节", "夏日穿搭": "季节",
    "春季穿搭": "季节", "春天穿搭": "季节", "春夏穿搭": "季节",
    "早春穿搭": "季节", "穿搭早春": "季节", "浅春系穿搭": "季节",
    "海边穿搭": "场景", "五一穿搭": "场景", "通勤穿搭": "场景",
    "健身穿搭": "场景", "出游穿搭": "场景", "约会穿搭": "场景",
    "五一出游穿搭": "场景", "colorwalk": "场景", "职场通勤穿搭": "场景",
    "韩系穿搭": "风格", "韩系": "风格", "松弛感穿搭": "风格",
    "温柔穿搭": "风格", "气质穿搭": "风格", "高级感穿搭": "风格",
    "慵懒感穿搭": "风格", "日系穿搭": "风格", "东方美学": "风格",
    "国风": "风格", "休闲穿搭": "风格", "不费力的穿搭": "风格",
    "氛围感穿搭": "风格", "甜妹": "风格", "复古穿搭": "风格",
    "辣妹穿搭": "风格", "新中式": "风格", "韩系穿搭分享": "风格",
    "韩剧安娜穿搭": "风格", "初秋穿搭": "风格", "秋季穿搭": "风格",
    "秋冬穿搭": "风格", "秋冬穿搭2024高级感": "风格", "复古": "风格",
    "小个子穿搭": "人群", "微胖穿搭": "人群", "梨形身材": "人群",
    "梨形身材穿搭": "人群", "方圆脸": "人群", "微胖女孩的夏天": "人群",
    "微胖女孩穿搭": "人群", "小个子女生穿搭": "人群", "高个子穿搭": "人群",
    "显瘦穿搭": "概念", "氛围感": "概念", "生活美学": "概念",
    "审美积累": "概念", "今天穿什么香": "概念", "今天穿什么": "概念",
    "显瘦神裤": "概念", "我的穿搭公式": "概念",
    "穿搭灵感": "灵感", "穿搭技巧": "灵感", "穿搭分享": "灵感",
    "每天一个穿搭灵感": "灵感", "穿搭合集": "灵感", "穿搭风格": "灵感",
    "穿搭bot": "灵感",
}

normalize_map = {
    "lululenmon": "lululemon",
    "不费力的穿撘": "不费力的穿搭",
    "穿搭早春": "早春穿搭",
    "ootd每日穿搭": "ootd",
    "ootdinspo": "ootd",
    "ootd穿搭": "ootd",
    "Ootd": "ootd",
    "OOTD": "ootd",
    "夏天穿搭": "夏季穿搭",
    "夏日穿搭": "夏季穿搭",
    "春天穿搭": "春季穿搭",
    "穿搭早春": "早春穿搭",
    "夏季穿搭推荐": "夏季穿搭",
}

# 非穿搭/与项目无关的话题黑名单
irrelevant = {
    "星联联", "fyp", "记录吧就现在", "来拍照了", "我的日常", "笔记灵感",
    "日常文案", "海外生活", "测评", "拍照", "拍照姿势", "分享", "分享我的日常",
    "小红书市集春上新", "小红书618攻略", "小红书", "宝藏新品", "宝藏店铺",
    "薯队长", "我的开箱日常", "想记录下此刻", "这个模板有点东西",
    "1年1度购物狂欢", "尝试一个新look", "热门", "小红书涨粉",
    "感谢小红书平台我要上热门", "当然要记录啊", "友好市集", "新春市集",
    "社会实验", "见到明星了", "二次元秋日瞬间", "安娜温图尔",
    "漂眉毛", "外扩", "冷皮暖皮", "Tina面料测评", "好看短剧",
    "模特", "妈妈", "女生", "生日", "身材", "衣服", "内衣",
    "闲鱼", "平价", "私藏店铺", "好搭的裤子", "裤子种草",
    "羊毛羊绒大衣", "毛衣", "大衣", "羽绒服",
    "howto过春天", "我的春天时刻", "我的平价好物", "香水",
    "大大方方做自己",
}

# 季节去重（同义组保留热度最高的）
seasonal_groups = [
    {"夏季穿搭", "夏天穿搭", "夏日穿搭", "夏季穿搭推荐"},
    {"春季穿搭", "春天穿搭", "春夏穿搭"},
    {"早春穿搭", "穿搭早春"},
]


# ========== 构建合并表 ==========

def norm_kw(kw):
    return normalize_map.get(kw.strip().strip("#").strip(), kw.strip().strip("#").strip())

# ---- 热词榜 ----
search_idx_map = {}
search_surging_map = {}
for kw, idx, surge in hot_search:
    nk = norm_kw(kw)
    search_idx_map[nk] = search_idx_map.get(nk, 0) + idx
    if surge:
        search_surging_map[nk] = True

# ---- 话题增量榜 ----
inc_views_map = {}
inc_parts_map = {}
for kw, v, p in topic_inc:
    nk = norm_kw(kw)
    inc_views_map[nk] = inc_views_map.get(nk, 0) + parse_views(v)
    inc_parts_map[nk] = inc_parts_map.get(nk, 0) + parse_participants(p)

# ---- 话题总量榜 ----
tot_views_map = {}
tot_parts_map = {}
for kw, v, p in topic_total:
    nk = norm_kw(kw)
    tot_views_map[nk] = tot_views_map.get(nk, 0) + parse_views(v)
    tot_parts_map[nk] = tot_parts_map.get(nk, 0) + parse_participants(p)

# ---- 所有唯一关键词 ----
all_keywords = set()
all_keywords.update(search_idx_map.keys())
all_keywords.update(inc_views_map.keys())
all_keywords.update(tot_views_map.keys())

# 排除非穿搭词
all_keywords -= irrelevant

# ---- 按分类过滤 + 分类 ----
classified = {kw for kw in all_keywords if kw in topics_classification}
# 没有分类但出现在热词榜或话题榜的、与穿搭相关的品类词也保留
product_words = {
    "短袖", "连衣裙", "旗袍", "衬衫", "裤子", "牛仔裤", "半身裙",
    "外套", "风衣穿搭", "高跟鞋", "洞洞鞋", "鬼冢虎",
    "裙子", "帽子", "双肩包", "lv包包", "包包", "睡衣",
    "鞋子", "吊带", "短袖t恤推荐女", "裙子推荐", "包包推荐",
    "鞋子推荐女", "睡衣推荐夏天", "洞洞鞋推荐", "衣服", "女装",
}

all_keywords = classified | {kw for kw in all_keywords if kw in product_words}


# ---- 构建记录 ----
records = []
for kw in sorted(all_keywords):
    si = search_idx_map.get(kw, 0)
    surging = search_surging_map.get(kw, False)
    iv = inc_views_map.get(kw, 0)
    ip = inc_parts_map.get(kw, 0)
    tv = tot_views_map.get(kw, 0)
    tp = tot_parts_map.get(kw, 0)

    sub_cat = topics_classification.get(kw, "品类参考")

    # 参与率
    inc_eng = round(ip / iv * 100, 2) if iv > 0 else 0
    tot_eng = round(tp / tv * 100, 2) if tv > 0 else 0

    # 增量占比 = 增量浏览量(万) / 总量浏览量(万) × 100
    inc_ratio = round(iv / tv * 100, 2) if tv > 0 and iv > 0 else 0

    # ---- 生命周期判定 (双维度: inc_ratio + total_views, 对齐设计文档 §4.1) ----
    # tv 单位: 万; 500亿=5,000,000万; 100亿=1,000,000万
    _BURST_TV = 5000000
    _GROWTH_TV = 1000000
    signals = []
    life_stage = "观察"

    if surging:
        signals.append("搜索飙升")

    if iv > 0 and tv > 0:
        if inc_ratio > 1.5 and tv > _BURST_TV:
            life_stage = "爆发期"
            signals.append(f"增占比{inc_ratio}%+总量超500亿(爆发期)")
        elif inc_ratio >= 0.5 and tv >= _GROWTH_TV:
            life_stage = "增长期"
            signals.append(f"增占比{inc_ratio}%+总量100-500亿(增长期)")
        elif inc_ratio >= 0.5 and tv < _GROWTH_TV:
            life_stage = "萌芽期"
            signals.append(f"增占比{inc_ratio}%+总量<100亿(萌芽期)")
        elif inc_ratio < 0.5 and tv >= _GROWTH_TV:
            life_stage = "成熟期"
            signals.append(f"增占比{inc_ratio}%+总量>100亿(成熟期)")
        else:
            life_stage = "萌芽期"
            signals.append(f"增占比{inc_ratio}%(萌芽期-小基数)")
    elif iv > 0 and tv == 0:
        life_stage = "萌芽期"
        signals.append("仅增量有数据(萌芽)")
    elif si > 0 and iv == 0 and tv == 0:
        life_stage = "需求期"
        signals.append("仅有搜索需求")
    elif iv == 0 and tv > 0:
        life_stage = "观察"
        signals.append("仅总量数据(观察)")

    if si > 200:
        signals.append(f"搜索需求强({si}w)")
    elif si > 100:
        signals.append(f"搜索需求中({si}w)")

    if tot_eng > 0.05:
        signals.append("总量参与率高")
    elif tot_eng > 0:
        signals.append("总量参与率偏低")

    # ---- 策略方向 ----
    direction = ""
    stage = life_stage
    if sub_cat == "风格" and stage in ("增长期", "爆发期"):
        direction = f"穿搭风格方向：{kw}，处于{stage}，建议抢占该风格标签"
    elif sub_cat == "人群" and stage != "成熟期":
        direction = f"定向内容：{kw}，精准触达该人群"
    elif sub_cat == "场景" and stage in ("增长期", "爆发期"):
        direction = f"场景化选题：{kw}，配合场景推送"
    elif sub_cat == "概念":
        direction = f"概念类内容：{kw}，提升内容差异化"
    elif sub_cat == "季节":
        direction = f"季节性内容：{kw}，结合节气推送"
    elif sub_cat == "灵感":
        direction = f"日常灵感：{kw}，稳定输出"
    elif sub_cat == "品类参考":
        direction = f"选品参考：{kw}，关注商品供给"
    if not direction:
        direction = f"参考方向：{kw}"

    # ---- 竞争度：该词话题浏览量占同子类总话题浏览量的比例 ----
    # Fix: 品类参考词也计算竞争度（所有品类参考词共享同一竞争池）
    competition = 0
    if tv > 0:
        if kw in classified:
            cat_key = topics_classification[kw]
            cat_views = sum(
                tot_views_map.get(k, 0)
                for k in all_keywords
                if topics_classification.get(k) == cat_key and k != kw and tot_views_map.get(k, 0) > 0
            )
        else:
            cat_views = sum(
                tot_views_map.get(k, 0)
                for k in all_keywords
                if topics_classification.get(k) is None and k != kw and tot_views_map.get(k, 0) > 0
            )
        denominator = tv + cat_views
        competition = round(tv / denominator * 100, 1) if denominator > 0 else 0

    # ---- recommend_for：决定该词应该路由到哪个下游 Skill ----
    # 风格/人群/概念类始终路由到"风格"（不受 lifecycle 限制），供 OutfitComposer 做风格方向
    if sub_cat == "品类参考" or si > 100:
        recommend_for = "选品"
    elif sub_cat == "风格":
        recommend_for = "风格"
    elif sub_cat == "人群":
        recommend_for = "风格"
    elif sub_cat == "概念":
        recommend_for = "风格"
    elif sub_cat in ("季节", "场景") and life_stage in ("增长期", "爆发期", "萌芽期"):
        recommend_for = "风格"
    else:
        recommend_for = "标签"
    if inc_ratio > 0.3 and inc_eng > 0.02 and recommend_for == "选品":
        recommend_for = "综合"

    # ---- 综合优先级 ----
    score = 0
    if surging: score += 3
    if si > 300: score += 2
    elif si > 100: score += 1
    if inc_ratio > 3: score += 3
    elif inc_ratio > 1.5: score += 2
    elif inc_ratio > 0.5: score += 1
    if tot_eng > 0.05: score += 1
    if tv > 500: score += 1
    if sub_cat in ("风格", "人群", "场景"): score += 1
    # 高搜索需求但无增量数据的品类，仍有选品价值
    if sub_cat == "品类参考" and surging and si > 200: score += 2
    if life_stage == "需求期" and si > 200: score += 1

    if score >= 5:
        priority = "高"
    elif score >= 3:
        priority = "中"
    else:
        priority = "低"

    # 简短行动建议
    if recommend_for == "综合":
        action = f"综合推荐：{kw}（搜索{si}w，增占比{inc_ratio}%）"
    elif recommend_for == "选品":
        action = f"优先备货：{kw}（搜索{si}w）" if si > 100 else f"可备选：{kw}"
    elif recommend_for == "风格":
        action = f"穿搭方向：{kw}（{life_stage}，增占比{inc_ratio}%）"
    else:
        action = f"话题标签：{kw}（参与率{inc_eng}%）"

    records.append({
        "keyword": kw,
        "category": sub_cat,
        "lifecycle": life_stage,
        "search_index_w": round(si, 1) if si > 0 else "",
        "is_surging": 1 if surging else 0,
        "inc_views_w": round(iv, 1) if iv > 0 else "",
        "inc_participants_w": round(ip, 4) if ip > 0 else "",
        "total_views_yi": round(tv / 10000, 1) if tv > 0 else "",
        "total_participants_w": round(tp, 1) if tp > 0 else "",
        "inc_engagement_pct": round(inc_eng, 2) if inc_eng > 0 else "",
        "total_engagement_pct": round(tot_eng, 2) if tot_eng > 0 else "",
        "inc_ratio_pct": round(inc_ratio, 2) if inc_ratio > 0 else "",
        "competition_pct": competition if competition > 0 else "",
        "priority": priority,
        "recommend_for": recommend_for,
        "action_note": action,
    })

# ---- 季节去重 ----
recs_by_kw = {r["keyword"]: r for r in records}
drop = set()
for group in seasonal_groups:
    present = [kw for kw in group if kw in recs_by_kw]
    if len(present) <= 1:
        continue
    def heat(kw):
        return tot_views_map.get(kw, 0) + inc_views_map.get(kw, 0)
    best = max(present, key=heat)
    for kw in present:
        if kw != best:
            drop.add(kw)
records = [r for r in records if r["keyword"] not in drop]

# ---- 排序 ----
def sort_key(r):
    pri_map = {"高": 0, "中": 1, "低": 2, "观察": 3}
    stage_map = {"爆发期": 0, "增长期": 1, "需求期": 2, "萌芽期": 3, "成熟期": 4, "观察": 5}
    si = r["search_index_w"] if isinstance(r["search_index_w"], (int, float)) else 0
    inc = r["inc_views_w"] if isinstance(r["inc_views_w"], (int, float)) else 0
    return (pri_map.get(r["priority"], 9), stage_map.get(r["lifecycle"], 9), -(max(si, inc)))

records.sort(key=sort_key)


# ========== 写入 CSV ==========

fields = [
    "keyword", "category", "lifecycle", "search_index_w", "is_surging",
    "inc_views_w", "inc_participants_w", "total_views_yi", "total_participants_w",
    "inc_engagement_pct", "total_engagement_pct", "inc_ratio_pct", "competition_pct",
    "priority", "recommend_for", "action_note"
]

path = os.path.join(data_dir, "strategy_full.csv")
with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in records:
        w.writerow(r)

print(f"✅ strategy_full.csv ({len(records)} 行)")
print()

# 打印摘要
stages = defaultdict(int)
pris = defaultdict(int)
cats = defaultdict(int)
recs_for = defaultdict(int)
for r in records:
    stages[r["lifecycle"]] += 1
    pris[r["priority"]] += 1
    cats[r["category"]] += 1
    recs_for[r["recommend_for"]] += 1

print("=== 生命周期分布 ===")
for s, c in sorted(stages.items(), key=lambda x: -x[1]):
    print(f"  {s}: {c}")
print()
print("=== 优先级分布 ===")
for p in ["高", "中", "低"]:
    print(f"  {p}: {pris.get(p, 0)}")
print()
print("=== 下游路由分布 ===")
for f, c in sorted(recs_for.items(), key=lambda x: -x[1]):
    print(f"  → {f}: {c}")
print()
print("=== 分类分布 ===")
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")
print()

print("--- 高优先级详情 ---")
for r in records:
    if r["priority"] == "高":
        print(f"  {r['keyword']} ({r['category']}) | lifecycle:{r['lifecycle']} | search:{r['search_index_w']} | inc_ratio:{r['inc_ratio_pct']}% | → {r['recommend_for']}")
print()
print("--- 中优先级（增长期 + 风格/人群/场景） ---")
for r in records:
    if r["priority"] == "中" and r["lifecycle"] in ("增长期", "爆发期") and r["category"] in ("风格", "人群", "场景", "季节"):
        print(f"  {r['keyword']} ({r['category']}) | lifecycle:{r['lifecycle']} | inc_ratio:{r['inc_ratio_pct']}% | search:{r['search_index_w']} | → {r['recommend_for']} | {r['action_note']}")
