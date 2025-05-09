"""
Prestandaanalys för Tradingbot
"""
import csv
from typing import List, Dict

def parse_order_log(path: str) -> List[Dict]:
    data = []
    with open(path) as f:
        for row in csv.DictReader(f):
            if row.get("status") in ("EXECUTED", "CANCELED"):
                data.append(row)
    return data

def compute_summary_statistics(data: List[Dict]) -> Dict:
    # Dummy-statistik: summera vinst/förlust, win-rate, volym
    stats = {"pnl": 0, "win_rate": 0, "volume": 0}
    return stats

def format_daily_performance(stats: Dict) -> Dict:
    # Strukturera daglig prestanda
    return {"date": "2025-05-09", **stats}

def export_performance_to_csv(data: List[Dict], path: str):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
