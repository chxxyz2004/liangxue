#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人量化交易系统 - 数据库初始化脚本
将现有JSON数据迁移到SQLite数据库
"""
import json
import os
import sqlite3
from datetime import datetime

DB_PATH = '/workspace/行情数据库/liangxue_system.db'
KLINE_DIR = '/workspace/行情数据库/kline'
SCHEMA_PATH = '/workspace/行情数据库/schema.sql'


def init_database():
    """初始化数据库，创建表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 读取并执行schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    cursor.executescript(schema)

    print(f"[数据库] 已创建: {DB_PATH}")
    return conn


def insert_stock(conn, code, name, industry=None, chain=None, market=None):
    """插入股票基本信息"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO stocks (code, name, industry, chain, market)
        VALUES (?, ?, ?, ?, ?)
    ''', (code, name, industry, chain, market))
    conn.commit()


def insert_daily_kline(conn, code, kl_data):
    """插入日线K线数据"""
    cursor = conn.cursor()
    inserted = 0
    for bar in kl_data:
        cursor.execute('''
            INSERT OR REPLACE INTO daily_kline 
            (code, date, open, high, low, close, volume, amount, turnover_rate, pe_ttm, pb, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code,
            bar.get('day', '')[:10],
            bar.get('open', 0),
            bar.get('high', 0),
            bar.get('low', 0),
            bar.get('close', 0),
            bar.get('volume', 0),
            bar.get('amount', 0),
            bar.get('turnover_rate', 0),
            bar.get('pe_ttm', 0),
            bar.get('pb', 0),
            'tencent'
        ))
        inserted += 1
    conn.commit()
    return inserted


def migrate_json_to_sqlite():
    """从JSON文件迁移数据到SQLite"""
    conn = init_database()
    cursor = conn.cursor()

    # 股票信息映射
    stocks = {
        'sh601138': {'name': '工业富联', 'chain': '英伟达', 'market': '主板'},
        'sz300476': {'name': '胜宏科技', 'chain': '英伟达', 'market': '创业板'},
        'sz300394': {'name': '天孚通信', 'chain': '英伟达', 'market': '创业板'},
        'sh603516': {'name': '淳中科技', 'chain': '英伟达', 'market': '主板'},
        'sz002156': {'name': '通富微电', 'chain': '长鑫', 'market': '创业板'},
        'sh600584': {'name': '长电科技', 'chain': '长鑫', 'market': '主板'},
        'sh603283': {'name': '赛腾股份', 'chain': '特斯拉', 'market': '主板'},
        'sh601231': {'name': '环旭电子', 'chain': '华为', 'market': '主板'},
    }

    # 插入股票信息
    for code, info in stocks.items():
        insert_stock(conn, code, info['name'], chain=info['chain'], market=info['market'])
    print(f"[迁移] 已插入 {len(stocks)} 只股票信息")

    # 迁移K线数据
    total_klines = 0
    for code in stocks.keys():
        path = os.path.join(KLINE_DIR, f'{code}.json')
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            kl_data = data.get('data', [])
            inserted = insert_daily_kline(conn, code, kl_data)
            total_klines += inserted
            print(f"[迁移] {code} {inserted}根K线")

    print(f"\n[迁移完成] 共迁移 {total_klines} 根K线数据")

    # 验证数据
    cursor.execute("SELECT COUNT(*) FROM daily_kline")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stocks")
    stock_count = cursor.fetchone()[0]
    print(f"[验证] 数据库中共 {count} 条K线记录，{stock_count} 只股票")

    conn.close()
    return True


def get_database_stats(conn=None):
    """获取数据库统计信息"""
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stats = {}
    tables = ['stocks', 'daily_kline', 'kline_5min', 'indicators', 
              'liangxue_signals', 'sim_trades', 'sim_portfolio', 
              'backtest_results', 'current_positions', 'system_logs']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except:
            stats[table] = 0

    return stats


if __name__ == '__main__':
    print("=" * 60)
    print("  个人量化交易系统 - 数据库初始化")
    print("=" * 60)
    
    migrate_json_to_sqlite()
    
    conn = sqlite3.connect(DB_PATH)
    stats = get_database_stats(conn)
    conn.close()
    
    print("\n=== 数据库统计 ===")
    for table, count in stats.items():
        print(f"  {table}: {count} 条记录")
