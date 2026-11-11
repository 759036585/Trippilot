# services/planner_chat.py
"""
对话式行程需求收集。

和 services/agent.py（真正生成行程）不同，这里的职责只有一个：
从聊天里一点点把「出发地 / 目的地 / 日期 / 人数 / 预算 / 住宿档次 / 偏好」
这些槽位填满，并给出下一句自然语言提问。

前端每一轮把完整对话和最新的 draft 一起传上来，后端无状态：
用大模型做信息抽取 + 生成提问，模型不可用时退回规则解析，保证对话不会中断。
"""
import json
import re
from datetime import date, datetime, timedelta

from openai import AsyncOpenAI

from config import settings

client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL
)

MODEL = "deepseek-chat"

HOTEL_LEVELS = ("经济型", "舒适型", "豪华型")
PREFERENCE_OPTIONS = ("自然风景", "美食", "历史文化", "亲子", "购物", "休闲")

# 对话里常见的中文数字，规则兜底时换算用
CN_NUMBERS = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

# draft 的字段，也是右侧面板的展示字段
DRAFT_FIELDS = (
    "origin", "destination", "start_date", "end_date",
    "travelers", "budget", "hotel_level", "preferences",
)

MAX_MESSAGES = 30          # 只带最近 30 条进模型，避免上下文过长
MAX_MESSAGE_CHARS = 1000   # 单条消息截断
MAX_TRIP_DAYS = 30         # 超过一个月的行程按异常处理，重新问日期

WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


# ---------------------------------------------------------------- 规范化
def _clean_text(value, limit: int = 30) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _parse_iso_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = _clean_text(value, 20).replace("/", "-").replace(".", "-")
    text = text.replace("年", "-").replace("月", "-").replace("日", "")
    # 兼容模型返回的 "2026-11-14T00:00:00" / "2026-11-14 00:00:00"
    text = text.split("T")[0].split(" ")[0]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_number(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("，", ""))
    except (TypeError, ValueError):
        return None


def normalize_draft(raw) -> dict:
    """把模型 / 前端传来的 draft 收敛成合法值，非法字段置空让助手重新问"""
    raw = raw if isinstance(raw, dict) else {}
    today = date.today()

    origin = _clean_text(raw.get("origin"))
    destination = _clean_text(raw.get("destination"))
    if origin and origin == destination:
        # 出发地和目的地相同说明抽取出错，保留目的地，重新问出发地
        origin = ""

    start = _parse_iso_date(raw.get("start_date"))
    end = _parse_iso_date(raw.get("end_date"))

    # 过去日期、倒挂日期、超过一个月的行程都作废，交给助手重新确认
    if start and start < today:
        start = None
        end = None
    if start and end and end < start:
        end = None
    if start and end and (end - start).days + 1 > MAX_TRIP_DAYS:
        start = None
        end = None

    travelers_value = None
    travelers = _parse_number(raw.get("travelers"))
    if travelers is not None:
        travelers_value = int(travelers)
        if not 1 <= travelers_value <= 20:
            travelers_value = None

    budget_value = None
    budget = _parse_number(raw.get("budget"))
    if budget is not None and budget >= 200:
        budget_value = round(budget, 2)

    hotel_level = _clean_text(raw.get("hotel_level"), 10)
    if hotel_level not in HOTEL_LEVELS:
        hotel_level = ""

    preferences = raw.get("preferences")
    prefs: list[str] = []
    if isinstance(preferences, list):
        for item in preferences:
            name = _clean_text(item, 10)
            if name in PREFERENCE_OPTIONS and name not in prefs:
                prefs.append(name)
    elif isinstance(preferences, str):
        for name in PREFERENCE_OPTIONS:
            if name in preferences and name not in prefs:
                prefs.append(name)

    return {
        "origin": origin,
        "destination": destination,
        "start_date": start.isoformat() if start else "",
        "end_date": end.isoformat() if end else "",
        "travelers": travelers_value,
        "budget": budget_value,
        "hotel_level": hotel_level,
        "preferences": prefs,
    }


