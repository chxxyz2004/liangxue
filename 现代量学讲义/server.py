#!/usr/bin/env python3
"""
量学实战系统 - 统一服务器
8000端口同时提供:
1. 静态文件 (讲义/案例/图表/报告)
2. 回测API (/api/*)
3. 单页应用入口
不需要8087端口, 手机通过预览URL即可访问全部功能
"""
import http.server
import socketserver
import os
import sys
import json
import urllib.parse
from pathlib import Path

sys.path.insert(0, '/workspace/回测分析')
sys.path.insert(0, '/workspace/行情数据库')

PORT = 8000
DIRECTORY = "/workspace/现代量学讲义"

# 延迟导入, 避免启动失败
def get_holdings():
    try:
        from config import HOLDINGS
        return HOLDINGS
    except Exception:
        return {}

def get_backtest_engine():
    import backtest_engine
    return backtest_engine


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 回测API路由
        if path.startswith('/api/backtest'):
            self.handle_backtest(parsed)
            return
        if path.startswith('/api/review'):
            self.handle_review()
            return
        if path.startswith('/api/preplan'):
            self.handle_preplan()
            return

        # 根路径返回单页应用
        if path == '/' or path == '':
            self.path = '/app.html'
        return super().do_GET()

    def handle_backtest(self, parsed):
        """回测API"""
        params = urllib.parse.parse_qs(parsed.query)
        symbol = params.get('symbol', ['sh603516'])[0]
        strategy = params.get('strategy', ['all'])[0]
        
        try:
            engine = get_backtest_engine()
            result = engine.run_backtest(symbol, strategy)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8'))

    def handle_review(self):
        """复盘日报"""
        path = os.path.join(DIRECTORY, '复盘日报.md')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/markdown; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def handle_preplan(self):
        """盘前预案"""
        path = os.path.join(DIRECTORY, '盘前预案.md')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/markdown; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # 静默日志
        pass


if __name__ == '__main__':
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        print(f"量学实战系统运行中: http://localhost:{PORT}")
        print("回测API: /api/backtest")
        print("复盘日报: /api/review")
        print("盘前预案: /api/preplan")
        httpd.serve_forever()
