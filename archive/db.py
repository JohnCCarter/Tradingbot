"""
Datapersistens och DB för Tradingbot
"""
from typing import Dict, Any, List
import os
import json

class SupabaseClient:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        # Initiera riktig Supabase-klient här

    def insert_log(self, log: Dict[str, Any]):
        pass
    def get_order_history(self) -> List[Dict]:
        return []
    def insert_backtest(self, data: Dict[str, Any]):
        pass

class LocalFallback:
    def __init__(self, path="order_status_log.txt"):
        self.path = path
    def write(self, entry: Dict[str, Any]):
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    def read(self) -> List[Dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f]
