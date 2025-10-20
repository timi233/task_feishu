import time
import os
import schedule
from read_feishu_data import FeishuBitableReader
from process_feishu_data import process_feishu_records
from task_db import init_db, save_processed_tasks_to_db

# --- 配置部分 ---
# 从环境变量读取飞书应用信息和多维表格信息
CONFIG = {
    "app_id": os.getenv("FEISHU_APP_ID"),
    "app_secret": os.getenv("FEISHU_APP_SECRET"),
    "app_token": os.getenv("FEISHU_APP_TOKEN"),
    "table_id": os.getenv("FEISHU_TABLE_ID")
}
# 同步间隔（分钟）
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
# --- 配置结束 ---


def sync_feishu_data_to_db():
    """从飞书同步数据到数据库"""
    print(f"\n[SYNC] Starting data synchronization at {time.ctime()}")
    
    try:
        # 1. 初始化飞书读取器
        reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
        
        # 2. 从飞书获取原始数据
        print("[SYNC] Fetching raw data from Feishu...")
        raw_records = reader.get_records(CONFIG["app_token"], CONFIG["table_id"])
        
        if not raw_records:
            print("[SYNC] No raw data fetched from Feishu. Skipping sync.")
            return

        # 3. 处理原始数据
        print("[SYNC] Processing fetched data...")
        processed_tasks = process_feishu_records(raw_records)
        
        # 4. 保存处理后的数据到数据库
        print("[SYNC] Saving processed data to database...")
        save_processed_tasks_to_db(processed_tasks)
        
        print("[SYNC] Data synchronization completed successfully.")
        
    except Exception as e:
        print(f"[SYNC ERROR] Data synchronization failed: {e}")


if __name__ == "__main__":
    # 初始化数据库
    init_db()
    
    # 立即运行一次同步
    sync_feishu_data_to_db()
    
    # 安排定时任务
    schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_feishu_data_to_db)
    print(f"[SCHEDULER] Scheduled data sync every {SYNC_INTERVAL_MINUTES} minutes.")
    
    # 保持脚本运行
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Scheduler stopped by user.")
