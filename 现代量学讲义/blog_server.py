#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学实战博客 - 后端API服务
提供文章、分类、行情数据、回测等API接口
"""
import json
import os
import re
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 路径配置
BASE_DIR = '/workspace'
BLOG_DIR = os.path.join(BASE_DIR, '现代量学讲义')
KLINE_DIR = os.path.join(BASE_DIR, '行情数据库', 'kline')
REPORTS_DIR = os.path.join(BLOG_DIR, 'reports')

# 分类定义
CATEGORIES = {
    '日报': {'name': '复盘日报', 'icon': '📊', 'desc': '每日复盘总结'},
    '预案': {'name': '盘前预案', 'icon': '📋', 'desc': '每日操作计划'},
    '案例': {'name': '个股案例', 'icon': '📈', 'desc': '持仓股深度分析'},
    '讲义': {'name': '讲义课程', 'icon': '📚', 'desc': '量学理论学习'},
    '路线': {'name': '学习路线', 'icon': '🗺️', 'desc': '系统学习路径'},
    '报告': {'name': '分析报告', 'icon': '📉', 'desc': '深度研究报告'},
    '课程': {'name': 'HTML课程', 'icon': '🎓', 'desc': '互动式课程'},
}

# 标签定义
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


class BlogHandler(BaseHTTPRequestHandler):
    """博客API处理器"""
    
    def log_message(self, format, *args):
        """静默日志"""
        pass
    
    def send_json(self, data, status=200):
        """发送JSON响应"""
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)
    
    def send_html(self, html):
        """发送HTML响应"""
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)
    
    def do_OPTIONS(self):
        """处理CORS预检"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # 路由分发
        if path == '/':
            self.send_html(self.get_index_html())
        elif path == '/api/health':
            self.send_json({'status': 'ok', 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        elif path == '/api/posts':
            self.send_json(self.get_posts(params))
        elif path.startswith('/api/posts/'):
            slug = path.split('/')[-1]
            self.send_json(self.get_post(slug))
        elif path == '/api/categories':
            self.send_json(self.get_categories())
        elif path == '/api/tags':
            self.send_json(self.get_tags())
        elif path == '/api/stats':
            self.send_json(self.get_stats())
        elif path.startswith('/api/stock/'):
            code = path.split('/')[-1]
            self.send_json(self.get_stock_data(code))
        elif path == '/api/backtest':
            self.send_json(self.get_backtest(params))
        elif path.startswith('/api/search/'):
            keyword = path.split('/')[-1]
            self.send_json(self.search_posts(keyword))
        elif path.startswith('/chart/'):
            self.serve_static(path[1:])
        else:
            self.serve_static(path[1:])
    
    def get_index_html(self):
        """返回博客首页HTML"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>量学实战博客</title>
<style>
:root{--primary:#6366f1;--bg:#0f172a;--card:#1e293b;--text:#f1f5f9;--dim:#94a3b8;--border:#334155}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
a{text-decoration:none;color:inherit}
.nav{position:fixed;top:0;left:0;right:0;height:56px;background:rgba(15,23,42,0.95);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;z-index:100}
.nav-logo{font-size:18px;font-weight:700;background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero{margin-top:56px;padding:60px 20px;text-align:center;background:linear-gradient(135deg,#1e1b4b,#4c1d95);position:relative;overflow:hidden}
.hero h1{font-size:clamp(24px,5vw,36px);font-weight:800;margin-bottom:12px}
.hero p{color:var(--dim);font-size:14px}
.container{max-width:900px;margin:0 auto;padding:20px}
.posts{display:grid;gap:16px}
.post-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;cursor:pointer;transition:all 0.2s}
.post-card:hover{transform:translateY(-2px);border-color:var(--primary);box-shadow:0 8px 24px rgba(99,102,241,0.2)}
.post-meta{display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.tag{background:rgba(99,102,241,0.15);color:#818cf8;padding:2px 8px;border-radius:4px;font-size:11px}
.post-title{font-size:16px;font-weight:600;margin-bottom:8px}
.post-excerpt{font-size:13px;color:var(--dim);line-height:1.6}
.post-date{font-size:11px;color:var(--dim);margin-top:8px}
.loading{text-align:center;padding:40px;color:var(--dim)}
</style>
</head>
<body>
<nav class="nav"><div class="nav-logo">量学实战博客</div></nav>
<div class="hero">
<h1>量学实战博客</h1>
<p>基于真实数据的量化交易学习笔记</p>
</div>
<div class="container">
<div class="posts" id="posts"><div class="loading">加载中...</div></div>
</div>
<script>
fetch('/api/posts').then(r=>r.json()).then(data=>{
const posts=data.posts||[];
const el=document.getElementById('posts');
if(!posts.length){el.innerHTML='<div class="loading">暂无文章</div>';return;}
el.innerHTML=posts.map(p=>`
<div class="post-card" onclick="window.location.href='/api/posts/${p.slug}'">
<div class="post-meta">
<span class="tag">${p.category||'文章'}</span>
${(p.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}
</div>
<div class="post-title">${p.title}</div>
<div class="post-excerpt">${(p.excerpt||'').substring(0,100)}...</div>
<div class="post-date">${p.date||''}</div>
</div>`).join('');
}).catch(e=>{document.getElementById('posts').innerHTML='<div class="loading">加载失败</div>'});
</script>
</body>
</html>'''
    
    def get_posts(self, params):
        """获取文章列表"""
        category = params.get('category', [None])[0]
        limit = int(params.get('limit', [20])[0])
        
        posts = []
        md_files = [f for f in os.listdir(BLOG_DIR) if f.endswith('.md') and not f.startswith('.')]
        
        for f in md_files:
            path = os.path.join(BLOG_DIR, f)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                
                # 解析frontmatter
                meta = self.parse_frontmatter(content)
                
                # 提取摘要
                excerpt = self.extract_excerpt(content)
                
                # 分类
                cat = meta.get('category', '其他')
                if category and cat != category:
                    continue
                
                posts.append({
                    'slug': f.replace('.md', ''),
                    'title': meta.get('title', f.replace('.md', '')),
                    'date': meta.get('date', datetime.now().strftime('%Y-%m-%d')),
                    'category': cat,
                    'tags': meta.get('tags', []),
                    'excerpt': excerpt,
                })
            except Exception as e:
                continue
        
        # 排序
        posts.sort(key=lambda x: x['date'], reverse=True)
        
        return {'posts': posts[:limit], 'total': len(posts)}
    
    def get_post(self, slug):
        """获取单篇文章"""
        path = os.path.join(BLOG_DIR, slug + '.md')
        if not os.path.exists(path):
            # 尝试查找HTML文件
            path = os.path.join(BLOG_DIR, slug + '.html')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return {'type': 'html', 'content': f.read()}
            return {'error': '文章不存在'}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        meta = self.parse_frontmatter(content)
        return {
            'slug': slug,
            'title': meta.get('title', slug),
            'date': meta.get('date', datetime.now().strftime('%Y-%m-%d')),
            'category': meta.get('category', '其他'),
            'tags': meta.get('tags', []),
            'content': content,
        }
    
    def get_categories(self):
        """获取分类列表"""
        cats = {}
        for f in os.listdir(BLOG_DIR):
            if f.endswith('.md'):
                path = os.path.join(BLOG_DIR, f)
                with open(path, 'r', encoding='utf-8') as fp:
                    meta = self.parse_frontmatter(fp.read())
                cat = meta.get('category', '其他')
                cats[cat] = cats.get(cat, 0) + 1
        return {'categories': cats}
    
    def get_tags(self):
        """获取标签列表"""
        return {'tags': TAGS}
    
    def get_stats(self):
        """获取统计数据"""
        md_count = len([f for f in os.listdir(BLOG_DIR) if f.endswith('.md')])
        html_count = len([f for f in os.listdir(BLOG_DIR) if f.endswith('.html')])
        stock_count = len([f for f in os.listdir(KLINE_DIR) if f.endswith('.json')]) if os.path.exists(KLINE_DIR) else 0
        return {
            'posts': md_count,
            'courses': html_count,
            'stocks': stock_count,
        }
    
    def get_stock_data(self, code):
        """获取股票数据"""
        path = os.path.join(KLINE_DIR, code + '.json')
        if not os.path.exists(path):
            return {'error': '股票数据不存在'}
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 返回最近60日数据
        recent = data.get('klines', [])[-60:] if 'klines' in data else []
        return {
            'code': code,
            'name': data.get('name', code),
            'recent': recent,
        }
    
    def get_backtest(self, params):
        """获取回测数据"""
        symbol = params.get('symbol', ['sh603516'])[0]
        strategy = params.get('strategy', ['all'])[0]
        
        # 这里可以调用回测引擎
        # 暂时返回模拟数据
        return {
            'symbol': symbol,
            'strategy': strategy,
            'strategies': {
                'golden_line': {'win_rate': 66.7, 'total': 15, 'valid': 10, 'invalid': 5, 'hits': []},
                'price_level': {'win_rate': 72.0, 'total': 25, 'valid': 18, 'invalid': 7},
            }
        }
    
    def search_posts(self, keyword):
        """搜索文章"""
        results = []
        for f in os.listdir(BLOG_DIR):
            if not f.endswith('.md'):
                continue
            path = os.path.join(BLOG_DIR, f)
            with open(path, 'r', encoding='utf-8') as fp:
                content = fp.read()
            
            if keyword.lower() in content.lower():
                meta = self.parse_frontmatter(content)
                results.append({
                    'slug': f.replace('.md', ''),
                    'title': meta.get('title', f),
                    'date': meta.get('date', ''),
                    'category': meta.get('category', '其他'),
                })
        
        return {'results': results}
    
    def parse_frontmatter(self, content):
        """解析Markdown frontmatter"""
        meta = {
            'title': '',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'category': '其他',
            'tags': [],
        }
        
        # 检查frontmatter格式 (--- yaml ---)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                yaml_content = parts[1]
                for line in yaml_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'title':
                            meta['title'] = value
                        elif key == 'date':
                            meta['date'] = value
                        elif key == 'category':
                            meta['category'] = value
                        elif key == 'tags' and value.startswith('['):
                            import re
                            tags = re.findall(r'"([^"]+)"', value)
                            meta['tags'] = tags
        
        return meta
    
    def extract_excerpt(self, content):
        """提取文章摘要"""
        # 移除frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            content = parts[2] if len(parts) > 2 else content
        
        # 移除markdown标题
        lines = content.split('\n')
        text = ' '.join([l.strip() for l in lines if not l.startswith('#')])
        # 清理特殊字符
        text = re.sub(r'[#*`>\-|]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:150] + '...' if len(text) > 150 else text
    
    def serve_static(self, filepath):
        """提供静态文件"""
        fullpath = os.path.join(BLOG_DIR, filepath)
        if os.path.exists(fullpath) and os.path.isfile(fullpath):
            ext = os.path.splitext(fullpath)[1].lower()
            content_types = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.svg': 'image/svg+xml',
            }
            ctype = content_types.get(ext, 'application/octet-stream')
            
            with open(fullpath, 'rb') as f:
                data = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f'量学实战博客服务启动: http://localhost:{port}')
    server = HTTPServer(('0.0.0.0', port), BlogHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.shutdown()


if __name__ == '__main__':
    main()
