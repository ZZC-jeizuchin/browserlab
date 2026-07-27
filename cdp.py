"""
cdp.py
Chrome DevTools Protocol 通信层，增加事件回调支持。
"""

import json
import time
import http.client
import websocket


class CDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws: websocket.WebSocket | None = None
        self._msg_id = 0
        self._connected = False
        self._event_callback = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self.ws is not None

    def connect(self, timeout: float = 5) -> None:
        self.ws = websocket.create_connection(self.ws_url, timeout=timeout)
        self.ws.settimeout(0.1)  # 缩短超时以便及时处理事件
        self._connected = True

    def set_event_callback(self, callback):
        """设置事件回调函数，callback 接收 (method, params) 两个参数"""
        self._event_callback = callback

    def send_command(self, method: str, params: dict | None = None) -> dict:
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
        while True:
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if not raw:
                continue
            message = json.loads(raw)
            # 事件消息没有 id
            if "id" not in message:
                if self._event_callback:
                    self._event_callback(message.get("method", ""), message.get("params", {}))
                continue
            if message.get("id") == msg_id:
                if "error" in message:
                    raise RuntimeError(f"CDP 命令执行失败: {message['error']}")
                return message.get("result", {})

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
    def __init__(self, host: str = "localhost", port: int = 9222):
        self.host = host
        self.port = port

    def _http_get_json(self, path: str) -> dict | list:
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

    def _http_put_json(self, path: str, body: dict | None = None) -> dict:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            body_json = json.dumps(body) if body else ""
            conn.request("PUT", path, body=body_json, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            if resp.status != 200:
                raise ConnectionError(f"CDP PUT 请求失败，状态码: {resp.status}")
            data = resp.read().decode("utf-8")
            return json.loads(data)
        finally:
            conn.close()

    def get_version_info(self) -> dict:
        return self._http_get_json("/json/version")

    def list_tabs(self) -> list[dict]:
        return self._http_get_json("/json")

    def create_new_tab(self, url: str = "about:blank") -> dict:
        return self._http_put_json(f"/json/new?url={url}")

    def connect_to_tab(self, tab_id: str | None = None) -> tuple[CDPClient, str]:
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
