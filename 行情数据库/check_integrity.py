#!/usr/bin/env python3
"""
数据完整性校验脚本
检查日K和5分钟K线数据的完整性和一致性
从 config.py 读取股票池，禁止硬编码
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/workspace/行情数据库')
from config import HOLDINGS, WATCH_LIST, INDEXES

# 所有股票（持仓+关注）
ALL_STOCKS = {**{k: v.name for k, v in HOLDINGS.items()},
              **{k: v.name for k, v in WATCH_LIST.items()}}


class DataIntegrityCheck:
    def __init__(self):
        self.base_dir = '/workspace/行情数据库'
        self.kline_dir = os.path.join(self.base_dir, 'kline')
        self.kline_5min_dir = os.path.join(self.base_dir, 'kline_5min')
        self.quotes_dir = os.path.join(self.base_dir, 'quotes')
        self.market_dir = os.path.join(self.base_dir, 'market')
        self.lhb_dir = os.path.join(self.base_dir, 'lhb')
        self.north_dir = os.path.join(self.base_dir, 'north_money')
        self.margin_dir = os.path.join(self.base_dir, 'margin')
        self.restrict_dir = os.path.join(self.base_dir, 'restrictions')
        self.financial_dir = os.path.join(self.base_dir, 'financial')
        self.errors = []
        self.warnings = []
        self.ok_count = 0

    def check_daily_kline(self):
        """检查日K数据完整性"""
        print("\n【日K数据检查】")

        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # 检查股票
        for code, name in ALL_STOCKS.items():
            filepath = os.path.join(self.kline_dir, f'{code}.json')
            if not os.path.exists(filepath):
                self.errors.append(f'{name}({code}): 日K文件不存在')
                print(f"  ✗ {name}: 文件缺失")
                continue

            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                bars = data.get('data') or data.get('klines') or []

                if len(bars) < 100:
                    self.warnings.append(f'{name}({code}): 数据量不足 ({len(bars)}条)')
                    print(f"  ⚠ {name}: 数据量不足 ({len(bars)}条)")
                else:
                    self.ok_count += 1
                    print(f"  ✓ {name}: {len(bars)}条")

                if bars:
                    latest_date = str(bars[-1].get('day', '')).split(' ')[0]
                    if latest_date != today and latest_date != yesterday:
                        self.warnings.append(f'{name}({code}): 最新日期为{latest_date}，非今日')
                        print(f"    ⚠ 最新日期: {latest_date}")

                # 校验数据类型
                if bars:
                    sample = bars[-1]
                    for field in ('open', 'high', 'low', 'close', 'volume', 'amount'):
                        val = sample.get(field)
                        if val is not None and not isinstance(val, (int, float)):
                            self.errors.append(f'{name}({code}): {field}值类型异常 {type(val).__name__}={val}')
                            print(f"  ✗ {name}: {field}类型异常 ({type(val).__name__})")
                            break

            except Exception as e:
                self.errors.append(f'{name}({code}): 解析错误 - {e}')
                print(f"  ✗ {name}: 解析错误")

        # 检查指数
        for code, name in INDEXES.items():
            filepath = os.path.join(self.kline_dir, f'{code}.json')
            if not os.path.exists(filepath):
                self.warnings.append(f'{name}({code}): 指数日K文件不存在')
                print(f"  ⚠ {name}: 文件缺失")
                continue

            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                bars = data.get('data') or []
                self.ok_count += 1
                print(f"  ✓ {name}: {len(bars)}条")
            except Exception as e:
                self.errors.append(f'{name}({code}): 指数解析错误 - {e}')
                print(f"  ✗ {name}: 解析错误")

    def check_5min_kline(self):
        """检查5分钟K线数据完整性"""
        print("\n【5分钟K线数据检查】")

        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        for code, name in ALL_STOCKS.items():
            # 检查今日
            for check_date in [today, yesterday]:
                filepath = os.path.join(self.kline_5min_dir, f'{code}_{check_date}.json')
                if not os.path.exists(filepath):
                    if check_date == today:
                        self.warnings.append(f'{name}({code}): 今日5分钟数据缺失')
                        print(f"  ⚠ {name}: {check_date}数据缺失")
                    continue

                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    bars = data.get('bars', [])
                    count = data.get('count', len(bars))

                    if count >= 48:
                        self.ok_count += 1
                        print(f"  ✓ {name} {check_date}: {count}根K线")
                    elif count > 0:
                        self.warnings.append(f'{name}({code}): 5分钟数据不足 ({count}根)')
                        print(f"  ⚠ {name} {check_date}: {count}根K线")
                    else:
                        self.errors.append(f'{name}({code}): 5分钟数据为空')
                        print(f"  ✗ {name} {check_date}: 数据为空")

                    # 校验数据类型
                    if bars:
                        sample = bars[0]
                        for field in ('open', 'high', 'low', 'close', 'volume', 'amount'):
                            val = sample.get(field)
                            if val is not None and not isinstance(val, (int, float)):
                                self.errors.append(f'{name}({code}): 5min {field}值类型异常 {type(val).__name__}')
                                print(f"  ✗ {name}: {field}类型异常 ({type(val).__name__})")
                                break

                except Exception as e:
                    self.errors.append(f'{name}({code}): 5min解析错误 - {e}')
                    print(f"  ✗ {name} {check_date}: 解析错误")

        # 检查指数5分钟K线
        for code, name in INDEXES.items():
            for check_date in [today, yesterday]:
                filepath = os.path.join(self.kline_5min_dir, f'{code}_{check_date}.json')
                if not os.path.exists(filepath):
                    if check_date == today:
                        self.warnings.append(f'{name}({code}): 今日5分钟数据缺失')
                        print(f"  ⚠ {name}: {check_date}数据缺失")
                    continue

                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    bars = data.get('bars', [])
                    count = data.get('count', len(bars))

                    if count >= 48:
                        self.ok_count += 1
                        print(f"  ✓ {name} {check_date}: {count}根K线")
                    elif count > 0:
                        self.warnings.append(f'{name}({code}): 5分钟数据不足 ({count}根)')
                        print(f"  ⚠ {name} {check_date}: {count}根K线")
                    else:
                        self.errors.append(f'{name}({code}): 5分钟数据为空')
                        print(f"  ✗ {name} {check_date}: 数据为空")

                except Exception as e:
                    self.errors.append(f'{name}({code}): 5min解析错误 - {e}')
                    print(f"  ✗ {name} {check_date}: 解析错误")

    def check_5min_history(self):
        """检查5分钟K线历史覆盖天数"""
        print("\n【5分钟K线历史覆盖】")

        for code, name in ALL_STOCKS.items():
            files = [f for f in os.listdir(self.kline_5min_dir) if f.startswith(f'{code}_') and f.endswith('.json')]
            dates = sorted(f.replace(f'{code}_', '').replace('.json', '') for f in files)

            if not dates:
                self.warnings.append(f'{name}({code}): 无5分钟历史数据')
                print(f"  ⚠ {name}: 无历史数据")
                continue

            self.ok_count += 1
            print(f"  ✓ {name}: {len(dates)}天 ({dates[0]} ~ {dates[-1]})")

        # 检查指数5分钟历史覆盖
        for code, name in INDEXES.items():
            files = [f for f in os.listdir(self.kline_5min_dir) if f.startswith(f'{code}_') and f.endswith('.json')]
            dates = sorted(f.replace(f'{code}_', '').replace('.json', '') for f in files)

            if not dates:
                self.warnings.append(f'{name}({code}): 无5分钟历史数据')
                print(f"  ⚠ {name}: 无历史数据")
                continue

            self.ok_count += 1
            print(f"  ✓ {name}: {len(dates)}天 ({dates[0]} ~ {dates[-1]})")

    def check_meta(self):
        """检查元数据"""
        print("\n【元数据检查】")

        meta_file = os.path.join(self.base_dir, 'meta.json')
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                stocks = meta.get('stocks', {})
                indexes = meta.get('indexes', {})
                print(f"  ✓ meta.json: {len(stocks)}只股票, {len(indexes)}个指数")
                self.ok_count += 1
                print(f"    更新时间: {meta.get('updated_at', '未知')}")
            except Exception as e:
                self.errors.append(f'meta.json: 解析错误 - {e}')
                print(f"  ✗ meta.json: 解析错误")
        else:
            self.warnings.append('meta.json: 不存在')
            print(f"  ⚠ meta.json: 不存在")

    def check_supplemental_data(self):
        """检查补充数据"""
        print("\n【补充数据检查】")

        # PE/PB
        pe_path = os.path.join(self.quotes_dir, 'pe_pb.json')
        if os.path.exists(pe_path):
            try:
                with open(pe_path, 'r') as f:
                    data = json.load(f)
                count = len(data.get('data', {}))
                self.ok_count += 1
                print(f"  ✓ PE/PB: {count}只 ({data.get('updated_at', '未知')})")
            except Exception as e:
                self.errors.append(f'PE/PB: 解析错误 - {e}')
                print(f"  ✗ PE/PB: 解析错误")
        else:
            self.warnings.append('PE/PB数据不存在')
            print(f"  ⚠ PE/PB数据不存在")

        # 涨跌家数
        market_path = os.path.join(self.market_dir, 'stats.json')
        if os.path.exists(market_path):
            try:
                with open(market_path, 'r') as f:
                    data = json.load(f)
                self.ok_count += 1
                print(f"  ✓ 涨跌统计: 涨{data.get('up')} 跌{data.get('down')} 总{data.get('total')}")
            except Exception as e:
                self.errors.append(f'涨跌统计: 解析错误 - {e}')
                print(f"  ✗ 涨跌统计: 解析错误")
        else:
            self.warnings.append('涨跌统计数据不存在')
            print(f"  ⚠ 涨跌统计数据不存在")

        # 龙虎榜
        lhb_files = [f for f in os.listdir(self.lhb_dir) if f.endswith('.json')] if os.path.exists(self.lhb_dir) else []
        if lhb_files:
            today_file = os.path.join(self.lhb_dir, f'{datetime.now().strftime("%Y-%m-%d")}.json')
            if os.path.exists(today_file):
                with open(today_file, 'r') as f:
                    data = json.load(f)
                self.ok_count += 1
                print(f"  ✓ 龙虎榜: {data.get('count', 0)}条 ({datetime.now().strftime('%Y-%m-%d')})")
            else:
                self.warnings.append(f'龙虎榜今日数据缺失')
                print(f"  ⚠ 龙虎榜今日数据缺失")
        else:
            self.warnings.append('龙虎榜数据不存在')
            print(f"  ⚠ 龙虎榜数据不存在")

        # 北向资金
        north_path = os.path.join(self.north_dir, 'history.json')
        if os.path.exists(north_path):
            try:
                with open(north_path, 'r') as f:
                    data = json.load(f)
                self.ok_count += 1
                print(f"  ✓ 北向资金: {data.get('count', 0)}条历史")
            except Exception as e:
                self.errors.append(f'北向资金: 解析错误 - {e}')
                print(f"  ✗ 北向资金: 解析错误")
        else:
            self.warnings.append('北向资金数据不存在')
            print(f"  ⚠ 北向资金数据不存在")

        # 融资融券
        margin_files = [f for f in os.listdir(self.margin_dir) if f.endswith('.json')] if os.path.exists(self.margin_dir) else []
        if margin_files:
            today_file = os.path.join(self.margin_dir, f'{datetime.now().strftime("%Y-%m-%d")}.json')
            if os.path.exists(today_file):
                with open(today_file, 'r') as f:
                    data = json.load(f)
                self.ok_count += 1
                print(f"  ✓ 融资融券: 沪{data.get('sh_count', 0)}条 深{data.get('sz_count', 0)}条")
            else:
                self.warnings.append('融资融券今日数据缺失')
                print(f"  ⚠ 融资融券今日数据缺失")
        else:
            self.warnings.append('融资融券数据不存在')
            print(f"  ⚠ 融资融券数据不存在")

        # 限售解禁
        restrict_files = [f for f in os.listdir(self.restrict_dir) if f.endswith('.json')] if os.path.exists(self.restrict_dir) else []
        if restrict_files:
            today_file = os.path.join(self.restrict_dir, f'{datetime.now().strftime("%Y-%m-%d")}.json')
            if os.path.exists(today_file):
                with open(today_file, 'r') as f:
                    data = json.load(f)
                self.ok_count += 1
                print(f"  ✓ 限售解禁: {data.get('count', 0)}条")
            else:
                self.warnings.append('限售解禁今日数据缺失')
                print(f"  ⚠ 限售解禁今日数据缺失")
        else:
            self.warnings.append('限售解禁数据不存在')
            print(f"  ⚠ 限售解禁数据不存在")

        # 财务指标
        fin_files = [f for f in os.listdir(self.financial_dir) if f.endswith('.json')] if os.path.exists(self.financial_dir) else []
        if fin_files:
            today_file = os.path.join(self.financial_dir, f'{datetime.now().strftime("%Y-%m-%d")}.json')
            if os.path.exists(today_file):
                with open(today_file, 'r') as f:
                    data = json.load(f)
                count = len(data.get('data', {}))
                self.ok_count += 1
                print(f"  ✓ 财务指标: {count}只股票")
            else:
                self.warnings.append('财务指标今日数据缺失')
                print(f"  ⚠ 财务指标今日数据缺失")
        else:
            self.warnings.append('财务指标数据不存在')
            print(f"  ⚠ 财务指标数据不存在")

        # 数据汇总
        summary_path = os.path.join(self.base_dir, 'data_summary.json')
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r') as f:
                    summary = json.load(f)
                self.ok_count += 1
                print(f"  ✓ 数据汇总: {summary.get('updated_at', '未知')}")
            except Exception as e:
                self.errors.append(f'数据汇总: 解析错误 - {e}')
                print(f"  ✗ 数据汇总: 解析错误")
        else:
            self.warnings.append('data_summary.json 不存在')
            print(f"  ⚠ data_summary.json 不存在")

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
    checker.check_5min_history()
    checker.check_meta()
    checker.check_supplemental_data()
    return checker.generate_report()


if __name__ == '__main__':
    sys.exit(main())
