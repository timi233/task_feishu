import os
import requests
import time
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            logger.debug("Using cached tenant_access_token")
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
                logger.info("Successfully obtained tenant_access_token, expires at %s", time.ctime(self.token_expire_time))
                return self.access_token
            else:
                logger.error("Failed to get tenant_access_token: %s", result)
                return None

        except Exception as e:
            logger.exception("Exception while getting tenant_access_token: %s", e)
            return None

    def get_records(self, app_token: str, table_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """获取多维表格中的所有记录"""
        token = self._get_tenant_access_token()
        if not token:
            logger.error("Failed to get access token, cannot fetch records")
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
                    logger.debug("Fetched %d records, total so far: %d", len(items), len(records))
                    
                    # 检查是否还有更多数据
                    page_token = result.get("data", {}).get("page_token")
                    has_more = result.get("data", {}).get("has_more", False)
                else:
                    logger.error("Failed to fetch records: %s", result)
                    break

            except Exception as e:
                logger.exception("Exception while fetching records: %s", e)
                break
                
        logger.info("Finished fetching all records. Total: %d", len(records))
        return records

if __name__ == "__main__":
    CONFIG = {
        "app_id": os.getenv("FEISHU_APP_ID"),
        "app_secret": os.getenv("FEISHU_APP_SECRET"),
        "app_token": os.getenv("FEISHU_APP_TOKEN"),
        "table_id": os.getenv("FEISHU_TABLE_ID")
    }

    reader = FeishuBitableReader(CONFIG["app_id"], CONFIG["app_secret"])
    
    logger.info("开始从飞书多维表格获取数据...")
    records = reader.get_records(CONFIG["app_token"], CONFIG["table_id"])
    
    if records:
        logger.info("成功获取到 %d 条记录:", len(records))
        # 打印前几条记录作为示例
        for i, record in enumerate(records[:3]):
            logger.info("--- Record %d ---", i + 1)
            logger.info("Record ID: %s", record.get('record_id'))
            logger.info("Fields: %s", record.get('fields', {}))
        if len(records) > 3:
            logger.info("... and %d more records.", len(records) - 3)
    else:
        logger.warning("未能获取到任何记录。")
