"""
network.py
Network 抽象层：负责管理浏览器网络身份。
包括 User-Agent、自定义 HTTP Headers、代理等。
通过 Browser 提供的方法将配置注入到浏览器。
"""

class Network:
    def __init__(self):
        self.proxy = None            # 预留：以后实现代理注入
        self.user_agent = None       # 自定义 UA 字符串
        self.headers = {}            # 自定义请求头

    # ---- User-Agent ----
    def set_user_agent(self, ua: str) -> None:
        """设置 User-Agent 字符串。"""
        self.user_agent = ua

    def get_user_agent(self) -> str | None:
        return self.user_agent

    # ---- Headers ----
    def set_header(self, key: str, value: str) -> None:
        """设置一个自定义 HTTP 请求头（会覆盖同名已有值）。"""
        self.headers[key] = value

    def remove_header(self, key: str) -> None:
        """移除一个自定义请求头。"""
        self.headers.pop(key, None)

    def clear_headers(self) -> None:
        """清空所有自定义请求头。"""
        self.headers.clear()

    def get_headers(self) -> dict:
        return dict(self.headers)

    # ---- Proxy (预留) ----
    def set_proxy(self, proxy: str) -> None:
        """设置代理地址（暂未实现到浏览器的注入）。"""
        self.proxy = proxy

    def get_proxy(self) -> str | None:
        return self.proxy

    # ---- 应用配置到浏览器 ----
    def apply_to_browser(self, browser) -> None:
        """
        将当前网络配置应用到指定的 Browser 实例。
        browser 需要提供 set_user_agent 和 set_extra_headers 方法。
        """
        if self.user_agent is not None:
            browser.set_user_agent(self.user_agent)
        if self.headers:
            browser.set_extra_headers(self.headers)
