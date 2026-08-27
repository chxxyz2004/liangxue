#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多数据源管理器
支持腾讯证券、新浪财经等多个数据源
实现fallback机制，确保数据获取的稳定性
借鉴自 daily_stock_analysis 和 akshare 项目
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict, Any

# 复用update_data.py的成功逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from update_data import fetch_tencent_qfq, fetch_sina_kline
except ImportError:
    print("⚠ 无法导入update_data.py，使用内置逻辑")
    fetch_tencent_qfq = None
    fetch_sina_kline = None

class DataSourceManager:
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'success': 0,
            'failed': 0,
            'source_hits': {'腾讯证券': 0, '新浪财经': 0}
        }
    
    def get_daily_kline(self, symbol: str, name: str, days: int = 300) -> Optional[List[Dict]]:
        """获取日K线数据，自动fallback"""
        self.stats['total_requests'] += 1
        
        # 优先尝试腾讯证券（前复权）- 复用update_data.py的逻辑
        try:
            data = fetch_tencent_qfq(symbol, days + 60)
            if data and len(data) > 0:
                self.stats['success'] += 1
                self.stats['source_hits']['腾讯证券'] += 1
                print(f"✓ {name}({symbol}): 使用腾讯证券获取数据，{len(data)}条")
                return data
        except Exception as e:
            print(f"  ⚠ 腾讯证券API失败: {e}")
        
        # 备用：新浪财经（不复权）
        try:
            data = fetch_sina_kline(symbol, days + 60)
            if data and len(data) > 0:
                self.stats['success'] += 1
                self.stats['source_hits']['新浪财经'] += 1
                print(f"✓ {name}({symbol}): 使用新浪财经获取数据，{len(data)}条")
                return data
        except Exception as e:
            print(f"  ⚠ 新浪财经API失败: {e}")
        
        self.stats['failed'] += 1
        print(f"✗ {name}({symbol}): 所有数据源均失败")
        return None
    
    def get_realtime_quote(self, symbol: str, name: str) -> Optional[Dict]:
        """获取实时行情"""
        try:
            # 使用gbk编码解码
            url = f"https://qt.gtimg.cn/q={symbol}"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = response.read()
                # 腾讯实时行情使用GBK编码
                data = raw.decode('gbk', errors='ignore')
            
            # 解析实时行情
            if '~' in data:
                parts = data.split('~')
                if len(parts) > 40:
                    return {
                        'code': symbol,
                        'name': parts[1] if len(parts) > 1 else name,
                        'price': float(parts[3]) if parts[3] else 0,
                        'change': float(parts[32]) if len(parts) > 32 and parts[32] else 0,
                        'pct_chg': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                        'volume': float(parts[6]) * 10000 if parts[6] else 0,
                        'time': parts[30] if len(parts) > 30 else '',
                        'date': parts[31] if len(parts) > 31 else ''
                    }
        except Exception as e:
            print(f"⚠ {name}实时行情获取失败: {e}")
        
        return None
    
    def get_index_kline(self, symbol: str, days: int = 360) -> Optional[List[Dict]]:
        """获取指数K线（新浪财经）"""
        try:
            data = fetch_sina_kline(symbol, days + 60)
            if data and len(data) > 0:
                return data
        except Exception as e:
            print(f"⚠ 指数数据获取失败: {e}")
        
        return None
    
    def get_stats(self) -> Dict:
        """获取统计数据"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印统计信息"""
        print("\n=== 数据源使用统计 ===")
        print(f"总请求数: {self.stats['total_requests']}")
        print(f"成功: {self.stats['success']}, 失败: {self.stats['failed']}")
        if self.stats['total_requests'] > 0:
            rate = self.stats['success'] / self.stats['total_requests'] * 100
            print(f"成功率: {rate:.1f}%")
        print("\n各数据源命中次数:")
        for name, count in self.stats['source_hits'].items():
            print(f"  {name}: {count}次")

# 全局管理器实例
manager = DataSourceManager()

def main():
    """测试多数据源管理器"""
    print("测试多数据源管理器...")
    print("=" * 60)
    
    # 测试股票
    test_stocks = [
        ('sh601138', '工业富联'),
        ('sz300476', '胜宏科技'),
        ('sh603516', '淳中科技'),
    ]
    
    for symbol, name in test_stocks:
        print(f"\n测试 {name}({symbol}):")
        data = manager.get_daily_kline(symbol, name, days=30)
        if data:
            print(f"  获取到 {len(data)} 条数据")
            print(f"  最新日期: {data[-1].get('day', 'N/A')[:10]}")
        
        # 测试实时行情
        quote = manager.get_realtime_quote(symbol, name)
        if quote:
            print(f"  实时行情: {quote.get('price', 0):.2f}元 ({quote.get('pct_chg', 0):+.2f}%)")
    
    # 打印统计
    manager.print_stats()

if __name__ == '__main__':
    main()
