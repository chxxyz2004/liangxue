#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量API服务 - 为8000端口提供/api/health等接口"""
import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, '/workspace/行情数据库')

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    
    def do_GET(self):
        if self.path == '/api/health':
            self._json({'status': 'ok', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        elif self.path == '/api/holdings':
            self._json({'holdings': len([f for f in os.listdir('/workspace/行情数据库/kline') if f.endswith('.json')])})
        else:
            self.send_error(404)
    
    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f'API服务启动: http://localhost:{port}')
    HTTPServer(('0.0.0.0', port), APIHandler).serve_forever()
