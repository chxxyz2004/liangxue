#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学行情数据库 - 数据拉取与更新脚本
数据源：
  8只股票：腾讯证券前复权日K接口（web.ifzq.gtimg.cn fqkline qfq）
           —— 与看盘软件（同花顺/东财/雪球）默认口径一致，除权日前的历史价格已按分红送转调整
  3个指数：新浪财经日K行情接口（指数无除权问题，不复权即准确）
更新策略：每次全量拉取，覆盖本地文件
用法：
  python3 update_data.py            # 全量更新8股+3指数
  python3 update_data.py 2026-08-24 # 指定数据截止日（校验用）
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 统一配置中心（股票池 = HOLDINGS + WATCH_LIST，禁止硬编码）
from config import HOLDINGS, WATCH_LIST, INDEXES

# 股票池（持仓 + 关注，用腾讯前复权接口）
STOCKS = {**{k: v.name for k, v in HOLDINGS.items()},
          **{k: v.name for k, v in WATCH_LIST.items()}}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KLINE_DIR = os.path.join(BASE_DIR, "kline")
META_FILE = os.path.join(BASE_DIR, "meta.json")

N_DAYS = 300  # 目标交易日数量

TENCENT_API = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{datalen},qfq"
SINA_API = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={datalen}"


def fetch(url, retries=3, timeout=20):
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


def fetch_tencent_qfq(symbol, datalen):
    """腾讯前复权日K。返回 [day, open, close, high, low, volume, ...] 列表"""
    url = TENCENT_API.format(symbol=symbol, datalen=datalen)
    raw = fetch(url)
    data = json.loads(raw)["data"][symbol]
    key = "qfqday" if "qfqday" in data else "day"
    out = []
    for r in data[key]:
        out.append({
            "day": r[0],
            "open": float(r[1]),
            "high": float(r[3]),
            "low": float(r[4]),
            "close": float(r[2]),
            "volume": float(r[5]),  # 单位：手
            "amount": float(r[5]) * float(r[2]) * 100,  # 成交额(元)【估算】= 成交量(手)×收盘价×100，腾讯fqkline接口不含真实成交额
        })
    return out


def fetch_sina_kline(symbol, datalen):
    """新浪日K（用于指数）。返回字典列表，volume单位：手"""
    url = SINA_API.format(symbol=symbol, datalen=datalen)
    raw = fetch(url).strip()
    if raw.startswith("var"):
        raw = raw[raw.index("=") + 1:].strip()
    data = json.loads(raw)
    out = []
    for d in data:
        out.append({
            "day": d["day"],
            "open": float(d["open"]),
            "high": float(d["high"]),
            "low": float(d["low"]),
            "close": float(d["close"]),
            "volume": float(d["volume"]),
            "amount": float(d["volume"]) * float(d["close"]) * 100,  # 成交额(元)【估算】= 成交量(手)×收盘价×100，新浪kline接口不含真实成交额
        })
    return out


def main():
    if len(sys.argv) > 1:
        expected_date = sys.argv[1]
    else:
        expected_date = None

    os.makedirs(KLINE_DIR, exist_ok=True)
    meta = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "fq_policy": "股票=腾讯前复权qfq，指数=新浪不复权", "stocks": {}, "indexes": {}}

    print(f"=== 更新 {len(STOCKS)} 只股票(腾讯前复权) + {len(INDEXES)} 个指数(新浪不复权) ===")
    all_ok = True
    for symbol, name in STOCKS.items():
        try:
            data = fetch_tencent_qfq(symbol, N_DAYS + 60)
            latest = data[-1]["day"]
            fpath = os.path.join(KLINE_DIR, f"{symbol}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump({"source": "腾讯证券前复权日K接口(与看盘软件一致)", "symbol": symbol, "name": name, "fq": "qfq", "data": data}, f, ensure_ascii=False, indent=1)
            meta["stocks"][symbol] = {"name": name, "count": len(data), "latest_day": latest}
            print(f"  ✓ {name}({symbol})  {len(data)}日 最新:{latest}")
        except Exception as e:
            all_ok = False
            print(f"  ✗ {name}({symbol}) 失败: {e}")

    for symbol, name in INDEXES.items():
        try:
            data = fetch_sina_kline(symbol, N_DAYS + 60)
            latest = data[-1]["day"]
            fpath = os.path.join(KLINE_DIR, f"{symbol}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump({"source": "新浪财经日K行情接口(指数无复权)", "symbol": symbol, "name": name, "fq": "none", "data": data}, f, ensure_ascii=False, indent=1)
            meta["indexes"][symbol] = {"name": name, "count": len(data), "latest_day": latest}
            print(f"  ✓ {name}({symbol})  {len(data)}日 最新:{latest}")
        except Exception as e:
            all_ok = False
            print(f"  ✗ {name}({symbol}) 失败: {e}")

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n=== 更新完成 ===")
    if expected_date:
        print(f"期望最新日期: {expected_date}")
        for symbol, info in {**meta["stocks"], **meta["indexes"]}.items():
            flag = "✓" if info["latest_day"] == expected_date else "✗"
            print(f"  {flag} {info['name']}: 最新 {info['latest_day']}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
