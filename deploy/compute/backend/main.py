# 后端服务主入口

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware # 添加CORS中间件导入
from fastapi.staticfiles import StaticFiles # 添加静态文件服务导入
import uvicorn
from pydantic import BaseModel
from typing import List, Optional
import datetime
# 从本地数据库模块导入
from task_db_mysql import init_db, get_tasks_from_db
# 导入筛选模块
from task_filter import task_filter

app = FastAPI()

# 添加CORS中间件，允许所有来源、方法和请求头（开发环境）
# 在生产环境中，你应该指定具体的域名以提高安全性
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 挂载静态文件目录，提供前端页面
# 当用户访问 /static 路径时，会返回 static 目录下的文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 在应用启动时初始化数据库
init_db()

# 定义Pydantic模型，用于API响应
class TaskItem(BaseModel):
    record_id: str
    task_name: str
    assignee: str
    status: str # 展示状态（进行中/已结束/优先级）
    priority: Optional[str] = None # 原始优先级
    application_status: Optional[str] = None # 申请状态
    date: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    weekday: Optional[str] = None

class TaskGroup(BaseModel):
    monday: List[TaskItem]
    tuesday: List[TaskItem]
    wednesday: List[TaskItem]
    thursday: List[TaskItem]
    friday: List[TaskItem]
    weekend: List[TaskItem]

def get_current_week_dates() -> tuple[str, str]:
    """获取本周的开始日期和结束日期 (YYYY-MM-DD)"""
    today = datetime.date.today()
    # 计算本周日（一周的开始）
    start_of_week = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    # 计算本周六（一周的结束）
    end_of_week = start_of_week + datetime.timedelta(days=6)
    
    start_str = start_of_week.strftime("%Y-%m-%d")
    end_str = end_of_week.strftime("%Y-%m-%d")
    
    return start_str, end_str

@app.get("/")
async def read_root():
    return {"message": "派工系统后端服务"}

@app.get("/api/tasks", response_model=TaskGroup)
async def get_tasks(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    filter_name: Optional[str] = Query(None, description="筛选器名称")
):
    """
    从本地数据库获取并返回处理后的任务数据。
    
    如果不提供 start_date 和 end_date，则返回本周任务数据。
    如果提供 start_date 和 end_date，则返回该日期范围内的任务数据。
    可以通过 filter_name 参数指定使用哪个筛选器。
    """
    print(f"Received request to /api/tasks with start_date={start_date}, end_date={end_date}, filter_name={filter_name}")
    
    try:
        # 如果提供了筛选器名称或使用激活的筛选器，则从数据库获取所有任务进行筛选
        if filter_name or not start_date or not end_date:
            # 获取所有任务
            all_tasks = []
            task_groups_data = get_tasks_from_db()  # 不提供日期范围，获取所有任务
            for day_tasks in task_groups_data.values():
                all_tasks.extend(day_tasks)
            
            # 如果没有提供日期范围，则使用本周的日期范围进行最终分组
            if not start_date or not end_date:
                start_date, end_date = get_current_week_dates()
                print(f"No date range provided, using current week: {start_date} to {end_date}")
        else:
            # 如果没有筛选器且提供了日期范围，则只获取指定日期范围内的任务
            print(f"Date range provided: {start_date} to {end_date}")
            task_groups_data = get_tasks_from_db(start_date, end_date)
            
            # 将所有任务合并为一个列表进行筛选
            all_tasks = []
            for day_tasks in task_groups_data.values():
                all_tasks.extend(day_tasks)
        
        # 如果没有指定筛选器名称，则使用当前激活的筛选器
        if not filter_name:
            filter_name = task_filter.get_active_filter()
            print(f"No filter name provided, using active filter: {filter_name}")
        
        # 应用筛选器
        filtered_tasks = task_filter.filter_tasks(all_tasks, filter_name)
        print(f"Filtered tasks count: {len(filtered_tasks)}")
        
        # 打印筛选后的任务详情用于调试
        if filtered_tasks:
            print("Filtered tasks details:")
            for i, task in enumerate(filtered_tasks):
                print(f"  {i+1}. Record ID: {task.get('record_id')}, Weekday: {task.get('weekday')}")
        
        # 重新按星期分组，并只保留指定日期范围内的任务
        filtered_task_groups = {
            "monday": [],
            "tuesday": [],
            "wednesday": [],
            "thursday": [],
            "friday": [],
            "weekend": [],
            "unknown_date": []
        }
        
        for task in filtered_tasks:
            # 如果提供了日期范围，则只保留该范围内的任务
            if start_date and end_date:
                task_date = task.get("date")
                if task_date and (task_date < start_date or task_date > end_date):
                    continue  # 跳过不在日期范围内的任务
            
            weekday = task.get("weekday", "unknown_date")
            print(f"Adding task to group: {weekday}")  # 调试信息
            if weekday in filtered_task_groups:
                filtered_task_groups[weekday].append(task)
            else:
                filtered_task_groups["unknown_date"].append(task)
        
        # 打印分组结果用于调试
        for day, tasks in filtered_task_groups.items():
            if tasks:
                print(f"Group {day}: {len(tasks)} tasks")
        
        # 转换为Pydantic模型
        task_groups = TaskGroup(**filtered_task_groups)
        
        print("Successfully served tasks from database")
        return task_groups
        
    except Exception as e:
        print(f"Error serving tasks from database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from database: {e}")

@app.get("/api/filters")
async def get_filters():
    """获取所有可用的筛选器"""
    return {
        "available_filters": task_filter.get_available_filters(),
        "active_filter": task_filter.get_active_filter()
    }

@app.post("/api/filters/activate")
async def activate_filter(filter_name: str):
    """激活指定的筛选器"""
    if task_filter.set_active_filter(filter_name):
        return {"message": f"Successfully activated filter '{filter_name}'"}
    else:
        raise HTTPException(status_code=404, detail=f"Filter '{filter_name}' not found")

class FilterCreate(BaseModel):
    name: str
    conditions: List[dict]
    enabled: bool = True
    logic: str = "and"

@app.post("/api/filters/add")
async def add_filter(filter_data: FilterCreate):
    """添加新的筛选器"""
    try:
        task_filter.add_filter(
            filter_data.name, 
            filter_data.conditions, 
            filter_data.enabled, 
            filter_data.logic
        )
        return {"message": f"Successfully added filter '{filter_data.name}'"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/filters/{name}")
async def update_filter(
    name: str,
    conditions: Optional[List[dict]] = None,
    enabled: Optional[bool] = None,
    logic: Optional[str] = None
):
    """更新现有筛选器"""
    try:
        task_filter.update_filter(name, conditions, enabled, logic)
        return {"message": f"Successfully updated filter '{name}'"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/filters/{name}")
async def remove_filter(name: str):
    """删除筛选器"""
    try:
        task_filter.remove_filter(name)
        return {"message": f"Successfully removed filter '{name}'"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)