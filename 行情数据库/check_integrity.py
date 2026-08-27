#!/usr/bin/env python3
"""
数据完整性校验脚本
检查日K和5分钟K线数据的完整性和一致性
"""
import json
import os
import sys
from datetime import datetime, timedelta

class DataIntegrityCheck:
    def __init__(self):
        self.base_dir = '/workspace/行情数据库'
        self.kline_dir = os.path.join(self.base_dir, 'kline')
        self.kline_5min_dir = os.path.join(self.base_dir, 'kline_5min')
        self.errors = []
        self.warnings = []
        self.ok_count = 0
    
    def check_daily_kline(self):
        """检查日K数据完整性"""
        print("\n【日K数据检查】")
        
        # 预期股票代码
        expected = {
            'sh601138': '工业富联',
            'sz300476': '胜宏科技',
            'sz300394': '天孚通信',
            'sh603516': '淳中科技',
            'sz002156': '通富微电',
            'sh600584': '长电科技',
            'sh603283': '赛腾股份',
            'sh601231': '环旭电子',
            'sh603220': '中贝通信',
            'sh600629': '华建集团',
        }
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        for code, name in expected.items():
            filepath = os.path.join(self.kline_dir, f'{code}.json')
            
            if not os.path.exists(filepath):
                self.errors.append(f'{name}({code}): 日K文件不存在')
                print(f"  ✗ {name}: 文件缺失")
                continue
            
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                bars = data.get('data', [])
                
                # 检查数据量
                if len(bars) < 100:
                    self.warnings.append(f'{name}({code}): 数据量不足 ({len(bars)}条)')
                    print(f"  ⚠ {name}: 数据量不足 ({len(bars)}条)")
                elif len(bars) < 300:
                    print(f"  ✓ {name}: {len(bars)}条")
                else:
                    self.ok_count += 1
                    print(f"  ✓ {name}: {len(bars)}条")
                
                # 检查最新日期
                if bars:
                    latest_date = bars[-1].get('day', '').split(' ')[0]
                    if latest_date != today and latest_date != yesterday:
                        self.warnings.append(f'{name}({code}): 最新日期为{latest_date}，非今日')
                        print(f"    ⚠ 最新日期: {latest_date}")
                    
            except Exception as e:
                self.errors.append(f'{name}({code}): 解析错误 - {e}')
                print(f"  ✗ {name}: 解析错误")
    
    def check_5min_kline(self):
        """检查5分钟K线数据完整性"""
        print("\n【5分钟K线数据检查】")
        
        today = datetime.now().strftime('%Y-%m-%d')
        expected = ['sh603516', 'sh601138', 'sh603283', 'sz002156', 
                   'sh601231', 'sz300476', 'sh603220', 'sh600629', 'sz300394']
        
        for code in expected:
            filepath = os.path.join(self.kline_5min_dir, f'{code}_{today}.json')
            
            if not os.path.exists(filepath):
                self.warnings.append(f'{code}: 今日5分钟数据缺失')
                print(f"  ⚠ {code}: 今日数据缺失")
                continue
            
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                bars = data.get('bars', [])
                count = data.get('count', len(bars))
                
                if count >= 48:
                    self.ok_count += 1
                    print(f"  ✓ {code}: {count}根K线")
                elif count > 0:
                    self.warnings.append(f'{code}: 5分钟数据不足 ({count}根)')
                    print(f"  ⚠ {code}: {count}根K线")
                else:
                    self.errors.append(f'{code}: 5分钟数据为空')
                    print(f"  ✗ {code}: 数据为空")
                    
            except Exception as e:
                self.errors.append(f'{code}: 解析错误 - {e}')
                print(f"  ✗ {code}: 解析错误")
    
    def check_meta(self):
        """检查元数据"""
        print("\n【元数据检查】")
        
        meta_file = os.path.join(self.base_dir, 'meta.json')
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                print(f"  ✓ meta.json: 版本{meta.get('version', '未知')}")
                self.ok_count += 1
            except Exception as e:
                self.errors.append(f'meta.json: 解析错误 - {e}')
                print(f"  ✗ meta.json: 解析错误")
        else:
            self.warnings.append('meta.json: 不存在')
            print(f"  ⚠ meta.json: 不存在")
    
    def generate_report(self):
        """生成检查报告"""
        print("\n" + "=" * 50)
        print("数据完整性检查报告")
        print("=" * 50)
        
        if self.errors:
            print(f"\n【错误】({len(self.errors)}个)")
            for err in self.errors:
                print(f"  ✗ {err}")
        
        if self.warnings:
            print(f"\n【警告】({len(self.warnings)}个)")
            for warn in self.warnings:
                print(f"  ⚠ {warn}")
        
        print(f"\n【统计】")
        print(f"  正常: {self.ok_count}项")
        print(f"  警告: {len(self.warnings)}项")
        print(f"  错误: {len(self.errors)}项")
        
        if not self.errors:
            print(f"\n✓ 数据完整性检查通过")
            return 0
        else:
            print(f"\n✗ 发现{len(self.errors)}个错误，需要修复")
            return 1

def main():
    checker = DataIntegrityCheck()
    checker.check_daily_kline()
    checker.check_5min_kline()
    checker.check_meta()
    report = checker.generate_report()
    
    # 保存报告
    report_file = f'/tmp/liangxue_integrity_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'
    with open(report_file, 'w') as f:
        f.write(f'数据完整性检查报告 • {datetime.now()}\n')
        f.write('=' * 50 + '\n\n')
        if checker.errors:
            f.write('错误:\n')
            for err in checker.errors:
                f.write(f'  ✗ {err}\n')
            f.write('\n')
        if checker.warnings:
            f.write('警告:\n')
            for warn in checker.warnings:
                f.write(f'  ⚠ {warn}\n')
            f.write('\n')
        f.write(f'统计: 正常{checker.ok_count}项, 警告{len(checker.warnings)}项, 错误{len(checker.errors)}项\n')
        f.write(f'结果文件: {report_file}\n')
    
    print(f"\n报告已保存: {report_file}")
    return report

if __name__ == '__main__':
    sys.exit(main())
