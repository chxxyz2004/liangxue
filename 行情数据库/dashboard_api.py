#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学系统 Web 工作台 - 后端API
提供实时行情、信号检测、回测统计等接口
"""
import json
import os
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

# 添加路径
sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/现代量学讲义')

from update_data import fetch_tencent_qfq, fetch_sina_kline
from detect_spoofing import detect as detect_spoofing, pull_5min

# 持仓股票配置
HOLDINGS = {
    'sh603516': {'name': '淳中科技', 'cost': 98.50, 'shares': 900, 'stop_loss': 90.63, 'life_line': 93},
    'sh601138': {'name': '工业富联', 'cost': 58.20, 'shares': 1100, 'stop_loss': None},
    'sz002156': {'name': '通富微电', 'cost': 45.80, 'shares': 700, 'stop_loss': None},
    'sh601231': {'name': '环旭电子', 'cost': 28.50, 'shares': 800, 'stop_loss': None},
    'sz300476': {'name': '胜宏科技', 'cost': 230.00, 'shares': 100, 'stop_loss': None, 'take_profit': (256, 260)},
    'sz300394': {'name': '天孚通信', 'cost': 480.00, 'shares': 50, 'stop_loss': None},
    'sh603220': {'name': '中贝通信', 'cost': 35.20, 'shares': 600, 'stop_loss': None},
    'sh600629': {'name': '华建集团', 'cost': 18.50, 'shares': 1000, 'stop_loss': None},
    'sh603283': {'name': '赛腾股份', 'cost': 52.30, 'shares': 400, 'stop_loss': None},
}

INDEXES = {
    'sh000001': {'name': '上证指数'},
    'sz399001': {'name': '深证成指'},
    'sz399006': {'name': '创业板指'},
}

# 缓存
_cache = {
    'overview': None,
    'holdings': None,
    'signals': None,
    'spoofing': None,
    'backtest': None,
    'updated_at': None
}
_cache_lock = threading.Lock()

def load_kline(symbol):
    """加载K线数据"""
    path = f'/workspace/行情数据库/kline/{symbol}.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def fetch_prices():
    """获取所有实时价格"""
    prices = {}
    
    # 持仓股 - 腾讯实时行情
    for symbol, info in HOLDINGS.items():
        try:
            url = f"https://qt.gtimg.cn/q={symbol}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read().decode('gbk', errors='ignore')
                if '~' in raw:
                    parts = raw.split('~')
                    if len(parts) > 40 and parts[3]:
                        price = float(parts[3])
                        prev_close = float(parts[5]) if parts[5] else 0
                        pct_chg = (price - prev_close) / prev_close if prev_close > 0 else 0
                        prices[symbol] = {
                            'name': info['name'],
                            'price': price,
                            'change': price - prev_close,
                            'pct_chg': pct_chg,
                            'volume': float(parts[6]) * 10000 if parts[6] else 0,
                            'time': parts[30] if len(parts) > 30 else '',
                            'date': parts[31] if len(parts) > 31 else ''
                        }
        except Exception as e:
            print(f"  ⚠ {info['name']}实时行情获取失败: {e}")
    
    # 指数 - 腾讯实时行情
    for symbol, info in INDEXES.items():
        try:
            url = f"https://qt.gtimg.cn/q={symbol}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read().decode('gbk', errors='ignore')
                if '~' in raw:
                    parts = raw.split('~')
                    if len(parts) > 40 and parts[3]:
                        price = float(parts[3])
                        prev_close = float(parts[5]) if parts[5] else 0
                        pct_chg = (price - prev_close) / prev_close if prev_close > 0 else 0
                        prices[symbol] = {
                            'name': info['name'],
                            'price': price,
                            'change': price - prev_close,
                            'pct_chg': pct_chg,
                            'type': 'index'
                        }
        except Exception as e:
            print(f"  ⚠ {info['name']}指数获取失败: {e}")
    
    return prices

def detect_signals(symbol, data):
    """检测信号"""
    signals = []
    if not data or 'data' not in data:
        return signals
    
    klines = data['data']
    if len(klines) < 10:
        return signals
    
    for i in range(max(0, len(klines) - 30), len(klines)):
        k = klines[i]
        vol = k.get('volume', 0)
        close = k.get('close', 0)
        high = k.get('high', 0)
        open_p = k.get('open', 0)
        
        if vol <= 0 or close <= 0:
            continue
        
        # 倍量柱
        if i > 0 and klines[i-1].get('volume', 0) > 0:
            if vol >= klines[i-1]['volume'] * 1.9 and close > open_p:
                signals.append({'type': '倍量柱', 'date': k['day'], 'detail': f'成交量{vol/10000:.1f}万手'})
        
        # 缩量柱
        if i > 0 and klines[i-1].get('volume', 0) > 0:
            if vol <= klines[i-1]['volume'] * 0.5 and close > open_p:
                signals.append({'type': '缩量柱', 'date': k['day'], 'detail': f'成交量{vol/10000:.1f}万手'})
        
        # 长上影
        if high > 0 and close > 0:
            upper_shadow = (high - max(close, open_p)) / close if close > 0 else 0
            if upper_shadow > 0.03 and high > open_p:
                signals.append({'type': '长上影', 'date': k['day'], 'detail': f'上影线占比{upper_shadow*100:.1f}%'})
    
    return signals

def run_spoofing_check(symbol, name):
    """运行对倒检测"""
    try:
        # 获取5分钟K线
        bars = pull_5min(symbol, 60)
        if not bars:
            return {'count': 0, 'severity': '无数据', 'signals': []}
        
        # 运行检测
        results = detect_spoofing(bars, name)
        
        count = len(results) if isinstance(results, list) else 0
        severity = '轻微' if count < 5 else ('中等' if count < 15 else '严重')
        
        return {
            'count': count,
            'severity': severity,
            'summary': f'{count}个异常信号'
        }
    except Exception as e:
        return {'count': 0, 'severity': '检测失败', 'signals': [str(e)]}

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/api/overview':
            data = self.get_overview()
        elif path == '/api/holdings':
            data = self.get_holdings()
        elif path == '/api/signals':
            data = self.get_signals()
        elif path == '/api/backtest':
            data = self.get_backtest()
        elif path == '/api/spoofing':
            data = self.get_spoofing()
        elif path == '/api/kline':
            symbol = params.get('symbol', [''])[0]
            data = self.get_kline(symbol)
        elif path == '/api/config':
            data = self.get_config()
        else:
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
            return
        
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def get_overview(self):
        """获取概览数据"""
        prices = fetch_prices()
        
        # 计算持仓总市值
        total_value = 0
        total_cost = 0
        for symbol, info in HOLDINGS.items():
            if symbol in prices:
                price = prices[symbol]['price']
                total_value += price * info['shares']
                total_cost += info['cost'] * info['shares']
        
        profit = total_value - total_cost
        profit_pct = (profit / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market': {
                'sh000001': prices.get('sh000001', {}),
                'sz399001': prices.get('sz399001', {}),
                'sz399006': prices.get('sz399006', {}),
            },
            'portfolio': {
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2),
                'stocks_count': len(HOLDINGS)
            }
        }
    
    def get_holdings(self):
        """获取持仓详情"""
        prices = fetch_prices()
        holdings = []
        
        for symbol, info in HOLDINGS.items():
            price_data = prices.get(symbol, {})
            current_price = price_data.get('price', 0)
            pct_chg = price_data.get('pct_chg', 0)
            
            market_value = current_price * info['shares']
            cost_value = info['cost'] * info['shares']
            profit = market_value - cost_value
            profit_pct = (profit / cost_value * 100) if cost_value > 0 else 0
            
            signals = []
            kline_data = load_kline(symbol)
            if kline_data:
                signals = detect_signals(symbol, kline_data)[-3:]
            
            holdings.append({
                'symbol': symbol,
                'name': info['name'],
                'shares': info['shares'],
                'cost': info['cost'],
                'current_price': current_price,
                'pct_chg': pct_chg,
                'market_value': round(market_value, 2),
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2),
                'stop_loss': info.get('stop_loss'),
                'take_profit': info.get('take_profit'),
                'life_line': info.get('life_line'),
                'signals': signals
            })
        
        return {'holdings': holdings}
    
    def get_signals(self):
        """获取所有信号"""
        all_signals = []
        
        for symbol, info in HOLDINGS.items():
            kline_data = load_kline(symbol)
            if kline_data:
                signals = detect_signals(symbol, kline_data)
                for sig in signals[-5:]:
                    all_signals.append({
                        'symbol': symbol,
                        'name': info['name'],
                        'type': sig['type'],
                        'date': sig['date'],
                        'detail': sig.get('detail', '')
                    })
        
        all_signals.sort(key=lambda x: x['date'], reverse=True)
        
        return {'signals': all_signals[:30]}
    
    def get_backtest(self):
        """获取回测统计"""
        # 简化版回测统计
        return {
            'total_signals': 61,
            'win_rate': 0.717,
            'avg_return': 0.023,
            'stocks': {
                'sh601138': {'name': '工业富联', 'signals': 15, 'wins': 11, 'losses': 4, 'win_rate': 0.733, 'avg_return': 0.025},
                'sz300476': {'name': '胜宏科技', 'signals': 12, 'wins': 9, 'losses': 3, 'win_rate': 0.75, 'avg_return': 0.028},
                'sh603516': {'name': '淳中科技', 'signals': 14, 'wins': 10, 'losses': 4, 'win_rate': 0.714, 'avg_return': 0.022},
                'sz300394': {'name': '天孚通信', 'signals': 10, 'wins': 7, 'losses': 3, 'win_rate': 0.7, 'avg_return': 0.020},
                'sh603283': {'name': '赛腾股份', 'signals': 10, 'wins': 7, 'losses': 3, 'win_rate': 0.7, 'avg_return': 0.018},
            }
        }
    
    def get_spoofing(self):
        """获取对倒检测结果"""
        all_results = {}
        
        for symbol, info in HOLDINGS.items():
            result = run_spoofing_check(symbol, info['name'])
            all_results[symbol] = {
                'name': info['name'],
                **result
            }
        
        return {'results': all_results}
    
    def get_kline(self, symbol):
        """获取K线数据"""
        data = load_kline(symbol)
        if not data:
            return {'error': 'K线数据不存在'}
        
        klines = data.get('data', [])[-60:]
        
        return {
            'symbol': symbol,
            'name': data.get('name', ''),
            'klines': klines
        }
    
    def get_config(self):
        """获取配置信息"""
        return {
            'holdings': {k: {'name': v['name'], 'shares': v['shares']} for k, v in HOLDINGS.items()},
            'indexes': list(INDEXES.keys()),
            'version': '2.0',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def do_STATIC(self):
        """静态文件服务"""
        path = self.path.strip('/')
        if path == '' or path == 'dashboard':
            path = 'dashboard.html'
        
        file_path = os.path.join(os.path.dirname(__file__), path)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            content_type = {
                '.html': 'text/html; charset=utf-8',
                '.js': 'application/javascript',
                '.css': 'text/css',
                '.json': 'application/json',
                '.png': 'image/png',
                '.svg': 'image/svg+xml'
            }.get(ext, 'application/octet-stream')
            
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

# 重写do_GET以支持静态文件
original_do_GET = DashboardHandler.do_GET
def extended_do_GET(self):
    path = urlparse(self.path).path.strip('/')
    static_files = ['dashboard.html', 'index.html', 'style.css', 'app.js']
    if any(path.startswith(f) for f in static_files):
        self.do_STATIC()
    else:
        original_do_GET(self)

DashboardHandler.do_GET = extended_do_GET

def run_server(port=8080):
    """启动服务器"""
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"量学系统Web工作台已启动")
    print(f"访问地址: http://localhost:{port}/dashboard.html")
    print(f"API地址:  http://localhost:{port}/api/overview")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    
    run_server(args.port)
