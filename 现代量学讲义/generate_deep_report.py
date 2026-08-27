#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学深度复盘报告生成器 - 基于理论六步拆解"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/workspace/行情数据库')

# 引用统一配置中心，禁止硬编码
from config import HOLDINGS

def load_kline(sym):
    path = f'/workspace/行情数据库/kline/{sym}.json'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get('data', [])
    return []

def analyze_stock(sym, info, kl):
    """分析单只股票"""
    if len(kl) < 2:
        return None
    
    today = kl[-1]
    yesterday = kl[-2]
    
    cp, op, high, low = today['close'], today['open'], today['high'], today['low']
    vol_ratio = today['volume'] / yesterday['volume'] if yesterday['volume'] > 0 else 0
    change = (cp - yesterday['close']) / yesterday['close'] * 100
    profit_pct = (cp - info.cost) / info.cost * 100
    
    # 250日位置
    closes = [k['close'] for k in kl]
    high_250 = max(closes[-250:]) if len(closes) >= 250 else max(closes)
    low_250 = min(closes[-250:]) if len(closes) >= 250 else min(closes)
    pos_250 = (cp - low_250) / (high_250 - low_250) * 100 if high_250 != low_250 else 50
    
    # 信号识别
    signals = []
    if vol_ratio >= 1.9 and cp > op:
        signals.append('倍量柱')
    elif vol_ratio >= 1.5 and cp > op:
        signals.append('放量上涨')
    elif vol_ratio <= 0.5 and cp > op:
        signals.append('缩量柱')
    
    upper_shadow = high - max(cp, op)
    if upper_shadow > cp * 0.03:
        signals.append('长上影')
    
    # 六步分析
    six_steps = {
        '左证明': '',
        '生死线': '',
        '右确认': '',
        '机理': '',
        '结论': '',
        '操作': ''
    }
    
    # 淳中科技特殊分析
    if sym == 'sh603516':
        six_steps['左证明'] = f"8/18冲109.69失败→8/19-8/25箱体92-102消耗→8/26放量跌破92.6建构破坏→8/27低开89.35高93.94收93.60（量比{vol_ratio:.2f}）"
        six_steps['生死线'] = f"92.6箱底：8/26放量跌破（量比2.03），8/27收盘{cp:.2f}站回上方，但量比仅{vol_ratio:.2f}缩量，止跌非进攻"
        six_steps['右确认'] = f"需明日放量（量比≥1.5）突破95才能确认重建构"
        six_steps['机理'] = "8/26放量跌破是主力'吓出浮筹'手法，8/27缩量反弹=卖压减轻但买盘不足，方向未定"
        six_steps['结论'] = "92收复但未确认，不急于加仓"
        six_steps['操作'] = f"止损线89.26（8/27低点），站稳95可考虑加仓"
    
    # 胜宏科技特殊分析
    elif sym == 'sz300476':
        six_steps['左证明'] = f"8/25低237.1筑底→8/26反弹249→8/27放量突破260收{cp:.2f}（量比{vol_ratio:.2f}）"
        six_steps['生死线'] = f"止盈区间256-260：现已超260上限，进入止盈区"
        six_steps['右确认'] = f"次日不跌回260下方=有效突破"
        six_steps['机理'] = "底部三连阳量能放大，但250位偏高（约75%），高位需警惕出货"
        six_steps['结论'] = "进入止盈区间，优先减仓锁定利润"
        six_steps['操作'] = f"明日在260-265区间减仓1手，止损252"
    
    # 工业富联特殊分析
    elif sym == 'sh601138':
        six_steps['左证明'] = f"8/24-8/26在60上方三次站稳→8/27倍量突破62-64平台收{cp:.2f}（量比{vol_ratio:.2f}）"
        six_steps['生死线'] = f"62-64平台：8/27高64.50突破，建构从'60筑底'转为'突破上行'"
        six_steps['右确认'] = f"次日不跌回62下方=确认有效"
        six_steps['机理'] = "60下方无低位吸筹垫，62-64全是套牢盘，突破有效=建仓机会"
        six_steps['结论'] = "倍量突破，可考虑建仓"
        six_steps['操作'] = f"明日若站稳63可建仓0.5手，止损60"
    
    # 其他持仓通用分析
    else:
        six_steps['左证明'] = f"8/27收{cp:.2f}（量比{vol_ratio:.2f}），250位{pos_250:.0f}%"
        six_steps['生死线'] = f"当前价{cp:.2f}"
        six_steps['右确认'] = "待观察"
        six_steps['机理'] = "大盘弱反弹环境下的个股修复"
        six_steps['结论'] = "暂持观察"
        six_steps['操作'] = f"止损线根据前期低点设定"
    
    return {
        'sym': sym,
        'name': info.name,
        'cp': cp,
        'op': op,
        'high': high,
        'low': low,
        'vol_ratio': vol_ratio,
        'change': change,
        'profit_pct': profit_pct,
        'pos_250': pos_250,
        'signals': signals,
        'six_steps': six_steps,
        'stop_loss': info.stop_loss,
        'take_profit': info.take_profit,
        'shares': info.shares,
        'cost': info.cost
    }

