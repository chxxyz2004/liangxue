#!/usr/bin/env python3
"""
量化对倒特征检测工具 (增强版)
基于5分钟K线数据，识别异常放量、长上影、脉冲回落等特征
无L2数据，纯OHLCV分析
"""

import urllib.request
import json
import os
import sys
import logging
from datetime import datetime

# 配置日志
LOG_FILE = '/tmp/liangxue_spoofing.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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

# 备用数据源
DATA_SOURCES = [
    ('新浪5分钟', lambda code: f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=5&ma=no&datalen=60'),
]

def pull_5min(code, datalen=60):
    """从本地或网络拉取5分钟K线"""
    # 尝试本地数据
    local_dir = '/workspace/行情数据库/kline_5min'
    today = datetime.now().strftime('%Y-%m-%d')
    local_file = os.path.join(local_dir, f'{code}_{today}.json')
    
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r') as f:
                data = json.load(f)
            bars = data.get('bars', [])
            if bars and len(bars) >= 20:
                logger.info(f'{code}: 使用本地数据 ({len(bars)}根)')
                return bars[:datalen]
            else:
                logger.warning(f'{code}: 本地数据不足 ({len(bars)}根)，尝试网络')
        except Exception as e:
            logger.error(f'{code}: 本地数据读取失败 - {e}')
    
    # 网络拉取（带重试）
    for source_name, url_func in DATA_SOURCES:
        try:
            url = url_func(code)
            logger.info(f'{code}: 从{source_name}拉取数据...')
            
            for retry in range(3):
                try:
                    data = urllib.request.urlopen(url, timeout=10).read().decode('gbk')
                    bars = json.loads(data)
                    
                    if bars and len(bars) >= 10:
                        logger.info(f'{code}: 成功获取 {len(bars)} 根K线')
                        return bars[:datalen]
                    else:
                        logger.warning(f'{code}: 返回数据过少 ({len(bars) if bars else 0}根)')
                        break
                except urllib.request.HTTPError as e:
                    if e.code == 404:
                        logger.error(f'{code}: API返回404，可能是代码错误')
                        return []
                    logger.warning(f'{code}: HTTP错误 {e.code}，重试 {retry+1}/3')
                except Exception as e:
                    logger.warning(f'{code}: 网络错误 {e}，重试 {retry+1}/3')
                    if retry < 2:
                        import time
                        time.sleep(1)
            
        except Exception as e:
            logger.error(f'{code}: {source_name} 拉取失败 - {e}')
    
    logger.error(f'{code}: 所有数据源均失败')
    return []

def detect(bars, name):
    """检测对倒特征，返回信号列表"""
    if len(bars) < 10:
        return [], "数据不足"
    
    try:
        volumes = [int(b['volume']) for b in bars[-20:]]
        avg_vol = sum(volumes) // len(volumes) if volumes else 1
    except (ValueError, KeyError) as e:
        return [], f"数据解析错误: {e}"
    
    signals = []
    for i in range(max(0, len(bars) - 48), len(bars)):
        try:
            bar = bars[i]
            o = float(bar['open'])
            h = float(bar['high'])
            l = float(bar['low'])
            c = float(bar['close'])
            v = int(bar['volume'])
            ts = bar['day'][-8:] if 'day' in bar else '?'
            
            body = abs(c - o)
            upper_shadow = h - max(o, c)
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
                    
        except (ValueError, KeyError, IndexError) as e:
            logger.warning(f'{name}: 数据解析异常 - {e}')
            continue
    
    return signals, "正常"

def main():
    logger.info(f'量化对倒特征扫描 · {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    logger.info('=' * 60)
    
    results = {}
    total_signals = 0
    
    for name, code in STOCKS.items():
        bars = pull_5min(code)
        signals, status = detect(bars, name)
        results[name] = signals
        
        if signals:
            logger.info(f'\n{name} ({code}):')
            for s in signals:
                logger.info(f'  {s}')
            total_signals += len(signals)
        else:
            logger.info(f'{name}: 无异常')
    
    logger.info(f'\n{"=" * 60}')
    logger.info(f'扫描完成: {len(STOCKS)}只股票, 共{total_signals}个异常信号')
    
    # 保存结果到文件
    result_file = f'/tmp/liangxue_spoofing_result_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'
    with open(result_file, 'w') as f:
        f.write(f'量化对倒检测结果 · {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
        f.write('=' * 60 + '\n\n')
        for name, signals in results.items():
            f.write(f'{name}: {len(signals)}个信号\n')
            for s in signals:
                f.write(f'  {s}\n')
            f.write('\n')
        f.write(f'总计: {total_signals}个异常信号\n')
    
    logger.info(f'结果已保存: {result_file}')
    return total_signals

if __name__ == '__main__':
    sys.exit(main())
