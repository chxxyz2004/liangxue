#!/usr/bin/env python3
"""
量学技术指标计算引擎
支持：MA、EMA、MACD、KDJ、RSI、BOLL
"""
import json
import sys
from collections import deque

sys.path.insert(0, '/workspace/行情数据库')
from config import HOLDINGS, WATCH_LIST, DATA_DIR


def load_kline(symbol):
    """加载K线数据"""
    path = f'{DATA_DIR}/{symbol}.json'
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None


def calc_ma(data, period=5):
    """简单移动平均线"""
    closes = [d['close'] for d in data]
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            avg = sum(closes[i-period+1:i+1]) / period
            result.append(round(avg, 2))
    return result


def calc_ema(data, period=12):
    """指数移动平均线"""
    closes = [d['close'] for d in data]
    result = []
    k = 2 / (period + 1)
    for i in range(len(closes)):
        if i == 0:
            result.append(closes[0])
        else:
            val = closes[i] * k + result[-1] * (1 - k)
            result.append(round(val, 2))
    return result


def calc_macd(data, fast=12, slow=26, signal=9):
    """MACD指标"""
    closes = [d['close'] for d in data]
    
    # DIF = EMA(fast) - EMA(slow)
    ema_fast = calc_ema(data, fast)
    ema_slow = calc_ema(data, slow)
    dif = [round(ema_fast[i] - ema_slow[i], 4) if ema_fast[i] and ema_slow[i] else None 
           for i in range(len(closes))]
    
    # DEA = EMA(DIF, signal)
    dif_valid = [(i, v) for i, v in enumerate(dif) if v is not None]
    dea = [None] * len(closes)
    if dif_valid:
        k = 2 / (signal + 1)
        dea[dif_valid[0][0]] = dif[dif_valid[0][0]]
        for j in range(1, len(dif_valid)):
            idx, val = dif_valid[j]
            dea[idx] = round(val * k + dea[dif_valid[j-1][0]] * (1 - k), 4)
    
    # MACD柱 = (DIF - DEA) * 2
    macd_hist = [round((dif[i] - dea[i]) * 2, 4) if dif[i] and dea[i] else None 
                 for i in range(len(closes))]
    
    return {'dif': dif, 'dea': dea, 'macd': macd_hist}


def calc_kdj(data, n=9, m1=3, m2=3):
    """KDJ指标"""
    lows = [d['low'] for d in data]
    highs = [d['high'] for d in data]
    closes = [d['close'] for d in data]
    
    k = [None] * len(data)
    d = [None] * len(data)
    j = [None] * len(data)
    
    rsv = [None] * len(data)
    for i in range(n - 1, len(data)):
        hn = max(highs[i-n+1:i+1])
        ln = min(lows[i-n+1:i+1])
        if hn != ln:
            rsv[i] = (closes[i] - ln) / (hn - ln) * 100
        else:
            rsv[i] = 50
    
    # 初始值
    if rsv[8] is not None:
        k[8] = 50
        d[8] = 50
        j[8] = 50
    
    for i in range(9, len(data)):
        if rsv[i] is not None:
            k[i] = round(2/3 * k[i-1] + 1/3 * rsv[i], 2) if k[i-1] is not None else 50
            d[i] = round(2/3 * d[i-1] + 1/3 * k[i], 2) if d[i-1] is not None else 50
            j[i] = round(3 * k[i] - 2 * d[i], 2)
    
    return {'k': k, 'd': d, 'j': j}


