#!/usr/bin/env python3
"""
量学历史案例回溯引擎
对比不同时期的信号效果，验证理论适用性
"""
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/技术指标')
from config import HOLDINGS, WATCH_LIST, DATA_DIR
from indicator_engine import load_kline, calc_ma, calc_macd, calc_kdj, calc_rsi


def analyze_period(symbol, start_date, end_date):
    """分析指定时期的信号效果"""
    data = load_kline(symbol)
    if not data or 'data' not in data:
        return None
    
    klines = data['data']
    
    # 筛选时期数据
    period_data = []
    for k in klines:
        if start_date <= k['day'] <= end_date:
            period_data.append(k)
    
    if len(period_data) < 20:
        return None
    
    # 统计倍量柱
    vol_signals = []
    for i in range(1, len(period_data)):
        curr = period_data[i]
        prev = period_data[i-1]
        vol_ratio = curr['volume'] / prev['volume'] if prev['volume'] > 0 else 0
        
        if vol_ratio >= 1.9 and curr['close'] > curr['open']:
            # 计算后续表现
            next_5d_return = 0
            next_10d_return = 0
            
            if i + 5 < len(period_data):
                next_5d_return = (period_data[i+5]['close'] - curr['close']) / curr['close'] * 100
            if i + 10 < len(period_data):
                next_10d_return = (period_data[i+10]['close'] - curr['close']) / curr['close'] * 100
            
            vol_signals.append({
                'date': curr['day'],
                'vol_ratio': round(vol_ratio, 2),
                'price': curr['close'],
                'next_5d': round(next_5d_return, 2),
                'next_10d': round(next_10d_return, 2)
            })
    
    # 计算黄金线胜率
    golden_results = {'total': 0, 'valid': 0}
    for i in range(len(period_data)-10, len(period_data)):
        if i < 2:
            continue
        curr = period_data[i]
        prev = period_data[i-1]
        
        if prev['volume'] > curr['volume'] * 1.5 and curr['close'] > curr['open']:
            support = curr['low']
            golden_results['total'] += 1
            
            # 检查后续5天是否守住支撑
            hit = True
            for j in range(i+1, min(i+6, len(period_data))):
                if period_data[j]['low'] < support * 0.98:
                    hit = False
                    break
            if hit:
                golden_results['valid'] += 1
    
    golden_win_rate = round(golden_results['valid'] / golden_results['total'] * 100, 1) if golden_results['total'] > 0 else 0
    
    # 计算均线信号
    closes = [k['close'] for k in period_data]
    ma5 = calc_ma(period_data, 5)
    ma10 = calc_ma(period_data, 10)
    
    ma_signals = {'golden_cross': 0, 'death_cross': 0, 'above_avg': 0, 'below_avg': 0}
    for i in range(1, len(period_data)):
        if ma5[i] and ma10[i] and ma5[i-1] and ma10[i-1]:
            if ma5[i-1] <= ma10[i-1] and ma5[i] > ma10[i]:
                ma_signals['golden_cross'] += 1
            elif ma5[i-1] >= ma10[i-1] and ma5[i] < ma10[i]:
                ma_signals['death_cross'] += 1
        
        if closes[i] > ma5[i] if ma5[i] else False:
            ma_signals['above_avg'] += 1
        else:
            ma_signals['below_avg'] += 1
    
    # 计算MACD信号
    macd = calc_macd(period_data)
    macd_signals = {'golden_cross': 0, 'death_cross': 0, 'red_bar': 0, 'green_bar': 0}
    for i in range(1, len(period_data)):
        if macd['dif'][i] and macd['dea'][i] and macd['dif'][i-1] and macd['dea'][i-1]:
            if macd['dif'][i-1] <= macd['dea'][i-1] and macd['dif'][i] > macd['dea'][i]:
                macd_signals['golden_cross'] += 1
            elif macd['dif'][i-1] >= macd['dea'][i-1] and macd['dif'][i] < macd['dea'][i]:
                macd_signals['death_cross'] += 1
        
        if macd['macd'][i] and macd['macd'][i] > 0:
            macd_signals['red_bar'] += 1
        elif macd['macd'][i] and macd['macd'][i] < 0:
            macd_signals['green_bar'] += 1
    
    # 计算KDJ信号
    kdj = calc_kdj(period_data)
    kdj_signals = {'oversold': 0, 'overbought': 0}
    for v in kdj['j']:
        if v is not None:
            if v < 20:
                kdj_signals['oversold'] += 1
            elif v > 80:
                kdj_signals['overbought'] += 1
    
    # 计算RSI信号
    rsi = calc_rsi(period_data)
    rsi_signals = {'oversold': 0, 'overbought': 0}
    for v in rsi:
        if v is not None:
            if v < 30:
                rsi_signals['oversold'] += 1
            elif v > 70:
                rsi_signals['overbought'] += 1
    
    return {
        'symbol': symbol,
        'period': f"{start_date} ~ {end_date}",
        'days': len(period_data),
        'vol_signals': vol_signals,
        'golden_win_rate': golden_win_rate,
        'golden_tests': golden_results['total'],
        'ma_signals': ma_signals,
        'macd_signals': macd_signals,
        'kdj_signals': kdj_signals,
        'rsi_signals': rsi_signals,
        'latest_price': closes[-1],
        'period_return': round((closes[-1] - closes[0]) / closes[0] * 100, 2) if closes[0] else 0
    }


