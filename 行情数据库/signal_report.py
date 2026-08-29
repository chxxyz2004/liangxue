#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""信号报告生成器 — 读取 signal_cache.json 并生成报告引用文本。

供复盘报告、讲义、文章等报告生成脚本调用。

典型用法：
    from signal_report import (
        get_risk_summary_text,
        get_stock_detail_text,
        get_all_signals_text,
        load_cache,
    )
    report_text = get_risk_summary_text()
    stock_detail = get_stock_detail_text('sh603516')
"""
import os
import json
from datetime import datetime
from typing import Dict, Optional, List

CACHE_PATH = '/workspace/行情数据库/signal_cache.json'
LIANGXUE_CACHE_PATH = '/workspace/行情数据库/liangxue_cache.json'


def load_cache() -> dict:
    """加载信号缓存，不存在返回空 dict。"""
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ============================================================
# 指标解释说明（用于报告中的原文引用）
# ============================================================

EXPLANATION = {
    'ma_cross': """
  【均线交叉信号解读】
  - 金叉（MA5 上穿 MA10）：短期动能强于中期，通常预示上涨趋势启动。
    市场机理：主力在短期密集买入，推动价格快速拉升，形成多头排列。
  - 死叉（MA5 下穿 MA10）：短期动能弱于中期，通常预示下跌趋势延续。
    市场机理：抛售压力持续，短期成本高于中期成本，筹码松动。
  - 注意：均线滞后，交叉信号需谨慎验证，最好结合成交量确认。""",

    'price_volume_divergence': """
  【价量发散/共振信号解读】
  - 价量共振（价涨量升）：价格与成交量同向，趋势确认度高。
    市场机理：买方力量强劲，追涨意愿强，趋势可持续。
  - 价量发散（价跌量升）：价格下跌但成交量放大，主力可能在出货。
    市场机理：恐慌性抛售或主力刻意打压吸筹，需结合位置判断。
  - 价量发散（价涨量缩）：价格上涨但成交量萎缩，多头力量减弱。
    市场机理：买盘不足，上涨动能衰减，警惕回调。""",

    'doubling_volume': """
  【倍量柱信号解读】
  - 定义：当日成交量 ≥ 前一日成交量的 1.9 倍，且收盘价高于开盘价（收阳）。
  - 市场机理：主力资金明显介入，可能处于建仓初期或拉升启动阶段。
  - 注意事项：倍量柱需结合后续K线确认，若次日缩量下跌则可能是诱多。""",

    'risk_assessment': """
  【量化风险评级逻辑】
  - CV（量变异系数）：成交量波动标准差 / 均值。CV < 0.5 表示成交过于均匀，
    疑似程序化交易或量化资金控盘，手动判断难度大。
  - 价量相关性：近10日收盘价变化与成交量变化的相关系数。相关系数 < 0.3
    表示量价背离，主力行为不明显或存在对倒嫌疑。
  - 风险等级：根据上述两项指标综合打分（每项最高25分），
    0分=正常，25分=低风险，50分=中风险，75分=高风险，100分=极高风险。""",

    'intraday_5min': """
  【5分钟分时分析逻辑】
  - 当日涨跌幅：首根K线开盘价至末根K线收盘价的变化率。
  - 价量相关系数：全部48根5分钟K线的价量变化量相关度，反映全天资金行为一致性。
  - 异常放量：尾段成交量较近期均值的偏离度，>50%视为异动。""",
}


def load_liangxue_cache() -> dict:
    """加载量学战法缓存，不存在返回空 dict。"""
    if not os.path.exists(LIANGXUE_CACHE_PATH):
        return {}
    try:
        with open(LIANGXUE_CACHE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ============================================================
# 量学战法报告函数
# ============================================================

def get_liangxue_text(symbol: str) -> str:
    """生成单只股票的量学战法报告文本，供复盘报告引用。"""
    try:
        from liangxue_engine import liangxue_engine
        return liangxue_engine.get_summary_text(symbol)
    except ImportError:
        return f"{symbol}：量学引擎未安装，跳过量学分析。"


def get_liangxue_summary_text() -> str:
    """生成所有股票的量学战法汇总文本。"""
    try:
        from config import HOLDINGS, WATCH_LIST
        all_stocks = {**HOLDINGS, **WATCH_LIST}
    except ImportError:
        all_stocks = {
            'sh603516': '淳中科技', 'sh601138': '工业富联', 'sz002156': '通富微电',
            'sh601231': '环旭电子', 'sz300476': '胜宏科技', 'sh603283': '赛腾股份',
            'sz300394': '天孚通信', 'sh600584': '长电科技',
        }

    syms = list(all_stocks.keys()) if hasattr(all_stocks, 'keys') else list(all_stocks)
    lines = ["## 量学战法汇总", ""]

    doubling_stocks = []
    golden_stocks = []
    line_stocks = []

    for sym in syms:
        try:
            from liangxue_engine import liangxue_engine
            result = liangxue_engine.full_analysis(sym)
            name = getattr(all_stocks.get(sym, ''), 'name', sym) if hasattr(all_stocks.get(sym, ''), 'name') else (all_stocks.get(sym, sym) if sym in all_stocks else sym)
        except Exception:
            continue

        kb = result.get('key_bars', {})
        vb = result.get('volume_bars', {}).get('summary', {})
        ql = result.get('quantity_lines', {})

        if vb.get('doubling_bars'):
            dbl = vb['doubling_bars'][-1]
            doubling_stocks.append((name, sym, dbl['date'], dbl['ratio']))

        golden = kb.get('golden_bars', [])
        marshal = kb.get('marshal_bars', [])
        general = kb.get('general_bars', [])
        if golden or marshal or general:
            bar_type = '黄金柱' if golden else ('元帅柱' if marshal else '将军柱')
            bar_date = (golden[-1]['date'] if golden else (marshal[-1]['date'] if marshal else general[-1]['date']))
            golden_stocks.append((name, sym, bar_type, bar_date))

        peak = ql.get('peak_lines', [])
        valley = ql.get('valley_lines', [])
        if peak or valley:
            key_line = f"峰顶线{peak[-1]['price']}" if peak else f"谷底线{valley[-1]['price']}"
            line_stocks.append((name, sym, key_line))

        lines.append(get_liangxue_text(sym))
        lines.append("---")
        lines.append("")

    # 摘要
    summary_lines = ["### 量学信号速览", ""]
    if doubling_stocks:
        summary_lines.append("**倍量柱记录**：")
        for name, sym, date, ratio in doubling_stocks:
            summary_lines.append(f"  - {name}（{sym}）：{date} {ratio:.2f}x")
        summary_lines.append("")

    if golden_stocks:
        summary_lines.append("**关键柱信号**：")
        for name, sym, btype, date in golden_stocks:
            summary_lines.append(f"  - {name}（{sym}）：{btype} {date}")
        summary_lines.append("")

    if line_stocks:
        summary_lines.append("**量线支撑/压力位**：")
        for name, sym, key_line in line_stocks[:5]:
            summary_lines.append(f"  - {name}（{sym}）：{key_line}")
        summary_lines.append("")

    if not any([doubling_stocks, golden_stocks, line_stocks]):
        summary_lines.append("当前无显著量学信号。")

    return '\n'.join(lines) + '\n' + '\n'.join(summary_lines)


def append_liangxue_section(symbol: str, lines: list) -> list:
    """在股票详情报告中追加量学战法分析章节。"""
    try:
        from liangxue_engine import liangxue_engine
        result = liangxue_engine.full_analysis(symbol)
        kb = result.get('key_bars', {})
        vb = result.get('volume_bars', {}).get('summary', {})
        ql = result.get('quantity_lines', {})
        pl = result.get('precision_lines', {})

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"### {symbol} 量学战法分析（黑马王子量学体系）")
        lines.append("")

        # 量柱形态
        lines.append("**量柱形态**：")
        if vb.get('doubling_bars'):
            for dbl in vb['doubling_bars'][-3:]:
                lines.append(f"  - 倍量柱：{dbl['date']}（量比{dbl['ratio']:.2f}x，收阳）")
        if vb.get('shrinking_bars'):
            shrinks = vb['shrinking_bars'][-2:]
            lines.append(f"  - 缩量柱：{'、'.join([s['date'] + '(' + str(s['ratio']) + 'x)' for s in shrinks])}")
        if vb.get('high_vol_bars'):
            hv = vb['high_vol_bars'][-1]
            lines.append(f"  - 高量柱：{hv['date']}（量比{hv['ratio']:.2f}x，位置偏高）")
        if vb.get('low_vol_bars'):
            lv = vb['low_vol_bars'][-1]
            lines.append(f"  - 低量柱：{lv['date']}（量比{lv['ratio']:.2f}x，地量区域）")
        if not any([vb.get('doubling_bars'), vb.get('shrinking_bars'), vb.get('high_vol_bars'), vb.get('low_vol_bars')]):
            lines.append("  - 近30日无明显量柱形态特征")
        lines.append("")

        # 关键柱
        lines.append("**关键柱判定**：")
        golden = kb.get('golden_bars', [])
        marshal = kb.get('marshal_bars', [])
        general = kb.get('general_bars', [])
        if golden:
            for g in golden:
                lines.append(f"  - 黄金柱：{g['date']}，回调{g['drawdown_ratio']:.0%}实体，强支撑确认")
        if marshal:
            for m in marshal:
                lines.append(f"  - 元帅柱：{m['date']}，回调{m['drawdown_ratio']:.0%}实体，中等支撑")
        if general:
            for g in general:
                lines.append(f"  - 将军柱：{g['date']}，回调{g['drawdown_ratio']:.0%}实体，关注守位")
        if not golden and not marshal and not general:
            lines.append("  - 近期无关键柱信号（倍量柱后缩量回调未满足标准）")
            # 如果有倍量柱但无关键柱，说明形态未确认
            if vb.get('doubling_bars'):
                latest_dbl = vb['doubling_bars'][-1]
                lines.append(f"  - 备注：{latest_dbl['date']} 倍量柱（{latest_dbl['ratio']:.2f}x）后回调尚未缩量确认")
        lines.append("")

        # 量线支撑/压力
        lines.append("**量线体系**：")
        peak_lines = ql.get('peak_lines', [])
        valley_lines = ql.get('valley_lines', [])
        concave_lines = ql.get('concave_lines', [])

        if peak_lines:
            lines.append("  压力位（峰顶线）：")
            for pl_line in peak_lines[-3:]:
                lines.append(f"    - {pl_line['price']} 元（{pl_line['count']}点确认）")
        if valley_lines:
            lines.append("  支撑位（谷底线）：")
            for vl in valley_lines[-3:]:
                lines.append(f"    - {vl['price']} 元（{vl['count']}点确认）")
        if concave_lines:
            lines.append("  凹口平衡位：")
            for cl in concave_lines[-2:]:
                lines.append(f"    - {cl['price']} 元")
        if not peak_lines and not valley_lines:
            lines.append("  - 量线数据不足，需更多历史K线")
        lines.append("")

        # 精准回踩
        precise_peaks = pl.get('precise_peak_lines', []) if isinstance(pl, dict) else []
        precise_valleys = pl.get('precise_valley_lines', []) if isinstance(pl, dict) else []
        if precise_peaks or precise_valleys:
            lines.append("**精准回踩验证**：")
            for pp in precise_peaks[-2:]:
                lines.append(f"  - 精准压力线 {pp['line_price']:.2f} 元（精准度{pp['precision_score']:.0%}，触及{pp['touch_count']}次）")
            for pv in precise_valleys[-2:]:
                lines.append(f"  - 精准支撑线 {pv['line_price']:.2f} 元（精准度{pv['precision_score']:.0%}，触及{pv['touch_count']}次）")
            lines.append("")

        # 当前价格与量线关系
        latest = result.get('latest', {})
        close_price = latest.get('close', 0)
        if close_price and (peak_lines or valley_lines):
            lines.append("**当前位置与量线关系**：")
            nearest_valley = min(valley_lines, key=lambda x: abs(x['price'] - close_price), default=None) if valley_lines else None
            nearest_peak = min(peak_lines, key=lambda x: abs(x['price'] - close_price), default=None) if peak_lines else None
            if nearest_valley and close_price > nearest_valley['price'] * 0.95:
                lines.append(f"  - 现价 {close_price:.2f} 元，位于谷底线 {nearest_valley['price']:.2f} 元上方 {((close_price/nearest_valley['price']-1)*100):+.1f}%，支撑有效")
            elif nearest_valley:
                lines.append(f"  - 现价 {close_price:.2f} 元，跌破谷底线 {nearest_valley['price']:.2f} 元，支撑失效")
            if nearest_peak:
                lines.append(f"  - 上方压力线：{nearest_peak['price']:.2f} 元（{nearest_peak['count']}点确认）")
            lines.append("")

    except Exception as e:
        lines.append(f"量学分析获取失败：{e}")

    return lines

def get_risk_summary_text() -> str:
    """生成风险汇总文本，供复盘报告引用。"""
    cache = load_cache()
    if not cache:
        return "信号缓存未生成，请先运行 python3 signal_engine.py --save"

    updated = cache.get('updated_at', '未知时间')
    s = cache.get('summary', {})

    lines = [
        f"## 风险评级汇总（数据截止：{updated}）",
        "",
    ]

    # 高风险股票
    high = s.get('high_risk', [])
    if high:
        lines.append(f"**高风险股票（{len(high)}只）**：{', '.join(high)}")
        lines.append("  特征：成交量过于均匀 且/或 量价背离，疑似量化控盘或主力对倒。")
        lines.append("")

    # 中风险股票
    med = s.get('medium_risk', [])
    if med:
        lines.append(f"**中风险股票（{len(med)}只）**：{', '.join(med)}")
        lines.append("  特征：单一风险因子触发，需继续观察。")
        lines.append("")

    # 死叉股票
    death = s.get('death_cross', [])
    if death:
        lines.append(f"**空头排列（死叉）股票（{len(death)}只）**：{', '.join(death)}")
        lines.append(EXPLANATION['ma_cross'])
        lines.append("")

    # 价量发散
    div = s.get('price_volume_divergence', [])
    if div:
        lines.append(f"**价量发散股票（{len(div)}只）**：{', '.join(div)}")
        lines.append(EXPLANATION['price_volume_divergence'])
        lines.append("")

    # 倍量柱
    dbl = s.get('volume_breakout', [])
    if dbl:
        lines.append("**近期倍量柱记录**：")
        for item in dbl:
            lines.append(f"  - {item['name']}：最近一次倍量柱日期={item['latest']['date']}, "
                         f"量比={item['latest']['ratio']:.2f}x")
        lines.append(EXPLANATION['doubling_volume'])
        lines.append("")

    if not any([high, med, death, div, dbl]):
        lines.append("当前无明显异常信号，市场整体平稳。")

    return '\n'.join(lines)


def get_stock_detail_text(symbol: str, include_explanation: bool = True) -> str:
    """生成单只股票的详细分析报告文本。"""
    cache = load_cache()
    if not cache or symbol not in cache.get('stocks', {}):
        return f"未找到 {symbol} 的数据，请先生成缓存。"

    st = cache['stocks'][symbol]
    name = st.get('name', symbol)
    daily = st.get('daily', {})
    risk = st.get('risk', {})
    intr = st.get('intraday', {})

    lines = [f"### {name}（{symbol}）技术指标详解"]
    lines.append("")

    # 基础行情
    latest = daily.get('latest', {})
    lines.append(f"- **最新日期**：{latest.get('day', 'N/A')}")
    lines.append(f"- **收盘价**：{latest.get('close', 'N/A')} 元")
    lines.append(f"- **当日涨跌**：开{latest.get('open', 'N/A')} → 收{latest.get('close', 'N/A')}")
    lines.append(f"- **成交量**：{latest.get('volume', 0)/10000:.1f}万手")
    lines.append("")

    # 均线系统
    ma = daily.get('ma', {})
    if ma:
        lines.append("**均线系统（MA5/10/20/60）**：")
        for k, v in ma.items():
            lines.append(f"  - {k}：{v:.2f} 元")
        lines.append("")

    # MACD
    macd = daily.get('macd', {})
    if macd:
        macd_bar = macd.get('macd', 0)
        macd_desc = "（正值表示多头动能，负值表示空头动能）"
        lines.append("**MACD 指标**：")
        lines.append(f"  - DIF：{macd.get('dif', 'N/A')}")
        lines.append(f"  - DEA：{macd.get('dea', 'N/A')}")
        lines.append(f"  - MACD柱：{macd_bar:.4f} {macd_desc}")
        if macd_bar > 0:
            lines.append("  → MACD柱为正，空头动能正在减弱，关注是否转多。")
        else:
            lines.append("  → DIF为负且MACD柱为负，空头趋势尚未结束。")
        lines.append("")

    # 量比
    vr = daily.get('volume_ratio')
    if vr is not None:
        lines.append(f"**量比**：{vr:.2f}")
        if vr < 0.8:
            lines.append("  → 缩量状态，买卖意愿偏弱，观望为主。")
        elif vr > 1.5:
            lines.append("  → 明显放量，资金活跃度提升，需关注后续方向。")
        lines.append("")

    # 均线交叉
    cross = daily.get('cross', {})
    if cross:
        lines.append(f"**均线信号**：{cross.get('type', 'N/A')} — {cross.get('signal', 'N/A')}")
        if include_explanation:
            lines.append(EXPLANATION['ma_cross'])
        lines.append("")

    # 价量发散
    pv = daily.get('price_volume', {})
    if pv:
        lines.append(f"**价量关系**：{pv.get('signal', 'N/A')}")
        if include_explanation:
            lines.append(EXPLANATION['price_volume_divergence'])
        lines.append("")

    # 风险评级
    lines.append("**量化风险评级**：")
    lines.append(f"  - 风险等级：{risk.get('risk_level', 'N/A')}（{risk.get('risk_score', 0)}分）")
    factors = risk.get('risk_factors', [])
    if factors:
        lines.append(f"  - 触发因子：{'，'.join(factors)}")
    if include_explanation:
        lines.append(EXPLANATION['risk_assessment'])
    lines.append("")

    # 5分钟分析
    if intr and 'error' not in intr:
        lines.append("**5分钟分时分析**（日期：{date}）：".format(date=intr.get('date', '')))
        lines.append(f"  - 当日涨跌幅：{intr.get('day_pct', 0):+.2f}%")
        lines.append(f"  - 价量相关系数：{intr.get('correlation', 0):.3f}")
        lines.append(f"  - 异常放量：{intr.get('volume_anomaly', 0):.1%}")
        signals = intr.get('signals', [])
        if signals:
            for sig in signals:
                lines.append(f"  - [{sig['type']}] {sig['subtype']}：{sig['detail']}")
        if include_explanation:
            lines.append(EXPLANATION['intraday_5min'])
        lines.append("")

    # 量学战法分析
    try:
        from liangxue_engine import liangxue_engine
        lines = append_liangxue_section(symbol, lines)
    except Exception:
        pass

    return '\n'.join(lines)


def get_all_signals_text() -> str:
    """生成全量信号汇总文本。"""
    cache = load_cache()
    if not cache:
        return "信号缓存未生成。"

    updated = cache.get('updated_at', '未知时间')
    stocks = cache.get('stocks', {})

    lines = [
        f"## 全量技术信号汇总（更新时间：{updated}）",
        "",
    ]

    # 按风险等级分组
    risk_groups = {'高风险': [], '中风险': [], '低风险': [], '正常': []}
    for sym, st in stocks.items():
        rl = st.get('risk', {}).get('risk_level', '未知')
        if rl in risk_groups:
            risk_groups[rl].append(st.get('name', sym))

    for level, names in risk_groups.items():
        if names:
            lines.append(f"### {level}（{len(names)}只）")
            for n in names:
                lines.append(f"  - {n}")
            lines.append("")

    # 倍量柱
    breakout_stocks = []
    for sym, st in stocks.items():
        dv = st.get('daily', {}).get('doubling_volume', [])
        if dv:
            breakout_stocks.append((st.get('name', sym), len(dv), dv[-1]))
    if breakout_stocks:
        lines.append("### 近期倍量柱（最近20日内有记录）")
        for name, count, latest in sorted(breakout_stocks, key=lambda x: -x[1]):
            lines.append(f"  - {name}：{count}次，最新 {latest['date']}（量比{latest['ratio']:.2f}x）")
        lines.append("")

    # 分时信号
    intraday_signals = []
    for sym, st in stocks.items():
        intr = st.get('intraday', {})
        if intr and 'signals' in intr and intr['signals']:
            intraday_signals.append((st.get('name', sym), intr.get('day_pct', 0), intr.get('signals')))
    if intraday_signals:
        lines.append("### 今日分时异动")
        for name, day_pct, sigs in intraday_signals:
            for sig in sigs:
                lines.append(f"  - {name}（当日{day_pct:+.2f}%）：{sig['subtype']} — {sig['detail']}")
        lines.append("")

    return '\n'.join(lines)


# ============================================================
# 命令行快速查看
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='信号报告生成器')
    parser.add_argument('--symbol', type=str, help='查询单只股票详情')
    parser.add_argument('--risk', action='store_true', help='输出风险汇总')
    parser.add_argument('--all', action='store_true', help='输出全量信号')
    parser.add_argument('--liangxue', action='store_true', help='输出量学战法汇总')
    args = parser.parse_args()

    if args.symbol:
        print(get_stock_detail_text(args.symbol))
    elif args.risk:
        print(get_risk_summary_text())
    elif args.all:
        print(get_all_signals_text())
    elif args.liangxue:
        print(get_liangxue_summary_text())
    else:
        # 默认输出风险汇总
        print(get_risk_summary_text())


if __name__ == '__main__':
    main()
