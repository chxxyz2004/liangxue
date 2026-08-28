#!/usr/bin/env python3
"""
量学实战博客 - 统一服务器
8000端口提供:
1. 博客首页 (/)
2. 静态文件 (讲义/案例/图表/报告)
3. 回测API (/api/backtest)
4. 博客API (/api/posts, /api/categories, /api/stats等)
"""
import http.server
import socketserver
import os
import sys
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/workspace/回测分析')
sys.path.insert(0, '/workspace/行情数据库')

PORT = 8000
DIRECTORY = "/workspace/现代量学讲义"
KLINE_DIR = '/workspace/行情数据库/kline'

# 分类映射
CATEGORIES = {
    '复盘日报': '日报',
    '复盘日报_': '日报',
    '盘前预案': '预案',
    '盘前预案_': '预案',
    '盘中盯盘': '日报',
    '收盘复盘': '日报',
    '联网复盘': '日报',
    '案例_': '案例',
    '讲义_': '讲义',
    '学习路线图_': '路线',
    '历史回溯': '报告',
    '案例报告': '报告',
}

TAGS = {
    '倍量柱': '量柱形态',
    '黄金线': '关键技术',
    '右确认': '买入信号',
    '左证明': '技术理论',
    '止损': '风险管理',
    '仓位': '资金管理',
    '对倒': '风险识别',
    '产业链': '市场分析',
}


def parse_frontmatter(content):
    """解析Markdown frontmatter"""
    meta = {'title': '', 'date': '', 'category': '', 'tags': []}
    if not content.startswith('---'):
        return meta, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return meta, content
    
    yaml = parts[1]
    body = parts[2]
    
    for line in yaml.split('\n'):
        line = line.strip()
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key, val = key.strip(), val.strip()
        if key == 'title':
            meta['title'] = val.strip('"\'')
        elif key == 'date':
            meta['date'] = val.strip('"\'')
        elif key == 'category':
            meta['category'] = val.strip('"\'')
        elif key == 'tags' and val.startswith('['):
            meta['tags'] = re.findall(r'"([^"]+)"', val)
    
    return meta, body


def detect_category(filename):
    """从文件名检测分类"""
    for prefix, cat in CATEGORIES.items():
        if filename.startswith(prefix):
            return cat
    return '其他'


