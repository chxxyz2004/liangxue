#!/usr/bin/env python3
"""
模拟交易模块
记录买卖决策和交易结果
"""
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

TRADE_LOG = '/tmp/liangxue_trades.json'

class TradeLogger:
    def __init__(self):
        self.trades = self.load_trades()
    
    def load_trades(self):
        if os.path.exists(TRADE_LOG):
            try:
                with open(TRADE_LOG, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_trades(self):
        with open(TRADE_LOG, 'w') as f:
            json.dump(self.trades, f, ensure_ascii=False, indent=2)
    
    def add_trade(self, action, code, name, price, quantity, reason, signal_type=None):
        trade = {
            'time': datetime.now().isoformat(),
            'action': action,
            'code': code,
            'name': name,
            'price': price,
            'quantity': quantity,
            'reason': reason,
            'signal_type': signal_type,
            'status': 'pending'
        }
        self.trades.append(trade)
        self.save_trades()
        return trade
    
    def update_trade(self, index, status, result_price=None, pnl=None):
        if index < len(self.trades):
            self.trades[index]['status'] = status
            if result_price is not None:
                self.trades[index]['result_price'] = result_price
            if pnl is not None:
                self.trades[index]['pnl'] = pnl
    
    def get_pending_trades(self):
        return [t for t in self.trades if t.get('status') == 'pending']
    
    def get_completed_trades(self):
        return [t for t in self.trades if t.get('status') != 'pending']
    
    def get_stats(self):
        completed = self.get_completed_trades()
        if not completed:
            return {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0}
        
        wins = len([t for t in completed if t.get('pnl', 0) > 0])
        losses = len([t for t in completed if t.get('pnl', 0) <= 0])
        
        return {
            'total': len(completed),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(completed) * 100
        }

def main():
    logger = TradeLogger()
    
    print("模拟交易模块")
    print("=" * 60)
    
    print("\\n【待执行交易】")
    pending = logger.get_pending_trades()
    if pending:
        for i, trade in enumerate(pending):
            print(f"{i+1}. {trade['action']} {trade['name']}({trade['code']}) "
                  f"@ {trade['price']} x {trade['quantity']}")
            print(f"   原因: {trade['reason']}")
            print(f"   时间: {trade['time']}")
    else:
        print("  无待执行交易")
    
    print("\\n【历史交易统计】")
    stats = logger.get_stats()
    print(f"  总交易数: {stats['total']}")
    print(f"  盈利: {stats['wins']}")
    print(f"  亏损: {stats['losses']}")
    print(f"  胜率: {stats['win_rate']:.1f}%")
    
    print("\\n【最近交易记录】")
    completed = logger.get_completed_trades()[-5:]
    if completed:
        for trade in completed:
            pnl_str = f"+{trade.get('pnl', 0):.2f}%" if trade.get('pnl', 0) > 0 else f"{trade.get('pnl', 0):.2f}%"
            print(f"  {trade['time'][:10]} {trade['action']} {trade['name']} "
                  f"@ {trade.get('result_price', trade['price'])} "
                  f"收益: {pnl_str}")
    else:
        print("  暂无交易记录")

if __name__ == '__main__':
    main()
