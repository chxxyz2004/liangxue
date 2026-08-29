#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学报告自动生成器 - 根据时间段生成对应类型报告"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/现代量学讲义')

# 引用统一配置中心，禁止硬编码
from config import HOLDINGS

LATEST_FILES = {
    '预案': None,
    '盯盘': None,
    '午盘': None,
    '复盘': None
}

# ========== 资金流向数据加载 ==========

def load_lhb_data():
    """加载龙虎榜数据，返回代码->记录的映射"""
    lhb_dir = '/workspace/行情数据库/lhb'
    if not os.path.exists(lhb_dir):
        return {}, {}
    latest_file = sorted([f for f in os.listdir(lhb_dir) if f.endswith('.json')], reverse=True)[0]
    with open(os.path.join(lhb_dir, latest_file)) as f:
        d = json.load(f)
    records = d.get('data', [])
    code_map = {}  # 纯代码 -> 记录列表
    name_map = {}  # 名称 -> 记录列表
    for r in records:
        code = str(r.get('代码', ''))
        name = r.get('名称', '')
        if code not in code_map:
            code_map[code] = []
        code_map[code].append(r)
        if name and name not in name_map:
            name_map[name] = []
        if name:
            name_map[name].append(r)
    return code_map, name_map


def load_spoofing_results():
    """加载最近一次量化对倒检测结果"""
    pattern = '/tmp/liangxue_spoofing_result_*.txt'
    files = sorted([f for f in os.listdir('/tmp') if f.startswith('liangxue_spoofing_result_') and f.endswith('.txt')], reverse=True)
    if not files:
        return {}
    result = {}
    with open(f'/tmp/{files[0]}') as f:
        content = f.read()
    current_stock = None
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('淳中科技') or line.startswith('工业富联') or line.startswith('赛腾股份') or line.startswith('通富微电') or line.startswith('环旭电子') or line.startswith('胜宏科技') or line.startswith('天孚通信'):
            parts = line.rsplit(':', 1)
            if len(parts) == 2:
                current_stock = parts[0].strip()
                result[current_stock] = []
        elif line.startswith('总计:') or line.startswith('='*10) or line.startswith('量化对倒'):
            current_stock = None
        elif current_stock and line and not line.startswith('量化对倒'):
            result.get(current_stock, []).append(line)
    return result


