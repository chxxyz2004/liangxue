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

# 关注股票池（8只算力产业链个股，用腾讯前复权接口）
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

# 大盘指数（无复权，用新浪接口）
INDEXES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
}

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
