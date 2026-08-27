#!/usr/bin/env python3
"""
量学系统稳定性监控
检查数据完整性、API可用性、日志状态
"""
import os
import json
import urllib.request
from datetime import datetime, timedelta

class SystemMonitor:
    def __init__(self):
        self.base_dir = '/workspace/行情数据库'
        self.kline_dir = os.path.join(self.base_dir, 'kline')
        self.kline_5min_dir = os.path.join(self.base_dir, 'kline_5min')
        self.results = []
    
    def check_api_health(self):
        """检查API可用性"""
        apis = [
            ('腾讯实时行情', 'https://qt.gtimg.cn/q=sh603516', 5),
            ('新浪5分钟K线', 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh603516&scale=5&ma=no&datalen=5', 5),
        ]
        
        for name, url, timeout in apis:
            try:
                data = urllib.request.urlopen(url, timeout=timeout).read()
                if len(data) > 100:
                    self.results.append(f'✓ {name}: 正常 ({len(data)} bytes)')
                else:
                    self.results.append(f'✗ {name}: 数据过少 ({len(data)} bytes)')
            except Exception as e:
                self.results.append(f'✗ {name}: 失败 - {str(e)[:50]}')
    
    def check_data_completeness(self):
        """检查数据完整性"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 日K数据
        expected_stocks = ['sh603516', 'sh601138', 'sh603283', 'sz002156', 
                          'sh601231', 'sz300476', 'sh603220', 'sh600629', 'sz300394']
        
        missing_daily = []
        for code in expected_stocks:
            filepath = os.path.join(self.kline_dir, f'{code}.json')
            if not os.path.exists(filepath):
                missing_daily.append(code)
            else:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                bars = data.get('data', [])
                if len(bars) < 100:
                    self.results.append(f'⚠ {code}: 日K数据不足 ({len(bars)}条)')
        
        if missing_daily:
            self.results.append(f'✗ 日K缺失: {missing_daily}')
        else:
            self.results.append(f'✓ 日K数据完整 ({len(expected_stocks)}只)')
        
        # 5分钟数据
        missing_5min = []
        for code in expected_stocks:
            filepath = os.path.join(self.kline_5min_dir, f'{code}_{today}.json')
            if not os.path.exists(filepath):
                missing_5min.append(code)
        
        if missing_5min:
            self.results.append(f'⚠ 5分钟数据缺失 ({today}): {missing_5min}')
        else:
            self.results.append(f'✓ 5分钟数据完整 ({today})')
    
    def check_logs(self):
        """检查日志文件"""
        logs = [
            '/tmp/liangxue_update.log',
            '/tmp/liangxue_noon.log',
            '/tmp/liangxue_cron.log',
        ]
        
        for log_file in logs:
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                self.results.append(f'✓ {os.path.basename(log_file)}: {size} bytes')
            else:
                self.results.append(f'⚠ {os.path.basename(log_file)}: 不存在')
    
    def check_memory(self):
        """检查MEMORY.md"""
        memory_file = '/workspace/.monkeycode/MEMORY.md'
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                content = f.read()
            lines = len(content.split('\n'))
            self.results.append(f'✓ MEMORY.md: {lines}行')
        else:
            self.results.append('✗ MEMORY.md: 不存在')
    
    def run(self):
        """运行所有检查"""
        self.results = []
        self.results.append(f'系统健康检查 · {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        self.results.append('=' * 50)
        
        self.check_api_health()
        self.check_data_completeness()
        self.check_logs()
        self.check_memory()
        
        # 运行完整性检查
        try:
            from check_integrity import DataIntegrityCheck
            checker = DataIntegrityCheck()
            checker.check_daily_kline()
            checker.check_5min_kline()
            checker.check_meta()
        except Exception as e:
            self.results.append(f'⚠ 完整性检查失败: {e}')
        
        return '\n'.join(self.results)

if __name__ == '__main__':
    monitor = SystemMonitor()
    print(monitor.run())