def merge_draft(base: dict, update) -> dict:
    """用新一轮抽取到的字段覆盖旧值；空值视为「没提到」，不清空已有信息"""
    merged = dict(base)
    if not isinstance(update, dict):
        return merged
    for key in DRAFT_FIELDS:
        value = update.get(key)
        if value in (None, "", []):
            continue
        merged[key] = value
    return normalize_draft(merged)


def missing_fields(draft: dict) -> list[str]:
    missing = []
    for field in ("origin", "destination"):
        if not draft.get(field):
            missing.append(field)
    if not draft.get("start_date") or not draft.get("end_date"):
        missing.append("dates")
    for field in ("travelers", "budget", "hotel_level"):
        if not draft.get(field):
            missing.append(field)
    return missing


# ---------------------------------------------------------------- 提问文案
OPENING_REPLY = (
    "你好，我是 TripPilot 的行程助手 👋\n"
    "一句话说说你想去哪儿、什么时候出发就行，剩下的我一步步帮你理清楚——"
    "城际交通、住哪儿、每天玩什么、花多少钱，最后都会给你排好。"
)
OPENING_SUGGESTIONS = ["这周末去成都", "下周去大理玩三天", "国庆去西安，两个人"]

QUESTIONS: dict[str, tuple[str, list[str]]] = {
    "origin": ("先从哪座城市出发呢？", ["北京", "上海", "广州", "成都"]),
    "destination": ("想去哪里玩？", ["成都", "大理", "厦门", "西安"]),
    "dates": ("打算什么时候出发、玩几天？", ["这周末，三天两晚", "下个周末出发", "我选具体日期"]),
    "travelers": ("几个人一起去？", ["1 人", "2 人", "3-4 人", "带孩子一起"]),
    "budget": ("这趟大概准备了多少钱？（交通住宿都算，全部人合计）", ["3000 元左右", "5000 元左右", "8000 元左右", "1 万左右"]),
    "hotel_level": ("住宿想住哪种档次？", ["经济型", "舒适型", "豪华型", "干净方便就行"]),
    "preferences": ("想玩点什么？可以多选。", ["自然风景", "美食", "历史文化", "亲子", "购物", "休闲"]),
}

READY_REPLY = "需求都记下啦，我整理成了一版方案 👇 没问题就点「开始生成行程」，想改哪里直接告诉我。"
READY_SUGGESTIONS = ["就按这个来", "预算再低一点", "换成经济型酒店", "多安排一些美食"]


def _question_for(field: str, draft: dict | None = None) -> tuple[str, list[str]]:
    # 用户只说了出发日期、没说玩几天时，换个问法，避免重复问"什么时候出发"
    if field == "dates" and draft and draft.get("start_date"):
        return "准备玩几天？（含出发当天）", ["3 天", "4 天", "5 天左右", "当天往返"]
    return QUESTIONS.get(field, ("还想再确认一下你的需求～", []))


def format_draft_line(draft: dict) -> str:
    """把 draft 拼成一句话，用于兜底回复和就绪归纳"""
    parts = []
    if draft.get("origin") and draft.get("destination"):
        parts.append(f"{draft['origin']} → {draft['destination']}")
    elif draft.get("destination"):
        parts.append(f"去{draft['destination']}")
    if draft.get("start_date") and draft.get("end_date"):
        days = (
            datetime.fromisoformat(draft["end_date"]).date()
            - datetime.fromisoformat(draft["start_date"]).date()
        ).days + 1
        parts.append(f"{draft['start_date']} 到 {draft['end_date']}（{days} 天）")
    if draft.get("travelers"):
        parts.append(f"{draft['travelers']} 人")
    if draft.get("budget"):
        parts.append(f"预算 {int(draft['budget'])} 元")
    if draft.get("hotel_level"):
        parts.append(draft["hotel_level"])
    if draft.get("preferences"):
        parts.append("偏好" + "、".join(draft["preferences"]))
    return " · ".join(parts)


