# services/agent.py
import json
import time
from openai import AsyncOpenAI
from config import settings
from services.amap import (
    get_intercity_info,
    get_route_time,
    search_hotels,
    search_places,
)

client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL
)

# 1. 定义工具
# 注意：我们把名字改成了 "get_route"，和模型习惯的名字对齐
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": "根据关键词和城市搜索真实的景点或旅游地点",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {"type": "string", "description": "搜索关键词，例如：武侯祠、大熊猫基地"},
                    "city": {"type": "string", "description": "所在城市，例如：成都"}
                },
                "required": ["keywords", "city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "获取两个经纬度坐标之间的交通耗时（分钟）",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_lnglat": {"type": "string", "description": "起点经纬度，格式：经度,纬度"},
                    "dest_lnglat": {"type": "string", "description": "终点经纬度，格式：经度,纬度"},
                    "mode": {"type": "string", "enum": ["transit", "driving"], "description": "交通方式：transit 公交，driving 驾车"}
                },
                "required": ["origin_lnglat", "dest_lnglat"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_intercity_transport",
            "description": (
                "查询出发城市到目的城市之间的城际交通基础数据：两座城市中心坐标、"
                "真实驾车距离（公里）与耗时（分钟）。高铁和航班据此按常识估算。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_city": {"type": "string", "description": "出发城市，例如：北京"},
                    "dest_city": {"type": "string", "description": "目的城市，例如：成都"}
                },
                "required": ["origin_city", "dest_city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "根据关键词和城市搜索真实酒店，返回名称、地址、评分和参考价格",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词，建议带上商圈或景点，例如：春熙路 酒店"
                    },
                    "city": {"type": "string", "description": "所在城市，例如：成都"}
                },
                "required": ["keywords", "city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_itinerary",
            "description": (
                "提交最终行程。当你已经查清城际交通、酒店、景点和市内交通，"
                "行程与预算都安排完成时调用它。调用后本次规划立即结束，不要再调用其他工具。"
                "所有金额都是「全部出行人的合计」。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "出发城市"},
                    "destination": {"type": "string", "description": "目的地城市"},
                    "transport": {
                        "type": "object",
                        "description": "城际交通方案：1 个推荐方案 + 1-2 个备选方案",
                        "properties": {
                            "recommended": {
                                "type": "object",
                                "properties": {
                                    "mode": {
                                        "type": "string",
                                        "enum": ["high_speed_rail", "train", "flight", "bus", "driving"]
                                    },
                                    "summary": {"type": "string", "description": "如：北京西 → 成都东 G89 次二等座"},
                                    "departure_time": {"type": "string", "description": "HH:MM"},
                                    "arrival_time": {"type": "string", "description": "HH:MM"},
                                    "duration_minutes": {"type": "integer", "description": "单程耗时（分钟）"},
                                    "cost": {"type": "number", "description": "全部出行人的往返交通费（元）"},
                                    "note": {"type": "string", "description": "补充说明，如是否含市内接驳"}
                                },
                                "required": ["mode", "summary", "cost"]
                            },
                            "alternatives": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "mode": {
                                            "type": "string",
                                            "enum": ["high_speed_rail", "train", "flight", "bus", "driving"]
                                        },
                                        "summary": {"type": "string"},
                                        "duration_minutes": {"type": "integer"},
                                        "cost": {"type": "number", "description": "全部出行人的往返交通费（元）"},
                                        "note": {"type": "string"}
                                    },
                                    "required": ["mode", "summary", "cost"]
                                }
                            }
                        },
                        "required": ["recommended"]
                    },
                    "hotel": {
                        "type": "object",
                        "description": "住宿方案：全程住同一家酒店",
                        "properties": {
                            "name": {"type": "string"},
                            "address": {"type": "string"},
                            "lng": {"type": "number"},
                            "lat": {"type": "number"},
                            "rating": {"type": "string", "description": "评分，如 4.6"},
                            "check_in_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "check_out_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "nights": {"type": "integer", "description": "晚数，通常为行程天数 - 1"},
                            "rooms": {"type": "integer", "description": "房间数"},
                            "price_per_night": {"type": "number", "description": "全部房间每晚合计（元）"},
                            "cost": {"type": "number", "description": "住宿总价（元）"},
                            "note": {"type": "string", "description": "如：近地铁 2 号线，含早餐"}
                        },
                        "required": ["name", "nights", "price_per_night", "cost"]
                    },
                    "budget": {
                        "type": "object",
                        "description": (
                            "预算分项。交通/住宿由系统按 transport、hotel 计算；"
                            "餐饮/门票玩乐/购物由系统按行程项自动汇总；这里只需填市内交通和其他。"
                        ),
                        "properties": {
                            "local_transport": {"type": "number", "description": "市内打车/地铁合计（元）"},
                            "other": {"type": "number", "description": "其他花费（纪念品、应急等，元）"}
                        }
                    },
                    "days": {
                        "type": "array",
                        "description": "每天的行程",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day_index": {"type": "integer", "description": "第几天，从 1 开始"},
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "place_name": {
                                                "type": "string",
                                                "description": "地点名称，只写地名（如：天坛公园），活动描述放到 note"
                                            },
                                            "start_time": {"type": "string", "description": "HH:MM"},
                                            "end_time": {"type": "string", "description": "HH:MM"},
                                            "category": {
                                                "type": "string",
                                                "enum": [
                                                    "sightseeing",
                                                    "food",
                                                    "shopping",
                                                    "entertainment",
                                                    "other"
                                                ],
                                                "description": "景点/餐饮/购物/玩乐/其他"
                                            },
                                            "cost_estimate": {
                                                "type": "number",
                                                "description": "该项全部出行人的预估花费（元）"
                                            },
                                            "note": {"type": "string", "description": "如：建议点招牌菜、需提前预约"},
                                            "lng": {"type": "number"},
                                            "lat": {"type": "number"}
                                        },
                                        "required": ["place_name", "start_time", "end_time", "category"]
                                    }
                                }
                            },
                            "required": ["day_index", "items"]
                        }
                    }
                },
                "required": ["origin", "destination", "transport", "days"]
            }
        }
    }
]

