"""
任务查询路由

提供任务数据的各种查询接口
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from models.schemas import TaskGroup, TaskListResponse, StatsResponse, TaskItem
from task_db import get_tasks_from_db, get_db_connection, get_week_range
from task_filter import task_filter
from auth import verify_readonly_api_key
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"]
)


@router.get("", response_model=TaskGroup)
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


@router.get(
    "/by-engineer",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)]
)
async def get_tasks_by_engineer(
    engineer: str = Query(..., description="工程师姓名"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
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


@router.get(
    "/by-date",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)]
)
async def get_tasks_by_date(
    date: str = Query(..., description="日期 (YYYY-MM-DD)")
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


@router.get(
    "/stats",
    response_model=StatsResponse,
    dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)]
)
async def get_task_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
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


@router.get(
    "/search",
    response_model=TaskListResponse,
    dependencies=[Depends(verify_readonly_api_key), Depends(check_rate_limit)]
)
async def search_tasks(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(100, description="最大返回数量")
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
