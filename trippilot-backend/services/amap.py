# 导入 httpx，这是一个支持异步的 HTTP 请求库（比 requests 更适合 FastAPI）
import asyncio
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
