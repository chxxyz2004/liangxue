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
  8. 概念板块资金流向（akshare）
  9. 行业板块资金流向（akshare）
  10. 个股主力资金流向kline（东财push2 API）
  11. 北向资金持股明细（akshare）
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
FUND_FLOW_DIR = os.path.join(BASE_DIR, 'fund_flow')

os.makedirs(QUOTES_DIR, exist_ok=True)
os.makedirs(LHB_DIR, exist_ok=True)
os.makedirs(NORTH_DIR, exist_ok=True)
os.makedirs(MARGIN_DIR, exist_ok=True)
os.makedirs(RESTRICT_DIR, exist_ok=True)
os.makedirs(FINANCIAL_DIR, exist_ok=True)
os.makedirs(MARKET_DIR, exist_ok=True)
os.makedirs(FUND_FLOW_DIR, exist_ok=True)

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
                'pe': float(fields[46]) if len(fields) > 46 and fields[46] else None,  # PE-TTM
                'pb': float(fields[65]) if len(fields) > 65 and fields[65] else None,  # PB
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
    """从akshare获取北向资金
    注意: 最近数据可能有NaN字段，需标注数据质量
    """
    print('\n=== 北向资金 ===')
    try:
        import akshare as ak
        df = ak.stock_hsgt_hist_em(symbol='北向资金')
        
        # 检查数据质量
        latest_dates = df.tail(10)['日期'].tolist() if len(df) >= 10 else df['日期'].tolist()
        nan_fields = ['当日成交净买额', '买入成交额', '卖出成交额']
        quality_issues = []
        
        for _, row in df.tail(5).iterrows():
            for field in nan_fields:
                if pd.isna(row.get(field)):
                    quality_issues.append(f"{row['日期']}: {field}为NaN")
                    break
        
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
            'latest_dates': latest_dates,
            'quality_issues': quality_issues[:3],  # 最多记录3个问题
            'latest': records,
        }
        path = os.path.join(NORTH_DIR, 'history.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'北向资金: {len(df)}条历史')
        if quality_issues:
            print(f'数据质量问题: {len(quality_issues)}条记录异常')
        return data
    except Exception as e:
        print(f'北向资金失败: {e}')
        return None


def fetch_margin():
    """从akshare获取融资融券
    注意: akshare接口可能返回滞后数据，需标注数据日期
    """
    print('\n=== 融资融券 ===')
    try:
        import akshare as ak
        df_sh = ak.stock_margin_detail_sse()
        df_sz = ak.stock_margin_detail_szse()
        
        # 检查数据日期
        sh_latest_date = df_sh['信用交易日期'].max() if len(df_sh) > 0 else '未知'
        
        data = {
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_date': str(sh_latest_date),  # 记录实际数据日期
            'sh_count': len(df_sh),
            'sz_count': len(df_sz),
            'sh_latest': json.loads(df_sh.tail(3).to_json(orient='records', force_ascii=False)),
            'sz_latest': json.loads(df_sz.tail(3).to_json(orient='records', force_ascii=False)),
        }
        path = os.path.join(MARGIN_DIR, f'{TODAY}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'沪市融资融券: {len(df_sh)}条, 深市: {len(df_sz)}条')
        print(f'数据日期: {sh_latest_date}')
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
                print(f"  {code}: ROE={results[code]['roe']}%, 营收={results[code]['revenue']:.0f}元({results[code]['revenue']/1e8:.2f}亿)")
            time.sleep(0.3)
        except Exception as e:
            print(f"  {code}: 失败 - {e}")

    data = {'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'data': results}
    path = os.path.join(FINANCIAL_DIR, f'{TODAY}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return results


def fetch_concept_fund_flow():
    """从akshare获取概念板块资金流向"""
    print('\n=== 概念板块资金流向 ===')
    try:
        import akshare as ak
        df = ak.stock_fund_flow_concept()
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
            'data': records,
        }
        path = os.path.join(FUND_FLOW_DIR, f'concept_{TODAY}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'概念板块: {len(df)}条')
        # 筛选持仓股相关概念
        relevant_keywords = ['AI', '算力', '光模块', '半导体', '芯片', '通信', '电子', '机器人', 'PCB', '液冷', '数据中心']
        matched = [r for r in records if any(kw in str(r.get('行业', '')) for kw in relevant_keywords)]
        print(f'相关概念({len(matched)}条):')
        for r in sorted(matched, key=lambda x: float(x.get('净额') or 0), reverse=True)[:10]:
            print(f"  {r.get('行业','?')}: 涨跌{r.get('行业-涨跌幅','?')}% 净额{r.get('净额','?')}亿")
        return data
    except Exception as e:
        print(f'概念板块资金流向失败: {e}')
        return None


def fetch_industry_fund_flow():
    """从akshare获取行业板块资金流向"""
    print('\n=== 行业板块资金流向 ===')
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator='今日', sector_type='行业资金流')
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
            'data': records,
        }
        path = os.path.join(FUND_FLOW_DIR, f'industry_{TODAY}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
        print(f'行业板块: {len(df)}条')
        # 筛选持仓股相关行业
        relevant_keywords = ['电子', '通信', '计算机', '半导体', '芯片', '机械']
        matched = [r for r in records if any(kw in str(r.get('行业', '')) for kw in relevant_keywords)]
        print(f'相关行业({len(matched)}条):')
        for r in sorted(matched, key=lambda x: float(x.get('净额') or 0), reverse=True)[:10]:
            print(f"  {r.get('行业','?')}: 涨跌{r.get('行业-涨跌幅','?')}% 净额{r.get('净额','?')}亿")
        return data
    except Exception as e:
        print(f'行业板块资金流向失败: {e}')
        return None


def fetch_individual_fund_flow():
    """从东财push2 API获取个股主力资金流向kline数据"""
    print('\n=== 个股主力资金流向 ===')
    stock_map = {
        'sh603516': '1.603516',
        'sh601138': '1.601138',
        'sz002156': '0.002156',
        'sh601231': '1.601231',
        'sz300476': '0.300476',
        'sh603283': '1.603283',
        'sz300394': '0.300394',
        'sh600584': '1.600584',
    }
    results = {}
    for sym, secid in stock_map.items():
        success = False
        for retry in range(5):
            try:
                url = (
                    f"https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
                    f"?lmt=0&klt=101&secid={secid}"
                    f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
                )
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://quote.eastmoney.com/',
                    'Accept': '*/*',
                })
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                kl = data.get('data', {}).get('klines', [])
                if kl:
                    # 解析: date,主力净流入,小单净流入,中单净流入,大单净流入,超大单净流入
                    parsed = []
                    for kline in kl:
                        parts = kline.split(',')
                        if len(parts) >= 6:
                            try:
                                parsed.append({
                                    'date': parts[0],
                                    'net_main': float(parts[1]) / 10000,  # 万->亿
                                    'net_small': float(parts[2]) / 10000,
                                    'net_medium': float(parts[3]) / 10000,
                                    'net_big': float(parts[4]) / 10000,
                                    'net_super': float(parts[5]) / 10000,
                                })
                            except (ValueError, IndexError):
                                pass
                    results[sym] = parsed
                    print(f'  {sym}: {len(parsed)}条K线, 最新={parsed[-1]["date"] if parsed else "N/A"}')
                    success = True
                    break
                else:
                    print(f'  {sym}: 无数据返回')
                    break
            except Exception as e:
                if retry < 4:
                    wait = (retry + 1) * 1.5
                    print(f'  {sym}: 重试{retry+1}/5 ({wait:.1f}s后) - {str(e)[:50]}')
                    time.sleep(wait)
                else:
                    print(f'  {sym}: 失败 - {e}')
                    results[sym] = None
            time.sleep(0.3)
        if not success and sym not in results:
            results[sym] = None

    data = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stocks': results,
    }
    path = os.path.join(FUND_FLOW_DIR, f'individual_{TODAY}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
    print(f'个股资金流向: 成功{sum(1 for v in results.values() if v)}/{len(results)}只')
    return data


def fetch_north_holdings():
    """从akshare获取北向资金持股明细"""
    print('\n=== 北向资金持股明细 ===')
    stock_map = {
        'sh603516': '603516',
        'sh601138': '601138',
        'sz002156': '002156',
        'sh601231': '601231',
        'sz300476': '300476',
        'sh603283': '603283',
        'sz300394': '300394',
        'sh600584': '600584',
    }
    results = {}
    try:
        import akshare as ak
        for sym, code in stock_map.items():
            try:
                df = ak.stock_hsgt_individual_em(symbol=code)
                if df is None:
                    results[sym] = {'error': '接口返回None', 'record_count': 0}
                    print(f'  {sym}: 接口返回None（该股无北水持股数据）')
                    time.sleep(0.3)
                    continue
                if len(df) > 0:
                    latest = df.iloc[-1]
                    results[sym] = {
                        'name': HOLDINGS.get(sym, WATCH_LIST.get(sym, INDEXES.get(sym, {}))).get('name', sym) if hasattr(HOLDINGS.get(sym), 'name') else sym,
                        'latest_date': str(latest.get('持股日期', '')),
                        'latest_shares': float(latest.get('持股数量', 0)) if pd.notna(latest.get('持股数量')) else None,
                        'latest_value': float(latest.get('持股市值', 0)) if pd.notna(latest.get('持股市值')) else None,
                        'latest_pct': float(latest.get('持股数量占A股百分比', 0)) if pd.notna(latest.get('持股数量占A股百分比')) else None,
                        'record_count': len(df),
                        'data_quality': '过期' if '2024' in str(latest.get('持股日期', '')) else '正常',
                    }
                    print(f'  {sym}: 最新={results[sym]["latest_date"]} 持股{results[sym]["latest_shares"]:.0f}股 市值{results[sym]["latest_value"]:.0f}元')
                else:
                    results[sym] = {'error': '无数据', 'record_count': 0}
                    print(f'  {sym}: 无数据')
            except Exception as e:
                results[sym] = {'error': str(e), 'record_count': 0}
                print(f'  {sym}: 失败 - {e}')
            time.sleep(0.3)
    except Exception as e:
        print(f'北向资金持股采集失败: {e}')
        return None

    data = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data': results,
    }
    path = os.path.join(FUND_FLOW_DIR, f'north_holdings_{TODAY}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=json_serial)
    return data


def main():
    print(f'数据全量采集 {TODAY}')
    print('=' * 50)

    # 1. PE/PB（最快，优先）
    pe_pb = fetch_pe_pb()

    # 2. 涨跌家数
    market_stats = fetch_market_stats()

    # 3. 龙虎榜
    lhb = fetch_lhb()

    # 4. 北向资金历史汇总
    north = fetch_north_money()

    # 5. 融资融券
    margin = fetch_margin()

    # 6. 限售解禁
    restrictions = fetch_restrictions()

    # 7. 财务指标（较慢）
    financial = fetch_financial()

    # 8. 概念板块资金流向
    concept_flow = fetch_concept_fund_flow()

    # 9. 行业板块资金流向
    industry_flow = fetch_industry_fund_flow()

    # 10. 个股主力资金流向
    individual_flow = fetch_individual_fund_flow()

    # 11. 北向资金持股明细
    north_holdings = fetch_north_holdings()

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
        'concept_flow_count': concept_flow['count'] if concept_flow else 0,
        'industry_flow_count': industry_flow['count'] if industry_flow else 0,
        'individual_flow_ok': sum(1 for v in (individual_flow.get('stocks', {}) if individual_flow else {}).values() if v) if individual_flow else 0,
        'north_holdings_ok': sum(1 for v in (north_holdings.get('data', {}) if north_holdings else {}).values() if not v.get('error')) if north_holdings else 0,
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
    print(f'  概念板块资金: {summary["concept_flow_count"]}条')
    print(f'  行业板块资金: {summary["industry_flow_count"]}条')
    print(f'  个股资金流向: {summary["individual_flow_ok"]}/8只成功')
    print(f'  北向持股明细: {summary["north_holdings_ok"]}/8只成功')


if __name__ == '__main__':
    main()