# 2. 系统提示词模板
PROMPT_TEMPLATE = """
你是一名资深旅行规划师，要为用户输出一份可以直接执行的完整行程：
城际交通（怎么去）、酒店住宿（住哪里）、每天吃喝玩乐怎么安排，以及分类预算。

可用工具：
1. search_places(keywords, city)：搜索真实的景点或旅游地点，返回名称和经纬度。
2. get_intercity_transport(origin_city, dest_city)：查询两座城市之间的真实驾车距离和耗时。
3. search_hotels(keywords, city)：搜索真实酒店，返回名称、地址、评分和参考价。
4. get_route(origin_lnglat, dest_lnglat, mode)：计算市内两点之间的交通耗时（分钟）。
5. submit_itinerary(...)：提交最终行程，信息足够后调用它结束规划。

工作流程：
1. 先调用一次 get_intercity_transport，拿到出发地到目的地的距离，用来判断该选什么交通工具。
2. 城际交通：
   - 距离 ≤ 400 公里优先高铁/动车；400-1200 公里给出高铁和飞机并比较；>1200 公里优先飞机。
   - 必须给出 1 个推荐方案和 1-2 个备选方案，说明耗时和费用。
   - 高铁/航班的时间和票价按常识估算（二等座约 0.45 元/公里；经济舱约 0.7-1.0 元/公里，另加基建燃油）；
     自驾用工具返回的距离、耗时和油费过路费。
   - 费用按「全部出行人往返」计算，不要只写单人单程。
3. 酒店：
   - 用 search_hotels 搜索 1-2 次，选择 1 家真实酒店，位置靠近主要景点或地铁站，档次和价位符合用户要求。
   - 入住晚数 = 行程天数 - 1（至少 1 晚），第一天入住、最后一天退房。
   - 如果用户是当天往返的一日游，可以不填酒店。
   - 房间数按人数估算（2 人 1 间，3-4 人 2 间），price_per_night 是全部房间每晚合计。
4. 每日行程：
   - 城际交通已经写在 transport 里，不要再把车次/航班作为某一天的行程项；从抵达目的地后的活动开始排。
   - place_name 只写地点本身的名字，例如「天坛公园」「鲜鱼口美食街」「故宫博物院」；
     不要写「酒店办理入住 + 周边简餐」「看升旗/拍照」这类活动描述，活动说明写进 note。
   - 每天安排 2-4 个地点，按地理位置顺路排序，用 get_route 确认关键路段耗时。
   - 必须包含餐饮：午餐、晚餐尽量作为 category=food 的行程项（写明餐馆或美食街）。
   - 每个行程项都要尽量通过 search_places 查到真实地点并填 lng/lat；确实查不到的再省略（系统会自动补全）。
   - 每个行程项的 category 只能是：sightseeing（景点门票）、food（餐饮）、
     shopping（购物）、entertainment（玩乐）、other（其他）。
5. 预算：
   - 交通、住宿、餐饮、门票玩乐、购物、市内交通、其他都要算到，不能遗漏。
   - 餐饮/门票玩乐/购物会按行程项自动汇总，请保证每个收费项目都写进成本；
     市内交通（local_transport）单独估算每天打车/地铁的花费，其他花费写进 other。
   - 总花费（交通 + 住宿 + 餐饮 + 门票玩乐 + 购物 + 市内交通 + 其他）不得超过用户预算；
     超了就换更便宜的酒店、减少收费景点或调整交通方式。
6. 所有地点尽量带上经纬度；同一个地点不要重复查询。
7. 信息足够后调用 submit_itinerary 提交，不要再输出解释文字。

如果无法调用 submit_itinerary，就直接输出最终行程 JSON（不要用 Markdown 代码块包裹），格式如下：
{
  "origin": "北京",
  "destination": "成都",
  "transport": {
    "recommended": {
      "mode": "high_speed_rail",
      "summary": "北京西 → 成都东 G89 次二等座",
      "departure_time": "08:00",
      "arrival_time": "14:24",
      "duration_minutes": 384,
      "cost": 3600,
      "note": "含往返，2 人"
    },
    "alternatives": [
      {"mode": "flight", "summary": "首都机场 → 天府机场", "duration_minutes": 180, "cost": 5200, "note": "含往返和机建燃油"}
    ]
  },
  "hotel": {
    "name": "成都春熙路某酒店",
    "address": "锦江区春熙路",
    "rating": "4.6",
    "check_in_date": "2026-01-01",
    "check_out_date": "2026-01-04",
    "nights": 3,
    "rooms": 1,
    "price_per_night": 420,
    "cost": 1260,
    "note": "近地铁 2 号线，含早餐"
  },
  "budget": {"local_transport": 300, "other": 200},
  "days": [
    {
      "day_index": 1,
      "items": [
        {
          "place_name": "武侯祠",
          "start_time": "09:30",
          "end_time": "11:30",
          "category": "sightseeing",
          "cost_estimate": 100,
          "note": "2 人门票",
          "lng": 104.047992,
          "lat": 30.646168
        }
      ]
    }
  ]
}
"""

