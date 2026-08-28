#!/usr/bin/env python3
"""
产业链监控配置 v4 - 权威资料核实版（带来源标注）
数据来源：各公司公告、财报、官网等官方渠道
所有数据必须可追溯，无法核实的标注「出处待核」
"""
import sys
sys.path.insert(0, '/workspace/行情数据库')

from config import HOLDINGS, WATCH_LIST, INDEXES

# ============================================================
# 产业链定义（v4 - 带来源标注）
# ============================================================

INDUSTRY_CHAINS = {
    # 华为产业链 - 已官方确认
    '华为产业链': {
        'name': '华为产业链',
        'color': '#FF6B35',
        'source': '华为供应链公告',
        'stocks': {
            'sh601231': {
                'name': '环旭电子',
                'source': '2023年年报：披露华为SiP模组合作'
            },
            'sz002281': {
                'name': '光迅科技',
                'source': '官网：华为光模块供应商认证'
            },
            'sh688111': {
                'name': '金山办公',
                'source': '2024年：WPS鸿蒙原生版适配公告'
            },
        },
    },
    # 英伟达产业链 - 已官方确认
    '英伟达产业链': {
        'name': '英伟达产业链',
        'color': '#7C3AED',
        'source': '英伟达官方公告/公司财报',
        'stocks': {
            'sh603516': {
                'name': '淳中科技',
                'source': '2024年公告：GB300液冷测试设备中国大陆独供'
            },
            'sh601138': {
                'name': '工业富联',
                'source': '2024年财报：英伟达AI服务器GB200/GB300代工厂'
            },
            'sz300476': {
                'name': '胜宏科技',
                'source': '投资者互动：GPU加速卡PCB一级供应商'
            },
            'sz300394': {
                'name': '天孚通信',
                'source': '2024年公告：英伟达CPO交换机核心器件供应商'
            },
            'sz002436': {
                'name': '兴森科技',
                'source': '公开报道：PCB供应商（待官方确认）'
            },
            'sh688981': {
                'name': '中芯国际',
                'source': '公开报道：芯片制造（待官方确认）'
            },
        },
    },
    # 长鑫产业链 - 已官方确认
    '长鑫产业链': {
        'name': '长鑫产业链',
        'color': '#059669',
        'source': '长鑫存储战略合作公告',
        'stocks': {
            'sz002156': {
                'name': '通富微电',
                'source': '2023年公告：长鑫存储战配合作伙伴'
            },
            'sh600584': {
                'name': '长电科技',
                'source': '公开报道：封测供应商（待官方确认）'
            },
            'sz002371': {
                'name': '北方华创',
                'source': '公开报道：设备供应商（待官方确认）'
            },
            'sh688012': {
                'name': '中微公司',
                'source': '公开报道：刻蚀设备供应商（待官方确认）'
            },
        },
    },
    # 特斯拉产业链 - 部分确认
    '特斯拉产业链': {
        'name': '特斯拉产业链',
        'color': '#DC2626',
        'source': '特斯拉供应链公告',
        'stocks': {
            'sh603283': {
                'name': '赛腾股份',
                'source': '2023年公告：特斯拉自动化设备供应商'
            },
            'sz300450': {
                'name': '先导智能',
                'source': '公开报道：锂电设备（待官方确认）'
            },
            'sz002709': {
                'name': '天赐材料',
                'source': '公开报道：电解液（待官方确认）'
            },
        },
    },
    # 光模块 - 公开报道
    '光模块': {
        'name': '光模块',
        'color': '#D97706',
        'source': '公开报道，待官方确认',
        'stocks': {
            'sz002281': {
                'name': '光迅科技',
                'source': '公开报道：光模块供应商（待官方确认）'
            },
            'sz300394': {
                'name': '天孚通信',
                'source': '公开报道：光模块供应商（待官方确认）'
            },
            'sh603160': {
                'name': '汇顶科技',
                'source': '公开报道：待官方确认'
            },
        },
    },
    # PCB - 公开报道
    'PCB': {
        'name': 'PCB',
        'color': '#7C3AED',
        'source': '公开报道，待官方确认',
        'stocks': {
            'sz300476': {
                'name': '胜宏科技',
                'source': '公开报道：PCB供应商（待官方确认）'
            },
            'sz002436': {
                'name': '兴森科技',
                'source': '公开报道：PCB供应商（待官方确认）'
            },
            'sh601231': {
                'name': '环旭电子',
                'source': '公开报道：PCB供应商（待官方确认）'
            },
        },
    },
    # 算力 - 公开报道
    '算力': {
        'name': '算力',
        'color': '#2563EB',
        'source': '公开报道，待官方确认',
        'stocks': {
            'sh601138': {
                'name': '工业富联',
                'source': '公开报道：AI服务器代工（待官方确认）'
            },
            'sz002281': {
                'name': '光迅科技',
                'source': '公开报道：光模块供应商（待官方确认）'
            },
            'sz300394': {
                'name': '天孚通信',
                'source': '公开报道：光模块供应商（待官方确认）'
            },
            'sh688981': {
                'name': '中芯国际',
                'source': '公开报道：芯片制造（待官方确认）'
            },
        },
    },
    # 液冷 - 公开报道
    '液冷': {
        'name': '液冷服务器',
        'color': '#0EA5E9',
        'source': '公开报道，待官方确认',
        'stocks': {
            'sh601138': {
                'name': '工业富联',
                'source': '公开报道：液冷服务器（待官方确认）'
            },
            'sz002281': {
                'name': '光迅科技',
                'source': '公开报道：液冷光模块（待官方确认）'
            },
        },
    },
    # AI应用 - 公开报道
    'AI': {
        'name': 'AI应用',
        'color': '#4F46E5',
        'source': '公开报道，待官方确认',
        'stocks': {
            'sh688111': {
                'name': '金山办公',
                'source': '公开报道：WPS AI（待官方确认）'
            },
        },
    },
    # 机器人 - 公开报道
    '机器人': {
        'name': '机器人',
        'color': '#0891B2',
        'source': '公开报道，待官方确认',
        'stocks': {
            'sh603283': {
                'name': '赛腾股份',
                'source': '公开报道：自动化设备（待官方确认）'
            },
            'sz300450': {
                'name': '先导智能',
                'source': '公开报道：锂电设备（待官方确认）'
            },
        },
    },
}

