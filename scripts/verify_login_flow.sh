#!/bin/bash
# 验证完整的登录流程

echo "================================"
echo "验证登录流程"
echo "================================"
echo ""

echo "1️⃣ 测试前端登录按钮URL生成..."
curl -s http://10.242.94.9:3000 | grep -o 'http://10.242.94.9:8081/auth/login[^"]*' | head -1
echo ""

echo "2️⃣ 访问后端登录端点（模拟点击登录按钮）..."
REDIRECT=$(curl -s -I "http://10.242.94.9:8081/auth/login?return_url=%2F" | grep -i "location:" | cut -d' ' -f2 | tr -d '\r')
echo "   重定向到: $REDIRECT"
echo ""

echo "3️⃣ 检查是否包含OAuth参数..."
if [[ "$REDIRECT" == *"oauth/authorize"* ]]; then
    echo "   ✅ 包含 oauth/authorize"
else
    echo "   ❌ 未包含 oauth/authorize"
fi

if [[ "$REDIRECT" == *"client_id"* ]]; then
    echo "   ✅ 包含 client_id"
else
    echo "   ❌ 未包含 client_id"
fi

if [[ "$REDIRECT" == *"redirect_uri"* ]]; then
    echo "   ✅ 包含 redirect_uri"
else
    echo "   ❌ 未包含 redirect_uri"
fi
echo ""

echo "4️⃣ 访问OAuth授权端点（模拟浏览器自动跳转）..."
OAUTH_URL=$(echo "$REDIRECT" | sed 's|http://[^/]*||')
LOGIN_REDIRECT=$(curl -s -I -H "Host: 10.242.94.9:9000" "http://10.242.94.9:9000${OAUTH_URL}" | grep -i "location:" | cut -d' ' -f2 | tr -d '\r')
echo "   重定向到: $LOGIN_REDIRECT"
echo ""

echo "5️⃣ 检查登录页面是否包含next参数..."
if [[ "$LOGIN_REDIRECT" == *"/login?next="* ]]; then
    echo "   ✅ 登录URL包含next参数（正确）"
    echo ""
    echo "✅ 流程验证通过！请按以下步骤操作："
    echo ""
    echo "   1. 浏览器访问: http://10.242.94.9:3000"
    echo "   2. 点击'登录'按钮（不要直接访问Identity Hub）"
    echo "   3. 在Identity Hub页面点击'📱 使用飞书扫码登录'"
    echo "   4. 飞书扫码授权"
    echo "   5. 应该自动跳转回 http://10.242.94.9:3000 并显示用户名"
else
    echo "   ❌ 登录URL缺少next参数"
    echo "   LOGIN_REDIRECT=$LOGIN_REDIRECT"
fi
echo ""
echo "================================"
