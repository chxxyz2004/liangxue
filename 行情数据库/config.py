#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量学系统统一配置"""

# 持仓股票配置（唯一数据源）
HOLDINGS = {
    'sh603516': {'name': '淳中科技', 'cost': 98.50, 'shares': 900, 'stop_loss': 90.63, 'life_line': 92.6},
    'sh601138': {'name': '工业富联', 'cost': 58.20, 'shares': 1100},
    'sz002156': {'name': '通富微电', 'cost': 45.80, 'shares': 700},
    'sh601231': {'name': '环旭电子', 'cost': 28.50, 'shares': 800},
    'sz300476': {'name': '胜宏科技', 'cost': 230.00, 'shares': 100, 'take_profit': (256, 260)},
    'sh603283': {'name': '赛腾股份', 'cost': 52.30, 'shares': 400},
}

# 关注股票池（未持仓）
WATCH_LIST = {
    'sz300394': {'name': '天孚通信', 'cost': None, 'shares': 0},
}

# 大盘指数
INDEXES = {
    'sh000001': '上证指数',
    'sz399001': '深证成指',
    'sz399006': '创业板指',
}

# 数据路径
DATA_DIR = '/workspace/行情数据库/kline'

# 量化对倒检测阈值
SPOOFING_THRESHOLDS = {
    'vol_ratio_min': 2.0,      # 量比下限
    'pct_max': 1.0,            # 最大涨跌幅（超过则不算对倒）
    'upper_shadow_ratio': 2.0, # 上影线/实体比值
    'pct_pulse_min': 3.0,      # 脉冲最小涨幅
    'pct_drop_retrace': 70,    # 回撤比例下限
}

# 报告生成配置
REPORT_CONFIG = {
    'morning': '09:25',
    'noon': '11:30',
    'close': '15:00',
    'evening': '21:00',
}

print("✓ config.py 加载成功")
