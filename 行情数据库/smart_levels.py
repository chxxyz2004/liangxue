#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学智能点位计算器 v1.0
自动识别重要价位、计算关键指标、生成买卖建议
"""
import json
import os
import sys
import math
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KLINE_DIR = os.path.join(BASE_DIR, "kline")

# 股票索引
INDEX = {
    "601138": ("sh601138", "工业富联"),
    "300476": ("sz300476", "胜宏科技"),
    "300394": ("sz300394", "天孚通信"),
    "603516": ("sh603516", "淳中科技"),
    "002156": ("sz002156", "通富微电"),
    "600584": ("sh600584", "长电科技"),
    "603283": ("sh603283", "赛腾股份"),
    "601231": ("sh601231", "环旭电子"),
}

def load(symbol):
    with open(os.path.join(KLINE_DIR, f"{symbol}.json"), encoding="utf-8") as f:
        return json.load(f)

def round_up(n, decimals=2):
    """向上取整到指定小数位"""
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier

def round_down(n, decimals=2):
    """向下取整到指定小数位"""
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

def find_integer_levels(price, range_margin=5):
    """找附近整数关口"""
    levels = []
    lower = math.floor(price - range_margin)
    upper = math.ceil(price + range_margin)
    for level in range(lower, upper + 1):
        if level % 10 == 0 or level % 5 == 0:
            levels.append(float(level))
    return sorted(set(levels))

def find_key_levels(data, lookback=60):
    """找关键价位：前高、前低、密集成交区"""
    recent = data[-lookback:] if len(data) > lookback else data
    
    highs = [d['high'] for d in recent]
    lows = [d['low'] for d in recent]
    closes = [d['close'] for d in recent]
    volumes = [d['volume'] for d in recent]
    
    # 前高前低（近60日）
    prev_high = max(highs)
    prev_low = min(lows)
    
    # 近期最高/最低收盘
    recent_high_close = max(closes)
    recent_low_close = min(closes)
    
    # 密集成交区（成交量前20%的价格区间）
    vol_threshold = sorted(volumes, reverse=True)[:max(1, len(volumes)//5)]
    high_vol_prices = []
    for i, v in enumerate(volumes):
        if v in vol_threshold:
            high_vol_prices.append((closes[i] + highs[i]) / 2)
    
    # 聚类密集成交区（间隔<2元视为同一区域）
    dense_zones = []
    if high_vol_prices:
        high_vol_prices.sort()
        current_zone = [high_vol_prices[0]]
        for p in high_vol_prices[1:]:
            if p - current_zone[-1] < 2:
                current_zone.append(p)
            else:
                if len(current_zone) >= 2:
                    dense_zones.append({
                        'center': sum(current_zone) / len(current_zone),
                        'range': (min(current_zone), max(current_zone)),
                        'volume': sum(volumes[:len(current_zone)]) / len(current_zone)
                    })
                current_zone = [p]
        if len(current_zone) >= 2:
            dense_zones.append({
                'center': sum(current_zone) / len(current_zone),
                'range': (min(current_zone), max(current_zone)),
                'volume': sum(volumes[-len(current_zone):]) / len(current_zone)
            })
    
    return {
        'prev_high': prev_high,
        'prev_low': prev_low,
        'recent_high_close': recent_high_close,
        'recent_low_close': recent_low_close,
        'dense_zones': dense_zones[:3]  # 取前3个密集成交区
    }

def calc_moving_averages(data, periods=None):
    """计算移动平均线"""
    if periods is None:
        periods = [5, 10, 20, 60, 120, 250]
    
    closes = [d['close'] for d in data]
    result = {}
    
    for period in periods:
        if len(closes) >= period:
            avg = sum(closes[-period:]) / period
            result[f'MA{period}'] = round(avg, 2)
        else:
            result[f'MA{period}'] = None
    
    return result

def calc_volatility(data, period=20):
    """计算波动率（近N日收盘价标准差）"""
    if len(data) < period:
        return None
    
    closes = [d['close'] for d in data[-period:]]
    mean = sum(closes) / period
    variance = sum((c - mean) ** 2 for c in closes) / period
    std = math.sqrt(variance)
    
    return {
        'std': round(std, 2),
        'percent': round(std / mean * 100, 2),
        'stop_loss': round(mean - 2 * std, 2)  # 波动率止损位
    }

def calc_position_percentile(data, window=250):
    """计算当前位置百分位"""
    if len(data) < 10:
        return None
    
    lookback = min(window, len(data))
    prices = [d['close'] for d in data[-lookback:]]
    current = prices[-1]
    min_price = min(prices)
    max_price = max(prices)
    
    if max_price == min_price:
        return 50.0
    
    percentile = (current - min_price) / (max_price - min_price) * 100
    return round(percentile, 1)

def calc_kelly(win_rate, win_loss_ratio):
    """凯利公式计算最优仓位"""
    loss_rate = 1 - win_rate
    kelly = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
    return round(min(max(kelly * 100, 0), 30), 1)  # 限制在0-30%

def analyze_stock(code, days=60):
    """综合分析单只股票"""
    if code not in INDEX:
        return None
    
    symbol, name = INDEX[code]
    rec = load(symbol)
    data = rec['data']
    
    current = data[-1]
    prev = data[-2] if len(data) > 1 else None
    
    # 基础指标
    price = current['close']
    volume = current['volume']
    prev_volume = prev['volume'] if prev else None
    vol_ratio = round(volume / prev_volume, 2) if prev_volume else None
    chg = round((price - prev['close']) / prev['close'] * 100, 2) if prev else None
    
    # 位置百分位
    percentile = calc_position_percentile(data)
    
    # 均线系统
    mas = calc_moving_averages(data)
    
    # 波动率
    vol = calc_volatility(data)
    
    # 关键价位
    keys = find_key_levels(data, days)
    
    # 整数关口
    int_levels = find_integer_levels(price)
    
    # 综合判断
    position = '低位区' if percentile < 40 else ('腰部区' if percentile < 70 else '高位区')
    
    # 量价关系判断
    if vol_ratio and chg:
        if vol_ratio > 1.5 and chg > 3:
            volume_signal = '放量上涨（健康）'
        elif vol_ratio > 1.5 and chg < -3:
            volume_signal = '放量下跌（危险）'
        elif vol_ratio < 0.7 and chg < 0:
            volume_signal = '缩量下跌（观望）'
        elif vol_ratio < 0.7 and chg > 0:
            volume_signal = '缩量上涨（弱势）'
        else:
            volume_signal = '量能平淡'
    else:
        volume_signal = '数据不足'
    
    # 均线排列
    ma_status = '无明确趋势'
    if mas.get('MA5') and mas.get('MA20'):
        if mas['MA5'] > mas['MA20']:
            ma_status = '短期均线多头'
        elif mas['MA5'] < mas['MA20']:
            ma_status = '短期均线空头'
    
    # 生死线建议（取前低和密集成交区下沿）
    life_line = min(keys['prev_low'], keys['recent_low_close'] if keys['recent_low_close'] < keys['prev_low'] else keys['prev_low'])
    
    # 综合评分（0-100，越高越好）
    score = 50  # 基准分
    if percentile < 30:
        score += 15  # 低位加分
    elif percentile > 70:
        score -= 15  # 高位减分
    
    if volume_signal == '放量上涨（健康）':
        score += 10
    elif volume_signal == '放量下跌（危险）':
        score -= 15
    
    if ma_status == '短期均线多头':
        score += 5
    elif ma_status == '短期均线空头':
        score -= 5
    
    score = max(0, min(100, score))
    
    return {
        'code': code,
        'name': name,
        'price': price,
        'chg': chg,
        'vol_ratio': vol_ratio,
        'percentile': percentile,
        'position': position,
        'volume_signal': volume_signal,
        'ma_status': ma_status,
        'mas': mas,
        'volatility': vol,
        'key_levels': keys,
        'integer_levels': int_levels,
        'life_line': life_line,
        'score': score,
        'kelly_default': calc_kelly(0.4, 1.5)  # 冷启动默认值
    }

def generate_report(codes=None):
    """生成综合分析报告"""
    if codes is None:
        codes = list(INDEX.keys())
    
    results = []
    for code in codes:
        r = analyze_stock(code)
        if r:
            results.append(r)
    
    # 排序（按评分降序）
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results

def print_report(results):
    """打印报告"""
    print("=" * 80)
    print("量学智能点位分析报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    for r in results:
        print(f"\n【{r['name']}({r['code']})】")
        print(f"  现价: {r['price']}元 | 涨跌: {r['chg']}% | 量比: {r['vol_ratio']}")
        print(f"  位置: {r['position']} ({r['percentile']}%) | 综合评分: {r['score']}/100")
        print(f"  量价信号: {r['volume_signal']}")
        print(f"  均线状态: {r['ma_status']}")
        
        # 关键价位
        print(f"  关键价位:")
        print(f"    前高: {r['key_levels']['prev_high']} | 前低: {r['key_levels']['prev_low']}")
        print(f"    近60日高收: {r['key_levels']['recent_high_close']} | 近60日低收: {r['key_levels']['recent_low_close']}")
        
        # 整数关口
        int_near = [x for x in r['integer_levels'] if abs(x - r['price']) < 3]
        if int_near:
            print(f"    附近整数关: {', '.join(map(str, int_near))}")
        
        # 密集成交区
        if r['key_levels']['dense_zones']:
            print(f"    密集成交区:")
            for i, zone in enumerate(r['key_levels']['dense_zones'], 1):
                print(f"      区域{i}: {zone['range'][0]:.2f}-{zone['range'][1]:.2f} (均价{zone['center']:.2f})")
        
        # 生死线
        print(f"    建议生死线: {r['life_line']:.2f} (跌破需警惕)")
        
        # 波动率止损
        if r['volatility']:
            print(f"    波动率止损: {r['volatility']['stop_loss']:.2f} (入场价-2×20日波动率)")
            print(f"    20日波动率: {r['volatility']['std']:.2f}元 ({r['volatility']['percent']}%)")
        
        # 均线
        mas = r['mas']
        if mas.get('MA5') and mas.get('MA20'):
            print(f"    MA5: {mas['MA5']} | MA20: {mas['MA20']} | 差值: {mas['MA5'] - mas['MA20']:.2f}")
        
        # 凯利建议
        print(f"    凯利默认仓位: {r['kelly_default']}% (无回测数据时观察仓)")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 smart_levels.py              # 8股综合报告")
        print("  python3 smart_levels.py 603516       # 单只股票详细分析")
        print("  python3 smart_levels.py --pos        # 仅显示位置百分位")
        print("  python3 smart_levels.py --help       # 显示帮助")
        sys.exit(1)
    
    if sys.argv[1] == '--pos':
        print("=== 8股位置百分位 ===")
        for code in INDEX:
            r = analyze_stock(code)
            symbol, name = INDEX[code]
            data = load(symbol)['data']
            highs = [d['high'] for d in data[-250:]]
            lows = [d['low'] for d in data[-250:]]
            high_250 = max(highs) if highs else 'N/A'
            low_250 = min(lows) if lows else 'N/A'
            print(f"{r['name']}({code}): 当前{r['price']} 250日高{high_250} 低{low_250} 百分位{r['percentile']}% [{r['position']}]")
        return
    
    if sys.argv[1] == '--help':
        main.__doc__
        return
    
    # 单只股票分析
    code = sys.argv[1]
    if code in INDEX:
        r = analyze_stock(code)
        print(f"\n{'='*60}")
        print(f"【{r['name']}({r['code']})】智能分析报告")
        print(f"{'='*60}")
        print(f"现价: {r['price']}元 | 涨跌: {r['chg']}% | 量比: {r['vol_ratio']}")
        print(f"位置: {r['position']} ({r['percentile']}%) | 评分: {r['score']}/100")
        print(f"\n关键价位:")
        print(f"  前高: {r['key_levels']['prev_high']:.2f}")
        print(f"  前低: {r['key_levels']['prev_low']:.2f}")
        print(f"  近60日高收: {r['key_levels']['recent_high_close']:.2f}")
        print(f"  近60日低收: {r['key_levels']['recent_low_close']:.2f}")
        print(f"\n建议生死线: {r['life_line']:.2f}")
        if r['volatility']:
            print(f"波动率止损: {r['volatility']['stop_loss']:.2f}")
            print(f"20日波动率: {r['volatility']['percent']}%")
        print(f"\n均线系统:")
        for k, v in r['mas'].items():
            if v:
                print(f"  {k}: {v}")
        print(f"\n凯利建议仓位: {r['kelly_default']}%")
    else:
        print(f"错误: 未找到 {code}")
        print(f"可用代码: {', '.join(INDEX.keys())}")

if __name__ == "__main__":
    main()
