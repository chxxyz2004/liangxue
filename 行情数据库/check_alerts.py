#!/usr/bin/env python3
"""
系统错误告警脚本
检测异常情况并记录告警
"""
import os
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/liangxue_alert.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ALERT_LOG = '/tmp/liangxue_alerts.json'

def load_alerts():
    """加载历史告警"""
    if os.path.exists(ALERT_LOG):
        try:
            with open(ALERT_LOG, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_alerts(alerts):
    """保存告警记录（保留最近100条）"""
    alerts = alerts[-100:]
    with open(ALERT_LOG, 'w') as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

def check_alert_conditions():
    """检查告警条件"""
    alerts = load_alerts()
    today = datetime.now().strftime('%Y-%m-%d')
    new_alerts = []
    
    # 检查1: 日志文件大小异常
    log_files = [
        '/tmp/liangxue_update.log',
        '/tmp/liangxue_noon.log',
        '/tmp/liangxue_spoofing.log',
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            if size == 0:
                alert = {
                    'time': datetime.now().isoformat(),
                    'type': 'empty_log',
                    'file': log_file,
                    'message': f'日志文件为空: {os.path.basename(log_file)}'
                }
                new_alerts.append(alert)
                logger.warning(f'告警: {alert["message"]}')
    
    # 检查2: 数据文件缺失
    kline_dir = '/workspace/行情数据库/kline'
    expected = ['sh603516', 'sh601138', 'sh603283', 'sz002156', 
               'sh601231', 'sz300476', 'sh603220', 'sh600629', 'sz300394']
    
    for code in expected:
        filepath = os.path.join(kline_dir, f'{code}.json')
        if not os.path.exists(filepath):
            alert = {
                'time': datetime.now().isoformat(),
                'type': 'missing_data',
                'code': code,
                'message': f'日K数据缺失: {code}'
            }
            new_alerts.append(alert)
            logger.warning(f'告警: {alert["message"]}')
    
    # 保存新告警
    if new_alerts:
        alerts.extend(new_alerts)
        save_alerts(alerts)
    
    return new_alerts

def main():
    logger.info('系统告警检查...')
    new_alerts = check_alert_conditions()
    
    if new_alerts:
        logger.info(f'发现{len(new_alerts)}个新告警')
        return 1
    else:
        logger.info('无新告警')
        return 0

if __name__ == '__main__':
    sys.exit(main())
