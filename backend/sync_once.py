from read_feishu_data import FeishuBitableReader
from process_feishu_data import process_feishu_records
from mysql_db import init_db, save_raw_feishu_records_to_db, save_processed_tasks_to_db

# --- 配置部分 ---
# 请替换为你的实际飞书应用信息和多维表格信息
CONFIG = {
    "app_id": "cli_a8e5c86826ab9013",
    "app_secret": "ObaI5gvFKKKtKZD09olblhM13kXrNFXB",
    "app_token": "ZbpqbNgpNa0IvTsXfLuc5seBnJg",  # 派工表格
    "table_id": "tblIrTdzXCFUwjti"  # 派工表格中的具体表
}
# --- 配置结束 ---


def sync_feishu_data_once():
    """从飞书同步数据到数据库 (仅运行一次)"""
    print(f"\n[SYNC] Starting one-time data synchronization...")
    
    try:
        # 1. 初始化飞书读取器
        reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
        
        # 2. 从飞书获取原始数据
        print("[SYNC] Fetching raw data from Feishu...")
        raw_records = reader.get_records(CONFIG["app_token"], CONFIG["table_id"])
        
        if not raw_records:
            print("[SYNC] No raw data fetched from Feishu. Skipping sync.")
            return False

        # 3. 保存原始数据到数据库
        print("[SYNC] Saving raw Feishu data to database...")
        save_raw_feishu_records_to_db(raw_records)
        
        # 4. 处理原始数据
        print("[SYNC] Processing fetched data...")
        processed_tasks = process_feishu_records(raw_records)
        
        # 5. 保存处理后的数据到数据库
        print("[SYNC] Saving processed data to database...")
        save_processed_tasks_to_db(processed_tasks)
        
        print("[SYNC] One-time data synchronization completed successfully.")
        return True
        
    except Exception as e:
        print(f"[SYNC ERROR] One-time data synchronization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 初始化数据库
    init_db()
    
    # 运行一次同步
    success = sync_feishu_data_once()
    
    if success:
        print("\n[SUCCESS] Data sync finished successfully.")
    else:
        print("\n[FAILURE] Data sync failed.")