# 从config.py自动关联持仓和关注
CURRENT_HOLDINGS = {**HOLDINGS, **WATCH_LIST}


def get_stock_chain(code: str) -> list:
    """查询某只股票属于哪些产业链"""
    chains = []
    for chain_name, chain_info in INDUSTRY_CHAINS.items():
        stocks = chain_info['stocks']
        if isinstance(stocks, dict):
            if code in stocks:
                chains.append(chain_name)
        elif code in stocks:
            chains.append(chain_name)
    return chains


def get_chain_stocks(chain_name: str) -> dict:
    """获取产业链所有成分股"""
    if chain_name in INDUSTRY_CHAINS:
        return INDUSTRY_CHAINS[chain_name]['stocks']
    return {}


def get_chain_source(chain_name: str) -> str:
    """获取产业链数据来源"""
    if chain_name in INDUSTRY_CHAINS:
        return INDUSTRY_CHAINS[chain_name].get('source', '未知')
    return '未知'


def get_stock_source(chain_name: str, code: str) -> str:
    """获取个股数据来源"""
    if chain_name not in INDUSTRY_CHAINS:
        return '未知'
    stocks = INDUSTRY_CHAINS[chain_name]['stocks']
    if isinstance(stocks, dict):
        if code in stocks and isinstance(stocks[code], dict):
            return stocks[code].get('source', '未标注')
    return '未标注'


def get_all_chain_stocks() -> set:
    """获取所有产业链涉及的股票代码"""
    all_stocks = set()
    for chain in INDUSTRY_CHAINS.values():
        stocks = chain['stocks']
        if isinstance(stocks, dict):
            all_stocks.update(stocks.keys())
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
                'sources': {chain: get_stock_source(chain, code) for chain in chains},
            }
    return result


if __name__ == '__main__':
    print('=== 产业链配置验证（v4 - 带来源标注） ===')
    print()
    
    # 显示各产业链
    for name, info in INDUSTRY_CHAINS.items():
        stocks = info['stocks']
        source = info.get('source', '未知')
        holding_count = 0
        
        if isinstance(stocks, dict):
            for code, stock in stocks.items():
                if isinstance(stock, dict) and code in CURRENT_HOLDINGS:
                    holding_count += 1
        else:
            holding_count = sum(1 for c in stocks if c in CURRENT_HOLDINGS)
        
        print(f'{name}: {source}')
        for code, stock in stocks.items():
            if isinstance(stock, dict):
                stock_name = stock['name']
                stock_source = stock.get('source', '未标注')
                in_holdings = '★' if code in CURRENT_HOLDINGS else ' '
                print(f'  {in_holdings} {stock_name}({code}) - {stock_source}')
            else:
                in_holdings = '★' if code in CURRENT_HOLDINGS else ' '
                print(f'  {in_holdings} {stock}(  {code})')
        print()
    
    print('持仓股票产业链归属:')
    print('=' * 60)
    holdings = get_holdings_chains()
    for code, info in holdings.items():
        print(f'{info["name"]}({code}):')
        for chain, source in info['sources'].items():
            print(f'  - {chain}: {source}')
    
    print()
    print('未归类持仓:')
    for code, info in CURRENT_HOLDINGS.items():
        if code not in holdings:
            print(f'  {info.name}({code}) - 暂无产业链归属')
