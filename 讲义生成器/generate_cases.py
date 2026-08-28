#!/usr/bin/env python3
"""
量学讲义案例生成器
基于真实K线数据和回测结果生成教学案例
"""
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/回测分析')
from config import HOLDINGS, WATCH_LIST
from backtest_engine import load_kline, find_volume_signals, test_golden_line_support


def analyze_stock(symbol):
    """分析单只股票，提取教学案例"""
    data = load_kline(symbol)
    if not data or 'data' not in data:
        return None
    
    # 获取股票信息（dataclass对象）
    info = HOLDINGS.get(symbol, WATCH_LIST.get(symbol, None))
    name = info.name if info else symbol
    
    # 提取关键数据
    klines = data['data']
    total_days = len(klines)
    
    # 最近价格
    latest = klines[-1]
    prev = klines[-2] if len(klines) > 1 else latest
    
    # 计算涨跌幅
    change_pct = round((latest['close'] - prev['close']) / prev['close'] * 100, 2)
    
    # 识别倍量柱
    volume_signals = find_volume_signals(data, lookback=60)
    
    # 黄金线测试
    golden_results = test_golden_line_support(data)
    
    # 提取关键高低点
    recent_high = max(k['high'] for k in klines[-60:])
    recent_low = min(k['low'] for k in klines[-60:])
    
    # 找涨停记录
    limit_ups = []
    for i in range(len(klines)-60, len(klines)):
        k = klines[i]
        if i > 0:
            prev_close = klines[i-1]['close']
            pct = (k['close'] - prev_close) / prev_close * 100
            if pct >= 9.5:
                limit_ups.append({
                    'date': k['day'],
                    'price': k['close'],
                    'change': round(pct, 2)
                })
    
    return {
        'symbol': symbol,
        'name': name,
        'latest': latest,
        'change_pct': change_pct,
        'recent_high': recent_high,
        'recent_low': recent_low,
        'volume_signals': volume_signals[-5:],
        'golden_win_rate': golden_results.get('win_rate', 0),
        'golden_tests': golden_results.get('total', 0),
        'limit_ups': limit_ups[-3:],
        'total_days': total_days,
        'date_range': f"{klines[0]['day']} ~ {klines[-1]['day']}"
    }


def generate_case_study(stock_data, focus='all'):
    """生成个股案例研究"""
    if not stock_data:
        return None
    
    lines = []
    sym = stock_data['symbol']
    name = stock_data['name']
    
    lines.append(f"## {name}（{sym}）案例分析\n")
    lines.append(f"**数据范围**：{stock_data['date_range']}（{stock_data['total_days']}个交易日）\n")
    
    # 当前状态
    lines.append("### 当前状态\n")
    lines.append(f"- **最新价**：{stock_data['latest']['close']}元")
    lines.append(f"- **日涨跌**：{stock_data['change_pct']}%")
    lines.append(f"- **近期高点**：{stock_data['recent_high']}元")
    lines.append(f"- **近期低点**：{stock_data['recent_low']}元")
    lines.append(f"- **振幅**：{round((stock_data['recent_high']-stock_data['recent_low'])/stock_data['recent_low']*100, 1)}%\n")
    
    # 倍量柱案例
    if focus in ['all', 'volume']:
        lines.append("### 倍量柱信号案例\n")
        signals = stock_data['volume_signals']
        if signals:
            for sig in signals[-3:]:
                lines.append(f"- **{sig['date']}**：倍量柱，量比{sig['volume_ratio']}x，收盘价{sig['price']}元，涨幅{sig['change_pct']}%")
        else:
            lines.append("近60日无倍量柱信号\n")
    
    # 黄金线测试
    if focus in ['all', 'golden']:
        lines.append("### 黄金线支撑测试\n")
        lines.append(f"- **胜率**：{stock_data['golden_win_rate']}%（{stock_data['golden_tests']}次测试）")
        status = '有效' if stock_data['golden_win_rate'] >= 60 else '待观察' if stock_data['golden_win_rate'] >= 40 else '失效'
        lines.append(f"- **结论**：{status}\n")
    
    # 涨停记录
    if focus in ['all', 'limit']:
        lines.append("### 近期涨停记录\n")
        limit_ups = stock_data['limit_ups']
        if limit_ups:
            for lu in limit_ups:
                lines.append(f"- {lu['date']}：涨停，收盘价{lu['price']}元，涨幅{lu['change']}%")
        else:
            lines.append("近60日无涨停记录\n")
    
    lines.append("---\n")
    return '\n'.join(lines)


