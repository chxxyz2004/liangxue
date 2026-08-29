#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量检查脚本
检查项：完整性、连续性、异常值
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import HOLDINGS, WATCH_LIST, INDEXES

KLINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kline')

def check_completeness(symbol, data):
    """检查数据完整性"""
    issues = []
    kl = data.get('data', [])
    
    if not kl:
        issues.append("数据为空")
        return issues
    
    # 检查必要字段
    required_fields = ['day', 'open', 'high', 'low', 'close', 'volume']
    for field in required_fields:
        if field not in kl[0]:
            issues.append(f"缺少字段: {field}")
            break
    
    # 检查日期连续性（排除节假日）
    dates = [d['day'][:10] for d in kl]
    for i in range(1, len(dates)):
        try:
            d1 = datetime.strptime(dates[i-1], '%Y-%m-%d')
            d2 = datetime.strptime(dates[i], '%Y-%m-%d')
            gap = (d2 - d1).days
            # 正常交易日间隔1天，周末间隔2天，节假日间隔3-11天都正常
            # 只有间隔>15天才认为是数据缺失
            if gap > 15:
                issues.append(f"{dates[i-1]}到{dates[i]}间隔{gap}天（疑似缺失）")
        except:
            pass
    
    return issues

def check_anomalies(symbol, data):
    """检查异常值"""
    issues = []
    kl = data.get('data', [])
    
    if len(kl) < 10:
        return issues
    
    # 检查价格异常（超过30%才告警）
    for i in range(1, len(kl)):
        prev_close = kl[i-1]['close']
        curr_close = kl[i]['close']
        pct_chg = (curr_close - prev_close) / prev_close * 100 if prev_close > 0 else 0
        
        if abs(pct_chg) > 30:  # 普通股票涨停10%，ST 5%，科创板/创业板20%
            issues.append(f"{kl[i]['day']} 涨跌幅{pct_chg:.1f}%异常")
    
    # 检查成交量异常（为0或负数）
    for i, bar in enumerate(kl):
        if bar.get('volume', 0) <= 0:
            issues.append(f"{bar['day']} 成交量为0或负数")
    
    return issues

def check_continuity(symbol, data):
    """检查数据连续性"""
    issues = []
    kl = data.get('data', [])
    
    if len(kl) < 100:
        issues.append(f"数据长度不足: {len(kl)}根（建议>100）")
    
    # 检查最新数据日期
    if kl:
        latest = kl[-1]['day'][:10]
        today = datetime.now().strftime('%Y-%m-%d')
        days_ago = (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(latest, '%Y-%m-%d')).days
        if days_ago > 2:
            issues.append(f"数据滞后{days_ago}天（最新:{latest}）")
    
    return issues

def main():
    print("=" * 60)
    print(f"数据质量检查 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_issues = {}
    total_checks = 0
    passed_checks = 0
    
    # 检查所有股票
    for symbol in list(HOLDINGS.keys()) + list(WATCH_LIST.keys()):
        path = os.path.join(KLINE_DIR, f"{symbol}.json")
        if not os.path.exists(path):
            all_issues[symbol] = ["文件不存在"]
            continue
        
        with open(path) as f:
            data = json.load(f)
        
        issues = []
        issues.extend(check_completeness(symbol, data))
        issues.extend(check_anomalies(symbol, data))
        issues.extend(check_continuity(symbol, data))
        
        if issues:
            all_issues[symbol] = issues
        else:
            passed_checks += 1
        
        total_checks += 1
    
    # 检查指数
    for symbol in INDEXES.keys():
        path = os.path.join(KLINE_DIR, f"{symbol}.json")
        if not os.path.exists(path):
            all_issues[symbol] = ["文件不存在"]
            continue
        
        with open(path) as f:
            data = json.load(f)
        
        issues = check_continuity(symbol, data)
        if issues:
            all_issues[symbol] = issues
        else:
            passed_checks += 1
        
        total_checks += 1
    
    # 输出结果
    print(f"\n检查总数: {total_checks}")
    print(f"通过: {passed_checks}")
    print(f"问题: {len(all_issues)}")
    print()
    
    if all_issues:
        print("【问题详情】")
        for symbol, issues in all_issues.items():
            print(f"\n{symbol}:")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print("\n✓ 所有数据质量检查通过")
    
    # 生成报告
    report_path = os.path.join(os.path.dirname(KLINE_DIR), 'DATA_QUALITY_REPORT.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 数据质量报告\n\n")
        f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 检查结果\n\n")
        f.write(f"- 总检查数: {total_checks}\n")
        f.write(f"- 通过: {passed_checks}\n")
        f.write(f"- 问题: {len(all_issues)}\n\n")
        
        if all_issues:
            f.write("## 问题详情\n\n")
            for symbol, issues in all_issues.items():
                f.write(f"### {symbol}\n\n")
                for issue in issues:
                    f.write(f"- {issue}\n")
                f.write("\n")
        else:
            f.write("✓ 所有数据质量检查通过\n\n")
    
    print(f"\n报告已保存: {report_path}")
    return 0 if not all_issues else 1

if __name__ == '__main__':
    sys.exit(main())
