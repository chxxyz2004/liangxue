#!/bin/bash
# 量学系统 - 一键部署脚本
# 在 Ubuntu 24.04 上运行

set -e

echo "======================================"
echo "  量学系统部署脚本"
echo "======================================"

# 1. 安装依赖
echo "[1/5] 安装依赖..."
apt update && apt install -y git python3 python3-pip python3-venv
pip3 install --break-system-packages requests -q

# 2. 克隆代码
echo "[2/5] 克隆代码..."
cd /opt
if [ ! -d "liangxue" ]; then
    git clone https://github.com/chxxyz2004/liangxue.git
else
    cd liangxue && git pull
fi

# 3. 创建定时任务（每日更新数据）
echo "[3/5] 配置定时任务..."
(crontab -l 2>/dev/null | grep -v "update_data.py"; echo "0 9 * * * cd /opt/liangxue/行情数据库 && python3 update_data.py >> /var/log/liangxue_update.log 2>&1") | crontab -
echo "  ✓ 已设置每日9:00自动更新数据"

# 4. 启动服务
echo "[4/5] 启动服务..."
nohup python3 /opt/liangxue/行情数据库/server.py 8086 > /var/log/liangxue.log 2>&1 &
sleep 2

# 5. 验证
echo "[5/5] 验证部署..."
if curl -s http://127.0.0.1:8086/api/overview | grep -q "total_value"; then
    echo "======================================"
    echo "  部署成功！"
    echo "======================================"
    echo ""
    echo "访问地址:"
    echo "  内网: http://<Ubuntu_IP>:8086"
    echo "  外网: 通过1Panel配置域名反代"
    echo ""
    echo "管理命令:"
    echo "  查看日志: tail -f /var/log/liangxue.log"
    echo "  停止服务: pkill -f server.py"
    echo "  重启服务: nohup python3 /opt/liangxue/行情数据库/server.py 8086 > /var/log/liangxue.log 2>&1 &"
    echo ""
    echo "数据目录: /opt/liangxue/行情数据库/kline/"
    echo "日志文件: /var/log/liangxue.log"
else
    echo "  ✗ 启动失败，请检查日志"
    exit 1
fi