def batch_historical_analysis(stocks=None, periods=None):
    """批量历史分析"""
    if stocks is None:
        stocks = list(HOLDINGS.keys())
    
    if periods is None:
        # 默认分析近一年分4个季度
        today = datetime.now()
        periods = [
            (today - timedelta(days=360), today - timedelta(days=270)),  # Q1
            (today - timedelta(days=270), today - timedelta(days=180)),  # Q2
            (today - timedelta(days=180), today - timedelta(days=90)),   # Q3
            (today - timedelta(days=90), today),                         # Q4
        ]
    
    results = {}
    for sym in stocks:
        results[sym] = {}
        for start, end in periods:
            period_key = f"{start.strftime('%Y-%m')}~{end.strftime('%Y-%m')}"
            analysis = analyze_period(sym, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
            if analysis:
                results[sym][period_key] = analysis
    
    return results


def generate_comparison_report(results):
    """生成对比报告"""
    lines = []
    lines.append("# 量学理论历史适用性对比报告\n")
    lines.append(f"**生成日期**：{datetime.now().strftime('%Y-%m-%d')}\n")
    
    # 汇总表格
    lines.append("## 各时期信号效果对比\n")
    lines.append("| 股票 | 时期 | 倍量柱次数 | 黄金线胜率 | MA金叉 | MACD金叉 | KDJ超卖 | RSI超卖 | 期间涨幅 |")
    lines.append("|-----|------|-----------|-----------|-------|---------|--------|--------|---------|")
    
    for sym, periods in results.items():
        for period, data in periods.items():
            lines.append(f"| {sym} | {period} | {len(data['vol_signals'])} | {data['golden_win_rate']}% | "
                        f"{data['ma_signals']['golden_cross']} | {data['macd_signals']['golden_cross']} | "
                        f"{data['kdj_signals']['oversold']} | {data['rsi_signals']['oversold']} | {data['period_return']}% |")
    
    lines.append("\n## 信号有效性统计\n")
    
    # 统计各信号有效性
    stats = {
        'volume': {'count': 0, 'win': 0},
        'golden': {'count': 0, 'win': 0},
        'ma_golden': {'count': 0},
        'macd_golden': {'count': 0},
        'kdj_oversold': {'count': 0},
        'rsi_oversold': {'count': 0}
    }
    
    for sym, periods in results.items():
        for period, data in periods.items():
            # 倍量柱
            stats['volume']['count'] += len(data['vol_signals'])
            for sig in data['vol_signals']:
                if sig['next_10d'] > 0:
                    stats['volume']['win'] += 1
            
            # 黄金线
            if data['golden_tests'] > 0:
                stats['golden']['count'] += 1
                if data['golden_win_rate'] >= 50:
                    stats['golden']['win'] += 1
            
            # MA金叉
            stats['ma_golden']['count'] += data['ma_signals']['golden_cross']
            
            # MACD金叉
            stats['macd_golden']['count'] += data['macd_signals']['golden_cross']
            
            # KDJ超卖
            stats['kdj_oversold']['count'] += data['kdj_signals']['oversold']
            
            # RSI超卖
            stats['rsi_oversold']['count'] += data['rsi_signals']['oversold']
    
    lines.append("### 信号统计\n")
    if stats['volume']['count'] > 0:
        vol_win_rate = round(stats['volume']['win'] / stats['volume']['count'] * 100, 1)
        lines.append(f"- **倍量柱信号**：{stats['volume']['count']}次，10日上涨率{vol_win_rate}%")
    if stats['golden']['count'] > 0:
        golden_win_rate = round(stats['golden']['win'] / stats['golden']['count'] * 100, 1)
        lines.append(f"- **黄金线支撑**：{stats['golden']['count']}次测试，胜率{golden_win_rate}%")
    
    lines.append(f"\n- **MA金叉次数**：{stats['ma_golden']['count']}次")
    lines.append(f"- **MACD金叉次数**：{stats['macd_golden']['count']}次")
    lines.append(f"- **KDJ超卖次数**：{stats['kdj_oversold']['count']}次")
    lines.append(f"- **RSI超卖次数**：{stats['rsi_oversold']['count']}次")
    
    lines.append("\n## 结论与建议\n")
    lines.append("### 信号有效性排序\n")
    
    # 根据统计结果排序
    signal_scores = []
    if stats['volume']['count'] > 0:
        signal_scores.append(('倍量柱', vol_win_rate))
    if stats['golden']['count'] > 0:
        signal_scores.append(('黄金线', golden_win_rate))
    
    signal_scores.sort(key=lambda x: x[1], reverse=True)
    
    for i, (name, rate) in enumerate(signal_scores, 1):
        lines.append(f"{i}. {name}：胜率{rate}%")
    
    lines.append("\n### 实战建议\n")
    lines.append("1. 优先使用高胜率信号作为主要依据")
    lines.append("2. 低胜率信号可作为辅助参考")
    lines.append("3. 结合市场环境选择合适信号")
    lines.append("4. 严格执行止损纪律\n")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', nargs='+', help='股票代码列表')
    parser.add_argument('--output', help='输出文件路径')
    args = parser.parse_args()
    
    symbols = args.symbols or list(HOLDINGS.keys())
    results = batch_historical_analysis(symbols)
    
    report = generate_comparison_report(results)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存: {args.output}")
    else:
        print(report)
