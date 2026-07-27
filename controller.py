"""
controller.py
Controller 是整个项目的唯一控制中心。
"""

from browser import Browser
from ui import UI
from network import Network
from storage import Storage
from session import Session
from fingerprint import Fingerprint
from injector import Injector
from urllib.parse import urlparse


class Controller:
    def __init__(self):
        self.browser = Browser()
        self.network = Network()
        self.storage = Storage()
        self.session = Session()
        self.fingerprint = Fingerprint()
        self.injector = Injector()
        self.ui = UI(self)

    def run(self):
        self.ui.run()

    def _safe_call(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.ui.log(f"[错误] {e}")
            return None

    # ---------- 辅助 ----------
    def _get_current_domain(self):
        url = self._safe_call(self.browser.get_url)
        if url:
            parsed = urlparse(url)
            return parsed.hostname or ""
        return ""

    def _apply_injection(self):
        """生成并注入完整的预加载脚本（Storage 守卫 + Fingerprint 伪装）。"""
        if not self.browser.is_running():
            return
        domain = self._get_current_domain()
        if not domain:
            domain = "unknown"

        # Storage 配置
        allow_write = self.storage.get_write_permission()
        cookies = self.storage.get_managed_cookies(domain)
        local_storage = self.storage.get_managed_local_storage(domain)

        # Fingerprint 配置
        fingerprint_overrides = self.fingerprint.get_injection_overrides()
        special = self.fingerprint.get_special_injection_data()

        # 生成并注入脚本
        script = self.injector.build_complete_script(
            allow_write=allow_write,
            managed_cookies=cookies,
            managed_local_storage=local_storage,
            fingerprint_overrides=fingerprint_overrides,
            special=special
        )
        self._safe_call(self.browser.inject_on_new_document, script)
        self.ui.log(f"注入脚本已更新，域: {domain}")

    # ---------- 浏览器生命周期 ----------
    def open_browser(self, url="https://example.com"):
        self._safe_call(self.browser.open, url)
        if self.browser.is_running():
            self._safe_call(self.network.apply_to_browser, self.browser)
            self._apply_injection()

    def close_browser(self):
        self._safe_call(self.browser.close)

    def browser_running(self):
        return self.browser.is_running()

    # ---------- 页面控制 ----------
    def load_url(self, url):
        self._safe_call(self.browser.load_url, url)
        self._apply_injection()

    def reload(self):
        self._apply_injection()   # 先更新注入脚本，再刷新
        self._safe_call(self.browser.reload)

    def back(self):
        self._safe_call(self.browser.back)

    def forward(self):
        self._safe_call(self.browser.forward)

    def execute_js(self, script):
        result = self._safe_call(self.browser.execute_js, script)
        if result is not None:
            self.ui.log(f"JS 返回值: {result}")
        return result

    def get_title(self):
        return self._safe_call(self.browser.get_title) or ""

    def get_url(self):
        return self._safe_call(self.browser.get_url) or ""

    def new_tab(self, url="about:blank"):
        self._safe_call(self.browser.new_tab, url)
        if self.browser.is_running():
            self._safe_call(self.network.apply_to_browser, self.browser)
            self._apply_injection()

    def close_tab(self):
        self._safe_call(self.browser.close_tab)

    def get_tab_count(self) -> int:
        tabs = self._safe_call(self.browser.get_tabs)
        if tabs:
            return len([t for t in tabs if t.get("type") == "page"])
        return 0

    # ---------- 网络身份 ----------
    def set_user_agent(self, ua):
        self.network.set_user_agent(ua)
        if self.browser.is_running():
            self._safe_call(self.browser.set_user_agent, ua)
        self.ui.log(f"User-Agent 已设置为: {ua}")

    def set_header(self, key, value):
        self.network.set_header(key, value)
        if self.browser.is_running():
            self._safe_call(self.browser.set_extra_headers, self.network.get_headers())
        self.ui.log(f"请求头已设置: {key}: {value}")

    def remove_header(self, key):
        self.network.remove_header(key)
        if self.browser.is_running():
            self._safe_call(self.browser.set_extra_headers, self.network.get_headers())
        self.ui.log(f"请求头已移除: {key}")

    def clear_headers(self):
        self.network.clear_headers()
        if self.browser.is_running():
            self._safe_call(self.browser.set_extra_headers, {})
        self.ui.log("所有自定义请求头已清除。")

    # ---------- Storage 管理 ----------
    def get_storage_write_permission(self) -> bool:
        return self.storage.get_write_permission()

    def set_storage_write_permission(self, allow: bool):
        self.storage.set_write_permission(allow)
        if self.browser.is_running():
            self._apply_injection()
        self.ui.log(f"Storage 写入权限已设置为: {'允许' if allow else '禁止'}")

    def get_storage_domains(self):
        return self.storage.get_all_domains()

    def get_managed_cookies(self, domain: str):
        return self.storage.get_managed_cookies(domain)

    def set_managed_cookie(self, domain: str, name: str, value: str):
        self.storage.set_cookie(domain, name, value)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()
        self.ui.log(f"Cookie [{domain}] {name} = {value}")

    def delete_managed_cookie(self, domain: str, name: str):
        self.storage.delete_cookie(domain, name)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()

    def clear_managed_cookies(self, domain: str):
        self.storage.clear_cookies(domain)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()

    def get_managed_local_storage(self, domain: str):
        return self.storage.get_managed_local_storage(domain)

    def set_managed_local_storage_item(self, domain: str, key: str, value: str):
        self.storage.set_local_storage_item(domain, key, value)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()

    def delete_managed_local_storage_item(self, domain: str, key: str):
        self.storage.delete_local_storage_item(domain, key)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()

    def clear_managed_local_storage(self, domain: str):
        self.storage.clear_local_storage(domain)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()

    def delete_storage_domain(self, domain: str):
        self.storage.delete_domain(domain)
        if self.browser.is_running() and self._get_current_domain() == domain:
            self._apply_injection()
        self.ui.log(f"域 [{domain}] 的 Storage 数据已删除。")

    def import_current_storage(self):
        """从浏览器当前页面导入 Cookie 和 LocalStorage 到管理器中。"""
        if not self.browser.is_running():
            return
        domain = self._get_current_domain()
        if not domain:
            return
        cookies = self._safe_call(self.browser.get_cookies_via_js) or {}
        local = self._safe_call(self.browser.get_local_storage_via_js) or {}
        self.storage.import_from_browser(domain, cookies, local)
        self.ui.log(f"已从浏览器导入域 [{domain}] 的 Storage 数据")

    # ---------- Fingerprint 管理 ----------
    def get_fingerprint_properties(self) -> dict:
        return self.fingerprint.get_all_properties()

    def set_fingerprint_property(self, key: str, value):
        self.fingerprint.set_property(key, value)
        self.ui.log(f"指纹属性 {key} 已设置为 {value}")

    def apply_fingerprint_preset(self, preset_name: str) -> bool:
        success = self.fingerprint.apply_preset(preset_name)
        if success:
            self.ui.log(f"已应用身份模板: {preset_name}")
            if self.browser.is_running():
                self._apply_injection()
        return success

    def apply_fingerprint_now(self):
        """立即将当前指纹配置注入到浏览器（重新注入）"""
        if self.browser.is_running():
            self._apply_injection()
            self.ui.log("指纹配置已重新注入")

    def add_fingerprint_custom_property(self, key: str, default_value=None):
        self.fingerprint.add_custom_property(key, default_value)
        self.ui.log(f"已添加自定义指纹属性: {key}")
