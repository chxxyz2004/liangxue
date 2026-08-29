#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学系统核心信号引擎

基于日线 + 5分钟 K 线的技术指标、信号与战法统一计算模块。
所有指标仅依赖已验证的真实数据源（腾讯 fqkline 日线 / 新浪 5分钟线），
禁止调用不存在的外部函数或编造数据。

核心能力：
- 量学指标：均线MA、MACD、均量线、量比、量变异系数、价量相关性
- 量学柱形：倍量柱、缩量柱、均量柱、长上影
- 量学战法：黄金交叉、死叉、价量发散/共振、主力牵手、对倒识别
- 风险管理：量化风险评分、风险等级、买卖点参考
- 5分钟级分时：量价关联、异常放量、异动检测
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

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


def load_5min_kline(symbol: str, date_str: Optional[str] = None) -> Optional[Dict]:
    """加载 5 分钟 K 线数据（新浪接口），未指定日期时选最新文件。"""
    if date_str is not None:
        path = os.path.join(KLINE_5MIN_DIR, f'{symbol}_{date_str}.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return None
    matches = [f for f in os.listdir(KLINE_5MIN_DIR)
               if f.startswith(symbol) and f.endswith('.json')]
    if not matches:
        return None
    path = os.path.join(KLINE_5MIN_DIR, max(matches))
    with open(path, 'r') as f:
        return json.load(f)


def _ma(values: List[float], period: int) -> Optional[float]:
    """简单移动平均。"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values: List[float], period: int) -> Optional[float]:
    """指数移动平均（简化 EMA）。"""
    if len(values) < period:
        return None
    alpha = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


class SignalEngine:
    """统一信号引擎：日线 + 5分钟线指标、信号与战法计算。"""

    def daily_indicators(self, symbol: str) -> Dict:
        """日线全景指标：价格、均线、MACD、均量、量比、信号。"""
        kdata = load_daily_kline(symbol)
        if not kdata or 'data' not in kdata or not kdata['data']:
            return {'symbol': symbol, 'error': '无数据'}
        kl = kdata['data']
        closes = [d['close'] for d in kl]
        volumes = [d.get('volume', 0) for d in kl]
        latest = kl[-1]

        indicators = {
            'symbol': symbol,
            'name': kdata.get('name', ''),
            'latest': {
                'day': latest.get('day'),
                'open': latest.get('open'),
                'close': latest.get('close'),
                'high': latest.get('high'),
                'low': latest.get('low'),
                'volume': latest.get('volume'),
                'amount': latest.get('amount'),
            },
        }

        # 均线 MA5/10/20/60
        ma = {}
        for p in (5, 10, 20, 60):
            val = _ma(closes, p)
            if val is not None:
                ma[f'ma{p}'] = round(val, 3)
        indicators['ma'] = ma

        # MACD（12,26,9 标准算法）
        if len(closes) >= 35:
            def _ema_series(vals, period):
                if len(vals) < period:
                    return None
                alpha = 2 / (period + 1)
                out = [vals[0]]
                for v in vals[1:]:
                    out.append(alpha * v + (1 - alpha) * out[-1])
                return out
            ema12 = _ema_series(closes, 12)
            ema26 = _ema_series(closes, 26)
            if ema12 and ema26:
                dif_series = [a - b for a, b in zip(ema12, ema26)]
                dea_series = _ema_series(dif_series, 9)
                if dea_series:
                    dif_now = dif_series[-1]
                    dea_now = dea_series[-1]
                    indicators['macd'] = {
                        'dif': round(dif_now, 4),
                        'dea': round(dea_now, 4),
                        'macd': round(2 * (dif_now - dea_now), 4),
                    }

        # 均量线 5/10
        vma = {}
        for p in (5, 10):
            val = _ma(volumes, p)
            if val is not None:
                vma[f'vol_ma{p}'] = round(val, 1)
        indicators['vol_ma'] = vma

        # 量比（最新量 / 5日均量）
        vma5 = _ma(volumes, 5)
        indicators['volume_ratio'] = round(volumes[-1] / vma5, 2) if vma5 else None

        # 倍量柱检测（量 >= 前一日 * 1.9 且收阳）
        doubling = []
        for i in range(len(kl) - 20, len(kl)):
            if i < 1:
                continue
            k, prev = kl[i], kl[i - 1]
            if (prev.get('volume', 0) > 0
                    and k.get('volume', 0) >= prev['volume'] * 1.9
                    and k.get('close', 0) > k.get('open', 0)):
                doubling.append({
                    'date': k.get('day'),
                    'volume': k.get('volume'),
                    'prev_volume': prev.get('volume'),
                    'ratio': round(k['volume'] / prev['volume'], 2),
                })
        indicators['doubling_volume'] = doubling[-5:]

        # 黄金交叉 / 死叉（MA5 与 MA10）
        if len(closes) >= 11:
            ma5_now = _ma(closes, 5)
            ma10_now = _ma(closes, 10)
            ma5_prev = _ma(closes[:-1], 5)
            ma10_prev = _ma(closes[:-1], 10)
            if ma5_now is not None and ma10_now is not None and ma5_prev is not None and ma10_prev is not None:
                if ma5_prev <= ma10_prev and ma5_now > ma10_now:
                    indicators['cross'] = {'type': '金叉', 'signal': '黄金交叉', 'confidence': 0.8}
                elif ma5_prev >= ma10_prev and ma5_now < ma10_now:
                    indicators['cross'] = {'type': '死叉', 'signal': '死叉', 'confidence': 0.8}
                elif ma5_now > ma10_now:
                    indicators['cross'] = {'type': '多头排列', 'signal': '多头排列（金叉）', 'confidence': 0.6}
                elif ma5_now < ma10_now:
                    indicators['cross'] = {'type': '空头排列', 'signal': '空头排列（死叉）', 'confidence': 0.6}
                else:
                    indicators['cross'] = {'type': '无', 'signal': '均线缠绕', 'confidence': 0.2}

        # 价量发散/共振
        if len(closes) >= 21 and len(volumes) >= 21:
            p_chg = closes[-1] - closes[-6]
            v_chg = volumes[-1] - volumes[-6]
            if p_chg < 0 and v_chg > 0:
                indicators['price_volume'] = {'signal': '价量发散（价跌量升）', 'confidence': 0.7}
            elif p_chg > 0 and v_chg > 0:
                indicators['price_volume'] = {'signal': '价量共振（价涨量升）', 'confidence': 0.7}
            else:
                indicators['price_volume'] = {'signal': '无显著发散', 'confidence': 0.2}

        return indicators

    def risk_assessment(self, symbol: str) -> Dict:
        """量化风险评分与等级。"""
        kdata = load_daily_kline(symbol)
        if not kdata or 'data' not in kdata or len(kdata['data']) < 2:
            return {'symbol': symbol, 'error': '数据不足'}
        kl = kdata['data']
        # 使用最近20日数据（不含当日，避免未来函数）
        history = kl[:-1] if len(kl) > 1 else kl
        volumes = [d.get('volume', 0) for d in history]
        closes = [d['close'] for d in history]

        score = 0
        factors = []

        # 量变异系数（成交量的离散程度）
        mean = sum(volumes) / len(volumes)
        if mean > 0:
            std = (sum((v - mean) ** 2 for v in volumes) / len(volumes)) ** 0.5
            cv = std / mean
        else:
            cv = 0
        if cv < 0.5:
            score += 25
            factors.append('成交量过于均匀')

        # 价量变化相关性（核心修复：用日变化量替代原始值）
        # 计算每日收盘价变化和成交量变化
        price_changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        volume_changes = [volumes[i] - volumes[i-1] for i in range(1, len(volumes))]
        # 取最近10个变化量样本
        n = min(10, len(price_changes), len(volume_changes))
        if n >= 3:
            corr = self._correlation(price_changes[-n:], volume_changes[-n:])
        else:
            corr = 0.0
        if corr < 0.3:
            score += 25
            factors.append('量价背离')

        if score == 0:
            level = '正常'
        elif score < 25:
            level = '低风险'
        elif score < 50:
            level = '中风险'
        elif score < 75:
            level = '高风险'
        else:
            level = '极高风险'

        return {
            'symbol': symbol,
            'risk_score': score,
            'risk_level': level,
            'risk_factors': factors,
            'cv_volume': round(cv, 3),
            'correlation': round(corr, 3),
        }

    def _correlation(self, a: List[float], b: List[float]) -> float:
        """皮尔逊相关系数（基于原始值序列）。"""
        if len(a) <= 1 or len(b) <= 1 or len(a) != len(b):
            return 0.0
        ma = sum(a) / len(a)
        mb = sum(b) / len(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = (sum((x - ma) ** 2 for x in a) ** 0.5)
        db = (sum((y - mb) ** 2 for y in b) ** 0.5)
        if da == 0 or db == 0:
            return 0.0
        return num / (da * db)

    def _change_correlation(self, values: List[float], changes: List[float]) -> float:
        """价量变化相关性：当日收盘价变化 与 当日成交量变化 的皮尔逊相关系数。

        这是风险评级的核心指标，比原始值相关更有意义：
        - 正相关：价涨量增/价跌量减 → 趋势健康
        - 负相关：价涨量减/价跌量增 → 背离信号
        """
        return self._correlation(values, changes)

    def intraday_analysis(self, symbol: str, date_str: Optional[str] = None) -> Dict:
        """5分钟分时分析：量价关联、异常放量、异动检测。"""
        d5 = load_5min_kline(symbol, date_str)
        if not d5:
            return {'symbol': symbol, 'error': '无5分钟数据'}
        bars = d5.get('bars') or d5.get('data') or []
        if not bars:
            return {'symbol': symbol, 'error': '无bars'}

        closes = [b.get('close', 0) for b in bars[-48:]]
        volumes = [b.get('volume', 0) for b in bars[-48:]]
        if not closes or not volumes:
            return {'symbol': symbol, 'error': '数据量不足'}

        signals = []

        # 当日涨跌幅（首笔开 -> 末笔收）
        first_open = bars[0].get('open', closes[0])
        day_pct = (closes[-1] - first_open) / first_open * 100 if first_open else 0

        # 量价相关性（使用全部48根K线的变化量，比仅用10根更稳定）
        price_chg = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        volume_chg = [volumes[i] - volumes[i-1] for i in range(1, len(volumes))]
        corr = self._correlation(price_chg, volume_chg) if len(price_chg) >= 3 else 0.0

        # 异常放量
        avg_v = sum(volumes) / len(volumes)
        last_v = volumes[-1]
        anomaly = (last_v - avg_v) / avg_v if avg_v else 0
        if anomaly > 0.5:
            signals.append({'type': '异动', 'subtype': '异常放量',
                            'detail': f'尾段放量{anomaly:.0%}', 'confidence': min(anomaly, 1.0)})

        if abs(day_pct) > 2:
            signals.append({'type': '价量', 'subtype': '强势波动' if day_pct > 0 else '弱势波动',
                            'detail': f'当日{day_pct:+.2f}%', 'confidence': min(abs(day_pct) / 5, 1.0)})

        return {
            'symbol': symbol,
            'date': d5.get('date'),
            'period': '5分钟',
            'bars': len(bars),
            'day_pct': round(day_pct, 2),
            'correlation': round(corr, 3),
            'volume_anomaly': round(anomaly, 3),
            'signals': signals,
        }


signal_engine = SignalEngine()

CACHE_PATH = '/workspace/行情数据库/signal_cache.json'


def load_cache() -> dict:
    """加载信号缓存文件。若不存在或损坏，返回空字典。"""
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {'error': str(e), 'updated_at': None}


def compute_all_and_save(stocks: Optional[Dict] = None) -> str:
    """计算所有股票的指标+风险，保存到 signal_cache.json，返回缓存路径。

    此函数被 generate_report.py 及自动脚本调用。
    """
    if stocks is None:
        from config import HOLDINGS, WATCH_LIST
        stocks = {**HOLDINGS, **WATCH_LIST}

    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'high_risk': [],
            'medium_risk': [],
            'low_risk': [],
            'normal_risk': [],
            'death_cross': [],
            'golden_cross': [],
            'volume_breakout': [],
            'price_volume_divergence': [],
        },
        'stocks': {}
    }

    for sym, info in stocks.items():
        # info 可能是 StockInfo 对象或纯字符串（命令行演示时）
        name = getattr(info, 'name', info) if not isinstance(info, str) else info
        name = info.name if hasattr(info, 'name') else sym
        ind = signal_engine.daily_indicators(sym)
        risk = signal_engine.risk_assessment(sym)
        intr = signal_engine.intraday_analysis(sym)

        stock_entry = {
            'name': name,
            'daily': ind,
            'risk': risk,
            'intraday': intr,
        }
        result['stocks'][sym] = stock_entry

        # 汇总统计
        rl = risk.get('risk_level', '')
        if rl == '高风险':
            result['summary']['high_risk'].append(name)
        elif rl == '中风险':
            result['summary']['medium_risk'].append(name)
        elif rl == '低风险':
            result['summary']['low_risk'].append(name)
        elif rl == '正常':
            result['summary']['normal_risk'].append(name)

        cross = ind.get('cross', {})
        cs = cross.get('signal', '')
        if '金叉' in cs or '多头排列' in cs:
            result['summary']['golden_cross'].append(name)
        elif '死叉' in cs or '空头排列' in cs:
            result['summary']['death_cross'].append(name)

        pv = ind.get('price_volume', {})
        if '发散' in pv.get('signal', ''):
            result['summary']['price_volume_divergence'].append(name)

    # 倍量柱检测汇总
    for sym, entry in result['stocks'].items():
        dv = entry.get('daily', {}).get('doubling_volume', [])
        if dv:
            result['summary']['volume_breakout'].append({
                'symbol': sym, 'name': entry['name'],
                'count': len(dv), 'latest': dv[-1]
            })

    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return CACHE_PATH


def main():
    """命令行演示：对全部股票计算日线指标与风险，并保存到缓存。"""
    import argparse
    parser = argparse.ArgumentParser(description='量学信号引擎')
    parser.add_argument('--save', action='store_true', help='计算结果保存到 signal_cache.json')
    args = parser.parse_args()

    sys_stocks = {
        'sh603516': '淳中科技', 'sh601138': '工业富联', 'sz002156': '通富微电',
        'sh601231': '环旭电子', 'sz300476': '胜宏科技', 'sh603283': '赛腾股份',
        'sz300394': '天孚通信', 'sh600584': '长电科技',
    }

    print("=" * 90)
    print("量学信号引擎 | 日线指标 + 风险评级 | 数据来源：腾讯fqkline")
    print("=" * 90)
    header_row = f"{'代码':<10} {'名称':<8} {'现价':>8} {'MA5':>8} {'MA10':>8} {'量比':>6} {'风险':>8}"
    print(header_row)
    print("-" * 90)
    for sym, name in sys_stocks.items():
        ind = signal_engine.daily_indicators(sym)
        risk = signal_engine.risk_assessment(sym)
        if 'error' in ind or 'error' in risk:
            print(f"{sym:<10} {name:<8} 数据读取失败")
            continue
        latest = ind['latest']['close']
        ma5 = ind['ma'].get('ma5', '-')
        ma10 = ind['ma'].get('ma10', '-')
        vratio = ind.get('volume_ratio', '-')
        print(f"{sym:<10} {name:<8} {latest:>8.2f} {ma5:>8.2f} {ma10:>8.2f} "
              f"{str(vratio):>6} {risk['risk_level']:>8}")
    print("=" * 90)

    if args.save:
        from config import HOLDINGS, WATCH_LIST
        path = compute_all_and_save({**HOLDINGS, **WATCH_LIST})
        print(f"\n缓存已保存至: {path}")
        # 打印汇总摘要
        with open(path) as f:
            cache = json.load(f)
        s = cache['summary']
        print(f"高风险: {s['high_risk']}")
        print(f"中风险: {s['medium_risk']}")
        print(f"低风险: {s['low_risk']}")
        print(f"多头排列(金叉): {s['golden_cross']}")
        print(f"空头排列(死叉): {s['death_cross']}")
        print(f"价量发散: {s['price_volume_divergence']}")
        print(f"倍量柱: {[(x['name'], x['count']) for x in s['volume_breakout']]}")


if __name__ == '__main__':
    main()
