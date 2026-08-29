#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分时数据量化特征分析工具
分析分钟级成交量、价格波动、量价关系，检测疑似量化交易特征
"""
import urllib.request
import json
import re
import statistics
import sys

def get_minute_data(symbol):
    """获取分时数据"""
    url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?_var=min_data_{symbol}&code={symbol}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read()
            text = data.decode('gbk')
            start = text.find('={')
            if start >= 0:
                return json.loads(text[start+1:].strip())
    except Exception as e:
        print(f"Error {symbol}: {e}")
    return None

def analyze_quant_pattern(minutes, name):
    """分析分时数据中的量化特征"""
    if not minutes or len(minutes) < 20:
        return None
    
    # 解析数据
    data = []
    for item in minutes:
        parts = item.split(' ')
        if len(parts) >= 4:
            try:
                time_str = parts[0]
                price = float(parts[1])
                volume = int(parts[2])
                amount = float(parts[3])
                data.append({
                    'time': time_str,
                    'price': price,
                    'volume': volume,
                    'amount': amount,
                    'volume_wan': volume / 10000
                })
            except:
                continue
    
    if len(data) < 20:
        return None
    
    # 计算特征
    volumes = [d['volume_wan'] for d in data]
    prices = [d['price'] for d in data]
    
    # 1. 成交量变异系数（量化特征：均匀度）
    cv_volume = statistics.stdev(volumes) / statistics.mean(volumes) if statistics.mean(volumes) > 0 else 0
    
    # 2. 价格波动率
    price_changes = []
    for i in range(1, len(prices)):
        change = abs(prices[i] - prices[i-1]) / prices[i-1] * 100
        price_changes.append(change)
    avg_price_change = statistics.mean(price_changes) if price_changes else 0
    
    # 3. 量价相关性
    if len(volumes) > 5 and len(prices) > 5:
        vol_mean = statistics.mean(volumes)
        price_mean = statistics.mean(prices)
        cov = sum((v - vol_mean) * (p - price_mean) for v, p in zip(volumes, prices)) / len(volumes)
        vol_std = statistics.stdev(volumes)
        price_std = statistics.stdev(prices)
        correlation = cov / (vol_std * price_std) if vol_std > 0 and price_std > 0 else 0
    else:
        correlation = 0
    
    # 4. 异常放量检测（量比>2且价格波动<0.1%）
    abnormal_count = 0
    for i in range(1, len(data)):
        vol_ratio = volumes[i] / volumes[i-1] if volumes[i-1] > 0 else 0
        price_change = abs(prices[i] - prices[i-1]) / prices[i-1] * 100
        if vol_ratio > 2.0 and price_change < 0.1:
            abnormal_count += 1
    abnormal_ratio = abnormal_count / len(data) * 100
    
    # 5. 均匀度评分（0-100，越接近100越均匀，疑似量化）
    uniformity_score = max(0, min(100, 100 - cv_volume * 100))
    
# 量化风险评级
    risk_score = 0
    risk_factors = []
    if cv_volume < 0.5:
        risk_score += 25
        risk_factors.append("成交量过于均匀")
    if correlation < 0.3:
        risk_score += 25
        risk_factors.append("量价背离")
    if abnormal_ratio > 10:
        risk_score += 25
        risk_factors.append("异常放量频繁")
    if uniformity_score > 70:
        risk_score += 25
        risk_factors.append("均匀度过高")

    # ==== 新增：技术指标与信号生成 ====
    # 计算短中长期移动平均（假设已有收盘价序列）
    prices = [d['price'] for d in data]
    if len(prices) >= 10:
        # 简单示例：5日均线、10日均线
        ma5 = sum(prices[-5:]) / 5
        ma10 = sum(prices[-10:]) / 10
        # Golden Cross / Death Cross 信号
        if ma5 > ma10:
            risk_factors.append("多头排列（金叉）")
            risk_score += 10
        elif ma5 < ma10:
            risk_factors.append("空头排列（死叉）")
            risk_score += 10
    # ==== 为止损/止盈判断（基于止损线、取利价）=====
    # 假设已有 stop_loss、take_profit 参数（此处简化示例）
    # 如果最新价触及止损或止盈，生成对应信号
    # 这里不做具体实现，仅占位示意
    # ==== 最终风险等级 ===
    if risk_score == 0:
        risk_level = "正常"
    elif risk_score < 25:
        risk_level = "低风险"
    elif risk_score < 50:
        risk_level = "中风险"
    elif risk_score < 75:
        risk_level = "高风险"
    else:
        risk_level = "极高风险"

    return {
        'name': name,
        'bars': len(data),
        'cv_volume': cv_volume,
        'avg_price_change': avg_price_change,
        'volume_price_corr': correlation,
        'abnormal_ratio': abnormal_ratio,
        'uniformity_score': uniformity_score,
        'risk_score': risk_score,
        'risk_level': risk_level,
        'risk_factors': risk_factors,
        'latest_price': prices[-1],
        'latest_volume': volumes[-1],
        # ==== 技术指标输出 ===
        'ma5': ma5,
        'ma10': ma10,
        'signal': risk_level  # 简化输出信号
    }

def main():
    stocks = {
        'sh601138': '工业富联',
        'sz300476': '胜宏科技',
        'sz300394': '天孚通信',
        'sh603516': '淳中科技',
        'sz002156': '通富微电',
        'sh600584': '长电科技',
        'sh603283': '赛腾股份',
        'sh601231': '环旭电子'
    }
    
    print("=" * 90)
    print("分时量化特征分析 | 数据来源：腾讯证券")
    print("=" * 90)
    print(f"\n{'股票':<10} {'数据条':>6} {'量变Coeff':>10} {'价波动%':>8} {'量价相关':>8} {'异常比%':>8} {'均匀分':>6} {'风险':>8}")
    print("-" * 90)
    
    results = []
    for symbol, name in stocks.items():
        result = get_minute_data(symbol)
        if result and 'data' in result and symbol in result['data']:
            minutes = result['data'][symbol]['data']['data']
            analysis = analyze_quant_pattern(minutes, name)
            if analysis:
                results.append(analysis)
                print(f"{analysis['name']:<10} {analysis['bars']:>6} {analysis['cv_volume']:>10.2f} "
                      f"{analysis['avg_price_change']:>8.2f} {analysis['volume_price_corr']:>8.2f} "
                      f"{analysis['abnormal_ratio']:>8.1f} {analysis['uniformity_score']:>6.0f} "
                      f"{analysis['risk_level']:>8}")
    
    print("-" * 90)
    print("\n判断标准：")
    print("  • 量变异系数<0.5：成交量过于均匀，疑似量化")
    print("  • 量价相关性<0.3：量价背离，可能有对倒")
    print("  • 异常比>10%：频繁出现放量不涨，疑似量化特征")
    print("  • 均匀分>70：成交量分布均匀度高于70%，疑似程序化交易")
    print("=" * 90)
    
    # 详细分析
    if results:
        print("\n详细分析：")
        for r in results:
            if r['risk_score'] > 0:
                print(f"\n{r['name']}: {r['risk_level']} ({r['risk_score']}分)")
                if r['risk_factors']:
                    print(f"  风险因素: {', '.join(r['risk_factors'])}")
                print(f"  量变异系数: {r['cv_volume']:.2f} | 量价相关: {r['volume_price_corr']:.2f} | 均匀分: {r['uniformity_score']}")

if __name__ == "__main__":
    main()