MODEL = "deepseek-chat"  # 如果你用的是其他模型，请替换

# --- 循环控制：主终止条件是「模型不再调用工具 / 调用 submit_itinerary」 ---
# 下面这些只是防止异常情况（模型卡住、重复查询、接口太慢）的保险丝，正常不会触发。
HARD_MAX_ROUNDS = 18       # 硬上限：最多思考几轮
MAX_TOOL_CALLS = 36        # 预算：整个规划最多执行多少次工具调用
TIME_BUDGET_SECONDS = 180  # 预算：整个规划最多耗时多少秒
REPEAT_LIMIT = 2           # 连续出现同样工具调用的次数上限
SUBMIT_TOOL_NAME = "submit_itinerary"

ITEM_CATEGORIES = {"sightseeing", "food", "shopping", "entertainment", "other"}
TRANSPORT_MODES = {"high_speed_rail", "train", "flight", "bus", "driving"}

# 工具结果缓存：模型重复查同一个景点时不再打高德接口，也不占用预算
_tool_cache: dict[str, str] = {}


async def _run_tool(tool_call) -> str:
    """执行模型请求的一次工具调用，并返回要塞回给模型的文本结果"""
    function_name = tool_call.function.name
    try:
        function_args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return f"参数解析失败：{tool_call.function.arguments}"

    # 同样的工具 + 同样的参数，结果不会变，直接复用，省一次高德请求
    cache_key = f"{function_name}:{json.dumps(function_args, ensure_ascii=False, sort_keys=True)}"
    if cache_key in _tool_cache:
        print(f"♻️ 命中工具缓存: {function_name}")
        return _tool_cache[cache_key]

    print(f"🔧 大模型请求调用工具: {function_name}，参数: {function_args}")

    if function_name == "search_places":
        result = await search_places(
            keywords=function_args.get("keywords", ""),
            city=function_args.get("city", "")
        )
        simplified = [
            {"name": p.get("name"), "location": p.get("location")}
            for p in result
        ]
        content_to_llm = json.dumps(simplified, ensure_ascii=False)
    elif function_name == "get_route":
        duration = await get_route_time(
            origin_lnglat=function_args.get("origin_lnglat", ""),
            dest_lnglat=function_args.get("dest_lnglat", ""),
            mode=function_args.get("mode", "transit")
        )
        content_to_llm = f"预计耗时 {duration} 分钟。"
    elif function_name == "get_intercity_transport":
        result = await get_intercity_info(
            origin_city=function_args.get("origin_city", ""),
            dest_city=function_args.get("dest_city", "")
        )
        content_to_llm = json.dumps(result, ensure_ascii=False)
    elif function_name == "search_hotels":
        result = await search_hotels(
            keywords=function_args.get("keywords", ""),
            city=function_args.get("city", "")
        )
        simplified = [
            {
                "name": hotel.get("name"),
                "address": hotel.get("address"),
                "location": f"{hotel.get('lng')},{hotel.get('lat')}",
                "rating": hotel.get("rating"),
                "price_estimate": hotel.get("cost") or None,
            }
            for hotel in result
        ]
        content_to_llm = json.dumps(
            {
                "hotels": simplified,
                "note": "price_estimate 为空的酒店没有公开参考价，请按城市和住宿档次估算每晚价格",
            },
            ensure_ascii=False,
        )
    else:
        return (
            f"未知工具：{function_name}，可用工具：search_places / get_route / "
            f"get_intercity_transport / search_hotels / {SUBMIT_TOOL_NAME}"
        )

    print(f"✅ 工具执行结果: {content_to_llm[:50]}...")
    if len(_tool_cache) > 300:
        _tool_cache.clear()
    _tool_cache[cache_key] = content_to_llm
    return content_to_llm


