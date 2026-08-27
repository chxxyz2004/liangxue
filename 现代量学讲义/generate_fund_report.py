#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学资金识别报告生成器 - 贯穿全天的核心报告"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/workspace/行情数据库')

HOLDINGS = {
    'sh603516': {'name': '淳中科技', 'cost': 98.50, 'shares': 900, 'stop_loss': 90.63, 'life_line': 92.6},
    'sh601138': {'name': '工业富联', 'cost': 58.20, 'shares': 1100},
    'sz002156': {'name': '通富微电', 'cost': 45.80, 'shares': 700},
    'sh601231': {'name': '环旭电子', 'cost': 28.50, 'shares': 800},
    'sz300476': {'name': '胜宏科技', 'cost': 230.00, 'shares': 100, 'take_profit': (256, 260)},
    'sh603283': {'name': '赛腾股份', 'cost': 52.30, 'shares': 400},
}

def load_kline(sym):
    path = f'/workspace/行情数据库/kline/{sym}.json'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get('data', [])
    return []

def get_index_data():
    """获取大盘指数数据"""
    indexes = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指'}
    results = {}
    for sym, name in indexes.items():
        kl = load_kline(sym)
        if len(kl) >= 2:
            today, yesterday = kl[-1], kl[-2]
            change = (today['close'] - yesterday['close']) / yesterday['close'] * 100
            vol_ratio = today['volume'] / yesterday['volume'] if yesterday['volume'] > 0 else 0
            results[name] = {
                'close': today['close'],
                'change': change,
                'vol_ratio': vol_ratio
            }
    return results

def analyze_stock_for_fund(sym, info, kl):
    """分析单只股票的资金行为"""
    if len(kl) < 2:
        return None
    
    today = kl[-1]
    yesterday = kl[-2]
    
    cp, op, high, low = today['close'], today['open'], today['high'], today['low']
    vol = today['volume']
    vol_ratio = vol / yesterday['volume'] if yesterday['volume'] > 0 else 0
    
    # 资金行为判断
    fund_behavior = []
    
    # 1. 量价关系
    if vol_ratio >= 1.9 and cp > op:
        fund_behavior.append(('倍量上涨', 'up'))
    elif vol_ratio >= 1.5 and cp > op:
        fund_behavior.append(('放量上涨', 'up'))
    elif vol_ratio <= 0.5 and cp > op:
        fund_behavior.append(('缩量上涨', 'flat'))
    elif vol_ratio <= 0.5 and cp < op:
        fund_behavior.append(('缩量下跌', 'down'))
    elif vol_ratio >= 1.5 and cp < op:
        fund_behavior.append(('放量下跌', 'down'))
    
    # 2. 主力行为
    upper_shadow = high - max(cp, op)
    lower_shadow = min(cp, op) - low
    body = abs(cp - op)
    
    if upper_shadow > body * 2 and body > 0:
        fund_behavior.append(('长上影出货', 'down'))
    elif lower_shadow > body * 2 and body > 0:
        fund_behavior.append(('长下影支撑', 'up'))
    
    # 3. 位置判断
    closes = [k['close'] for k in kl]
    high_250 = max(closes[-250:]) if len(closes) >= 250 else max(closes)
    low_250 = min(closes[-250:]) if len(closes) >= 250 else min(closes)
    pos_250 = (cp - low_250) / (high_250 - low_250) * 100
    
    if pos_250 > 80:
        fund_behavior.append(('高位风险', 'down'))
    elif pos_250 < 20:
        fund_behavior.append(('低位机会', 'up'))
    
    change = (cp - yesterday['close']) / yesterday['close'] * 100
    profit_pct = (cp - info['cost']) / info['cost'] * 100
    
    return {
        'sym': sym,
        'name': info['name'],
        'cp': cp,
        'op': op,
        'high': high,
        'low': low,
        'vol': vol,
        'vol_ratio': vol_ratio,
        'change': change,
        'profit_pct': profit_pct,
        'pos_250': pos_250,
        'fund_behavior': fund_behavior,
        'stop_loss': info.get('stop_loss'),
        'take_profit': info.get('take_profit')
    }

