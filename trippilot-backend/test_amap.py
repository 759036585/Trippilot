# 导入 asyncio 库，因为我们的 amap.py 里的函数是异步的（async def），需要用 asyncio.run() 来执行
import asyncio
# 导入我们刚才写好的高德地图服务
from services.amap import search_places, get_route_time

# 定义一个异步的主函数
async def main():
    print("===== 测试 1：搜索景点 =====")
    # 调用 search_places，搜索成都的“武侯祠”
    pois = await search_places(keywords="武侯祠", city="成都")
    
    # 检查返回的数据是否为空
    if not pois:
        print("❌ 搜索失败：请检查高德 API Key 是否正确，或者网络是否通畅。")
        return
    
    # 打印搜索到的第一个结果（通常是最匹配的）
    first_poi = pois[0]
    print(f"✅ 成功搜到景点：{first_poi['name']}")
    print(f"   地址：{first_poi['address']}")
    # 高德返回的 location 格式是 "经度,纬度"，例如 "104.043,30.641"
    print(f"   经纬度：{first_poi['location']}")
    
    # 我们再搜索一个“大熊猫繁育研究基地”
    pois2 = await search_places(keywords="大熊猫繁育研究基地", city="成都")
    if pois2:
        second_poi = pois2[0]
        print(f"✅ 成功搜到景点：{second_poi['name']}")
        print(f"   经纬度：{second_poi['location']}")
        
        print("\n===== 测试 2：计算两景点间的公交耗时 =====")
        # 调用 get_route_time，传入两个景点的经纬度
        # 注意：高德接口的经纬度顺序是 "经度,纬度"
        origin_lnglat = first_poi['location']
        dest_lnglat = second_poi['location']
        
        print(f"正在计算从【{first_poi['name']}】到【{second_poi['name']}】的公交耗时...")
        duration = await get_route_time(origin_lnglat, dest_lnglat, mode="transit")
        
        if duration > 0:
            print(f"✅ 路线计算成功：预计公交耗时 {duration} 分钟。")
        else:
            print("❌ 路线计算失败：请检查高德返回的数据结构。")

# Python 的入口判断，如果直接运行这个文件，就执行 main()
if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())