#!/usr/bin/env python3
"""
技术指标计算脚本
基于日线K线计算MA/RSI/MACD等技术指标，填充indicators表
"""
import sqlite3
import math
from datetime import datetime, timedelta

DB_PATH = '/workspace/行情数据库/liangxue_system.db'


def compute_ma(closes: list, period: int) -> float:
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def compute_ema(closes: list, period: int) -> float:
    if len(closes) < period:
        return 0.0
    k = 2 / (period + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    return ema


def compute_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 0.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(closes: list) -> tuple:
    if len(closes) < 35:
        return (0.0, 0.0, 0.0)
    
    # 计算每日DIF
    macd_list = []
    for i in range(26, len(closes)):
        e12 = compute_ema(closes[:i+1], 12)
        e26 = compute_ema(closes[:i+1], 26)
        macd_list.append(e12 - e26)
    
    if len(macd_list) < 9:
        e12 = compute_ema(closes, 12)
        e26 = compute_ema(closes, 26)
        dif = e12 - e26
        return (dif, 0.0, 0.0)
    
    dif = macd_list[-1]
    dea = compute_ema(macd_list, 9)
    macd_hist = (dif - dea) * 2
    return (dif, dea, macd_hist)


def compute_indicators_for_stock(conn, code: str):
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, close, volume 
        FROM daily_kline 
        WHERE code = ? 
        ORDER BY date DESC
    """, (code,))
    rows = cursor.fetchall()
    
    if len(rows) < 60:
        return 0
    
    # 转换为列表（逆序，最新在前）
    dates = [r[0] for r in reversed(rows)]
    closes = [r[1] for r in reversed(rows)]
    volumes = [r[2] for r in reversed(rows)]
    
    inserted = 0
    for i in range(len(dates)):
        if i < 60:
            continue
        
        date = dates[i]
        
        # 计算各周期均线
        ma5 = compute_ma(closes[:i+1], 5)
        ma10 = compute_ma(closes[:i+1], 10)
        ma20 = compute_ma(closes[:i+1], 20)
        ma60 = compute_ma(closes[:i+1], 60)
        ma120 = compute_ma(closes[:i+1], 120) if i >= 119 else 0
        ma250 = compute_ma(closes[:i+1], 250) if i >= 249 else 0
        
        # 成交量均线
        vol_ma5 = compute_ma(volumes[:i+1], 5)
        vol_ma20 = compute_ma(volumes[:i+1], 20)
        
        # RSI
        rsi = compute_rsi(closes[:i+1], 14)
        
        # MACD
        dif, dea, hist = compute_macd(closes[:i+1])
        
        cursor.execute('''
            INSERT OR REPLACE INTO indicators
            (code, date, ma5, ma10, ma20, ma60, ma120, ma250,
             vol_ma5, vol_ma20, rsi_14, macd, macd_signal, macd_hist, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code, date,
            round(ma5, 3), round(ma10, 3), round(ma20, 3), round(ma60, 3),
            round(ma120, 3), round(ma250, 3),
            round(vol_ma5, 2), round(vol_ma20, 2),
            round(rsi, 2),
            round(dif, 6), round(dea, 6), round(hist, 6),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        inserted += 1
    
    conn.commit()
    return inserted


def main():
    print("=" * 60)
    print("  技术指标计算")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT code FROM daily_kline ORDER BY code")
    codes = [row[0] for row in cursor.fetchall()]
    
    total = 0
    for code in codes:
        count = compute_indicators_for_stock(conn, code)
        if count > 0:
            print(f"  {code}: {count}条指标已计算")
            total += count
    
    conn.close()
    print(f"\n[完成] 共计算 {total} 条技术指标")
    
    # 验证
    conn2 = sqlite3.connect(DB_PATH)
    c = conn2.cursor()
    c.execute("SELECT COUNT(*) FROM indicators")
    print(f"数据库中指标总数: {c.fetchone()[0]}")
    
    c.execute("SELECT code, MAX(date) FROM indicators GROUP BY code ORDER BY code")
    print("最新指标日期:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    conn2.close()


if __name__ == '__main__':
    main()
