#!/bin/bash

# 添加申请状态本周筛选器的脚本

echo "Adding application status this week filter..."

# 发送POST请求添加筛选器
response=$(curl -s -X POST "http://localhost:8000/api/filters/add" \
     -H "Content-Type: application/json" \
     -d '{
           "name": "application_status_this_week",
           "conditions": [
             {
               "field": "status",
               "operator": "in",
               "value": ["已通过", "审批中"]
             },
             {
               "field": "start_date",
               "operator": "this_week"
             }
           ],
           "enabled": true,
           "logic": "and"
         }')

echo "Response: $response"

# 检查是否成功添加
if [[ $response == *"Successfully added filter"* ]]; then
    echo "Filter added successfully!"
    
    # 激活筛选器
    echo "Activating filter..."
    activate_response=$(curl -s -X POST "http://localhost:8000/api/filters/activate?filter_name=application_status_this_week")
    echo "Activation response: $activate_response"
    
    if [[ $activate_response == *"Successfully activated filter"* ]]; then
        echo "Filter activated successfully!"
    else
        echo "Failed to activate filter."
    fi
else
    echo "Failed to add filter."
fi