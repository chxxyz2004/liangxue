#!/bin/bash
# 自动复盘生成脚本
# 收盘后运行，结合日K数据和5分钟对倒检测结果

cd /workspace/行情数据库

# 获取今日日期
TODAY=$(date '+%Y-%m-%d')

# 检查本地5分钟数据是否存在
if [ ! -d "kline_5min" ] || [ -z "$(ls kline_5min/*.json 2>/dev/null)" ]; then
    echo "[$TODAY] 无5分钟数据，先入库..."
    python3 pull_5min.py >> /tmp/liangxue_review.log 2>&1
fi

# 运行对倒检测并保存结果
python3 /workspace/现代量学讲义/detect_spoofing.py > /tmp/liangxue_spoofing_result.txt 2>&1

echo "[$TODAY $(date '+%H:%M:%S')] 复盘数据准备完成，对倒检测结果: $(wc -l < /tmp/liangxue_spoofing_result.txt) 行" >> /tmp/liangxue_review.log
