"""
ui.py
BrowserLab 图形界面：提供浏览器控制、网络身份配置、Storage/Fingerprint 入口和日志输出。
"""

import tkinter as tk
from tkinter import ttk


class UI:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("BrowserLab V0.6")
        self.root.geometry("800x650")
        self.create_widgets()

    def create_widgets(self):
        # 浏览器控制
        control_frame = ttk.LabelFrame(self.root, text="浏览器控制", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(control_frame, text="Open Browser", command=self.open_browser).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Close Browser", command=self.close_browser).pack(side="left", padx=5)
        ttk.Button(control_frame, text="New Tab", command=self.new_tab).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Close Tab", command=self.close_tab).pack(side="left", padx=5)
        self.tab_count_label = ttk.Label(control_frame, text="Tabs: 0")
        self.tab_count_label.pack(side="left", padx=15)

        # 地址栏
        url_frame = ttk.Frame(self.root)
        url_frame.pack(fill="x", padx=10, pady=2)
        ttk.Label(url_frame, text="URL:").pack(side="left")
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.url_entry.insert(0, "https://example.com")
        self.url_entry.bind("<Return>", lambda e: self.go())
        ttk.Button(url_frame, text="Go", command=self.go).pack(side="left")

        # 导航按钮
        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(fill="x", padx=10, pady=2)
        ttk.Button(nav_frame, text="← Back", command=self.back).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="→ Forward", command=self.forward).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="Reload", command=self.reload).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="Get URL", command=self.show_url).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="Get Title", command=self.show_title).pack(side="left", padx=2)

        # JS 控制台
        js_frame = ttk.LabelFrame(self.root, text="JavaScript 控制台", padding=10)
        js_frame.pack(fill="x", padx=10, pady=5)
        self.js_entry = ttk.Entry(js_frame)
        self.js_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.js_entry.insert(0, "document.title")
        self.js_entry.bind("<Return>", lambda e: self.execute_js())
        ttk.Button(js_frame, text="Execute JS", command=self.execute_js).pack(side="left")

        # 网络身份
        net_frame = ttk.LabelFrame(self.root, text="网络身份 (Network)", padding=10)
        net_frame.pack(fill="x", padx=10, pady=5)

        ua_frame = ttk.Frame(net_frame)
        ua_frame.pack(fill="x", pady=2)
        ttk.Label(ua_frame, text="User-Agent:").pack(side="left")
        self.ua_entry = ttk.Entry(ua_frame)
        self.ua_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.ua_entry.insert(0, "")
        ttk.Button(ua_frame, text="Set UA", command=self.set_ua).pack(side="left")

        hdr_frame = ttk.Frame(net_frame)
        hdr_frame.pack(fill="x", pady=2)
        ttk.Label(hdr_frame, text="Header (key=value):").pack(side="left")
        self.header_entry = ttk.Entry(hdr_frame)
        self.header_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.header_entry.insert(0, "X-Custom-Header=MyValue")
        self.header_entry.bind("<Return>", lambda e: self.set_header())
        ttk.Button(hdr_frame, text="Add/Set Header", command=self.set_header).pack(side="left")
        ttk.Button(hdr_frame, text="Clear Headers", command=self.clear_headers).pack(side="left", padx=5)

        # Storage 和 Fingerprint 入口
        mgmt_frame = ttk.Frame(self.root)
        mgmt_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(mgmt_frame, text="Manage Storage", command=self.open_storage_manager).pack(side="left")
        ttk.Button(mgmt_frame, text="Manage Fingerprint", command=self.open_fingerprint_manager).pack(side="left", padx=5)

        # 日志
        log_frame = ttk.LabelFrame(self.root, text="Console Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.console = tk.Text(log_frame, height=15, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=scrollbar.set)
        self.console.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ---------- 辅助 ----------
    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.update_tab_count()

    def update_tab_count(self):
        try:
            if self.controller.browser_running():
                count = self.controller.get_tab_count()
                self.tab_count_label.config(text=f"Tabs: {count}")
            else:
                self.tab_count_label.config(text="Tabs: 0")
        except Exception:
            self.tab_count_label.config(text="Tabs: ?")

    def open_storage_manager(self):
        from storage_manager import StorageManagerWindow
        StorageManagerWindow(self.root, self.controller)

    def open_fingerprint_manager(self):
        from fingerprint_manager import FingerprintManagerWindow
        FingerprintManagerWindow(self.root, self.controller)

    # ---------- 按钮回调 ----------
    def open_browser(self):
        url = self.url_entry.get().strip() or "https://swctools.pages.dev/device"
        self.controller.open_browser(url)
        self.log(f"打开浏览器: {url}")

    def close_browser(self):
        self.controller.close_browser()
        self.log("浏览器已关闭。")

    def go(self):
        url = self.url_entry.get().strip()
        if url:
            self.controller.load_url(url)
            self.log(f"导航至: {url}")

    def back(self):
        self.controller.back()
        self.log("后退")

    def forward(self):
        self.controller.forward()
        self.log("前进")

    def reload(self):
        self.controller.reload()
        self.log("刷新页面")

    def show_url(self):
        url = self.controller.get_url()
        self.log(f"当前 URL: {url}")
        if url:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)

    def show_title(self):
        title = self.controller.get_title()
        self.log(f"页面标题: {title}")

    def execute_js(self):
        script = self.js_entry.get().strip()
        if script:
            self.log(f"执行 JS: {script}")
            self.controller.execute_js(script)

    def new_tab(self):
        url = self.url_entry.get().strip() or "about:blank"
        self.controller.new_tab(url)
        self.log(f"打开新标签页: {url}")

    def close_tab(self):
        self.controller.close_tab()
        self.log("关闭当前标签页")

    def set_ua(self):
        ua = self.ua_entry.get().strip()
        if ua:
            self.controller.set_user_agent(ua)
        else:
            self.log("User-Agent 输入为空，未做修改。")

    def set_header(self):
        text = self.header_entry.get().strip()
        if "=" not in text:
            self.log("格式错误，请使用 key=value")
            return
        key, _, value = text.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            self.log("Header 键不能为空")
            return
        self.controller.set_header(key, value)

    def clear_headers(self):
        self.controller.clear_headers()

    def run(self):
        self.root.mainloop()
