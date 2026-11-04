# 定义预算校验函数
def validate_budget(total_estimate: float, budget_limit: float) -> dict:
    # 如果预估总花费 > 预算上限
    if total_estimate > budget_limit:
        # 返回一个字典，包含是否通过（False）和提示信息
        return {
            "passed": False, 
            "message": f"预算超支！预估{total_estimate}元，超出{total_estimate - budget_limit}元。"
        }
    # 如果未超支，返回通过
    return {"passed": True, "message": "预算符合要求"}

# 定义时间冲突校验函数
def validate_time_conflict(items: list) -> dict:
    # items 是一个列表，里面每个元素是一个字典，包含 'start_time' 和 'end_time' 以及 'place_name'
    # 如果没有行程，直接返回通过
    if not items:
        return {"passed": True, "message": "无行程"}
        
    # 1. 按开始时间对行程进行排序
    # sorted 是内置排序函数，key=lambda x: x['start_time'] 表示按照字典里的 'start_time' 字段排序
    # 因为时间格式是 "09:30" 这种字符串，字符串比较大小是可行的（"09:30" < "11:00"）
    sorted_items = sorted(items, key=lambda x: x['start_time'])
    
    # 2. 遍历排序后的列表，检查相邻两个行程是否有重叠
    # range(len(sorted_items) - 1) 遍历到倒数第二个即可，因为我们要比较当前和下一个
    for i in range(len(sorted_items) - 1):
        # 当前行程的结束时间
        current_end = sorted_items[i]['end_time']
        # 下一个行程的开始时间
        next_start = sorted_items[i+1]['start_time']
        
        # 如果当前结束时间 > 下一个开始时间，说明有重叠（时间冲突）
        if current_end > next_start:
            return {
                "passed": False, 
                "message": f"时间冲突！'{sorted_items[i]['place_name']}' 的结束时间晚于下一个景点的开始时间。"
            }
    # 如果循环结束都没有冲突，说明通过
    return {"passed": True, "message": "时间安排无冲突"}