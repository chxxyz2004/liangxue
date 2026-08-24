#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学行情数据库 - 读库查询工具
讲课/复盘时直接读取本地数据，不碰网络。
用法：
  python3 query.py                # 查看8股最新状态总览
  python3 query.py 601138 30      # 查工业富联最近30日
  python3 query.py 300394 10      # 查天孚通信最近10日（含量比/涨跌幅）
  python3 query.py 002156 30 2026-08-17  # 查通富，从指定日期开始
  python3 query.py --pos          # 查看8股250日位置百分位
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KLINE_DIR = os.path.join(BASE_DIR, "kline")

# code -> (symbol, name)
INDEX = {
    "601138": ("sh601138", "工业富联"),
    "300476": ("sz300476", "胜宏科技"),
    "300394": ("sz300394", "天孚通信"),
    "603516": ("sh603516", "淳中科技"),
    "002156": ("sz002156", "通富微电"),
    "600584": ("sh600584", "长电科技"),
    "603283": ("sh603283", "赛腾股份"),
    "601231": ("sh601231", "环旭电子"),
}


def load(symbol):
    with open(os.path.join(KLINE_DIR, f"{symbol}.json"), encoding="utf-8") as f:
        return json.load(f)


def fmt_row(d, prev):
    v = d["volume"]
    r = round(v / prev["volume"], 2) if prev else None
    chg = round((d["close"] - prev["close"]) / prev["close"] * 100, 2) if prev else None
    return f"{d['day']} 开{d['open']} 高{d['high']} 低{d['low']} 收{d['close']} 量{v/10000:.0f}万手 量比{r} 涨跌{chg}%"


def overview():
    print("=== 8股最新状态总览 ===")
    for code, (symbol, name) in INDEX.items():
        rec = load(symbol)
        data = rec["data"]
        latest = data[-1]
        prev = data[-2] if len(data) > 1 else None
        print(f"{name}({code}): {fmt_row(latest, prev)}")


def detail(code, n, start=None):
    if code not in INDEX:
        print(f"未找到 {code}，可用：{list(INDEX.keys())}")
        return
    symbol, name = INDEX[code]
    rec = load(symbol)
    data = rec["data"]
    if start:
        data = [d for d in data if d["day"] >= start]
    data = data[-n:]
    print(f"=== {name}({code}) 最近{len(data)}日 ===")
    prev = None
    for d in data:
        print(fmt_row(d, prev))
        prev = d


def position():
    print("=== 8股250日位置百分位 ===")
    for code, (symbol, name) in INDEX.items():
        rec = load(symbol)
        data = rec["data"][-250:]
        cur = data[-1]["close"]
        hi = max(d["high"] for d in data)
        lo = min(d["low"] for d in data)
        pct = (cur - lo) / (hi - lo) * 100 if hi != lo else 0
        zone = "高位区" if pct >= 70 else ("腰部" if pct >= 40 else "低位区")
        print(f"{name}({code}): 当前{cur} 250日高{hi} 低{lo} 百分位{pct:.0f}% [{zone}]")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        overview()
    elif args[0] == "--pos":
        position()
    else:
        code = args[0]
        n = int(args[1]) if len(args) > 1 else 10
        start = args[2] if len(args) > 2 else None
        detail(code, n, start)