def generate_summary_report():
    """生成汇总报告"""
    all_stocks = {**HOLDINGS, **WATCH_LIST}
    results = []
    
    for sym in all_stocks:
        data = analyze_stock(sym)
        if data:
            results.append(data)
    
    # 生成报告
    lines = []
    lines.append("# 量学理论实战案例报告\n")
    lines.append(f"**生成日期**：{datetime.now().strftime('%Y-%m-%d')}\n")
    lines.append(f"**覆盖股票**：{len(results)}只（持仓{len(HOLDINGS)}只 + 关注{len(WATCH_LIST)}只）\n")
    
    # 汇总表
    lines.append("## 持仓股概况\n")
    lines.append("| 股票代码 | 名称 | 最新价 | 日涨跌 | 黄金线胜率 | 近期涨停 |")
    lines.append("|---------|------|-------|--------|-----------|---------|")
    
    for r in results:
        if r['symbol'] in HOLDINGS:
            limit_str = f"{len(r['limit_ups'])}次" if r['limit_ups'] else '-'
            lines.append(f"| {r['symbol']} | {r['name']} | {r['latest']['close']} | {r['change_pct']}% | {r['golden_win_rate']}% | {limit_str} |")
    
    lines.append("\n## 详细案例\n")
    
    for r in results:
        case = generate_case_study(r)
        if case:
            lines.append(case)
    
    # 理论验证结论
    lines.append("## 量学理论验证结论\n")
    lines.append("### 黄金线支撑有效性\n")
    golden_rates = [r['golden_win_rate'] for r in results if r['golden_tests'] > 0]
    if golden_rates:
        avg_rate = sum(golden_rates) / len(golden_rates)
        lines.append(f"- **平均胜率**：{avg_rate:.1f}%")
        lines.append(f"- **有效样本**：{len(golden_rates)}只")
        conclusion = '黄金线支撑有效，可参考使用' if avg_rate >= 60 else '黄金线支撑效果一般，需结合其他信号' if avg_rate >= 40 else '黄金线支撑失效，建议调整策略'
        lines.append(f"- **结论**：{conclusion}\n")
    
    lines.append("### 倍量柱信号有效性\n")
    vol_counts = [len(r['volume_signals']) for r in results]
    lines.append(f"- **有信号的股票**：{sum(1 for v in vol_counts if v > 0)}/{len(results)}只")
    lines.append(f"- **总信号数**：{sum(vol_counts)}次\n")
    
    lines.append("### 实战建议\n")
    lines.append("1. 倍量柱出现后，观察后续量能变化，确认是否为真倍量")
    lines.append("2. 黄金线支撑有效时，可在支撑位附近布局")
    lines.append("3. 结合量波理论，观察黄白线交叉信号")
    lines.append("4. 注意左证明和右确认的完整性\n")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', help='分析单只股票')
    parser.add_argument('--focus', default='all', choices=['all', 'volume', 'golden', 'limit'])
    parser.add_argument('--summary', action='store_true', help='生成汇总报告')
    parser.add_argument('--output', help='输出文件路径')
    args = parser.parse_args()
    
    if args.summary:
        report = generate_summary_report()
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"报告已保存: {args.output}")
        else:
            print(report)
    elif args.symbol:
        data = analyze_stock(args.symbol)
        if data:
            case = generate_case_study(data, args.focus)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(case)
                print(f"案例已保存: {args.output}")
            else:
                print(case)
        else:
            print(f"未找到 {args.symbol} 的数据")
    else:
        # 默认生成所有持仓股的案例
        for sym in list(HOLDINGS.keys())[:3]:
            data = analyze_stock(sym)
            if data:
                case = generate_case_study(data, args.focus)
                print(case)
                print("\n")