def generate_morning_report(today_str, time_str):
    """生成午间资金识别报告"""
    all_stocks = []
    
    for sym, info in HOLDINGS.items():
        kl = load_kline(sym)
        if kl:
            analysis = analyze_stock_for_fund(sym, info, kl)
            if analysis:
                all_stocks.append(analysis)
    
    index_data = get_index_data()
    
    # 生成HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{today_str} 午间资金识别 | 现代量学实战体系</title>
<style>
:root {{ --bg:#0a0e14; --surface:#151b23; --surface2:#1e2530; --border:#2a3441; --text:#e8edf4; --text-dim:#8899a6; --accent:#f5a623; --red:#ff4757; --green:#2ed573; --orange:#e67e22; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"PingFang SC",sans-serif; background:var(--bg); color:var(--text); font-size:15px; line-height:1.7; padding:16px; }}
h1 {{ font-size:20px; font-weight:700; color:var(--accent); margin-bottom:8px; }}
h2 {{ font-size:17px; font-weight:700; color:var(--accent); margin:24px 0 12px; padding-left:10px; border-left:4px solid var(--red); }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px; margin:12px 0; }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; min-width:600px; }}
th,td {{ padding:10px 8px; text-align:left; border-bottom:1px solid var(--border); }}
th {{ background:var(--surface2); color:var(--accent); font-weight:600; white-space:nowrap; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.up {{ color:var(--red); }} .down {{ color:var(--green); }} .flat {{ color:var(--orange); }}
.tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; margin:2px; }}
.tag-up {{ background:rgba(46,213,115,0.15); color:var(--green); }}
.tag-down {{ background:rgba(255,71,87,0.15); color:var(--red); }}
.tag-flat {{ background:rgba(230,126,34,0.15); color:var(--orange); }}
.core {{ background:var(--surface); border-left:4px solid var(--accent); border-radius:10px; padding:14px; margin:16px 0; }}
.footer {{ margin-top:30px; padding-top:16px; border-top:1px solid var(--border); color:var(--text-dim); font-size:12px; text-align:center; }}
</style>
</head>
<body>

<div class="card">
  <p style="margin:0 0 8px"><a href="./index.html" style="color:var(--blue)">← 返回讲义首页</a></p>
  <h1><span class="tag tag-flat">午间资金识别</span> {today_str} · 11:30数据</h1>
  <p style="font-size:13px;color:var(--text-dim);margin-top:6px">现代量学实战体系 · 上午资金流向全景 + 主力行为判断</p>
</div>

<h2>一、大盘环境（上午）</h2>
<div class="table-wrap">
<table>
<tr><th>指数</th><th>收盘</th><th>涨跌</th><th>量比</th><th>环境判定</th></tr>
'''
    
    for name, data in index_data.items():
        cls = 'up' if data['change'] >= 0 else 'down'
        env = '强势' if data['change'] > 0.5 and data['vol_ratio'] > 1 else ('弱势' if data['change'] < -0.5 else '震荡')
        html += f'<tr><td>{name}</td><td class="num">{data["close"]:.2f}</td><td class="num {cls}">{data["change"]:+.2f}%</td><td class="num">{data["vol_ratio"]:.2f}</td><td class="{cls}">{env}</td></tr>\n'
    
    html += '''
</table>
</div>

<h2>二、持仓资金行为分析（上午）</h2>
<div class="table-wrap">
<table>
<tr><th>股票</th><th>现价</th><th>涨跌</th><th>量比</th><th>250位</th><th>资金行为</th><th>判断</th></tr>
'''
    
    for s in all_stocks:
        cls = 'up' if s['change'] >= 0 else 'down'
        pos_cls = 'up' if s['pos_250'] < 50 else ('down' if s['pos_250'] > 70 else 'flat')
        
        # 资金行为标签
        behavior_tags = ''
        for behavior, direction in s['fund_behavior'][:2]:
            tag_cls = 'tag-up' if direction == 'up' else ('tag-down' if direction == 'down' else 'tag-flat')
            behavior_tags += f'<span class="tag {tag_cls}">{behavior}</span> '
        
        # 综合判断
        if len(s['fund_behavior']) >= 2 and any('上涨' in b for b, d in s['fund_behavior'][:2]):
            judgment = '<span class="up">主力进场</span>'
        elif any('下跌' in b for b, d in s['fund_behavior'][:2]):
            judgment = '<span class="down">主力出货</span>'
        else:
            judgment = '<span class="flat">观望为主</span>'
        
        html += f'''<tr>
