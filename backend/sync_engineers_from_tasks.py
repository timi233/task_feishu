"""从任务数据中同步工程师到engineers表

当无法从飞书通讯录或Identity Hub同步完整用户列表时，
可以从任务数据的assignee字段中提取工程师信息。

使用方式:
    python sync_engineers_from_tasks.py

日期: 2025-11-03
"""

import logging
import sys
import os
from typing import Set, Dict, Any

sys.path.insert(0, os.path.dirname(__file__))

from task_db import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_engineer_names_from_tasks() -> Set[str]:
    """从tasks表中提取所有工程师姓名

    Returns:
        Set[str]: 工程师姓名集合
    """
    engineer_names = set()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 从assignee字段提取
        cursor.execute("""
            SELECT DISTINCT assignee
            FROM tasks
            WHERE assignee IS NOT NULL AND assignee != ''
        """)

        assignees = cursor.fetchall()

        for row in assignees:
            assignee = row[0]
            # 处理多人派工的情况（逗号分隔）
            if ',' in assignee:
                names = [name.strip() for name in assignee.split(',')]
                engineer_names.update(names)
            else:
                engineer_names.add(assignee.strip())

        # 从creator_name字段提取
        cursor.execute("""
            SELECT DISTINCT creator_name
            FROM tasks
            WHERE creator_name IS NOT NULL AND creator_name != ''
        """)

        creators = cursor.fetchall()

        for row in creators:
            creator_name = row[0]
            if creator_name:
                engineer_names.add(creator_name.strip())

    return engineer_names


def sync_engineers_from_tasks() -> Dict[str, Any]:
    """从任务数据同步工程师到engineers表

    Returns:
        Dict: 同步结果统计
    """
    logger.info("开始从任务数据中提取工程师信息...")

    stats = {
        "success": False,
        "total_engineers": 0,
        "created": 0,
        "skipped": 0,
        "errors": []
    }

    try:
        # 1. 提取工程师姓名
        engineer_names = extract_engineer_names_from_tasks()
        stats["total_engineers"] = len(engineer_names)

        logger.info(f"从任务数据中提取到 {len(engineer_names)} 个工程师")

        # 2. 同步到engineers表
        with get_db_connection() as conn:
            cursor = conn.cursor()

            for name in sorted(engineer_names):
                # 使用姓名作为临时user_id（添加前缀以区分）
                temp_user_id = f"task_{name}"

                # 检查是否已存在（通过user_id或name）
                cursor.execute("""
                    SELECT user_id FROM engineers
                    WHERE user_id = ? OR name = ?
                """, (temp_user_id, name))

                exists = cursor.fetchone()

                if exists:
                    stats["skipped"] += 1
                    logger.debug(f"  跳过已存在的工程师: {name}")
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO engineers
                        (user_id, name, status, synced_at)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    """, (temp_user_id, name))

                    stats["created"] += 1
                    logger.info(f"  新增工程师: {name} (临时ID: {temp_user_id})")

            conn.commit()

        stats["success"] = True
        logger.info(f"✅ 同步完成: 新增 {stats['created']}, 跳过 {stats['skipped']}")

        return stats

    except Exception as e:
        error_msg = f"同步失败: {str(e)}"
        logger.exception(error_msg)
        stats["errors"].append(error_msg)
        return stats


if __name__ == "__main__":
    print("\n" + "="*60)
    print("从任务数据同步工程师信息")
    print("="*60 + "\n")

    # 执行同步
    result = sync_engineers_from_tasks()

    # 打印结果
    print("\n" + "="*60)
    if result["success"]:
        print("✅ 同步成功")
        print(f"  发现工程师: {result['total_engineers']}")
        print(f"  新增: {result['created']}")
        print(f"  跳过: {result['skipped']}")
    else:
        print("❌ 同步失败")
        if result["errors"]:
            print("\n错误信息:")
            for error in result["errors"]:
                print(f"  - {error}")
    print("="*60 + "\n")