def cross_validate_lhb_intent(hv_intent, lhb_records):
    """高量柱意图与龙虎榜交叉验证，返回额外置信度调整和对冲信号"""
    if not lhb_records:
        return 0, []
    recent = [r for r in lhb_records if r.get('上榜日') >= (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')]
    if not recent:
        return 0, []
    signals = []
    adjustment = 0
    for r in recent[-3:]:
        net = r.get('龙虎榜净买额', 0)
        try:
            net = float(net) if net not in (None, 'nan') else 0
        except (ValueError, TypeError):
            net = 0
        interpretation = r.get('解读', '')
        if '机构卖出' in interpretation or net < -1000000:
            if hv_intent in ('吸筹', '拉升'):
                adjustment -= 0.15
                signals.append(f"LHB机构卖出({net/10000:.0f}万)，与意图{hv_intent}冲突")
            elif hv_intent == '观望':
                adjustment -= 0.05
                signals.append("LHB机构卖出，观望信号强化")
        elif '机构买入' in interpretation or net > 1000000:
            if hv_intent in ('吸筹', '拉升'):
                adjustment += 0.10
                signals.append(f"LHB机构买入({net/10000:.0f}万)，与意图{hv_intent}共振")
            elif hv_intent == '观望':
                adjustment += 0.05
                signals.append("LHB机构买入，观望可能转为积极")
    return adjustment, signals

def find_latest_file(prefix):
    """查找该类型最新文件"""
    files = []
    for f in os.listdir('/workspace/现代量学讲义'):
        if f.startswith(prefix) and f.endswith('.html'):
            files.append(f)
    if files:
        files.sort(reverse=True)
        return files[0]
    return None

def load_kline(sym):
    path = f'/workspace/行情数据库/kline/{sym}.json'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def get_time_type():
    """根据当前时间判断报告类型"""
    now = datetime.now()
    h, m = now.hour, now.minute
    
    # 盘前（9:25之前）
    if h < 9 or (h == 9 and m < 25):
        return '盘前预案'
    # 集合竞价（9:25-9:30）
    elif (h == 9 and 25 <= m < 30):
        return '集合竞价+盘前预案'
    # 盘中盯盘（9:30-11:30, 13:00-15:00）
    elif ((h == 9 and m >= 30) or (10 <= h <= 11)) or ((h == 13) or (h == 14 and m <= 59)):
        return '盯盘清单'
    # 午盘研判（11:30-13:00）
    elif (h == 11 and m >= 30) or h == 12:
        return '午盘研判'
    # 收盘复盘（15:00之后）
    elif h >= 15:
        return '收盘复盘'
    else:
        return '其他时间'

def get_current_price(sym, data):
    """获取最新价格"""
    if not data or 'data' not in data:
        return None
    kl = data['data']
    if len(kl) < 2:
        return None
    today = kl[-1]
    yesterday = kl[-2]
    return {
        'price': today['close'],
        'change': (today['close'] - yesterday['close']) / yesterday['close'] * 100,
        'vol': today['volume'],
        'vol_ratio': today['volume'] / yesterday['volume'] if yesterday['volume'] > 0 else 0,
        'high': today['high'],
        'low': today['low'],
        'date': today['day']
    }

def generate_report_content(report_type, timestamp):
    """生成报告内容"""
    stocks = []
    total_profit = 0
    total_value = 0
    total_cost = 0
    alerts = []

    # 预加载资金流向数据
    lhb_code_map, lhb_name_map = load_lhb_data()
    spoofing_results = load_spoofing_results()
    # 名称到名称的映射
    name_to_sym = {info.name: sym for sym, info in HOLDINGS.items()}

    for sym, info in HOLDINGS.items():
        data = load_kline(sym)
        price_data = get_current_price(sym, data)
        if not price_data:
            continue
        
        profit = (price_data['price'] - info.cost) * info.shares
        value = price_data['price'] * info.shares

        total_profit += profit
        total_value += value
        total_cost += info.cost * info.shares

        signals = []
        if price_data['vol_ratio'] >= 1.9 and price_data['price'] > data['data'][-1]['open']:
            signals.append('倍量柱')
        if price_data['vol_ratio'] <= 0.5 and price_data['price'] > data['data'][-1]['open']:
            signals.append('缩量柱')

        # 止损检查
        if info.stop_loss and price_data['price'] < info.stop_loss:
            alerts.append(f"🔴 {info.name} 破止损线 {info.stop_loss}")
        elif info.stop_loss:
            dist = (price_data['price'] - info.stop_loss) / price_data['price'] * 100
            alerts.append(f"🟢 {info.name} 止损线 {info.stop_loss} (距现价{dist:.1f}%)")

        # 止盈检查
        if info.take_profit:
            tp_low, tp_high = info.take_profit
            if price_data['price'] >= tp_low:
                alerts.append(f"🔴 {info.name} 进入止盈区间 {tp_low}-{tp_high}")

        # 量学战法信号
        liangxue_info = {}
        try:
            from liangxue_engine import liangxue_engine
            lx = liangxue_engine.full_analysis(sym)
            kb = lx.get('key_bars', {})
            vb = lx.get('volume_bars', {}).get('summary', {})
            ql = lx.get('quantity_lines', {})
            pl = lx.get('precision_lines', {})
            latest_close = price_data['price']

            # 量柱
            dbls = vb.get('doubling_bars', [])
            shrinks = vb.get('shrinking_bars', [])
            if dbls:
                liangxue_info['doubling'] = f"{dbls[-1]['date']}({dbls[-1]['ratio']:.2f}x)"
            if shrinks:
                liangxue_info['shrinking'] = shrinks[-1]['date']

            # 关键柱
            golden = kb.get('golden_bars', [])
            marshal = kb.get('marshal_bars', [])
            general = kb.get('general_bars', [])
            if golden:
                liangxue_info['golden'] = f"黄金柱{golden[-1]['date']}(回调{golden[-1]['drawdown_ratio']:.0%})"
            elif marshal:
                liangxue_info['marshal'] = f"元帅柱{marshal[-1]['date']}(回调{marshal[-1]['drawdown_ratio']:.0%})"
            elif general:
                liangxue_info['general'] = f"将军柱{general[-1]['date']}(回调{general[-1]['drawdown_ratio']:.0%})"

            # 高量柱意图分析
            hva = lx.get('high_vol_analysis', {})
            hv_bars = hva.get('bars', [])
            if hv_bars:
                latest_hv = hv_bars[-1]
                intent = latest_hv.get('intent', {})
                rc = latest_hv.get('right_confirm', {})
                intent_label = intent.get('intent', '')
                rc_dir = rc.get('direction', '')
                rc_arrow = {'strong_up': '↑↑', 'up': '↑', 'down': '↓', 'strong_down': '↓↓'}.get(rc_dir, '')
                pos = intent.get('price_position', 0.5)
                pos_label = '低' if pos < 0.3 else ('中' if pos < 0.7 else '高')
                liangxue_info['high_vol'] = f"{latest_hv['date']}({intent_label},{pos_label}位{rc_arrow})"

            # 量线位置
            peak_lines = ql.get('peak_lines', [])
            valley_lines = ql.get('valley_lines', [])
            nearest_valley = min(valley_lines, key=lambda x: abs(x['price'] - latest_close), default=None) if valley_lines else None
            nearest_peak = min(peak_lines, key=lambda x: abs(x['price'] - latest_close), default=None) if peak_lines else None
            if nearest_valley:
                liangxue_info['support'] = f"{nearest_valley['price']:.2f}({nearest_valley['count']}点)"
            if nearest_peak:
                liangxue_info['resistance'] = f"{nearest_peak['price']:.2f}({nearest_peak['count']}点)"

            # 精准线
            precise_valleys = pl.get('precise_valley_lines', []) if isinstance(pl, dict) else []
            precise_peaks = pl.get('precise_peak_lines', []) if isinstance(pl, dict) else []
            if precise_valleys:
                best_v = max(precise_valleys, key=lambda x: x['precision_score'])
                liangxue_info['precise_support'] = f"{best_v['line_price']:.2f}({best_v['precision_score']:.0%})"
            if precise_peaks:
                best_p = max(precise_peaks, key=lambda x: x['precision_score'])
                liangxue_info['precise_resistance'] = f"{best_p['line_price']:.2f}({best_p['precision_score']:.0%})"
        except Exception:
            pass

        # ========== 资金流向数据 ==========
        # 1. 龙虎榜
        code_clean = sym.replace('sh','').replace('sz','')
        lhb_records = lhb_code_map.get(code_clean, [])
        lhb_info = None
        if lhb_records:
            # 取最近一次上榜
            lhb_info = lhb_records[0]
            net_val = lhb_info.get('龙虎榜净买额', 0)
            try:
                net_val = float(net_val) if net_val not in (None, 'nan') else 0
            except (ValueError, TypeError):
                net_val = 0
            liangxue_info['lhb'] = {
                'date': lhb_info.get('上榜日',''),
                'interpretation': lhb_info.get('解读',''),
                'net_buy': round(net_val/10000, 1),
                'turnover': lhb_info.get('换手率'),
                'reason': lhb_info.get('上榜原因',''),
                'return_1d': lhb_info.get('上榜后1日'),
                'return_2d': lhb_info.get('上榜后2日'),
            }

        # 2. 量化对倒检测
        spoofing_count = 0
        spoofing_summary = []
        for sname, ssignals in spoofing_results.items():
            if info.name in sname or sname in info.name:
                spoofing_count = len(ssignals)
                spoofing_summary = ssignals[:3]  # 最多显示3条
                break

        # 3. 交叉验证
        cross_alerts = []
        hv_intent = liangxue_info.get('high_vol', '')
        intent_label = ''
        if '(' in hv_intent:
            intent_label = hv_intent.split('(')[1].split(',')[0]
        if intent_label:
            adj, cv_signals = cross_validate_lhb_intent(intent_label, lhb_records)
            if adj != 0:
                liangxue_info['lhb_intent_adj'] = round(adj, 2)
                cross_alerts.extend(cv_signals)
            # 对倒信号与高量柱意图交叉验证
            if spoofing_count > 5 and intent_label in ('吸筹', '拉升'):
                cross_alerts.append(f"对倒异常({spoofing_count}信号)，与意图{intent_label}需警惕")
            elif spoofing_count <= 2 and intent_label in ('吸筹', '拉升'):
                cross_alerts.append(f"对倒干净({spoofing_count}信号)，意图{intent_label}可信度提升")

        # 4. 北向资金（当前NaN，标记状态）
        liangxue_info['north_status'] = '接口NaN'

        stocks.append({
            'name': info.name,
            'sym': sym,
            'price': price_data['price'],
            'change': price_data['change'],
            'cost': info.cost,
            'profit_pct': (price_data['price'] - info.cost) / info.cost * 100,
            'profit': profit,
            'signals': signals,
            'shares': info.shares,
            'liangxue': liangxue_info,
            'lhb': lhb_info,
            'spoofing_count': spoofing_count,
            'spoofing_summary': spoofing_summary,
            'cross_alerts': cross_alerts,
        })
    
    return {
        'type': report_type,
        'timestamp': timestamp,
        'stocks': stocks,
        'total_profit': total_profit,
        'total_value': total_value,
        'total_cost': total_cost,
        'alerts': alerts
    }

def save_report(content, today_str):
    """保存报告文件"""
    report_type = content['type'].replace(' ', '-')
    
    if '复盘' in report_type:
        filename = f'收盘复盘-{today_str}.html'
    elif '盘前' in report_type or '集合竞价' in report_type:
        filename = f'盘前预案-{today_str}.html'
    elif '盯盘' in report_type:
        filename = f'盘中盯盘-{today_str}.html'
    elif '午盘' in report_type or '午间' in report_type:
        filename = f'午间研判-{today_str}.html'
    else:
        filename = f'{report_type}-{today_str}.html'
    
    filepath = f'/workspace/现代量学讲义/{filename}'
    
    # 生成HTML内容（简化版，实际可调用现有模板）
    html = generate_html(content, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return filename

def generate_html(content, filename):
    """生成HTML报告"""
    today = content['timestamp'].split()[0]
    time_str = content['timestamp'].split()[1] if ' ' in content['timestamp'] else ''

    # 表格行
    rows = ''
    for s in content['stocks']:
        pct_cls = 'up' if s['change'] >= 0 else 'down'
        profit_cls = 'up' if s['profit'] >= 0 else 'down'
        signals_html = ' '.join([f'<span class="signal-tag">{sg}</span>' for sg in s['signals']]) or '-'
        lx = s.get('liangxue', {})
        lx_tags = ''
        if lx.get('doubling'):
            lx_tags += f'<span class="lx-tag" title="倍量柱">倍{lx["doubling"]}</span>'
        if lx.get('golden'):
            lx_tags += f'<span class="lx-tag gx" title="黄金柱">{lx["golden"]}</span>'
        elif lx.get('marshal'):
            lx_tags += f'<span class="lx-tag yz" title="元帅柱">{lx["marshal"]}</span>'
        elif lx.get('general'):
            lx_tags += f'<span class="lx-tag jj" title="将军柱">{lx["general"]}</span>'
        if lx.get('precise_support'):
            lx_tags += f'<span class="lx-tag sup" title="精准支撑">{lx["precise_support"]}</span>'
        if lx.get('precise_resistance'):
            lx_tags += f'<span class="lx-tag res" title="精准压力">{lx["precise_resistance"]}</span>'
        if lx.get('high_vol'):
            intent = lx['high_vol'].split('(')[1].split(',')[0] if '(' in lx['high_vol'] else ''
            intent_cls = {'吸筹': 'gx', '拉升': 'gx', '出货': 'jj', '砸盘': 'jj', '洗盘': 'yz', '观望': ''}.get(intent, '')
            lx_tags += f'<span class="lx-tag {intent_cls}" title="高量柱意图">{lx["high_vol"]}</span>'
        if not lx_tags:
            lx_tags = '-'

        # 龙虎榜标签
        lhb_tag = ''
        lhb = s.get('lhb')
        if lhb:
            net = lhb.get('net_buy', 0)
            if net > 0:
                lhb_tag = f'<span class="lx-tag gx" title="机构净买{net:.0f}万">LHB+{net:.0f}万</span>'
            elif net < 0:
                lhb_tag = f'<span class="lx-tag jj" title="机构净卖{abs(net):.0f}万">LHB-{abs(net):.0f}万</span>'
            else:
                lhb_tag = f'<span class="lx-tag yz" title="龙虎榜上榜">LHB上榜</span>'
            if lhb.get('date'):
                lhb_tag += f'<span class="lx-tag yz" title="上榜日">{lhb["date"]}</span>'

        # 对倒检测标签
        spoof_tag = ''
        sc = s.get('spoofing_count', 0)
        if sc > 0:
            spoof_cls = 'jj' if sc > 10 else ('yz' if sc > 5 else 'gx')
            spoof_tag = f'<span class="lx-tag {spoof_cls}" title="对倒异常信号">{sc}个对倒</span>'

        # 交叉验证警报
        cross_tags = ''
        for ca in s.get('cross_alerts', []):
            if '冲突' in ca or '警惕' in ca:
                cross_tags += f'<span class="lx-tag jj" title="交叉验证警告">{ca[:20]}</span>'
            else:
                cross_tags += f'<span class="lx-tag gx" title="交叉验证确认">{ca[:20]}</span>'

        rows += f'''<tr>
<td><strong>{s['name']}</strong><br><span style="color:var(--text-dim);font-size:11px">{s['sym']}</span></td>
<td class="num {pct_cls}">{s['price']:.2f}</td>
<td class="num {pct_cls}">{s['change']:+.2f}%</td>
<td class="num">{s['cost']:.2f}</td>
<td class="num {profit_cls}">{s['profit_pct']:+.2f}%</td>
<td>{signals_html}</td>
<td style="font-size:11px;line-height:1.6">{lx_tags}{lhb_tag}{spoof_tag}{cross_tags}</td>
</tr>'''

    # 警报
    alerts_html = ''
    for a in content['alerts']:
        alerts_html += f'<div class="alert">{a}</div>'
    if not alerts_html:
        alerts_html = '<p style="color:var(--text-dim)">无警报</p>'

    # 资金流向分析摘要
    fund_flow_lines = []
    lhb_stocks = [s for s in content['stocks'] if s.get('lhb')]
    spoof_stocks = [s for s in content['stocks'] if s.get('spoofing_count', 0) > 0]
    cross_stocks = [s for s in content['stocks'] if s.get('cross_alerts')]

    if lhb_stocks:
        for s in lhb_stocks:
            lhb = s['lhb']
            net = lhb.get('net_buy', 0)
            net_str = f'+{net:.0f}万' if net >= 0 else f'{net:.0f}万'
            fund_flow_lines.append(f'<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:12px"><strong>{s["name"]}</strong> LHB {lhb.get("date","")} · 解读:{lhb.get("interpretation","")} · 净买{net_str} · 上榜后1日:{lhb.get("return_1d","?")}%</div>')
    else:
        fund_flow_lines.append('<div style="color:var(--text-dim);font-size:12px;padding:6px 0">近30日持仓股无龙虎榜上榜记录</div>')

    if spoof_stocks:
        for s in spoof_stocks:
            sc = s['spoofing_count']
            cls = 'jj' if sc > 10 else 'yz'
            fund_flow_lines.append(f'<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:12px"><strong>{s["name"]}</strong> <span class="lx-tag {cls}">{sc}个对倒信号</span></div>')

    if cross_stocks:
        for s in cross_stocks:
            for ca in s.get('cross_alerts', []):
                cls = 'jj' if '冲突' in ca or '警惕' in ca else 'gx'
                fund_flow_lines.append(f'<div style="padding:6px 0;font-size:12px"><strong>{s["name"]}</strong> <span class="lx-tag {cls}">{ca}</span></div>')

    fund_flow_html = ''.join(fund_flow_lines) if fund_flow_lines else '<p style="color:var(--text-dim)">无资金流向数据</p>'

    type_label = content['type']
    header_label = f"{type_label} · 数据时间: {time_str}" if time_str else type_label

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>量学{type_label} {today}</title>
<style>
:root {{ --bg:#0a0e14; --surface:#151b23; --surface2:#1e2530; --border:#2a3441; --text:#e8edf4; --text-dim:#8899a6; --red:#ff4757; --red-dim:rgba(255,71,87,0.12); --green:#2ed573; --green-dim:rgba(46,213,115,0.12); --orange:#e67e22; --orange-dim:rgba(230,126,34,0.12); }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"PingFang SC",sans-serif; background:var(--bg); color:var(--text); font-size:14px; line-height:1.6; padding:16px; }}
.up {{ color:var(--red); }} .down {{ color:var(--green); }}
h1 {{ font-size:20px; font-weight:700; margin-bottom:8px; }}
h2 {{ font-size:16px; font-weight:600; margin:20px 0 12px; color:var(--text-dim); }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:16px; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:10px 8px; text-align:left; border-bottom:1px solid var(--border); }}
th {{ font-size:11px; color:var(--text-dim); text-transform:uppercase; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.signal-tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; margin-right:4px; background:var(--green-dim); color:var(--green); }}
.lx-tag {{ display:inline-block; padding:1px 5px; border-radius:3px; font-size:10px; font-weight:600; margin:1px 2px; background:rgba(46,213,115,0.1); color:var(--green); }}
.lx-tag.gx {{ background:rgba(245,166,35,0.15); color:#f5a623; }}
.lx-tag.yz {{ background:rgba(230,126,34,0.15); color:var(--orange); }}
.lx-tag.jj {{ background:rgba(255,71,87,0.12); color:var(--red); }}
.lx-tag.sup {{ background:rgba(46,213,115,0.1); color:var(--green); }}
.lx-tag.res {{ background:rgba(255,71,87,0.1); color:var(--red); }}
.alert {{ background:var(--orange-dim); border-left:3px solid var(--orange); padding:12px; border-radius:0 8px 8px 0; margin:8px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
.stat-box {{ background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; text-align:center; }}
.stat-box .value {{ font-size:24px; font-weight:700; }}
.stat-box .label {{ font-size:11px; color:var(--text-dim); margin-top:4px; }}
@media(max-width:600px){{ .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<h1>量学{type_label} {today}</h1>
<p style="color:var(--text-dim);margin-bottom:20px;">{header_label}</p>
<div class="grid">
  <div class="stat-box"><div class="value {'up' if content['total_profit'] >= 0 else 'down'}">{content['total_profit']:+,.0f}</div><div class="label">总盈亏</div></div>
  <div class="stat-box"><div class="value">{content['total_value']:,.0f}</div><div class="label">持仓市值</div></div>
  <div class="stat-box"><div class="value {'up' if content['total_profit'] >= 0 else 'down'}">{content['total_profit']/content['total_cost']*100:+.2f}%</div><div class="label">收益率</div></div>
</div>
<h2>持仓明细</h2>
<div class="card"><table>
<thead><tr><th>股票</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">成本</th><th class="num">盈亏%</th><th>信号</th><th>量学战法</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<h2>资金流向与交叉验证</h2>
<div class="card" style="font-size:13px">{fund_flow_html}</div>
<h2>关键位提醒</h2>
<div class="card">{alerts_html}</div>
</body></html>'''
    
    return html

def update_index_html(new_files):
    """更新index.html中的快速操作链接"""
    index_path = '/workspace/现代量学讲义/index.html'
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新快速操作行
    changes = []
    
    # 预案
    if '预案' in new_files and new_files['预案']:
        filename = new_files['预案']
        date_str = filename.replace('开盘预案-', '').replace('.html', '')
        # 替换旧的预案链接
        old_pattern = "<!-- PREVIEW_PLACEHOLDER_PLAN -->"
        if old_pattern in content:
            content = content.replace(old_pattern, f'''<div class="quick-card info" onclick="openReader('./{filename}','{date_str} 开盘预案');return false;">
        <div class="qc-icon">📋</div>
        <div class="qc-title">开盘预案</div>
        <div class="qc-sub">{date_str} 盘前分析</div>
        <span class="qc-badge">今日</span>
      </div>''')
        changes.append(f"预案: {filename}")
    
    # 盯盘
    if '盯盘' in new_files and new_files['盯盘']:
        filename = new_files['盯盘']
        date_str = filename.replace('盯盘清单-', '').replace('.html', '')
        old_pattern = "<!-- PREVIEW_PLACEHOLDER_WATCH -->"
        if old_pattern in content:
            content = content.replace(old_pattern, f'''<div class="quick-card danger" onclick="openReader('./{filename}','今日盯盘清单');return false;">
        <div class="qc-icon">🔴</div>
        <div class="qc-title">今日盯盘清单</div>
        <div class="qc-sub">{date_str} 盘中监控</div>
        <span class="qc-badge">必须打开</span>
      </div>''')
        changes.append(f"盯盘: {filename}")
    
    # 午盘
    if '午盘' in new_files and new_files['午盘']:
        filename = new_files['午盘']
        date_str = filename.replace('午盘研判-', '').replace('.html', '')
        old_pattern = "<!-- PREVIEW_PLACEHOLDER_NOON -->"
        if old_pattern in content:
            content = content.replace(old_pattern, f'''<div class="quick-card warning" onclick="openReader('./{filename}','{date_str} 午盘研判');return false;">
        <div class="qc-icon">📊</div>
        <div class="qc-title">午盘研判</div>
        <div class="qc-sub">{date_str} 午间分析</div>
        <span class="qc-badge">11:30数据</span>
      </div>''')
        changes.append(f"午盘: {filename}")
    
    # 复盘 - 直接匹配文本替换
    if '复盘' in new_files and new_files['复盘']:
        filename = new_files['复盘']
        date_str = filename.replace('复盘-', '').replace('.html', '')
        # 匹配现有的昨日复盘卡片并替换
        old_pattern = '''<div class="quick-card secondary" onclick="openReader\('./复盘-\d{4}-\d{2}-\d{2}\.html','[^']+'");return false;">
        <div class="qc-icon">📝</div>
        <div class="qc-title">昨日复盘</div>'''
        new_card = f'''<div class="quick-card secondary" onclick="openReader('./{filename}','{date_str} 收盘复盘');return false;">
        <div class="qc-icon">📝</div>
        <div class="qc-title">复盘日报</div>'''
        if old_pattern in content:
            content = content.replace(old_pattern, new_card)
            changes.append(f"复盘: {filename}")
        else:
            # 如果没有找到，尝试匹配"昨日复盘"文本
            if "昨日复盘" in content:
                content = content.replace("昨日复盘", "复盘日报")
                content = content.replace("复盘-2026-08-26.html", f"复盘-{today_str}.html")
                changes.append(f"复盘: {filename}")
    
    # 同时更新复盘页列表
    review_section = '''    <div class="section-header">
      <span class="section-title">收盘复盘</span>
      <span class="section-count">{count}份</span>
    </div>
    <div class="card-list">
      {items}
    </div>'''
    
    if '复盘' in new_files and new_files['复盘']:
        review_items = ''
        # 获取所有复盘文件
        review_files = sorted([f for f in os.listdir('/workspace/现代量学讲义') if f.startswith('复盘-') and f.endswith('.html')], reverse=True)[:5]
        for rf in review_files:
            ds = rf.replace('复盘-', '').replace('.html', '')
            review_items += f'''      <a class="lesson-card" href="#" onclick="openReader('./{rf}', '{ds} 收盘复盘');return false;">
        <div class="card-head">
          <div class="card-icon review">📝</div>
          <div class="card-meta">
            <span class="card-tag review">复盘</span>
            <div class="card-title">{ds} 收盘复盘</div>
            <div class="card-subtitle">每日收盘总结</div>
          </div>
        </div>
        <div class="card-desc">{ds} 持仓股走势分析</div>
        {'<span class="card-status new">最新</span>' if rf == new_files['复盘'] else ''}
      </a>
'''
        content = content.replace(
            '<div class="section-header">\n      <span class="section-title">收盘复盘</span>\n      <span class="section-count">3份</span>\n    </div>\n    <div class="card-list">\n      <a class="lesson-card" href="#" onclick="openReader(\'./复盘-2026-08-26.html\', \'8/26 收盘复盘\');return false;">',
            review_section.format(count=len(review_files), items=review_items)
        )
    
    if changes:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已更新 index.html:")
        for c in changes:
            print(f"  - {c}")
        return True
    return False

def main():
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    timestamp = now.strftime('%Y-%m-%d %H:%M')
    
    report_type = get_time_type()
    print(f"当前时间: {timestamp}")
    print(f"报告类型: {report_type}")
    
    # 查找最新文件
    new_files = {}
    for prefix in ['预案', '盯盘', '午盘', '复盘']:
        latest = find_latest_file(prefix)
        if latest:
            new_files[prefix] = latest
    
    # 如果没有今天的报告，生成新的
    need_generate = False
    if '复盘' in report_type and '复盘' not in new_files:
        need_generate = True
    elif '盘前' in report_type and '预案' not in new_files:
        need_generate = True
    elif '盯盘' in report_type and '盯盘' not in new_files:
        need_generate = True
    elif '午盘' in report_type and '午盘' not in new_files:
        need_generate = True
    
    if need_generate:
        content = generate_report_content(report_type, timestamp)
        filename = save_report(content, today_str)
        new_files[report_type.split()[0]] = filename
        print(f"已生成报告: {filename}")
    else:
        print("今日报告已存在，跳过生成")
    
    # 更新index.html
    update_index_html(new_files)
    
    # 提交git
    print("\n提交更新...")
    os.system('cd /workspace && git add -A && git commit -m "auto: 更新量学报告" 2>/dev/null && git push 2>/dev/null')
    print("完成!")

if __name__ == '__main__':
    main()
