# -*- coding: utf-8 -*-
"""黑马王子张得一量学战法信号引擎 v2.0

实现量学核心战法体系：
  - 量柱形态：高量柱、低量柱、倍量柱、平量柱、梯量柱、缩量柱、阴量柱
  - 高量柱战法：位置判定、右确认机制、量化/主力意图识别
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

        # 预填充 _prev_volume 供 _bar_features 使用
        for i, k in enumerate(kl):
            k['_prev_volume'] = kl[i - 1].get('volume', 0) if i > 0 else 0

        # ---- 1. 高量柱：近 lookback 日最高量 ----
        # 额外用60日窗口做位置判定和年内涨幅
        pos_lookback = min(60, n)

        for i in range(max(0, n - self.lookback), n):
            window = vols[max(0, i - self.lookback + 1):i + 1]
            if max(window) > 0 and vols[i] >= max(window) * 0.98:
                item = {
                    'date': dates[i],
                    'index': i,
                    'volume': vols[i],
                    'ratio': round(vols[i] / _mean(window), 2) if _mean(window) > 0 else 0,
                }
                # --- 位置判定：当日收盘在60日区间中的相对位置 ---
                pos_window = kl[max(0, i - pos_lookback + 1):i + 1]
                ph = max(k.get('high', 0) for k in pos_window) if pos_window else 0
                pl = min(k.get('low', 0) for k in pos_window) if pos_window else 0
                pr = kl[i].get('close', 0)
                price_range = ph - pl
                if price_range > 0:
                    item['price_position'] = round((pr - pl) / price_range, 3)
                else:
                    item['price_position'] = 0.5
                # --- 年内/周期涨幅 ---
                if i >= pos_lookback:
                    start_close = pos_window[0].get('close', 0)
                    if start_close > 0:
                        item['period_return'] = round((pr - start_close) / start_close, 4)
                    else:
                        item['period_return'] = 0.0
                else:
                    # 数据不足，用可用区间
                    avail = kl[:i + 1]
                    start_close = avail[0].get('close', 0)
                    if start_close > 0:
                        item['period_return'] = round((pr - start_close) / start_close, 4)
                    else:
                        item['period_return'] = 0.0
                # --- K线形态特征 ---
                item.update(self._bar_features(kl[i]))
                results['summary']['high_vol_bars'].append(item)

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

    def _bar_features(self, k: Dict) -> Dict:
        """提取单根K线的形态特征，用于意图分析。"""
        open_p = k.get('open', 0)
        high_p = k.get('high', 0)
        low_p = k.get('low', 0)
        close_p = k.get('close', 0)
        volume = k.get('volume', 0)
        amount = k.get('amount', 0)
        tr = k.get('turnover_ratio', 0)
        total_range = high_p - low_p if high_p > low_p else 1

        body = close_p - open_p
        is_yang = body >= 0
        abs_body = abs(body)

        # 上影线 / 下影线 / 实体占比
        upper_shadow = high_p - max(close_p, open_p)
        lower_shadow = min(close_p, open_p) - low_p
        body_pct = abs_body / total_range if total_range > 0 else 0
        upper_pct = upper_shadow / total_range if total_range > 0 else 0
        lower_pct = lower_shadow / total_range if total_range > 0 else 0

        # 量比（当日量 / 前一日量）
        prev_vol = k.get('_prev_volume', 0)
        vol_ratio = volume / prev_vol if prev_vol > 0 else 0.0

        return {
            'is_yang': is_yang,
            'body': round(body, 4),
            'abs_body': round(abs_body, 4),
            'upper_shadow': round(upper_shadow, 4),
            'lower_shadow': round(lower_shadow, 4),
            'body_pct': round(body_pct, 3),
            'upper_pct': round(upper_pct, 3),
            'lower_pct': round(lower_pct, 3),
            'turnover_ratio': round(tr, 2) if tr else 0.0,
            'amount': round(amount, 2) if amount else 0.0,
            'vol_ratio': round(vol_ratio, 2),
            'total_range': round(total_range, 4),
        }

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
# 四、高量柱意图分析：右确认 + 量化/主力行为识别
# ================================================================

class RightConfirmAnalyzer:
    """高量柱右确认分析器

    核心逻辑（黑马王子《量柱擒涨停》）：
    - 高量柱后1~3日不破高量柱最低点 → 看涨确认（主力护盘）
    - 高量柱后1~3日跌破高量柱最低点 → 看跌确认（主力出货）
    - 缩量不破 → 强确认（主力锁仓，置信度↑）
    - 放量跌破 → 强出货（置信度↑，方向↓）
    """

    def __init__(self, confirm_days: int = 3, shrink_threshold: float = 0.7):
        self.confirm_days = confirm_days
        self.shrink_threshold = shrink_threshold  # 缩量判定阈值

    def analyze(self, kl: List[Dict], hb: Dict) -> Dict:
        """对单个高量柱进行右确认分析，返回确认结果。"""
        idx = hb['index']
        n = len(kl)
        if idx + 1 >= n:
            return {'status': '当日，无法确认', 'direction': 'unknown', 'confidence': 0.0}

        hb_low = hb.get('low', kl[idx].get('low', 0))
        hb_close = hb.get('close', kl[idx].get('close', 0))
        hb_vol = hb.get('volume', kl[idx].get('volume', 0))
        hb_date = hb.get('date', '')

        # 检查后续 confirm_days 根K线
        confirm_bars = kl[idx + 1:idx + 1 + self.confirm_days]
        if not confirm_bars:
            return {'status': '数据不足', 'direction': 'unknown', 'confidence': 0.0}

        # 逐日检查：是否跌破高量柱低点
        broke_low = False
        break_idx = -1
        for j, bar in enumerate(confirm_bars):
            if bar.get('low', 0) < hb_low:
                broke_low = True
                break_idx = j
                break

        # 统计后续K线的涨跌和量能
        up_count = sum(1 for b in confirm_bars if b.get('close', 0) >= b.get('open', 0))
        down_count = len(confirm_bars) - up_count
        avg_confirm_vol = _mean([b.get('volume', 0) for b in confirm_bars]) if confirm_bars else 0
        shrink_flag = avg_confirm_vol < hb_vol * self.shrink_threshold if hb_vol > 0 else False

        # 判断方向
        if broke_low:
            break_bar = confirm_bars[break_idx]
            if break_bar.get('volume', 0) > hb_vol * 0.9:
                direction = 'strong_down'  # 放量跌破，强出货
                status = f'放量跌破（{break_bar.get("day","")}），主力出货'
            else:
                direction = 'down'
                status = f'跌破高量柱低点（{break_bar.get("day","")}），趋势转弱'
            confidence = 0.75 if direction == 'strong_down' else 0.6
        else:
            # 未跌破，检查强度
            if shrink_flag:
                direction = 'strong_up'  # 缩量不破，强看涨
                status = f'缩量不破高量柱低点，主力锁仓确认'
                confidence = 0.8
            elif up_count >= len(confirm_bars):
                direction = 'up'
                status = '连续上涨，未破低点，多头占优'
                confidence = 0.65
            else:
                direction = 'neutral'
                status = '未破低点但走势杂乱，观察中'
                confidence = 0.4

        return {
            'status': status,
            'direction': direction,
            'confidence': confidence,
            'broke_low': broke_low,
            'break_date': confirm_bars[break_idx].get('day', '') if broke_low and break_idx >= 0 else '',
            'confirm_days': len(confirm_bars),
            'up_count': up_count,
            'down_count': down_count,
            'shrink_flag': shrink_flag,
            'avg_confirm_vol': round(avg_confirm_vol, 0),
            'hb_low': hb_low,
            'hb_close': hb_close,
        }


class HighVolIntentAnalyzer:
    """高量柱意图分析器：量化资金 vs 主力资金

    意图分类逻辑：
    ┌─────────────────────────────────────────────────────────────┐
    │  阳线高量柱 + 低换手(<4%) + 实体饱满(body_pct>0.5)         │
    │       → 主力吸筹（谨慎看涨）                                │
    ├─────────────────────────────────────────────────────────────┤
    │  阳线高量柱 + 高换手(>6%) + 下影线长(lower_pct>0.3)        │
    │       → 主力拉升（试探抛压，看涨）                          │
    ├─────────────────────────────────────────────────────────────┤
    │  阴线高量柱 + 高换手(>6%) + 长上影(upper_pct>0.3)         │
    │       → 量化资金出货（看跌）                                │
    ├─────────────────────────────────────────────────────────────┤
    │  阴线高量柱 + 高换手(>6%) + 实体大(body_pct>0.4)          │
    │       → 主力砸盘出货（强看跌）                              │
    ├─────────────────────────────────────────────────────────────┤
    │  阳线高量柱 + 极高换手(>8%) + 上影线长                     │
    │       → 量化资金对倒做T（中性偏空）                         │
    ├─────────────────────────────────────────────────────────────┤
    │  高位高量柱(价格位置>0.7) + 年内涨幅>30%                   │
    │       → 主力出货风险（无论阴阳）                            │
    └─────────────────────────────────────────────────────────────┘
    """

    # 阈值参数
    LOW_TURN = 4.0      # 低换手阈值（%）
    MID_TURN = 6.0      # 中换手阈值（%）
    HIGH_TURN = 8.0     # 高换手阈值（%）
    HIGH_PRICE_POS = 0.7   # 高位判定（价格在60日区间上部）
    YTD_HIGH_RETURN = 0.30  # 年内涨幅警戒线

    def analyze(self, hb: Dict, rc: Dict, kl: List[Dict]) -> Dict:
        """综合分析单根高量柱的意图，返回意图分析结果。"""
        features = hb.get('_features', {})
        if not features:
            return {'intent': 'unknown', 'reason': '数据不足', 'confidence': 0.0}

        is_yang = features.get('is_yang', True)
        body_pct = features.get('body_pct', 0.5)
        upper_pct = features.get('upper_pct', 0.0)
        lower_pct = features.get('lower_pct', 0.0)
        tr = features.get('turnover_ratio', 0.0)
        price_pos = hb.get('price_position', 0.5)
        period_ret = hb.get('period_return', 0.0)
        vol_ratio = features.get('vol_ratio', 1.0)

        direction = rc.get('direction', 'unknown')
        rc_conf = rc.get('confidence', 0.0)

        # ---- 第一步：高位风险过滤（出货优先判断） ----
        is_high_position = price_pos > self.HIGH_PRICE_POS
        is_high_return = period_ret > self.YTD_HIGH_RETURN
        high_risk = is_high_position and is_high_return

        # ---- 第二步：量化资金特征判定 ----
        quant_signals = []
        is_quant = False
        if tr > self.HIGH_TURN and upper_pct > 0.25:
            quant_signals.append('高换手+长上影（对倒出货特征）')
            is_quant = True
        if tr > self.MID_TURN and vol_ratio > 1.5 and abs(body_pct - 0.5) < 0.2:
            quant_signals.append('量比放大+实体居中（算法做T特征）')
            is_quant = True
        if is_yang and tr > self.MID_TURN and upper_pct > lower_pct and upper_pct > 0.2:
            quant_signals.append('阳线冲高回落（量化拉高出货）')
            is_quant = True

        # ---- 第三步：主力资金特征判定 ----
        main_force_signals = []
        is_main_force = False
        if is_yang and tr < self.LOW_TURN and body_pct > 0.5:
            main_force_signals.append('低换手大实体阳线（主力锁仓吸筹）')
            is_main_force = True
        if is_yang and tr > self.MID_TURN and lower_pct > 0.25:
            main_force_signals.append('放量下影线（主力承接试探）')
            is_main_force = True
        if is_yang and tr < self.MID_TURN and direction == 'strong_up':
            main_force_signals.append('缩量右确认（主力控盘）')
            is_main_force = True

        # ---- 第四步：综合意图判定 ----
        if high_risk and not is_yang:
            intent = '出货'
            intent_detail = '高位阴线高量柱，主力出货风险最高'
            confidence = min(0.85, rc_conf + 0.1)
        elif high_risk and is_yang and is_quant:
            intent = '出货'
            intent_detail = '高位阳线但量化特征明显，疑似拉高出货'
            confidence = min(0.75, rc_conf + 0.05)
        elif is_main_force and direction in ('strong_up', 'up'):
            intent = '吸筹'
            intent_detail = '主力吸筹特征明确，右确认看涨'
            confidence = min(0.85, rc_conf + 0.15)
        elif is_main_force and direction == 'neutral':
            intent = '洗盘'
            intent_detail = '主力洗盘震荡，等待方向选择'
            confidence = 0.5
        elif is_quant:
            intent = '量化对倒'
            intent_detail = '量化资金特征明显，方向待确认'
            confidence = 0.4
        elif direction == 'strong_down':
            intent = '砸盘'
            intent_detail = '放量跌破高量柱低点，主力砸盘'
            confidence = 0.8
        elif direction == 'down':
            intent = '出货'
            intent_detail = '跌破高量柱低点，趋势转弱'
            confidence = 0.65
        elif direction == 'strong_up':
            intent = '拉升'
            intent_detail = '缩量不破，主力拉升确认'
            confidence = 0.75
        else:
            intent = '观望'
            intent_detail = '暂无明确意图信号'
            confidence = 0.3

        # 量化信号叠加调整
        if is_quant and intent not in ('出货', '砸盘'):
            intent = '量化混作'
            intent_detail += '（叠加量化资金活动）'
            confidence = min(confidence + 0.05, 0.7)

        return {
            'intent': intent,
            'intent_detail': intent_detail,
            'confidence': round(confidence, 2),
            'is_quant': is_quant,
            'is_main_force': is_main_force,
            'quant_signals': quant_signals,
            'main_force_signals': main_force_signals,
            'high_risk': high_risk,
            'price_position': price_pos,
            'period_return': period_ret,
            'direction': direction,
            'right_confirm': rc,
        }


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
        self.right_confirm = RightConfirmAnalyzer(confirm_days=3, shrink_threshold=0.7)
        self.intent_analyzer = HighVolIntentAnalyzer()

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

        # 高量柱右确认 + 意图分析
        result['high_vol_analysis'] = self._analyze_high_vol_bars(kl, result['volume_bars'])

        # 生成综合信号摘要
        result['signals'] = self._generate_signals(result)

        return result

    def _analyze_high_vol_bars(self, kl: List[Dict], vb: Dict) -> Dict:
        """对每个高量柱做右确认 + 意图分析。"""
        high_vol = vb.get('summary', {}).get('high_vol_bars', [])
        if not high_vol:
            return {'bars': [], 'latest_intent': None}

        analyzed = []
        for hb in high_vol:
            # _prev_volume 已在 detect_all 中预填充，直接从 kl 取特征
            idx = hb['index']
            if idx > 0 and idx < len(kl):
                hb['_features'] = self.volume_detector._bar_features(kl[idx])
            rc = self.right_confirm.analyze(kl, hb)
            intent = self.intent_analyzer.analyze(hb, rc, kl)
            analyzed.append({
                'date': hb['date'],
                'index': hb['index'],
                'right_confirm': rc,
                'intent': intent,
            })

        return {
            'bars': analyzed,
            'latest_intent': analyzed[-1] if analyzed else None,
        }

    def _generate_signals(self, analysis: Dict) -> List[Dict]:
        """从各项检测结果中提取交易信号。"""
        signals = []

        # ---- 量柱信号 ----
         vb = analysis.get('volume_bars', {})
         doubling = vb.get('summary', {}).get('doubling_bars', [])
         shrinking = vb.get('summary', {}).get('shrinking_bars', [])
         high_vol = vb.get('summary', {}).get('high_vol_bars', [])
         low_vol = vb.get('summary', {}).get('low_vol_bars', [])

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
            latest_hv = high_vol[-1]
            hva = analysis.get('high_vol_analysis', {})
            lv = hva.get('latest_intent')
            if lv:
                intent = lv.get('intent', {})
                rc = lv.get('right_confirm', {})
                detail_parts = [f"近{self.lookback}日最高量柱"]
                pos = latest_hv.get('price_position', 0.5)
                if pos > 0.7:
                    detail_parts.append('高位')
                elif pos < 0.3:
                    detail_parts.append('低位')
                intent_label = intent.get('intent', '')
                if intent_label:
                    detail_parts.append(f"意图:{intent_label}")
                rc_dir = rc.get('direction', '')
                if rc_dir and rc_dir != 'unknown':
                    rc_labels = {'strong_up': '右确认↑', 'up': '右确认▲', 'down': '右确认↓', 'strong_down': '右确认↓↓'}
                    detail_parts.append(rc_labels.get(rc_dir, ''))
                detail = '，'.join(p for p in detail_parts if p)
                conf = min(intent.get('confidence', 0.4), 0.85)
                action_map = {
                    '吸筹': '关注建仓机会，设高量柱低点为防守线',
                    '拉升': '趋势延续，持有',
                    '出货': '警惕出货，跌破高量柱低点离场',
                    '砸盘': '果断止损，高量柱低点为止损位',
                    '洗盘': '震荡整理，观望等待方向',
                    '量化对倒': '量化资金活动，谨慎参与',
                    '量化混作': '量化与主力交织，观望为主',
                    '观望': '暂无明确信号，继续观察',
                }
                action = action_map.get(intent_label, '观察量能持续性')
            else:
                detail = f"近{self.lookback}日最高量柱，位置需结合后续走势判断"
                conf = 0.4
                action = '观察量能持续性'
            signals.append({
                'type': '量柱信号',
                'subtype': '高量柱',
                'date': latest_hv.get('date', ''),
                'detail': detail,
                'confidence': conf,
                'action': action,
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

        # 高量柱意图分析
        hva = analysis.get('high_vol_analysis', {})
        hv_bars = hva.get('bars', [])
        if hv_bars:
            lines.append("**高量柱意图分析**：")
            for hv in hv_bars[-3:]:
                intent = hv.get('intent', {})
                rc = hv.get('right_confirm', {})
                hb_idx = hv.get('index', 0)
                hb = next((b for b in high_vol if b.get('index') == hb_idx), {})
                pos = hb.get('price_position', 0.5)
                pos_label = '低位' if pos < 0.3 else ('高位' if pos > 0.7 else '中位')
                ret = hb.get('period_return', 0)
                ret_str = f"（周期涨幅{ret:+.0%}）" if ret != 0 else ""
                lines.append(f"  - {hv['date']}：意图{intent.get('intent','?')}（{intent.get('intent_detail','')}）{ret_str}，价格位置{pos_label}({pos:.0%})")
                lines.append(f"    右确认：{rc.get('status','?')}，方向{rc.get('direction','?')}，置信度{rc.get('confidence',0):.0%}")
                qs = intent.get('quant_signals', [])
                ms = intent.get('main_force_signals', [])
                if qs:
                    lines.append(f"    量化特征：{'；'.join(qs)}")
                if ms:
                    lines.append(f"    主力特征：{'；'.join(ms)}")
                if intent.get('high_risk'):
                    lines.append(f"    ⚠ 高位出货风险：年内涨幅{ret:.0%}，价格位置{pos:.0%}")
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
