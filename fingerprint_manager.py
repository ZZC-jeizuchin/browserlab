"""
fingerprint_manager.py
Fingerprint 管理窗口 - 全局滚动，滚轮完美工作。
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class FingerprintManagerWindow:
    def __init__(self, parent, controller):
        self.controller = controller
        self.window = tk.Toplevel(parent)
        self.window.title("Fingerprint Manager")
        self.window.geometry("1000x700")

        # 主窗口网格：顶部栏 + 滚动区域
        self.window.grid_rowconfigure(0, weight=0)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        # ---------- 顶部按钮栏 ----------
        top_frame = ttk.Frame(self.window)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        top_frame.grid_columnconfigure(0, weight=0)
        top_frame.grid_columnconfigure(1, weight=0)
        top_frame.grid_columnconfigure(2, weight=0)
        top_frame.grid_columnconfigure(3, weight=0)
        top_frame.grid_columnconfigure(4, weight=1)

        ttk.Label(top_frame, text="身份模板:").grid(row=0, column=0, padx=(0,5))
        from fingerprint import Fingerprint
        preset_names = list(Fingerprint.PRESETS.keys())
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(top_frame, textvariable=self.preset_var,
                                         values=preset_names, state="readonly", width=30)
        self.preset_combo.grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="应用模板", command=self.apply_preset, width=10).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="立即注入", command=self.apply_now, width=10).grid(row=0, column=3, padx=5)

        # ---------- 可滚动画布区域 ----------
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # 在 Canvas 上绑定滚轮（保留作为后备）
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.category_texts = {}
        self._build_sections()
        # 为所有内部组件绑定滚轮，确保鼠标在任何位置都能滚动
        self._bind_scroll_recursive(self.scrollable_frame)
        # 打开窗口时自动从浏览器加载真实指纹值
        self.controller.refresh_fingerprint_from_browser()
        self.refresh()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self.canvas.yview_scroll(1, "units")

    def _bind_scroll_recursive(self, parent):
        """递归为所有子组件绑定滚轮事件，将滚动传递给 Canvas"""
        for child in parent.winfo_children():
            child.bind("<MouseWheel>", self._on_mousewheel)
            child.bind("<Button-4>", self._on_mousewheel)
            child.bind("<Button-5>", self._on_mousewheel)
            if child.winfo_children():
                self._bind_scroll_recursive(child)

    def _build_sections(self):
        categories = self.controller.fingerprint.CATEGORIES
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        for idx, category_name in enumerate(categories):
            frame = ttk.LabelFrame(self.scrollable_frame, text=category_name, padding=5)
            frame.grid(row=idx, column=0, sticky="ew", padx=5, pady=3)
            frame.grid_columnconfigure(0, weight=1)

            text = tk.Text(frame, wrap="none", font=("Consolas", 10), state="disabled",
                           height=6, bg="#ffffff")
            text.grid(row=0, column=0, sticky="nsew")
            frame.grid_rowconfigure(0, weight=1)

            text.bind("<Double-1>", lambda e, cat=category_name: self._edit_category_property(cat))
            self.category_texts[category_name] = text

    def refresh(self):
        categorized = self.controller.fingerprint.get_categorized_properties()

        for category, props in categorized.items():
            text = self.category_texts.get(category)
            if not text:
                continue

            text.config(state="normal")
            text.delete("1.0", tk.END)

            if not props:
                text.insert("end", "(无属性)")
                text.config(state="disabled")
                text.configure(height=2)
                continue

            max_key_len = max((len(p["key"]) for p in props), default=20)
            header = f"{'Property'.ljust(max_key_len)}  {'Value'.ljust(30)}  Description\n"
            separator = "-" * (max_key_len + 80)

            text.insert("end", header)
            text.insert("end", separator + "\n")

            for i, prop in enumerate(props):
                key = prop["key"]
                val_str = str(prop["value"]) if prop["value"] is not None else "(not set)"
                desc = prop["description"]
                line = f"{key.ljust(max_key_len)}  {val_str.ljust(30)}  {desc}"
                if i < len(props) - 1:
                    line += "\n"
                text.insert("end", line)

            text.config(state="disabled")
            num_lines = 2 + len(props)
            text.configure(height=num_lines)

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _edit_category_property(self, category):
        text = self.category_texts[category]
        try:
            cursor_pos = text.index("insert")
            line_text = text.get(f"{cursor_pos} linestart", f"{cursor_pos} lineend").strip()
            if not line_text or line_text.startswith("Property") or line_text.startswith("-"):
                return
            parts = line_text.split()
            if len(parts) < 2:
                return
            key = parts[0]
            old_val = self.controller.fingerprint.get_property(key)

            new_val = simpledialog.askstring("编辑属性", f"{key}\n当前值: {old_val}\n输入新值:",
                                             initialvalue=str(old_val) if old_val is not None else "",
                                             parent=self.window)
            if new_val is None:
                return
            try:
                if old_val is not None and isinstance(old_val, bool):
                    val = new_val.lower() in ("true", "1", "yes")
                elif old_val is not None and isinstance(old_val, int):
                    val = int(new_val)
                elif old_val is not None and isinstance(old_val, float):
                    val = float(new_val)
                elif old_val is not None and isinstance(old_val, list):
                    val = eval(new_val)
                else:
                    val = new_val
            except:
                val = new_val

            self.controller.fingerprint.set_property(key, val)
            self.refresh()
        except Exception:
            pass

    def apply_preset(self):
        preset = self.preset_var.get()
        if not preset:
            return
        success = self.controller.fingerprint.apply_preset(preset)
        if success:
            self.refresh()
            messagebox.showinfo("成功", f"已应用模板: {preset}")
        else:
            messagebox.showerror("错误", "应用模板失败")

    def apply_now(self):
        self.controller.apply_fingerprint_now()
        messagebox.showinfo("提示", "指纹配置已注入（刷新页面生效）")
