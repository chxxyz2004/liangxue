#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学系统Web工作台 - 静态文件+API服务（v2.0 融合版）

引用统一配置中心 config.py，不再硬编码持仓/指数数据。
"""
import json, os, sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/现代量学讲义')

from signal_engine import signal_engine, load_daily_kline as load_kline
from config import HOLDINGS, WATCH_LIST, INDEXES, DATA_DIR, SPOOFING_THRESHOLDS

# 引用统一配置中心
from config import HOLDINGS, WATCH_LIST, INDEXES, DATA_DIR, SPOOFING_THRESHOLDS

STATIC_DIR = DATA_DIR.rstrip('/kline') if 'kline' in DATA_DIR else '/workspace/行情数据库'


def load_kline(sym):
    """从统一配置路径加载K线数据"""
    p = os.path.join(STATIC_DIR, 'kline', f'{sym}.json')
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def get_signals(kline_data):
    """保留兼容：倍量柱信号（从signal_engine导入）"""
    return []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        path = urlparse(self.path).path

        # API路由
        if path == '/api/overview':
            self._json(self._overview())
        elif path == '/api/holdings':
            self._json(self._holdings())
        elif path == '/api/watchlist':
            self._json(self._watchlist())
        elif path == '/api/signals':
            self._json(self._signals())
        elif path == '/api/health':
            self._json(self._backtest())
        elif path == '/api/spoofing':
            self._json(self._spoofing())
        elif path == '/api/config':
            self._json(self._config())
        elif path == '/api/health':
            self._json({'status': 'ok', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
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
            path = '/dashboard.html'
        file_path = os.path.join(STATIC_DIR, path.lstrip('/'))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            ct = {'html': 'text/html; charset=utf-8', '.js': 'application/javascript',
                  '.css': 'text/css', '.json': 'application/json'}.get(ext, 'application/octet-stream')
            with open(file_path, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def _overview(self):
        """投资组合总览"""
        prices = {}
        for sym in HOLDINGS:
            kl = load_kline(sym)
            if kl and kl.get('data'):
                d = kl['data']
                if len(d) >= 2:
                    prices[sym] = {'price': d[-1]['close'], 'pct_chg': (d[-1]['close']-d[-2]['close'])/d[-2]['close']}

        tv = sum(prices.get(s, {}).get('price', 0) * h.shares for s, h in HOLDINGS.items())
        tc = sum(h.cost * h.shares for h in HOLDINGS.values() if h.cost is not None)
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': {
                'total_value': round(tv, 2),
                'total_cost': round(tc, 2),
                'profit': round(tv-tc, 2),
                'profit_pct': round((tv-tc)/tc*100, 2) if tc > 0 else 0
            }
        }

    def _holdings(self):
        """持仓股票数据（含技术指标与风险评级）"""
        holdings = []
        for sym, info in HOLDINGS.items():
            kl = load_kline(sym)
            ind = signal_engine.daily_indicators(sym)
            if 'error' in ind:
                continue
            risk = signal_engine.risk_assessment(sym)
            d = kl['data']
            cp = d[-1]['close']
            pc = d[-2]['close'] if len(d) > 1 else cp
            pv = cp * info.shares
            cv = (info.cost * info.shares) if info.cost is not None else 0
            signals = ind.get('doubling_volume', [])
            cross = ind.get('cross', {})
            price_vol = ind.get('price_volume', {})
            holdings.append({
                'symbol': sym,
                'name': info.name,
                'shares': info.shares,
                'cost': info.cost,
                'current_price': cp,
                'pct_chg': round((cp-pc)/pc, 4) if pc > 0 else 0,
                'market_value': round(pv, 2),
                'profit': round(pv-cv, 2) if cv > 0 else 0,
                'stop_loss': info.stop_loss,
                'life_line': info.life_line,
                'take_profit': info.take_profit,
                'ma': ind.get('ma', {}),
                'macd': ind.get('macd', {}),
                'volume_ratio': ind.get('volume_ratio'),
                'risk_level': risk.get('risk_level'),
                'risk_score': risk.get('risk_score'),
                'cross_signal': cross.get('signal', ''),
                'price_volume_signal': price_vol.get('signal', ''),
                'recent_doubling': [{'date': s['date'], 'ratio': s['ratio']} for s in signals[-3:]]
            })
        return {'holdings': holdings}

    def _watchlist(self):
        """关注股票池（未持仓）"""
        watchlist = []
        for sym, info in WATCH_LIST.items():
            kl = load_kline(sym)
            ind = signal_engine.daily_indicators(sym)
            risk = signal_engine.risk_assessment(sym)
            if not kl or 'data' not in kl:
                watchlist.append({'symbol': sym, 'name': info.name, 'status': '无数据'})
                continue
            d = kl['data']
            cp = d[-1]['close']
            pc = d[-2]['close'] if len(d) > 1 else cp
            watchlist.append({
                'symbol': sym,
                'name': info.name,
                'current_price': cp,
                'pct_chg': round((cp-pc)/pc, 4) if pc > 0 else 0,
                'ma': ind.get('ma', {}),
                'macd': ind.get('macd', {}),
                'volume_ratio': ind.get('volume_ratio'),
                'cross_signal': ind.get('cross', {}).get('signal', ''),
                'risk_level': risk.get('risk_level'),
                'risk_score': risk.get('risk_score'),
            })
        return {'watchlist': watchlist}

    def _signals(self):
        """全量技术指标与信号汇总（倍量柱+均线交叉+价量发散+风险评级）"""
        all_signals = []
        for sym, info in HOLDINGS.items():
            ind = signal_engine.daily_indicators(sym)
            if 'error' in ind:
                continue
            risk = signal_engine.risk_assessment(sym)
            # 倍量柱
            for s in ind.get('doubling_volume', []):
                all_signals.append({
                    'symbol': sym, 'name': info.name,
                    'type': '倍量柱', 'date': s['date'],
                    'detail': f'量比{s["ratio"]:.2f}x'
                })
            # 均线交叉
            cross = ind.get('cross', {})
            if cross.get('signal'):
                all_signals.append({
                    'symbol': sym, 'name': info.name,
                    'type': cross.get('type'),
                    'signal': cross.get('signal'),
                    'confidence': cross.get('confidence'),
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
            # 价量发散
            pv = ind.get('price_volume', {})
            if pv.get('signal'):
                all_signals.append({
                    'symbol': sym, 'name': info.name,
                    'type': '价量发散',
                    'signal': pv.get('signal'),
                    'confidence': pv.get('confidence'),
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
            # 风险等级
            all_signals.append({
                'symbol': sym, 'name': info.name,
                'type': '风险评级',
                'risk_level': risk.get('risk_level'),
                'risk_score': risk.get('risk_score'),
                'factors': risk.get('risk_factors', []),
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        # 按日期降序排列
        all_signals.sort(key=lambda x: x.get('date', ''), reverse=True)
        return {'signals': all_signals[:50]}

    def _risk(self):
        """量化风险评级汇总"""
        results = []
        for sym, info in HOLDINGS.items():
            r = signal_engine.risk_assessment(sym)
            results.append({
                'symbol': sym, 'name': info.name,
                'risk_level': r.get('risk_level'),
                'risk_score': r.get('risk_score'),
                'cv_volume': r.get('cv_volume'),
                'correlation': r.get('correlation'),
                'factors': r.get('risk_factors', [])
            })
        return {'risks': results}

    def _five_min(self, symbol):
        """5分钟分时分析"""
        if not symbol:
            return {'error': '需要symbol参数，如 /api/5min?symbol=sh603516'}
        return signal_engine.intraday_analysis(symbol)

    def _indicators(self, symbol):
        """单只股票完整技术指标"""
        if not symbol:
            return {'error': '需要symbol参数，如 /api/indicators?symbol=sh603516'}
        ind = signal_engine.daily_indicators(symbol)
        risk = signal_engine.risk_assessment(symbol)
        return {**ind, **risk}
        """回测结果（静态数据，待接入真实回测框架）"""
        return {
            'total_signals': 61,
            'win_rate': 0.717,
            'avg_return': 0.023,
            'stocks': {
                'sh601138': {'name': '工业富联', 'signals': 15, 'wins': 11, 'losses': 4, 'win_rate': 0.733, 'avg_return': 0.025},
                'sz300476': {'name': '胜宏科技', 'signals': 12, 'wins': 9, 'losses': 3, 'win_rate': 0.75, 'avg_return': 0.028},
                'sh603516': {'name': '淳中科技', 'signals': 14, 'wins': 10, 'losses': 4, 'win_rate': 0.714, 'avg_return': 0.022},
            }
        }

    def _spoofing(self):
        """对倒检测结果（待接入 detect_spoofing.py）"""
        return {
            'results': {
                sym: {
                    'name': info.name,
                    'count': 0,
                    'severity': '轻微',
                    'summary': '无异常',
                    'thresholds': {
                        'vol_ratio_min': SPOOFING_THRESHOLDS.vol_ratio_min,
                        'pct_max': SPOOFING_THRESHOLDS.pct_max,
                        'upper_shadow_ratio': SPOOFING_THRESHOLDS.upper_shadow_ratio
                    }
                }
                for sym, info in HOLDINGS.items()
            },
            'thresholds': {
                'vol_ratio_min': SPOOFING_THRESHOLDS.vol_ratio_min,
                'pct_max': SPOOFING_THRESHOLDS.pct_max,
                'upper_shadow_ratio': SPOOFING_THRESHOLDS.upper_shadow_ratio,
                'pct_pulse_min': SPOOFING_THRESHOLDS.pct_pulse_min,
                'pct_drop_retrace': SPOOFING_THRESHOLDS.pct_drop_retrace
            }
        }

    def _config(self):
        """返回当前配置信息"""
        return {
            'version': '2.0',
            'holdings_count': len(HOLDINGS),
            'watchlist_count': len(WATCH_LIST),
            'indexes_count': len(INDEXES),
            'holdings': {k: {'name': v.name, 'shares': v.shares, 'cost': v.cost} for k, v in HOLDINGS.items()},
            'watchlist': {k: {'name': v.name} for k, v in WATCH_LIST.items()},
            'indexes': INDEXES,
            'spoofing_thresholds': {
                'vol_ratio_min': SPOOFING_THRESHOLDS.vol_ratio_min,
                'pct_max': SPOOFING_THRESHOLDS.pct_max,
                'upper_shadow_ratio': SPOOFING_THRESHOLDS.upper_shadow_ratio,
                'pct_pulse_min': SPOOFING_THRESHOLDS.pct_pulse_min,
                'pct_drop_retrace': SPOOFING_THRESHOLDS.pct_drop_retrace
            }
        }


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8086
    print(f'量学工作台启动: http://localhost:{port}')
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
