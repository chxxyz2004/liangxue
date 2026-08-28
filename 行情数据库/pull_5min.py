#!/usr/bin/env python3
"""
5分钟K线入库脚本
支持两种模式：
  1. 当日采集（默认）：拉取当日48根5分钟K线
  2. 历史回填（--backfill N）：拉取最近N*48根5分钟K线，按日期分文件存储

数据源：新浪财经5分钟K线接口
  symbol: 股票代码（sh600519 / sz000001）
  scale:  K线周期（5=5分钟）
  datalen: 返回根数（48=1天，240=5天，480=10天）
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, '/workspace/行情数据库')

from config import HOLDINGS, WATCH_LIST, INDEXES

STOCKS = {**{k: v.name for k, v in HOLDINGS.items()},
          **{k: v.name for k, v in WATCH_LIST.items()},
          **INDEXES}

BASE_DIR = '/workspace/行情数据库/kline_5min'
os.makedirs(BASE_DIR, exist_ok=True)

SINA_API = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=5&ma=no&datalen={datalen}'


def pull_5min(code, datalen=48):
    """拉取5分钟K线，返回标准化列表（浮点数）"""
    url = SINA_API.format(symbol=code, datalen=datalen)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        raw = urllib.request.urlopen(req, timeout=15).read().decode('gbk')
        bars = json.loads(raw)
        if not bars:
            return []
        # 统一为浮点数
        result = []
        for b in bars:
            result.append({
                'day': b['day'],
                'open': float(b['open']),
                'high': float(b['high']),
                'low': float(b['low']),
                'close': float(b['close']),
                'volume': float(b['volume']),
                'amount': float(b['volume']) * float(b['close']) * 100,  # 成交额(元)
            })
        return result
    except Exception as e:
        print(f'  拉取失败 {code}: {e}')
        return []


def group_by_date(bars):
    """按交易日期分组"""
    groups = defaultdict(list)
    for b in bars:
        date = b['day'][:10]
        groups[date].append(b)
    return groups


def save_daily_file(code, name, date, bars):
    """保存单日5分钟K线文件"""
    filename = f'{code}_{date}.json'
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'code': code,
            'name': name,
            'date': date,
            'bars': bars,
            'count': len(bars)
        }, f, ensure_ascii=False, indent=2)
    return filepath


def backfill(datalen):
    """历史回填模式：拉取大量K线，按日期分文件存储"""
    print(f'5分钟K线历史回填 · datalen={datalen} ({datalen // 48}个交易日)')
    print('=' * 50)

    total_files = 0
    for code, name in STOCKS.items():
        bars = pull_5min(code, datalen)
        if not bars:
            print(f'{name}: 无数据')
            continue

        groups = group_by_date(bars)
        for date, day_bars in sorted(groups.items()):
            filepath = save_daily_file(code, name, date, day_bars)
            total_files += 1

        days = len(groups)
        print(f'{name}: {len(bars)}根K线, {days}天 → {groups and list(groups.keys())[-1]}')

    print('=' * 50)
    print(f'回填完成，共写入 {total_files} 个文件')


def today_pull():
    """当日采集模式"""
    today = datetime.now().strftime('%Y-%m-%d')
    print(f'5分钟K线入库 · {today}')
    print('=' * 50)

    for code, name in STOCKS.items():
        bars = pull_5min(code, 48)
        if not bars:
            print(f'{name}: 无数据')
            continue

        filepath = save_daily_file(code, name, today, bars)
        print(f'{name}: {len(bars)}根K线 → {filepath}')

    print('=' * 50)
    print('入库完成')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--backfill':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        backfill(days * 48)
    else:
        today_pull()


if __name__ == '__main__':
    main()
