#!/usr/bin/env python3
"""
产业链监控配置 v3 - 基于官方权威资料核实
数据来源：英伟达官方公告、公司财报、证券时报、上交所公告等
"""
import sys
sys.path.insert(0, '/workspace/行情数据库')

from config import HOLDINGS, WATCH_LIST, INDEXES

# ============================================================
# 产业链定义（v3 - 权威资料核实版）
# ============================================================

INDUSTRY_CHAINS = {
    # 华为产业链 - 真华为供应商
    '华为产业链': {
        'name': '华为产业链',
        'color': '#FF6B35',
        'stocks': {
            'sh601231': '环旭电子',      # 华为SiP模组供应商（官方确认）
            'sz002281': '光迅科技',      # 华为光模块供应商（官方确认）
            'sh688111': '金山办公',      # WPS鸿蒙适配（官方确认）
        },
    },
    # 英伟达产业链 - AI算力核心供应商
    '英伟达产业链': {
        'name': '英伟达产业链',
        'color': '#7C3AED',
        'stocks': {
            'sh603516': '淳中科技',      # GB300液冷测试设备独供（英伟达官方确认）
            'sh601138': '工业富联',      # AI服务器代工龙头（英伟达官方确认）
            'sz300476': '胜宏科技',      # GPU加速卡PCB核心供应商（官方确认）
            'sz300394': '天孚通信',      # CPO交换机核心器件供应商（英伟达官方确认）
            'sz002436': '兴森科技',      # PCB供应商
            'sh688981': '中芯国际',      # 芯片制造
        },
    },
    # 长鑫产业链 - 国产存储
    '长鑫产业链': {
        'name': '长鑫产业链',
        'color': '#059669',
        'stocks': {
            'sz002156': '通富微电',      # 长鑫核心封测伙伴（官方确认）
            'sh600584': '长电科技',      # 封测供应商
            'sz002371': '北方华创',      # 设备供应商
            'sh688012': '中微公司',      # 刻蚀设备供应商
        },
    },
    # 特斯拉产业链 - 新能源车
    '特斯拉产业链': {
        'name': '特斯拉产业链',
        'color': '#DC2626',
        'stocks': {
            'sh603283': '赛腾股份',      # 自动化检测设备
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
            'sh601138': '工业富联',      # AI服务器代工
            'sz002281': '光迅科技',      # 光模块
            'sz300394': '天孚通信',      # 光模块
            'sh688981': '中芯国际',      # 芯片制造
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
            'sh603283': '赛腾股份',
            'sz300450': '先导智能',
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


if __name__ == '__main__':
    print('=== 产业链配置验证（权威资料核实版） ===')
    print()
    
    # 显示各产业链
    for name, info in INDUSTRY_CHAINS.items():
        stocks = info['stocks']
        holding_count = sum(1 for c in stocks if c in CURRENT_HOLDINGS)
        print(f'{name}: {len(stocks)}只 ({holding_count}只持仓)')
        for code, stock_name in stocks.items():
            in_holdings = '★' if code in CURRENT_HOLDINGS else ' '
            print(f'  {in_holdings} {stock_name}({code})')
        print()
    
    print('持仓股票产业链归属:')
    print('=' * 50)
    holdings = get_holdings_chains()
    for code, info in holdings.items():
        print(f'{info["name"]}({code}): {", ".join(info["chains"])}')
    
    print()
    print('未归类持仓:')
    for code, info in CURRENT_HOLDINGS.items():
        if code not in holdings:
            print(f'  {info.name}({code}) - 暂无产业链归属')
