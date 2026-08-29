#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学战法回测框架 v2.0
避免未来函数，使用正确的回测逻辑
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import HOLDINGS, WATCH_LIST

KLINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kline')

class BacktestEngine:
    def __init__(self):
        self.kline_dir = KLINE_DIR
        
    def load_kline(self, symbol):
        path = os.path.join(self.kline_dir, f"{symbol}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return data.get('data', [])
    
    def run_backtest(self, symbol):
        kl = self.load_kline(symbol)
        if not kl or len(kl) < 50:
            return None
        
        # 检测倍量柱信号
        signals = []
        for i in range(1, len(kl) - 20):  # 预留20根K线作为观察期
            vol_ratio = kl[i]['volume'] / kl[i-1]['volume'] if kl[i-1]['volume'] > 0 else 0
            pct_chg = (kl[i]['close'] - kl[i-1]['close']) / kl[i-1]['close'] * 100
            
            if vol_ratio >= 1.9 and pct_chg > 0:
                signals.append({
                    'index': i,
                    'date': kl[i]['day'][:10],
                    'price': kl[i]['close'],
                    'vol_ratio': vol_ratio,
                })
        
        if not signals:
            return None
        
        # 回测每笔交易（持有20天）
        trades = []
        for sig in signals:
            sig_idx = sig['index']
            exit_idx = min(sig_idx + 20, len(kl) - 1)
            exit_price = kl[exit_idx]['close']
            profit_pct = (exit_price - sig['price']) / sig['price'] * 100
            
            trades.append({
                'date': sig['date'],
                'profit_pct': profit_pct,
            })
        
        if not trades:
            return None
        
        wins = [t for t in trades if t['profit_pct'] > 0]
        losses = [t for t in trades if t['profit_pct'] <= 0]
        
        return {
            'symbol': symbol,
            'total': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades) * 100,
            'avg_profit': sum(t['profit_pct'] for t in trades) / len(trades),
            'avg_win': sum(t['profit_pct'] for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t['profit_pct'] for t in losses) / len(losses) if losses else 0,
        }
    
    def run_all(self):
        results = {}
        for symbol in list(HOLDINGS.keys()) + list(WATCH_LIST.keys()):
            result = self.run_backtest(symbol)
            if result:
                results[symbol] = result
        return results

def main():
    engine = BacktestEngine()
    results = engine.run_all()
    
    print("=" * 70)
    print(f"量学战法回测报告 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    for symbol, r in results.items():
        print(f"\n{symbol}:")
        print(f"  总信号数: {r['total']}")
        print(f"  胜率: {r['win_rate']:.1f}%")
        print(f"  平均收益: {r['avg_profit']:+.2f}%")
        print(f"  平均盈利: {r['avg_win']:+.2f}%")
        print(f"  平均亏损: {r['avg_loss']:+.2f}%")
    
    total = sum(r['total'] for r in results.values())
    wins = sum(r['wins'] for r in results.values())
    avg_profit = sum(r['avg_profit'] * r['total'] for r in results.values()) / total if total > 0 else 0
    
    print(f"\n{'=' * 70}")
    print("整体统计:")
    print(f"  总信号数: {total}")
    print(f"  整体胜率: {wins/total*100:.1f}%")
    print(f"  加权平均收益: {avg_profit:+.2f}%")
    print("=" * 70)

if __name__ == '__main__':
    main()
