#!/bin/bash
# 量学系统自动更新脚本
# 每日收盘后运行：15:30

cd /workspace/行情数据库

# 1. 更新日K数据
python3 update_data.py >> /tmp/liangxue_update.log 2>&1

# 2. 入库5分钟K线
python3 pull_5min.py >> /tmp/liangxue_5min.log 2>&1

# 3. 运行对倒检测
python3 /workspace/现代量学讲义/detect_spoofing.py >> /tmp/liangxue_spoofing.log 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 自动更新完成" >> /tmp/liangxue_update.log
