"""
fingerprint_manager.py
独立的 Fingerprint 管理窗口 - 支持所有可读属性、添加自定义属性、双击编辑。
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class FingerprintManagerWindow:
    def __init__(self, parent, controller):
        self.controller = controller
        self.window = tk.Toplevel(parent)
        self.window.title("Fingerprint Manager")
        self.window.geometry("800x600")

        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        self.create_widgets()
        self.refresh_properties()

    def create_widgets(self):
        top_frame = ttk.Frame(self.window)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(top_frame, text="身份模板:").pack(side="left")
        from fingerprint import Fingerprint
        preset_names = list(Fingerprint.PRESETS.keys())
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(top_frame, textvariable=self.preset_var,
                                         values=preset_names, state="readonly", width=30)
        self.preset_combo.pack(side="left", padx=5)
        ttk.Button(top_frame, text="应用模板", command=self.apply_preset).pack(side="left", padx=5)
        ttk.Button(top_frame, text="立即注入到浏览器", command=self.apply_now).pack(side="left", padx=5)

        text_frame = ttk.Frame(self.window)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.text = tk.Text(text_frame, wrap="none", font=("Consolas", 11), state="disabled")
        self.text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self.window)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Add Property", command=self.add_property).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_properties).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack(side="right", padx=2)

        self.text.bind("<Double-Button-1>", self.on_double_click)

    def refresh_properties(self):
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)

        props = self.controller.get_fingerprint_properties()
        if not props:
            self.text.insert("end", "No properties found.\n")
        else:
            max_key_len = max((len(k) for k in props), default=20)
            header = f"{'Property'.ljust(max_key_len)}  Value\n"
            separator = "-" * (max_key_len + 50) + "\n"
            self.text.insert("end", header)
            self.text.insert("end", separator)
            for key, value in sorted(props.items()):
                display_val = str(value) if value is not None else "(not set)"
                line = f"{key.ljust(max_key_len)}  {display_val}\n"
                self.text.insert("end", line)

        self.text.config(state="disabled")

    def _get_selected_property(self):
        try:
            cursor_index = self.text.index("insert")
            line_text = self.text.get(f"{cursor_index} linestart", f"{cursor_index} lineend").strip()
            if not line_text or "Property" in line_text or "---" in line_text:
                return None, None
            parts = line_text.split(None, 1)
            if len(parts) >= 1:
                prop = parts[0]
                old_val = parts[1] if len(parts) > 1 else ""
                if old_val == "(not set)":
                    old_val = ""
                return prop, old_val
        except Exception:
            pass
        return None, None

    def edit_selected(self):
        prop, old_val = self._get_selected_property()
        if prop:
            self.edit_property(prop, old_val)
        else:
            messagebox.showinfo("提示", "请先将光标移动到属性行上。")

    def on_double_click(self, event):
        prop, old_val = self._get_selected_property()
        if prop:
            self.edit_property(prop, old_val)

    def edit_property(self, prop, old_val):
        new_val = simpledialog.askstring("编辑属性", f"{prop}\n输入新值:",
                                         initialvalue=old_val, parent=self.window)
        if new_val is None:
            return

        # 类型转换
        if prop in ["navigator.hardwareConcurrency", "navigator.deviceMemory",
                     "screen.width", "screen.height", "screen.availWidth", "screen.availHeight",
                     "screen.colorDepth", "screen.pixelDepth",
                     "navigator.maxTouchPoints", "navigator.connection.rtt", "navigator.connection.downlink",
                     "battery.chargingTime", "battery.dischargingTime"]:
            try:
                val = int(new_val)
            except ValueError:
                messagebox.showerror("错误", "请输入整数")
                return
        elif prop in ["battery.level"]:
            try:
                val = float(new_val)
            except ValueError:
                messagebox.showerror("错误", "请输入数字")
                return
        elif prop in ["battery.charging", "navigator.cookieEnabled", "navigator.onLine"]:
            if new_val.lower() in ("true", "1", "yes"):
                val = True
            elif new_val.lower() in ("false", "0", "no"):
                val = False
            else:
                messagebox.showerror("错误", "请输入 True 或 False")
                return
        elif prop in ["navigator.languages", "mediaDevices", "navigator.plugins", "navigator.mimeTypes"]:
            try:
                val = eval(new_val)
                if not isinstance(val, list):
                    raise ValueError
            except Exception:
                messagebox.showerror("错误", "格式错误，请输入 Python 列表")
                return
        else:
            val = new_val

        self.controller.set_fingerprint_property(prop, val)
        self.refresh_properties()

    def add_property(self):
        prop = simpledialog.askstring("添加属性", "输入属性路径 (例如 navigator.webdriver):", parent=self.window)
        if not prop:
            return
        default_val = simpledialog.askstring("默认值", "输入默认值 (留空为 None):", parent=self.window)
        if default_val == "" or default_val is None:
            val = None
        else:
            try:
                val = eval(default_val)
            except Exception:
                val = default_val
        self.controller.add_fingerprint_custom_property(prop, val)
        self.controller.set_fingerprint_property(prop, val)
        self.refresh_properties()

    def apply_preset(self):
        preset = self.preset_var.get()
        if not preset:
            return
        success = self.controller.apply_fingerprint_preset(preset)
        if success:
            self.refresh_properties()
            messagebox.showinfo("成功", f"已应用模板: {preset}")
        else:
            messagebox.showerror("错误", "应用模板失败")

    def apply_now(self):
        self.controller.apply_fingerprint_now()
        messagebox.showinfo("提示", "指纹配置已注入到浏览器（刷新页面后生效）")
