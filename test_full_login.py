#!/usr/bin/env python3
"""
完整登录流程测试（包括飞书扫码）
"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def test_full_login():
    """测试完整登录流程（包括飞书扫码）"""
    async with async_playwright() as p:
        # 启动浏览器（headless=True无界面模式）
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("🔍 步骤1: 访问前端页面 http://10.242.94.9:3000")
            await page.goto("http://10.242.94.9:3000", wait_until="networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path="/tmp/test_step1_homepage.png")
            print("   ✅ 页面加载成功")

            print("\n🔍 步骤2: 点击登录按钮")
            login_button = await page.query_selector("button:has-text('登录')")
            if not login_button:
                print("   ❌ 未找到登录按钮")
                return False

            await login_button.click()
            await asyncio.sleep(3)
            await page.screenshot(path="/tmp/test_step2_identity_hub.png")
            current_url = page.url
            print(f"   ✅ 跳转到: {current_url}")

            if "10.242.94.9:9000" not in current_url:
                print(f"   ❌ 未正确跳转到Identity Hub")
                return False

            print("\n🔍 步骤3: 点击'使用飞书扫码登录'链接")
            # 等待飞书登录链接（<a>标签，不是<button>）
            feishu_link = await page.wait_for_selector("a.login-btn, a:has-text('使用飞书扫码登录')", timeout=10000)
            await feishu_link.click()
            await asyncio.sleep(3)
            await page.screenshot(path="/tmp/test_step3_feishu_qrcode.png")
            print("   ✅ 飞书二维码页面已加载")
            print(f"   当前URL: {page.url}")

            # 检查是否有二维码或iframe
            has_qrcode = await page.query_selector("iframe, img[alt*='二维码'], canvas, [class*='qrcode']")
            if has_qrcode:
                print("   ✅ 检测到二维码元素")
            else:
                print("   ⚠️  未检测到明显的二维码元素（可能在iframe内）")

            print("\n⏸️  等待飞书扫码授权（60秒超时）...")
            print("   请使用飞书App扫描二维码并授权")

            # 监听URL变化，等待回调
            try:
                # 等待跳转回前端（最多60秒）
                await page.wait_for_url("http://10.242.94.9:3000/**", timeout=60000)
                await asyncio.sleep(3)
                await page.screenshot(path="/tmp/test_step4_callback_success.png")

                final_url = page.url
                print(f"\n✅ 步骤4: 授权成功，已跳转回: {final_url}")

                # 检查是否显示用户名和登出按钮
                user_name_elem = await page.query_selector("span.user-name")
                logout_button = await page.query_selector("button:has-text('登出')")

                if user_name_elem and logout_button:
                    user_name = await user_name_elem.inner_text()
                    print(f"   ✅ 登录成功！当前用户: {user_name}")
                    print("   ✅ 检测到登出按钮")
                    return True
                else:
                    print("   ⚠️  未检测到用户名或登出按钮")
                    # 检查是否有登录按钮（说明未登录）
                    login_btn = await page.query_selector("button:has-text('登录')")
                    if login_btn:
                        print("   ❌ 仍显示登录按钮，登录未成功")
                        return False
                    return True

            except Exception as timeout_error:
                print(f"\n⏱️  等待超时: {timeout_error}")
                print("   请确保在60秒内完成飞书扫码授权")
                await page.screenshot(path="/tmp/test_timeout.png")
                return False

        except Exception as e:
            print(f"\n❌ 测试过程中出错: {e}")
            await page.screenshot(path="/tmp/test_error.png")
            import traceback
            traceback.print_exc()
            return False
        finally:
            print("\n⏳ 等待5秒后关闭浏览器...")
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 完整登录流程测试（包括飞书扫码）")
    print("=" * 70)
    print("\n⚠️  注意：此测试需要手动操作")
    print("   1. 测试将打开飞书二维码页面")
    print("   2. 请在60秒内使用飞书App扫码授权")
    print("   3. 测试将自动检测登录结果\n")

    result = asyncio.run(test_full_login())

    print("\n" + "=" * 70)
    if result:
        print("✅ 测试通过：完整登录流程正常")
        sys.exit(0)
    else:
        print("❌ 测试失败：登录流程有问题")
        sys.exit(1)
    print("=" * 70)
