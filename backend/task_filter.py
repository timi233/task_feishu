import json
import os
from typing import Dict, Any, List, Union
from fastapi import HTTPException
from datetime import datetime, timedelta
# 导入统一的日期计算函数
from task_db import get_week_range

class TaskFilter:
    def __init__(self, config_path: str = "filter_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载筛选配置"""
        if not os.path.exists(self.config_path):
            # 创建默认配置文件
            default_config = {
                "filters": {
                    "default": {
                        "enabled": True,
                        "conditions": [
                            {
                                "field": "status",
                                "operator": "not_in",
                                "value": ["已取消", "已关闭"]
                            }
                        ]
                    }
                },
                "active_filter": "default"
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return default_config
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _evaluate_condition(self, task: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """评估单个条件"""
        field = condition["field"]
        operator = condition["operator"]
        value = condition.get("value")
        
        # 获取任务字段值
        task_value = task.get(field)
        
        # 处理空值情况
        if task_value is None:
            if operator in ["not_empty", "is_empty"]:
                return operator == "is_empty"
            return False
        
        # 根据操作符评估条件
        if operator == "equals":
            return task_value == value
        elif operator == "not_equals":
            return task_value != value
        elif operator == "contains":
            return value in str(task_value)
        elif operator == "not_contains":
            return value not in str(task_value)
        elif operator == "in":
            return task_value in value if isinstance(value, list) else False
        elif operator == "not_in":
            return task_value not in value if isinstance(value, list) else True
        elif operator == "greater_than":
            try:
                return float(task_value) > float(value)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(task_value) < float(value)
            except (ValueError, TypeError):
                return False
        elif operator == "not_empty":
            return task_value is not None and task_value != ""
        elif operator == "is_empty":
            return task_value is None or task_value == ""
        elif operator == "this_week":
            # 检查日期是否在本周（周日开始）
            return self._is_date_in_current_week(task_value)
        else:
            return False
    
    def _evaluate_conditions(self, task: Dict[str, Any], conditions: List[Dict[str, Any]], logic: str = "and") -> bool:
        """评估条件列表"""
        if not conditions:
            return True
            
        results = [self._evaluate_condition(task, cond) for cond in conditions]
        
        if logic == "and":
            return all(results)
        elif logic == "or":
            return any(results)
        else:
            return all(results)  # 默认为AND逻辑
    
    def filter_tasks(self, tasks: List[Dict[str, Any]], filter_name: str = None) -> List[Dict[str, Any]]:
        """根据配置筛选任务"""
        # 如果没有指定筛选器，使用当前激活的筛选器
        if not filter_name:
            filter_name = self.config.get("active_filter", "default")
        
        # 获取筛选器配置
        filter_config = self.config.get("filters", {}).get(filter_name)
        
        # 如果筛选器不存在或未启用，返回所有任务
        if not filter_config or not filter_config.get("enabled", False):
            return tasks
        
        # 获取条件和逻辑
        conditions = filter_config.get("conditions", [])
        logic = filter_config.get("logic", "and")  # 默认AND逻辑
        
        # 筛选任务
        filtered_tasks = [
            task for task in tasks 
            if self._evaluate_conditions(task, conditions, logic)
        ]
        
        return filtered_tasks
    
    def get_available_filters(self) -> List[str]:
        """获取所有可用的筛选器名称"""
        return list(self.config.get("filters", {}).keys())
    
    def get_active_filter(self) -> str:
        """获取当前激活的筛选器"""
        return self.config.get("active_filter", "default")
    
    def set_active_filter(self, filter_name: str) -> bool:
        """设置当前激活的筛选器"""
        if filter_name in self.config.get("filters", {}):
            self.config["active_filter"] = filter_name
            self._save_config()
            return True
        return False
    
    def add_filter(self, name: str, conditions: List[Dict[str, Any]], enabled: bool = True, logic: str = "and"):
        """添加新的筛选器"""
        if "filters" not in self.config:
            self.config["filters"] = {}
        
        self.config["filters"][name] = {
            "enabled": enabled,
            "conditions": conditions,
            "logic": logic
        }
        self._save_config()
    
    def update_filter(self, name: str, conditions: List[Dict[str, Any]] = None, enabled: bool = None, logic: str = None):
        """更新现有筛选器"""
        if name not in self.config.get("filters", {}):
            raise HTTPException(status_code=404, detail=f"Filter '{name}' not found")
        
        if conditions is not None:
            self.config["filters"][name]["conditions"] = conditions
        if enabled is not None:
            self.config["filters"][name]["enabled"] = enabled
        if logic is not None:
            self.config["filters"][name]["logic"] = logic
            
        self._save_config()
    
    def remove_filter(self, name: str):
        """删除筛选器"""
        if name in self.config.get("filters", {}):
            del self.config["filters"][name]
            # 如果删除的是当前激活的筛选器，切换到默认筛选器
            if self.config.get("active_filter") == name:
                self.config["active_filter"] = "default"
            self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def _is_date_in_current_week(self, date_str: str) -> bool:
        """检查日期是否在本周（使用统一的日期计算逻辑，周日开始）"""
        if not date_str:
            return False

        try:
            # 解析日期字符串为标准格式
            if isinstance(date_str, str):
                # 如果是时间戳格式
                if date_str.isdigit() and len(date_str) == 13:
                    # 毫秒级时间戳
                    date_obj = datetime.fromtimestamp(int(date_str) / 1000.0)
                    check_date = date_obj.strftime("%Y-%m-%d")
                elif date_str.isdigit() and len(date_str) == 10:
                    # 秒级时间戳
                    date_obj = datetime.fromtimestamp(int(date_str))
                    check_date = date_obj.strftime("%Y-%m-%d")
                else:
                    # YYYY-MM-DD 格式
                    check_date = date_str
            else:
                return False

            # 使用统一的日期计算函数获取本周范围
            start_date_str, end_date_str = get_week_range(week_start="sunday")

            # 比较日期字符串
            return start_date_str <= check_date <= end_date_str
        except Exception as e:
            print(f"[WARN] Failed to parse date {date_str}: {e}")
            return False

# 全局实例
task_filter = TaskFilter()