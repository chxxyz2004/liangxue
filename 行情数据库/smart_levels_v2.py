#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学智能价位计算器 v2.0
自动识别：四把尺子、黄金柱/黄金线、进攻线/防守线
基于黑马王子现代量学画线五步法
"""
import json
import os
import sys
import math
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KLINE_DIR = os.path.join(BASE_DIR, "kline")

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

def find_box_level(data, lookback=60, min_touches=2):
    """找箱体边沿：被触碰≥min_touches次的高/低点"""
    recent = data[-lookback:] if len(data) > lookback else data
    
    if len(recent) < 10:
        return [], []
    
    # 找局部高点（前后各2根K线都比它低）
    local_highs = []
    local_lows = []
    
    for i in range(2, len(recent)-2):
        curr_high = recent[i]['high']
        curr_low = recent[i]['low']
        
        # 局部高点：前后各2根K线的高点都比它低
        is_high = all(recent[j]['high'] < curr_high for j in range(i-2, i+3) if j != i)
        # 局部低点：前后各2根K线的低点都比它高
        is_low = all(recent[j]['low'] > curr_low for j in range(i-2, i+3) if j != i)
        
        if is_high:
            local_highs.append((i, curr_high))
        if is_low:
            local_lows.append((i, curr_low))
    
    # 聚类找箱体边沿（间隔<3%视为同一区域）
    def cluster_levels(levels, threshold=0.03):
        if not levels:
            return []
        levels.sort(key=lambda x: x[1])
        clusters = [[levels[0]]]
        for level in levels[1:]:
            if level[1] - clusters[-1][0][1] < clusters[-1][0][1] * threshold:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        result = []
        for c in clusters:
            avg_price = sum(x[1] for x in c) / len(c)
            result.append(avg_price)
        return result
    
    high_clusters = cluster_levels(local_highs)
    low_clusters = cluster_levels(local_lows)
    
    # 找被触碰≥min_touches次的价位
    current_price = data[-1]['close']
    
    box_highs = []
    box_lows = []
    
    # 箱体上沿（压力位）：在现价上方，被触碰≥min_touches次
    for level_price in high_clusters:
        if level_price <= current_price:
            continue
        # 计算触碰次数
        touches = sum(1 for d in recent if d['high'] >= level_price * 0.98)
        if touches >= min_touches and (level_price - current_price) / current_price < 0.2:
            box_highs.append({'price': level_price, 'touches': touches})
    
    # 箱体下沿（支撑位）：在现价下方，被触碰≥min_touches次
    for level_price in low_clusters:
        if level_price >= current_price:
            continue
        touches = sum(1 for d in recent if d['low'] <= level_price * 1.02)
        if touches >= min_touches and (current_price - level_price) / current_price < 0.2:
            box_lows.append({'price': level_price, 'touches': touches})
    
    # 按距离现价从近到远排序
    box_highs.sort(key=lambda x: x['price'] - current_price)
    box_lows.sort(key=lambda x: current_price - x['price'])
    
    return box_highs[:2], box_lows[:2]

def find_high_volume_pillar(data, lookback=30):
    """找高量柱：近N日量比最大且≥1.5"""
    recent = data[-lookback:] if len(data) > lookback else data
    
    if len(recent) < 2:
        return None
    
    max_vol_idx = 0
    max_vol_ratio = 0
    
    for i in range(1, len(recent)):
        vol_ratio = recent[i]['volume'] / recent[i-1]['volume'] if recent[i-1]['volume'] > 0 else 0
        if vol_ratio > max_vol_ratio:
            max_vol_ratio = vol_ratio
            max_vol_idx = i
    
    if max_vol_ratio >= 1.5:
        pillar = recent[max_vol_idx]
        prev = recent[max_vol_idx - 1]
        return {
            'day': pillar['day'],
            'index': len(data) - len(recent) + max_vol_idx,
            'open': pillar['open'],
            'high': pillar['high'],
            'low': pillar['low'],
            'close': pillar['close'],
            'volume': pillar['volume'],
            'vol_ratio': round(max_vol_ratio, 2),
            'real_top': pillar['close'],  # 实顶=收盘价（阳柱）
            'real_bottom': pillar['low'],  # 实底=最低价
            'is_bullish': pillar['close'] >= pillar['open']
        }
    
    return None

def find_golden_pillar(data, lookback=60):
    """找黄金柱：将军柱+3日缩量不破实底"""
    recent = data[-lookback:] if len(data) > lookback else data
    
    if len(recent) < 4:
        return None
    
    # 找将军柱候选（放量大阳线）
    candidates = []
    for i in range(1, len(recent)-3):
        curr = recent[i]
        prev = recent[i-1]
        
        # 将军柱条件：阳线、涨幅明显（>3%）、量能放大（量比>1.3）
        chg = (curr['close'] - prev['close']) / prev['close'] * 100
        vol_ratio = curr['volume'] / prev['volume'] if prev['volume'] > 0 else 0
        
        if (curr['close'] >= curr['open'] and 
            chg >= 3 and 
            vol_ratio >= 1.3):
            candidates.append({
                'index': i,
                'day': curr['day'],
                'close': curr['close'],
                'low': curr['low'],
                'vol_ratio': round(vol_ratio, 2),
                'change': round(chg, 2)
            })
    
    # 验证黄金柱条件：之后3日缩量不破实底
    for candidate in candidates:
        i = candidate['index']
        base_low = recent[i]['low']
        base_close = recent[i]['close']
        
        # 检查后续3日
        if i + 3 >= len(recent):
            continue
        
        shrinking_volume = True
        no_break_low = True
        
        for j in range(1, 4):
            curr_vol = recent[i+j]['volume']
            prev_vol = recent[i+j-1]['volume']
            
            # 缩量条件
            if prev_vol > 0 and curr_vol / prev_vol > 1.0:
                shrinking_volume = False
            
            # 不破实底条件
            if recent[i+j]['low'] < base_low:
                no_break_low = False
        
        if shrinking_volume and no_break_low:
            candidate['golden'] = True
            candidate['golden_line'] = curr['close']  # 黄金线=黄金柱实顶（收盘价）
            return candidate
    
    return None

def find_gap_levels(data, lookback=60):
    """找向下跳空缺口下沿"""
    recent = data[-lookback:] if len(data) > lookback else data
    
    gaps = []
    for i in range(1, len(recent)):
        curr = recent[i]
        prev = recent[i-1]
        
        # 向下跳空：今日最低 < 昨日最高
        if curr['low'] < prev['high']:
            gap_size = (prev['high'] - curr['low']) / prev['high'] * 100
            if gap_size > 1:  # 缺口>1%才记录
                gaps.append({
                    'day': curr['day'],
                    'bottom': curr['low'],
                    'size': round(gap_size, 2)
                })
    
    return gaps[:3]  # 返回最近3个缺口

def find_integer_levels(price, range_margin=3):
    """找附近整数关口"""
    levels = []
    lower = int(math.floor(price - range_margin))
    upper = int(math.ceil(price + range_margin))
    
    for level in range(lower, upper + 1):
        if level % 10 == 0 or level % 5 == 0:
            levels.append(float(level))
    
    return sorted(set(levels))

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
    return round((current - min_price) / (max_price - min_price) * 100, 1)

def analyze_full_levels(code):
    """完整价位分析"""
    if code not in INDEX:
        return None
    
    symbol, name = INDEX[code]
    rec = load(symbol)
    data = rec['data']
    
    current = data[-1]
    prev = data[-2] if len(data) > 1 else None
    price = current['close']
    
    # 基础指标
    vol_ratio = round(current['volume'] / prev['volume'], 2) if prev else None
    chg = round((price - prev['close']) / prev['close'] * 100, 2) if prev else None
    percentile = calc_position_percentile(data)
    
    # 均线系统
    mas = calc_moving_averages(data)
    
    # 四把尺子
    box_highs, box_lows = find_box_level(data)
    high_vol_pillar = find_high_volume_pillar(data)
    golden_pillar = find_golden_pillar(data)
    gaps = find_gap_levels(data)
    int_levels = find_integer_levels(price)
    
    # 波动率
    if len(data) >= 20:
        closes = [d['close'] for d in data[-20:]]
        mean = sum(closes) / 20
        variance = sum((c - mean) ** 2 for c in closes) / 20
        std = math.sqrt(variance)
        volatility = {'std': round(std, 2), 'percent': round(std / mean * 100, 2)}
    else:
        volatility = None
    
    # 确定生死线、进攻线、防守线
    # 生死线=最强的支撑位（在现价下方）
    # 进攻线=跌破必须走的线（通常是最强的支撑）
    # 防守线=反抽不过不加仓的线（通常在现价上方）
    
    life_line = None
    attack_line = None
    defense_line = None
    
    # 从支撑位中找最强的
    if box_lows:
        life_line = {'price': box_lows[0]['price'], 'sources': ['箱体下沿'], 'type': '支撑'}
        attack_line = life_line
    elif golden_pillar:
        life_line = {'price': golden_pillar['golden_line'], 'sources': ['黄金线'], 'type': '支撑'}
        attack_line = life_line
    
    # 从压力位中找最近的防守线
    if box_highs:
        defense_line = {'price': box_highs[0]['price'], 'source': '箱体上沿'}
    elif resistance_levels:
        defense_line = {'price': resistance_levels[0]['price'], 'source': resistance_levels[0]['source']}
    
    # 综合评分
    score = 50
    if percentile and percentile < 30:
        score += 15
    elif percentile and percentile > 70:
        score -= 15
    
    if vol_ratio and chg:
        if vol_ratio > 1.5 and chg > 3:
            score += 10
        elif vol_ratio > 1.5 and chg < -3:
            score -= 15
    
    if mas.get('MA5') and mas.get('MA20'):
        if mas['MA5'] > mas['MA20']:
            score += 5
        else:
            score -= 5
    
    score = max(0, min(100, score))
    
    return {
        'code': code,
        'name': name,
        'price': price,
        'chg': chg,
        'vol_ratio': vol_ratio,
        'percentile': percentile,
        'position': '低位区' if percentile and percentile < 40 else ('腰部区' if percentile and percentile < 70 else '高位区'),
        'score': score,
        'ma_system': mas,
        'box_levels': {'highs': box_highs, 'lows': box_lows},
        'high_volume_pillar': high_vol_pillar,
        'golden_pillar': golden_pillar,
        'gaps': gaps,
        'integer_levels': int_levels,
        'volatility': volatility,
        'life_line': life_line,
        'attack_line': attack_line,
        'defense_line': defense_line,
        'support_levels': support_levels if 'support_levels' in locals() else [],
        'resistance_levels': resistance_levels if 'resistance_levels' in locals() else []
    }

def generate_report(codes=None):
    """生成完整价位分析报告"""
    if codes is None:
        codes = list(INDEX.keys())
    
    results = []
    for code in codes:
        r = analyze_full_levels(code)
        if r:
            results.append(r)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def print_report(results):
    """打印报告"""
    print("=" * 80)
    print("量学智能价位分析报告 v2.0")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    for r in results:
        print(f"\n{'='*60}")
        print(f"【{r['name']}({r['code']})】")
        print(f"{'='*60}")
        print(f"现价: {r['price']}元 | 涨跌: {r['chg']}% | 量比: {r['vol_ratio']}")
        print(f"位置: {r['position']} ({r['percentile']}%) | 综合评分: {r['score']}/100")
        
        # 生死线/进攻线/防守线
        print(f"\n【关键价位】")
        if r['life_line']:
            print(f"  生死线(进攻线): {r['life_line']['price']:.2f}元 ({' + '.join(r['life_line']['sources'])})")
        if r['defense_line']:
            print(f"  防守线: {r['defense_line']['price']:.2f}元 ({r['defense_line']['source']})")
        
        # 黄金柱
        if r['golden_pillar']:
            gp = r['golden_pillar']
            print(f"\n【黄金柱结构】")
            print(f"  将军柱日: {gp['day']} | 收盘{gp['close']:.2f} | 量比{gp['vol_ratio']} | 涨幅{gp['change']}%")
            print(f"  黄金线: {gp['golden_line']:.2f}元 (将军柱实底)")
        
        # 高量柱
        if r['high_volume_pillar']:
            hp = r['high_volume_pillar']
            print(f"\n【高量柱】")
            print(f"  日期: {hp['day']} | 实顶{hp['real_top']:.2f} | 实底{hp['real_bottom']:.2f}")
            print(f"  量比: {hp['vol_ratio']} | 阳柱: {'是' if hp['is_bullish'] else '否'}")
        
        # 箱体
        if r['box_levels']['highs']:
            print(f"\n【箱体上沿】")
            for h in r['box_levels']['highs']:
                print(f"  {h['price']:.2f}元 (触碰{h['touches']}次)")
        if r['box_levels']['lows']:
            print(f"【箱体下沿】")
            for l in r['box_levels']['lows']:
                print(f"  {l['price']:.2f}元 (触碰{l['touches']}次)")
        
        # 均线
        print(f"\n【均线系统】")
        for k, v in r['ma_system'].items():
            if v:
                marker = " ✓" if v < r['price'] else " ✗"
                print(f"  {k}: {v}{marker}")
        
        # 波动率
        if r['volatility']:
            print(f"\n【波动率】")
            print(f"  20日标准差: {r['volatility']['std']:.2f}元 ({r['volatility']['percent']}%)")
            print(f"  波动率止损位: {r['price'] - 2*r['volatility']['std']:.2f}元")
        
        # 缺口
        if r['gaps']:
            print(f"\n【近期缺口】")
            for g in r['gaps']:
                print(f"  {g['day']}: 缺口下沿{g['bottom']:.2f}元 (缺口幅度{g['size']}%)")
        
        # 整数关口
        if r['integer_levels']:
            near_int = [x for x in r['integer_levels'] if abs(x - r['price']) < 2]
            if near_int:
                print(f"\n【附近整数关】: {', '.join(map(str, near_int))}")
        
        # 多线合一
        if r.get('multi_line_合一'):
            print(f"\n【多线合一价位】")
            for price, sources in r['multi_line_合一'].items():
                print(f"  {price:.2f}元 ← {' + '.join(sources)}")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 smart_levels_v2.py              # 8股综合报告")
        print("  python3 smart_levels_v2.py 603516       # 单只股票详细分析")
        print("  python3 smart_levels_v2.py --summary    # 8股速览表格")
        print("  python3 smart_levels_v2.py --help       # 显示帮助")
        sys.exit(1)
    
    if sys.argv[1] == '--help':
        main.__doc__
        return
    
    if sys.argv[1] == '--summary':
        results = generate_report()
        print("\n| 股票 | 现价 | 位置% | 生死线 | 进攻线 | 防守线 | 评分 |")
        print("|------|------|-------|--------|--------|--------|------|")
        for r in results:
            ll = r['life_line']['price'] if r['life_line'] else 'N/A'
            al = r['attack_line']['price'] if r['attack_line'] else 'N/A'
            dl = r['defense_line']['price'] if r['defense_line'] else 'N/A'
            score_color = '🟢' if r['score'] >= 60 else ('🟡' if r['score'] >= 50 else '🟠')
            print(f"| {r['name']} | {r['price']} | {r['percentile']}% | {ll:.2f} | {al:.2f} | {dl:.2f} | {r['score']} |")
        return
    
    code = sys.argv[1]
    if code in INDEX:
        r = analyze_full_levels(code)
        print_report([r])
    else:
        print(f"错误: 未找到 {code}")
        print(f"可用代码: {', '.join(INDEX.keys())}")

if __name__ == "__main__":
    main()
