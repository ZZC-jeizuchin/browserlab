"""
storage_manager.py
独立 Storage 管理窗口 - 所有数据实时从浏览器获取，不缓存。
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class StorageManagerWindow:
    def __init__(self, parent, controller):
        self.controller = controller
        self.window = tk.Toplevel(parent)
        self.window.title("Storage Manager")
        self.window.geometry("900x650")

        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(1, weight=1)

        self.selected_domain = tk.StringVar()
        self.create_widgets()
        self.refresh_domain_list()

    def create_widgets(self):
        # 顶部：Refresh All 按钮 + 写入权限开关
        top_frame = ttk.Frame(self.window)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ttk.Button(top_frame, text="Refresh All", command=self.refresh_all).pack(side="left", padx=10)

        # 左侧域列表
        left_frame = ttk.Frame(self.window, width=200)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        left_frame.grid_propagate(False)

        ttk.Label(left_frame, text="Domains").pack(anchor="w")
        self.domain_listbox = tk.Listbox(left_frame)
        self.domain_listbox.pack(fill="both", expand=True, pady=5)
        self.domain_listbox.bind("<<ListboxSelect>>", self.on_domain_select)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Add Domain", command=self.add_domain).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete Domain", command=self.delete_domain).pack(side="left", padx=2)

        # 右侧 Notebook
        right_frame = ttk.Frame(self.window)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill="both", expand=True)

        cookie_tab = ttk.Frame(self.notebook)
        self.notebook.add(cookie_tab, text="Cookies")
        self.build_text_tab(cookie_tab, "cookie")

        ls_tab = ttk.Frame(self.notebook)
        self.notebook.add(ls_tab, text="LocalStorage")
        self.build_text_tab(ls_tab, "localstorage")

        ttk.Button(self.window, text="Close", command=self.window.destroy).grid(
            row=2, column=0, columnspan=2, pady=5
        )

    def build_text_tab(self, parent, storage_type):
        btn_bar = ttk.Frame(parent)
        btn_bar.pack(fill="x", pady=2)

        if storage_type == "cookie":
            ttk.Button(btn_bar, text="Add Cookie", command=self.add_cookie).pack(side="left", padx=2)
            ttk.Button(btn_bar, text="Delete Selected", command=lambda: self.delete_item("cookie")).pack(side="left", padx=2)
            ttk.Button(btn_bar, text="Clear All", command=self.clear_cookies).pack(side="left", padx=2)
        else:
            ttk.Button(btn_bar, text="Add Item", command=self.add_localstorage).pack(side="left", padx=2)
            ttk.Button(btn_bar, text="Delete Selected", command=lambda: self.delete_item("localstorage")).pack(side="left", padx=2)
            ttk.Button(btn_bar, text="Clear All", command=self.clear_localstorage).pack(side="left", padx=2)

        ttk.Button(btn_bar, text="Reload Page", command=self.reload_page).pack(side="right", padx=5)

        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True, pady=5)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        text_widget = tk.Text(text_frame, wrap="none", font=("Consolas", 11), state="disabled")
        text_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.bind("<Double-Button-1>", lambda e: self.edit_item(storage_type))

        if storage_type == "cookie":
            self.cookie_text = text_widget
        else:
            self.ls_text = text_widget

    # ================== 域列表操作 ==================
    def refresh_domain_list(self):
        domains = self.controller.get_storage_domains()
        self.domain_listbox.delete(0, tk.END)
        for d in domains:
            self.domain_listbox.insert(tk.END, d)
        if domains:
            self.domain_listbox.selection_set(0)
            self.on_domain_select()
        else:
            self.cookie_text.config(state="normal")
            self.cookie_text.delete("1.0", tk.END)
            self.cookie_text.insert("1.0", "No domains.")
            self.cookie_text.config(state="disabled")
            self.ls_text.config(state="normal")
            self.ls_text.delete("1.0", tk.END)
            self.ls_text.config(state="disabled")

    def on_domain_select(self, event=None):
        sel = self.domain_listbox.curselection()
        if sel:
            domain = self.domain_listbox.get(sel[0])
            self.selected_domain.set(domain)
            self.load_domain_data(domain)

    def load_domain_data(self, domain):
        # 实时从浏览器获取数据
        cookies = self.controller.get_cookies_for_domain(domain)
        self._populate_text(self.cookie_text, cookies, title="Cookie (live)")
        ls = self.controller.get_local_storage_for_domain(domain)
        self._populate_text(self.ls_text, ls, title="LocalStorage (live)")

    def _populate_text(self, text_widget, data_dict, title=""):
        text_widget.config(state="normal")
        text_widget.delete("1.0", tk.END)
        if title:
            text_widget.insert("end", f"{title}\n", "header")
            text_widget.insert("end", "-" * 40 + "\n")
        if not data_dict:
            text_widget.insert("end", "(empty)\n")
        else:
            for key, value in data_dict.items():
                line = f"{key} = {value}\n"
                text_widget.insert("end", line)
        text_widget.config(state="disabled")
        text_widget.tag_config("header", font=("Consolas", 11, "bold"))

    # ================== 编辑 / 删除 ==================
    def edit_item(self, storage_type):
        text_widget = self.cookie_text if storage_type == "cookie" else self.ls_text
        try:
            cursor_index = text_widget.index("insert")
            line_text = text_widget.get(f"{cursor_index} linestart", f"{cursor_index} lineend").strip()
            if not line_text or "=" not in line_text or "(empty)" in line_text:
                messagebox.showinfo("提示", "请点击具体的键值对行。")
                return
            key, _, value = line_text.partition("=")
            key = key.strip()
            value = value.strip()
            self._edit_key_value(storage_type, key, value)
        except Exception:
            pass

    def _edit_key_value(self, storage_type, key, current_value):
        domain = self.selected_domain.get()
        if not domain:
            return
        new_val = simpledialog.askstring("编辑", f"修改 {key} 的值:", initialvalue=current_value, parent=self.window)
        if new_val is None:
            return
        if storage_type == "cookie":
            self.controller.set_cookie(domain, key, new_val)
        else:
            self.controller.set_local_storage_item(domain, key, new_val)
        self.load_domain_data(domain)  # 立即刷新显示

    def delete_item(self, storage_type):
        text_widget = self.cookie_text if storage_type == "cookie" else self.ls_text
        try:
            sel = text_widget.tag_ranges("sel")
            if sel:
                line_text = text_widget.get(sel[0], sel[1]).strip()
            else:
                cursor_index = text_widget.index("insert")
                line_text = text_widget.get(f"{cursor_index} linestart", f"{cursor_index} lineend").strip()
        except Exception:
            return

        if not line_text or "=" not in line_text or "(empty)" in line_text:
            messagebox.showinfo("提示", "请选中要删除的行。")
            return

        key = line_text.split("=")[0].strip()
        domain = self.selected_domain.get()
        if not domain:
            return
        if messagebox.askyesno("确认", f"删除 {key}？"):
            if storage_type == "cookie":
                self.controller.delete_cookie(domain, key)
            else:
                self.controller.delete_local_storage_item(domain, key)
            self.load_domain_data(domain)

    # ================== 添加 / 清空 ==================
    def add_cookie(self):
        domain = self.selected_domain.get()
        if not domain:
            messagebox.showerror("错误", "请先选择一个域。")
            return
        name = simpledialog.askstring("添加 Cookie", "名称:", parent=self.window)
        if not name:
            return
        value = simpledialog.askstring("添加 Cookie", "值:", parent=self.window)
        if value is None:
            return
        self.controller.set_cookie(domain, name, value)
        self.load_domain_data(domain)

    def add_localstorage(self):
        domain = self.selected_domain.get()
        if not domain:
            messagebox.showerror("错误", "请先选择一个域。")
            return
        key = simpledialog.askstring("添加 LocalStorage", "键:", parent=self.window)
        if not key:
            return
        value = simpledialog.askstring("添加 LocalStorage", "值:", parent=self.window)
        if value is None:
            return
        self.controller.set_local_storage_item(domain, key, value)
        self.load_domain_data(domain)

    def clear_cookies(self):
        domain = self.selected_domain.get()
        if domain and messagebox.askyesno("确认", f"清空 {domain} 的所有 Cookie？"):
            self.controller.clear_cookies(domain)
            self.load_domain_data(domain)

    def clear_localstorage(self):
        domain = self.selected_domain.get()
        if domain and messagebox.askyesno("确认", f"清空 {domain} 的所有 LocalStorage？"):
            self.controller.clear_local_storage(domain)
            self.load_domain_data(domain)

    # ================== 域管理 ==================
    def add_domain(self):
        domain = simpledialog.askstring("添加域", "输入域名 (例如 example.com):", parent=self.window)
        if domain:
            self.controller.storage.add_domain(domain)
            self.refresh_domain_list()

    def delete_domain(self):
        sel = self.domain_listbox.curselection()
        if not sel:
            return
        domain = self.domain_listbox.get(sel[0])
        if messagebox.askyesno("确认", f"删除域 [{domain}] 及其所有数据？"):
            # 从浏览器中清除该域的所有数据
            self.controller.clear_cookies(domain)
            self.controller.clear_local_storage(domain)
            # 从永久域名列表中移除
            self.controller.storage.remove_domain(domain)
            self.refresh_domain_list()

    # ================== 全量刷新 ==================
    def refresh_all(self):
        """刷新所有域的显示（重新加载当前选中域）"""
        self.refresh_domain_list()
        sel = self.domain_listbox.curselection()
        if sel:
            domain = self.domain_listbox.get(sel[0])
            self.load_domain_data(domain)

    def reload_page(self):
        self.controller.reload()
