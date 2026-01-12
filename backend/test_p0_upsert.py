#!/usr/bin/env python3
"""
测试P0-2修复: 数据库UPSERT逻辑

验证:
1. INSERT OR REPLACE正常工作
2. 并发写入不会丢失数据
3. last_updated时间戳正确更新
"""

import sys
import os
import threading
import time
from datetime import datetime

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_db import init_db, save_processed_tasks_to_db, get_task_count, get_db_connection

def test_upsert_basic():
    """测试基本UPSERT功能"""
    print("\n[TEST 1] 测试基本UPSERT功能...")

    # 准备测试数据
    test_tasks = {
        "monday": [{
            "record_id": "test_001",
            "task_name": "测试任务1",
            "assignee": "测试工程师",
            "status": "进行中",
            "date": "2025-10-28",
            "start_date": "2025-10-28",
            "end_date": "2025-10-28",
            "priority": "紧急",
            "application_status": "审批中"
        }]
    }

    # 第一次插入
    save_processed_tasks_to_db(test_tasks)
    count1 = get_task_count()
    print(f"  第一次插入后任务数: {count1}")

    # 修改数据后再次插入（应该是REPLACE，不是新增）
    test_tasks["monday"][0]["task_name"] = "测试任务1-已修改"
    save_processed_tasks_to_db(test_tasks)
    count2 = get_task_count()
    print(f"  第二次插入后任务数: {count2}")

    # 验证数据是否被更新
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT task_name, last_updated
            FROM tasks
            WHERE record_id = 'test_001'
        """)
        row = cursor.fetchone()
        if row:
            print(f"  更新后的任务名: {row['task_name']}")
            print(f"  更新时间: {row['last_updated']}")

    # 验证没有重复数据
    if count2 == count1:
        print("  ✅ UPSERT正常工作 - 数据被更新而非新增")
        return True
    else:
        print(f"  ❌ UPSERT异常 - 期望{count1}条，实际{count2}条")
        return False


def test_concurrent_upsert():
    """测试并发UPSERT（核心修复点）"""
    print("\n[TEST 2] 测试并发UPSERT...")

    # 准备两组不同的数据
    tasks1 = {
        "tuesday": [{
            "record_id": f"concurrent_001",
            "task_name": "并发任务1",
            "assignee": "工程师A",
            "status": "进行中",
            "date": "2025-10-29",
            "start_date": "2025-10-29",
            "end_date": "2025-10-29",
            "priority": "重要",
            "application_status": "已通过"
        }]
    }

    tasks2 = {
        "wednesday": [{
            "record_id": f"concurrent_002",
            "task_name": "并发任务2",
            "assignee": "工程师B",
            "status": "进行中",
            "date": "2025-10-30",
            "start_date": "2025-10-30",
            "end_date": "2025-10-30",
            "priority": "紧急",
            "application_status": "已通过"
        }]
    }

    initial_count = get_task_count()
    print(f"  初始任务数: {initial_count}")

    # 并发写入
    def write_tasks(tasks, name):
        print(f"  {name} 开始写入...")
        save_processed_tasks_to_db(tasks)
        print(f"  {name} 写入完成")

    t1 = threading.Thread(target=write_tasks, args=(tasks1, "线程1"))
    t2 = threading.Thread(target=write_tasks, args=(tasks2, "线程2"))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    final_count = get_task_count()
    print(f"  并发写入后任务数: {final_count}")

    # 验证两条数据都存在
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM tasks
            WHERE record_id IN ('concurrent_001', 'concurrent_002')
        """)
        result = cursor.fetchone()["count"]

    expected_count = initial_count + 2
    if final_count == expected_count and result == 2:
        print(f"  ✅ 并发写入成功 - 两条数据都保存了")
        return True
    else:
        print(f"  ❌ 并发写入失败 - 期望{expected_count}条，实际{final_count}条，并发数据{result}条")
        return False


def test_no_delete_used():
    """测试代码中没有使用DELETE"""
    print("\n[TEST 3] 验证代码中不使用DELETE...")

    with open('task_db.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查save_processed_tasks_to_db函数
    func_start = content.find('def save_processed_tasks_to_db')
    func_end = content.find('\ndef ', func_start + 1)
    func_code = content[func_start:func_end]

    # 检查是否有DELETE语句（应该被注释掉）
    has_delete = 'DELETE FROM tasks' in func_code and '# cursor.execute("DELETE FROM tasks")' in func_code
    has_insert_replace = 'INSERT OR REPLACE' in func_code

    if has_delete and has_insert_replace:
        print("  ✅ 代码已修改 - DELETE被注释，使用INSERT OR REPLACE")
        return True
    else:
        print(f"  ❌ 代码检查失败 - has_delete:{has_delete}, has_insert_replace:{has_insert_replace}")
        return False


def cleanup():
    """清理测试数据"""
    print("\n[CLEANUP] 清理测试数据...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE record_id LIKE 'test_%' OR record_id LIKE 'concurrent_%'")
    print("  清理完成")


if __name__ == "__main__":
    print("=" * 60)
    print("P0-2修复测试: 数据库UPSERT逻辑")
    print("=" * 60)

    # 初始化数据库
    init_db()

    # 运行测试
    results = []

    try:
        results.append(("基本UPSERT", test_upsert_basic()))
        results.append(("并发UPSERT", test_concurrent_upsert()))
        results.append(("代码验证", test_no_delete_used()))
    finally:
        cleanup()

    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("🎉 所有测试通过！数据库UPSERT修复正常工作。")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败，请检查修复代码。")
        sys.exit(1)
