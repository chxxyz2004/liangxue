#!/usr/bin/env python3
"""
产业链行情采集
从腾讯qt接口批量获取产业链成分股实时行情
"""
import json
import os
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, '/workspace/行情数据库')
from industry_chains import INDUSTRY_CHAINS, get_all_chain_stocks

BASE_DIR = '/workspace/行情数据库'
CHAIN_DIR = os.path.join(BASE_DIR, 'industry_chains')
os.makedirs(CHAIN_DIR, exist_ok=True)


def fetch_chain_quotes():
    """获取所有产业链成分股的实时行情"""
    all_stocks = get_all_chain_stocks()
    
    # 构建腾讯qt请求代码
    codes = list(all_stocks)
    qt_codes = []
    for code in codes:
        if code.startswith('sh'):
            qt_codes.append('sh' + code[2:])
        elif code.startswith('sz'):
            qt_codes.append('sz' + code[2:])
    
    url = f'https://qt.gtimg.cn/q={",".join(qt_codes)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        raw = urllib.request.urlopen(req, timeout=15).read().decode('gbk')
    except Exception as e:
        print(f'行情获取失败: {e}')
        return None
    
    # 解析行情数据
    stock_quotes = {}
    for line in raw.strip().split('\n'):
        if '=' not in line:
            continue
        fields = line.split('"')[1].split('~')
        if len(fields) < 35:
            continue
        try:
            qt_code = fields[2]  # 如 603516
            # 根据原始代码映射回完整代码
            stock_quotes[qt_code] = {
                'name': fields[1],
                'price': float(fields[3]) if fields[3] else None,
                'change_pct': float(fields[32]) if len(fields) > 32 and fields[32] else 0,
                'volume': float(fields[6]) if len(fields) > 6 and fields[6] else 0,
                'amount': float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                'high': float(fields[33]) if len(fields) > 33 and fields[33] else 0,
                'low': float(fields[34]) if len(fields) > 34 and fields[34] else 0,
                'open': float(fields[5]) if len(fields) > 5 and fields[5] else 0,
                'prev_close': float(fields[4]) if len(fields) > 4 and fields[4] else 0,
            }
        except (ValueError, IndexError):
            pass
    
    # 将qt_code映射回完整代码
    code_mapping = {}
    for code in codes:
        short = code[2:]  # 去掉sh/sz前缀
        code_mapping[short] = code
    
    final_quotes = {}
    for qt_code, quote in stock_quotes.items():
        full_code = code_mapping.get(qt_code, f'sh{qt_code}')
        final_quotes[full_code] = quote
    
    # 按产业链分组
    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chains': {},
        'all_stocks': final_quotes,
    }
    
    for chain_name, chain_info in INDUSTRY_CHAINS.items():
        chain_stocks = chain_info['stocks']
        stocks_data = []
        total_change = 0
        limit_up = 0
        limit_down = 0
        
        for code, name in chain_stocks.items():
            quote = final_quotes.get(code, {})
            change_pct = quote.get('change_pct', 0)
            stocks_data.append({
                'code': code,
                'name': name,
                'price': quote.get('price'),
                'change_pct': change_pct,
                'volume': quote.get('volume', 0),
                'amount': quote.get('amount', 0),
            })
            total_change += change_pct
            if change_pct >= 9.9:
                limit_up += 1
            elif change_pct <= -9.9:
                limit_down += 1
        
        # 计算板块指数（简单平均涨跌幅）
        avg_change = total_change / len(stocks_data) if stocks_data else 0
        
        result['chains'][chain_name] = {
            'color': chain_info['color'],
            'avg_change': round(avg_change, 2),
            'limit_up': limit_up,
            'limit_down': limit_down,
            'stocks': stocks_data,
        }
    
    # 按板块涨跌幅排序
    sorted_chains = sorted(
        result['chains'].items(),
        key=lambda x: x[1]['avg_change'],
        reverse=True
    )
    result['chains'] = dict(sorted_chains)
    
    return result


def main():
    print(f'产业链行情采集 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)
    
    data = fetch_chain_quotes()
    if not data:
        print('采集失败')
        return 1
    
    # 保存数据
    today = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(CHAIN_DIR, f'{today}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    print(f'采集时间: {data["updated_at"]}')
    print(f'覆盖产业链: {len(data["chains"])}个')
    print()
    print('板块涨幅排行:')
    for i, (chain_name, info) in enumerate(data['chains'].items(), 1):
        print(f'  {i}. {chain_name}: {info["avg_change"]:+.2f}% (涨停{info["limit_up"]} 跌停{info["limit_down"]})')
    
    print()
    print(f'数据已保存: {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
