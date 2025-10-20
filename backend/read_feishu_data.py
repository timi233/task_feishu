import requests
import time
from typing import Dict, List, Any, Optional

class FeishuBitableReader:
    def __init__(self, app_id: str, app_secret: str, timeout: int = 15):
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        self.access_token = None
        self.token_expire_time = 0

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        # 检查缓存的 token 是否 still有效 (提前60秒过期)
        if self.access_token and self.token_expire_time > time.time() + 60:
            print("Using cached tenant_access_token")
            return self.access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                self.token_expire_time = time.time() + result["expire"]
                print(f"[SUCCESS] Successfully obtained tenant_access_token, expires at {time.ctime(self.token_expire_time)}")
                return self.access_token
            else:
                print(f"[ERROR] Failed to get tenant_access_token: {result}")
                return None

        except Exception as e:
            print(f"[ERROR] Exception while getting tenant_access_token: {e}")
            return None

    def get_records(self, app_token: str, table_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """获取多维表格中的所有记录"""
        token = self._get_tenant_access_token()
        if not token:
            print("[ERROR] Failed to get access token, cannot fetch records")
            return []

        records = []
        page_token = None
        has_more = True

        while has_more:
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
                
            headers = {
                "Authorization": f"Bearer {token}"
            }

            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    items = result.get("data", {}).get("items", [])
                    records.extend(items)
                    print(f"[INFO] Fetched {len(items)} records, total so far: {len(records)}")
                    
                    # 检查是否还有更多数据
                    page_token = result.get("data", {}).get("page_token")
                    has_more = result.get("data", {}).get("has_more", False)
                else:
                    print(f"[ERROR] Failed to fetch records: {result}")
                    break

            except Exception as e:
                print(f"[ERROR] Exception while fetching records: {e}")
                break
                
        print(f"[SUCCESS] Finished fetching all records. Total: {len(records)}")
        return records

if __name__ == "__main__":
    import os
    # 从环境变量读取飞书应用信息和多维表格信息
    CONFIG = {
        "app_id": os.getenv("FEISHU_APP_ID"),
        "app_secret": os.getenv("FEISHU_APP_SECRET"),
        "app_token": os.getenv("FEISHU_APP_TOKEN"),
        "table_id": os.getenv("FEISHU_TABLE_ID")
    }

    reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
    
    print("开始从飞书多维表格获取数据...")
    records = reader.get_records(CONFIG["app_token"], CONFIG["table_id"])
    
    if records:
        print(f"\n成功获取到 {len(records)} 条记录:")
        # 打印前几条记录作为示例
        for i, record in enumerate(records[:3]):
            print(f"\n--- Record {i+1} ---")
            print(f"Record ID: {record.get('record_id')}")
            print(f"Fields: {record.get('fields', {})}")
        if len(records) > 3:
            print(f"\n... and {len(records) - 3} more records.")
    else:
        print("\n未能获取到任何记录。")
