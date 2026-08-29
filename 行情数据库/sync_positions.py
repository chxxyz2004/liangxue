#!/usr/bin/env python3
"""
持仓同步脚本
将config.py中的持仓信息同步到current_positions表和sim_portfolio表
"""
import sqlite3
import sys
from datetime import datetime

DB_PATH = '/workspace/行情数据库/liangxue_system.db'

sys.path.insert(0, '/workspace/行情数据库')
from config import HOLDINGS


def sync_positions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    synced = 0
    total_value = 0
    total_cost = 0
    
    for code, info in HOLDINGS.items():
        # 获取最新收盘价
        cursor.execute("""
            SELECT date, close FROM daily_kline 
            WHERE code = ? ORDER BY date DESC LIMIT 1
        """, (code,))
        row = cursor.fetchone()
        
        if not row:
            print(f"  [跳过] {info.name}({code}) 无K线数据")
            continue
        
        latest_date, current_price = row
        shares = info.shares
        cost = info.cost or 0
        stop_loss = info.stop_loss
        
        market_value = current_price * shares
        cost_total = cost * shares
        unrealized_pnl = market_value - cost_total
        unrealized_pnl_pct = (unrealized_pnl / cost_total * 100) if cost_total > 0 else 0
        
        # 更新current_positions表
        cursor.execute('''
            INSERT OR REPLACE INTO current_positions
            (code, name, shares, cost_price, current_price, market_value,
             unrealized_pnl, unrealized_pnl_pct, stop_loss, take_profit,
             entry_date, strategy, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code,
            info.name,
            shares,
            cost,
            round(current_price, 2),
            round(market_value, 2),
            round(unrealized_pnl, 2),
            round(unrealized_pnl_pct, 2),
            stop_loss,
            info.take_profit[0] if info.take_profit else None,
            None,
            '模拟盘',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        total_value += market_value
        total_cost += cost_total
        synced += 1
        pnl_sign = '+' if unrealized_pnl >= 0 else ''
        print(f"  {code} {info.name}: 现价{current_price:.2f} 市值{market_value:.0f} 盈亏{pnl_sign}{unrealized_pnl:.0f}")
    
    conn.commit()
    
    # 更新模拟投资组合表（每日快照）
    today = datetime.now().strftime('%Y-%m-%d')
    cash = 50000  # 假设初始现金
    total_equity = total_value + cash
    
    cursor.execute("SELECT id FROM sim_portfolio WHERE date = ?", (today,))
    if cursor.fetchone():
        cursor.execute('''
            UPDATE sim_portfolio SET position_value = ?, total_equity = ?, updated_at = ? 
            WHERE date = ?
        ''', (round(total_value, 2), round(total_equity, 2), datetime.now(), today))
    else:
        cursor.execute('''
            INSERT INTO sim_portfolio
            (date, cash, position_value, total_equity, daily_return,
             max_equity, max_drawdown, total_return, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today, cash, round(total_value, 2),
            round(total_equity, 2), 0.0,
            round(total_equity, 2), 0.0, 0.0,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    conn.commit()
    conn.close()
    
    profit = total_value - total_cost
    profit_pct = (profit / total_cost * 100) if total_cost > 0 else 0
    pnl_sign = '+' if profit >= 0 else ''
    
    print(f"\n[同步完成] {synced}只持仓")
    print(f"总市值: {total_value:,.0f}元")
    print(f"总成本: {total_cost:,.0f}元")
    print(f"总盈亏: {pnl_sign}{profit:,.0f}元 ({pnl_sign}{profit_pct:.2f}%)")
    print(f"模拟账户: 现金{cash} + 持仓{total_value:.0f} = 总值{total_equity:.0f}")
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'profit': profit,
        'profit_pct': profit_pct,
        'count': synced
    }


if __name__ == '__main__':
    sync_positions()
