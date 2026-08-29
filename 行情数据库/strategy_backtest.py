# -*- coding: utf-8 -*-
"""
量学战法回测框架 v3.0
覆盖：倍量柱 / 黄金柱 / 元帅柱 / 将军柱 四大战法
引入市场环境因子，动态调整策略参数
"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from liangxue_engine import KeyBarDetector, VolumeBarDetector, LiangXueEngine

KLINE_DIR = '/workspace/行情数据库/kline'
INDEX_CODES = ['sh000001', 'sz399001', 'sz399006']  # 上证、深证、创业板
STOCK_CODES = ['sh601138', 'sz300476', 'sz300394', 'sh603516', 'sz002156', 'sh600584', 'sh603283', 'sh601231']


# ================================================================
# 市场环境因子评估器
# ================================================================

class MarketEnvFactor:
    """
    市场环境因子：综合评估大盘趋势、成交量、市场宽度
    返回：环境得分(0-100) + 环境状态字符串
    """

    def __init__(self):
        self._cache = {}

    def load_index_kline(self, code):
        path = os.path.join(KLINE_DIR, f'{code}.json')
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f).get('data', [])

    def get_env_score(self, lookback=20):
        """
        计算综合环境得分（0-100分）
        分项：趋势方向(30分) + 成交量(30分) + 市场宽度(20分) + 波动率(20分)
        """
        scores = {}
        totals = 0

        for code in INDEX_CODES:
            kl = self.load_index_kline(code)
            if not kl or len(kl) < 60:
                continue

            closes = [float(k['close']) for k in kl]
            volumes = [int(k['volume']) for k in kl]
            n = len(closes)

            # --- 1. 趋势方向（30分）---
            ma5 = sum(closes[-5:]) / 5
            ma10 = sum(closes[-10:]) / 10
            ma20 = sum(closes[-20:]) / 20
            ma60 = sum(closes[-60:]) / 60

            trend_score = 0
            if ma5 > ma10 > ma20 > ma60:
                trend_score = 30       # 完美多头
            elif ma5 > ma10 > ma20:
                trend_score = 22       # 短期多头
            elif ma5 > ma10:
                trend_score = 12       # 弱多头
            elif ma5 < ma10 < ma20 < ma60:
                trend_score = 0        # 完美空头
            elif ma5 < ma10:
                trend_score = -5       # 弱空头
            else:
                trend_score = 5        # 震荡

            scores['trend'] = trend_score

            # --- 2. 成交量趋势（30分）---
            vol_ma5 = sum(volumes[-5:]) / 5
            vol_ma20 = sum(volumes[-20:]) / 20
            vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0

            if code == 'sh000001':
                vol_score = min(30, max(0, int((vol_ratio - 0.7) * 40)))
            elif code == 'sz399001':
                vol_score = min(30, max(0, int((vol_ratio - 0.7) * 40)))
            else:
                vol_score = min(30, max(0, int((vol_ratio - 0.6) * 45)))

            scores['volume'] = vol_score
            totals += vol_score

            # --- 3. 市场宽度（20分）---
            up_days = sum(1 for i in range(max(0, n-20), n) if closes[i] > closes[i-1] if i > 0)
            width_ratio = up_days / 20
            width_score = int(width_ratio * 20)
            scores['width'] = width_score
            totals += width_score

            # --- 4. 波动率稳定性（20分）---
            if n >= 20:
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(n-20, n)]
                std_vol = (sum(r**2 for r in returns) / len(returns)) ** 0.5
                if std_vol < 0.015:
                    vol_stability = 20
                elif std_vol < 0.025:
                    vol_stability = 14
                elif std_vol < 0.04:
                    vol_stability = 8
                else:
                    vol_stability = 2
            else:
                vol_stability = 10
            scores['volatility'] = vol_stability
            totals += vol_stability

        # 标准化到0-100
        if len(INDEX_CODES) == 3:
            env_score = totals / 3.0 * (100.0 / 100.0)
        else:
            env_score = totals

        env_score = max(0, min(100, env_score))

        if env_score >= 70:
            state = '强势牛市'
        elif env_score >= 50:
            state = '震荡偏多'
        elif env_score >= 30:
            state = '震荡偏弱'
        else:
            state = '弱势熊市'

        return {
            'score': round(env_score, 1),
            'state': state,
            'breakdown': scores,
            'timestamp': datetime.now().isoformat(),
        }

    def get_position_adjustment(self, env_score):
        """根据环境得分返回仓位调整系数"""
        if env_score >= 75:
            return {'factor': 1.0, 'max_pos': 0.8, 'reason': '强势牛市，满仓出击'}
        elif env_score >= 55:
            return {'factor': 0.75, 'max_pos': 0.6, 'reason': '震荡偏多，六成仓'}
        elif env_score >= 35:
            return {'factor': 0.5, 'max_pos': 0.4, 'reason': '震荡偏弱，四成仓'}
        elif env_score >= 20:
            return {'factor': 0.3, 'max_pos': 0.2, 'reason': '弱势市场，两成仓试探'}
        else:
            return {'factor': 0.0, 'max_pos': 0.0, 'reason': '熊市强制空仓'}

    def get_threshold_adjustment(self, env_score):
        """根据环境得分调整信号阈值"""
        adjustments = {}
        if env_score >= 70:
            # 牛市：降低入场门槛（更容易买入）
            adjustments['vol_ratio_min'] = 1.7    # 原版1.9
            adjustments['lookback_window'] = 40   # 原版30
            adjustments['min_drawdown'] = 0.15    # 原版1/3≈0.33
        elif env_score >= 40:
            # 震荡市：维持标准阈值
            adjustments['vol_ratio_min'] = 1.9
            adjustments['lookback_window'] = 30
            adjustments['min_drawdown'] = 0.33
        else:
            # 熊市：提高入场门槛（更严格）
            adjustments['vol_ratio_min'] = 2.2
            adjustments['lookback_window'] = 20
            adjustments['min_drawdown'] = 0.50
        return adjustments


# ================================================================
# 战法回测引擎
# ================================================================

class StrategyBacktest:
    """
    回测四大战法：倍量柱 / 黄金柱 / 元帅柱 / 将军柱
    每根K线只使用已发生的数据，绝不使用未来函数
    """

    def __init__(self, initial_capital=100000, commission_rate=0.0003, slippage=0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.market_env = MarketEnvFactor()

    def load_kline(self, code):
        path = os.path.join(KLINE_DIR, f'{code}.json')
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f).get('data', [])

    def backtest_volume_strategy(self, kl, strategy='all', env_score=None):
        """
        回测指定战法
        strategy: 'doubling'(倍量柱) | 'golden'(黄金柱) | 'marshal'(元帅柱) | 'general'(将军柱) | 'all'
        返回所有信号的收益分布
        """
        if not kl or len(kl) < 60:
            return []

        n = len(kl)
        results = []

        # 获取市场环境调整参数
        if env_score is None:
            env_info = self.market_env.get_env_score()
            env_score = env_info['score']
        adjustments = self.market_env.get_threshold_adjustment(env_score)

        vol_ratio_min = adjustments['vol_ratio_min']
        min_drawdown = adjustments['min_drawdown']

        cutoff = 0  # 全量数据回测，不限制搜索窗口

        # 检测倍量柱并分类
        doubling_bars = []
        for i in range(cutoff, n):
            if i == 0:
                continue
            v_prev = kl[i-1].get('volume', 0)
            v_curr = kl[i].get('volume', 0)
            if v_prev <= 0:
                continue
            ratio = v_curr / v_prev
            close_p, open_p = kl[i].get('close', 0), kl[i].get('open', 0)
            if ratio >= vol_ratio_min and close_p >= open_p:
                doubling_bars.append({
                    'index': i, 'date': kl[i].get('day', ''),
                    'ratio': round(ratio, 2),
                    'high': kl[i].get('high', 0), 'low': kl[i].get('low', 0),
                    'close': close_p, 'volume': v_curr,
                })

        # 对每个倍量柱，检测后续关键柱并计算收益
        for dbl in doubling_bars:
            dbl_idx = dbl['index']
            dbl_high = dbl['high']
            dbl_low = dbl['low']
            dbl_body = dbl_high - dbl_low
            if dbl_body <= 0:
                continue

            # 寻找关键柱（黄金/元帅/将军）
            key_bar = None
            key_type = None
            for j in range(dbl_idx + 1, min(dbl_idx + 10, n)):
                k = kl[j]
                k_vol = k.get('volume', 0)
                if k_vol >= dbl['volume'] * 0.9:
                    continue  # 未缩量

                drawdown = (dbl_high - k['low']) / dbl_body
                if drawdown > 1.0:
                    break  # 已破倍量柱低点，形态失效

                if drawdown < min_drawdown:
                    key_type = '黄金柱'
                elif drawdown <= 0.5:
                    key_type = '元帅柱' if drawdown >= 1/3 else '黄金柱'
                else:
                    key_type = '将军柱'

                key_bar = {
                    'index': j,
                    'date': k.get('day', ''),
                    'type': key_type,
                    'low': k['low'],
                    'high': k['high'],
                    'close': k['close'],
                    'drawdown': round(drawdown, 3),
                }
                break

            # 计算持仓收益：从关键柱次日开盘买入，持有5/10/20日
            if key_bar is None:
                continue

            # 策略过滤：如果指定了特定战法，只保留匹配的信号
            if strategy != 'all':
                type_map = {'golden': '黄金柱', 'marshal': '元帅柱', 'general': '将军柱', 'doubling': None}
                required_type = type_map.get(strategy)
                if required_type and key_type != required_type:
                    continue
                if not required_type:
                    pass  # 倍量柱策略：不过滤，保留所有倍量柱信号

            buy_idx = key_bar['index'] + 1
            if buy_idx >= n:
                continue

            buy_price = kl[buy_idx].get('open', kl[buy_idx].get('close', 0))
            if buy_price <= 0:
                continue

            # 实际买入价考虑滑点
            actual_buy = buy_price * (1 + self.slippage)

            hitrates = {}
            for hold_days in [5, 10, 20]:
                sell_idx = buy_idx + hold_days
                if sell_idx >= n:
                    continue

                sell_price = kl[sell_idx].get('close', kl[sell_idx].get('high', 0))
                actual_sell = sell_price * (1 - self.slippage)

                # 止损：亏损超过8%
                stop_loss_price = actual_buy * 0.92
                if sell_price < stop_loss_price:
                    actual_sell = stop_loss_price * (1 - self.slippage)

                # 止盈：盈利超过15%
                take_profit_price = actual_buy * 1.15
                if sell_price > take_profit_price and hold_days >= 5:
                    actual_sell = take_profit_price * (1 - self.slippage)

                gross_return = (actual_sell - actual_buy) / actual_buy
                commission = (actual_buy + actual_sell) * self.commission_rate
                net_return = gross_return - commission

                if hold_days not in hitrates:
                    hitrates[hold_days] = {'wins': 0, 'losses': 0, 'total_return': 0.0, 'trades': 0}
                hitrates[hold_days]['total_return'] += net_return
                hitrates[hold_days]['trades'] += 1
                if net_return > 0:
                    hitrates[hold_days]['wins'] += 1
                else:
                    hitrates[hold_days]['losses'] += 1

            results.append({
                'doubling_date': dbl['date'],
                'key_bar_date': key_bar['date'],
                'key_type': key_bar['type'],
                'drawdown': key_bar['drawdown'],
                'buy_price': round(actual_buy, 2),
                'hitrates': hitrates,
                'env_score': env_score,
            })

        return results

    def run_all_backtests(self):
        """对所有股票运行完整回测"""
        all_results = {}
        env_info = self.market_env.get_env_score()

        print(f"\n{'='*70}")
        print(f"  量学战法回测 v3.0 — 市场环境: {env_info['state']} (得分: {env_info['score']})")
        print(f"{'='*70}")

        for code in STOCK_CODES:
            kl = self.load_kline(code)
            if not kl:
                continue

            name_map = {
                'sh601138': '工业富联', 'sz300476': '胜宏科技', 'sz300394': '天孚通信',
                'sh603516': '淳中科技', 'sz002156': '通富微电', 'sh600584': '长电科技',
                'sh603283': '赛腾股份', 'sh601231': '环旭电子',
            }
            name = name_map.get(code, code)
            print(f"\n--- {code} {name} ---")

            strategies = ['doubling', 'golden', 'marshal', 'general']
            for strategy in strategies:
                results = self.backtest_volume_strategy(kl, strategy=strategy, env_score=env_info['score'])
                if not results:
                    print(f"  [{strategy}] 无信号")
                    continue

                # 汇总统计
                summary = self._summarize_results(results)
                all_results[f"{code}_{strategy}"] = summary
                short_name = {'doubling': '倍量', 'golden': '黄金柱', 'marshal': '元帅柱', 'general': '将军柱'}[strategy]
                print(f"  [{short_name}] 信号数={summary['total_signals']}, "
                      f"胜率={summary['win_rate']:.1f}%, "
                      f"平均收益={summary['avg_return']:.2%}, "
                      f"最大盈亏比={summary['max_profit_loss_ratio']:.2f}")

        return all_results, env_info

    def _summarize_results(self, results):
        """汇总回测结果"""
        if not results:
            return {'total_signals': 0, 'win_rate': 0, 'avg_return': 0, 'max_profit_loss_ratio': 0}

        total = sum(r['hitrates'].get(5, {}).get('trades', 0) for r in results)
        wins = sum(r['hitrates'].get(5, {}).get('wins', 0) for r in results)
        losses = sum(r['hitrates'].get(5, {}).get('losses', 0) for r in results)
        total_return = sum(r['hitrates'].get(5, {}).get('total_return', 0.0) for r in results)

        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        avg_return = total_return / total if total > 0 else 0

        # 计算最大盈亏比
        profitable_trades = [r['hitrates'].get(5, {}).get('total_return', 0) for r in results]
        max_win = max([t for t in profitable_trades if t > 0], default=0.01)
        max_loss = min([abs(t) for t in profitable_trades if t < 0], default=0.01)
        profit_loss_ratio = max_win / max_loss if max_loss > 0 else 999

        return {
            'total_signals': len(results),
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return,
            'max_profit_loss_ratio': profit_loss_ratio,
        }


# ================================================================
# 主函数
# ================================================================

def main():
    engine = StrategyBacktest(initial_capital=100000)
    results, env_info = engine.run_all_backtests()

    # 保存结果
    output_path = '/workspace/行情数据库/backtest_results_v3.json'
    with open(output_path, 'w') as f:
        json.dump({
            'env_info': env_info,
            'results': results,
            'timestamp': datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {output_path}")


if __name__ == '__main__':
    main()
