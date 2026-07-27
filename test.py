#!/usr/bin/env python3
"""
最小测试：通过 CDP 获取当前页面的 Cookie 和 LocalStorage。
已适配 Chromium 返回格式。
"""

import json
import websocket
import http.client

def http_get_json(host, port, path):
    conn = http.client.HTTPConnection(host, port, timeout=3)
    conn.request("GET", path)
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    return json.loads(data)

def get_page_ws_url():
    tabs = http_get_json("localhost", 9222, "/json")
    for t in tabs:
        if t["type"] == "page":
            return t["webSocketDebuggerUrl"]
    raise Exception("没有找到打开的页面")

def send_cdp(ws, method, params=None):
    msg_id = 1
    payload = {"id": msg_id, "method": method, "params": params or {}}
    ws.send(json.dumps(payload))
    while True:
        raw = ws.recv()
        resp = json.loads(raw)
        if resp.get("id") == msg_id:
            if "error" in resp:
                print("CDP 错误:", resp["error"])
                return None
            return resp.get("result", {})

def main():
    ws_url = get_page_ws_url()
    print("连接到:", ws_url)
    ws = websocket.create_connection(ws_url, timeout=5)
    ws.settimeout(1)

    send_cdp(ws, "DOMStorage.enable")
    send_cdp(ws, "Network.enable")

    # 获取当前 origin
    result = send_cdp(ws, "Runtime.evaluate", {"expression": "window.location.origin", "returnByValue": True})
    origin = result.get("result", {}).get("value", "")
    print("当前 origin:", origin)

    # 获取 LocalStorage
    if origin:
        print("尝试获取 LocalStorage...")
        result = send_cdp(ws, "DOMStorage.getDOMStorageItems", {
            "storageId": {"securityOrigin": origin, "isLocalStorage": True}
        })
        if result:
            entries = result.get("entries", [])
            print(f"LocalStorage 项数: {len(entries)}")
            for item in entries:
                # 条目可能是 [key, value] 对
                if isinstance(item, list) and len(item) == 2:
                    key, value = item[0], item[1]
                elif isinstance(item, dict):
                    key, value = item["key"], item["value"]
                else:
                    print("未知格式:", item)
                    continue
                print(f"  {key} = {value}")

    # 获取 Cookie
    print("尝试获取 Cookie...")
    result = send_cdp(ws, "Network.getCookies")
    if result:
        cookies = result.get("cookies", [])
        print(f"Cookie 数: {len(cookies)}")
        for c in cookies:
            print(f"  {c['name']} = {c['value']} (domain: {c.get('domain', '')})")

    ws.close()

if __name__ == "__main__":
    main()
