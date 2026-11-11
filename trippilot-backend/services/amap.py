# 导入 httpx，这是一个支持异步的 HTTP 请求库（比 requests 更适合 FastAPI）
import asyncio
import re

import httpx
# 从配置文件读取高德 Key
from config import settings

# 高德接口在“没有值”时会返回空列表 [] 而不是空字符串，统一兜底成 str/int，避免前端拿到奇怪的数据
def _as_str(value) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _as_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _simplify_poi(poi: dict) -> dict | None:
    """把高德返回的 POI 精简成前端需要的字段"""
    lng, lat = 0.0, 0.0
    location = _as_str(poi.get("location"))
    if "," in location:
        lng_str, lat_str = location.split(",", 1)
        lng, lat = _as_float(lng_str), _as_float(lat_str)
    if lng == 0.0 and lat == 0.0:
        return None

    biz_ext = poi.get("biz_ext") or {}
    rating = _as_str(biz_ext.get("rating"))
    # 酒店的参考价高德不一定给，有就带上，没有就留给模型估算
    cost = _as_float(biz_ext.get("cost"))
    photos = poi.get("photos") or []
    photo = _as_str(photos[0].get("url")) if photos and isinstance(photos[0], dict) else ""
    tel = _as_str(poi.get("tel")).split(",")[0]

    return {
        "id": _as_str(poi.get("id")),
        "name": _as_str(poi.get("name")),
        "address": _as_str(poi.get("address")),
        "distance": int(_as_float(poi.get("distance"))),
        "type": _as_str(poi.get("type")),
        "rating": rating,
        "cost": round(cost) if cost > 0 else 0,
        "tel": tel,
        "photo": photo,
        "lng": lng,
        "lat": lat,
    }

# 定义一个异步函数，用来搜索景点
# async def 是 Python 的异步语法，表示这个函数在等待网络请求时，可以去干别的事
async def search_places(keywords: str, city: str):
    # 拼接高德地图的“搜索POI”接口 URL
    # 参数解释：key 是身份认证，keywords 是关键词（如：武侯祠），city 是城市（如：成都），types 限定搜索类别为风景名胜和博物馆
    url = f"https://restapi.amap.com/v3/place/text?key={settings.AMAP_API_KEY}&keywords={keywords}&city={city}&types=风景名胜|博物馆"
    
    # 使用 httpx 的异步客户端发起 GET 请求
    # async with 是异步上下文管理器，确保请求结束后自动关闭连接
    async with httpx.AsyncClient() as client:
        # await 表示等待这个网络请求完成，在等待期间程序不会卡死
        response = await client.get(url)
        # 把返回的数据解析成 Python 字典（JSON格式）
        data = response.json()
        
        # 高德接口成功时会返回 status="1"
        if data.get("status") == "1":
            # 返回里面所有的 POI（兴趣点）列表
            return data.get("pois", [])
        # 如果请求失败（比如 Key 过期），返回空列表，不要直接报错让程序崩溃
        return []

# 定义一个异步函数，用来获取两点之间的路线耗时
async def get_route_time(origin_lnglat: str, dest_lnglat: str, mode: str = "transit"):
    # 参数说明：
    # origin_lnglat 是起点经纬度，格式为 "经度,纬度"，例如 "104.043,30.641"
    # dest_lnglat 是终点经纬度
    # mode 是交通方式，默认是 transit（公交），可选 driving（驾车）
    
    # 如果是公交
    if mode == "transit":
        # 拼接公交路线规划接口
        url = f"https://restapi.amap.com/v3/direction/transit/integrated?key={settings.AMAP_API_KEY}&origin={origin_lnglat}&destination={dest_lnglat}&city=成都"
    # 如果是驾车
    else:
        # 拼接驾车路线规划接口
        url = f"https://restapi.amap.com/v3/direction/driving?key={settings.AMAP_API_KEY}&origin={origin_lnglat}&destination={dest_lnglat}"
        
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        
        # 异常处理：因为第三方接口返回的JSON结构可能不固定，如果没有找到数据，会引发 KeyError 或 IndexError
        # 使用 try...except 可以防止程序直接崩溃，返回默认值 0
        try:
            # 如果是公交，获取第一条公交方案，["duration"] 是耗时（单位：秒），整除 60 转换成分钟
            if mode == "transit":
                return int(data["route"]["transits"][0]["duration"]) // 60
            # 如果是驾车，获取第一条驾车方案，耗时转换成分钟
            else:
                return int(data["route"]["paths"][0]["duration"]) // 60
        # 如果出现任何解析错误，默认耗时返回 0 分钟
        except (KeyError, IndexError):
            return 0


