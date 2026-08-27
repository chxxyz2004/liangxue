#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送通知模块
支持企业微信、飞书、钉钉等 webhook 推送
借鉴自 daily_stock_analysis 项目
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict, Any

class NotificationManager:
    def __init__(self):
        self.config = self._load_config()
        self.stats = {
            'total_sent': 0,
            'success': 0,
            'failed': 0
        }
    
    def _load_config(self) -> Dict:
        """加载推送配置"""
        config_file = os.path.join(os.path.dirname(__file__), 'notify_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认配置（需要从环境变量或配置文件读取）
        return {
            'wechat_webhook': os.environ.get('WECHAT_WEBHOOK_URL', ''),
            'feishu_webhook': os.environ.get('FEISHU_WEBHOOK_URL', ''),
            'dingtalk_webhook': os.environ.get('DINGTALK_WEBHOOK_URL', ''),
            'enabled': {
                'wechat': bool(os.environ.get('WECHAT_WEBHOOK_URL')),
                'feishu': bool(os.environ.get('FEISHU_WEBHOOK_URL')),
                'dingtalk': bool(os.environ.get('DINGTALK_WEBHOOK_URL'))
            }
        }
    
    def send_report(self, report: str, title: str = "量学系统日报", 
                   channels: List[str] = None) -> bool:
        """发送报告到指定渠道"""
        if channels is None:
            channels = [k for k, v in self.config['enabled'].items() if v]
        
        if not channels:
            print("⚠ 没有启用的推送渠道")
            return False
        
        success_channels = []
        for channel in channels:
            try:
                if channel == 'wechat' and self.config['enabled']['wechat']:
                    self._send_wechat(report, title)
                    success_channels.append('企业微信')
                elif channel == 'feishu' and self.config['enabled']['feishu']:
                    self._send_feishu(report, title)
                    success_channels.append('飞书')
                elif channel == 'dingtalk' and self.config['enabled']['dingtalk']:
                    self._send_dingtalk(report, title)
                    success_channels.append('钉钉')
                
                self.stats['success'] += 1
            except Exception as e:
                print(f"⚠ {channel}推送失败: {e}")
                self.stats['failed'] += 1
        
        self.stats['total_sent'] += 1
        
        if success_channels:
            print(f"✓ 推送成功: {', '.join(success_channels)}")
            return True
        else:
            print("✗ 所有推送渠道均失败")
            return False
    
    def _send_wechat(self, content: str, title: str = ""):
        """发送企业微信消息"""
        if not self.config['wechat_webhook']:
            raise ValueError("未配置企业微信Webhook")
        
        # 企业微信机器人消息格式
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n\n{content}"
            }
        }
        
        url = self.config['wechat_webhook']
        data = json.dumps(message).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={
            'Content-Type': 'application/json'
        }, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('errcode', 0) != 0:
                raise ValueError(f"企业微信API错误: {result.get('errmsg')}")
    
    def _send_feishu(self, content: str, title: str = ""):
        """发送飞书消息"""
        if not self.config['feishu_webhook']:
            raise ValueError("未配置飞书Webhook")
        
        # 飞书机器人消息格式
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [{
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                }]
            }
        }
        
        url = self.config['feishu_webhook']
        data = json.dumps(message).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={
            'Content-Type': 'application/json'
        }, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code', 0) != 0:
                raise ValueError(f"飞书API错误: {result.get('msg')}")
    
    def _send_dingtalk(self, content: str, title: str = ""):
        """发送钉钉消息"""
        if not self.config['dingtalk_webhook']:
            raise ValueError("未配置钉钉Webhook")
        
        # 钉钉机器人消息格式
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }
        
        url = self.config['dingtalk_webhook']
        data = json.dumps(message).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={
            'Content-Type': 'application/json'
        }, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('errcode', 0) != 0:
                raise ValueError(f"钉钉API错误: {result.get('errmsg')}")
    
    def generate_daily_report(self, stocks_data: List[Dict], market_data: Dict) -> str:
        """生成日报格式"""
        report = f"**量学系统日报** • {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # 大盘概况
        report += "## 📊 大盘概况\n"
        for idx in market_data.get('indexes', []):
            report += f"- {idx.get('name', '')}: {idx.get('price', 0):.2f} ({idx.get('pct_chg', 0):+.2f}%)\n"
        report += "\n"
        
        # 持仓股表现
        report += "## 📈 持仓股表现\n"
        for stock in stocks_data:
            status = "🟢" if stock.get('pct_chg', 0) > 0 else "🔴"
            report += f"{status} {stock.get('name', '')}: {stock.get('price', 0):.2f} ({stock.get('pct_chg', 0):+.2f}%)\n"
        report += "\n"
        
        # 关键信号
        signals = []
        for stock in stocks_data:
            if stock.get('signals'):
                for sig in stock.get('signals', []):
                    signals.append(f"- {stock.get('name', '')}: {sig}")
        
        if signals:
            report += "## ⚠️ 关键信号\n"
            report += "\n".join(signals[:10])  # 最多显示10条
            report += "\n\n"
        
        # 操作建议
        report += "## 📋 操作建议\n"
        report += "- 请查阅详细报告获取具体操作建议\n"
        report += f"- 报告链接: {os.environ.get('REPORT_URL', 'N/A')}\n"
        
        return report
    
    def get_stats(self) -> Dict:
        """获取统计数据"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印统计信息"""
        print("\n=== 推送通知统计 ===")
        print(f"总发送次数: {self.stats['total_sent']}")
        print(f"成功: {self.stats['success']}, 失败: {self.stats['failed']}")

# 全局管理器实例
notif_manager = NotificationManager()

def main():
    """测试推送通知模块"""
    print("测试推送通知模块...")
    print("=" * 60)
    
    # 生成测试报告
    test_stocks = [
        {'name': '工业富联', 'code': 'sh601138', 'price': 63.48, 'pct_chg': 6.45, 
         'signals': ['放量滞涨', '长上影']},
        {'name': '胜宏科技', 'code': 'sz300476', 'price': 260.47, 'pct_chg': -2.34,
         'signals': ['缩量回调']},
        {'name': '淳中科技', 'code': 'sh603516', 'price': 93.03, 'pct_chg': 3.21,
         'signals': ['倍量柱', '突破生命线']},
    ]
    
    test_market = {
        'indexes': [
            {'name': '上证指数', 'price': 3250.12, 'pct_chg': 0.85},
            {'name': '深证成指', 'price': 10521.36, 'pct_chg': 1.02},
            {'name': '创业板指', 'price': 2156.78, 'pct_chg': 1.35},
        ]
    }
    
    report = notif_manager.generate_daily_report(test_stocks, test_market)
    print("\n生成的报告:")
    print(report)
    
    # 尝试推送（需要配置Webhook）
    print("\n尝试推送...")
    # notif_manager.send_report(report, "量学系统日报")
    print("（跳过实际推送，需配置Webhook）")
    
    # 打印统计
    notif_manager.print_stats()

if __name__ == '__main__':
    main()
