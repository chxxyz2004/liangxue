#!/usr/bin/env python3
"""
量学系统 - 综合数据采集脚本
采集范围：
  1. PE/PB（腾讯qt接口）
  2. 涨跌家数（新浪A股列表）
  3. 龙虎榜（东财API）
  4. 北向资金（akshare）
  5. 融资融券（akshare）
  6. 限售解禁（akshare）
  7. 财务指标（akshare）
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, '/workspace/行情数据库')
from config import HOLDINGS, WATCH_LIST, INDEXES

BASE_DIR = '/workspace/行情数据库'
QUOTES_DIR = os.path.join(BASE_DIR, 'quotes')
LHB_DIR = os.path.join(BASE_DIR, 'lhb')
NORTH_DIR = os.path.join(BASE_DIR, 'north_money')
MARGIN_DIR = os.path.join(BASE_DIR, 'margin')
RESTRICT_DIR = os.path.join(BASE_DIR, 'restrictions')
FINANCIAL_DIR = os.path.join(BASE_DIR, 'financial')
MARKET_DIR = os.path.join(BASE_DIR, 'market')

os.makedirs(QUOTES_DIR, exist_ok=True)
os.makedirs(LHB_DIR, exist_ok=True)
os.makedirs(NORTH_DIR, exist_ok=True)
os.makedirs(MARGIN_DIR, exist_ok=True)
os.makedirs(RESTRICT_DIR, exist_ok=True)
os.makedirs(FINANCIAL_DIR, exist_ok=True)
os.makedirs(MARKET_DIR, exist_ok=True)

STOCK_CODES = list({**{k: v.name for k, v in HOLDINGS.items()},
                    **{k: v.name for k, v in WATCH_LIST.items()},
                    **INDEXES}.keys())

TODAY = datetime.now().strftime('%Y-%m-%d')
TODAY_STR = datetime.now().strftime('%Y%m%d')


def fetch_pe_pb():
    """从腾讯qt接口获取PE/PB/总市值"""
    print('\n=== PE/PB 数据 ===')
    codes = ','.join(STOCK_CODES)
    url = f'https://qt.gtimg.cn/q={codes}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req, timeout=15).read().decode('gbk')

    result = {}
    for line in raw.strip().split('\n'):
        if '=' not in line:
            continue
        code = line.split('=')[0].split('_')[-1]
        fields = line.split('"')[1].split('~')
        if len(fields) < 66:
            continue
        try:
            result[code] = {
                'name': fields[1],
                'price': float(fields[3]) if fields[3] else None,
                'pe': float(fields[64]) if len(fields) > 64 and fields[64] else None,
                'pb': float(fields[65]) if len(fields) > 65 and fields[65] else None,
                'total_market_cap_yi': float(fields[44]) if len(fields) > 44 and fields[44] else None,
            }
        except (ValueError, IndexError):
            pass

    data = {'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'data': result}
    path = os.path.join(QUOTES_DIR, 'pe_pb.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'获取 {len(result)} 只股票PE/PB')
    for code, info in result.items():
        print(f"  {code} {info['name']}: PE={info['pe']}, PB={info['pb']}")
    return result


def fetch_market_stats():
    """从新浪获取涨跌家数"""
    print('\n=== 涨跌家数 ===')
    all_data = []
    for page in range(1, 21):
        url = f'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={page}&num=1000&sort=symbol&asc=1&node=hs_a&_s_r_a=page'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            raw = urllib.request.urlopen(req, timeout=8).read().decode('gbk')
            data = json.loads(raw)
            if not data:
                break
            all_data.extend(data)
        except:
            break

    up = sum(1 for d in all_data if float(d.get('changepercent', 0)) > 0)
    down = sum(1 for d in all_data if float(d.get('changepercent', 0)) < 0)
    flat = sum(1 for d in all_data if float(d.get('changepercent', 0)) == 0)
    limit_up = sum(1 for d in all_data if float(d.get('changepercent', 0)) >= 9.9)
    limit_down = sum(1 for d in all_data if float(d.get('changepercent', 0)) <= -9.9)

    stats = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(all_data),
        'up': up,
        'down': down,
        'flat': flat,
        'limit_up': limit_up,
        'limit_down': limit_down,
    }

    path = os.path.join(MARKET_DIR, 'stats.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f'A股: 涨{up} 跌{down} 平{flat} 涨停{limit_up} 跌停{limit_down} 总{len(all_data)}')
    return stats


def json_serial(obj):
    """JSON序列化辅助"""
    if isinstance(obj, (datetime,)):
        return obj.strftime('%Y-%m-%d')
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def fetch_lhb():
    """从东财获取龙虎榜数据"""
    print('\n=== 龙虎榜 ===')
    try:
        import akshare as ak
        df = ak.stock_lhb_detail_em(start_date=(datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                                      end_date=TODAY_STR)
        records = []
        for _, row in df.iterrows():
            record = {}
            for k, v in row.items():
                try:
                    record[k] = float(v) if pd.notna(v) and isinstance(v, (int, float)) else str(v) if v is not None else None
                except:
                    record[k] = str(v) if v is not None else None
            records.append(record)
        data = {
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(df),
            'data': records[:500],
        }
        path = os.path.join(LHB_DIR, f'{TODAY}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'龙虎榜: {len(df)}条')
        return data
    except Exception as e:
        print(f'龙虎榜失败: {e}')
        return None


def fetch_north_money():
    """从akshare获取北向资金"""
    print('\n=== 北向资金 ===')
    try:
        import akshare as ak
        df = ak.stock_hsgt_hist_em(symbol='北向资金')
        records = []
        for _, row in df.tail(20).iterrows():
            record = {}
            for k, v in row.items():
                try:
                    record[k] = float(v) if pd.notna(v) and isinstance(v, (int, float)) else str(v) if v is not None else None
                except:
                    record[k] = str(v) if v is not None else None
            records.append(record)
        data = {
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(df),
            'latest': records,
        }
        path = os.path.join(NORTH_DIR, 'history.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'北向资金: {len(df)}条历史')
        return data
    except Exception as e:
        print(f'北向资金失败: {e}')
        return None


def fetch_margin():
    """从akshare获取融资融券"""
    print('\n=== 融资融券 ===')
    try:
        import akshare as ak
        df_sh = ak.stock_margin_detail_sse()
        df_sz = ak.stock_margin_detail_szse()
        data = {
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sh_count': len(df_sh),
            'sz_count': len(df_sz),
            'sh_latest': json.loads(df_sh.tail(3).to_json(orient='records', force_ascii=False)),
            'sz_latest': json.loads(df_sz.tail(3).to_json(orient='records', force_ascii=False)),
        }
        path = os.path.join(MARGIN_DIR, f'{TODAY}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'沪市融资融券: {len(df_sh)}条, 深市: {len(df_sz)}条')
        return data
    except Exception as e:
        print(f'融资融券失败: {e}')
        return None


def fetch_restrictions():
    """从akshare获取限售解禁"""
    print('\n=== 限售解禁 ===')
    try:
        import akshare as ak
        df = ak.stock_restricted_release_detail_em(
            start_date=(datetime.now() - timedelta(days=60)).strftime('%Y%m%d'),
            end_date=(datetime.now() + timedelta(days=30)).strftime('%Y%m%d'))
        records = []
        for _, row in df.head(100).iterrows():
            record = {}
            for k, v in row.items():
                try:
                    record[k] = float(v) if pd.notna(v) and isinstance(v, (int, float)) else str(v) if v is not None else None
                except:
                    record[k] = str(v) if v is not None else None
            records.append(record)
        data = {
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(df),
            'data': records,
        }
        path = os.path.join(RESTRICT_DIR, f'{TODAY}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'解禁: {len(df)}条')
        return data
    except Exception as e:
        print(f'解禁失败: {e}')
        return None


def fetch_financial():
    """从akshare获取财务指标"""
    print('\n=== 财务指标 ===')
    results = {}
    for code in STOCK_CODES:
        if not code.startswith('sh') and not code.startswith('sz'):
            continue
        try:
            import akshare as ak
            stock_code = code[2:]
            df = ak.stock_financial_analysis_indicator_em(symbol=f'{stock_code}.SH' if code.startswith('sh') else f'{stock_code}.SZ',
                                                           indicator='按报告期')
            if len(df) > 0:
                latest = df.iloc[0]
                results[code] = {
                    'report_date': str(latest.get('REPORT_DATE', ''))[:10],
                    'eps': float(latest.get('EPSJB', 0)) if pd.notna(latest.get('EPSJB')) else None,
                    'bps': float(latest.get('BPS', 0)) if pd.notna(latest.get('BPS')) else None,
                    'roe': float(latest.get('ROEJQ', 0)) if pd.notna(latest.get('ROEJQ')) else None,
                    'revenue': float(latest.get('TOTALOPERATEREVE', 0)) if pd.notna(latest.get('TOTALOPERATEREVE')) else None,
                    'net_profit': float(latest.get('PARENTNETPROFIT', 0)) if pd.notna(latest.get('PARENTNETPROFIT')) else None,
                }
                print(f"  {code}: ROE={results[code]['roe']}%, 营收={results[code]['revenue']:.0f}万")
            time.sleep(0.3)
        except Exception as e:
            print(f"  {code}: 失败 - {e}")

    data = {'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'data': results}
    path = os.path.join(FINANCIAL_DIR, f'{TODAY}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return results


def main():
    print(f'数据全量采集 {TODAY}')
    print('=' * 50)

    # 1. PE/PB（最快，优先）
    pe_pb = fetch_pe_pb()

    # 2. 涨跌家数
    market_stats = fetch_market_stats()

    # 3. 龙虎榜
    lhb = fetch_lhb()

    # 4. 北向资金
    north = fetch_north_money()

    # 5. 融资融券
    margin = fetch_margin()

    # 6. 限售解禁
    restrictions = fetch_restrictions()

    # 7. 财务指标（较慢）
    financial = fetch_financial()

    # 汇总报告
    summary = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pe_pb_count': len(pe_pb) if pe_pb else 0,
        'market_stats': market_stats,
        'lhb_count': lhb['count'] if lhb else 0,
        'north_count': north['count'] if north else 0,
        'margin_count': (margin['sh_count'] + margin['sz_count']) if margin else 0,
        'restriction_count': restrictions['count'] if restrictions else 0,
        'financial_count': len(financial) if financial else 0,
    }

    summary_path = os.path.join(BASE_DIR, 'data_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'\n采集完成，汇总已保存: {summary_path}')
    print(f'  PE/PB: {summary["pe_pb_count"]}只')
    print(f'  涨跌: 总{summary["market_stats"]["total"]} 涨{summary["market_stats"]["up"]} 跌{summary["market_stats"]["down"]}')
    print(f'  龙虎榜: {summary["lhb_count"]}条')
    print(f'  北向资金: {summary["north_count"]}条')
    print(f'  融资融券: {summary["margin_count"]}条')
    print(f'  限售解禁: {summary["restriction_count"]}条')
    print(f'  财务指标: {summary["financial_count"]}只')


if __name__ == '__main__':
    main()