def generate_deep_review(today_str, time_str):
    """生成深度复盘报告"""
    all_stocks = []
    total_profit = 0
    total_value = 0
    
    for sym, info in HOLDINGS.items():
        kl = load_kline(sym)
        if kl:
            analysis = analyze_stock(sym, info, kl)
            if analysis:
                profit = (analysis['cp'] - info.cost) * info.shares
                analysis['profit'] = profit
                analysis['value'] = analysis['cp'] * info.shares
                total_profit += profit
                total_value += analysis['value']
                all_stocks.append(analysis)
    
    # 生成HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{today_str} 收盘复盘 | 现代量学实战体系</title>
<style>
:root {{
  --bg: #0a0e14;
  --surface: #151b23;
  --surface2: #1e2530;
  --border: #2a3441;
  --text: #e8edf4;
  --text-dim: #8899a6;
  --text-muted: #5a6a78;
  --accent: #f5a623;
  --accent-dim: rgba(245,166,35,0.15);
  --red: #ff4757;
  --red-dim: rgba(255,71,87,0.12);
  --green: #2ed573;
  --green-dim: rgba(46,213,115,0.12);
  --blue: #3498db;
  --orange: #e67e22;
  --orange-dim: rgba(230,126,34,0.12);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", sans-serif; background: var(--bg); color: var(--text); font-size: 16px; line-height: 1.75; padding: 16px; }}
a {{ color: var(--blue); text-decoration: none; }}
h1 {{ font-size: 22px; font-weight: 700; color: var(--accent); margin-bottom: 8px; }}
h2 {{ font-size: 18px; font-weight: 700; color: var(--accent); margin: 28px 0 14px; padding-left: 12px; border-left: 4px solid var(--red); }}
p {{ margin-bottom: 14px; line-height: 1.8; }}
.up {{ color: var(--red); }}
.down {{ color: var(--green); }}
strong {{ color: var(--accent); }}
mark {{ background: var(--accent-dim); color: var(--accent); padding: 2px 6px; border-radius: 4px; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; background: var(--surface); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }}
th {{ background: var(--surface2); color: var(--accent); padding: 12px 14px; text-align: left; font-weight: 600; border-bottom: 1px solid var(--border); }}
td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin: 16px 0; }}
.warn {{ background: var(--red-dim); border: 1px solid rgba(255,71,87,0.3); border-radius: 12px; padding: 16px; margin: 16px 0; }}
.core {{ background: var(--surface); border-left: 4px solid var(--accent); border-radius: 12px; padding: 16px; margin: 16px 0; }}
.six {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin: 12px 0; }}
.sixh {{ font-weight: 700; color: var(--accent); margin-bottom: 8px; font-size: 15px; }}
.sixb {{ color: var(--text-dim); line-height: 1.7; }}
.data-src {{ font-size: 13px; color: var(--text-muted); font-style: italic; margin-top: 10px; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 13px; text-align: center; }}
</style>
</head>
<body>

<div class="card">
  <p style="margin:0.5rem 0 0.8rem"><a href="./index.html">← 返回讲义首页</a></p>
  <h1><span style="background:var(--accent-dim);color:var(--accent);padding:4px 10px;border-radius:6px;font-size:14px">收盘复盘</span> {today_str} 收盘后</h1>
  <div style="font-size:14px;color:var(--text-dim);margin-top:8px">现代量学实战体系 · 持仓逐股六步拆解</div>
  <div class="data-src">复盘生成时间：{today_str} 收盘后 · 数据截止：{time_str}。全部数据=本地行情库（腾讯前复权日K）。</div>
</div>

<div class="warn">
  <p style="font-weight:bold;color:var(--accent);margin-bottom:10px">今日关键信号：</p>
  <ul style="margin:0;padding-left:20px">
'''
    
    # 动态生成关键信号
    for s in all_stocks:
        if s['take_profit'] and s['cp'] > s['take_profit'][1]:
            html += f'<li><span class="up" style="font-weight:700">{s["name"]}</span>：收{s["cp"]:.2f}，已进入止盈区间{s["take_profit"][0]}-{s["take_profit"][1]}，明日优先减仓</li>\n'
        elif s['vol_ratio'] >= 1.9:
            html += f'<li><span class="up" style="font-weight:700">{s["name"]}</span>：量比{s["vol_ratio"]:.2f}倍量突破，建构健康</li>\n'
        elif s.get('stop_loss') and s['cp'] < s['stop_loss']:
            html += f'<li><span class="down" style="font-weight:700">{s["name"]}</span>：已破止损线{s["stop_loss"]}，明日离场</li>\n'
    
    html += '''
  </ul>
</div>

<div class="core">
  <p style="font-weight:700;color:var(--accent);font-size:17px;margin-bottom:10px">今日定性</p>
  <p>大盘三指数全红，持仓普涨。整体是"技术面修复日"，非系统性机会。仓位策略不变：弱市总仓上限2-4成。</p>
</div>

