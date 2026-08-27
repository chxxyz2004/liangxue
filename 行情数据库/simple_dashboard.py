#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学系统 Web 工作台 - 简化版API"""
import sys, json, os, urllib.request
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/现代量学讲义')
from update_data import fetch_tencent_qfq
from detect_spoofing import detect as detect_spoofing_func, pull_5min

# 引用统一配置中心，禁止硬编码
from config import HOLDINGS, WATCH_LIST, INDEXES

def fetch_prices():
    prices = {}
    for sym, info in HOLDINGS.items():
        try:
            url = f"https://qt.gtimg.cn/q={sym}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as r:
                raw = r.read().decode('gbk', errors='ignore')
                parts = raw.split('~')
                if len(parts) > 40 and parts[3]:
                    p, pc = float(parts[3]), float(parts[5]) if parts[5] else 0
                    prices[sym] = {'name': info.name, 'price': p, 'pct_chg': (p-pc)/pc if pc>0 else 0}
        except: pass
    for sym, name in INDEXES.items():
        try:
            url = f"https://qt.gtimg.cn/q={sym}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as r:
                raw = r.read().decode('gbk', errors='ignore')
                parts = raw.split('~')
                if len(parts) > 40 and parts[3]:
                    p, pc = float(parts[3]), float(parts[5]) if parts[5] else 0
                    prices[sym] = {'name': name, 'price': p, 'pct_chg': (p-pc)/pc if pc>0 else 0, 'type':'index'}
        except: pass
    return prices

def load_kline(sym):
    p = f'/workspace/行情数据库/kline/{sym}.json'
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return None

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        path = urlparse(self.path).path
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if path == '/api/overview':
            prices = fetch_prices()
            tv, tc = 0, 0
            for s, info in HOLDINGS.items():
                if s in prices:
                    tv += prices[s]['price'] * info.shares
                    tc += info.cost * info.shares
            profit = tv - tc
            data = {'timestamp': str(datetime.now()), 'market': prices, 'portfolio': {'total_value': tv, 'total_cost': tc, 'profit': profit, 'profit_pct': profit/tc*100 if tc>0 else 0}}
        elif path == '/api/holdings':
            prices = fetch_prices()
            holdings = []
            for s, info in HOLDINGS.items():
                pd = prices.get(s, {})
                cp = pd.get('price', 0)
                pv = cp * info.shares
                cv = info.cost * info.shares
                kline = load_kline(s)
                signals = []
                if kline:
                    kl = kline.get('data', [])
                    for i in range(max(0,len(kl)-10), len(kl)):
                        k = kl[i]
                        if k.get('volume',0) > 0 and k.get('close',0) > 0:
                            if i > 0 and k['volume'] >= kl[i-1]['volume']*1.9 and k['close'] > k['open']:
                                signals.append({'type':'倍量柱','date':k['day']})
                holdings.append({'symbol':s,'name':info.name,'shares':info.shares,'cost':info.cost,'current_price':cp,'pct_chg':pd.get('pct_chg',0),'market_value':pv,'profit':pv-cv,'signals':signals[-3:]})
            data = {'holdings': holdings}
        elif path == '/api/signals':
            all_signals = []
            for s, info in HOLDINGS.items():
                kline = load_kline(s)
                if kline:
                    kl = kline.get('data', [])
                    for i in range(max(0,len(kl)-20), len(kl)):
                        k = kl[i]
                        if k.get('volume',0) > 0 and k.get('close',0) > 0:
                            if i > 0 and k['volume'] >= kl[i-1]['volume']*1.9 and k['close'] > k['open']:
                                all_signals.append({'symbol':s,'name':info.name,'type':'倍量柱','date':k['day']})
            data = {'signals': all_signals[:20]}
        elif path == '/api/spoofing':
            results = {}
            for s, info in HOLDINGS.items():
                try:
                    bars = pull_5min(s, 30)
                    if bars:
                        res = detect_spoofing_func(bars, info.name)
                        cnt = len(res) if isinstance(res, list) else 0
                        sev = '轻微' if cnt < 5 else ('中等' if cnt < 15 else '严重')
                        results[s] = {'name':info.name,'count':cnt,'severity':sev}
                except: results[s] = {'name':info.name,'count':0,'severity':'无数据'}
            data = {'results': results}
        else:
            data = {'error': 'Not found'}
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

print('Starting dashboard API on port 8081...')
HTTPServer(('0.0.0.0', 8081), H).serve_forever()
