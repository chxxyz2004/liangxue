#!/usr/bin/env python3
"""
数据层质量诊断报告 v1.0
诊断时间: 2026-08-29
诊断目标: 确保所有数据真实、可靠、官方、权威
"""
import json
import os
from datetime import datetime

BASE_DIR = '/workspace/行情数据库'
REPORT_PATH = os.path.join(BASE_DIR, 'data_quality_report.json')

# ============================================================
# 数据质量检查项
# ============================================================

def check_kline_data():
    """检查K线数据质量"""
    issues = []
    kline_dir = os.path.join(BASE_DIR, 'kline')
    
    # 检查文件完整性
    expected_files = [
        'sh603516.json', 'sh601138.json', 'sz002156.json',
        'sh601231.json', 'sz300476.json', 'sh603283.json',
        'sz300394.json', 'sh600584.json', 'sh000001.json',
        'sz399001.json', 'sz399006.json'
    ]
    
    for f in expected_files:
        path = os.path.join(kline_dir, f)
        if not os.path.exists(path):
            issues.append({'level': 'ERROR', 'file': f, 'msg': '文件不存在'})
            continue
        
        with open(path) as fp:
            data = json.load(fp)
        
        # 检查数据条数
        count = len(data.get('data', []))
        if count < 300:
            issues.append({'level': 'WARNING', 'file': f, 'msg': f'数据条数不足: {count}'})
        
        # 检查最后一条日期
        if data.get('data'):
            last_date = data['data'][-1].get('day', '')
            if last_date < '2026-08-28':
                issues.append({'level': 'WARNING', 'file': f, 'msg': f'数据过期: {last_date}'})
    
    return issues


def check_pe_pb_data():
    """检查PE/PB数据质量"""
    issues = []
    path = os.path.join(BASE_DIR, 'quotes/pe_pb.json')
    
    if not os.path.exists(path):
        issues.append({'level': 'ERROR', 'msg': 'PE/PB数据文件不存在'})
        return issues
    
    with open(path) as f:
        data = json.load(f)
    
    # 检查字段值合理性
    for code, info in data.get('data', {}).items():
        pe = info.get('pe')
        pb = info.get('pb')
        name = info.get('name', code)
        
        # PE合理性检查
        if pe is not None:
            if pe < 0 or pe > 500:
                issues.append({'level': 'ERROR', 'code': code, 'field': 'pe', 
                             'value': pe, 'msg': f'{name} PE值异常: {pe}'})
            elif pe < 1:
                issues.append({'level': 'WARNING', 'code': code, 'field': 'pe',
                             'value': pe, 'msg': f'{name} PE值过低，可能数据错误: {pe}'})
        
        # PB合理性检查
        if pb is not None:
            if pb < 0 or pb > 100:
                issues.append({'level': 'ERROR', 'code': code, 'field': 'pb',
                             'value': pb, 'msg': f'{name} PB值异常: {pb}'})
    
    return issues


def check_margin_data():
    """检查融资融券数据质量"""
    issues = []
    margin_dir = os.path.join(BASE_DIR, 'margin')
    
    # 查找最新文件
    files = [f for f in os.listdir(margin_dir) if f.endswith('.json')]
    if not files:
        issues.append({'level': 'ERROR', 'msg': '融资融券数据文件不存在'})
        return issues
    
    latest_file = max(files)
    path = os.path.join(margin_dir, latest_file)
    
    with open(path) as f:
        data = json.load(f)
    
    # 检查沪市数据日期
    if data.get('sh_latest'):
        dates = [item.get('信用交易日期', '') for item in data['sh_latest']]
        if dates:
            latest_date = max(dates)
            if latest_date < '20260101':
                issues.append({'level': 'ERROR', 'msg': f'融资融券沪市数据严重滞后: {latest_date}'})
    
    # 检查深市数据日期
    if data.get('sz_latest'):
        # 深市可能没有日期字段
        pass
    
    return issues


def check_north_money_data():
    """检查北向资金数据质量"""
    issues = []
    path = os.path.join(BASE_DIR, 'north_money/history.json')
    
    if not os.path.exists(path):
        issues.append({'level': 'ERROR', 'msg': '北向资金数据文件不存在'})
        return issues
    
    with open(path) as f:
        data = json.load(f)
    
    # 检查最新数据
    latest = data.get('latest', [])
    if latest:
        # 检查资金流向数据
        nan_count = 0
        for item in latest[-5:]:
            if str(item.get('当日成交净买额', '')) == 'nan':
                nan_count += 1
        
        if nan_count >= 3:
            issues.append({'level': 'WARNING', 'msg': f'北向资金最近{nan_count}条数据资金流向为NaN，可能接口异常'})
    
    return issues