def _as_number(value, default: float = 0.0) -> float:
    """把模型可能写成字符串 / null 的金额统一成非负浮点数"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def _as_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_transport_option(raw) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("summary"):
        return None
    mode = str(raw.get("mode") or "other")
    return {
        "mode": mode if mode in TRANSPORT_MODES else "other",
        "summary": str(raw.get("summary") or ""),
        "departure_time": str(raw.get("departure_time") or ""),
        "arrival_time": str(raw.get("arrival_time") or ""),
        "duration_minutes": max(0, _as_int(raw.get("duration_minutes"))),
        "cost": _as_number(raw.get("cost")),
        "note": str(raw.get("note") or ""),
    }


def _normalize_transport(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    # 有些模型会省略 recommended，直接把方案写在 transport 上
    recommended = _normalize_transport_option(raw.get("recommended") or raw)
    if not recommended:
        return None

    alternatives = []
    for alternative in raw.get("alternatives") or []:
        option = _normalize_transport_option(alternative)
        if option:
            alternatives.append(option)
    return {"recommended": recommended, "alternatives": alternatives[:3]}


def _normalize_hotel(raw, fallback_nights: int) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("name"):
        return None

    nights = max(1, _as_int(raw.get("nights"), fallback_nights or 1))
    rooms = max(1, _as_int(raw.get("rooms"), 1))
    price_per_night = _as_number(raw.get("price_per_night"))
    cost = _as_number(raw.get("cost")) or price_per_night * nights

    return {
        "name": str(raw.get("name") or ""),
        "address": str(raw.get("address") or ""),
        "lng": _as_number(raw.get("lng")) or None,
        "lat": _as_number(raw.get("lat")) or None,
        "rating": str(raw.get("rating") or ""),
        "check_in_date": str(raw.get("check_in_date") or ""),
        "check_out_date": str(raw.get("check_out_date") or ""),
        "nights": nights,
        "rooms": rooms,
        "price_per_night": price_per_night,
        "cost": cost,
        "note": str(raw.get("note") or ""),
    }


def _normalize_itinerary(arguments: str) -> tuple[str | None, str | None]:
    """校验 submit_itinerary 的参数，成功返回 (JSON 字符串, None)，失败返回 (None, 错误说明)"""
    try:
        data = json.loads(arguments or "{}")
    except json.JSONDecodeError as error:
        return None, f"参数不是合法 JSON：{error}"
    if not isinstance(data, dict):
        return None, "参数必须是一个 JSON 对象"

    days = data.get("days")
    if not isinstance(days, list) or not days:
        return None, "days 必须是非空数组"

    normalized_days = []
    for index, day in enumerate(days):
        if not isinstance(day, dict):
            return None, f"第 {index + 1} 天不是对象"
        items = day.get("items")
        if not isinstance(items, list) or not items:
            return None, f"第 {index + 1} 天没有 items，请补充至少一个地点"
        normalized_items = []
        for item in items:
            if not isinstance(item, dict) or not item.get("place_name"):
                return None, f"第 {index + 1} 天有地点缺少 place_name"
            if not item.get("start_time") or not item.get("end_time"):
                return None, f"「{item.get('place_name')}」缺少 start_time 或 end_time"
            category = str(item.get("category") or "sightseeing")
            normalized_items.append({
                "place_name": item.get("place_name"),
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time"),
                "category": category if category in ITEM_CATEGORIES else "other",
                "cost_estimate": _as_number(item.get("cost_estimate")),
                "note": str(item.get("note") or ""),
                "lng": item.get("lng"),
                "lat": item.get("lat"),
            })
        normalized_days.append({
            "day_index": day.get("day_index") or index + 1,
            "items": normalized_items,
        })

    transport = _normalize_transport(data.get("transport"))
    fallback_nights = max(len(normalized_days) - 1, 1)
    hotel = _normalize_hotel(data.get("hotel"), fallback_nights)

    raw_budget = data.get("budget") if isinstance(data.get("budget"), dict) else {}
    breakdown = {
        "transport": transport["recommended"]["cost"] if transport else 0.0,
        "local_transport": _as_number(raw_budget.get("local_transport")),
        "accommodation": hotel["cost"] if hotel else 0.0,
        "food": 0.0,
        "tickets": 0.0,
        "shopping": 0.0,
        "other": _as_number(raw_budget.get("other")),
    }
    for day in normalized_days:
        for item in day["items"]:
            cost = item["cost_estimate"]
            if item["category"] == "food":
                breakdown["food"] += cost
            elif item["category"] in ("sightseeing", "entertainment"):
                breakdown["tickets"] += cost
            elif item["category"] == "shopping":
                breakdown["shopping"] += cost
            else:
                breakdown["other"] += cost

    breakdown = {key: round(value, 2) for key, value in breakdown.items()}
    breakdown["total"] = round(sum(breakdown.values()), 2)

    return json.dumps(
        {
            "origin": data.get("origin"),
            "destination": data.get("destination"),
            "transport": transport,
            "hotel": hotel,
            "budget": breakdown,
            "days": normalized_days,
        },
        ensure_ascii=False,
    ), None


async def plan_trip_agent(user_input: str) -> str:
    print(f"👤 用户输入: {user_input}")

    messages = [
        {"role": "system", "content": PROMPT_TEMPLATE},
        {"role": "user", "content": user_input}
    ]

    started = time.monotonic()
    tool_calls_used = 0
    rounds = 0
    last_signature = ""
    repeats = 0

    # 主终止条件：① 模型不再调用工具  ② 模型调用 submit_itinerary 交卷
    # 其余都是防止异常情况（卡住 / 重复查询 / 太慢）的保险丝
    while True:
        rounds += 1
        stop_reason = ""
        if rounds > HARD_MAX_ROUNDS:
            stop_reason = f"达到 {HARD_MAX_ROUNDS} 轮保险上限"
        elif tool_calls_used >= MAX_TOOL_CALLS:
            stop_reason = f"工具调用达到 {MAX_TOOL_CALLS} 次预算"
        elif time.monotonic() - started > TIME_BUDGET_SECONDS:
            stop_reason = f"超过 {TIME_BUDGET_SECONDS} 秒时间预算"
        if stop_reason:
            print(f"\n⚠️ {stop_reason}，停止调用工具")
            break

        print(f"\n--- 第 {rounds} 轮思考 ---")

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        choice = response.choices[0]
        response_message = choice.message
        tool_calls = response_message.tool_calls or []

        # 终止条件①：模型不再调用工具，说明它已经给出最终结果
        if not tool_calls:
            if choice.finish_reason == "length":
                print("⚠️ 模型输出被截断，改为强制输出 JSON")
                break
            content = (response_message.content or "").strip()
            if content:
                print("\n🤖 最终规划完成！")
                return content
            break

        # 终止条件②：模型调用 submit_itinerary 交卷
        submit_call = next((call for call in tool_calls if call.function.name == SUBMIT_TOOL_NAME), None)
        if submit_call:
            tool_calls_used += 1
            itinerary, error = _normalize_itinerary(submit_call.function.arguments)
            if itinerary:
                print("\n✅ 模型通过 submit_itinerary 提交行程")
                return itinerary

            # 参数不合法：把错误回灌给模型，让它修正后重新提交
            print(f"⚠️ submit_itinerary 参数不合法，退回模型修正：{error}")
            messages.append(response_message)
            for call in tool_calls:
                if call.function.name == SUBMIT_TOOL_NAME:
                    content_to_llm = f"提交失败：{error}。请修正后再次调用 {SUBMIT_TOOL_NAME}。"
                else:
                    content_to_llm = "本次调用已取消，请先修正行程数据再重新提交。"
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.function.name,
                    "content": content_to_llm,
                })
            continue

        # 进度检测：连续几轮发起完全相同的工具调用，说明模型在原地打转
        signature = json.dumps(
            sorted((call.function.name, call.function.arguments) for call in tool_calls),
            ensure_ascii=False,
        )
        repeats = repeats + 1 if signature == last_signature else 0
        last_signature = signature
        if repeats >= REPEAT_LIMIT:
            print("⚠️ 连续重复相同的工具调用，判定为原地打转，提前结束")
            break

        # 把模型本轮的请求加入历史记录
        messages.append(response_message)

        for tool_call in tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": "工具调用次数已达上限，本次未执行，请基于已有信息继续。",
                })
                continue
            tool_calls_used += 1
            content_to_llm = await _run_tool(tool_call)
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_call.function.name,
                "content": content_to_llm,
            })

    # 保险丝触发（或模型返回空内容）：强制让它直接吐出行程 JSON
    print("\n⚠️ 结束工具调用，强制模型输出最终行程 JSON")
    messages.append({
        "role": "user",
        "content": "信息已经足够，请立即输出最终的行程 JSON，不要再调用任何工具，也不要输出任何解释文字。"
    })
    try:
        # JSON 模式可以让模型只能输出合法 JSON，省掉后面的清洗
        final = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
    except Exception as error:
        # 有些兼容接口不支持 response_format，退回普通模式
        print(f"⚠️ JSON 模式不可用，退回普通输出：{error}")
        final = await client.chat.completions.create(model=MODEL, messages=messages)
    return (final.choices[0].message.content or "").strip()

if __name__ == "__main__":
    import asyncio
    test_prompt = "我想去成都玩，帮我查一下武侯祠的经纬度，然后再查一下去大熊猫繁育研究基地坐公交要多久？"
    asyncio.run(plan_trip_agent(test_prompt))