<td><strong>{s['name']}</strong></td>
<td class="num {cls}">{s['cp']:.2f}</td>
<td class="num {cls}">{s['change']:+.2f}%</td>
<td class="num">{s['vol_ratio']:.2f}</td>
<td class="num {pos_cls}">{s['pos_250']:.0f}%</td>
<td>{behavior_tags}</td>
<td>{judgment}</td>
</tr>
'''
    
    html += '''
</table>
</div>

<div class="core">
  <p style="font-weight:700;color:var(--accent);margin-bottom:8px">午间资金识别结论</p>
  <ul style="margin:0;padding-left:20px">
    <li><strong>大盘环境：</strong>根据上午量能判断市场情绪，决定下午仓位策略</li>
    <li><strong>持仓重点：</strong>关注量比异常（>1.5或<0.5）的股票，这是主力行为的直接信号</li>
    <li><strong>风险提示：</strong>高位放量下跌=出货，低位缩量下跌=洗盘，需区分对待</li>
  </ul>
</div>

<div class="footer">
  <p>现代量学实战体系 · 午间资金识别 {today_str}</p>
  <p style="margin-top:6px">数据截止：11:30午盘 | 来源：腾讯证券前复权日K</p>
</div>

</body></html>
'''
    
    return html

def generate_evening_report(today_str, time_str):
    """生成收盘资金识别+全面复盘报告（含次日预案）"""
    all_stocks = []
    total_profit = 0
    total_value = 0
    
    for sym, info in HOLDINGS.items():
        kl = load_kline(sym)
        if kl:
            analysis = analyze_stock_for_fund(sym, info, kl)
            if analysis:
                profit = (analysis['cp'] - info['cost']) * info['shares']
                analysis['profit'] = profit
                analysis['value'] = analysis['cp'] * info['shares']
                total_profit += profit
                total_value += analysis['value']
                all_stocks.append(analysis)
    
    index_data = get_index_data()
    
    # 生成HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{today_str} 收盘资金识别+复盘 | 现代量学实战体系</title>
<style>
:root {{ --bg:#0a0e14; --surface:#151b23; --surface2:#1e2530; --border:#2a3441; --text:#e8edf4; --text-dim:#8899a6; --accent:#f5a623; --red:#ff4757; --green:#2ed573; --orange:#e67e22; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"PingFang SC",sans-serif; background:var(--bg); color:var(--text); font-size:15px; line-height:1.7; padding:16px; }}
h1 {{ font-size:20px; font-weight:700; color:var(--accent); margin-bottom:8px; }}
h2 {{ font-size:17px; font-weight:700; color:var(--accent); margin:24px 0 12px; padding-left:10px; border-left:4px solid var(--red); }}
h3 {{ font-size:16px; font-weight:700; color:#e8b04a; margin:18px 0 10px; }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px; margin:12px 0; }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; min-width:600px; }}
th,td {{ padding:10px 8px; text-align:left; border-bottom:1px solid var(--border); }}
th {{ background:var(--surface2); color:var(--accent); font-weight:600; white-space:nowrap; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.up {{ color:var(--red); }} .down {{ color:var(--green); }} .flat {{ color:var(--orange); }}
.tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; margin:2px; }}
.tag-up {{ background:rgba(46,213,115,0.15); color:var(--green); }}
.tag-down {{ background:rgba(255,71,87,0.15); color:var(--red); }}
.tag-flat {{ background:rgba(230,126,34,0.15); color:var(--orange); }}
.core {{ background:var(--surface); border-left:4px solid var(--accent); border-radius:10px; padding:14px; margin:16px 0; }}
.warn {{ background:rgba(255,71,87,0.1); border:1px solid rgba(255,71,87,0.3); border-radius:10px; padding:14px; margin:16px 0; }}
.six {{ background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; margin:10px 0; }}
.sixh {{ font-weight:700; color:var(--accent); margin-bottom:6px; font-size:14px; }}
.sixb {{ color:var(--text-dim); font-size:13px; line-height:1.6; }}
.stat-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:16px 0; }}
.stat-box {{ background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; text-align:center; }}
.stat-val {{ font-size:22px; font-weight:700; }}
.stat-lbl {{ font-size:11px; color:var(--text-dim); margin-top:4px; }}
.plan-box {{ background:rgba(245,166,35,0.1); border:1px solid rgba(245,166,35,0.3); border-radius:10px; padding:14px; margin:16px 0; }}
.footer {{ margin-top:30px; padding-top:16px; border-top:1px solid var(--border); color:var(--text-dim); font-size:12px; text-align:center; }}
</style>
</head>
<body>

<div class="card">
  <p style="margin:0 0 8px"><a href="./index.html" style="color:var(--blue)">← 返回讲义首页</a></p>
  <h1><span class="tag tag-flat">收盘资金识别+全面复盘</span> {today_str} · 15:00后</h1>
  <p style="font-size:13px;color:var(--text-dim);margin-top:6px">现代量学实战体系 · 全天资金流向 + 六步拆解 + 次日预案</p>
</div>

<div class="stat-grid">
  <div class="stat-box"><div class="stat-val {'up' if total_profit >= 0 else 'down'}">{total_profit:+,.0f}</div><div class="stat-lbl">总盈亏</div></div>
  <div class="stat-box"><div class="stat-val">{total_value:,.0f}</div><div class="stat-lbl">持仓市值</div></div>
  <div class="stat-box"><div class="stat-val {'up' if total_profit >= 0 else 'down'}">{total_profit/total_value*100:+.2f}%</div><div class="stat-lbl">收益率</div></div>
</div>

<h2>一、大盘环境（全天）</h2>
<div class="table-wrap">
<table>
<tr><th>指数</th><th>收盘</th><th>涨跌</th><th>量比</th><th>环境判定</th></tr>
'''
    
    for name, data in index_data.items():
        cls = 'up' if data['change'] >= 0 else 'down'
        env = '强势' if data['change'] > 0.5 and data['vol_ratio'] > 1 else ('弱势' if data['change'] < -0.5 else '震荡')
        html += f'<tr><td>{name}</td><td class="num">{data["close"]:.2f}</td><td class="num {cls}">{data["change"]:+.2f}%</td><td class="num">{data["vol_ratio"]:.2f}</td><td class="{cls}">{env}</td></tr>\n'
    
    html += '''
</table>
</div>

<h2>二、持仓资金行为全天分析</h2>
<div class="table-wrap">
<table>
<tr><th>股票</th><th>收盘</th><th>涨跌</th><th>量比</th><th>250位</th><th>全天行为</th><th>主力意图</th></tr>
'''
    
    for s in all_stocks:
        cls = 'up' if s['change'] >= 0 else 'down'
        pos_cls = 'up' if s['pos_250'] < 50 else ('down' if s['pos_250'] > 70 else 'flat')
        
        # 全天资金行为标签
        behavior_tags = ''
        for behavior, direction in s['fund_behavior'][:2]:
            tag_cls = 'tag-up' if direction == 'up' else ('tag-down' if direction == 'down' else 'tag-flat')
            behavior_tags += f'<span class="tag {tag_cls}">{behavior}</span> '
        
        # 主力意图判断
        if len(s['fund_behavior']) >= 2 and any('上涨' in b for b, d in s['fund_behavior'][:2]) and s['pos_250'] < 60:
            intent = '<span class="up">主力建仓/加仓</span>'
        elif any('下跌' in b for b, d in s['fund_behavior'][:2]) and s['pos_250'] > 60:
            intent = '<span class="down">主力出货</span>'
        elif s['pos_250'] < 30:
            intent = '<span class="flat">低位筑底</span>'
        else:
            intent = '<span class="flat">观望为主</span>'
        
        html += f'''<tr>
<td><strong>{s['name']}</strong></td>
<td class="num {cls}">{s['cp']:.2f}</td>
<td class="num {cls}">{s['change']:+.2f}%</td>
<td class="num">{s['vol_ratio']:.2f}</td>
<td class="num {pos_cls}">{s['pos_250']:.0f}%</td>
<td>{behavior_tags}</td>
<td>{intent}</td>
</tr>
'''
    
    html += '''
</table>
</div>

<h2>三、重点股票六步拆解</h2>
'''
    
    # 对重点股票进行六步拆解
    key_stocks = [s for s in all_stocks if s['name'] in ['淳中科技', '胜宏科技', '工业富联']]
    
    for s in key_stocks:
        html += f'''
<div class="card">
  <div style="font-weight:700;color:var(--accent);font-size:15px;margin-bottom:10px">{s['name']}（{s['sym']}）收{s['cp']:.2f} 量比{s['vol_ratio']:.2f}</div>
  
  <div class="six">
    <div class="sixh">第①步 · 左证明建构</div>
    <div class="sixb"><p>全天量价关系：开盘{s['op']:.2f} → 最高{s['high']:.2f} → 最低{s['low']:.2f} → 收盘{s['cp']:.2f}，成交量{s['vol']//10000}万手，量比{s['vol_ratio']:.2f}。</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第②步 · 左侧生死线</div>
    <div class="sixb"><p>当前价{s['cp']:.2f}，250日位置{s['pos_250']:.0f}%。{"已超止盈区间" if s.get("take_profit") and s["cp"] > s["take_profit"][1] else "处于正常区间"}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第③步 · 右确认</div>
    <div class="sixb"><p>需明日验证是否能站稳当前位置。</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第④步 · 市场机理</div>
    <div class="sixb"><p>{"高位放量=出货风险" if s["pos_250"] > 70 and s["vol_ratio"] > 1.5 else "低位缩量=筑底过程" if s["pos_250"] < 30 else "腰部震荡=方向未定"}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第⑤步 · 结论</div>
    <div class="sixb"><p style="font-weight:700;color:var(--accent)">{s["fund_behavior"][0][0] if s["fund_behavior"] else "观望"}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第⑥步 · 操作建议</div>
    <div class="sixb"><p>{"明日优先减仓锁定利润" if s.get("take_profit") and s["cp"] > s["take_profit"][1] else "止损线"+str(s["stop_loss"]) if s.get("stop_loss") else "暂持观察"}</p></div>
  </div>
</div>
'''
    
    html += '''
<h2>四、次日预案</h2>
<div class="plan-box">
  <p style="font-weight:700;color:var(--accent);margin-bottom:10px">明日重点关注</p>
  <ul style="margin:0;padding-left:20px">
'''
    
    # 动态生成次日预案
    for s in all_stocks:
        if s.get('take_profit') and s['cp'] > s['take_profit'][1]:
            html += f'<li><span class="up" style="font-weight:700">{s["name"]}</span>：已进入止盈区间，明日优先减仓锁定利润</li>\n'
        elif s.get('stop_loss') and s['cp'] < s['stop_loss']:
            html += f'<li><span class="down" style="font-weight:700">{s["name"]}</span>：已破止损线{s["stop_loss"]}，明日离场</li>\n'
        elif s['vol_ratio'] >= 1.9 and s['change'] > 0:
            html += f'<li><span class="up" style="font-weight:700">{s["name"]}</span>：倍量突破，明日若企稳可考虑加仓</li>\n'
    
    html += '''
  </ul>
  <p style="margin-top:12px;font-size:13px;color:var(--text-dim)">大盘弱反弹（量能不足），持仓修复为主。仓位策略不变：弱市总仓上限2-4成。</p>
</div>

<div class="footer">
  <p>现代量学实战体系 · 收盘资金识别+全面复盘 {today_str}</p>
  <p style="margin-top:6px">数据截止：15:00收盘 | 来源：腾讯证券前复权日K | 算法：本地行情库</p>
</div>

</body></html>
'''
    
    return html