def calc_rsi(data, period=14):
    """RSI指标"""
    closes = [d['close'] for d in data]
    result = [None] * len(closes)
    
    for i in range(period, len(closes)):
        gains = []
        losses = []
        for j in range(i-period+1, i+1):
            change = closes[j] - closes[j-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            result[i] = 100
        else:
            rs = avg_gain / avg_loss
            result[i] = round(100 - 100 / (1 + rs), 2)
    
    return result


def calc_boll(data, period=20, std_dev=2):
    """布林带"""
    closes = [d['close'] for d in data]
    result = {'mid': [], 'upper': [], 'lower': []}
    
    for i in range(len(closes)):
        if i < period - 1:
            result['mid'].append(None)
            result['upper'].append(None)
            result['lower'].append(None)
        else:
            mid = sum(closes[i-period+1:i+1]) / period
            variance = sum((closes[j] - mid) ** 2 for j in range(i-period+1, i+1)) / period
            std = variance ** 0.5
            result['mid'].append(round(mid, 2))
            result['upper'].append(round(mid + std_dev * std, 2))
            result['lower'].append(round(mid - std_dev * std, 2))
    
    return result


def calc_all_indicators(symbol, lookback=60):
    """计算所有技术指标"""
    data = load_kline(symbol)
    if not data or 'data' not in data:
        return None
    
    klines = data['data'][-lookback:]
    info = HOLDINGS.get(symbol, WATCH_LIST.get(symbol, None))
    name = info.name if info else symbol
    
    # 计算各指标
    ma5 = calc_ma(klines, 5)
    ma10 = calc_ma(klines, 10)
    ma20 = calc_ma(klines, 20)
    
    macd = calc_macd(klines)
    kdj = calc_kdj(klines)
    rsi = calc_rsi(klines)
    boll = calc_boll(klines)
    
    # 最新值
    latest = klines[-1]
    
    result = {
        'symbol': symbol,
        'name': name,
        'latest_price': latest['close'],
        'date': latest['day'],
        'indicators': {
            'ma': {
                'ma5': ma5[-1],
                'ma10': ma10[-1],
                'ma20': ma20[-1]
            },
            'macd': {
                'dif': macd['dif'][-1],
                'dea': macd['dea'][-1],
                'macd': macd['macd'][-1]
            },
            'kdj': {
                'k': kdj['k'][-1],
                'd': kdj['d'][-1],
                'j': kdj['j'][-1]
            },
            'rsi': {
                'rsi14': rsi[-1]
            },
            'boll': {
                'upper': boll['upper'][-1],
                'mid': boll['mid'][-1],
                'lower': boll['lower'][-1]
            }
        }
    }
    
    # 判断指标信号
    signals = []
    
    # MA信号
    if ma5[-1] and ma10[-1]:
        if ma5[-1] > ma10[-1] and result['latest_price'] > ma5[-1]:
            signals.append({'type': '均线多头', 'desc': 'MA5上穿MA10，价格在均线上方'})
        elif ma5[-1] < ma10[-1] and result['latest_price'] < ma5[-1]:
            signals.append({'type': '均线空头', 'desc': 'MA5下穿MA10，价格在均线下方'})
    
    # MACD信号
    if macd['dif'][-1] and macd['dea'][-1]:
        if macd['dif'][-1] > macd['dea'][-1] and macd['macd'][-1] > 0:
            signals.append({'type': 'MACD金叉', 'desc': 'DIF上穿DEA，红柱放大'})
        elif macd['dif'][-1] < macd['dea'][-1] and macd['macd'][-1] < 0:
            signals.append({'type': 'MACD死叉', 'desc': 'DIF下穿DEA，绿柱放大'})
    
    # KDJ信号
    if kdj['k'][-1] and kdj['d'][-1]:
        if kdj['k'][-1] < 20 and kdj['j'][-1] < 10:
            signals.append({'type': 'KDJ超卖', 'desc': 'J值低于10，短期超卖'})
        elif kdj['k'][-1] > 80 and kdj['j'][-1] > 100:
            signals.append({'type': 'KDJ超买', 'desc': 'J值高于100，短期超买'})
    
    # RSI信号
    if rsi[-1]:
        if rsi[-1] < 30:
            signals.append({'type': 'RSI超卖', 'desc': f'RSI={rsi[-1]}，超卖区域'})
        elif rsi[-1] > 70:
            signals.append({'type': 'RSI超买', 'desc': f'RSI={rsi[-1]}，超买区域'})
    
    # BOLL信号
    if boll['lower'][-1] and boll['upper'][-1]:
        if result['latest_price'] <= boll['lower'][-1] * 1.02:
            signals.append({'type': '触及下轨', 'desc': '价格触及布林带下轨'})
        elif result['latest_price'] >= boll['upper'][-1] * 0.98:
            signals.append({'type': '触及上轨', 'desc': '价格触及布林带上轨'})
    
    result['signals'] = signals
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='sh603516')
    args = parser.parse_args()
    
    result = calc_all_indicators(args.symbol)
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"未找到 {args.symbol} 的数据")
