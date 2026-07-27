"""
cdp.py
Chrome DevTools Protocol 通信层。
提供同步的 WebSocket 连接、命令发送、页面管理功能。
"""

import json
import time
import http.client
import websocket


class CDPClient:
    """
    连接到某个 Tab 的 CDP WebSocket，发送命令并接收返回结果。
    所有操作均为同步，适配 Tkinter 单线程模型。
    """

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws: websocket.WebSocket | None = None
        self._msg_id = 0
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.ws is not None

    def connect(self, timeout: float = 5) -> None:
        """建立 WebSocket 连接，设置超时读取，方便后续同步等待。"""
        self.ws = websocket.create_connection(self.ws_url, timeout=timeout)
        self.ws.settimeout(0.5)  # 后续 recv 的超时时间，用于轮询
        self._connected = True

    def send_command(self, method: str, params: dict | None = None) -> dict:
        """
        发送 CDP 命令并同步等待返回。
        返回结果中的 result 字段（dict）。
        若收到 error 则抛出 RuntimeError。
        """
        if not self.is_connected:
            raise ConnectionError("CDP WebSocket 未连接")

        self._msg_id += 1
        msg_id = self._msg_id
        payload = {
            "id": msg_id,
            "method": method,
            "params": params or {}
        }

        self.ws.send(json.dumps(payload))

        # 循环接收消息直到收到对应 id 的响应
        while True:
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if not raw:
                continue

            message = json.loads(raw)
            if message.get("id") == msg_id:
                if "error" in message:
                    raise RuntimeError(f"CDP 命令执行失败: {message['error']}")
                return message.get("result", {})
            # 事件消息暂时忽略，后续可扩展事件处理

    def close(self) -> None:
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            finally:
                self.ws = None
                self._connected = False


class CDPManager:
    """
    管理 Chromium 进程的 CDP 连接。
    通过 HTTP 接口获取页面列表、创建新标签页、连接到指定页面。
    """

    def __init__(self, host: str = "localhost", port: int = 9222):
        self.host = host
        self.port = port

    def _http_get_json(self, path: str) -> dict | list:
        """向 CDP HTTP 服务发送 GET 请求并解析 JSON 响应。"""
        conn = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            if resp.status != 200:
                raise ConnectionError(f"CDP HTTP 请求失败，状态码: {resp.status}")
            data = resp.read().decode("utf-8")
            return json.loads(data)
        finally:
            conn.close()

    def get_version_info(self) -> dict:
        """获取浏览器版本信息（可用于检查 CDP 是否就绪）。"""
        return self._http_get_json("/json/version")

    def list_tabs(self) -> list[dict]:
        """返回所有打开的标签页信息列表。"""
        return self._http_get_json("/json")

    def create_new_tab(self, url: str = "about:blank") -> dict:
        """
        创建一个新的标签页，返回包含 webSocketDebuggerUrl 的 tab 信息。
        """
        return self._http_get_json(f"/json/new?url={url}")

    def connect_to_tab(self, tab_id: str | None = None) -> tuple[CDPClient, str]:
        """
        连接到指定的 tab_id，若不指定则连接到第一个 type=page 的标签页。
        返回 (CDPClient 实例, tab_id)。
        """
        tabs = self.list_tabs()
        pages = [t for t in tabs if t.get("type") == "page"]

        if not pages:
            raise RuntimeError("没有可用的浏览器页面（type=page）")

        target = None
        if tab_id:
            for page in pages:
                if page["id"] == tab_id:
                    target = page
                    break
            if not target:
                raise RuntimeError(f"未找到指定的标签页: {tab_id}")
        else:
            target = pages[0]

        ws_url = target["webSocketDebuggerUrl"]
        client = CDPClient(ws_url)
        client.connect()
        return client, target["id"]
