#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学行情数据库 - 数据拉取与更新脚本
数据源：新浪财经官方日K行情接口
更新策略：每次全量拉取N日数据，覆盖本地文件（接口轻量，8只股票一次拉取很快）
用法：
  python3 update_data.py          # 全量更新8只股票
  python3 update_data.py 2026-08-24  # 指定数据截止日（主要用于校验）
"""
import json
import os
import sys
import time
import urllib.request

# 关注股票池（8只算力产业链个股）
STOCKS = {
    "sh601138": "工业富联",
    "sz300476": "胜宏科技",
    "sz300394": "天孚通信",
    "sh603516": "淳中科技",
    "sz002156": "通富微电",
    "sh600584": "长电科技",
    "sh603283": "赛腾股份",
    "sh601231": "环旭电子",
}

# 大盘指数（用于复盘背景）
INDEXES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KLINE_DIR = os.path.join(BASE_DIR, "kline")
META_FILE = os.path.join(BASE_DIR, "meta.json")

N_DAYS = 300  # 拉取交易日数量（约覆盖一年）

API_URL = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={datalen}"


def fetch(url, retries=3, timeout=20):
    """带重试的请求"""
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"请求失败: {url} -> {last_err}")


def normalize(raw):
    """新浪返回的可能是 var xxx= 包裹的 JSON，也可能是裸数组"""
    raw = raw.strip()
    if raw.startswith("var"):
        raw = raw[raw.index("=") + 1:].strip()
    return json.loads(raw)


def fetch_kline(symbol, datalen):
    url = API_URL.format(symbol=symbol, datalen=datalen)
    raw = fetch(url)
    data = normalize(raw)
    # 统一字段名与类型
    out = []
    for d in data:
        out.append({
            "day": d["day"],
            "open": float(d["open"]),
            "high": float(d["high"]),
            "low": float(d["low"]),
            "close": float(d["close"]),
            "volume": float(d["volume"]),
        })
    return out


def main():
    if len(sys.argv) > 1:
        expected_date = sys.argv[1]
    else:
        expected_date = None

    os.makedirs(KLINE_DIR, exist_ok=True)
    meta = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "stocks": {}, "indexes": {}}

    print(f"=== 更新 {len(STOCKS)} 只股票 + {len(INDEXES)} 个指数 ===")
    for symbol, name in {**STOCKS, **INDEXES}.items():
        try:
            data = fetch_kline(symbol, N_DAYS)
            latest = data[-1]["day"]
            fpath = os.path.join(KLINE_DIR, f"{symbol}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump({"source": "新浪财经日K行情接口", "symbol": symbol, "name": name, "data": data}, f, ensure_ascii=False, indent=1)
            meta["stocks"][symbol] = {"name": name, "count": len(data), "latest_day": latest}
            print(f"  ✓ {name}({symbol})  {len(data)}日 最新:{latest}")
        except Exception as e:
            print(f"  ✗ {name}({symbol}) 失败: {e}")

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n=== 更新完成 ===")
    if expected_date:
        print(f"期望最新日期: {expected_date}")
        for symbol, info in meta["stocks"].items():
            flag = "✓" if info["latest_day"] == expected_date else "✗"
            print(f"  {flag} {info['name']}: 最新 {info['latest_day']}")


if __name__ == "__main__":
    main()