def extract_excerpt(content, max_len=150):
    """提取文章摘要"""
    # 移除frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2]
    
    # 移除markdown标记
    lines = content.split('\n')
    text = ' '.join([l.strip() for l in lines if not l.startswith('#')])
    text = re.sub(r'[#*`>\-|~\[\]]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text[:max_len] + '...' if len(text) > max_len else text


class BlogHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    @property
    def decoded_path(self):
        """正确解码包含UTF-8字符的路径"""
        if hasattr(self, 'raw_requestline'):
            try:
                raw = self.raw_requestline
                if isinstance(raw, bytes):
                    decoded = raw.decode('utf-8')
                    parts = decoded.split(' ')
                    if len(parts) >= 2:
                        return parts[1]
            except (UnicodeDecodeError, IndexError):
                pass
        return self.path
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.decoded_path)
        path = urllib.parse.unquote(parsed.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        # 博客API路由
        if path == '/api/health':
            self.send_json({'status': 'ok', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        elif path == '/api/posts':
            self.handle_get_posts(params)
        elif path.startswith('/api/posts/'):
            slug = path.split('/')[-1]
            self.handle_get_post(slug)
        elif path == '/api/categories':
            self.handle_get_categories()
        elif path == '/api/tags':
            self.handle_get_tags()
        elif path == '/api/stats':
            self.handle_get_stats()
        elif path.startswith('/api/stock/'):
            code = path.split('/')[-1]
            self.handle_get_stock(code)
        elif path == '/api/backtest':
            self.handle_backtest(params)
        elif path.startswith('/api/search/'):
            keyword = urllib.parse.unquote(path.split('/')[-1])
            self.handle_search(keyword)
        
        # 回退到静态文件
        elif path == '/' or path == '':
            self.path = '/blog.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def do_OPTIONS(self):
        """处理CORS预检"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    # ===== 博客API处理 =====
    
    def handle_get_posts(self, params):
        """获取文章列表"""
        category = params.get('category', [None])[0]
        limit = int(params.get('limit', [50])[0])
        
        posts = []
        for f in os.listdir(DIRECTORY):
            if not f.endswith('.md') or f.startswith('.'):
                continue
            
            path = os.path.join(DIRECTORY, f)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                
                meta, body = parse_frontmatter(content)
                excerpt = extract_excerpt(content)
                
                cat = meta.get('category') or detect_category(f)
                if category and cat != category:
                    continue
                
                posts.append({
                    'slug': f.replace('.md', ''),
                    'title': meta.get('title') or f.replace('.md', ''),
                    'date': meta.get('date', datetime.now().strftime('%Y-%m-%d')),
                    'category': cat,
                    'tags': meta.get('tags', []),
                    'excerpt': excerpt,
                })
            except Exception:
                continue
        
        posts.sort(key=lambda x: x['date'], reverse=True)
        
        self.send_json({'posts': posts[:limit], 'total': len(posts)})
    
    def handle_get_post(self, slug):
        """获取单篇文章"""
        # 先尝试MD
        md_path = os.path.join(DIRECTORY, slug + '.md')
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            meta, body = parse_frontmatter(content)
            self.send_json({
                'slug': slug,
                'title': meta.get('title') or slug,
                'date': meta.get('date', datetime.now().strftime('%Y-%m-%d')),
                'category': meta.get('category') or detect_category(slug + '.md'),
                'tags': meta.get('tags', []),
                'content': body,
            })
            return
        
        # 尝试HTML
        html_path = os.path.join(DIRECTORY, slug + '.html')
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_json({'type': 'html', 'content': content})
            return
        
        self.send_json({'error': '文章不存在'}, 404)
    
    def handle_get_categories(self):
        """获取分类"""
        cats = {}
        for f in os.listdir(DIRECTORY):
            if not f.endswith('.md'):
                continue
            cat = detect_category(f)
            cats[cat] = cats.get(cat, 0) + 1
        self.send_json({'categories': cats})
    
    def handle_get_tags(self):
        """获取标签"""
        self.send_json({'tags': TAGS})
    
    def handle_get_stats(self):
        """获取统计"""
        md_count = len([f for f in os.listdir(DIRECTORY) if f.endswith('.md') and not f.startswith('.')])
        html_count = len([f for f in os.listdir(DIRECTORY) if f.endswith('.html')])
        stock_count = len([f for f in os.listdir(KLINE_DIR) if f.endswith('.json')]) if os.path.exists(KLINE_DIR) else 0
        self.send_json({'posts': md_count, 'courses': html_count, 'stocks': stock_count})
    
    def handle_get_stock(self, code):
        """获取股票数据"""
        path = os.path.join(KLINE_DIR, code + '.json')
        if not os.path.exists(path):
            self.send_json({'error': '数据不存在'}, 404)
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        klines = data.get('klines') or data.get('data') or []
        recent = klines[-60:] if klines else []
        self.send_json({'code': code, 'name': data.get('name', code), 'recent': recent})
    
    def handle_search(self, keyword):
        """搜索文章"""
        results = []
        kw = keyword.lower()
        for f in os.listdir(DIRECTORY):
            if not f.endswith('.md'):
                continue
            path = os.path.join(DIRECTORY, f)
            with open(path, 'r', encoding='utf-8') as fp:
                content = fp.read()
            if kw in content.lower():
                meta, _ = parse_frontmatter(content)
                results.append({
                    'slug': f.replace('.md', ''),
                    'title': meta.get('title') or f,
                    'date': meta.get('date', ''),
                    'category': meta.get('category') or detect_category(f),
                })
        self.send_json({'results': results})
    
    # ===== 原有API =====
    
    def handle_backtest(self, params):
        """回测API"""
        symbol = params.get('symbol', ['sh603516'])[0]
        strategy = params.get('strategy', ['all'])[0]
        
        try:
            sys.path.insert(0, '/workspace/回测分析')
            import backtest_engine
            result = backtest_engine.run_backtest(symbol, strategy)
            self.send_json(result)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    # ===== 工具方法 =====
    
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, format, *args):
        pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    server = ReusableTCPServer(("", PORT), BlogHandler)
    print(f"量学实战博客运行中: http://localhost:{PORT}")
    print(f"博客首页: /")
    print(f"文章列表: /api/posts")
    print(f"回测API: /api/backtest")
    server.serve_forever()
