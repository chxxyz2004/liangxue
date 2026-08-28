#!/bin/bash
# 量学案例自动生成脚本
# 每日运行，更新案例数据和回测结果

echo "=== 量学案例自动更新 $(date '+%Y-%m-%d %H:%M') ==="

# 切换到工作目录
cd /workspace

# 拉取最新K线数据
echo "正在拉取K线数据..."
python3 /workspace/行情数据库/pull_data.py --all 2>/dev/null

# 生成案例
echo "正在生成案例..."
python3 /workspace/讲义生成器/generate_cases.py --summary --output /workspace/现代量学讲义/案例报告_$(date +%Y%m%d).md

# 生成个股案例
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/workspace/讲义生成器')
sys.path.insert(0, '/workspace/行情数据库')
from generate_cases import analyze_stock, generate_case_study
from config import HOLDINGS, WATCH_LIST

for sym in {**HOLDINGS, **WATCH_LIST}.keys():
    data = analyze_stock(sym)
    if data:
        case = generate_case_study(data)
        path = f'/workspace/现代量学讲义/案例_{data["name"]}.md'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(case)
PYEOF

# 更新回测报告
echo "正在更新回测报告..."
python3 /workspace/回测分析/backtest_engine.py --summary > /workspace/回测分析/reports/backtest_$(date +%Y%m%d).json 2>&1

echo "=== 更新完成 ==="

# 生成复盘日报和盘前预案
echo "正在生成复盘日报和盘前预案..."
python3 /workspace/盘前预案/preplan_generator.py --type review --output /workspace/现代量学讲义/复盘日报.md
python3 /workspace/盘前预案/preplan_generator.py --type preplan --output /workspace/现代量学讲义/盘前预案.md

echo "复盘日报和盘前预案已更新"

# 生成K线图表
echo "正在生成K线图表..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/workspace/行情数据库')
sys.path.insert(0, '/workspace/技术指标')
from config import HOLDINGS, WATCH_LIST
from indicator_engine import load_kline, calc_ma, calc_macd, calc_kdj, calc_rsi, calc_boll
import os

os.makedirs('/workspace/现代量学讲义/图表', exist_ok=True)

for sym in list(HOLDINGS.keys()) + list(WATCH_LIST.keys()):
    data = load_kline(sym)
    if data and 'data' in data:
        klines = data['data'][-60:]
        info = HOLDINGS.get(sym, WATCH_LIST.get(sym, None))
        name = info.name if info else sym
        
        path = f'/workspace/现代量学讲义/图表/chart_{sym}.html'
        # 简化版本：只保存路径标记
        with open(path, 'w') as f:
            f.write(f'<div>图表: {name} ({sym}) - {klines[-1]["day"]}</div>')
PYEOF

echo "K线图表已更新"
