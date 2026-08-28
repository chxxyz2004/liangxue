#!/usr/bin/env python3
"""
量学盘前预案生成器
基于K线数据和回测结果，为次日交易生成预案
"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/回测分析')
sys.path.insert(0, '/workspace/讲义生成器')
from config import HOLDINGS, WATCH_LIST, SPOOFING_THRESHOLDS
from backtest_engine import load_kline, find_volume_signals, test_golden_line_support
from generate_cases import analyze_stock


def get_today_data():
    """获取今日数据"""
    today = datetime.now().strftime('%Y-%m-%d')
    return today


def analyze_market_status():
    """分析大盘环境"""
    status = {}
    
    # 分析主要指数
    indexes = {
        'sh000001': '上证指数',
        'sz399001': '深证成指',
        'sz399006': '创业板指'
    }
    
    for sym, name in indexes.items():
        data = load_kline(sym)
        if data and 'data' in data:
            klines = data['data']
            latest = klines[-1]
            prev = klines[-2] if len(klines) > 1 else latest
            
            change_pct = round((latest['close'] - prev['close']) / prev['close'] * 100, 2)
            
            # 判断大盘状态
            if change_pct >= 1:
                env = '强势'
            elif change_pct >= 0:
                env = '偏强'
            elif change_pct >= -1:
                env = '偏弱'
            else:
                env = '弱势'
            
            status[sym] = {
                'name': name,
                'close': latest['close'],
                'change': change_pct,
                'env': env,
                'recent_high': max(k['high'] for k in klines[-20:]),
                'recent_low': min(k['low'] for k in klines[-20:])
            }
    
    return status


def analyze_stock_for_plan(stock_data):
    """为单只股票生成盘前预案"""
    if not stock_data:
        return None
    
    lines = []
    sym = stock_data['symbol']
    name = stock_data['name']
    
    # 关键价位
    support = stock_data['recent_low']
    resistance = stock_data['recent_high']
    latest = stock_data['latest']['close']
    
    # 黄金线支撑
    golden_support = support * 0.95 if stock_data['golden_win_rate'] >= 60 else None
    
    lines.append(f"### {name}（{sym}）\n")
    lines.append(f"- **最新价**：{latest}元")
    lines.append(f"- **近期支撑**：{support:.2f}元")
    lines.append(f"- **近期压力**：{resistance:.2f}元")
    
    if golden_support:
        lines.append(f"- **黄金线支撑**：{golden_support:.2f}元（胜率{stock_data['golden_win_rate']}%）")
    
    # 操作建议
    lines.append("\n**操作预案**：\n")
    
    if latest < support * 1.02:
        lines.append(f"1. 股价接近支撑位{support:.2f}元，可观察是否企稳")
        lines.append(f"2. 若缩量跌破{support:.2f}元，暂停买入")
        lines.append(f"3. 若在支撑位出现倍量柱，可考虑介入")
    elif latest > resistance * 0.98:
        lines.append(f"1. 股价接近压力位{resistance:.2f}元，注意量能变化")
        lines.append(f"2. 若放量突破{resistance:.2f}元，可跟进")
        lines.append(f"3. 若缩量滞涨，考虑减仓")
    else:
        lines.append(f"1. 股价处于{support:.2f}-{resistance:.2f}区间")
        lines.append(f"2. 等待方向选择，不急于操作")
        lines.append(f"3. 关注{support:.2f}元支撑和{resistance:.2f}元压力")
    
    lines.append("\n---\n")
    return '\n'.join(lines)


def generate_preplan():
    """生成盘前预案"""
    today = get_today_data()
    market = analyze_market_status()
    
    lines = []
    lines.append(f"# 量学盘前预案\n")
    lines.append(f"**日期**：{today}\n")
    lines.append(f"**生成时间**：{datetime.now().strftime('%H:%M')}\n")
    
    # 大盘环境
    lines.append("## 一、大盘环境分析\n")
    for sym, data in market.items():
        arrow = '↑' if data['change'] >= 0 else '↓'
        lines.append(f"- **{data['name']}**：{data['close']}元（{arrow}{abs(data['change'])}%）- {data['env']}")
    
    # 总体判断
    avg_change = sum(d['change'] for d in market.values()) / len(market)
    if avg_change >= 0.5:
        overall = '强势环境，可积极操作'
    elif avg_change >= 0:
        overall = '偏强环境，谨慎做多'
    elif avg_change >= -0.5:
        overall = '偏弱环境，控制仓位'
    else:
        overall = '弱势环境，观望为主'
    
    lines.append(f"\n**大盘判断**：{overall}\n")
    
    # 持仓股预案
    lines.append("## 二、持仓股预案\n")
    
    for sym in HOLDINGS.keys():
        data = analyze_stock(sym)
        if data:
            case = analyze_stock_for_plan(data)
            if case:
                lines.append(case)
    
    # 关注股预案
    lines.append("## 三、关注股预案\n")
    
    for sym in WATCH_LIST.keys():
        data = analyze_stock(sym)
        if data:
            case = analyze_stock_for_plan(data)
            if case:
                lines.append(case)
    
    # 今日操作要点
    lines.append("## 四、今日操作要点\n")
    lines.append("1. **开盘观察**：关注大盘开盘走势，判断环境强弱\n")
    lines.append("2. **持仓股**：\n")
    lines.append("   - 观察是否出现倍量柱信号")
    lines.append("   - 关注关键支撑位是否守住")
    lines.append("   - 注意量能变化，确认信号有效性\n")
    lines.append("3. **风控纪律**：\n")
    lines.append("   - 严格执行止损线")
    lines.append("   - 不追高，不抄底")
    lines.append("   - 仓位控制在30%以内\n")
    
    lines.append("---\n")
    lines.append("*本预案基于历史数据和回测结果生成，仅供参考，不构成投资建议*\n")
    
    return '\n'.join(lines)


def generate_review():
    """生成复盘日报"""
    today = get_today_data()
    
    lines = []
    lines.append(f"# 量学复盘日报\n")
    lines.append(f"**日期**：{today}\n")
    lines.append(f"**生成时间**：{datetime.now().strftime('%H:%M')}\n")
    
    # 大盘回顾
    lines.append("## 一、大盘回顾\n")
    market = analyze_market_status()
    
    for sym, data in market.items():
        lines.append(f"### {data['name']}\n")
        lines.append(f"- **收盘**：{data['close']}元")
        lines.append(f"- **涨跌**：{data['change']}%")
        lines.append(f"- **环境**：{data['env']}")
        lines.append(f"- **区间**：{data['recent_low']:.2f} - {data['recent_high']:.2f}元\n")
    
    # 持仓股回顾
    lines.append("## 二、持仓股回顾\n")
    
    for sym in HOLDINGS.keys():
        data = analyze_stock(sym)
        if data:
            lines.append(f"### {data['name']}（{sym}）\n")
            lines.append(f"- **收盘**：{data['latest']['close']}元")
            lines.append(f"- **涨跌**：{data['change_pct']}%")
            lines.append(f"- **信号**：{len(data['volume_signals'])}个倍量柱信号")
            lines.append(f"- **黄金线胜率**：{data['golden_win_rate']}%")
            lines.append(f"- **近期涨停**：{len(data['limit_ups'])}次\n")
            
            # 技术形态分析
            if data['volume_signals']:
                lines.append("**倍量柱分析**：\n")
                for sig in data['volume_signals'][-3:]:
                    lines.append(f"- {sig['date']}：量比{sig['volume_ratio']}x，收盘价{sig['price']}元，涨幅{sig['change_pct']}%")
                lines.append("")
    
    # 信号验证
    lines.append("## 三、信号验证\n")
    
    golden_rates = []
    for sym in HOLDINGS.keys():
        data = analyze_stock(sym)
        if data and data['golden_tests'] > 0:
            golden_rates.append(data['golden_win_rate'])
    
    if golden_rates:
        avg_rate = sum(golden_rates) / len(golden_rates)
        lines.append(f"### 黄金线支撑有效性\n")
        lines.append(f"- **平均胜率**：{avg_rate:.1f}%")
        lines.append(f"- **结论**：{'有效' if avg_rate >= 60 else '待观察' if avg_rate >= 40 else '失效'}\n")
    
    # 操作总结
    lines.append("## 四、操作总结\n")
    lines.append("### 今日操作记录\n")
    lines.append("- 无操作（示例模板）\n")
    
    lines.append("### 经验教训\n")
    lines.append("1. 关注量能变化，确认信号有效性")
    lines.append("2. 注意左证明和右确认的完整性")
    lines.append("3. 严格执行止损纪律\n")
    
    # 明日展望
    lines.append("## 五、明日展望\n")
    lines.append("1. 关注大盘环境变化")
    lines.append("2. 观察持仓股是否出现新信号")
    lines.append("3. 准备盘前预案\n")
    
    lines.append("---\n")
    lines.append("*本复盘基于真实数据生成，仅供参考*\n")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', choices=['preplan', 'review'], required=True, help='生成类型')
    parser.add_argument('--output', help='输出文件路径')
    args = parser.parse_args()
    
    if args.type == 'preplan':
        content = generate_preplan()
    else:
        content = generate_review()
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已保存: {args.output}")
    else:
        print(content)
