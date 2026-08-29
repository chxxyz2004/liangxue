#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人量化交易系统 - 数据自动更新脚本
每日定时运行，更新行情数据和信号
"""
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_PATH = '/workspace/行情数据库/liangxue_system.db'
KLINE_DIR = '/workspace/行情数据库/kline'

# 从config导入持仓和关注池
try:
    from config import HOLDINGS, WATCH_LIST, INDEXES
except ImportError:
    HOLDINGS = {'sh601138': '工业富联', 'sz300476': '胜宏科技', 'sz300394': '天孚通信',
                'sh603516': '淳中科技', 'sz002156': '通富微电', 'sh600584': '长电科技',
                'sh603283': '赛腾股份', 'sh601231': '环旭电子'}
    WATCH_LIST = {}
    INDEXES = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指'}

# ========== 数据获取函数 ==========

def fetch_sina_kline(code, count=100):
    """从新浪获取K线数据（已验证可用）"""
    import urllib.request
    import ssl
    
    url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?' \
          f'symbol={code}&scale=240&ma=no&datalen={count}'
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = resp.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        print(f"  [新浪错误] {code}: {e}")
        return []


def fetch_tencent_quote(codes):
    """从腾讯qt接口获取实时行情"""
    import urllib.request
    
    url = f'https://qt.gtimg.cn/q={",".join(codes)}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('gbk')
            
        result = {}
        for line in raw.strip().split('\n'):
            if '=' not in line:
                continue
            code = line.split('=')[0].split('_')[-1]
            fields = line.split('"')[1].split('~')
            if len(fields) > 5:
                try:
                    result[code] = {
                        'name': fields[1],
                        'price': float(fields[3]) if fields[3] else 0,
                        'high': float(fields[33]) if len(fields) > 33 and fields[33] else 0,
                        'low': float(fields[34]) if len(fields) > 34 and fields[34] else 0,
                        'volume': float(fields[6]) if len(fields) > 6 and fields[6] else 0,
                    }
                except:
                    pass
        return result
    except Exception as e:
        print(f"  [腾讯错误] {e}")
        return {}


def fetch_pe_pb(codes):
    """从腾讯qt接口获取PE/PB"""
    import urllib.request
    
    url = f'https://qt.gtimg.cn/q={",".join(codes)}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('gbk')
            
        result = {}
        for line in raw.strip().split('\n'):
            if '=' not in line or '"' not in line:
                continue
            # 格式: v_sh601138="1~工业富联~601138~64.04~..."
            code_part = line.split('=')[0]  # v_sh601138
            code = code_part.split('_')[-1]  # sh601138
            # 提取引号内的数据
            data_str = line.split('"')[1] if '"' in line else ''
            fields = data_str.split('~')
            if len(fields) > 65:
                try:
                    result[code] = {
                        'pe_ttm': float(fields[46]) if fields[46] else None,
                        'pb': float(fields[65]) if fields[65] else None,
                        'total_market_cap': float(fields[44]) if len(fields) > 44 and fields[44] else None,
                    }
                except:
                    pass
        return result
    except Exception as e:
        return {}


def update_kline_from_sina(conn, code):
    """从新浪更新K线数据"""
    cursor = conn.cursor()
    
    # 获取新浪数据
    klines = fetch_sina_kline(code, count=200)
    if not klines:
        return 0
    
    # 查找最新日期
    cursor.execute("SELECT MAX(date) FROM daily_kline WHERE code = ?", (code,))
    row = cursor.fetchone()
    last_date = row[0] if row else '1900-01-01'
    
    if not last_date or last_date == 'None':
        last_date = '1900-01-01'
    
    # 插入新数据
    inserted = 0
    for bar in klines:
        date_str = bar.get('day', '')
        if date_str > last_date:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_kline 
                    (code, date, open, high, low, close, volume, amount, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sina')
                ''', (
                    code,
                    date_str,
                    float(bar.get('open', 0)),
                    float(bar.get('high', 0)),
                    float(bar.get('low', 0)),
                    float(bar.get('close', 0)),
                    int(float(bar.get('volume', 0))),
                    int(float(bar.get('volume', 0)) * float(bar.get('close', 0)) / 100000000),
                ))
                inserted += 1
            except:
                pass
    
    conn.commit()
    return inserted


def update_stock_info(conn, pe_data):
    """更新股票基本信息（PE/PB等）"""
    cursor = conn.cursor()
    
    for code, info in pe_data.items():
        cursor.execute("SELECT code FROM stocks WHERE code = ?", (code,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE stocks SET pe_ttm = ?, pb = ?, total_market_cap = ?
                WHERE code = ?
            ''', (info.get('pe_ttm'), info.get('pb'), info.get('total_market_cap'), code))
    
    conn.commit()
    
    # 如果没有pe_ttm列，直接忽略基本面更新
    try:
        cursor.execute("SELECT pe_ttm FROM stocks LIMIT 1")
    except:
        print("  [提示] stocks表无pe_ttm列，基本面数据暂不更新")


def update_all_klines():
    """更新所有股票的K线数据"""
    conn = sqlite3.connect(DB_PATH)
    total_inserted = 0
    
    print(f"\n[数据更新] 开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 合并持仓、关注列表和指数
    all_codes = list(HOLDINGS.keys()) + list(WATCH_LIST.keys()) + list(INDEXES.keys())
    
    # 更新K线
    for code in all_codes:
        inserted = update_kline_from_sina(conn, code)
        if inserted > 0:
            print(f"  [更新] {code} +{inserted}根K线")
        time.sleep(0.2)  # 避免请求过快
        total_inserted += inserted
    
    # 更新PE/PB
    pe_data = fetch_pe_pb(all_codes)
    if pe_data:
        update_stock_info(conn, pe_data)
        print(f"  [PE/PB] 更新 {len(pe_data)} 只股票基本面")
    
    conn.close()
    print(f"\n[数据更新] 完成，共更新 {total_inserted} 根K线")
    return total_inserted


# ========== 信号生成 ==========

def generate_daily_signals(conn):
    """生成每日量学信号"""
    from liangxue_engine import KeyBarDetector, VolumeBarDetector
    
    cursor = conn.cursor()
    
    # 获取最近有数据的股票
    cursor.execute("""
        SELECT DISTINCT code FROM daily_kline 
        WHERE date >= date('now', '-60 days')
        ORDER BY code
    """)
    codes = [row[0] for row in cursor.fetchall()]
    
    signals_generated = 0
    
    for code in codes:
        # 获取最近80根K线
        cursor.execute("""
            SELECT date, open, high, low, close, volume 
            FROM daily_kline 
            WHERE code = ? 
            ORDER BY date DESC 
            LIMIT 80
        """, (code,))
        rows = cursor.fetchall()
        
        if len(rows) < 30:
            continue
        
        # 构建K线数据
        kl = []
        for row in reversed(rows):
            kl.append({
                'day': row[0],
                'open': row[1],
                'high': row[2],
                'low': row[3],
                'close': row[4],
                'volume': row[5],
            })
        
        # 检测倍量柱
        vol_detector = VolumeBarDetector()
        vol_result = vol_detector.detect_all(kl)
        
        # 检测关键柱
        key_detector = KeyBarDetector()
        key_result = key_detector.detect_all(kl)
        
        # 插入信号（去重）
        for bar_type in ['doubling_bars', 'golden_bars', 'marshal_bars', 'general_bars']:
            bars = key_result.get(bar_type, [])
            for bar in bars[-3:]:  # 只取最近3个
                signal_type = bar_type.replace('_bars', '')
                cursor.execute('''
                    INSERT OR IGNORE INTO liangxue_signals 
                    (code, date, signal_type, bar_type, volume_ratio, drawdown_ratio, key_price, env_score, filter_result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                ''', (
                    code,
                    bar.get('date', bar.get('day', '')),
                    signal_type,
                    bar.get('type', ''),
                    bar.get('ratio', bar.get('volume_ratio', 0)),
                    bar.get('drawdown_ratio', 0),
                    bar.get('high', bar.get('low', 0)),
                    38.0,  # 当前环境得分占位符
                ))
                signals_generated += 1
    
    conn.commit()
    print(f"[信号生成] 共生成 {signals_generated} 个新信号")
    return signals_generated


# ========== 主入口 ==========

if __name__ == '__main__':
    print("=" * 60)
    print("  个人量化交易系统 - 数据自动更新")
    print("=" * 60)
    
    # 检查数据库是否存在
    if not os.path.exists(DB_PATH):
        print("[错误] 数据库不存在，请先运行 db_init.py")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 更新K线数据
    update_all_klines()
    
    # 生成信号
    generate_daily_signals(conn)
    
    conn.close()
    
    print("\n[完成] 数据更新已完成")
