"""
browser.py
Browser 抽象层：负责浏览器生命周期、页面导航、JS 执行、标签管理，
以及通过 CDP 注入网络身份、通用预加载脚本。
"""

import subprocess
import time
import json
from cdp import CDPManager, CDPClient


class Browser:
    def __init__(self, debug_port: int = 9222):
        self.process: subprocess.Popen | None = None
        self.debug_port = debug_port
        self.cdp_manager = CDPManager(port=debug_port)
        self.cdp_client: CDPClient | None = None
        self.current_tab_id: str | None = None

    # ==================== 生命周期 ====================
    def is_running(self) -> bool:
        if self.process is None:
            return False
        if self.process.poll() is None:
            return True
        self.process = None
        self._cleanup_cdp()
        return False

    def open(self, url: str = "https://example.com") -> None:
        if self.is_running():
            return

        self.process = subprocess.Popen(
            [
                "chromium",
                f"--remote-debugging-port={self.debug_port}",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--no-default-browser-check",
                url,
            ]
        )

        self._wait_for_cdp_ready()

        try:
            self.cdp_client, self.current_tab_id = self.cdp_manager.connect_to_tab()
        except Exception:
            self._terminate_process()
            raise RuntimeError("无法连接到浏览器页面，请检查 CDP 端口是否可用")

        self.cdp_client.send_command("Page.enable")
        self.cdp_client.send_command("Runtime.enable")
        self.cdp_client.send_command("Network.enable")

    def close(self) -> None:
        if not self.is_running():
            return
        self._cleanup_cdp()
        self._terminate_process()

    # ==================== 页面控制 ====================
    def load_url(self, url: str) -> None:
        self._ensure_connected()
        self.cdp_client.send_command("Page.navigate", {"url": url})

    def reload(self) -> None:
        self._ensure_connected()
        self.cdp_client.send_command("Page.reload")

    def back(self) -> None:
        self.execute_js("window.history.back();")

    def forward(self) -> None:
        self.execute_js("window.history.forward();")

    def execute_js(self, script: str) -> any:
        self._ensure_connected()
        result = self.cdp_client.send_command(
            "Runtime.evaluate",
            {"expression": script, "returnByValue": True}
        )
        if "result" in result and "value" in result["result"]:
            return result["result"]["value"]
        return None

    def get_title(self) -> str:
        return self.execute_js("document.title") or ""

    def get_url(self) -> str:
        return self.execute_js("window.location.href") or ""

    def get_tabs(self) -> list[dict]:
        return self.cdp_manager.list_tabs()

    def new_tab(self, url: str = "about:blank") -> None:
        self._ensure_connected()
        new_tab_info = self.cdp_manager.create_new_tab(url)
        new_id = new_tab_info["id"]
        self._switch_to_tab(new_id)

    def close_tab(self) -> None:
        self._ensure_connected()
        if not self.current_tab_id:
            return
        try:
            self.cdp_client.send_command("Target.closeTarget", {"targetId": self.current_tab_id})
        except RuntimeError:
            pass
        try:
            self.cdp_client, self.current_tab_id = self.cdp_manager.connect_to_tab()
            self.cdp_client.send_command("Page.enable")
            self.cdp_client.send_command("Runtime.enable")
            self.cdp_client.send_command("Network.enable")
        except RuntimeError:
            self.cdp_client = None
            self.current_tab_id = None

    # ==================== 网络身份注入 ====================
    def set_user_agent(self, user_agent: str) -> None:
        self._ensure_connected()
        self.cdp_client.send_command("Network.setUserAgentOverride", {
            "userAgent": user_agent
        })

    def set_extra_headers(self, headers: dict[str, str]) -> None:
        self._ensure_connected()
        self.cdp_client.send_command("Network.setExtraHTTPHeaders", {
            "headers": headers
        })

    # ==================== 通用预加载脚本注入 ====================
    def inject_on_new_document(self, script: str) -> None:
        """
        注入一段 JavaScript 脚本，在每次新页面加载前执行。
        """
        self._ensure_connected()
        self.cdp_client.send_command("Page.addScriptToEvaluateOnNewDocument", {
            "source": script
        })

    # ==================== 读取 Storage 快照 ====================
    def get_cookies_via_js(self) -> dict[str, str]:
        """通过 JS 获取当前页面可访问的 Cookie（name: value）"""
        script = """
        (function() {
            const pairs = document.cookie.split('; ');
            const result = {};
            for (const p of pairs) {
                const eq = p.indexOf('=');
                if (eq > 0) {
                    const name = decodeURIComponent(p.substring(0, eq));
                    const value = decodeURIComponent(p.substring(eq + 1));
                    result[name] = value;
                }
            }
            return result;
        })()
        """
        result = self.execute_js(script)
        return result if isinstance(result, dict) else {}

    def get_local_storage_via_js(self) -> dict[str, str]:
        """通过 JS 获取当前页面的所有 LocalStorage 键值对"""
        script = """
        (function() {
            const result = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                result[key] = localStorage.getItem(key);
            }
            return result;
        })()
        """
        result = self.execute_js(script)
        return result if isinstance(result, dict) else {}

    # ==================== 内部辅助 ====================
    def _ensure_connected(self) -> None:
        if not self.is_running():
            raise RuntimeError("浏览器未启动")
        if not self.cdp_client or not self.cdp_client.is_connected:
            raise RuntimeError("CDP 连接已断开")

    def _wait_for_cdp_ready(self, timeout: float = 10) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.is_running():
                raise RuntimeError("浏览器进程意外退出")
            try:
                self.cdp_manager.get_version_info()
                return
            except Exception:
                time.sleep(0.2)
        raise TimeoutError("等待 Chromium CDP 服务启动超时")

    def _terminate_process(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None

    def _cleanup_cdp(self) -> None:
        if self.cdp_client:
            self.cdp_client.close()
            self.cdp_client = None
            self.current_tab_id = None

    def _switch_to_tab(self, tab_id: str) -> None:
        if self.cdp_client:
            self.cdp_client.close()
        self.cdp_client, self.current_tab_id = self.cdp_manager.connect_to_tab(tab_id)
        self.cdp_client.send_command("Page.enable")
        self.cdp_client.send_command("Runtime.enable")
        self.cdp_client.send_command("Network.enable")
