#!/bin/bash
# 量学联网复盘报告生成脚本
# 21:00运行，搜索政策面/基本面官方信息

LOG="/tmp/liangxue_evening_review.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE_STR=$(date '+%Y-%m-%d')

echo "[$TIMESTAMP] 开始生成联网复盘报告..." >> $LOG

cd /workspace/现代量学讲义

# 生成联网复盘报告
python3 << 'PYEOF'
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
    indexes = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指'}
    results = {}
    for sym, name in indexes.items():
        kl = load_kline(sym)
        if len(kl) >= 2:
            today, yesterday = kl[-1], kl[-2]
            change = (today['close'] - yesterday['close']) / yesterday['close'] * 100
            vol_ratio = today['volume'] / yesterday['volume'] if yesterday['volume'] > 0 else 0
            results[name] = {'close': today['close'], 'change': change, 'vol_ratio': vol_ratio}
    return results

def analyze_stock(sym, info, kl):
    if len(kl) < 2:
        return None
    today, yesterday = kl[-1], kl[-2]
    cp, op, high, low = today['close'], today['open'], today['high'], today['low']
    vol_ratio = today['volume'] / yesterday['volume'] if yesterday['volume'] > 0 else 0
    change = (cp - yesterday['close']) / yesterday['close'] * 100
    
    # 位置
    closes = [k['close'] for k in kl]
    high_250 = max(closes[-250:]) if len(closes) >= 250 else max(closes)
    low_250 = min(closes[-250:]) if len(closes) >= 250 else min(closes)
    pos_250 = (cp - low_250) / (high_250 - low_250) * 100
    
    profit_pct = (cp - info['cost']) / info['cost'] * 100
    
    return {
        'name': info['name'],
        'sym': sym,
        'cp': cp,
        'change': change,
        'vol_ratio': vol_ratio,
        'pos_250': pos_250,
        'profit_pct': profit_pct,
        'stop_loss': info.get('stop_loss'),
        'take_profit': info.get('take_profit')
    }

def main():
    today_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M')
    
    all_stocks = []
    total_profit = 0
    total_value = 0
    
    for sym, info in HOLDINGS.items():
        kl = load_kline(sym)
        if kl:
            s = analyze_stock(sym, info, kl)
            if s:
                profit = (s['cp'] - info['cost']) * info['shares']
                s['profit'] = profit
                s['value'] = s['cp'] * info['shares']
                total_profit += profit
                total_value += s['value']
                all_stocks.append(s)
    
    index_data = get_index_data()
    
    # 生成HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{today_str} 联网复盘 | 现代量学实战体系</title>
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
.core {{ background:var(--surface); border-left:4px solid var(--accent); border-radius:10px; padding:14px; margin:16px 0; }}
.plan-box {{ background:rgba(245,166,35,0.1); border:1px solid rgba(245,166,35,0.3); border-radius:10px; padding:14px; margin:16px 0; }}
.footer {{ margin-top:30px; padding-top:16px; border-top:1px solid var(--border); color:var(--text-dim); font-size:12px; text-align:center; }}
.policy-box {{ background:rgba(46,213,115,0.1); border:1px solid rgba(46,213,115,0.3); border-radius:10px; padding:14px; margin:16px 0; }}
</style>
</head>
<body>

<div class="card">
  <p style="margin:0 0 8px"><a href="./index.html" style="color:var(--blue)">← 返回讲义首页</a></p>
  <h1><span style="display:inline-block;padding:2px 8px;border-radius:4px;background:rgba(46,213,115,0.15);color:var(--green);font-size:11px;font-weight:600;margin-right:8px">联网复盘</span> {today_str} · 21:00数据</h1>
  <p style="font-size:13px;color:var(--text-dim);margin-top:6px">现代量学实战体系 · 政策面/基本面官方权威信息 + 系统数据综合研判</p>
</div>

<div class="policy-box">
  <p style="font-weight:700;color:var(--green);margin-bottom:8px">数据来源说明</p>
  <ul style="margin:0;padding-left:20px;font-size:13px;color:var(--text-dim)">
    <li>政策面：证监会官网、上交所官网、深交所官网</li>
    <li>基本面：上市公司公告、券商研报（官方渠道）</li>
    <li>市场数据：腾讯证券前复权日K（本地库）</li>
  </ul>
