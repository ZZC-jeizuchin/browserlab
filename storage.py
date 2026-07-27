"""
storage.py
Storage 抽象层：管理按域组织的 Cookie 和 LocalStorage。
支持全局写入权限开关、与浏览器同步、独立管理窗口集成。
"""

class Storage:
    def __init__(self):
        # 全局写入权限：True 表示允许网站写入，False 表示禁止网站写入
        self.allow_write = True

        # 按域存储我们手动管理的 Cookie 和 LocalStorage
        # 数据结构：{ "domain": { "cookies": {name: value}, "localStorage": {key: value} } }
        self.domains = {}

    def _ensure_domain(self, domain: str):
        """确保域存在，不存在则创建空记录。"""
        if domain not in self.domains:
            self.domains[domain] = {"cookies": {}, "localStorage": {}}

    # ---- 全局写入权限 ----
    def set_write_permission(self, allow: bool):
        """设置全局写入权限。"""
        self.allow_write = allow

    def get_write_permission(self) -> bool:
        return self.allow_write

    # ---- 按域管理 Cookie ----
    def get_managed_cookies(self, domain: str) -> dict[str, str]:
        self._ensure_domain(domain)
        return dict(self.domains[domain]["cookies"])

    def set_cookie(self, domain: str, name: str, value: str):
        self._ensure_domain(domain)
        self.domains[domain]["cookies"][name] = value

    def delete_cookie(self, domain: str, name: str):
        if domain in self.domains:
            self.domains[domain]["cookies"].pop(name, None)

    def clear_cookies(self, domain: str):
        if domain in self.domains:
            self.domains[domain]["cookies"].clear()

    # ---- 按域管理 LocalStorage ----
    def get_managed_local_storage(self, domain: str) -> dict[str, str]:
        self._ensure_domain(domain)
        return dict(self.domains[domain]["localStorage"])

    def set_local_storage_item(self, domain: str, key: str, value: str):
        self._ensure_domain(domain)
        self.domains[domain]["localStorage"][key] = value

    def delete_local_storage_item(self, domain: str, key: str):
        if domain in self.domains:
            self.domains[domain]["localStorage"].pop(key, None)

    def clear_local_storage(self, domain: str):
        if domain in self.domains:
            self.domains[domain]["localStorage"].clear()

    # ---- 获取所有域列表 ----
    def get_all_domains(self) -> list[str]:
        return list(self.domains.keys())

    # ---- 与浏览器同步 ----
    def import_from_browser(self, domain: str, cookies: dict[str, str],
                            local_storage: dict[str, str]):
        """将浏览器当前的 Storage 快照导入到管理域（保留手动管理值）。"""
        self._ensure_domain(domain)
        managed_c = self.domains[domain]["cookies"]
        managed_ls = self.domains[domain]["localStorage"]
        # 合并：浏览器值覆盖同名未管理键，但我们管理的键不变
        for k, v in cookies.items():
            if k not in managed_c:
                managed_c[k] = v
        for k, v in local_storage.items():
            if k not in managed_ls:
                managed_ls[k] = v

    # ---- 删除整个域 ----
    def delete_domain(self, domain: str):
        if domain in self.domains:
            del self.domains[domain]
