"""
test.py — 验证 Fingerprint 注入脚本是否正确
用法：先正常启动 BrowserLab 或手动启动 chromium --remote-debugging-port=9222，然后运行本脚本。
"""

import time
import sys
sys.path.insert(0, '.')
from browser import Browser
from fingerprint import Fingerprint
from injector import Injector

def test():
    # 1. 连接到已运行的 Chromium（假设端口 9222）
    print("连接浏览器...")
    b = Browser()
    # 如果浏览器没启动，启动它
    if not b.is_running():
        print("未检测到浏览器，尝试启动...")
        b.open("about:blank")
        time.sleep(2)
    else:
        print("浏览器已运行")
        b.sync_active_tab()  # 确保 CDP 连接正常

    # 2. 创建一个 Fingerprint 实例并修改一个简单属性
    fp = Fingerprint()
    fp.set_property("navigator.platform", "TestPlatformXYZ")
    print(f"已设置 navigator.platform = TestPlatformXYZ")

    # 3. 生成注入脚本
    overrides = fp.get_injection_overrides()
    special = fp.get_special_injection_data()
    script = Injector.build_fingerprint_script(overrides, special)

    # 打印生成的脚本（便于检查）
    print("=" * 60)
    print("生成的注入脚本：")
    print(script)
    print("=" * 60)

    # 4. 通过 CDP 注入
    try:
        b.inject_on_new_document(script)
        print("✅ 注入命令已发送")
    except Exception as e:
        print(f"❌ 注入失败: {e}")
        return

    # 5. 打开一个测试页面（about:blank 可以，但我们需要执行 JS，所以用空白页）
    # 为了简单，直接在当前空白页执行 JS，但注入脚本只对后续页面生效，
    # 所以这里我们导航到一个新页面（例如 about:blank 再加载一次）。
    b.execute_js("window.location.href = 'about:blank';")
    time.sleep(0.5)  # 等待加载

    # 6. 读取 navigator.platform
    result = b.execute_js("navigator.platform")
    print(f"navigator.platform 实际值: {result}")

    if result == "TestPlatformXYZ":
        print("🎉 注入成功！")
    else:
        print("💥 注入失败或未覆盖该属性。")

    # 7. 检查标志
    flag = b.execute_js("window.__bl_fingerprint_installed")
    print(f"__bl_fingerprint_installed: {flag}")

if __name__ == "__main__":
    test()