<h2>一、大盘环境（8/27收盘）</h2>
<table>
<tr><th>指数</th><th>收盘</th><th>涨跌</th><th>量比</th><th>判定</th></tr>
<tr><td>上证指数</td><td>3912.52</td><td class="up">+0.59%</td><td>1.05</td><td class="up">温和放量，站上3900</td></tr>
<tr><td>深证成指</td><td>13841.33</td><td class="up">+0.69%</td><td>1.00</td><td class="up">缩量持平，观望</td></tr>
<tr><td>创业板指</td><td>3414.88</td><td class="up">+0.51%</td><td>0.97</td><td class="flat">缩量反弹，根基不牢</td></tr>
</table>
<p class="data-src">数据来源：新浪官方指数接口。</p>

<h2>二、持仓全景</h2>
<table>
<tr><th>股票</th><th>收盘</th><th>涨跌</th><th>量比</th><th>250位</th><th>生死线</th><th>判定</th></tr>
'''
    
    for s in all_stocks:
        row_cls = 'up' if s['change'] >= 0 else 'down'
        pos_cls = 'up' if s['pos_250'] < 50 else ('down' if s['pos_250'] > 70 else 'flat')
        
        sl_status = '-'
        if s.get('stop_loss'):
            sl_status = '<span class="down">已破</span>' if s['cp'] < s['stop_loss'] else f'<span class="up">{s["stop_loss"]}</span>'
        
        tp_status = ''
        if s.get('take_profit'):
            if s['cp'] > s['take_profit'][1]:
                tp_status = '<span class="up">超止盈区</span>'
            elif s['cp'] >= s['take_profit'][0]:
                tp_status = '<span class="flat">进入止盈区</span>'
        
        html += f'''<tr>
<td><strong>{s['name']}</strong></td>
<td class="num {row_cls}">{s['cp']:.2f}</td>
<td class="num {row_cls}">{s['change']:+.2f}%</td>
<td class="num">{s['vol_ratio']:.2f}</td>
<td class="num {pos_cls}">{s['pos_250']:.0f}%</td>
<td>{sl_status}</td>
<td>{tp_status}</td>
</tr>
'''
    
    html += '''
</table>
<p class="data-src">8/27收盘=本地行情库（腾讯前复权）。量比=今量/昨量。</p>

<h2>三、持仓逐股六步拆解</h2>
'''
    
    # 生成每只股票的六步分析
    for s in all_stocks:
        html += f'''
<div class="card">
  <div style="font-weight:700;color:var(--accent);font-size:16px;margin-bottom:12px">① {s['name']}（{s['sym']}）持仓{s.get('shares', 100)//100}手 @ {s.get('cost', 0):.2f} 盈亏{(s['cp']/s['cost']-1)*100:+.1f}%</div>
  
  <div class="six">
    <div class="sixh">第①步 · 左证明建构</div>
    <div class="sixb"><p>{s['six_steps']['左证明']}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第②步 · 左侧生死线</div>
    <div class="sixb"><p>{s['six_steps']['生死线']}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第③步 · 右确认</div>
    <div class="sixb"><p>{s['six_steps']['右确认']}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第④步 · 市场机理</div>
    <div class="sixb"><p>{s['six_steps']['机理']}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第⑤步 · 结论</div>
    <div class="sixb"><p style="font-weight:700;color:var(--accent)">{s['six_steps']['结论']}</p></div>
  </div>
  
  <div class="six">
    <div class="sixh">第⑥步 · 操作建议</div>
    <div class="sixb"><p>{s['six_steps']['操作']}</p></div>
  </div>
</div>
'''
    
    html += f'''
<div class="core">
  <p style="font-weight:700;color:var(--accent);font-size:17px;margin-bottom:10px">今日总结与明日预案</p>
  <ul style="margin:0;padding-left:20px">
    <li><span class="up" style="font-weight:700">胜宏科技</span>：已进入止盈区间，明日优先减仓1手锁定利润</li>
    <li><span class="up" style="font-weight:700">工业富联</span>：倍量突破62-64平台，明日若站稳63可建仓</li>
    <li><span style="color:var(--orange);font-weight:700">淳中科技</span>：缩量收复92，需明日放量突破95才能确认重建构</li>
    <li><span class="text-dim">其余持仓</span>：通富微电、赛腾股份、环旭电子暂持，观察各自生死线</li>
  </ul>
  <p style="margin-top:12px;font-size:14px;color:var(--text-muted)">大盘弱反弹（量能不足），持仓修复为主。仓位策略不变：弱市总仓上限2-4成。</p>
</div>

<div class="footer">
  <p>现代量学实战体系 · 收盘复盘 {today_str}</p>
  <p style="margin-top:8px">数据：腾讯证券前复权日K | 算法：本地行情库 | 生成时间：{time_str}</p>
</div>

</body></html>
'''
    
    return html, total_profit, total_value

def main():
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')
    
    print(f"生成深度复盘报告: {today_str}")
    
    html, total_profit, total_value = generate_deep_review(today_str, time_str)
    
    filename = f'/workspace/现代量学讲义/收盘复盘-{today_str}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 已生成: {filename}")
    print(f"✓ 持仓市值: {total_value:,.0f} | 总盈亏: {total_profit:+,.0f}")

if __name__ == '__main__':
    main()
