# test_planner_chat.py
"""对话式需求收集的规则部分自测：不联网，直接验证抽取 / 规范化 / 缺失项计算"""
import asyncio
from datetime import date, timedelta

from services import planner_chat as pc

print("===== 测试 1：draft 规范化 =====")
draft = pc.normalize_draft({
    "origin": "北京",
    "destination": "北京",           # 与出发地相同 -> 清空出发地
    "start_date": "2020-01-01",      # 过去日期 -> 作废
    "travelers": 99,                  # 超出范围 -> 清空
    "budget": 50,                     # 低于下限 -> 清空
    "hotel_level": "五星",            # 非法档位 -> 清空
    "preferences": ["美食", "乱写"],  # 非法偏好 -> 丢弃
})
assert draft["origin"] == "" and draft["destination"] == "北京", draft
assert draft["start_date"] == "" and draft["end_date"] == "", draft
assert draft["travelers"] is None and draft["budget"] is None, draft
assert draft["hotel_level"] == "" and draft["preferences"] == ["美食"], draft
print("✅ 非法值被清空，合法值保留")

print("\n===== 测试 2：模型返回 ISO 时间也能解析 =====")
draft = pc.normalize_draft({
    "start_date": "2026-12-01T00:00:00",
    "end_date": "2026-12-03T00:00:00",
})
assert draft["start_date"] == "2026-12-01" and draft["end_date"] == "2026-12-03", draft
print("✅ T 分隔的时间被截成日期")

print("\n===== 测试 3：合并时不清空已有信息 =====")
base = pc.normalize_draft({"origin": "上海", "destination": "大理", "travelers": 2})
merged = pc.merge_draft(base, {"destination": "丽江"})
assert merged["origin"] == "上海" and merged["destination"] == "丽江", merged
assert merged["travelers"] == 2, merged
print("✅ 新字段覆盖旧值，未提到的字段保留")

print("\n===== 测试 4：规则抽取 =====")
start = (date.today() + timedelta(days=10)).isoformat()
text = f"从北京去成都玩，{start} 出发，两个人，预算5000元，想住舒适型，喜欢吃火锅看古迹"
extracted = pc._fallback_extract(text)
assert extracted["origin"] == "北京" and extracted["destination"] == "成都", extracted
assert extracted["travelers"] == 2 and extracted["budget"] == 5000, extracted
assert extracted["hotel_level"] == "舒适型", extracted
assert "美食" in extracted["preferences"] and "历史文化" in extracted["preferences"], extracted
assert extracted["start_date"] == start, extracted

extracted = pc._fallback_extract("我们三个人，人均预算2000，下周去厦门")
assert extracted["travelers"] == 3 and extracted["budget"] == 6000, extracted
assert extracted["destination"] == "厦门", extracted

extracted = pc._fallback_extract("12月5日去西安，三天两晚")
assert extracted["start_date"].endswith("-12-05"), extracted
assert extracted["end_date"].endswith("-12-07"), extracted
print("✅ 城市 / 日期 / 人数 / 预算 / 档次 / 偏好都能抠出来")

print("\n===== 测试 5：缺失项与开场白 =====")
assert pc.missing_fields({}) == ["origin", "destination", "dates", "travelers", "budget", "hotel_level"]
assert pc.missing_fields(pc.normalize_draft({
    "origin": "北京", "destination": "成都",
    "start_date": "2026-12-01", "end_date": "2026-12-03",
    "travelers": 2, "budget": 5000, "hotel_level": "舒适型",
})) == []

opening = asyncio.run(pc.chat_turn([], {}))
assert opening["reply"] and opening["suggestions"], opening
assert opening["ready"] is False
print("✅ 缺失项计算正确，空历史返回开场白且不调用模型")

print("\n全部通过 🎉")
