# 导入我们写的校验函数
from services.validator import validate_budget, validate_time_conflict

print("===== 测试 1：预算校验 =====")
# 场景 A：预算充足
res1 = validate_budget(total_estimate=4500, budget_limit=5000)
print(f"预估 4500，上限 5000：{res1['message']}")
# 场景 B：预算超支
res2 = validate_budget(total_estimate=5200, budget_limit=5000)
print(f"预估 5200，上限 5000：{res2['message']}")

print("\n===== 测试 2：时间冲突校验 =====")
# 构造一个模拟的行程列表
mock_items = [
    {"place_name": "武侯祠", "start_time": "09:00", "end_time": "11:00"},
    {"place_name": "锦里", "start_time": "10:30", "end_time": "12:30"},  # 这个和武侯祠有重叠
    {"place_name": "杜甫草堂", "start_time": "14:00", "end_time": "16:00"}
]

# 调用校验函数
res3 = validate_time_conflict(mock_items)
print(f"校验结果：{res3['message']}")

# 构造一个没有冲突的行程
mock_items_ok = [
    {"place_name": "武侯祠", "start_time": "09:00", "end_time": "11:00"},
    {"place_name": "锦里", "start_time": "11:30", "end_time": "13:30"},
]
res4 = validate_time_conflict(mock_items_ok)
print(f"校验结果：{res4['message']}")