#!/usr/bin/env python3
"""
自动化测试登录功能
使用playwright进行浏览器自动化测试
"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def test_login():
    """测试登录流程"""
    async with async_playwright() as p:
        # 启动浏览器（headless=True无界面模式，适合服务器环境）
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("🔍 步骤1: 访问前端页面 http://10.242.94.9:3000")
            await page.goto("http://10.242.94.9:3000", wait_until="networkidle")
            await asyncio.sleep(2)

            # 截图
            await page.screenshot(path="/tmp/step1_homepage.png")
            print("   ✅ 页面加载成功，截图保存到 /tmp/step1_homepage.png")

            print("\n🔍 步骤2: 检查登录按钮是否存在")
            login_button = await page.query_selector("button:has-text('登录')")
            if not login_button:
                print("   ❌ 未找到登录按钮")
                # 尝试查找其他可能的登录元素
                all_buttons = await page.query_selector_all("button")
                print(f"   页面上共有 {len(all_buttons)} 个按钮")
                for i, btn in enumerate(all_buttons[:5]):
                    text = await btn.inner_text()
                    print(f"   按钮{i+1}: {text}")
                return False

            print("   ✅ 找到登录按钮")

            print("\n🔍 步骤3: 点击登录按钮")
            # 等待导航
            async with page.expect_navigation(timeout=10000):
                await login_button.click()

            await asyncio.sleep(2)
            current_url = page.url
            await page.screenshot(path="/tmp/step3_after_click.png")
            print(f"   ✅ 点击后跳转到: {current_url}")
            print("   ✅ 截图保存到 /tmp/step3_after_click.png")

            print("\n🔍 步骤4: 验证是否跳转到Identity Hub")
            if "10.242.94.9:9000" in current_url:
                print("   ✅ 成功跳转到Identity Hub登录页面")
                print(f"   完整URL: {current_url}")

                # 检查登录表单
                username_input = await page.query_selector("input[name='username'], input[type='text']")
                password_input = await page.query_selector("input[name='password'], input[type='password']")

                if username_input and password_input:
                    print("   ✅ Identity Hub登录表单加载正常")
                    print("   - 找到用户名输入框")
                    print("   - 找到密码输入框")
                else:
                    print("   ⚠️  未找到完整的登录表单")

                return True
            else:
                print(f"   ❌ 未跳转到Identity Hub，当前URL: {current_url}")
                return False

        except Exception as e:
            print(f"\n❌ 测试过程中出错: {e}")
            await page.screenshot(path="/tmp/error.png")
            print("   错误截图保存到 /tmp/error.png")
            return False
        finally:
            print("\n⏳ 等待5秒以便查看...")
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 开始测试登录功能")
    print("=" * 60)

    result = asyncio.run(test_login())

    print("\n" + "=" * 60)
    if result:
        print("✅ 测试通过：登录跳转功能正常")
        sys.exit(0)
    else:
        print("❌ 测试失败：登录跳转未按预期工作")
        sys.exit(1)
    print("=" * 60)
