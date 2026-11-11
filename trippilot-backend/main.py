# main.py
import json
import sys
from fastapi import Depends, Header, FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import date, timedelta
import time
import asyncio

# Windows 中文控制台默认是 GBK 编码，打印 emoji 会抛 UnicodeEncodeError，
# 这会让后台任务直接失败（状态变成 failed）。这里统一把输出切成 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# 引入数据库相关
from database.index import Base, engine, SessionLocal
from database.models import User, Trip, TripDay, TripItem
# 引入 Agent
from services.agent import plan_trip_agent
from services.planner_chat import chat_turn as planner_chat_turn
from services.amap import geocode_place, get_route_detail, search_around
from services.security import create_token, decode_token, hash_password, verify_password

# 自动建表
Base.metadata.create_all(bind=engine)


# create_all 只建新表，不会给已有表补列。
# 这里用 Postgres 的 IF NOT EXISTS 做一次幂等的轻量迁移，老库也能直接用上新字段。
def _ensure_trip_columns():
    existing = {col["name"] for col in inspect(engine).get_columns("trips")}
    statements = []
    if "budget" not in existing:
        statements.append("ALTER TABLE trips ADD COLUMN budget DOUBLE PRECISION")
    if "travelers" not in existing:
        statements.append("ALTER TABLE trips ADD COLUMN travelers INTEGER")
    if "user_id" not in existing:
        statements.append("ALTER TABLE trips ADD COLUMN user_id INTEGER REFERENCES users(id)")
        statements.append("CREATE INDEX IF NOT EXISTS ix_trips_user_id ON trips (user_id)")
    if "origin" not in existing:
        statements.append("ALTER TABLE trips ADD COLUMN origin VARCHAR")
    if "plan_json" not in existing:
        statements.append("ALTER TABLE trips ADD COLUMN plan_json TEXT")
    if not statements:
        return
    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))
    print(f"🛠️ 已为 trips 表补充字段: {', '.join(statements)}")


def _ensure_trip_item_columns():
    existing = {col["name"] for col in inspect(engine).get_columns("trip_items")}
    statements = []
    if "category" not in existing:
        statements.append("ALTER TABLE trip_items ADD COLUMN category VARCHAR")
    if "note" not in existing:
        statements.append("ALTER TABLE trip_items ADD COLUMN note VARCHAR")
    if not statements:
        return
    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))
    print(f"🛠️ 已为 trip_items 表补充字段: {', '.join(statements)}")


_ensure_trip_columns()
_ensure_trip_item_columns()

