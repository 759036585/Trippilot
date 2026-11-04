# services/agent.py
import json
import time
from openai import AsyncOpenAI
from config import settings
from services.amap import search_places, get_route_time

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
            "name": "submit_itinerary",
            "description": (
                "提交最终行程。当你已经查清景点和交通、行程安排完成时调用它。"
                "调用后本次规划立即结束，不要再调用其他工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地城市"},
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
                                            "place_name": {"type": "string"},
                                            "start_time": {"type": "string", "description": "HH:MM"},
                                            "end_time": {"type": "string", "description": "HH:MM"},
                                            "cost_estimate": {"type": "number", "description": "该地点预估花费（元）"},
                                            "lng": {"type": "number"},
                                            "lat": {"type": "number"}
                                        },
                                        "required": ["place_name", "start_time", "end_time"]
                                    }
                                }
                            },
                            "required": ["day_index", "items"]
                        }
                    }
                },
                "required": ["destination", "days"]
            }
        }
    }
]

# 2. 系统提示词模板
PROMPT_TEMPLATE = """
你是一个专业的旅行规划师。你可以使用以下工具：
1. search_places(keywords, city): 搜索真实的景点或旅游地点，返回名称和经纬度。
2. get_route(origin_lnglat, dest_lnglat, mode): 计算两个经纬度之间的交通耗时（分钟）。
3. submit_itinerary(destination, days): 提交最终行程。信息足够、安排完成后调用它结束规划。

工作流程：
- 先用 search_places 确认景点真实存在，必要时用 get_route 估算地点之间的交通时间。
- 同一个地点不要重复查询，查到结果就直接使用。
- 信息足够后，调用 submit_itinerary 提交行程，不要再输出解释文字。

如果无法调用 submit_itinerary，就直接输出最终行程 JSON（不要用 Markdown 代码块包裹），格式如下：
{
  "destination": "成都",
  "days": [
    {
      "day_index": 1,
      "items": [
            {
                "place_name": "武侯祠",
                "start_time": "09:30",
                "end_time": "11:30",
                "cost_estimate": 50,
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
HARD_MAX_ROUNDS = 12       # 硬上限：最多思考几轮
MAX_TOOL_CALLS = 24        # 预算：整个规划最多执行多少次工具调用
TIME_BUDGET_SECONDS = 120  # 预算：整个规划最多耗时多少秒
REPEAT_LIMIT = 2           # 连续出现同样工具调用的次数上限
SUBMIT_TOOL_NAME = "submit_itinerary"

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
    else:
        return f"未知工具：{function_name}，可用工具：search_places / get_route / {SUBMIT_TOOL_NAME}"

    print(f"✅ 工具执行结果: {content_to_llm[:50]}...")
    if len(_tool_cache) > 300:
        _tool_cache.clear()
    _tool_cache[cache_key] = content_to_llm
    return content_to_llm


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
            normalized_items.append({
                "place_name": item.get("place_name"),
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time"),
                "cost_estimate": item.get("cost_estimate") or 0,
                "lng": item.get("lng"),
                "lat": item.get("lat"),
            })
        normalized_days.append({
            "day_index": day.get("day_index") or index + 1,
            "items": normalized_items,
        })

    return json.dumps(
        {"destination": data.get("destination"), "days": normalized_days},
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