#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学战法回测框架 v2.0
支持多种战法策略的回测验证
"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import HOLDINGS, WATCH_LIST

KLINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kline')

class BacktestEngine:
    def __init__(self, kline_dir=None):
        self.kline_dir = kline_dir or KLINE_DIR
        self.results = {}
        
    def load_kline(self, symbol):
        """加载K线数据"""
        path = os.path.join(self.kline_dir, f"{symbol}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return data.get('data', [])
    
    def calculate_indicators(self, kl):
        """计算技术指标"""
        if len(kl) < 20:
            return None
        
        indicators = []
        for i, bar in enumerate(kl):
            close = float(bar['close'])
            volume = float(bar['volume'])
            
            # 基础指标
            if i > 0:
                prev_close = float(kl[i-1]['close'])
                prev_volume = float(kl[i-1]['volume'])
                vol_ratio = volume / prev_volume if prev_volume > 0 else 0
                pct_chg = (close - prev_close) / prev_close * 100 if prev_close > 0 else 0
            else:
                vol_ratio = 0
                pct_chg = 0
            
            # 移动平均线
            if i >= 4:
                ma5 = sum(float(kl[j]['close']) for j in range(i-4, i+1)) / 5
            else:
                ma5 = close
            if i >= 9:
                ma10 = sum(float(kl[j]['close']) for j in range(i-9, i+1)) / 10
            else:
                ma10 = close
            if i >= 19:
                ma20 = sum(float(kl[j]['close']) for j in range(i-19, i+1)) / 20
            else:
                ma20 = close
            
            indicators.append({
                'date': bar.get('day', '')[:10],
                'close': close,
                'volume': volume,
                'vol_ratio': vol_ratio,
                'pct_chg': pct_chg,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
            })
        
        return indicators
    
    def detect_volume_signals(self, indicators):
        """检测量柱信号"""
        signals = []
        for i, ind in enumerate(indicators):
            # 倍量柱
            if ind['vol_ratio'] >= 1.9 and ind['pct_chg'] > 0:
                signals.append({
                    'type': '倍量柱',
                    'date': ind['date'],
                    'close': ind['close'],
                    'vol_ratio': ind['vol_ratio'],
                    'pct_chg': ind['pct_chg'],
                })
            
            # 缩量柱
            if ind['vol_ratio'] < 0.5 and abs(ind['pct_chg']) < 2:
                signals.append({
                    'type': '缩量柱',
                    'date': ind['date'],
                    'close': ind['close'],
                    'vol_ratio': ind['vol_ratio'],
                    'pct_chg': ind['pct_chg'],
                })
        
        return signals
    
    def backtest_volume_strategy(self, symbol, kl, indicators, signals, lookback=20):
        """回测倍量柱策略"""
        trades = []
        
        for sig in signals:
            if sig['type'] != '倍量柱':
                continue
            
            sig_idx = next(i for i, ind in enumerate(indicators) if ind['date'] == sig['date'])
            
            # 查找后续最高价和最低价
            future_bars = indicators[sig_idx+1:sig_idx+lookback+1]
            if not future_bars:
                continue
            
            future_high = max(b['close'] for b in future_bars)
            future_low = min(b['close'] for b in future_bars)
            last_close = future_bars[-1]['close']
            
            # 计算收益
            entry_price = sig['close']
            profit_pct = (last_close - entry_price) / entry_price * 100
            
            trades.append({
                'signal_date': sig['date'],
                'entry_price': entry_price,
                'exit_price': last_close,
                'profit_pct': profit_pct,
                'max_profit': (future_high - entry_price) / entry_price * 100,
                'max_loss': (future_low - entry_price) / entry_price * 100,
                'holding_days': len(future_bars),
            })
        
        return trades
    
    def run_backtest(self, symbol):
        """运行回测"""
        kl = self.load_kline(symbol)
        if not kl:
            return None
        
        indicators = self.calculate_indicators(kl)
        if not indicators:
            return None
        
        signals = self.detect_volume_signals(indicators)
        trades = self.backtest_volume_strategy(symbol, kl, indicators, signals)
        
        if not trades:
            return None
        
        wins = [t for t in trades if t['profit_pct'] > 0]
        losses = [t for t in trades if t['profit_pct'] <= 0]
        
        return {
            'symbol': symbol,
            'total_signals': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_profit': sum(t['profit_pct'] for t in trades) / len(trades) if trades else 0,
            'avg_win': sum(t['profit_pct'] for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t['profit_pct'] for t in losses) / len(losses) if losses else 0,
            'max_profit_trade': max(t['profit_pct'] for t in trades) if trades else 0,
            'max_loss_trade': min(t['profit_pct'] for t in trades) if trades else 0,
            'trades': trades[-10:],  # 最近10笔交易
        }
    
    def run_all(self):
        """运行所有股票回测"""
        all_results = {}
        
        for symbol in list(HOLDINGS.keys()) + list(WATCH_LIST.keys()):
            result = self.run_backtest(symbol)
            if result:
                all_results[symbol] = result
        
        return all_results
    
    def print_report(self, results):
        """打印回测报告"""
        print("=" * 70)
        print(f"量学战法回测报告 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        if not results:
            print("无回测结果")
            return
        
        for symbol, r in results.items():
            print(f"
{symbol}:")
            print(f"  总信号数: {r['total_signals']}")
            print(f"  盈利次数: {r['wins']}")
            print(f"  亏损次数: {r['losses']}")
            print(f"  胜率: {r['win_rate']:.1f}%")
            print(f"  平均收益: {r['avg_profit']:+.2f}%")
            print(f"  平均盈利: {r['avg_win']:+.2f}%")
            print(f"  平均亏损: {r['avg_loss']:+.2f}%")
            print(f"  最大单笔盈利: {r['max_profit_trade']:+.2f}%")
            print(f"  最大单笔亏损: {r['max_loss_trade']:+.2f}%")
        
        # 汇总统计
        total_signals = sum(r['total_signals'] for r in results.values())
        total_wins = sum(r['wins'] for r in results.values())
        total_losses = sum(r['losses'] for r in results.values())
        overall_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
        overall_avg_profit = sum(r['avg_profit'] * r['total_signals'] for r in results.values()) / total_signals if total_signals > 0 else 0
        
        print(f"
{'=' * 70}")
        print("整体统计:")
        print(f"  总信号数: {total_signals}")
        print(f"  总盈利: {total_wins}")
        print(f"  总亏损: {total_losses}")
        print(f"  整体胜率: {overall_win_rate:.1f}%")
        print(f"  加权平均收益: {overall_avg_profit:+.2f}%")
        print("=" * 70)

def main():
    engine = BacktestEngine()
    results = engine.run_all()
    engine.print_report(results)
    
    # 保存报告
    report_path = '/tmp/liangxue_backtest_detailed.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write(f"量学战法回测报告 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        
        for symbol, r in results.items():
            f.write(f"{symbol}:\n")
            f.write(f"  总信号数: {r[\'total_signals\']}\n")
            f.write(f"  胜率: {r[\'win_rate\']:.1f}%\n")
            f.write(f"  平均收益: {r[\'avg_profit\']:+.2f}%\n\n")
    
    print(f"\n报告已保存: {report_path}")

if __name__ == '__main__':
    main()
