#!/usr/bin/env python3
"""
产业链监控配置 v2
基于真实业务关系定义产业链成分股
"""
import sys
sys.path.insert(0, '/workspace/行情数据库')

from config import HOLDINGS, WATCH_LIST, INDEXES

# ============================================================
# 产业链定义（v2 - 基于真实业务）
# ============================================================

INDUSTRY_CHAINS = {
    # 华为产业链 - 真华为供应商
    '华为产业链': {
        'name': '华为产业链',
        'color': '#FF6B35',
        'stocks': {
            'sh601231': '环旭电子',      # SiP模组供应商
            'sz002281': '光迅科技',      # 光模块供应商
            'sh688111': '金山办公',      # WPS鸿蒙适配
        },
    },
    # 英伟达产业链 - AI服务器/算力
    '英伟达产业链': {
        'name': '英伟达产业链',
        'color': '#7C3AED',
        'stocks': {
            'sh601138': '工业富联',      # AI服务器代工
            'sz300476': '胜宏科技',      # PCB供应商
            'sz300394': '天孚通信',      # 光模块
            'sz002436': '兴森科技',      # PCB
            'sh688981': '中芯国际',      # 芯片制造
        },
    },
    # 长鑫产业链 - 存储芯片
    '长鑫产业链': {
        'name': '长鑫产业链',
        'color': '#059669',
        'stocks': {
            'sz002156': '通富微电',      # 封测
            'sh600584': '长电科技',      # 封测
            'sz002371': '北方华创',      # 设备
            'sh688012': '中微公司',      # 设备
        },
    },
    # 特斯拉产业链 - 新能源车
    '特斯拉产业链': {
        'name': '特斯拉产业链',
        'color': '#DC2626',
        'stocks': {
            'sh603283': '赛腾股份',      # 自动化设备
            'sz300450': '先导智能',      # 锂电设备
            'sz002709': '天赐材料',      # 电解液
        },
    },
    # 光模块 - 独立产业链
    '光模块': {
        'name': '光模块',
        'color': '#D97706',
        'stocks': {
            'sz002281': '光迅科技',
            'sz300394': '天孚通信',
            'sh603160': '汇顶科技',
        },
    },
    # PCB - 独立产业链
    'PCB': {
        'name': 'PCB',
        'color': '#7C3AED',
        'stocks': {
            'sz300476': '胜宏科技',
            'sz002436': '兴森科技',
            'sh601231': '环旭电子',
        },
    },
    # 算力 - AI基础设施
    '算力': {
        'name': '算力',
        'color': '#2563EB',
        'stocks': {
            'sh601138': '工业富联',      # AI服务器
            'sz002281': '光迅科技',      # 光模块
            'sz300394': '天孚通信',      # 光模块
            'sh688981': '中芯国际',      # 芯片
        },
    },
    # 液冷服务器
    '液冷': {
        'name': '液冷服务器',
        'color': '#0EA5E9',
        'stocks': {
            'sh601138': '工业富联',
            'sz002281': '光迅科技',
        },
    },
    # AI应用
    'AI': {
        'name': 'AI应用',
        'color': '#4F46E5',
        'stocks': {
            'sh688111': '金山办公',      # WPS AI
        },
    },
    # 机器人
    '机器人': {
        'name': '机器人',
        'color': '#0891B2',
        'stocks': {
            'sh603283': '赛腾股份',      # 自动化检测
            'sz300450': '先导智能',
        },
    },
}

# 淳中科技单独归类
HUAZHONG_CATEGORY = {
    'code': 'sh603516',
    'name': '淳中科技',
    'actual_business': '视频协作系统、显示控制系统',
    'category': '智能显示',
}

# 从config.py自动关联持仓和关注
CURRENT_HOLDINGS = {**HOLDINGS, **WATCH_LIST}


def get_stock_chain(code: str) -> list:
    """查询某只股票属于哪些产业链"""
    chains = []
    for chain_name, chain_info in INDUSTRY_CHAINS.items():
        if code in chain_info['stocks']:
            chains.append(chain_name)
    return chains


def get_chain_stocks(chain_name: str) -> dict:
    """获取产业链所有成分股"""
    if chain_name in INDUSTRY_CHAINS:
        return INDUSTRY_CHAINS[chain_name]['stocks']
    return {}


def get_all_chain_stocks() -> set:
    """获取所有产业链涉及的股票代码"""
    all_stocks = set()
    for chain in INDUSTRY_CHAINS.values():
        all_stocks.update(chain['stocks'].keys())
    return all_stocks


def get_holdings_chains():
    """获取持仓股票所属产业链"""
    result = {}
    for code, info in CURRENT_HOLDINGS.items():
        chains = get_stock_chain(code)
        if chains:
            result[code] = {
                'name': info.name,
                'chains': chains,
            }
    return result
