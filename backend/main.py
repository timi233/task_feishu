# 后端服务主入口

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware # 添加CORS中间件导入
from fastapi.staticfiles import StaticFiles # 添加静态文件服务导入
import uvicorn
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os
import logging
import time
# 从本地数据库模块导入
from task_db import init_db, get_tasks_from_db, get_week_range, get_db_connection, get_task_count
# 导入筛选模块
from task_filter import task_filter
# 导入认证和限流模块
from auth import verify_readonly_api_key
from rate_limit import check_rate_limit

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 添加CORS中间件，从环境变量读取允许的来源
# ALLOWED_ORIGINS 格式: "http://localhost:3000,http://localhost:8080"
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

class TaskListResponse(BaseModel):
    """任务列表响应(扁平结构,供其他系统使用)"""
    total: int
    tasks: List[TaskItem]

class EngineerStatsItem(BaseModel):
    """工程师统计信息"""
    engineer: str
    total_tasks: int
    very_urgent: int
    urgent: int
    important: int

class StatsResponse(BaseModel):
    """统计响应"""
    date_range: dict
    by_engineer: List[EngineerStatsItem]
    by_priority: dict


# ===== 中间件 =====

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有API请求(用于审计)"""
    start_time = time.time()

    # 获取API Key(用于审计)
    api_key = request.headers.get("X-API-Key", "none")
    masked_key = api_key[:8] + "***" if len(api_key) > 8 else "***"

    response = await call_next(request)

    process_time = time.time() - start_time

    logger.info(
        "API Request: method=%s path=%s api_key=%s status=%d duration=%.3fs",
        request.method,
        request.url.path,
        masked_key,
        response.status_code,
        process_time
    )

    return response


# ===== 端点定义 =====

@app.get("/")
async def read_root():
    return {"message": "派工系统后端服务"}


@app.get("/health")
async def health_check():
    """
    健康检查端点

    供监控系统调用,验证:
    1. 数据库连接正常
    2. 数据量在合理范围

    Returns:
        dict: 包含status, database, task_count, timestamp
    """
    try:
        task_count = get_task_count()

        return {
            "status": "healthy",
            "database": "connected",
            "task_count": task_count,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

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
                start_date, end_date = get_week_range(week_start="sunday")
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


# ===== 新增API端点(供其他系统调用) =====

@app.get(
    "/api/tasks/by-engineer",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key)]
)
async def get_tasks_by_engineer(
    engineer: str = Query(..., description="工程师姓名"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    api_key: str = Depends(verify_readonly_api_key)
):
    """
    按工程师查询任务

    用例:
    - 其他系统查询"张三"本周的所有任务
    - HR系统统计工程师工作量

    示例:
    GET /api/tasks/by-engineer?engineer=张三&start_date=2025-10-13&end_date=2025-10-19
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: by-engineer=%s, start=%s, end=%s", engineer, start_date, end_date)

    try:
        # 如果未提供日期范围,使用本周
        if not start_date or not end_date:
            start_date, end_date = get_week_range(week_start="sunday")

        # 从数据库查询
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority,
                       application_status, date, start_date, end_date, weekday
                FROM tasks
                WHERE assignee = ? AND date BETWEEN ? AND ?
                ORDER BY date
            """, (engineer, start_date, end_date))

            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]

        return TaskListResponse(total=len(tasks), tasks=tasks)

    except Exception as e:
        logger.exception("Failed to query tasks by engineer")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/tasks/by-date",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key)]
)
async def get_tasks_by_date(
    date: str = Query(..., description="日期 (YYYY-MM-DD)"),
    api_key: str = Depends(verify_readonly_api_key)
):
    """
    按单日查询所有任务

    用例:
    - 日报系统获取2025-10-15当天的所有派工
    - 考勤系统核对某天的工作安排

    示例:
    GET /api/tasks/by-date?date=2025-10-15
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: by-date=%s", date)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority,
                       application_status, date, start_date, end_date, weekday
                FROM tasks
                WHERE date = ?
                ORDER BY assignee, priority DESC
            """, (date,))

            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]

        return TaskListResponse(total=len(tasks), tasks=tasks)

    except Exception as e:
        logger.exception("Failed to query tasks by date")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/tasks/stats",
    response_model=StatsResponse,
    dependencies=[Depends(verify_readonly_api_key)]
)
async def get_task_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    api_key: str = Depends(verify_readonly_api_key)
):
    """
    获取任务统计数据

    用例:
    - 管理仪表盘展示工作量分布
    - 报表系统生成周报

    返回:
    - 按工程师统计(总任务数,各优先级数量)
    - 按优先级统计

    示例:
    GET /api/tasks/stats?start_date=2025-10-13&end_date=2025-10-19
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: stats, start=%s, end=%s", start_date, end_date)

    try:
        if not start_date or not end_date:
            start_date, end_date = get_week_range(week_start="sunday")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 按工程师统计
            cursor.execute("""
                SELECT
                    assignee as engineer,
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN priority='非常紧急' THEN 1 ELSE 0 END) as very_urgent,
                    SUM(CASE WHEN priority='紧急' THEN 1 ELSE 0 END) as urgent,
                    SUM(CASE WHEN priority='重要' THEN 1 ELSE 0 END) as important
                FROM tasks
                WHERE date BETWEEN ? AND ?
                GROUP BY assignee
                ORDER BY total_tasks DESC
            """, (start_date, end_date))

            by_engineer = [dict(row) for row in cursor.fetchall()]

            # 按优先级统计
            cursor.execute("""
                SELECT
                    priority,
                    COUNT(*) as count
                FROM tasks
                WHERE date BETWEEN ? AND ?
                GROUP BY priority
            """, (start_date, end_date))

            by_priority = {row["priority"]: row["count"] for row in cursor.fetchall()}

        return StatsResponse(
            date_range={"start": start_date, "end": end_date},
            by_engineer=by_engineer,
            by_priority=by_priority
        )

    except Exception as e:
        logger.exception("Failed to get task stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/tasks/search",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key)]
)
async def search_tasks(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(100, description="最大返回数量"),
    api_key: str = Depends(verify_readonly_api_key)
):
    """
    全文搜索任务

    用例:
    - 搜索包含"XX公司"的所有任务
    - 搜索"网络故障"相关派工

    搜索字段: task_name, assignee

    示例:
    GET /api/tasks/search?keyword=阿里巴巴&limit=50
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: search=%s, limit=%d", keyword, limit)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_id, task_name, assignee, status, priority,
                       application_status, date, start_date, end_date, weekday
                FROM tasks
                WHERE task_name LIKE ? OR assignee LIKE ?
                ORDER BY date DESC
                LIMIT ?
            """, (f"%{keyword}%", f"%{keyword}%", limit))

            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]

        return TaskListResponse(total=len(tasks), tasks=tasks)

    except Exception as e:
        logger.exception("Failed to search tasks")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/engineers",
    dependencies=[Depends(verify_readonly_api_key)]
)
async def get_engineers(api_key: str = Depends(verify_readonly_api_key)):
    """
    获取所有工程师列表

    用例:
    - 其他系统需要工程师选择器
    - 统计系统获取人员名单

    示例:
    GET /api/engineers
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: get engineers")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT assignee
                FROM tasks
                WHERE assignee IS NOT NULL AND assignee != ''
                ORDER BY assignee
            """)

            engineers = [row["assignee"] for row in cursor.fetchall()]

        return {"total": len(engineers), "engineers": engineers}

    except Exception as e:
        logger.exception("Failed to get engineers")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/sync",
    dependencies=[Depends(verify_readonly_api_key)]
)
async def sync_from_feishu(api_key: str = Depends(verify_readonly_api_key)):
    """
    手动触发从飞书同步数据到数据库

    用例:
    - 用户在前端点击"同步数据"按钮
    - 管理员需要立即更新数据

    示例:
    POST /api/sync
    Header: X-API-Key: your-readonly-key
    """
    logger.info("API request: manual sync triggered")

    try:
        from feishu_reader import FeishuBitableReader
        from process_feishu_data import process_feishu_records
        from task_db import save_processed_tasks_to_db

        # 从环境变量读取飞书配置
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        app_token = os.getenv("FEISHU_APP_TOKEN")
        table_id = os.getenv("FEISHU_TABLE_ID")

        if not all([app_id, app_secret, app_token, table_id]):
            raise HTTPException(
                status_code=500,
                detail="Feishu configuration incomplete. Check environment variables."
            )

        # 1. 从飞书获取数据
        logger.info("Fetching data from Feishu...")
        reader = FeishuBitableReader(app_id, app_secret)
        raw_records = reader.get_records(app_token, table_id)

        if not raw_records:
            return {
                "success": False,
                "message": "No data fetched from Feishu",
                "records_synced": 0
            }

        # 2. 处理数据
        logger.info(f"Processing {len(raw_records)} records...")
        processed_tasks = process_feishu_records(raw_records)

        # 3. 保存到数据库
        logger.info("Saving to database...")
        save_processed_tasks_to_db(processed_tasks)

        logger.info(f"Sync completed: {len(processed_tasks)} tasks synced")

        return {
            "success": True,
            "message": "Data synced successfully",
            "records_synced": len(processed_tasks),
            "timestamp": datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception("Failed to sync data from Feishu")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)