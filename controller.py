"""
controller.py
Controller：增加 Cookie 过滤调试，打印过滤前后的数据。
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

        self.browser.set_domain_visit_callback(self._on_domain_visited)
        self.open_browser("about:blank")

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
        if not self.browser.is_running():
            return
        fingerprint_overrides = self.fingerprint.get_injection_overrides()
        special = self.fingerprint.get_special_injection_data()
        script = self.injector.build_fingerprint_script(fingerprint_overrides, special)
        self._safe_call(self.browser.inject_on_new_document, script)

    # ---------- 浏览器生命周期 ----------
    def open_browser(self, url="about:blank"):
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
        self._apply_injection()
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
    def get_storage_domains(self):
        return self.storage.get_all_domains()

    # Cookie（本地过滤）
    def get_cookies_for_domain(self, domain: str) -> dict:
        if not self.browser.is_running():
            return {}
        all_cookies = self._safe_call(self.browser.get_all_cookies) or []
        print(f"[Controller] 过滤前 Cookie 总数: {len(all_cookies)}")
        result = {}
        for c in all_cookies:
            cookie_domain = c.get("domain", "").lstrip(".")
            # 调试打印每个 Cookie 的域匹配情况
            print(f"  检查 Cookie: domain={cookie_domain}, name={c['name']}, target={domain}")
            if cookie_domain == domain or cookie_domain.endswith("." + domain) or domain.endswith(cookie_domain):
                result[c["name"]] = c["value"]
                print(f"    -> 匹配")
        print(f"[Controller] 过滤后 Cookie 数量: {len(result)}")
        return result

    def set_cookie(self, domain: str, name: str, value: str):
        self._safe_call(self.browser.set_cookie, name, value, domain)
        self.ui.log(f"Cookie [{domain}] {name} = {value}")

    def delete_cookie(self, domain: str, name: str):
        self._safe_call(self.browser.delete_cookies, name, domain)

    def clear_cookies(self, domain: str):
        cookies = self.get_cookies_for_domain(domain)
        for name in cookies:
            self._safe_call(self.browser.delete_cookies, name, domain)

    # LocalStorage
    def get_local_storage_for_domain(self, domain: str) -> dict:
        if not self.browser.is_running():
            return {}
        origin = f"https://{domain}"
        return self._safe_call(self.browser.get_all_local_storage, origin) or {}

    def set_local_storage_item(self, domain: str, key: str, value: str):
        origin = f"https://{domain}"
        self._safe_call(self.browser.set_local_storage_item, origin, key, value)

    def delete_local_storage_item(self, domain: str, key: str):
        origin = f"https://{domain}"
        self._safe_call(self.browser.remove_local_storage_item, origin, key)

    def clear_local_storage(self, domain: str):
        origin = f"https://{domain}"
        self._safe_call(self.browser.clear_local_storage, origin)

    # ---------- 域名自动记录 ----------
    def _on_domain_visited(self, domain: str):
        self.storage.add_domain(domain)
        self.ui.log(f"域名已记录: {domain}")

    # ---------- Fingerprint ----------
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
        if self.browser.is_running():
            self._apply_injection()
            self.ui.log("指纹配置已重新注入")

    def shutdown(self):
        pass
