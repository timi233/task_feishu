import requests
import json

# 基础URL
BASE_URL = "http://localhost:8000"

def add_application_status_filter():
    """添加申请状态筛选器"""
    # 定义筛选器条件
    conditions = [
        {
            "field": "status",  # 申请状态字段
            "operator": "in",
            "value": ["已通过", "审批中"]
        },
        {
            "field": "start_date",  # 服务开始时间字段
            "operator": "this_week"  # 本周
        }
    ]
    
    # 构造请求体
    payload = {
        "name": "application_status_this_week",
        "conditions": conditions,
        "enabled": True,
        "logic": "and"
    }
    
    # 添加筛选器
    response = requests.post(
        f"{BASE_URL}/api/filters/add",
        json=payload
    )
    
    print("Add filter response:", response.status_code)
    if response.status_code == 200:
        print(response.json())
        return True
    else:
        print("Error:", response.text)
        return False

def test_filter():
    """测试新添加的筛选器"""
    # 激活筛选器
    response = requests.post(f"{BASE_URL}/api/filters/activate?filter_name=application_status_this_week")
    print("Activate filter response:", response.status_code)
    
    # 获取任务列表（使用新筛选器）
    response = requests.get(f"{BASE_URL}/api/tasks")
    print("Get tasks with filter response:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("Filtered tasks count by day:")
        for day, tasks in data.items():
            print(f"  {day}: {len(tasks)} tasks")

if __name__ == "__main__":
    print("Adding application status filter...")
    if add_application_status_filter():
        print("\nTesting filter...")
        test_filter()