"""
Realtidsbearbetning för Tradingbot
"""
import asyncio
import websockets
import json
from typing import Callable

async def listen_order_updates(ws_url: str, on_update: Callable):
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "auth"}))
        while True:
            msg = await ws.recv()
            on_update(json.loads(msg))

async def process_candles(msg, indicator_func):
    # Bearbeta candlestick-data och kör indikatorer
    indicator_func(msg)

async def start_realtime_loop(ws_url: str, indicator_func):
    await asyncio.gather(
        listen_order_updates(ws_url, lambda msg: process_candles(msg, indicator_func)),
    )