# --- 周边搜索：以某个经纬度为中心，找附近的景点 / 美食 / 酒店 ---
async def search_around(
    lng: float,
    lat: float,
    keywords: str = "",
    types: str = "",
    radius: int = 1500,
    offset: int = 12,
):
    params = {
        "key": settings.AMAP_API_KEY,
        "location": f"{lng},{lat}",
        "radius": radius,
        "offset": offset,
        "page": 1,
        "sortrule": "distance",
        "extensions": "all",
    }
    if keywords:
        params["keywords"] = keywords
    elif types:
        params["types"] = types

    url = "https://restapi.amap.com/v3/place/around"
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if data.get("status") != "1":
        return []

    pois = []
    for poi in data.get("pois", []):
        simplified = _simplify_poi(poi)
        if simplified and simplified["name"]:
            pois.append(simplified)
    return pois


# --- 酒店搜索：给规划 Agent 挑真实酒店用 ---
async def search_hotels(keywords: str, city: str, limit: int = 8) -> list[dict]:
    """按关键词和城市搜索酒店，返回名称 / 地址 / 评分 / 参考价"""
    params = {
        "key": settings.AMAP_API_KEY,
        "keywords": (keywords or "酒店").strip(),
        "city": (city or "").strip(),
        "types": "100000",  # 住宿服务
        "offset": min(max(limit, 1), 25),
        "page": 1,
        "extensions": "all",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get("https://restapi.amap.com/v3/place/text", params=params)
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    if data.get("status") != "1":
        return []

    hotels = []
    for poi in data.get("pois", []):
        simplified = _simplify_poi(poi)
        if simplified and simplified["name"]:
            hotels.append(simplified)
        if len(hotels) >= limit:
            break
    return hotels


# --- 城际交通：城市中心坐标 + 真实的驾车距离/耗时 ---
_city_coord_cache: dict[str, tuple[float, float] | None] = {}


async def _geocode_city(city: str) -> tuple[float, float] | None:
    """城市名 -> (经度, 纬度)，结果缓存，避免反复打高德"""
    name = (city or "").strip()
    if not name:
        return None
    if name in _city_coord_cache:
        return _city_coord_cache[name]

    coord = None
    params = {"key": settings.AMAP_API_KEY, "address": name, "city": name}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get("https://restapi.amap.com/v3/geocode/geo", params=params)
            data = response.json()
        geocodes = data.get("geocodes") or []
        if data.get("status") == "1" and geocodes:
            location = _as_str(geocodes[0].get("location"))
            lng_str, _, lat_str = location.partition(",")
            lng, lat = _as_float(lng_str), _as_float(lat_str)
            if lng and lat:
                coord = (lng, lat)
    except (httpx.HTTPError, ValueError, TypeError):
        coord = None

    _city_coord_cache[name] = coord
    return coord


async def get_intercity_info(origin_city: str, dest_city: str) -> dict:
    """
    返回两座城市中心的坐标，以及高德真实的驾车距离 / 耗时。
    高铁和航班没有公开的实时接口，交给模型结合距离按常识估算。
    """
    origin_city = (origin_city or "").strip()
    dest_city = (dest_city or "").strip()
    origin_coord, dest_coord = await asyncio.gather(
        _geocode_city(origin_city),
        _geocode_city(dest_city),
    )
    if not origin_coord or not dest_coord:
        return {
            "error": f"无法解析城市坐标（{origin_city or '出发地'} / {dest_city or '目的地'}），请按常识估算"
        }

    origin_lnglat = f"{origin_coord[0]},{origin_coord[1]}"
    dest_lnglat = f"{dest_coord[0]},{dest_coord[1]}"
    route = await get_route_detail(origin_lnglat, dest_lnglat, "driving", city=origin_city)

    distance_km = round(route["distance"] / 1000, 1) if route else 0
    duration_minutes = round(route["duration"] / 60) if route else 0

    return {
        "origin": {"city": origin_city, "lng": origin_coord[0], "lat": origin_coord[1]},
        "destination": {"city": dest_city, "lng": dest_coord[0], "lat": dest_coord[1]},
        "driving": {
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
            # 油费 + 过路费按每公里约 0.9 元粗略估算（每辆车）
            "fuel_toll_cost_per_vehicle": round(distance_km * 0.9) if distance_km else 0,
        },
        "note": "驾车数据来自高德实时路线；高铁/航班的时间与票价请按常识估算，并标注为预估",
    }


# --- 地点坐标补全：模型偶尔不给经纬度，用高德反查兜底 ---
_geocode_cache: dict[str, tuple[float, float] | None] = {}
_geocode_semaphore = asyncio.Semaphore(2)

# 高德个人 Key 的 QPS 很低，所有坐标查询统一节流，避免并发时被限流拿到错误结果
_amap_rate_lock = asyncio.Lock()
_amap_last_request_at = 0.0
_AMAP_MIN_INTERVAL = 0.3


async def _pace_amap():
    global _amap_last_request_at
    async with _amap_rate_lock:
        loop = asyncio.get_running_loop()
        wait = _amap_last_request_at + _AMAP_MIN_INTERVAL - loop.time()
        if wait > 0:
            await asyncio.sleep(wait)
        _amap_last_request_at = loop.time()

# 行程项名字里常见的活动后缀，去掉后更容易命中真实地点
_PLACE_SUFFIXES = (
    "办理入住", "周边简餐", "周边午餐", "周边晚餐", "周边", "简餐", "晚餐", "午餐",
    "早餐", "夜宵", "夜景闲逛", "夜景", "闲逛", "打卡", "拍照", "看升旗", "游览", "参观",
)


def _parse_location(value) -> tuple[float, float] | None:
    lng_str, _, lat_str = _as_str(value).partition(",")
    lng, lat = _as_float(lng_str), _as_float(lat_str)
    if lng and lat:
        return (lng, lat)
    return None


def _place_candidates(name: str) -> list[str]:
    """把「前门大街·鲜鱼口美食街晚餐」这类描述拆成可以查询的地名候选"""
    raw = _as_str(name)
    candidates: list[str] = []

    def add(value: str):
        value = value.strip(" ·+，,、/—–-")
        value = re.sub(r"[\s·+，,、/—–-]+$", "", value)
        if 2 <= len(value) <= 40 and value not in candidates:
            candidates.append(value)

    add(raw)
    base = re.split(r"[（(]", raw)[0]
    add(base)
    for part in re.split(r"[·+，,、/\s]+", base):
        add(part)
    for value in list(candidates):
        for suffix in _PLACE_SUFFIXES:
            if value.endswith(suffix) and len(value) > len(suffix) + 1:
                add(value[: -len(suffix)])
    return candidates


# 高德在限流 / 配额不足时会返回这些关键字，需要退避重试；
# 其他 status=0（如地址无法解析）只代表「查无结果」，交给上层继续尝试 POI 搜索。
_AMAP_RETRY_MARKERS = ("QPS", "LIMIT", "QUOTA", "RATE", "EXCEED", "BUSY", "FREQUENT")


async def _request_amap(client: httpx.AsyncClient, url: str, params: dict) -> dict | None:
    """
    请求高德接口。成功返回 JSON；被限流时退避重试；
    查无结果返回一个空的成功结构；接口彻底不可用时返回 None。
    """
    for attempt in range(3):
        data = None
        await _pace_amap()
        try:
            response = await client.get(url, params=params)
            data = response.json()
        except (httpx.HTTPError, ValueError):
            data = None

        if isinstance(data, dict):
            if data.get("status") == "1":
                return data

            info = str(data.get("info") or "").upper()
            if not any(marker in info for marker in _AMAP_RETRY_MARKERS):
                # 业务层面的「查无结果」，不要重试，也不要当成接口故障
                return {"status": "0", "geocodes": [], "pois": []}

        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))
    return None


