#!/bin/bash
# 午盘研判自动生成脚本
# 每日11:30运行

cd /workspace/行情数据库

# 拉取11:30数据并生成午盘报告
python3 pull_5min.py >> /tmp/liangxue_noon.log 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 午盘数据已入库" >> /tmp/liangxue_noon.log
