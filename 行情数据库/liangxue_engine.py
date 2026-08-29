# -*- coding: utf-8 -*-
"""黑马王子张得一量学战法信号引擎

实现量学核心战法体系：
  - 量柱形态：高量柱、低量柱、倍量柱、平量柱、梯量柱、缩量柱、阴量柱
  - 关键柱：黄金柱、元帅柱、将军柱（基于倍量柱后缩量回调幅度判定）
  - 量线体系：峰顶线、谷底线、凹口平衡线、将军线、平行线
  - 精准线：精准回踩、精准划线判断

所有计算仅基于已完成的K线数据，绝不使用未来函数。
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

DB_DIR = '/workspace/行情数据库'
KLINE_DIR = os.path.join(DB_DIR, 'kline')
KLINE_5MIN_DIR = os.path.join(DB_DIR, 'kline_5min')


def load_daily_kline(symbol: str) -> Optional[Dict]:
    """加载日线 K 线数据（腾讯 fqkline 前复权）。"""
    path = os.path.join(KLINE_DIR, f'{symbol}.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None


# ================================================================
# 辅助工具函数
# ================================================================

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def _correlation(a: List[float], b: List[float]) -> float:
    if len(a) <= 1 or len(b) <= 1 or len(a) != len(b):
        return 0.0
    ma, mb = _mean(a), _mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = (sum((x - ma) ** 2 for x in a)) ** 0.5
    db = (sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0


def _is_yang(k: Dict) -> bool:
    """是否收阳（收盘价 >= 开盘价）"""
    return k.get('close', 0) >= k.get('open', 0)


def _is_yin(k: Dict) -> bool:
    """是否收阴（收盘价 < 开盘价）"""
    return k.get('close', 0) < k.get('open', 0)


def _real_body(k: Dict) -> float:
    """实体高度 = |close - open|"""
    return abs(k.get('close', 0) - k.get('open', 0))


def _upper_shadow(k: Dict) -> float:
    """上影线长度"""
    return k.get('high', 0) - max(k.get('close', 0), k.get('open', 0))


def _lower_shadow(k: Dict) -> float:
    """下影线长度"""
    return min(k.get('close', 0), k.get('open', 0)) - k.get('low', 0)


def _body_range(k: Dict) -> float:
    """实体范围（最高-最低含上下影）"""
    return k.get('high', 0) - k.get('low', 0)


# ================================================================
# 一、量柱形态识别
# ================================================================

class VolumeBarDetector:
    """量柱形态检测器：高量柱、低量柱、倍量柱、平量柱、梯量柱、缩量柱、阴量柱"""

    def __init__(self, lookback: int = 20, tolerance: float = 0.2):
        self.lookback = lookback
        self.tolerance = tolerance  # 平量柱容差 ±20%

    def detect_all(self, kl: List[Dict]) -> Dict:
        """检测最近 lookback 日内的所有量柱形态，返回结果字典。"""
        n = len(kl)
        if n < 2:
            return {'error': '数据不足'}

        results = {
            'bars': [],  # 每根K线的量柱标签
            'summary': {
                'high_vol_bars': [],
                'low_vol_bars': [],
                'doubling_bars': [],
                'flat_bars': [],
                'ladder_up': [],
                'ladder_down': [],
                'shrinking_bars': [],
                'yin_volume_bars': [],
            }
        }

        vols = [k.get('volume', 0) for k in kl]
        dates = [k.get('day', '') for k in kl]

        # ---- 1. 高量柱：近 lookback 日最高量 ----
        for i in range(max(0, n - self.lookback), n):
            window = vols[max(0, i - self.lookback + 1):i + 1]
            if max(window) > 0 and vols[i] >= max(window) * 0.98:
                results['summary']['high_vol_bars'].append({
                    'date': dates[i],
                    'index': i,
                    'volume': vols[i],
                    'ratio': round(vols[i] / _mean(window), 2) if _mean(window) > 0 else 0,
                })

        # ---- 2. 低量柱：近 lookback 日最低量 ----
        for i in range(max(0, n - self.lookback), n):
            window = vols[max(0, i - self.lookback + 1):i + 1]
            mn = min(window)
            if mn > 0 and vols[i] <= mn * 1.02:
                results['summary']['low_vol_bars'].append({
                    'date': dates[i],
                    'index': i,
                    'volume': vols[i],
                    'ratio': round(vols[i] / _mean(window), 2) if _mean(window) > 0 else 0,
                })

        # ---- 3. 倍量柱：量比 >= 1.9 且收阳 ----
        for i in range(1, n):
            if vols[i - 1] > 0:
                ratio = vols[i] / vols[i - 1]
                if ratio >= 1.9 and _is_yang(kl[i]):
                    results['summary']['doubling_bars'].append({
                        'date': dates[i],
                        'index': i,
                        'volume': vols[i],
                        'prev_volume': vols[i - 1],
                        'ratio': round(ratio, 2),
                    })

        # ---- 4. 平量柱：当日量与前一日相差 ±tolerance ----
        for i in range(1, n):
            if vols[i - 1] > 0:
                change = abs(vols[i] - vols[i - 1]) / vols[i - 1]
                if change <= self.tolerance:
                    results['summary']['flat_bars'].append({
                        'date': dates[i],
                        'index': i,
                        'volume': vols[i],
                        'change_ratio': round(change, 3),
                    })

        # ---- 5. 梯量柱：连续3根以上递增或递减 ----
        # 检测递增梯形
        i = 1
        while i < n:
            if vols[i] > vols[i - 1] * 1.05:
                length = 1
                j = i + 1
                while j < n and vols[j] > vols[j - 1] * 1.05:
                    length += 1
                    j += 1
                if length >= 2:  # 至少3根（含起点）
                    start_idx = i - length
                    end_idx = i
                    results['summary']['ladder_up'].append({
                        'start_date': dates[start_idx],
                        'end_date': dates[end_idx],
                        'length': length + 1,
                        'start_vol': vols[start_idx],
                        'end_vol': vols[end_idx],
                    })
                i = j
            else:
                i += 1

        # 检测递减梯形
        i = 1
        while i < n:
            if vols[i] < vols[i - 1] * 0.95:
                length = 1
                j = i + 1
                while j < n and vols[j] < vols[j - 1] * 0.95:
                    length += 1
                    j += 1
                if length >= 2:
                    start_idx = i - length
                    end_idx = i
                    results['summary']['ladder_down'].append({
                        'start_date': dates[start_idx],
                        'end_date': dates[end_idx],
                        'length': length + 1,
                        'start_vol': vols[start_idx],
                        'end_vol': vols[end_idx],
                    })
                i = j
            else:
                i += 1

        # ---- 6. 缩量柱：当日量 < 前一日 * 0.8 且收阴 ----
        for i in range(1, n):
            if vols[i - 1] > 0 and vols[i] < vols[i - 1] * 0.8 and _is_yin(kl[i]):
                results['summary']['shrinking_bars'].append({
                    'date': dates[i],
                    'index': i,
                    'volume': vols[i],
                    'prev_volume': vols[i - 1],
                    'ratio': round(vols[i] / vols[i - 1], 2),
                })

        # ---- 7. 阴量柱：当日收阴但成交量放大 ----
        for i in range(1, n):
            if vols[i - 1] > 0 and vols[i] > vols[i - 1] * 1.1 and _is_yin(kl[i]):
                results['summary']['yin_volume_bars'].append({
                    'date': dates[i],
                    'index': i,
                    'volume': vols[i],
                    'prev_volume': vols[i - 1],
                    'ratio': round(vols[i] / vols[i - 1], 2),
                })

        # ---- 8. 为每根K线标注量柱标签 ----
        bar_labels = {}
        for item in results['summary']['high_vol_bars']:
            bar_labels[item['index']] = bar_labels.get(item['index'], [])
            bar_labels[item['index']].append('高量柱')
        for item in results['summary']['low_vol_bars']:
            bar_labels[item['index']] = bar_labels.get(item['index'], [])
            bar_labels[item['index']].append('低量柱')
        for item in results['summary']['doubling_bars']:
            bar_labels[item['index']] = bar_labels.get(item['index'], [])
            bar_labels[item['index']].append('倍量柱')
        for item in results['summary']['flat_bars']:
            bar_labels[item['index']] = bar_labels.get(item['index'], [])
            bar_labels[item['index']].append('平量柱')
        for item in results['summary']['shrinking_bars']:
            bar_labels[item['index']] = bar_labels.get(item['index'], [])
            bar_labels[item['index']].append('缩量柱')
        for item in results['summary']['yin_volume_bars']:
            bar_labels[item['index']] = bar_labels.get(item['index'], [])
            bar_labels[item['index']].append('阴量柱')

        for i in range(n):
            labels = bar_labels.get(i, [])
            results['bars'].append({
                'date': dates[i],
                'index': i,
                'volume': vols[i],
                'labels': labels,
                'is_doubling': any('倍量柱' in l for l in labels),
                'is_shrinking': any('缩量柱' in l for l in labels),
            })

        # 截断到最近 lookback 日
        cutoff = max(0, n - self.lookback)
        results['bars'] = results['bars'][cutoff:]
        for key in results['summary']:
            results['summary'][key] = [
                item for item in results['summary'][key]
                if item.get('index', 0) >= cutoff
            ]
            if isinstance(results['summary'][key], list) and results['summary'][key]:
                results['summary'][key] = results['summary'][key][-10:]  # 最多保留10条

        return results


# ================================================================
# 二、关键柱判断：黄金柱、元帅柱、将军柱
# ================================================================

class KeyBarDetector:
    """关键柱识别：黄金柱、元帅柱、将军柱

    核心逻辑（黑马王子《量柱擒涨停》）：
    - 先找到倍量柱（启动信号）
    - 倍量柱后出现缩量回调柱
    - 回调幅度 = (倍量柱最高价 - 回调柱最低价) / 倍量柱实体高度
      - 回调 ≤ 1/3 实体高度 → 黄金柱
      - 回调 1/3 ~ 1/2 实体高度 → 元帅柱
      - 回调 > 1/2 实体高度但未破前低 → 将军柱
    """

    def __init__(self, lookback: int = 30, max_skip: int = 8):
        self.lookback = lookback
        self.max_skip = max_skip  # 倍量柱后最多跳过 N 根K线寻找关键柱

    def detect_all(self, kl: List[Dict]) -> Dict:
        n = len(kl)
        if n < 5:
            return {'error': '数据不足'}

        results = {
            'golden_bars': [],     # 黄金柱
            'marshal_bars': [],    # 元帅柱
            'general_bars': [],    # 将军柱
            'doubling_bars': [],   # 倍量柱（作为关键柱的前置信号）
        }

        cutoff = max(0, n - self.lookback)

        # ---- Step 1: 找到所有倍量柱 ----
        for i in range(cutoff, n):
            if i == 0:
                continue
            v_prev = kl[i - 1].get('volume', 0)
            v_curr = kl[i].get('volume', 0)
            if v_prev <= 0:
                continue
            ratio = v_curr / v_prev
            if ratio >= 1.9 and _is_yang(kl[i]):
                results['doubling_bars'].append({
                    'date': kl[i].get('day', ''),
                    'index': i,
                    'ratio': round(ratio, 2),
                    'high': kl[i].get('high', 0),
                    'low': kl[i].get('low', 0),
                    'open': kl[i].get('open', 0),
                    'close': kl[i].get('close', 0),
                    'volume': v_curr,
                })

        # ---- Step 2: 每个倍量柱向后搜索关键柱 ----
        for dbl in results['doubling_bars'][-10:]:  # 只看最近10个倍量柱
            dbl_idx = dbl['index']
            dbl_high = dbl['high']
            dbl_low = dbl['low']
            dbl_body = dbl_high - dbl_low
            dbl_close = dbl['close']
            dbl_open = dbl['open']

            # 向前找倍量柱前一日低点作为参考基准
            ref_low = kl[dbl_idx - 1].get('low', dbl_low) if dbl_idx > 0 else dbl_low

            # 向后搜索缩量回调柱
            found_key_bar = False
            # ref_low 使用倍量柱自身的最低价作为基准
            ref_low = dbl['low']
            for j in range(dbl_idx + 1, min(dbl_idx + self.max_skip + 1, n)):
                k = kl[j]
                k_vol = k.get('volume', 0)
                dbl_vol = dbl.get('volume', 0)

                # 回调柱必须缩量：成交量 ≤ 倍量柱的 90%
                if dbl_vol > 0 and k_vol >= dbl_vol * 0.9:
                    continue  # 量没有缩，跳过

                # 计算回调幅度：(倍量柱最高 - 回调柱最低) / 倍量柱实体高度
                # normalized ∈ [0, 1]: 0=刚好在倍量柱低点；1=回到倍量柱高点
                # 若回调柱最低价 > 倍量柱最高价 → normalized < 0（向上突破，不归类为关键柱）
                if dbl_body <= 0:
                    continue
                drawdown = (dbl_high - k['low']) / dbl_body

                # 将军柱：回调幅度 1/2 ~ 1（未破倍量柱低点）
                # 元帅柱：回调幅度 1/3 ~ 1/2
                # 黄金柱：回调幅度 ≤ 1/3
                # 跌破倍量柱低点（drawdown > 1）不再归类为关键柱
                if drawdown > 1.0:
                    # 已破倍量柱低点，关键柱形态失效
                    break

                date_str = k.get('day', '')
                if drawdown > 0.5:
                    results['general_bars'].append({
                        'date': date_str,
                        'index': j,
                        'related_doubling': dbl['date'],
                        'drawdown_ratio': round(drawdown, 3),
                        'volume_ratio': round(k_vol / dbl_vol, 2) if dbl_vol > 0 else 0,
                        'type': '将军柱',
                        'note': f'回调{drawdown:.0%}实体，守住倍量柱低点{ref_low:.2f}',
                    })
                    found_key_bar = True
                    break

                if 1 / 3 <= drawdown <= 0.5:
                    results['marshal_bars'].append({
                        'date': date_str,
                        'index': j,
                        'related_doubling': dbl['date'],
                        'drawdown_ratio': round(drawdown, 3),
                        'volume_ratio': round(k_vol / dbl_vol, 2) if dbl_vol > 0 else 0,
                        'type': '元帅柱',
                        'note': f'回调{drawdown:.0%}实体',
                    })
                    found_key_bar = True
                    break

                if 0 < drawdown < 1 / 3:
                    results['golden_bars'].append({
                        'date': date_str,
                        'index': j,
                        'related_doubling': dbl['date'],
                        'drawdown_ratio': round(drawdown, 3),
                        'volume_ratio': round(k_vol / dbl_vol, 2) if dbl_vol > 0 else 0,
                        'type': '黄金柱',
                        'note': f'回调{drawdown:.0%}实体，强支撑',
                    })
                    found_key_bar = True
                    break

            # 若未找到关键柱，检查是否为平量柱确认型
            if not found_key_bar:
                for j in range(dbl_idx + 1, min(dbl_idx + self.max_skip + 1, n)):
                    k = kl[j]
                    k_vol = k.get('volume', 0)
                    dbl_vol = dbl.get('volume', 0)
                    if dbl_vol > 0 and abs(k_vol - dbl_vol) / dbl_vol < 0.15:
                        # 平量确认柱（倍量后紧跟平量）
                        pass  # 平量确认属于辅助信号，不单独列为关键柱

        return results


# ================================================================
# 三、量线体系：峰顶线、谷底线、凹口平衡线、将军线、平行线
# ================================================================

class QuantityLineDetector:
    """量线识别：峰顶线、谷底线、凹口平衡线、将军线、平行线

    量学核心战法（《量线捉涨停》）：
    - 峰顶线：连接多个高点形成的压力线
    - 谷底线：连接多个低点形成的支撑线
    - 凹口平衡线：凹口两侧的高点/低点连线
    - 将军线：从重要高低点发出的水平支撑/压力线
    - 平行线：与已有量线平行的辅助线
    """

    def __init__(self, tolerance: float = 0.03):
        self.tolerance = tolerance  # 高点/低点判等同的容差（3%）

    def detect_peaks_and_valleys(self, kl: List[Dict], window: int = 5) -> Dict:
        """检测局部峰顶和谷底（用滑动窗口法）。

        峰顶：当日最高价是 window 日内最高
        谷底：当日最低价是 window 日内最低
        """
        n = len(kl)
        peaks = []  # 峰顶列表
        valleys = []  # 谷底列表

        for i in range(window, n - window):
            high_window = [kl[j].get('high', 0) for j in range(i - window, i + window + 1)]
            low_window = [kl[j].get('low', 0) for j in range(i - window, i + window + 1)]

            if kl[i].get('high', 0) >= max(high_window) * 0.99:
                peaks.append({
                    'date': kl[i].get('day', ''),
                    'index': i,
                    'price': kl[i].get('high', 0),
                })
            if kl[i].get('low', 0) <= min(low_window) * 1.01:
                valleys.append({
                    'date': kl[i].get('day', ''),
                    'index': i,
                    'price': kl[i].get('low', 0),
                })

        return {'peaks': peaks[-15:], 'valleys': valleys[-15:]}

    def find_peak_lines(self, peaks: List[Dict], tolerance: float = None) -> List[Dict]:
        """从峰顶列表中找出大致在同一水平的峰顶线。"""
        tol = tolerance or self.tolerance
        lines = []
        used = set()

        for i, p1 in enumerate(peaks):
            if i in used:
                continue
            group = [p1]
            for j, p2 in enumerate(peaks):
                if j in used or i == j:
                    continue
                avg = (p1['price'] + p2['price']) / 2
                if abs(p2['price'] - avg) / avg <= tol:
                    group.append(p2)
                    used.add(j)
            if len(group) >= 2:
                avg_price = _mean([g['price'] for g in group])
                lines.append({
                    'type': '峰顶线',
                    'price': round(avg_price, 2),
                    'points': [{'date': g['date'], 'price': g['price']} for g in group],
                    'count': len(group),
                })
                for g in group:
                    used.add(g['index'])

        return lines

    def find_valley_lines(self, valleys: List[Dict], tolerance: float = None) -> List[Dict]:
        """从谷底列表中找出大致在同一水平的谷底线。"""
        tol = tolerance or self.tolerance
        lines = []
        used = set()

        for i, v1 in enumerate(valleys):
            if i in used:
                continue
            group = [v1]
            for j, v2 in enumerate(valleys):
                if j in used or i == j:
                    continue
                avg = (v1['price'] + v2['price']) / 2
                if abs(v2['price'] - avg) / avg <= tol:
                    group.append(v2)
                    used.add(j)
            if len(group) >= 2:
                avg_price = _mean([g['price'] for g in group])
                lines.append({
                    'type': '谷底线',
                    'price': round(avg_price, 2),
                    'points': [{'date': g['date'], 'price': g['price']} for g in group],
                    'count': len(group),
                })
                for g in group:
                    used.add(g['index'])

        return lines

    def find_concave_balance_lines(self, peaks: List[Dict], valleys: List[Dict]) -> List[Dict]:
        """凹口平衡线：找到凹口两侧对称的高点/低点。

        凹口形态：高-低-高 或 低-高-低
        平衡线取凹口两侧等高点/等低点
        """
        lines = []
        used_peak_indices = set()
        used_valley_indices = set()

        # 高-低-高 型凹口
        for i, pk in enumerate(peaks):
            if pk['index'] in used_peak_indices:
                continue
            # 找此峰顶之后的谷底
            for j, vl in enumerate(valleys):
                if vl['index'] <= pk['index']:
                    continue
                if vl['index'] in used_valley_indices:
                    continue
                # 找谷底之后的另一个峰顶
                for k, pk2 in enumerate(peaks):
                    if pk2['index'] <= vl['index']:
                        continue
                    if pk2['index'] in used_peak_indices:
                        continue
                    # 检查两侧峰顶是否近似等高
                    avg = (pk['price'] + pk2['price']) / 2
                    if abs(pk2['price'] - avg) / avg <= self.tolerance:
                        lines.append({
                            'type': '凹口平衡线(高-低-高)',
                            'price': round(avg, 2),
                            'left_peak': {'date': pk['date'], 'price': pk['price']},
                            'valley': {'date': vl['date'], 'price': vl['price']},
                            'right_peak': {'date': pk2['date'], 'price': pk2['price']},
                            'note': f'凹口平衡，预计回归{avg:.2f}',
                        })
                        used_peak_indices.add(pk['index'])
                        used_peak_indices.add(pk2['index'])
                        used_valley_indices.add(vl['index'])
                        break
                else:
                    continue
                break

        # 低-高-低 型凹口
        for i, vl1 in enumerate(valleys):
            if vl1['index'] in used_valley_indices:
                continue
            for j, pk in enumerate(peaks):
                if pk['index'] <= vl1['index']:
                    continue
                if pk['index'] in used_peak_indices:
                    continue
                for k, vl2 in enumerate(valleys):
                    if vl2['index'] <= pk['index']:
                        continue
                    if vl2['index'] in used_valley_indices:
                        continue
                    avg = (vl1['price'] + vl2['price']) / 2
                    if abs(vl2['price'] - avg) / avg <= self.tolerance:
                        lines.append({
                            'type': '凹口平衡线(低-高-低)',
                            'price': round(avg, 2),
                            'left_valley': {'date': vl1['date'], 'price': vl1['price']},
                            'peak': {'date': pk['date'], 'price': pk['price']},
                            'right_valley': {'date': vl2['date'], 'price': vl2['price']},
                            'note': f'凹口平衡，预计回归{avg:.2f}',
                        })
                        used_valley_indices.add(vl1['index'])
                        used_valley_indices.add(vl2['index'])
                        used_peak_indices.add(pk['index'])
                        break
                else:
                    continue
                break

        return lines

    def find_general_lines(self, kl: List[Dict], peaks: List[Dict], valleys: List[Dict]) -> List[Dict]:
        """将军线：从重要高低点发出的水平支撑/压力线。

        将军线定义：从最近的重要峰顶或谷底发出，向右延伸的水平线。
        将军线分为：
        - 将军峰顶线：从重要峰顶发出，作为压力线
        - 将军谷底线：从重要谷底发出，作为支撑线
        """
        lines = []
        n = len(kl)

        if not peaks and not valleys:
            return lines

        # 取最近3个峰顶和谷底作为将军线起点
        recent_peaks = peaks[-3:] if len(peaks) >= 3 else peaks
        recent_valleys = valleys[-3:] if len(valleys) >= 3 else valleys

        for pk in recent_peaks:
            pk_idx = pk.get('index', 0)
            # 将军峰顶线：从此峰顶向右延伸，计算触及次数
            touches = 0
            for k in kl[pk_idx + 1:]:
                if abs(k.get('high', 0) - pk['price']) / pk['price'] <= self.tolerance:
                    touches += 1
            lines.append({
                'type': '将军峰顶线',
                'price': round(pk['price'], 2),
                'origin_date': pk.get('date', ''),
                'origin_index': pk_idx,
                'touches': touches,
                'strength': '强' if touches >= 2 else '中',
            })

        for vl in recent_valleys:
            vl_idx = vl.get('index', 0)
            touches = 0
            for k in kl[vl_idx + 1:]:
                if abs(k.get('low', 0) - vl['price']) / vl['price'] <= self.tolerance:
                    touches += 1
            lines.append({
                'type': '将军谷底线',
                'price': round(vl['price'], 2),
                'origin_date': vl.get('date', ''),
                'origin_index': vl_idx,
                'touches': touches,
                'strength': '强' if touches >= 2 else '中',
            })

        return lines

    def find_parallel_lines(self, existing_lines: List[Dict], kl: List[Dict]) -> List[Dict]:
        """平行线：基于已有峰顶线/谷底线，计算平行辅助线。

        平行线间距 = 主线的价格幅度 / 2
        """
        parallel_lines = []
        if len(existing_lines) < 2:
            return parallel_lines

        # 取间距最大的两条线作为基准
        prices = sorted(set(l['price'] for l in existing_lines))
        if len(prices) < 2:
            return parallel_lines

        # 计算相邻价格的平均间距
        gaps = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
        if not gaps:
            return parallel_lines
        avg_gap = _mean(gaps)

        # 生成平行辅助线（主线上下各一条）
        for price in prices:
            upper = price + avg_gap
            lower = price - avg_gap
            # 检查是否已有接近的线
            has_upper = any(abs(pl['price'] - upper) / upper < self.tolerance for pl in existing_lines)
            has_lower = any(abs(pl['price'] - lower) / lower < self.tolerance for pl in existing_lines)
            if not has_upper and upper > 0:
                parallel_lines.append({
                    'type': '平行线(上)',
                    'price': round(upper, 2),
                    'source': price,
                    'offset': round(avg_gap, 2),
                })
            if not has_lower and lower > 0:
                parallel_lines.append({
                    'type': '平行线(下)',
                    'price': round(lower, 2),
                    'source': price,
                    'offset': round(-avg_gap, 2),
                })

        return parallel_lines[:6]  # 最多保留6条平行线

    def detect_all(self, kl: List[Dict]) -> Dict:
        """完整量线检测。"""
        n = len(kl)
        if n < 20:
            return {'error': '数据不足'}

        # 1. 检测峰顶和谷底
        pv = self.detect_peaks_and_valleys(kl, window=5)
        peaks = pv['peaks']
        valleys = pv['valleys']

        # 2. 找峰顶线和谷底线
        peak_lines = self.find_peak_lines(peaks)
        valley_lines = self.find_valley_lines(valleys)

        # 3. 找凹口平衡线
        concave_lines = self.find_concave_balance_lines(peaks, valleys)

        # 4. 找将军线
        general_lines = self.find_general_lines(kl, peaks, all_lines := peak_lines + valley_lines)

        # 5. 找平行线
        all_lines_data = peak_lines + valley_lines
        parallel_lines = self.find_parallel_lines(all_lines_data, kl)

        return {
            'peaks': peaks,
            'valleys': valleys,
            'peak_lines': peak_lines,       # 峰顶线
            'valley_lines': valley_lines,   # 谷底线
            'concave_lines': concave_lines, # 凹口平衡线
            'general_lines': general_lines, # 将军线
            'parallel_lines': parallel_lines,  # 平行线
        }


# ================================================================
# 四、精准线体系
# ================================================================

class PrecisionLineDetector:
    """精准线体系：精准回踩、精准划线判断

    精准线定义（黑马王子）：
    - 精准线 = 量线体系中能被价格多次验证的水平支撑/压力线
    - 精准回踩 = 价格回落至精准线附近并获得支撑/压力的行为
    - 精准确认 = 价格触及精准线后反向运动，验证该线有效
    """

    def __init__(self, touch_tolerance: float = 0.02, confirm_tolerance: float = 0.03):
        self.touch_tol = touch_tolerance
        self.confirm_tol = confirm_tolerance

    def check_precision_touch(self, kl: List[Dict], line_price: float,
                               start_idx: int = 0) -> Dict:
        """检查某条线是否是精准线：统计价格触及次数和确认效果。

        Returns:
            {
                'line_price': 线的价格,
                'touch_count': 触及次数,
                'confirm_count': 确认次数（触及后反向），
                'precision_score': 精准度评分 0~1,
                'is_precise': 是否精准线,
                'touches': 每次触及的详情,
            }
        """
        n = len(kl)
        touches = []
        confirmations = 0

        for i in range(start_idx, n):
            high = kl[i].get('high', 0)
            low = kl[i].get('low', 0)
            close = kl[i].get('close', 0)

            # 上影线触及（压力线检测）
            if line_price > 0 and abs(high - line_price) / line_price <= self.touch_tol:
                touches.append({
                    'date': kl[i].get('day', ''),
                    'index': i,
                    'type': '上沿触及',
                    'price': round(high, 2),
                })
                # 确认：后续收盘价低于线下方
                if i + 1 < n:
                    next_close = kl[i + 1].get('close', 0)
                    if next_close < line_price * (1 - self.confirm_tol):
                        confirmations += 1

            # 下影线触及（支撑线检测）
            if line_price > 0 and abs(low - line_price) / line_price <= self.touch_tol:
                touches.append({
                    'date': kl[i].get('day', ''),
                    'index': i,
                    'type': '下沿触及',
                    'price': round(low, 2),
                })
                if i + 1 < n:
                    next_close = kl[i + 1].get('close', 0)
                    if next_close > line_price * (1 + self.confirm_tol):
                        confirmations += 1

        precision_score = confirmations / max(len(touches), 1)
        is_precise = len(touches) >= 2 and confirmations >= 1

        return {
            'line_price': round(line_price, 2),
            'touch_count': len(touches),
            'confirm_count': confirmations,
            'precision_score': round(precision_score, 3),
            'is_precise': is_precise,
            'touches': touches[-5:],
        }

    def detect_all_precision_lines(self, kl: List[Dict],
                                    peak_lines: List[Dict],
                                    valley_lines: List[Dict]) -> Dict:
        """对所有峰顶线、谷底线进行精准度验证。"""
        results = {
            'precise_peak_lines': [],
            'precise_valley_lines': [],
            'all_verifications': [],
        }

        for line in peak_lines:
            ver = self.check_precision_touch(kl, line['price'])
            ver['line_type'] = '峰顶线'
            ver['line_price'] = line['price']
            results['all_verifications'].append(ver)
            if ver['is_precise']:
                results['precise_peak_lines'].append(ver)

        for line in valley_lines:
            ver = self.check_precision_touch(kl, line['price'])
            ver['line_type'] = '谷底线'
            ver['line_price'] = line['price']
            results['all_verifications'].append(ver)
            if ver['is_precise']:
                results['precise_valley_lines'].append(ver)

        return results


# ================================================================
# 五、综合信号引擎：整合所有量学战法
# ================================================================

class LiangXueEngine:
    """黑马王子量学全体系信号引擎"""

    def __init__(self, lookback: int = 30):
        self.lookback = lookback
        self.volume_detector = VolumeBarDetector(lookback=lookback)
        self.key_bar_detector = KeyBarDetector(lookback=lookback)
        self.line_detector = QuantityLineDetector()
        self.precision_detector = PrecisionLineDetector()

    def full_analysis(self, symbol: str) -> Dict:
        """完整量学分析：量柱 + 关键柱 + 量线 + 精准线"""
        kdata = load_daily_kline(symbol)
        if not kdata or 'data' not in kdata or not kdata['data']:
            return {'symbol': symbol, 'error': '无数据'}

        kl = kdata['data']
        name = kdata.get('name', symbol)
        latest = kl[-1]

        result = {
            'symbol': symbol,
            'name': name,
            'latest': {
                'day': latest.get('day'),
                'close': latest.get('close'),
                'high': latest.get('high'),
                'low': latest.get('low'),
                'open': latest.get('open'),
                'volume': latest.get('volume'),
            },
            'volume_bars': self.volume_detector.detect_all(kl),
            'key_bars': self.key_bar_detector.detect_all(kl),
            'quantity_lines': self.line_detector.detect_all(kl),
        }

        # 精准线验证
        pl = result['quantity_lines']
        result['precision_lines'] = self.precision_detector.detect_all_precision_lines(
            kl, pl.get('peak_lines', []), pl.get('valley_lines', [])
        )

        # 生成综合信号摘要
        result['signals'] = self._generate_signals(result)

        return result

    def _generate_signals(self, analysis: Dict) -> List[Dict]:
        """从各项检测结果中提取交易信号。"""
        signals = []

        # ---- 量柱信号 ----
        vb = analysis.get('volume_bars', {})
        doubling = vb.get('doubling_bars', [])
        shrinking = vb.get('shrinking_bars', [])
        high_vol = vb.get('high_vol_bars', [])
        low_vol = vb.get('low_vol_bars', [])

        if doubling:
            latest_dbl = doubling[-1]
            signals.append({
                'type': '量柱信号',
                'subtype': '倍量柱',
                'date': latest_dbl['date'],
                'detail': f"倍量柱 {latest_dbl['ratio']}x，启动信号",
                'confidence': min(latest_dbl['ratio'] / 3.0, 0.9),
                'action': '关注突破方向',
            })

        if shrinking:
            latest_shrink = shrinking[-1]
            signals.append({
                'type': '量柱信号',
                'subtype': '缩量柱',
                'date': latest_shrink['date'],
                'detail': f"缩量柱 {latest_shrink['ratio']}x，抛压减轻",
                'confidence': 0.5,
                'action': '等待确认',
            })

        if high_vol:
            signals.append({
                'type': '量柱信号',
                'subtype': '高量柱',
                'detail': f"近{self.lookback}日最高量柱，位置需结合后续走势判断",
                'confidence': 0.4,
                'action': '观察量能持续性',
            })

        if low_vol:
            signals.append({
                'type': '量柱信号',
                'subtype': '低量柱',
                'detail': f"近{self.lookback}日最低量柱，地量见地价",
                'confidence': 0.5,
                'action': '关注反转信号',
            })

        # ---- 关键柱信号 ----
        kb = analysis.get('key_bars', {})
        golden = kb.get('golden_bars', [])
        marshal = kb.get('marshal_bars', [])
        general = kb.get('general_bars', [])

        if golden:
            latest = golden[-1]
            signals.append({
                'type': '关键柱信号',
                'subtype': '黄金柱',
                'date': latest['date'],
                'detail': f"黄金柱（回调{latest['drawdown_ratio']:.0%}实体），强支撑确认",
                'confidence': 0.85,
                'action': '持有/加仓，以黄金柱最低点为防守线',
            })

        if marshal:
            latest = marshal[-1]
            signals.append({
                'type': '关键柱信号',
                'subtype': '元帅柱',
                'date': latest['date'],
                'detail': f"元帅柱（回调{latest['drawdown_ratio']:.0%}实体）",
                'confidence': 0.7,
                'action': '谨慎持有，关注能否守住',
            })

        if general:
            latest = general[-1]
            signals.append({
                'type': '关键柱信号',
                'subtype': '将军柱',
                'date': latest['date'],
                'detail': f"将军柱（回调{latest['drawdown_ratio']:.0%}实体）",
                'confidence': 0.55,
                'action': '严格止损，跌破将军柱低点离场',
            })

        # ---- 量线信号 ----
        ql = analysis.get('quantity_lines', {})
        peak_lines = ql.get('peak_lines', [])
        valley_lines = ql.get('valley_lines', [])
        concave = ql.get('concave_lines', [])
        general_lines = ql.get('general_lines', [])

        if peak_lines:
            latest = peak_lines[-1]
            signals.append({
                'type': '量线信号',
                'subtype': '峰顶线',
                'detail': f"峰顶线 {latest['price']} 元（{latest['count']}次验证）",
                'confidence': 0.6 * latest['count'],
                'action': f"压力位 {latest['price']}，接近可减仓",
            })

        if valley_lines:
            latest = valley_lines[-1]
            signals.append({
                'type': '量线信号',
                'subtype': '谷底线',
                'detail': f"谷底线 {latest['price']} 元（{latest['count']}次验证）",
                'confidence': 0.6 * latest['count'],
                'action': f"支撑位 {latest['price']}，接近可考虑加仓",
            })

        if concave:
            latest = concave[-1]
            signals.append({
                'type': '量线信号',
                'subtype': '凹口平衡线',
                'detail': f"凹口平衡位 {latest['price']} 元",
                'confidence': 0.5,
                'action': f"关注 {latest['price']} 附近的平衡行为",
            })

        # ---- 精准线信号 ----
        pl = analysis.get('precision_lines', {})
        precise_peaks = pl.get('precise_peak_lines', [])
        precise_valleys = pl.get('precise_valley_lines', [])

        if precise_peaks:
            best = max(precise_peaks, key=lambda x: x['precision_score'])
            signals.append({
                'type': '精准线信号',
                'subtype': '精准峰顶线',
                'detail': f"精准压力线 {best['line_price']} 元（精准度{best['precision_score']:.0%}）",
                'confidence': best['precision_score'],
                'action': f"精准压力 {best['line_price']}，可做空参考",
            })

        if precise_valleys:
            best = max(precise_valleys, key=lambda x: x['precision_score'])
            signals.append({
                'type': '精准线信号',
                'subtype': '精准谷底线',
                'detail': f"精准支撑线 {best['line_price']} 元（精准度{best['precision_score']:.0%}）",
                'confidence': best['precision_score'],
                'action': f"精准支撑 {best['line_price']}，可做多参考",
            })

        # 按置信度排序
        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return signals

    def get_summary_text(self, symbol: str) -> str:
        """生成文本摘要，供报告引用。"""
        analysis = self.full_analysis(symbol)
        if 'error' in analysis:
            return f"{symbol}: 无数据"

        lines = []
        name = analysis.get('name', symbol)
        latest = analysis.get('latest', {})
        lines.append(f"### {name}（{symbol}）量学战法分析")
        lines.append(f"- **最新日期**：{latest.get('day', 'N/A')}")
        lines.append(f"- **收盘价**：{latest.get('close', 'N/A')} 元")
        lines.append("")

        # 量柱形态
        vb = analysis.get('volume_bars', {}).get('summary', {})
        doubling = vb.get('doubling_bars', [])
        shrinking = vb.get('shrinking_bars', [])
        high_vol = vb.get('high_vol_bars', [])
        low_vol = vb.get('low_vol_bars', [])
        flat = vb.get('flat_bars', [])
        ladder_up = vb.get('ladder_up', [])
        ladder_down = vb.get('ladder_down', [])

        lines.append("**量柱形态**：")
        if doubling:
            lines.append(f"  - 倍量柱：最近 {doubling[-1]['date']}（{doubling[-1]['ratio']}x）")
        if shrinking:
            lines.append(f"  - 缩量柱：最近 {shrinking[-1]['date']}（{shrinking[-1]['ratio']}x）")
        if high_vol:
            lines.append(f"  - 高量柱：{len(high_vol)} 根，最近 {high_vol[-1]['date']}")
        if low_vol:
            lines.append(f"  - 低量柱：{len(low_vol)} 根，最近 {low_vol[-1]['date']}")
        if flat:
            lines.append(f"  - 平量柱：{len(flat)} 根")
        if ladder_up:
            lines.append(f"  - 梯量上升：{len(ladder_up)} 组，最近 {ladder_up[-1]['start_date']}~{ladder_up[-1]['end_date']}")
        if ladder_down:
            lines.append(f"  - 梯量下降：{len(ladder_down)} 组，最近 {ladder_down[-1]['start_date']}~{ladder_down[-1]['end_date']}")
        if not any([doubling, shrinking, high_vol, low_vol, flat, ladder_up, ladder_down]):
            lines.append("  - 无明显量柱形态特征")
        lines.append("")

        # 关键柱
        kb = analysis.get('key_bars', {})
        golden = kb.get('golden_bars', [])
        marshal = kb.get('marshal_bars', [])
        general = kb.get('general_bars', [])
        lines.append("**关键柱**：")
        if golden:
            lines.append(f"  - 黄金柱：{golden[-1]['date']}，回调{golden[-1]['drawdown_ratio']:.0%}实体，强支撑")
        if marshal:
            lines.append(f"  - 元帅柱：{marshal[-1]['date']}，回调{marshal[-1]['drawdown_ratio']:.0%}实体")
        if general:
            lines.append(f"  - 将军柱：{general[-1]['date']}，回调{general[-1]['drawdown_ratio']:.0%}实体")
        if not golden and not marshal and not general:
            lines.append("  - 近期无关键柱信号")
        lines.append("")

        # 量线
        ql = analysis.get('quantity_lines', {})
        peak_lines = ql.get('peak_lines', [])
        valley_lines = ql.get('valley_lines', [])
        concave = ql.get('concave_lines', [])
        general_lines = ql.get('general_lines', [])
        lines.append("**量线体系**：")
        if peak_lines:
            for pl in peak_lines[-3:]:
                lines.append(f"  - 峰顶线：{pl['price']} 元（{pl['count']}点确认）")
        if valley_lines:
            for vl in valley_lines[-3:]:
                lines.append(f"  - 谷底线：{vl['price']} 元（{vl['count']}点确认）")
        if concave:
            for cl in concave[-2:]:
                lines.append(f"  - 凹口平衡线：{cl['price']} 元")
        if general_lines:
            for gl in general_lines[-3:]:
                lines.append(f"  - {gl['type']}：{gl['price']} 元（触及{gl['touches']}次，{gl['strength']}）")
        if not peak_lines and not valley_lines and not concave and not general_lines:
            lines.append("  - 量线数据不足，需更多历史K线")
        lines.append("")

        # 精准线
        pl = analysis.get('precision_lines', {})
        precise_peaks = pl.get('precise_peak_lines', [])
        precise_valleys = pl.get('precise_valley_lines', [])
        lines.append("**精准线**：")
        if precise_peaks:
            for ppl in precise_peaks[-3:]:
                lines.append(f"  - 精准峰顶线：{ppl['line_price']} 元（精准度{ppl['precision_score']:.0%}，触及{ppl['touch_count']}次）")
        if precise_valleys:
            for pvl in precise_valleys[-3:]:
                lines.append(f"  - 精准谷底线：{pvl['line_price']} 元（精准度{pvl['precision_score']:.0%}，触及{pvl['touch_count']}次）")
        if not precise_peaks and not precise_valleys:
            lines.append("  - 暂无精准线确认")
        lines.append("")

        # 综合信号
        signals = analysis.get('signals', [])
        if signals:
            lines.append("**综合信号**：")
            for sig in signals[:5]:
                conf = sig.get('confidence', 0)
                lines.append(f"  - [{sig['subtype']}] {sig['detail']}（置信度{conf:.0%}）→ {sig.get('action', '')}")
        else:
            lines.append("**综合信号**：暂无明确信号")
        lines.append("")

        return '\n'.join(lines)


# ================================================================
# 单例 + 缓存
# ================================================================

liangxue_engine = LiangXueEngine(lookback=30)
LIANGXUE_CACHE_PATH = '/workspace/行情数据库/liangxue_cache.json'


def compute_liangxue_and_save(stocks: Optional[Dict] = None) -> str:
    """计算所有股票的量学战法信号，保存到 liangxue_cache.json。"""
    if stocks is None:
        try:
            from config import HOLDINGS, WATCH_LIST
            stocks = {**HOLDINGS, **WATCH_LIST}
        except ImportError:
            stocks = {
                'sh603516': '淳中科技', 'sh601138': '工业富联', 'sz002156': '通富微电',
                'sh601231': '环旭电子', 'sz300476': '胜宏科技', 'sh603283': '赛腾股份',
                'sz300394': '天孚通信', 'sh600584': '长电科技',
            }

    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stocks': {},
    }

    for sym, info in stocks.items():
        name = getattr(info, 'name', info) if hasattr(info, 'name') else info
        analysis = liangxue_engine.full_analysis(sym)
        analysis['name'] = name
        result['stocks'][sym] = analysis

    with open(LIANGXUE_CACHE_PATH, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return LIANGXUE_CACHE_PATH


def main():
    import argparse
    parser = argparse.ArgumentParser(description='黑马王子量学战法引擎')
    parser.add_argument('--save', action='store_true', help='计算结果保存到 liangxue_cache.json')
    parser.add_argument('--symbol', type=str, help='指定股票分析')
    args = parser.parse_args()

    syms = {}
    if args.symbol:
        syms = {args.symbol: args.symbol}
    else:
        try:
            from config import HOLDINGS, WATCH_LIST
            syms = {**HOLDINGS, **WATCH_LIST}
        except ImportError:
            syms = {
                'sh603516': '淳中科技', 'sh601138': '工业富联', 'sz002156': '通富微电',
                'sh601231': '环旭电子', 'sz300476': '胜宏科技', 'sh603283': '赛腾股份',
                'sz300394': '天孚通信', 'sh600584': '长电科技',
            }

    print("=" * 80)
    print("黑马王子量学战法引擎 v1.0")
    print("=" * 80)

    for sym, name in syms.items():
        print(f"\n{'='*40}")
        print(f"【{name}】（{sym}）")
        print(f"{'='*40}")
        text = liangxue_engine.get_summary_text(sym)
        print(text)

    if args.save:
        path = compute_liangxue_and_save(syms)
        print(f"\n缓存已保存: {path}")


if __name__ == '__main__':
    main()