app = FastAPI(title="TripPilot API", version="1.0.0")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 登录相关：从 Authorization: Bearer <token> 中解析当前用户 ---
def _user_from_token(authorization: str | None, db: Session) -> User | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    user_id = decode_token(parts[1].strip())
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """可选登录：没带 token 就当作游客，带了但无效则 401"""
    if not authorization:
        return None
    user = _user_from_token(authorization, db)
    if not user:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_token(authorization, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


# --- 定义请求数据模型（使用 Pydantic 进行参数校验）---
class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


def _normalize_username(username: str) -> str:
    return (username or "").strip()


@app.post("/api/v1/auth/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = _normalize_username(request.username)
    password = request.password or ""

    if len(username) < 3 or len(username) > 32:
        raise HTTPException(status_code=400, detail="用户名长度需要在 3-32 个字符之间")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=400, detail="该用户名已被注册")

    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=(request.nickname or "").strip() or username,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该用户名已被注册")
    db.refresh(user)

    return {"token": create_token(user.id), "user": user.to_dict()}


@app.post("/api/v1/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    username = _normalize_username(request.username)
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(request.password or "", user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    return {"token": create_token(user.id), "user": user.to_dict()}


@app.get("/api/v1/auth/me")
def me(user: User = Depends(get_current_user)):
    return user.to_dict()


class TripCreateRequest(BaseModel):
    origin: str = ""
    destination: str
    start_date: date
    end_date: date
    travelers: int
    budget: float
    preferences: list[str] = []
    # 经济型 / 舒适型 / 豪华型，影响 Agent 选酒店的价位
    hotel_level: str = "舒适型"


# --- 对话式需求收集：前端聊天界面每轮带上完整对话和已收集的 draft ---
class PlannerMessage(BaseModel):
    role: str = "user"
    content: str = ""


class PlannerDraft(BaseModel):
    origin: str = ""
    destination: str = ""
    start_date: str = ""
    end_date: str = ""
    travelers: int | None = None
    budget: float | None = None
    hotel_level: str = ""
    preferences: list[str] = []


class PlannerChatRequest(BaseModel):
    messages: list[PlannerMessage] = []
    draft: PlannerDraft | None = None


@app.post("/api/v1/planner/chat")
async def planner_chat(request: PlannerChatRequest):
    """对话式创建行程：AI 引导用户补齐出发地/目的地/日期/人数/预算等信息"""
    return await planner_chat_turn(
        [message.model_dump() for message in request.messages],
        request.draft.model_dump() if request.draft else {},
    )


ITEM_CATEGORIES = {"sightseeing", "food", "shopping", "entertainment", "other"}
# 行程项类别 -> 预算分项
ITEM_BUDGET_BUCKETS = {
    "sightseeing": "tickets",
    "entertainment": "tickets",
    "food": "food",
    "shopping": "shopping",
    "other": "other",
}


def parse_plan(plan_json: str | None) -> dict:
    """plan_json 是城际交通 / 酒店 / 预算的 JSON 快照，解析失败时退回空对象"""
    if not plan_json:
        return {}
    try:
        plan = json.loads(plan_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    return plan if isinstance(plan, dict) else {}


def build_budget_breakdown(items, plan: dict) -> dict:
    """
    按「方案数据 + 行程项」实时汇总预算，保证用户后来手动加地点时金额也跟着变。
    transport / accommodation / local_transport / other 来自方案，
    餐饮 / 门票玩乐 / 购物 按行程项类别汇总。
    """
    plan_budget = plan.get("budget") if isinstance(plan.get("budget"), dict) else {}
    transport = plan.get("transport") if isinstance(plan.get("transport"), dict) else {}
    recommended = transport.get("recommended") if isinstance(transport.get("recommended"), dict) else {}
    hotel = plan.get("hotel") if isinstance(plan.get("hotel"), dict) else {}

    breakdown = {
        "transport": float(recommended.get("cost") or 0),
        "local_transport": float(plan_budget.get("local_transport") or 0),
        "accommodation": float(hotel.get("cost") or 0),
        "food": 0.0,
        "tickets": 0.0,
        "shopping": 0.0,
        "other": float(plan_budget.get("other") or 0),
    }

    for item in items:
        # 老数据的 category 为空，按景点门票处理
        bucket = ITEM_BUDGET_BUCKETS.get(item.category or "sightseeing", "other")
        breakdown[bucket] += float(item.cost_estimate or 0)

    breakdown = {key: round(value, 2) for key, value in breakdown.items()}
    breakdown["total"] = round(sum(breakdown.values()), 2)
    return breakdown


def trip_total_cost(trip) -> float:
    items = [item for day in trip.days for item in day.items]
    return build_budget_breakdown(items, parse_plan(trip.plan_json))["total"]


def _to_float(value, default: float = 0.0) -> float:
    """模型兜底输出的 JSON 里数字可能是字符串，转换失败时用默认值"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# --- 补齐行程项坐标：模型偶尔只给地点名不给经纬度，会导致地图没点位、路线算不出来 ---
def _is_valid_coord(value) -> bool:
    try:
        return value is not None and value != "" and float(value) != 0
    except (TypeError, ValueError):
        return False


def _item_has_coords(item) -> bool:
    if isinstance(item, dict):
        return _is_valid_coord(item.get("lng")) and _is_valid_coord(item.get("lat"))
    return _is_valid_coord(item.lng) and _is_valid_coord(item.lat)


def _item_place_name(item) -> str:
    value = item.get("place_name") if isinstance(item, dict) else item.place_name
    return str(value or "")


def _set_item_coords(item, coord: tuple[float, float]):
    if isinstance(item, dict):
        item["lng"], item["lat"] = coord
    else:
        item.lng, item.lat = coord


async def fill_item_coords(items, city: str) -> int:
    """给缺少经纬度的行程项用高德补全，返回成功补全的数量"""
    city = (city or "").strip()
    if not city:
        return 0

    missing = [item for item in items if not _item_has_coords(item)]
    if not missing:
        return 0

    # geocode_place 内部用信号量限制并发，这里可以放心并发等待
    coords = await asyncio.gather(
        *(geocode_place(_item_place_name(item), city) for item in missing)
    )
    resolved = 0
    for item, coord in zip(missing, coords):
        if coord:
            _set_item_coords(item, coord)
            resolved += 1
    return resolved


# --- 工具函数：把大模型的返回清洗成 JSON 对象 ---
def parse_agent_json(text: str) -> dict:
    """模型可能带有 ```json 标记或前后夹带说明文字，这里统一清洗后解析"""
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # 兜底：截取第一个 { 到最后一个 } 之间的内容
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"模型返回的内容不是合法 JSON: {text[:200]}")
        data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError(f"模型返回的 JSON 不是对象: {text[:200]}")
    return data


# --- 后台任务：实际去运行 Agent 的函数 ---
# 注意：不能把接口里的 db 会话传进来，FastAPI 会在后台任务执行前关闭它，
# 所以这里自己创建 Session，用完即关。
async def run_agent_task(trip_id: int, request: TripCreateRequest):
    db = SessionLocal()
    try:
        day_count = (request.end_date - request.start_date).days + 1
        night_count = max(day_count - 1, 1)
        stay_text = f"{day_count}天{day_count - 1}晚" if day_count > 1 else "当天往返"
        origin = (request.origin or "").strip() or "我所在的城市"
        prompt = (
            f"我想从{origin}出发去{request.destination}旅游，"
            f"{request.start_date} 出发、{request.end_date} 返回，"
            f"共{stay_text}，{request.travelers}人，"
            f"总预算{request.budget}元，住宿希望是{request.hotel_level}，"
            f"偏好是{','.join(request.preferences) or '无'}。"
            "请帮我规划一份完整行程：包括城际交通方案（推荐 + 备选）、"
            "酒店住宿、每天的吃喝玩乐安排，并把交通、住宿、餐饮、门票玩乐等费用都算清楚。"
        )

        # 1. 获取 Agent 返回的 JSON 字符串并解析
        result_str = await plan_trip_agent(prompt)
        trip_data = parse_agent_json(result_str)

        days = trip_data.get("days") or []
        if not days:
            raise ValueError(f"Agent 未返回任何行程天数据: {result_str[:200]}")

        # 模型偶尔只给地点名不给经纬度，先补全，保证地图有点位、路线能计算
        resolved = await fill_item_coords(
            [item for day in days for item in (day.get("items") or [])],
            str(trip_data.get("destination") or request.destination or ""),
        )
        if resolved:
            print(f"🗺️ 已补全 {resolved} 个地点的坐标")

        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            print(f"行程 {trip_id} 已被删除，放弃写入")
            return

        # 2. 整理城际交通 / 酒店 / 预算快照
        hotel = trip_data.get("hotel") if isinstance(trip_data.get("hotel"), dict) else None
        if hotel:
            try:
                nights = max(int(hotel.get("nights") or night_count), 1)
            except (TypeError, ValueError):
                nights = night_count
            hotel["nights"] = nights
            # 模型没写入住/退房日期时，用行程日期补全
            hotel["check_in_date"] = hotel.get("check_in_date") or str(request.start_date)
            hotel["check_out_date"] = hotel.get("check_out_date") or str(
                min(request.start_date + timedelta(days=nights), request.end_date)
            )

        plan = {
            "transport": trip_data.get("transport"),
            "hotel": hotel,
            "budget": trip_data.get("budget") or {},
        }
        origin_value = str(trip_data.get("origin") or request.origin or "").strip()
        trip.origin = origin_value or None
        trip.plan_json = json.dumps(plan, ensure_ascii=False)

        # 3. 写入数据库：先清空可能残留的旧数据，保证重试时不会重复
        for old_day in list(trip.days):
            db.delete(old_day)
        db.flush()

        for index, day_data in enumerate(days):
            new_day = TripDay(
                trip_id=trip.id,
                day_index=index + 1,
                date=request.start_date + timedelta(days=index)
            )
            db.add(new_day)
            db.flush()  # flush 之后才能拿到 new_day.id

            for item_data in day_data.get("items", []):
                category = str(item_data.get("category") or "sightseeing")
                db.add(TripItem(
                    trip_day_id=new_day.id,
                    place_name=item_data.get("place_name"),
                    start_time=item_data.get("start_time"),
                    end_time=item_data.get("end_time"),
                    category=category if category in ITEM_CATEGORIES else "other",
                    cost_estimate=_to_float(item_data.get("cost_estimate")),
                    note=str(item_data.get("note") or "") or None,
                    lng=_to_float_or_none(item_data.get("lng")),
                    lat=_to_float_or_none(item_data.get("lat"))
                ))

        # 4. 更新状态为 ready
        trip.status = "ready"
        db.commit()
        print(f"✅ 行程 {trip_id} 规划完成")

    except Exception as e:
        print(f"Agent 运行或存库失败: {e}")
        db.rollback()
        try:
            trip = db.query(Trip).filter(Trip.id == trip_id).first()
            if trip:
                trip.status = "failed"
                db.commit()
        except Exception as db_error:
            print(f"写入失败状态时出错: {db_error}")
    finally:
        db.close()


# --- 接口 1：创建行程（提交需求） ---
@app.post("/api/v1/trips")
def create_trip(
    request: TripCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    # 1. 校验日期
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    # 2. 写入数据库（状态初始化为 planning）
    new_trip = Trip(
        origin=(request.origin or "").strip() or None,
        destination=request.destination,
        start_date=request.start_date,
        end_date=request.end_date,
        status="planning",
        budget=request.budget,
        travelers=request.travelers,
        user_id=user.id if user else None,
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip) # 刷新以获取自动生成的 ID
    
    # 3. 把耗时的大模型任务丢到后台执行
    background_tasks.add_task(run_agent_task, new_trip.id, request)
    
    # 4. 立刻返回给前端，告诉它任务正在后台跑
    return {
        "trip_id": new_trip.id,
        "status": "planning",
        "message": "正在为您规划行程，请稍候..."
    }

# --- 接口 2：查询任务状态（供前端轮询） ---
@app.get("/api/v1/trips/{trip_id}/status")
def get_trip_status(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"trip_id": trip.id, "status": trip.status}


# --- 接口：我的行程历史（必须登录） ---
# 注意要写在 /api/v1/trips/{trip_id} 之前，否则 "mine" 会被当成 trip_id 去转 int
@app.get("/api/v1/trips/mine")
def my_trips(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    trips = (
        db.query(Trip)
        .filter(Trip.user_id == user.id)
        .order_by(Trip.id.desc())
        .all()
    )

    result = []
    for trip in trips:
        items = [item for day in trip.days for item in day.items]
        result.append({
            "trip_id": trip.id,
            "origin": trip.origin,
            "destination": trip.destination,
            "status": trip.status,
            "start_date": str(trip.start_date) if trip.start_date else None,
            "end_date": str(trip.end_date) if trip.end_date else None,
            "budget": trip.budget,
            "travelers": trip.travelers,
            "day_count": len(trip.days),
            "item_count": len(items),
            "total_cost": trip_total_cost(trip),
        })
    return {"trips": result}


@app.get("/api/v1/trips/{trip_id}")
async def get_trip_detail(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    # 组装返回给前端的数据格式
    all_items = [item for day in trip.days for item in day.items]
    plan = parse_plan(trip.plan_json)
    breakdown = build_budget_breakdown(all_items, plan)

    # 老行程 / 模型漏坐标时，打开详情顺便补全并写回数据库（结果有缓存，不会每次都查）
    repaired = await fill_item_coords(all_items, trip.destination or "")
    if repaired:
        db.commit()
        print(f"🗺️ 行程 {trip_id} 补全了 {repaired} 个地点坐标")

    days_data = []
    for day in sorted(trip.days, key=lambda d: d.day_index or 0):
        items_data = []
        # 按开始时间排序，保证列表顺序和实际游览顺序一致（新增地点也是插在合理位置）
        for item in sorted(day.items, key=lambda i: (i.start_time or "")):
            items_data.append({
                "id": item.id,
                "place_name": item.place_name,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "category": item.category or "sightseeing",
                "cost_estimate": item.cost_estimate,
                "note": item.note,
                "lng": item.lng,
                "lat": item.lat,
            })
        days_data.append({
            "day_index": day.day_index,
            "date": str(day.date),
            "items": items_data
        })

    return {
        "trip_id": trip.id,
        "origin": trip.origin,
        "destination": trip.destination,
        "status": trip.status,
        "start_date": str(trip.start_date) if trip.start_date else None,
        "end_date": str(trip.end_date) if trip.end_date else None,
        "budget": trip.budget,
        "travelers": trip.travelers,
        # 交通 / 酒店 / 分类预算，老行程可能为空
        "transport": plan.get("transport"),
        "hotel": plan.get("hotel"),
        "budget_breakdown": breakdown,
        "total_cost": breakdown["total"],
        "days": days_data
    }

class RevisionRequest(BaseModel):
    instruction: str


# --- 接口 4：批量计算路线（一次请求返回当天每一段的距离/耗时/真实道路折线） ---
class RouteSegmentIn(BaseModel):
    origin: str   # "经度,纬度"
    destination: str
    mode: str = "driving"


class RouteBatchRequest(BaseModel):
    segments: list[RouteSegmentIn] = []
    # 公交规划需要城市名，前端直接把行程目的地传过来
    city: str | None = None


@app.post("/api/v1/routes")
async def batch_routes(request: RouteBatchRequest):
    # 段数过多时截断，避免一次请求把高德的 QPS 打满
    segments = request.segments[:40]
    tasks = [
        get_route_detail(seg.origin, seg.destination, seg.mode, request.city)
        for seg in segments
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    routes = [None if isinstance(r, Exception) else r for r in results]
    return {"routes": routes}


# --- 接口 5：周边推荐（景点 / 美食 / 酒店） ---
NEARBY_CATEGORY_TYPES = {
    "scenic": "110000",   # 风景名胜
    "food": "050000",     # 餐饮服务
    "hotel": "100000",    # 住宿服务
    "shopping": "060000", # 购物服务
}


@app.get("/api/v1/pois/nearby")
async def nearby_pois(
    lng: float,
    lat: float,
    category: str = "scenic",
    radius: int = 1500,
    keywords: str | None = None,
    limit: int = 12,
):
    radius = max(200, min(radius, 5000))
    limit = max(1, min(limit, 25))
    types = NEARBY_CATEGORY_TYPES.get(category, NEARBY_CATEGORY_TYPES["scenic"])
    # 多要几条，因为下面会过滤掉「当前位置本身」，过滤后再截断
    pois = await search_around(
        lng=lng,
        lat=lat,
        keywords=(keywords or "").strip(),
        types=types,
        radius=radius,
        offset=min(limit + 3, 25),
    )

    results = []
    seen = set()
    for poi in pois:
        # 过滤掉「当前位置本身」（距离为 0 的那条），不然推荐列表第一条永远是自己
        if poi["distance"] <= 5 or poi["id"] in seen:
            continue
        seen.add(poi["id"])
        results.append(poi)
        if len(results) >= limit:
            break

    return {"category": category, "radius": radius, "pois": results}


# --- 接口 6：把周边推荐里的地点加到某一天的行程末尾 ---
class AddItemRequest(BaseModel):
    place_name: str
    lng: float
    lat: float
    cost_estimate: float = 0
    # 从周边推荐加入时的类别：sightseeing / food / shopping / entertainment / other
    category: str = "other"


def _minutes_of(time_str: str | None) -> int | None:
    try:
        hour, minute = (time_str or "").split(":")[:2]
        return int(hour) * 60 + int(minute)
    except (ValueError, AttributeError):
        return None


def _format_minutes(minutes: int) -> str:
    minutes = max(0, min(minutes, 23 * 60 + 59))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@app.post("/api/v1/trips/{trip_id}/days/{day_index}/items")
def add_trip_item(trip_id: int, day_index: int, request: AddItemRequest, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    day = next((d for d in trip.days if d.day_index == day_index), None)
    if not day:
        raise HTTPException(status_code=404, detail="没有找到对应的行程天")

    # 默认排在这一天最后一个地点之后（间隔 30 分钟），并预留 90 分钟游玩时间
    last_end = max(
        (_minutes_of(item.end_time) or 0 for item in day.items),
        default=None,
    )
    start = _format_minutes((last_end + 30) if last_end is not None else 9 * 60)
    end = _format_minutes(_minutes_of(start) + 90)

    item = TripItem(
        trip_day_id=day.id,
        place_name=request.place_name,
        start_time=start,
        end_time=end,
        category=request.category if request.category in ITEM_CATEGORIES else "other",
        cost_estimate=float(request.cost_estimate or 0),
        lng=request.lng,
        lat=request.lat,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "place_name": item.place_name,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "category": item.category,
        "cost_estimate": item.cost_estimate,
        "lng": item.lng,
        "lat": item.lat,
        "day_index": day_index,
    }


@app.post("/api/v1/trips/{trip_id}/revisions")
async def revise_trip(trip_id: int, request: RevisionRequest, db: Session = Depends(get_db)):
    # MVP 阶段简化：直接返回成功，让前端重新拉取数据
    # 实际生产环境中，这里要调用大模型，理解用户的修改指令，更新数据库
    print(f"收到修改指令: {request.instruction}")
    
    # 模拟处理延时
    import time
    time.sleep(1) 
    
    return {"status": "success", "message": "修改已应用（模拟）"}

@app.get("/")
def read_root():
    return {"message": "Welcome to TripPilot API"}