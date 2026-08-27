#!/usr/bin/env python3
"""
量化对倒特征检测工具
基于5分钟K线数据，识别异常放量、长上影、脉冲回落等特征
无L2数据，纯OHLCV分析
"""

import urllib.request
import json
import sys
from datetime import datetime

# 8只持仓 + 天孚
STOCKS = {
    '淳中科技': 'sh603516',
    '工业富联': 'sh601138',
    '赛腾股份': 'sh603283',
    '通富微电': 'sz002156',
    '环旭电子': 'sh601231',
    '胜宏科技': 'sz300476',
    '中贝通信': 'sh603220',
    '华建集团': 'sh600629',
    '天孚通信': 'sz300394',
}

# 阈值配置（可调整）
THRESHOLDS = {
    'vol_ratio_spike': 2.0,      # 量比异常阈值
    'upper_shadow_ratio': 2.0,   # 上影/实体比值阈值
    'pct_drop_retrace': 70,      # 脉冲回吐百分比阈值
    'pct_pulse_min': 3.0,        # 单根脉冲最小涨幅
}


def pull_5min(code, datalen=60):
    """优先从本地数据库读取，无则实时拉取"""
    # 尝试本地数据
    local_dir = '/workspace/行情数据库/kline_5min'
    today = datetime.now().strftime('%Y-%m-%d')
    local_file = os.path.join(local_dir, f'{code}_{today}.json')
    
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r') as f:
                data = json.load(f)
            bars = data.get('bars', [])
            if bars:
                return bars[:datalen]
        except:
            pass
    
    # 本地无数据，实时拉取
    url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=5&ma=no&datalen={datalen}'
    try:
        data = urllib.request.urlopen(url, timeout=10).read().decode('gbk')
        return json.loads(data)
    except Exception as e:
        print(f'  拉取失败: {e}', file=sys.stderr)
        return []


def detect(bars, name):
    """检测对倒特征，返回信号列表"""
    if len(bars) < 10:
        return []

    volumes = [int(b['volume']) for b in bars[-20:]]
    avg_vol = sum(volumes) // len(volumes) if volumes else 1

    signals = []
    for i in range(max(0, len(bars) - 48), len(bars)):
        bar = bars[i]
        o = float(bar['open'])
        h = float(bar['high'])
        l = float(bar['low'])
        c = float(bar['close'])
        v = int(bar['volume'])
        ts = bar['day'][-8:]  # HH:MM:SS

        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        total_range = h - l
        pct_chg = (c - o) / o * 100 if o > 0 else 0
        vol_ratio = v / avg_vol if avg_vol > 0 else 0

        # 规则1：放量滞涨
        if vol_ratio >= THRESHOLDS['vol_ratio_spike'] and abs(pct_chg) < 1.0 and total_range > 0:
            signals.append(f'{ts} ⚠️放量滞涨 量{vol_ratio:.1f}x 涨跌{pct_chg:+.2f}%')

        # 规则2：长上影假突破
        if body > 0 and upper_shadow / body >= THRESHOLDS['upper_shadow_ratio'] and pct_chg > 0:
            signals.append(f'{ts} 🔴长上影 上影{upper_shadow:.2f}/实体{body:.2f}={upper_shadow/body:.1f}x')

        # 规则3：脉冲-回落
        if i > 1 and i < len(bars) - 2 and pct_chg >= THRESHOLDS['pct_pulse_min']:
            n1c = float(bars[i + 1]['close'])
            n2c = float(bars[i + 2]['close'])
            lowest = min(n1c, n2c)
            retrace = (c - lowest) / c * 100 if c > 0 else 0
            if retrace >= THRESHOLDS['pct_drop_retrace']:
                signals.append(f'{ts} 💥脉冲回落 涨{pct_chg:.1f}% 回吐{retrace:.0f}%')

    return signals


def main():
    print(f'量化对倒特征扫描 · {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    print('=' * 60)

    results = {}
    total_signals = 0

    for name, code in STOCKS.items():
        bars = pull_5min(code)
        signals = detect(bars, name)
        results[name] = signals
        total_signals += len(signals)

        if signals:
            print(f'\n{name} ({code}):')
            for s in signals:
                print(f'  {s}')
        else:
            print(f'{name}: 无异常')

    print(f'\n{"=" * 60}')
    print(f'扫描完成: {len(STOCKS)}只股票, 共{total_signals}个异常信号')
    return total_signals


if __name__ == '__main__':
    sys.exit(main())