def _same_city(requested: str, returned: str) -> bool:
    left = _as_str(requested).replace("市", "")
    right = _as_str(returned).replace("市", "")
    if not left or not right:
        return True
    return left in right or right in left


async def _geocode_address(client: httpx.AsyncClient, address: str, city: str):
    """返回 (坐标, 标准化地址, 所在城市, 是否成功请求)"""
    params = {"key": settings.AMAP_API_KEY, "address": address, "city": city}
    data = await _request_amap(client, "https://restapi.amap.com/v3/geocode/geo", params)
    if data is None:
        return None, "", "", False
    geocodes = data.get("geocodes") or []
    if not geocodes:
        return None, "", "", True
    first = geocodes[0]
    coord = _parse_location(first.get("location"))
    formatted = _as_str(first.get("formatted_address"))
    returned_city = _as_str(first.get("city")) or _as_str(first.get("province"))
    return coord, formatted, returned_city, True


def _longest_common_substring(left: str, right: str) -> int:
    if not left or not right:
        return 0
    best = 0
    previous = [0] * (len(right) + 1)
    for i in range(1, len(left) + 1):
        current = [0] * (len(right) + 1)
        for j in range(1, len(right) + 1):
            if left[i - 1] == right[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
        previous = current
    return best


def _match_score(candidate: str, poi_name: str) -> int:
    """查询词和 POI 名称的相似度：包含关系优先，其次是最长公共子串"""
    left = _as_str(candidate)
    right = _as_str(poi_name)
    if not left or not right:
        return 0
    if left in right or right in left:
        return min(len(left), len(right)) + 2
    return _longest_common_substring(left, right)


async def _text_search_location(client: httpx.AsyncClient, keywords: str, city: str):
    """返回 (坐标, 是否成功请求)"""
    params = {
        "key": settings.AMAP_API_KEY,
        "keywords": keywords,
        "city": city,
        "offset": 10,
        "page": 1,
        "extensions": "base",
    }
    data = await _request_amap(client, "https://restapi.amap.com/v3/place/text", params)
    if data is None:
        return None, False

    best_score = 0
    best_coord = None
    for poi in data.get("pois") or []:
        if not _same_city(city, poi.get("cityname") or ""):
            continue
        score = _match_score(keywords, poi.get("name"))
        if score < 3 or score <= best_score:
            continue
        location = _parse_location(poi.get("location"))
        if location:
            best_score = score
            best_coord = location
    return best_coord, True


async def geocode_place(name: str, city: str) -> tuple[float, float] | None:
    """
    地点名 -> (经度, 纬度)。先试地理编码（校验地址相关性），
    不相关或查无结果时再用 POI 搜索（带名称相似度校验）。结果（包括失败）会缓存。
    """
    raw = _as_str(name)
    city = _as_str(city)
    if not raw:
        return None
    cache_key = f"{city}|{raw}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    coord = None
    api_failed = False
    candidates = _place_candidates(raw)
    try:
        async with _geocode_semaphore:
            async with httpx.AsyncClient(timeout=8) as client:
                for candidate in candidates:
                    # 1. 地理编码：结果地址必须包含查询词里的地名，避免把「农家午餐」解析到外地
                    geo_coord, formatted, returned_city, ok = await _geocode_address(
                        client, candidate, city
                    )
                    if not ok:
                        api_failed = True
                        coord = None
                        break
                    if (
                        geo_coord
                        and _same_city(city, returned_city)
                        and _match_score(candidate, formatted) >= 3
                    ):
                        coord = geo_coord
                        break

                    # 2. POI 搜索：按名称相似度挑最匹配的一条
                    coord, ok = await _text_search_location(client, candidate, city)
                    if not ok:
                        api_failed = True
                        coord = None
                        break
                    if coord:
                        break
    except (httpx.HTTPError, ValueError, TypeError):
        api_failed = True
        coord = None

    if len(_geocode_cache) > 1000:
        _geocode_cache.clear()
    # 接口故障导致的失败不缓存，下次打开行程还能再试
    if not (api_failed and coord is None):
        _geocode_cache[cache_key] = coord
    return coord


def _parse_polyline(polyline: str) -> list[list[float]]:
    """高德的 polyline 是 "lng,lat;lng,lat;..." 的字符串，转成前端能用的坐标数组"""
    points = []
    for pair in (polyline or "").split(";"):
        if not pair:
            continue
        lng_str, _, lat_str = pair.partition(",")
        if not lat_str:
            continue
        points.append([_as_float(lng_str), _as_float(lat_str)])
    return points


def _thin_points(points: list[list[float]], max_points: int = 140) -> list[list[float]]:
    """抽稀坐标点，避免一段路线就把前端画布刷爆"""
    if len(points) <= max_points:
        return points
    step = len(points) / (max_points - 1)
    result = [points[int(i * step)] for i in range(max_points - 1)]
    result.append(points[-1])
    return result


# --- 路线详情：驾车（打车）/ 公交 / 步行 ---
# 个人版高德 Key 有 QPS 限制，路线接口并发太高会直接返回空结果，
# 这里用信号量把并发压到 2，并做一次重试；顺带缓存结果，避免重复请求。
_route_semaphore = asyncio.Semaphore(2)
_route_cache: dict[str, dict] = {}
_city_cache: dict[str, str] = {}

ROUTE_MODES = {"driving", "transit", "walking"}

ROUTE_URLS = {
    "driving": "https://restapi.amap.com/v3/direction/driving",
    "walking": "https://restapi.amap.com/v3/direction/walking",
    "transit": "https://restapi.amap.com/v3/direction/transit/integrated",
}


async def _resolve_city(origin_lnglat: str) -> str:
    """公交规划接口必须带城市，用逆地理编码反查一次并缓存"""
    lng, _, lat = origin_lnglat.partition(",")
    key = f"{_as_float(lng):.2f},{_as_float(lat):.2f}"
    if key in _city_cache:
        return _city_cache[key]

    params = {"key": settings.AMAP_API_KEY, "location": origin_lnglat, "extensions": "base"}
    city = ""
    try:
        async with _route_semaphore:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get("https://restapi.amap.com/v3/geocode/regeo", params=params)
                data = response.json()
        component = (data.get("regeocode") or {}).get("addressComponent") or {}
        # 直辖市的 city 字段是空列表，退回用 province
        city = _as_str(component.get("city")) or _as_str(component.get("province"))
    except (httpx.HTTPError, ValueError, TypeError):
        city = ""

    if city:
        _city_cache[key] = city
    return city


def _step_distance_duration(node: dict) -> tuple[int, int]:
    return int(_as_float(node.get("distance"))), int(_as_float(node.get("duration")))


def _parse_driving(data: dict) -> dict | None:
    paths = (data.get("route") or {}).get("paths") or []
    if not paths:
        return None
    path = paths[0]

    points: list[list[float]] = []
    steps = []
    for step in path.get("steps", []):
        points.extend(_parse_polyline(step.get("polyline", "")))
        instruction = _as_str(step.get("instruction"))
        if instruction and len(steps) < 12:
            distance, duration = _step_distance_duration(step)
            steps.append({"mode": "drive", "text": instruction, "distance": distance, "duration": duration})

    taxi_cost = _as_float((data.get("route") or {}).get("taxi_cost")) or _as_float(path.get("taxi_cost"))
    return {
        "mode": "driving",
        "distance": int(_as_float(path.get("distance"))),
        "duration": int(_as_float(path.get("duration"))),
        "points": _thin_points(points),
        "cost": taxi_cost if taxi_cost > 0 else None,
        "steps": steps,
    }


def _parse_walking(data: dict) -> dict | None:
    paths = (data.get("route") or {}).get("paths") or []
    if not paths:
        return None
    path = paths[0]

    points: list[list[float]] = []
    steps = []
    for step in path.get("steps", []):
        points.extend(_parse_polyline(step.get("polyline", "")))
        instruction = _as_str(step.get("instruction"))
        if instruction and len(steps) < 12:
            distance, duration = _step_distance_duration(step)
            steps.append({"mode": "walk", "text": instruction, "distance": distance, "duration": duration})

    return {
        "mode": "walking",
        "distance": int(_as_float(path.get("distance"))),
        "duration": int(_as_float(path.get("duration"))),
        "points": _thin_points(points),
        "cost": None,
        "steps": steps,
    }


def _split_line_name(name: str) -> tuple[str, str]:
    """"地铁4号线(安河桥北--天宫院)" -> ("地铁4号线", "天宫院")"""
    base, _, rest = name.partition("(")
    tail = rest.rstrip(")").replace("—", "--").replace("－", "--")
    # 括号里是「起点--终点」，取终点站作为开往方向
    direction = tail.split("--")[-1].strip()
    return base.strip() or name, direction


def _parse_transit(data: dict) -> dict | None:
    transits = (data.get("route") or {}).get("transits") or []
    if not transits:
        return None
    transit = transits[0]

    points: list[list[float]] = []
    steps = []

    def add_walk(node: dict):
        distance, duration = _step_distance_duration(node)
        points.extend(_parse_polyline(node.get("polyline", "")))
        if distance <= 0:
            return
        # 优先用高德给的步行指引，没有就自己拼一句
        instruction = ""
        for walk_step in node.get("steps", []):
            instruction = _as_str(walk_step.get("instruction"))
            if instruction:
                break
        steps.append({
            "mode": "walk",
            "distance": distance,
            "duration": duration,
            "text": instruction or f"步行 {distance} 米",
        })

    for segment in transit.get("segments", []):
        walking = segment.get("walking") or {}
        if walking:
            add_walk(walking)

        bus = segment.get("bus") or {}
        buslines = bus.get("buslines") or []
        if not buslines:
            continue
        line = buslines[0]
        name = _as_str(line.get("name"))
        base, direction = _split_line_name(name)
        points.extend(_parse_polyline(line.get("polyline", "")))

        departure = (line.get("departure_stop") or {}).get("name")
        arrival = (line.get("arrival_stop") or {}).get("name")
        steps.append({
            "mode": "subway" if ("地铁" in base or "轨道" in base) else "bus",
            "line": base,
            "direction": direction,
            "from": _as_str(departure),
            "to": _as_str(arrival),
            "stops": int(_as_float(line.get("via_num"))),
            "distance": int(_as_float(line.get("distance"))),
            "duration": int(_as_float(line.get("duration"))),
        })

    cost = _as_float(transit.get("cost"))

    # 把步行段落润色成「步行 276 米到 XX 站 / 步行 479 米到达终点」，比高德原始转向指令更直观
    for index, step in enumerate(steps):
        if step["mode"] != "walk":
            continue
        next_step = steps[index + 1] if index + 1 < len(steps) else None
        if next_step and next_step["mode"] in ("bus", "subway") and next_step.get("from"):
            step["text"] = f"步行 {step['distance']} 米到 {next_step['from']}"
        elif next_step is None:
            step["text"] = f"步行 {step['distance']} 米到达终点"

    return {
        "mode": "transit",
        "distance": int(_as_float(transit.get("distance"))),
        "duration": int(_as_float(transit.get("duration"))),
        "points": _thin_points(points),
        "cost": cost if cost > 0 else None,
        "walking_distance": int(_as_float(transit.get("walking_distance"))),
        "steps": steps,
    }


_PARSERS = {"driving": _parse_driving, "walking": _parse_walking, "transit": _parse_transit}


async def get_route_detail(origin_lnglat: str, dest_lnglat: str, mode: str = "driving", city: str | None = None):
    """mode: driving（打车）/ transit（公交地铁）/ walking（步行）"""
    if mode not in ROUTE_MODES:
        mode = "driving"

    cache_key = f"{mode}|{origin_lnglat}->{dest_lnglat}"
    if cache_key in _route_cache:
        return _route_cache[cache_key]

    params = {
        "key": settings.AMAP_API_KEY,
        "origin": origin_lnglat,
        "destination": dest_lnglat,
        "extensions": "all" if mode == "driving" else "base",
    }
    if mode == "driving":
        params["strategy"] = 0
    elif mode == "transit":
        resolved_city = (city or "").strip() or await _resolve_city(origin_lnglat)
        params["city"] = resolved_city or "全国"
        params["strategy"] = 0

    parse = _PARSERS[mode]

    for attempt in range(2):
        try:
            async with _route_semaphore:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(ROUTE_URLS[mode], params=params)
                    data = response.json()
            result = parse(data) if data.get("status") == "1" else None
            if not result:
                # 常见原因是并发限流或没有公交方案，稍等后重试一次
                if attempt == 0:
                    await asyncio.sleep(0.4)
                    continue
                return None

            # 简单的容量控制，MVP 阶段够用
            if len(_route_cache) > 800:
                _route_cache.clear()
            _route_cache[cache_key] = result
            return result
        except (KeyError, IndexError, TypeError, ValueError, httpx.HTTPError):
            if attempt == 0:
                await asyncio.sleep(0.4)
                continue
            return None

    return None
