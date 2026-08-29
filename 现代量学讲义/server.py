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
    
    def end_headers(self):
        """覆盖默认方法，添加禁用缓存头"""
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
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
        # 产业链API路由
        elif path == '/api/industry_chains':
            self.handle_get_industry_chains()
        elif path == '/api/industry_chains/latest':
            self.handle_get_industry_chains_latest()
        # 持仓跟踪API路由
        elif path == '/api/holdings':
            self.handle_get_holdings()
        elif path == '/api/watchlist':
            self.handle_get_watchlist()
        elif path == '/api/signals':
            self.handle_get_signals()
        elif path == '/api/portfolio':
            self.handle_get_portfolio()
        
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
    
    def handle_get_industry_chains(self):
        """获取产业链数据（从文件读取）"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'fetch_chain', '/workspace/行情数据库/fetch_chain_quotes.py')
            # 直接使用已保存的数据
            chain_dir = '/workspace/行情数据库/industry_chains'
            today = datetime.now().strftime('%Y-%m-%d')
            path = os.path.join(chain_dir, f'{today}.json')
            
            if not os.path.exists(path):
                self.send_json({'error': '暂无数据，请先运行 fetch_chain_quotes.py'}, 404)
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.send_json(data)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def handle_get_industry_chains_latest(self):
        """获取最新产业链数据（支持缓存刷新）"""
        try:
            # 导入并运行采集脚本
            sys.path.insert(0, '/workspace/行情数据库')
            from fetch_chain_quotes import fetch_chain_quotes
            data = fetch_chain_quotes()
            
            if not data:
                self.send_json({'error': '数据采集失败'}, 500)
                return
            
            self.send_json(data)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)
    
    # ===== 持仓跟踪API =====
    
    def handle_get_holdings(self):
        """获取持仓数据"""
        try:
            sys.path.insert(0, '/workspace/行情数据库')
            from config import HOLDINGS
            import sqlite3
            import os
            
            DB_PATH = '/workspace/行情数据库/liangxue_system.db'
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            holdings = []
            for sym, info in HOLDINGS.items():
                name = info.name if hasattr(info, 'name') else info.get('name', sym)
                shares = info.shares if hasattr(info, 'shares') else info.get('shares', 0)
                cost = info.cost if hasattr(info, 'cost') else info.get('cost', 0)
                stop_loss = info.stop_loss if hasattr(info, 'stop_loss') else info.get('stop_loss', 0)
                life_line = info.life_line if hasattr(info, 'life_line') else info.get('life_line', 0)
                
                # 获取最新K线
                cursor.execute("""
                    SELECT date, open, high, low, close, volume 
                    FROM daily_kline 
                    WHERE code = ? 
                    ORDER BY date DESC 
                    LIMIT 2
                """, (sym,))
                rows = cursor.fetchall()
                
                if len(rows) >= 1:
                    latest = rows[0]
                    cp = latest[4]  # close
                    pct_chg = ((cp - latest[4]) / latest[4] * 100) if len(rows) > 1 else 0
                    if len(rows) > 1:
                        prev_close = rows[1][4]
                        pct_chg = (cp - prev_close) / prev_close
                    market_value = cp * shares
                    profit = (cp - cost) * shares if cost else 0
                else:
                    cp = 0
                    pct_chg = 0
                    market_value = 0
                    profit = 0
                
                # 获取MA数据
                cursor.execute("""
                    SELECT date, close FROM daily_kline 
                    WHERE code = ? AND date >= date('now', '-60 days')
                    ORDER BY date DESC
                """, (sym,))
                closes = [r[1] for r in cursor.fetchall()[:60]]
                
                ma = {}
                if len(closes) >= 5:
                    ma['ma5'] = sum(closes[:5])/5
                if len(closes) >= 10:
                    ma['ma10'] = sum(closes[:10])/10
                if len(closes) >= 20:
                    ma['ma20'] = sum(closes[:20])/20
                if len(closes) >= 60:
                    ma['ma60'] = sum(closes[:60])/60
                
                holdings.append({
                    'symbol': sym,
                    'name': name,
                    'shares': shares,
                    'cost': cost,
                    'current_price': round(cp, 2),
                    'pct_chg': round(pct_chg, 4),
                    'market_value': round(market_value, 2),
                    'profit': round(profit, 2),
                    'stop_loss': stop_loss,
                    'life_line': life_line,
                    'ma': {k: round(v, 2) for k, v in ma.items()},
                })
            
            conn.close()
            self.send_json({'holdings': holdings})
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def handle_get_watchlist(self):
        """获取关注列表"""
        try:
            sys.path.insert(0, '/workspace/行情数据库')
            from config import WATCH_LIST
            import sqlite3
            
            DB_PATH = '/workspace/行情数据库/liangxue_system.db'
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            watchlist = []
            for sym, info in WATCH_LIST.items():
                name = info.name if hasattr(info, 'name') else info.get('name', sym)
                
                cursor.execute("""
                    SELECT date, close, volume FROM daily_kline 
                    WHERE code = ? ORDER BY date DESC LIMIT 1
                """, (sym,))
                row = cursor.fetchone()
                
                if row:
                    watchlist.append({
                        'symbol': sym,
                        'name': name,
                        'price': row[1],
                        'volume': row[2],
                        'date': row[0],
                    })
            
            conn.close()
            self.send_json({'watchlist': watchlist})
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def handle_get_signals(self):
        """获取量学信号"""
        try:
            import sqlite3
            DB_PATH = '/workspace/行情数据库/liangxue_system.db'
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT code, date, signal_type, bar_type, volume_ratio, key_price
                FROM liangxue_signals 
                WHERE date >= date('now', '-30 days')
                ORDER BY date DESC LIMIT 20
            """)
            signals = []
            for row in cursor.fetchall():
                signals.append({
                    'code': row[0],
                    'date': row[1],
                    'type': row[2],
                    'bar_type': row[3],
                    'volume_ratio': row[4],
                    'key_price': row[5],
                })
            
            conn.close()
            self.send_json({'signals': signals})
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def handle_get_portfolio(self):
        """获取投资组合汇总"""
        try:
            import sqlite3
            sys.path.insert(0, '/workspace/行情数据库')
            from config import HOLDINGS
            
            DB_PATH = '/workspace/行情数据库/liangxue_system.db'
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            total_value = 0
            total_cost = 0
            for sym in HOLDINGS:
                cursor.execute("SELECT close, volume FROM daily_kline WHERE code = ? ORDER BY date DESC LIMIT 1", (sym,))
                row = cursor.fetchone()
                if row:
                    info = HOLDINGS[sym]
                    shares = info.shares if hasattr(info, 'shares') else info.get('shares', 0)
                    cost = info.cost if hasattr(info, 'cost') else info.get('cost', 0)
                    total_value += row[0] * shares
                    total_cost += cost * shares
            
            conn.close()
            
            profit = total_value - total_cost
            profit_pct = (profit / total_cost * 100) if total_cost > 0 else 0
            
            self.send_json({
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
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
    print(f"产业链API: /api/industry_chains")
    print(f"持仓API: /api/holdings")
    print(f"信号API: /api/signals")
    print(f"组合API: /api/portfolio")
    server.serve_forever()
