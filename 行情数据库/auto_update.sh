#!/bin/bash
# 量学系统自动更新脚本
# 每日收盘后运行：15:30

LOG="/tmp/liangxue_cron.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始自动更新..." >> $LOG

cd /workspace/行情数据库

# 1. 检查系统健康
python3 system_monitor.py >> $LOG 2>&1
python3 check_integrity.py >> $LOG 2>&1
python3 check_alerts.py >> $LOG 2>&1

# 2. 更新日K数据
python3 update_data.py >> $LOG 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 日K更新失败" >> $LOG
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 日K更新成功" >> $LOG
fi

# 3. 入库5分钟K线
python3 pull_5min.py >> $LOG 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 5分钟K线入库失败" >> $LOG
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 5分钟K线入库成功" >> $LOG
fi

# 4. 全量补充数据采集（PE/PB、龙虎榜、北向资金、融资融券、解禁、财务）
python3 fetch_all_data.py >> $LOG 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 补充数据更新失败" >> $LOG
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 补充数据更新成功" >> $LOG
fi

# 5. 采集产业链行情（新增）
python3 fetch_chain_quotes.py >> $LOG 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 产业链行情采集失败" >> $LOG
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 产业链行情采集成功" >> $LOG
fi

# 6. 采集换手率数据（新增）
python3 fetch_turnover.py >> $LOG 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 换手率采集失败" >> $LOG
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 换手率采集成功" >> $LOG
fi

# 7. 运行对倒检测
python3 /workspace/现代量学讲义/detect_spoofing.py >> $LOG 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 对倒检测失败" >> $LOG
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 对倒检测完成" >> $LOG
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 自动更新完成" >> $LOG