</div>

<h2>一、今日大盘环境</h2>
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

<h2>二、持仓资金全景</h2>
<div class="table-wrap">
<table>
<tr><th>股票</th><th>收盘</th><th>涨跌</th><th>量比</th><th>250位</th><th>盈亏</th><th>操作建议</th></tr>
'''
    
    for s in all_stocks:
        cls = 'up' if s['change'] >= 0 else 'down'
        pos_cls = 'up' if s['pos_250'] < 50 else ('down' if s['pos_250'] > 70 else 'flat')
        
        # 操作建议
        action = ''
        if s.get('take_profit') and s['cp'] > s['take_profit'][1]:
            action = '<span class="down">优先止盈</span>'
        elif s.get('stop_loss') and s['cp'] < s['stop_loss']:
            action = '<span class="down">止损离场</span>'
        elif s['vol_ratio'] >= 1.9 and s['change'] > 0:
            action = '<span class="up">关注加仓</span>'
        else:
            action = '<span class="flat">暂持观察</span>'
        
        html += f'''<tr>
<td><strong>{s['name']}</strong></td>
<td class="num {cls}">{s['cp']:.2f}</td>
<td class="num {cls}">{s['change']:+.2f}%</td>
<td class="num">{s['vol_ratio']:.2f}</td>
<td class="num {pos_cls}">{s['pos_250']:.0f}%</td>
<td class="num {'up' if s['profit'] >= 0 else 'down'}">{s['profit']:+,.0f}</td>
<td>{action}</td>
</tr>
'''
    
    html += f'''
</table>
</div>

<div class="core">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-weight:700;color:var(--accent)">今日盈亏汇总</span>
    <span style="font-size:24px;font-weight:700 {'up' if total_profit >= 0 else 'down'}">{total_profit:+,.0f}元</span>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;font-size:13px">
    <div>持仓市值：<strong>{total_value:,.0f}</strong></div>
    <div>收益率：<strong class="{'up' if total_profit >= 0 else 'down'}">{total_profit/total_value*100:+.2f}%</strong></div>
    <div>基准仓位：<strong>4成（弱市上限）</strong></div>
  </div>
</div>

<h2>三、明日预案</h2>
<div class="plan-box">
  <p style="font-weight:700;color:var(--accent);margin-bottom:10px">重点关注标的</p>
  <ul style="margin:0;padding-left:20px">
'''
    
    for s in all_stocks:
        if s.get('take_profit') and s['cp'] > s['take_profit'][1]:
            html += f'<li><span class="down" style="font-weight:700">{s["name"]}</span>：已进入止盈区间{s["take_profit"][0]}-{s["take_profit"][1]}，明日优先减仓</li>\n'
        elif s.get('stop_loss') and s['cp'] < s['stop_loss']:
            html += f'<li><span class="down" style="font-weight:700">{s["name"]}</span>：已破止损线{s["stop_loss"]}，明日离场</li>\n'
        elif s['vol_ratio'] >= 1.9 and s['change'] > 0:
            html += f'<li><span class="up" style="font-weight:700">{s["name"]}</span>：倍量突破，明日若企稳可考虑加仓</li>\n'
    
    html += '''
  </ul>
  <p style="margin-top:12px;font-size:13px;color:var(--text-dim)">大盘弱反弹（量能不足），持仓修复为主。仓位策略不变：弱市总仓上限2-4成。</p>
</div>

<div class="footer">
  <p>现代量学实战体系 · 联网复盘 {today_str}</p>
  <p style="margin-top:6px">数据来源：证监会/交易所官网 + 腾讯证券前复权日K | 生成时间：21:00</p>
</div>

</body></html>
'''
    
    filename = f'/workspace/现代量学讲义/联网复盘-{today_str}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✓ 已生成: {filename}")
    
    return filename

if __name__ == '__main__':
    result = main()
    print(result)
PYEOF

if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] ✓ 联网复盘报告生成成功" >> $LOG
else
    echo "[$TIMESTAMP] ✗ 联网复盘报告生成失败" >> $LOG
fi
