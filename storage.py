"""
storage.py
仅存储永久域名列表，不保存任何 Cookie/LocalStorage 数据。
"""

import json
import os

VISITED_DOMAINS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visited_domains.txt")


class Storage:
    def __init__(self):
        self.visited_domains = self._load_visited_domains()

    def add_domain(self, domain: str):
        if domain not in self.visited_domains:
            self.visited_domains.add(domain)
            self._save()

    def remove_domain(self, domain: str):
        if domain in self.visited_domains:
            self.visited_domains.remove(domain)
            self._save()

    def get_all_domains(self) -> list:
        return sorted(list(self.visited_domains))

    def _load_visited_domains(self):
        if not os.path.exists(VISITED_DOMAINS_FILE):
            return set()
        with open(VISITED_DOMAINS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())

    def _save(self):
        with open(VISITED_DOMAINS_FILE, "w") as f:
            for domain in sorted(self.visited_domains):
                f.write(domain + "\n")
