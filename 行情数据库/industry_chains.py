#!/usr/bin/env python3
"""
产业链监控配置
定义用户关注的科技产业链及其成分股
"""
import sys
sys.path.insert(0, '/workspace/行情数据库')

from config import HOLDINGS, WATCH_LIST, INDEXES

# ============================================================
# 产业链定义
# ============================================================

# 产业链关键词 → 成分股代码映射
INDUSTRY_CHAINS = {
    # 华为产业链
    '华为产业链': {
        'name': '华为产业链',
        'color': '#FF6B35',
        'stocks': {
            'sh603516': '淳中科技',
            'sh601231': '环旭电子',
            'sz002281': '光迅科技',
            'sz300628': '亿联网络',
            'sh688111': '金山办公',
            'sz300036': '优博讯',
        },
    },
    # 英伟达产业链
    '英伟达产业链': {
        'name': '英伟达产业链',
        'color': '#7C3AED',
        'stocks': {
            'sh601138': '工业富联',
            'sz300476': '胜宏科技',
            'sz300394': '天孚通信',
            'sz002436': '兴森科技',
            'sh688981': '中芯国际',
        },
    },
    # 长鑫产业链
    '长鑫产业链': {
        'name': '长鑫产业链',
        'color': '#059669',
        'stocks': {
            'sz002156': '通富微电',
            'sh600584': '长电科技',
            'sz002371': '北方华创',
            'sh688012': '中微公司',
        },
    },
    # 特斯拉产业链
    '特斯拉产业链': {
        'name': '特斯拉产业链',
        'color': '#DC2626',
        'stocks': {
            'sh603283': '赛腾股份',
            'sz300450': '先导智能',
            'sz002709': '天赐材料',
        },
    },
    # 算力
    '算力': {
        'name': '算力',
        'color': '#2563EB',
        'stocks': {
            'sh600584': '长电科技',
            'sz002281': '光迅科技',
            'sz300394': '天孚通信',
            'sh688981': '中芯国际',
        },
    },
    # 光模块
    '光模块': {
        'name': '光模块',
        'color': '#D97706',
        'stocks': {
            'sz002281': '光迅科技',
            'sz300394': '天孚通信',
            'sh603160': '汇顶科技',
            'sz002241': '歌尔股份',
        },
    },
    # PCB
    'PCB': {
        'name': 'PCB',
        'color': '#7C3AED',
        'stocks': {
            'sz300476': '胜宏科技',
            'sz002436': '兴森科技',
            'sh601231': '环旭电子',
        },
    },
    # 机器人
    '机器人': {
        'name': '机器人',
        'color': '#0891B2',
        'stocks': {
            'sz300394': '天孚通信',
            'sh603283': '赛腾股份',
            'sz300450': '先导智能',
        },
    },
    # AI
    'AI': {
        'name': 'AI应用',
        'color': '#4F46E5',
        'stocks': {
            'sh688111': '金山办公',
            'sz300628': '亿联网络',
        },
    },
    # 液冷
    '液冷': {
        'name': '液冷服务器',
        'color': '#0EA5E9',
        'stocks': {
            'sh601138': '工业富联',
            'sz002281': '光迅科技',
        },
    },
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