def check_financial_data():
    """检查财务数据质量"""
    issues = []
    path = os.path.join(BASE_DIR, 'financial/2026-08-29.json')
    
    if not os.path.exists(path):
        issues.append({'level': 'ERROR', 'msg': '财务数据文件不存在'})
        return issues
    
    with open(path) as f:
        data = json.load(f)
    
    # 检查数据完整性
    for code, info in data.get('data', {}).items():
        # ROE合理性
        roe = info.get('roe')
        if roe is not None and (roe < 0 or roe > 100):
            issues.append({'level': 'WARNING', 'code': code, 'field': 'roe',
                         'value': roe, 'msg': f'{code} ROE值异常'})
        
        # EPS合理性
        eps = info.get('eps')
        if eps is not None and eps < -10:
            issues.append({'level': 'WARNING', 'code': code, 'field': 'eps',
                         'value': eps, 'msg': f'{code} EPS为负值'})
    
    return issues


def check_lhb_data():
    """检查龙虎榜数据质量"""
    issues = []
    lhb_dir = os.path.join(BASE_DIR, 'lhb')
    
    # 查找今日文件
    today = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(lhb_dir, f'{today}.json')
    
    if not os.path.exists(path):
        issues.append({'level': 'WARNING', 'msg': f'龙虎榜今日数据文件不存在: {today}.json'})
        return issues
    
    with open(path) as f:
        data = json.load(f)
    
    # 检查数据条数
    count = data.get('count', 0)
    if count == 0:
        issues.append({'level': 'WARNING', 'msg': '龙虎榜今日无数据'})
    
    return issues


def check_chain_data():
    """检查产业链数据质量"""
    issues = []
    chain_dir = os.path.join(BASE_DIR, 'industry_chains')
    
    # 查找今日文件
    today = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(chain_dir, f'{today}.json')
    
    if not os.path.exists(path):
        issues.append({'level': 'ERROR', 'msg': f'产业链数据文件不存在: {today}.json'})
        return issues
    
    with open(path) as f:
        data = json.load(f)
    
    # 检查数据更新状态
    updated_at = data.get('updated_at', '')
    if not updated_at.startswith(today):
        issues.append({'level': 'WARNING', 'msg': f'产业链数据更新时间不一致: {updated_at}'})
    
    return issues


# ============================================================
# 生成诊断报告
# ============================================================

def generate_report():
    """生成完整诊断报告"""
    report = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'target': '数据层质量诊断',
        'principle': '所有数据必须真实、可靠、官方、权威',
        'checks': {},
        'summary': {}
    }
    
    # 执行所有检查
    report['checks']['kline'] = check_kline_data()
    report['checks']['pe_pb'] = check_pe_pb_data()
    report['checks']['margin'] = check_margin_data()
    report['checks']['north_money'] = check_north_money_data()
    report['checks']['financial'] = check_financial_data()
    report['checks']['lhb'] = check_lhb_data()
    report['checks']['chain'] = check_chain_data()
    
    # 统计问题
    errors = []
    warnings = []
    for check_name, issues in report['checks'].items():
        for issue in issues:
            level = issue.get('level')
            msg = issue.get('msg', issue.get('code', ''))
            if level == 'ERROR':
                errors.append(f'{check_name}: {msg}')
            elif level == 'WARNING':
                warnings.append(f'{check_name}: {msg}')
    
    report['summary'] = {
        'total_errors': len(errors),
        'total_warnings': len(warnings),
        'errors': errors,
        'warnings': warnings
    }
    
    # 保存报告
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report


if __name__ == '__main__':
    report = generate_report()
    
    print('=' * 70)
    print('数据层质量诊断报告')
    print('=' * 70)
    print(f'生成时间: {report[\"generated_at\"]}')
    print(f'诊断原则: {report[\"principle\"]}')
    print()
    
    # 打印各检查项结果
    for check_name, issues in report['checks'].items():
        if issues:
            status = '✗ 有问题' if any(i.get('level') == 'ERROR' for i in issues) else '⚠ 有警告'
            print(f'{check_name}: {status}')
            for issue in issues:
                print(f'  - [{issue.get(\"level\")}] {issue.get(\"msg\", issue.get(\"code\", \"\"))}')
        else:
            print(f'{check_name}: ✓ 正常')
    
    print()
    print('=' * 70)
    print('诊断总结')
    print('=' * 70)
    print(f'错误数: {report[\"summary\"][\"total_errors\"]}')
    print(f'警告数: {report[\"summary\"][\"total_warnings\"]}')
    
    if report['summary']['errors']:
        print()
        print('严重错误:')
        for err in report['summary']['errors']:
            print(f'  ✗ {err}')
    
    if report['summary']['warnings']:
        print()
        print('警告信息:')
        for warn in report['summary']['warnings']:
            print(f'  ⚠ {warn}')
    
    print()
    print(f'详细报告已保存: {REPORT_PATH}')