def main():
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')
    hour = now.hour
    
    # 根据时间决定生成哪种报告
    if 11 <= hour < 13:
        # 午间
        print(f"生成午间资金识别报告: {today_str}")
        html = generate_morning_report(today_str, time_str)
        filename = f'/workspace/现代量学讲义/午间资金识别-{today_str}.html'
    elif hour >= 15:
        # 收盘后
        print(f"生成收盘资金识别+全面复盘报告: {today_str}")
        html = generate_evening_report(today_str, time_str)
        filename = f'/workspace/现代量学讲义/收盘资金识别-{today_str}.html'
    else:
        print(f"当前时间{time_str}不在报告生成时段（11:00-13:00或15:00后）")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 已生成: {filename}")
    
    # 更新index.html
    update_index_html(filename)

def update_index_html(new_file):
    """更新index.html中的报告链接"""
    index_path = '/workspace/现代量学讲义/index.html'
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取日期
    today_str = new_file.split('-')[-1].replace('.html', '')
    date_short = today_str.split('-')[-1]
    
    # 判断报告类型
    report_type = ''
    if '午间' in new_file:
        report_type = 'noon'
    elif '收盘' in new_file:
        report_type = 'close'
    elif '联网' in new_file:
        report_type = 'evening'
    
    if not report_type:
        return
    
    # 构建新的卡片HTML
    card_map = {
        'noon': f'''<div class="quick-card warning" onclick="openReader('./{os.path.basename(new_file)}','{today_str} 午间资金识别');return false;">
        <div class="qc-icon">📊</div>
        <div class="qc-title">午间资金识别</div>
        <div class="qc-sub">{today_str} 上午资金流向</div>
        <span class="qc-badge">11:30数据</span>
      </div>''',
        'close': f'''<div class="quick-card secondary" onclick="openReader('./{os.path.basename(new_file)}','{today_str} 收盘资金识别+全面复盘');return false;">
        <div class="qc-icon">📝</div>
        <div class="qc-title">收盘资金识别+复盘</div>
        <div class="qc-sub">{today_str} 全天资金流向+次日预案</div>
        <span class="qc-badge">今日</span>
      </div>''',
        'evening': f'''<div class="quick-card info" onclick="openReader('./{os.path.basename(new_file)}','{today_str} 联网复盘');return false;">
        <div class="qc-icon">🌐</div>
        <div class="qc-title">联网复盘</div>
        <div class="qc-sub">{today_str} 政策面+基本面官方信息</div>
        <span class="qc-badge">21:00</span>
      </div>'''
    }
    
    new_card = card_map.get(report_type, '')
    if not new_card:
        return
    
    # 替换快速操作行中的对应卡片
    # 匹配对应的旧卡片并替换
    patterns = {
        'noon': '午间研判',
        'close': '收盘复盘',
        'evening': '联网复盘'
    }
    
    old_keyword = patterns.get(report_type, '')
    
    # 使用更精确的替换
    import re
    if report_type == 'noon':
        # 替换午间研判卡片
        content = re.sub(
            r'<div class="quick-card warning"[^>]*>.*?</div>\s*</div>',
            new_card,
            content,
            count=1,
            flags=re.DOTALL
        )
    elif report_type == 'close':
        # 替换收盘复盘卡片
        content = re.sub(
            r'<div class="quick-card secondary"[^>]*>.*?</div>\s*</div>',
            new_card,
            content,
            count=1,
            flags=re.DOTALL
        )
    elif report_type == 'evening':
        # 在快速操作行末尾添加联网复盘卡片
        content = content.replace(
            '<div class="quick-card purple"',
            new_card + '\n      <div class="quick-card purple"'
        )
    
    # 更新复盘页列表
    if report_type in ['noon', 'close']:
        # 在复盘页添加新报告链接
        review_link = f'<a class="lesson-card" href="#" onclick="openReader(\'./{os.path.basename(new_file)}\', \'{today_str} {report_type}\');return false;">\n        <div class="card-head">\n          <div class="card-icon review">📝</div>\n          <div class="card-meta">\n            <span class="card-tag review">复盘</span>\n            <div class="card-title">{today_str} {report_type}</div>\n            <div class="card-subtitle">全天资金流向 + 次日预案</div>\n          </div>\n        </div>\n        <div class="card-desc">资金行为分析 + 主力意图判断</div>\n        <span class="card-status new">今日</span>\n      </a>'
        
        # 在复盘页第一个位置插入
        content = content.replace(
            '<div class="card-list">\n      <a class="lesson-card" href="#" onclick="openReader(\'./收盘资金识别-',
            '<div class="card-list">\n      ' + review_link + '\n      <a class="lesson-card" href="#" onclick="openReader(\'./收盘资金识别-'
        )
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ 已更新index.html导航")

if __name__ == '__main__':
    main()
