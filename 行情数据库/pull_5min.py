#!/usr/bin/env python3
"""
5分钟K线入库脚本
每日收盘后运行，将当日5分钟K线存储到本地数据库
"""
import json
import os
import urllib.request
from datetime import datetime

STOCKS = {
    'sh603516': '淳中科技',
    'sh601138': '工业富联',
    'sh603283': '赛腾股份',
    'sz002156': '通富微电',
    'sh601231': '环旭电子',
    'sz300476': '胜宏科技',
    'sh603220': '中贝通信',
    'sh600629': '华建集团',
    'sz300394': '天孚通信',
}

BASE_DIR = '/workspace/行情数据库/kline_5min'
os.makedirs(BASE_DIR, exist_ok=True)

def pull_5min(code):
    """拉取当日5分钟K线"""
    url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=5&ma=no&datalen=48'
    try:
        data = urllib.request.urlopen(url, timeout=10).read().decode('gbk')
        return json.loads(data)
    except Exception as e:
        print(f'  拉取失败 {code}: {e}')
        return []

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f'5分钟K线入库 · {today}')
    print('=' * 50)
    
    for code, name in STOCKS.items():
        bars = pull_5min(code)
        if not bars:
            print(f'{name}: 无数据')
            continue
        
        # 保存文件
        filename = f'{code}_{today}.json'
        filepath = os.path.join(BASE_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump({
                'code': code,
                'name': name,
                'date': today,
                'bars': bars,
                'count': len(bars)
            }, f, ensure_ascii=False, indent=2)
        
        print(f'{name}: {len(bars)}根K线 → {filepath}')
    
    print('=' * 50)
    print('入库完成')

if __name__ == '__main__':
    main()
