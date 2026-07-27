"""
browser.py
Browser 抽象层：Storage.getCookies 获取全部 Cookie，复用空白页避免标签页弹出。
"""

import subprocess
import time
from urllib.parse import urlparse
from cdp import CDPManager, CDPClient


def _ensure_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url


class Browser:
    def __init__(self, debug_port: int = 9222):
        self.process: subprocess.Popen | None = None
        self.debug_port = debug_port
        self.cdp_manager = CDPManager(port=debug_port)
        self.cdp_client: CDPClient | None = None
        self.current_tab_id: str | None = None
        self._domain_visit_callback = None

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
        url = _ensure_url(url)
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
        self.sync_active_tab()

    def close(self) -> None:
        if not self.is_running():
            return
        self._cleanup_cdp()
        self._terminate_process()

    def set_domain_visit_callback(self, callback):
        self._domain_visit_callback = callback
        if self.cdp_client:
            self._setup_event_listener()

    # ==================== 标签页同步 ====================
    def sync_active_tab(self) -> None:
        try:
            pages = [t for t in self.cdp_manager.list_tabs() if t.get("type") == "page"]
            if not pages:
                self._cleanup_cdp()
                raise RuntimeError("浏览器没有打开的页面")
            active_id = pages[0]["id"]
            if self.current_tab_id != active_id or not self.cdp_client or not self.cdp_client.is_connected:
                if self.cdp_client:
                    self.cdp_client.close()
                ws_url = pages[0]["webSocketDebuggerUrl"]
                self.cdp_client = CDPClient(ws_url)
                self.cdp_client.connect()
                self.current_tab_id = active_id
                self.cdp_client.send_command("Page.enable")
                self.cdp_client.send_command("Runtime.enable")
                self.cdp_client.send_command("Network.enable")
                self.cdp_client.send_command("DOMStorage.enable")
                self._setup_event_listener()
        except Exception:
            self._cleanup_cdp()
            raise RuntimeError("无法同步活动标签页")

    def _ensure_connected(self) -> None:
        if not self.is_running():
            raise RuntimeError("浏览器未启动")
        self.sync_active_tab()
        if not self.cdp_client or not self.cdp_client.is_connected:
            raise RuntimeError("CDP 连接已断开")

    def _setup_event_listener(self):
        if not self.cdp_client:
            return
        def on_event(method, params):
            if method == "Page.frameNavigated" and self._domain_visit_callback:
                url = params.get("frame", {}).get("url", "")
                if url and not url.startswith("chrome://") and url != "about:blank":
                    parsed = urlparse(url)
                    domain = parsed.hostname
                    if domain:
                        self._domain_visit_callback(domain)
        self.cdp_client.set_event_callback(on_event)

    # ==================== 页面控制 ====================
    def load_url(self, url: str) -> None:
        self._ensure_connected()
        url = _ensure_url(url)
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
        url = _ensure_url(url) if url != "about:blank" else url
        try:
            self.cdp_manager.create_new_tab(url)
        except Exception as e:
            raise RuntimeError(f"创建新标签页失败: {e}")
        self.sync_active_tab()

    def close_tab(self) -> None:
        self._ensure_connected()
        if not self.current_tab_id:
            return
        closing_id = self.current_tab_id
        try:
            self.cdp_client.send_command("Target.closeTarget", {"targetId": closing_id})
        except RuntimeError:
            pass
        self.sync_active_tab()

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

    # ==================== LocalStorage 操作 ====================
    def _storage_id(self, origin: str):
        return {"securityOrigin": origin, "isLocalStorage": True}

    def get_all_local_storage(self, origin: str) -> dict[str, str]:
        """直接读取 LocalStorage，失败则通过临时导航空白页读取。"""
        self._ensure_connected()
        try:
            result = self.cdp_client.send_command("DOMStorage.getDOMStorageItems", {
                "storageId": self._storage_id(origin)
            })
            return self._parse_ls_entries(result.get("entries", []))
        except RuntimeError as e:
            if "Frame not found" in str(e):
                return self._read_ls_with_temp_frame(origin)
            raise

    def _parse_ls_entries(self, entries) -> dict[str, str]:
        storage = {}
        for item in entries:
            if isinstance(item, list) and len(item) == 2:
                key, value = item[0], item[1]
            elif isinstance(item, dict):
                key, value = item["key"], item["value"]
            else:
                continue
            storage[key] = value
        return storage

    def set_local_storage_item(self, origin: str, key: str, value: str) -> None:
        self._ensure_connected()
        try:
            self.cdp_client.send_command("DOMStorage.setDOMStorageItem", {
                "storageId": self._storage_id(origin),
                "key": key,
                "value": value
            })
        except RuntimeError as e:
            if "Frame not found" in str(e):
                self._write_ls_with_temp_frame("set", origin, key, value)
            else:
                raise

    def remove_local_storage_item(self, origin: str, key: str) -> None:
        self._ensure_connected()
        try:
            self.cdp_client.send_command("DOMStorage.removeDOMStorageItem", {
                "storageId": self._storage_id(origin),
                "key": key
            })
        except RuntimeError as e:
            if "Frame not found" in str(e):
                self._write_ls_with_temp_frame("remove", origin, key)
            else:
                raise

    def clear_local_storage(self, origin: str) -> None:
        self._ensure_connected()
        try:
            self.cdp_client.send_command("DOMStorage.clearDOMStorageItems", {
                "storageId": self._storage_id(origin)
            })
        except RuntimeError as e:
            if "Frame not found" in str(e):
                self._write_ls_with_temp_frame("clear", origin)
            else:
                raise

    # ==================== Cookie 操作 ====================
    def get_all_cookies(self) -> list[dict]:
        """
        使用 Storage.getCookies 获取浏览器全部 Cookie（不依赖当前页面）。
        """
        self._ensure_connected()
        result = self.cdp_client.send_command("Storage.getCookies")
        cookies = result.get("cookies", [])
        # 调试输出
        print("[Browser] 原始 Cookie 数据:")
        for c in cookies:
            print(f"  {c.get('domain')}: {c.get('name')} = {c.get('value')}")
        return cookies

    def set_cookie(self, name: str, value: str, domain: str, path: str = "/") -> None:
        self._ensure_connected()
        expires = time.time() + 365 * 24 * 3600
        self.cdp_client.send_command("Network.setCookie", {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "secure": True,
            "httpOnly": False,
            "sameSite": "None",
            "expires": expires
        })

    def delete_cookies(self, name: str, domain: str) -> None:
        self._ensure_connected()
        self.cdp_client.send_command("Network.deleteCookies", {
            "name": name,
            "domain": domain
        })

    # ==================== 临时导航（复用空白页） ====================
    def _with_temp_frame(self, origin: str, callback, *args, **kwargs):
        """
        在当前标签页（空白页）上临时导航至目标 origin，执行回调后恢复 about:blank。
        整个过程不创建新标签页，用户无感。
        """
        original_url = self.get_url()
        # 导航到目标域（极轻量资源）
        self.cdp_client.send_command("Page.navigate", {"url": origin + "/favicon.ico"})
        deadline = time.time() + 1.0
        while time.time() < deadline:
            try:
                current = self.get_url()
                if current.startswith(origin):
                    break
            except:
                pass
            time.sleep(0.05)
        # 停止加载并清空文档
        self.cdp_client.send_command("Page.stopLoading")
        self.execute_js("document.open();document.write('');document.close();")
        try:
            # 执行回调（例如读写 LocalStorage）
            callback(*args, **kwargs)
        finally:
            # 恢复为 about:blank
            self.cdp_client.send_command("Page.navigate", {"url": "about:blank"})
            deadline = time.time() + 0.5
            while time.time() < deadline:
                if self.get_url() == "about:blank":
                    break
                time.sleep(0.05)

    def _read_ls_with_temp_frame(self, origin: str) -> dict[str, str]:
        storage = {}
        def do_read():
            nonlocal storage
            result = self.cdp_client.send_command("DOMStorage.getDOMStorageItems", {
                "storageId": self._storage_id(origin)
            })
            storage = self._parse_ls_entries(result.get("entries", []))
        self._with_temp_frame(origin, do_read)
        return storage

    def _write_ls_with_temp_frame(self, action: str, origin: str,
                                    key: str = None, value: str = None):
        def do_write():
            sid = self._storage_id(origin)
            if action == "set":
                self.cdp_client.send_command("DOMStorage.setDOMStorageItem", {
                    "storageId": sid, "key": key, "value": value
                })
            elif action == "remove":
                self.cdp_client.send_command("DOMStorage.removeDOMStorageItem", {
                    "storageId": sid, "key": key
                })
            elif action == "clear":
                self.cdp_client.send_command("DOMStorage.clearDOMStorageItems", {
                    "storageId": sid
                })
        self._with_temp_frame(origin, do_write)

    # ==================== 指纹注入 ====================
    def inject_on_new_document(self, script: str) -> None:
        self._ensure_connected()
        self.cdp_client.send_command("Page.addScriptToEvaluateOnNewDocument", {
            "source": script
        })

    # ==================== 内部辅助 ====================
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
