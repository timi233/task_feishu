import requests
import json

# 基础URL
BASE_URL = "http://localhost:8000"

def test_get_tasks():
    """测试获取任务列表"""
    response = requests.get(f"{BASE_URL}/api/tasks")
    print("Get tasks response:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("Tasks count by day:")
        for day, tasks in data.items():
            print(f"  {day}: {len(tasks)} tasks")

def test_get_filters():
    """测试获取筛选器列表"""
    response = requests.get(f"{BASE_URL}/api/filters")
    print("\nGet filters response:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("Available filters:", data["available_filters"])
        print("Active filter:", data["active_filter"])

def test_activate_filter(filter_name):
    """测试激活筛选器"""
    response = requests.post(f"{BASE_URL}/api/filters/activate?filter_name={filter_name}")
    print(f"\nActivate filter '{filter_name}' response:", response.status_code)
    if response.status_code == 200:
        print(response.json())

def test_add_filter():
    """测试添加筛选器"""
    new_filter = {
        "name": "high_priority",
        "conditions": [
            {
                "field": "status",
                "operator": "in",
                "value": ["紧急", "高优先级"]
            }
        ],
        "enabled": True,
        "logic": "and"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/filters/add",
        params=new_filter
    )
    print("\nAdd filter response:", response.status_code)
    if response.status_code == 200:
        print(response.json())

def test_get_tasks_with_filter(filter_name):
    """测试使用筛选器获取任务"""
    response = requests.get(f"{BASE_URL}/api/tasks?filter_name={filter_name}")
    print(f"\nGet tasks with filter '{filter_name}' response:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print(f"Filtered tasks count by day (filter: {filter_name}):")
        for day, tasks in data.items():
            print(f"  {day}: {len(tasks)} tasks")

if __name__ == "__main__":
    print("Testing filter functionality...")
    
    # 测试获取任务列表
    test_get_tasks()
    
    # 测试获取筛选器
    test_get_filters()
    
    # 测试添加筛选器
    test_add_filter()
    
    # 再次获取筛选器列表
    test_get_filters()
    
    # 测试使用筛选器获取任务
    test_get_tasks_with_filter("high_priority")
    
    # 测试激活筛选器
    test_activate_filter("high_priority")
    
    # 测试获取任务（使用激活的筛选器）
    test_get_tasks()