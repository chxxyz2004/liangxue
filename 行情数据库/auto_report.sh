#!/bin/bash
# 量学报告自动生成脚本
# 根据当前时间生成对应类型的报告

LOG="/tmp/liangxue_report.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] 开始生成报告..." >> $LOG

cd /workspace/现代量学讲义
python3 generate_report.py >> $LOG 2>&1

if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] ✓ 报告生成成功" >> $LOG
else
    echo "[$TIMESTAMP] ✗ 报告生成失败" >> $LOG
fi
