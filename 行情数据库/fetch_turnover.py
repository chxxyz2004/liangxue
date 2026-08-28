#!/usr/bin/env python3
"""
换手率获取脚本
从腾讯qt接口获取实时换手率数据
"""
import json
import os
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, '/workspace/行情数据库')
from config import HOLDINGS, WATCH_LIST, INDEXES

QT_API = 'https://qt.gtimg.cn/q={codes}'

STOCK_CODES = list({**{k: v.name for k, v in HOLDINGS.items()},
                    **{k: v.name for k, v in WATCH_LIST.items()},
                    **INDEXES}.keys())


def parse_qt_data(raw):
    """解析腾讯qt接口返回的数据"""
    result = {}
    for line in raw.strip().split('\n'):
        if '=' not in line:
            continue
        code = line.split('=')[0].split('_')[-1]
        data_str = line.split('"')[1]
        fields = data_str.split('~')
        
        if len(fields) < 40:
            continue
        
        result[code] = {
            'name': fields[1] if len(fields) > 1 else '',
            'price': float(fields[3]) if len(fields) > 3 and fields[3] else None,
            'volume': int(float(fields[6])) if len(fields) > 6 and fields[6] else 0,  # 手
            'turnover_ratio': float(fields[38]) if len(fields) > 38 and fields[38] else None,  # 换手率%
            'float_shares': int(float(fields[72])) if len(fields) > 72 and fields[72] else None,  # 流通股本(股)
            'amount': float(fields[57]) * 10000 if len(fields) > 57 and fields[57] else None,  # 成交额(万元)→(元)
        }
    return result


def fetch_turnover():
    """获取所有股票的换手率"""
    codes = ','.join(STOCK_CODES)
    url = QT_API.format(codes=codes)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        raw = urllib.request.urlopen(req, timeout=15).read().decode('gbk')
        return parse_qt_data(raw)
    except Exception as e:
        print(f'获取失败: {e}')
        return {}


def save_turnover(data, output_dir):
    """保存换手率数据到文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 保存汇总文件
    summary = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data': data,
    }
    
    summary_file = os.path.join(output_dir, 'turnover.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 保存每只股票的数据
    for code, info in data.items():
        file_path = os.path.join(output_dir, f'{code}_turnover.json')
        stock_data = {
            'code': code,
            'name': info['name'],
            'date': today,
            'turnover_ratio': info['turnover_ratio'],
            'float_shares': info['float_shares'],
            'price': info['price'],
            'volume': info['volume'],
            'amount': info['amount'],
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stock_data, f, ensure_ascii=False, indent=2)
    
    return summary_file


def main():
    output_dir = '/workspace/行情数据库/turnover'
    
    print(f'获取换手率数据 ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
    print('=' * 50)
    
    data = fetch_turnover()
    
    if not data:
        print('无数据')
        return 1
    
    summary_file = save_turnover(data, output_dir)
    
    print(f'\n已保存到: {summary_file}')
    print(f'\n获取到 {len(data)} 只股票数据:')
    for code, info in data.items():
        print(f"  {code} {info['name']}: 换手率={info['turnover_ratio']}%, 流通股本={info['float_shares']:,}股")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
