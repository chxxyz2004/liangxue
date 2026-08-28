#!/usr/bin/env python3
"""
量学图表生成器
生成HTML格式的K线图表（纯文本，无外部依赖）
"""
import json
import sys
from datetime import datetime

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/技术指标')
from config import HOLDINGS, WATCH_LIST, DATA_DIR
from indicator_engine import load_kline, calc_all_indicators


def generate_candlestick_chart(symbol, days=60):
    """生成K线图HTML"""
    data = load_kline(symbol)
    if not data or 'data' not in data:
        return None
    
    klines = data['data'][-days:]
    info = HOLDINGS.get(symbol, WATCH_LIST.get(symbol, None))
    name = info.name if info else symbol
    
    # 计算指标（需要完整序列）
    from indicator_engine import calc_ma, calc_all_indicators
    klines_full = data['data'][-days:]
    ma5_data = calc_ma(klines_full, 5)
    ma10_data = calc_ma(klines_full, 10)
    ma20_data = calc_ma(klines_full, 20)
    
    # 计算最新指标值（用于显示）
    latest_indicators = calc_all_indicators(symbol, lookback=days)
    
    # 准备数据
    dates = [k['day'][-5:] for k in klines]  # 只显示月-日
    opens = [k['open'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 价格范围
    price_min = min(lows) * 0.95
    price_max = max(highs) * 1.05
    vol_max = max(volumes)
    
    # 生成图表数据
    chart_width = 800
    chart_height = 400
    padding = 50
    
    # 计算缩放比例
    price_range = price_max - price_min
    vol_range = vol_max
    
    rows = []
    rows.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} ({symbol}) - K线图</title>
<style>
body {{ font-family: -apple-system, "PingFang SC", sans-serif; background: #0a0e14; color: #e8edf4; margin: 0; padding: 20px; }}
.container {{ max-width: {chart_width}px; margin: 0 auto; }}
h1 {{ text-align: center; color: #e8edf4; }}
.chart {{ background: #151b23; border: 1px solid #2a3441; border-radius: 8px; padding: 20px; margin-top: 20px; }}
.info {{ display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px; }}
.info-item {{ background: #1e2530; padding: 10px 15px; border-radius: 4px; }}
.info-label {{ font-size: 12px; color: #8899a6; }}
.info-value {{ font-size: 16px; font-weight: 600; }}
.signal {{ background: #1e2530; padding: 10px; border-radius: 4px; margin-top: 10px; }}
.signal-type {{ color: #3498db; font-weight: 600; }}
.signal-desc {{ font-size: 12px; color: #8899a6; margin-top: 5px; }}
svg {{ width: 100%; height: auto; }}
.text-date {{ font-size: 10px; fill: #8899a6; }}
.text-price {{ font-size: 10px; fill: #8899a6; }}
.grid {{ stroke: #2a3441; stroke-width: 1; }}
.candle-up {{ fill: #ff4757; stroke: #ff4757; }}
.candle-down {{ fill: #2ed573; stroke: #2ed573; }}
.ma5 {{ stroke: #f39c12; stroke-width: 1.5; fill: none; }}
.ma10 {{ stroke: #3498db; stroke-width: 1.5; fill: none; }}
.ma20 {{ stroke: #9b59b6; stroke-width: 1.5; fill: none; }}
.back-btn {{ display: inline-block; margin-bottom: 20px; color: #3498db; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
<a href="#" onclick="history.back();return false" class="back-btn">← 返回</a>
<h1>{name} ({symbol})</h1>
<div class="info">
''')
    
    # 添加信息
    if latest_indicators:
        ind = latest_indicators['indicators']
        latest = closes[-1]
        prev = closes[-2] if len(closes) > 1 else latest
        change_pct = (latest - prev) / prev * 100
        
        rows.append(f'''<div class="info-item"><div class="info-label">最新价</div><div class="info-value">{latest}</div></div>
<div class="info-item"><div class="info-label">涨跌</div><div class="info-value" style="color:{'#ff4757' if change_pct >= 0 else '#2ed573'}">{change_pct:+.2f}%</div></div>
<div class="info-item"><div class="info-label">MA5</div><div class="info-value">{ind['ma']['ma5']}</div></div>
<div class="info-item"><div class="info-label">MA10</div><div class="info-value">{ind['ma']['ma10']}</div></div>
<div class="info-item"><div class="info-label">MA20</div><div class="info-value">{ind['ma']['ma20']}</div></div>
''')
    
    rows.append('</div>\n')
    
    # 生成SVG图表
    cell_width = (chart_width - 2 * padding) / len(klines)
    
    rows.append('<div class="chart">\n<svg viewBox="0 0 {} {}">'.format(chart_width, chart_height))
    
    # 网格线
    for i in range(5):
        y = padding + (chart_height - 2 * padding) * i / 4
        rows.append('<line x1="{}" y1="{}" x2="{}" y2="{}" class="grid"/>'.format(
            padding, y, chart_width - padding, y))
        price = price_max - price_range * i / 4
        rows.append('<text x="{}" y="{}" class="text-price" text-anchor="end">{}</text>'.format(
            padding - 5, y + 3, round(price, 1)))
    
    # 绘制K线
    for i, (o, h, l, c, v) in enumerate(zip(opens, highs, lows, closes, volumes)):
        x = padding + i * cell_width + cell_width / 2
        is_up = c >= o
        
        # 实体
        body_top = padding + (price_max - max(o, c)) / price_range * (chart_height - 2 * padding)
        body_bottom = padding + (price_max - min(o, c)) / price_range * (chart_height - 2 * padding)
        body_height = max(body_bottom - body_top, 1)
        
        cls = 'candle-up' if is_up else 'candle-down'
        rows.append('<rect x="{}" y="{}" width="{}" height="{}" class="{}"/>'.format(
            x - cell_width * 0.3, body_top, cell_width * 0.6, body_height, cls))
        
        # 影线
        high_y = padding + (price_max - h) / price_range * (chart_height - 2 * padding)
        low_y = padding + (price_max - l) / price_range * (chart_height - 2 * padding)
        rows.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="1"/>'.format(
            x, high_y, x, low_y, '#2ed573' if is_up else '#ff4757'))
        
        # 日期标签（每10天显示一个）
        if i % 10 == 0:
            rows.append('<text x="{}" y="{}" class="text-date" text-anchor="middle">{}</text>'.format(
                x, chart_height - 10, dates[i]))
    
    # 绘制均线
    path_d = ''
    for i, v in enumerate(ma5_data):
        if v:
            x = padding + i * cell_width + cell_width / 2
            y = padding + (price_max - v) / price_range * (chart_height - 2 * padding)
            path_d += ('M' if i == 0 else 'L') + f'{x},{y} '
    if path_d:
        rows.append('<path d="{}" class="ma5"/>'.format(path_d))
    
    # MA10
    path_d = ''
    for i, v in enumerate(ma10_data):
        if v:
            x = padding + i * cell_width + cell_width / 2
            y = padding + (price_max - v) / price_range * (chart_height - 2 * padding)
            path_d += ('M' if i == 0 else 'L') + f'{x},{y} '
    if path_d:
        rows.append('<path d="{}" class="ma10"/>'.format(path_d))
    
    # MA20
    path_d = ''
    for i, v in enumerate(ma20_data):
        if v:
            x = padding + i * cell_width + cell_width / 2
            y = padding + (price_max - v) / price_range * (chart_height - 2 * padding)
            path_d += ('M' if i == 0 else 'L') + f'{x},{y} '
    if path_d:
        rows.append('<path d="{}" class="ma20"/>'.format(path_d))
    
    rows.append('</svg>\n')
    
    # 图例
    rows.append('''<div style="margin-top:20px;display:flex;gap:20px;font-size:12px;">
<div><span style="color:#f39c12;">━</span> MA5</div>
<div><span style="color:#3498db;">━</span> MA10</div>
<div><span style="color:#9b59b6;">━</span> MA20</div>
<div><span style="color:#ff4757;">■</span> 阳线</div>
<div><span style="color:#2ed573;">■</span> 阴线</div>
</div>\n''')
    
    # 信号列表
    if latest_indicators and latest_indicators.get('signals'):
        rows.append('<div style="margin-top:20px;"><h3>技术信号</h3>\n')
        for sig in latest_indicators['signals']:
            rows.append('<div class="signal"><div class="signal-type">{}</div><div class="signal-desc">{}</div></div>\n'.format(
                sig['type'], sig['desc']))
        rows.append('</div>\n')
    
    rows.append('</div>\n</body>\n</html>')
    
    return ''.join(rows)


def batch_generate_charts(stocks=None, output_dir='/workspace/现代量学讲义/图表'):
    """批量生成图表"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    if stocks is None:
        stocks = list(HOLDINGS.keys())
    
    results = []
    for sym in stocks:
        html = generate_candlestick_chart(sym)
        if html:
            name = HOLDINGS.get(sym, {}).name if isinstance(HOLDINGS.get(sym), object) else sym
            path = f'{output_dir}/chart_{sym}.html'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            results.append({'symbol': sym, 'name': name, 'path': path})
            print(f"已生成: {path}")
    
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', help='单只股票')
    parser.add_argument('--batch', action='store_true', help='批量生成')
    parser.add_argument('--output', default='/workspace/现代量学讲义/图表')
    args = parser.parse_args()
    
    if args.batch:
        batch_generate_charts(output_dir=args.output)
    elif args.symbol:
        html = generate_candlestick_chart(args.symbol)
        if html:
            path = f'{args.output}/chart_{args.symbol}.html'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"已生成: {path}")
    else:
        # 默认生成持仓股图表
        batch_generate_charts(list(HOLDINGS.keys()), args.output)
