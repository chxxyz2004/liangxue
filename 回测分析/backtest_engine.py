#!/usr/bin/env python3
"""
量学回测分析引擎
支持：信号识别、支撑压力线检验、胜率统计
"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/workspace/行情数据库')
from config import HOLDINGS, WATCH_LIST, DATA_DIR


def load_kline(symbol):
    """加载K线数据"""
    path = f'{DATA_DIR}/{symbol}.json'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def find_volume_signals(kline_data, lookback=30):
    """识别倍量柱信号"""
    if not kline_data or 'data' not in kline_data:
        return []
    
    signals = []
    data = kline_data['data']
    
    for i in range(max(0, len(data)-lookback), len(data)):
        if i < 1:
            continue
        curr = data[i]
        prev = data[i-1]
        
        # 倍量柱：成交量放大1.9倍以上，且收盘价上涨
        vol_ratio = curr['volume'] / prev['volume'] if prev['volume'] > 0 else 0
        if vol_ratio >= 1.9 and curr['close'] > curr['open']:
            signals.append({
                'date': curr['day'],
                'type': '倍量柱',
                'volume_ratio': round(vol_ratio, 2),
                'price': curr['close'],
                'open': curr['open'],
                'high': curr['high'],
                'low': curr['low'],
                'change_pct': round((curr['close']-curr['open'])/curr['open']*100, 2)
            })
    
    return signals[-10:]


def test_golden_line_support(kline_data, lookback=60):
    """测试黄金线支撑有效性"""
    if not kline_data or 'data' not in kline_data:
        return {'total': 0, 'valid': 0, 'invalid': 0, 'hits': []}
    
    data = kline_data['data']
    results = {'total': 0, 'valid': 0, 'invalid': 0, 'hits': []}
    
    # 找黄金柱（倍量后缩量回调不破）
    for i in range(len(data)-lookback, len(data)):
        if i < 2:
            continue
        
        # 识别潜在黄金柱
        curr = data[i]
        prev = data[i-1]
        
        # 条件：放量阳线后缩量回调不破低点
        if prev['volume'] > curr['volume'] * 1.5 and curr['close'] > curr['open']:
            # 找回调低点
            support = curr['low']
            # 检查后续是否守住支撑
            hit = False
            break_count = 0
            for j in range(i+1, min(i+10, len(data))):
                if data[j]['low'] < support * 0.98:
                    break_count += 1
                if data[j]['close'] > support:
                    hit = True
                    break
            
            results['total'] += 1
            if hit and break_count == 0:
                results['valid'] += 1
                results['hits'].append({
                    'date': curr['day'],
                    'support': round(support, 2),
                    'outcome': '有效'
                })
            else:
                results['invalid'] += 1
                results['hits'].append({
                    'date': curr['day'],
                    'support': round(support, 2),
                    'outcome': '失效'
                })
    
    if results['total'] > 0:
        results['win_rate'] = round(results['valid'] / results['total'] * 100, 1)
    else:
        results['win_rate'] = 0
    
    return results


def test_price_level_test(kline_data, lookback=60):
    """测试价格水平支撑压力有效性"""
    if not kline_data or 'data' not in kline_data:
        return {'total': 0, 'valid': 0, 'invalid': 0, 'hits': []}
    
    data = kline_data['data']
    results = {'total': 0, 'valid': 0, 'invalid': 0, 'hits': []}
    
    # 找近期高低点作为支撑压力
    recent = data[-lookback:]
    highs = [d['high'] for d in recent]
    lows = [d['low'] for d in recent]
    
    # 找关键高点（压力位）
    for i in range(2, len(highs)-2):
        # 局部高点
        if highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and \
           highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
            resistance = highs[i]
            
            # 检查后续是否跌破
            for j in range(i+1, min(i+10, len(data))):
                if data[j]['close'] < resistance * 0.98:
                    results['total'] += 1
                    results['valid'] += 1  # 压力有效（被突破意味着要跌）
                    results['hits'].append({
                        'date': data[i]['day'],
                        'level': round(resistance, 2),
                        'type': '压力',
                        'outcome': '突破'
                    })
                    break
                elif data[j]['high'] > resistance * 1.02:
                    results['total'] += 1
                    results['invalid'] += 1
                    results['hits'].append({
                        'date': data[i]['day'],
                        'level': round(resistance, 2),
                        'type': '压力',
                        'outcome': '未突破'
                    })
                    break
    
    if results['total'] > 0:
        results['win_rate'] = round(results['valid'] / results['total'] * 100, 1)
    else:
        results['win_rate'] = 0
    
    return results


def run_backtest(symbol, strategy='all'):
    """运行完整回测"""
    data = load_kline(symbol)
    if not data:
        return {'error': f'未找到 {symbol} 的数据'}
    
    result = {
        'symbol': symbol,
        'name': data.get('name', symbol),
        'total_days': len(data.get('data', [])),
        'date_range': f"{data['data'][0]['day']} ~ {data['data'][-1]['day']}" if data.get('data') else '',
        'strategies': {}
    }
    
    if strategy in ['all', 'volume']:
        signals = find_volume_signals(data)
        result['strategies']['volume'] = {
            'signals': signals,
            'count': len(signals)
        }
    
    if strategy in ['all', 'golden']:
        golden = test_golden_line_support(data)
        result['strategies']['golden_line'] = golden
    
    if strategy in ['all', 'price']:
        price = test_price_level_test(data)
        result['strategies']['price_level'] = price
    
    return result


def batch_backtest(stocks=None, strategy='all'):
    """批量回测多只股票"""
    if stocks is None:
        stocks = list(HOLDINGS.keys())
    
    all_results = {}
    for sym in stocks:
        result = run_backtest(sym, strategy)
        all_results[sym] = result
    
    return all_results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='sh603516')
    parser.add_argument('--strategy', default='all')
    args = parser.parse_args()
    
    result = run_backtest(args.symbol, args.strategy)
    print(json.dumps(result, ensure_ascii=False, indent=2))
