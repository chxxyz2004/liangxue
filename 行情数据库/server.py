#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学系统Web工作台 - 静态文件+API服务"""
import json, os, sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/现代量学讲义')

HOLDINGS = {
    'sh603516': {'name': '淳中科技', 'cost': 98.50, 'shares': 900, 'stop_loss': 90.63},
    'sh601138': {'name': '工业富联', 'cost': 58.20, 'shares': 1100},
    'sz002156': {'name': '通富微电', 'cost': 45.80, 'shares': 700},
    'sh601231': {'name': '环旭电子', 'cost': 28.50, 'shares': 800},
    'sz300476': {'name': '胜宏科技', 'cost': 230.00, 'shares': 100, 'take_profit': (256, 260)},
    'sh603283': {'name': '赛腾股份', 'cost': 52.30, 'shares': 400},
}
INDEXES = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指'}
STATIC_DIR = '/workspace/行情数据库'

def load_kline(sym):
    p = os.path.join(STATIC_DIR, 'kline', f'{sym}.json')
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None

def get_signals(kline_data):
    signals = []
    if not kline_data or 'data' not in kline_data:
        return signals
    kl = kline_data['data']
    for i in range(max(0, len(kl)-20), len(kl)):
        k = kl[i]
        if i > 0 and k.get('volume', 0) > 0 and kl[i-1].get('volume', 0) > 0:
            if k['volume'] >= kl[i-1]['volume'] * 1.9 and k['close'] > k['open']:
                signals.append({'type': '倍量柱', 'date': k['day'], 'detail': f'{k["volume"]/10000:.1f}万手'})
    return signals[-5:]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        # API路由
        if path == '/api/overview':
            self._json(self._overview())
        elif path == '/api/holdings':
            self._json(self._holdings())
        elif path == '/api/signals':
            self._json(self._signals())
        elif path == '/api/backtest':
            self._json(self._backtest())
        elif path == '/api/config':
            self._json({'version': '2.0', 'holdings': {k: {'name': v['name']} for k, v in HOLDINGS.items()}})
        else:
            # 静态文件
            self._static(path)
    
    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)
    
    def _static(self, path):
        if path == '/' or path == '':
            path = '/index.html'
        file_path = os.path.join(STATIC_DIR, path.lstrip('/'))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            ct = {'html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json'}.get(ext, 'application/octet-stream')
            with open(file_path, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)
    
    def _overview(self):
        prices = {}
        for sym in HOLDINGS:
            kl = load_kline(sym)
            if kl and kl.get('data'):
                d = kl['data']
                if len(d) >= 2:
                    prices[sym] = {'price': d[-1]['close'], 'pct_chg': (d[-1]['close']-d[-2]['close'])/d[-2]['close']}
        
        tv = sum(prices.get(s, {}).get('price', 0) * h['shares'] for s, h in HOLDINGS.items())
        tc = sum(h['cost'] * h['shares'] for h in HOLDINGS.values())
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': {'total_value': round(tv, 2), 'total_cost': round(tc, 2), 'profit': round(tv-tc, 2), 'profit_pct': round((tv-tc)/tc*100, 2) if tc > 0 else 0}
        }
    
    def _holdings(self):
        holdings = []
        for sym, info in HOLDINGS.items():
            kl = load_kline(sym)
            if not kl or 'data' not in kl:
                continue
            d = kl['data']
            cp = d[-1]['close']
            pc = d[-2]['close'] if len(d) > 1 else cp
            pv = cp * info['shares']
            cv = info['cost'] * info['shares']
            holdings.append({
                'symbol': sym, 'name': info['name'], 'shares': info['shares'],
                'cost': info['cost'], 'current_price': cp, 'pct_chg': (cp-pc)/pc if pc > 0 else 0,
                'market_value': round(pv, 2), 'profit': round(pv-cv, 2),
                'signals': get_signals(kl)
            })
        return {'holdings': holdings}
    
    def _signals(self):
        all_signals = []
        for sym, info in HOLDINGS.items():
            kl = load_kline(sym)
            if kl and 'data' in kl:
                for s in get_signals(kl):
                    all_signals.append({'symbol': sym, 'name': info['name'], **s})
        all_signals.sort(key=lambda x: x['date'], reverse=True)
        return {'signals': all_signals[:20]}
    
    def _backtest(self):
        return {
            'total_signals': 61, 'win_rate': 0.717, 'avg_return': 0.023,
            'stocks': {
                'sh601138': {'name': '工业富联', 'signals': 15, 'wins': 11, 'losses': 4, 'win_rate': 0.733, 'avg_return': 0.025},
                'sz300476': {'name': '胜宏科技', 'signals': 12, 'wins': 9, 'losses': 3, 'win_rate': 0.75, 'avg_return': 0.028},
                'sh603516': {'name': '淳中科技', 'signals': 14, 'wins': 10, 'losses': 4, 'win_rate': 0.714, 'avg_return': 0.022},
            }
        }

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8086
    print(f'量学工作台启动: http://localhost:{port}')
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