def _compose_reply(draft: dict, missing: list[str], prefix: str = "") -> tuple[str, list[str]]:
    """没有模型时自己拼一条回复：接一句 + 下一个问题"""
    head = prefix.strip()

    if not missing:
        summary = format_draft_line(draft)
        lead = f"好的，{summary}，需求都记下了。" if summary else ""
        return "\n".join(part for part in (head, lead, READY_REPLY) if part), READY_SUGGESTIONS

    if not head:
        if draft.get("destination") and missing[0] != "destination":
            head = f"{draft['destination']}不错！"
        if draft.get("origin") and draft.get("destination") and missing[0] == "dates":
            head = f"{draft['origin']}到{draft['destination']}，好安排！"

    question, suggestions = _question_for(missing[0], draft)
    reply = f"{head}\n{question}" if head else question
    return reply, suggestions


# ---------------------------------------------------------------- 规则兜底
def _fallback_extract(text: str) -> dict:
    """模型不可用时，用正则尽量从用户这句话里抠出槽位"""
    text = text or ""
    extracted: dict = {}

    # 从 A 到 B / 从 A 去 B
    route = re.search(
        r"从\s*([一-龥]{2,10}?)\s*(?:到|去|飞往|飞|出发去)\s*([一-龥]{2,10}?)(?:[，,。！!？?\s]|玩|旅游|旅行|出差|$)",
        text,
    )
    if route:
        extracted["origin"], extracted["destination"] = route.group(1), route.group(2)
    else:
        go = re.search(r"(?:去|到)\s*([一-龥]{2,8}?)(?:玩|旅游|旅行|出差|自由行|逛逛|看看|[，,。！!？?]|$)", text)
        if go:
            extracted["destination"] = go.group(1)

    def _iso(parts) -> str:
        year, month, day = parts
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    # 完整日期，例如 2026-12-05 / 2026年12月5日
    full_dates = re.findall(r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})\s*日?", text)
    if len(full_dates) >= 2:
        extracted["start_date"] = _iso(full_dates[0])
        extracted["end_date"] = _iso(full_dates[1])
    elif len(full_dates) == 1:
        extracted["start_date"] = _iso(full_dates[0])
    else:
        # 只说月日时按今年算，已经过去就顺延到明年
        month_day = re.search(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*日?", text)
        if month_day:
            today = date.today()
            candidate = date(today.year, int(month_day.group(1)), int(month_day.group(2)))
            if candidate < today:
                candidate = date(today.year + 1, candidate.month, candidate.day)
            extracted["start_date"] = candidate.isoformat()

    # 「明天」「后天」这类相对说法
    if not extracted.get("start_date"):
        for word, offset in (("明天", 1), ("后天", 2), ("大后天", 3)):
            if word in text:
                extracted["start_date"] = (date.today() + timedelta(days=offset)).isoformat()
                break

    # 「玩三天」「三天两晚」「三日游」用来补结束日期
    if extracted.get("start_date") and not extracted.get("end_date"):
        if "当天往返" in text or "一日游" in text:
            extracted["end_date"] = extracted["start_date"]
        else:
            days_match = re.search(
                r"([\d一两二三四五六七八九十]{1,2})\s*(?:天(?:\s*[\d一两二三四五六七八九十]{1,2}\s*晚)?|日游)",
                text,
            )
            if days_match:
                raw_days = days_match.group(1)
                count = int(raw_days) if raw_days.isdigit() else CN_NUMBERS.get(raw_days)
                if count:
                    extracted["end_date"] = (
                        date.fromisoformat(extracted["start_date"]) + timedelta(days=max(0, count - 1))
                    ).isoformat()

    # 人数：支持「2 人」「两个人」「三个人」
    travelers = re.search(r"(\d{1,2}|[一两二三四五六七八九十]{1,2})\s*个?\s*人", text)
    if travelers:
        value = travelers.group(1)
        extracted["travelers"] = int(value) if value.isdigit() else CN_NUMBERS.get(value)

    # 预算：预算 5000 / 5000 元左右 / 人均 2000
    budget = re.search(r"(?:预算|大概|准备了|花)\D{0,4}(\d{3,6})", text) or re.search(r"(\d{3,6})\s*(?:元|块|块钱)", text)
    if budget:
        value = float(budget.group(1))
        if "人均" in text and extracted.get("travelers"):
            value *= extracted["travelers"]
        extracted["budget"] = value

    for level in HOTEL_LEVELS:
        if level in text:
            extracted["hotel_level"] = level
            break
    if not extracted.get("hotel_level"):
        if re.search(r"经济|便宜|省钱|青旅", text):
            extracted["hotel_level"] = "经济型"
        elif re.search(r"豪华|五星|高档", text):
            extracted["hotel_level"] = "豪华型"
        elif re.search(r"舒适|干净|方便就行", text):
            extracted["hotel_level"] = "舒适型"

    pref_keywords = {
        "自然风景": r"自然|风景|山水|海边|看海|户外|爬山",
        "美食": r"美食|吃|火锅|小吃|探店",
        "历史文化": r"历史|文化|古城|博物馆|古迹|寺庙",
        "亲子": r"亲子|孩子|带娃|小朋友",
        "购物": r"购物|逛街|买东西|商场",
        "休闲": r"休闲|放松|悠闲|发呆|慢生活",
    }
    prefs = [name for name, pattern in pref_keywords.items() if re.search(pattern, text)]
    if prefs:
        extracted["preferences"] = prefs

    return extracted


# ---------------------------------------------------------------- 大模型
SYSTEM_PROMPT_TEMPLATE = """
你是 TripPilot 的旅行规划助手，正在通过对话收集用户的出行需求。
今天是 {today}（{weekday}）。

需要收集的字段：
- origin：出发城市
- destination：目的地城市
- start_date / end_date：出行日期，格式 YYYY-MM-DD
- travelers：出行人数（整数）
- budget：总预算，单位元，包含交通和住宿，是全部人的合计（用户说人均时要乘以人数）
- hotel_level：住宿档次，只能是 经济型 / 舒适型 / 豪华型
- preferences：旅行偏好，数组，元素只能是 自然风景 / 美食 / 历史文化 / 亲子 / 购物 / 休闲

对话规则：
1. 每一轮最多问 1-2 个问题，优先补齐还缺的字段，提问顺序：出发地 → 目的地 → 日期 → 人数 → 预算 → 住宿档次 → 偏好。
2. 用户一句话里给了多个信息就全部记下，已经有的信息不要重复问。
3. 相对日期要按今天推算：「这周末」是本周六出发，「下周末」是下周六，「三天两晚」表示 3 天行程。日期不能早于今天。
4. 用户说「随便」「你定」这类模糊回答时，替用户选一个合理的默认值填进 draft，并在回复里说明，不要再追问。
5. 用户改主意时要更新对应字段，不要保留冲突的旧值。
6. 语气自然口语化，像朋友聊旅行，回复控制在 2-3 句，不要长篇罗列，不要用 Markdown 代码块。
7. 每一轮都给出 2-4 个 suggestions，是用户下一步可以直接点选的短语（例如「2 人」「舒适型」「5000 元左右」），要贴合当前正在问的问题。
8. 出发地、目的地、日期、人数、预算、住宿档次都齐了以后，reply 简要复述方案并询问是否开始生成行程；
   如果用户已经提过偏好就不要再追问偏好，直接进入确认，最多再问一句「要不要补充偏好」。
9. 只输出一个 JSON 对象，不要输出任何其他文字。

输出 JSON 结构：
{{
  "reply": "给用户看的中文回复",
  "draft": {{
    "origin": "城市名或空字符串",
    "destination": "城市名或空字符串",
    "start_date": "YYYY-MM-DD 或空字符串",
    "end_date": "YYYY-MM-DD 或空字符串",
    "travelers": 整数或 null,
    "budget": 数字或 null,
    "hotel_level": "经济型/舒适型/豪华型 或空字符串",
    "preferences": ["自然风景"]
  }},
  "suggestions": ["选项1", "选项2"]
}}

draft 必须是「合并了本轮新信息之后的完整需求」，已收集到的字段要保留，不要漏掉。
"""


def _build_messages(messages: list[dict], draft: dict) -> list[dict]:
    today = date.today()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        today=today.isoformat(),
        weekday=WEEKDAYS[today.weekday()],
    )
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[-MAX_MESSAGES:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    # 当前已收集的需求单独贴在最后，避免模型从长对话里自己拼
    history.append({
        "role": "user",
        "content": "当前已收集的需求（JSON）：" + json.dumps(draft, ensure_ascii=False)
                   + "\n请结合上面对话，输出本轮回复和合并后的完整 draft。",
    })
    return [{"role": "system", "content": system}, *history]


async def _ask_llm(messages: list[dict], draft: dict) -> dict | None:
    response = await client.chat.completions.create(
        model=MODEL,
        messages=_build_messages(messages, draft),
        response_format={"type": "json_object"},
        temperature=0.5,
        max_tokens=900,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        return None
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end <= start:
            return None
        data = json.loads(content[start:end + 1])
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------- 对外接口
def _sanitize_suggestions(raw, fallback: list[str]) -> list[str]:
    if not isinstance(raw, list):
        return fallback
    suggestions = []
    for item in raw:
        text = _clean_text(item, 24)
        if text and text not in suggestions:
            suggestions.append(text)
    return suggestions[:4] or fallback


def _build_response(reply: str, suggestions, draft: dict) -> dict:
    missing = missing_fields(draft)
    reply = (reply or "").strip() or _compose_reply(draft, missing)[0]
    fallback_suggestions = _question_for(missing[0], draft)[1] if missing else READY_SUGGESTIONS
    return {
        "reply": reply[:600],
        "suggestions": _sanitize_suggestions(suggestions, fallback_suggestions),
        "draft": draft,
        "missing": missing,
        "ready": not missing,
    }


async def chat_turn(messages: list[dict], draft_raw) -> dict:
    """跑一轮对话：返回 {reply, suggestions, draft, missing, ready}"""
    draft = normalize_draft(draft_raw)
    messages = [
        {"role": str(m.get("role")), "content": _clean_text(m.get("content"), MAX_MESSAGE_CHARS)}
        for m in (messages or [])
        if isinstance(m, dict)
    ]
    user_messages = [m for m in messages if m["role"] == "user" and m["content"]]

    # 还没有任何用户消息：给一句开场白，不用调模型
    if not user_messages:
        return {
            "reply": OPENING_REPLY,
            "suggestions": OPENING_SUGGESTIONS,
            "draft": draft,
            "missing": missing_fields(draft),
            "ready": False,
        }

    data = None
    if settings.LLM_API_KEY:
        try:
            data = await _ask_llm(messages, draft)
        except Exception as error:  # 模型超时 / 限流 / 返回异常都不能打断对话
            print(f"⚠️ 需求收集模型调用失败，改用规则解析：{error}")

    if data is None:
        extracted = _fallback_extract(user_messages[-1]["content"])
        merged = merge_draft(draft, extracted)
        reply, suggestions = _compose_reply(
            merged,
            missing_fields(merged),
            prefix="好的，我记下了。" if extracted else "",
        )
        return _build_response(reply, suggestions, merged)

    merged = merge_draft(draft, data.get("draft"))
    missing = missing_fields(merged)
    reply = data.get("reply") or ""
    if not missing and not reply:
        reply = READY_REPLY
    return _build_response(reply, data.get("suggestions"), merged)
