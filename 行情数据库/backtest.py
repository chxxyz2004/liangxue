#!/usr/bin/env python3
"""
量学信号回测框架
用于验证信号规则的有效性和参数优化
"""
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

class BacktestEngine:
    def __init__(self, kline_dir='/workspace/行情数据库/kline'):
        self.kline_dir = kline_dir
        self.results = defaultdict(list)
    
    def load_data(self, code):
        filepath = os.path.join(self.kline_dir, f'{code}.json')
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return data.get('data', [])
    
    def calculate_indicators(self, bars):
        if len(bars) < 20:
            return None
        
        indicators = []
        for i, bar in enumerate(bars):
            close = float(bar['close'])
            volume = int(bar['volume'])
            
            if i > 0:
                prev_close = float(bars[i-1]['close'])
                prev_volume = int(bars[i-1]['volume'])
                vol_ratio = volume / prev_volume if prev_volume > 0 else 0
                pct_chg = (close - prev_close) / prev_close * 100 if prev_close > 0 else 0
            else:
                vol_ratio = 0
                pct_chg = 0
            
            if i >= 9:
                ma5 = sum(float(bars[j]['close']) for j in range(i-4, i+1)) / 5
                ma10 = sum(float(bars[j]['close']) for j in range(i-9, i+1)) / 10
                ma20 = sum(float(bars[j]['close']) for j in range(i-19, i+1)) / 20
            else:
                ma5 = ma10 = ma20 = close
            
            indicators.append({
                'date': bar.get('day', '').split(' ')[0],
                'close': close,
                'volume': volume,
                'vol_ratio': vol_ratio,
                'pct_chg': pct_chg,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
            })
        
        return indicators
    
    def detect_signals(self, indicators):
        signals = []
        
        for i, ind in enumerate(indicators):
            if ind['vol_ratio'] >= 2.0 and ind['pct_chg'] > 0:
                signals.append({
                    'type': '倍量柱',
                    'date': ind['date'],
                    'close': ind['close'],
                    'vol_ratio': ind['vol_ratio'],
                    'pct_chg': ind['pct_chg'],
                    'success': None
                })
            
            if ind['vol_ratio'] < 0.5 and abs(ind['pct_chg']) < 2.0:
                signals.append({
                    'type': '缩量柱',
                    'date': ind['date'],
                    'close': ind['close'],
                    'vol_ratio': ind['vol_ratio'],
                    'pct_chg': ind['pct_chg'],
                    'success': None
                })
        
        return signals
    
    def verify_signal(self, signals, bars, lookforward=5):
        for signal in signals:
            date = signal['date']
            
            idx = None
            for i, bar in enumerate(bars):
                if bar.get('day', '').startswith(date):
                    idx = i
                    break
            
            if idx is None or idx + lookforward >= len(bars):
                signal['success'] = 'unknown'
                continue
            
            entry_price = signal['close']
            max_gain = 0
            max_loss = 0
            
            for j in range(idx + 1, min(idx + lookforward + 1, len(bars))):
                close = float(bars[j]['close'])
                gain = (close - entry_price) / entry_price * 100
                
                if gain > max_gain:
                    max_gain = gain
                if gain < max_loss:
                    max_loss = gain
            
            if max_gain >= 3.0:
                signal['success'] = 'win'
                signal['max_gain'] = max_gain
                signal['max_loss'] = max_loss
            elif max_loss <= -3.0:
                signal['success'] = 'loss'
                signal['max_gain'] = max_gain
                signal['max_loss'] = max_loss
            else:
                signal['success'] = 'neutral'
                signal['max_gain'] = max_gain
                signal['max_loss'] = max_loss
        
        return signals
    
    def run_backtest(self, codes, lookforward=5):
        all_results = {}
        
        for code in codes:
            bars = self.load_data(code)
            if not bars:
                continue
            
            indicators = self.calculate_indicators(bars)
            if not indicators:
                continue
            
            signals = self.detect_signals(indicators)
            signals = self.verify_signal(signals, bars, lookforward)
            
            wins = len([s for s in signals if s['success'] == 'win'])
            losses = len([s for s in signals if s['success'] == 'loss'])
            neutrals = len([s for s in signals if s['success'] == 'neutral'])
            unknowns = len([s for s in signals if s['success'] == 'unknown'])
            
            total = wins + losses + neutrals
            win_rate = wins / total * 100 if total > 0 else 0
            
            all_results[code] = {
                'total_signals': len(signals),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'signals': signals
            }
        
        return all_results
    
    def generate_report(self, results):
        report = []
        report.append(f"回测报告 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        
        total_signals = 0
        total_wins = 0
        total_losses = 0
        
        for code, data in results.items():
            report.append(f"\n{code}:")
            report.append(f"  总信号数: {data['total_signals']}")
            report.append(f"  盈利信号: {data['wins']}")
            report.append(f"  亏损信号: {data['losses']}")
            report.append(f"  胜率: {data['win_rate']:.1f}%")
            
            total_signals += data['total_signals']
            total_wins += data['wins']
            total_losses += data['losses']
        
        overall_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
        report.append(f"\n整体统计:")
        report.append(f"  总信号数: {total_signals}")
        report.append(f"  总盈利: {total_wins}")
        report.append(f"  总亏损: {total_losses}")
        report.append(f"  整体胜率: {overall_win_rate:.1f}%")
        
        return '\n'.join(report)

def main():
    print("量学信号回测框架")
    print("=" * 60)
    
    test_codes = ['sh603516', 'sh601138', 'sz300476', 'sz300394', 'sh600584']
    
    engine = BacktestEngine()
    results = engine.run_backtest(test_codes, lookforward=5)
    
    print(engine.generate_report(results))
    
    output_file = f'/tmp/liangxue_backtest_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'
    with open(output_file, 'w') as f:
        f.write(engine.generate_report(results))
    print(f"\n报告已保存: {output_file}")

if __name__ == '__main__':
    sys.exit(main())
