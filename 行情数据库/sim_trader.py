# -*- coding: utf-8 -*-
"""
模拟盘系统 v2.0
实现：账户管理 + 仓位控制 + 止损止盈 + 交易记录 + 绩效分析
改进：基于K线日序回测，避免重复信号
"""
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from liangxue_engine import KeyBarDetector, VolumeBarDetector, LiangXueEngine
from strategy_backtest import MarketEnvFactor

SIM_ACCOUNT_PATH = '/workspace/行情数据库/sim_account.json'


class SimAccount:
    """模拟账户：现金 + 持仓 + 交易记录 + 净值曲线"""

    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
        self.daily_nav = []
        self.max_equity = initial_capital
        self.max_drawdown = 0.0
        self.total_return = 0.0

    def load(self):
        if os.path.exists(SIM_ACCOUNT_PATH):
            try:
                with open(SIM_ACCOUNT_PATH) as f:
                    data = json.load(f)
                self.cash = data.get('cash', self.initial_capital)
                self.positions = data.get('positions', {})
                self.trades = data.get('trades', [])
                self.daily_nav = data.get('daily_nav', [])
                self.max_equity = data.get('max_equity', self.initial_capital)
                self.max_drawdown = data.get('max_drawdown', 0.0)
                self.total_return = data.get('total_return', 0.0)
                return True
            except Exception as e:
                print(f"[模拟盘] 加载失败: {e}，使用新账户")
        return False

    def save(self):
        with open(SIM_ACCOUNT_PATH, 'w') as f:
            json.dump({
                'cash': self.cash, 'positions': self.positions,
                'trades': self.trades, 'daily_nav': self.daily_nav,
                'max_equity': self.max_equity,
                'max_drawdown': self.max_drawdown,
                'total_return': self.total_return,
                'updated_at': datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)

    def get_total_equity(self, price_dict=None):
        """总资产 = 现金 + 持仓市值"""
        pos_value = 0
        for code, pos in self.positions.items():
            p = price_dict.get(code, pos['cost']) if price_dict else pos['cost']
            pos_value += pos['shares'] * p
        return self.cash + pos_value

    def record_daily_nav(self, date, price_dict=None):
        """记录每日净值"""
        equity = self.get_total_equity(price_dict)
        self.daily_nav.append({'date': date, 'equity': round(equity, 2)})
        if equity > self.max_equity:
            self.max_equity = equity
        dd = (self.max_equity - equity) / self.max_equity if self.max_equity > 0 else 0
        if dd > self.max_drawdown:
            self.max_drawdown = dd
        self.total_return = (equity - self.initial_capital) / self.initial_capital

    def buy(self, code, name, shares, price, reason, strategy='default', stop_loss=None, take_profit=None):
        """买入"""
        cost = shares * price * 1.0003
        if cost > self.cash:
            shares = int(self.cash / (price * 1.0003) / 100) * 100
            if shares <= 0:
                return False, "资金不足"
            cost = shares * price * 1.0003
        self.cash -= cost
        if code not in self.positions:
            self.positions[code] = {'shares': 0, 'cost': 0, 'entry_date': '', 'name': name,
                                     'stop_loss': stop_loss, 'take_profit': take_profit, 'strategy': strategy}
        pos = self.positions[code]
        old_val = pos['cost'] * pos['shares']
        pos['shares'] += shares
        pos['cost'] = (old_val + cost) / pos['shares']
        if not pos['entry_date']:
            pos['entry_date'] = datetime.now().strftime('%Y-%m-%d')
        pos['stop_loss'] = stop_loss
        pos['take_profit'] = take_profit
        pos['strategy'] = strategy
        self.trades.append({'time': datetime.now().isoformat(), 'action': 'BUY', 'code': code,
                            'name': name, 'shares': shares, 'price': price, 'cost': cost,
                            'reason': reason, 'strategy': strategy,
                            'stop_loss': stop_loss, 'take_profit': take_profit})
        self.save()
        return True, f"买入 {name} {shares}股 @{price:.2f}"

    def sell(self, code, shares, price, reason):
        """卖出"""
        if code not in self.positions or self.positions[code]['shares'] < shares:
            return False, "持仓不足"
        pos = self.positions[code]
        revenue = shares * price * 0.9997
        pnl = revenue - shares * pos['cost']
        pnl_pct = pnl / (shares * pos['cost']) if shares * pos['cost'] > 0 else 0
        self.cash += revenue
        pos['shares'] -= shares
        if pos['shares'] <= 0:
            del self.positions[code]
        self.trades.append({'time': datetime.now().isoformat(), 'action': 'SELL', 'code': code,
                            'name': pos.get('name', code), 'shares': shares, 'price': price,
                            'pnl': round(pnl, 2), 'pnl_pct': round(pnl_pct, 4),
                            'reason': reason, 'strategy': pos.get('strategy', 'default')})
        self.save()
        return True, f"卖出 {pos.get('name', code)} {shares}股 @{price:.2f} PnL={pnl:+.0f}({pnl_pct:+.1%})"


class SimTrader:
    """
    模拟交易员：基于量学信号逐日回测
    核心改进：按K线日期顺序推进，每日只处理当天的买入/卖出
    """

    def __init__(self, initial_capital=100000):
        self.account = SimAccount(initial_capital)
        self.account.load()
        self.market_env = MarketEnvFactor()
        self.stocks = {
            'sh601138': '工业富联', 'sz300476': '胜宏科技', 'sz300394': '天孚通信',
            'sh603516': '淳中科技', 'sz002156': '通富微电', 'sh600584': '长电科技',
            'sh603283': '赛腾股份', 'sh601231': '环旭电子',
        }
        self._signal_cache = {}

    def load_kline(self, code):
        path = os.path.join('/workspace/行情数据库/kline', f'{code}.json')
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f).get('data', [])

    def build_signal_map(self, kl, env_score, code, name):
        """
        预先构建全量信号映射：{买入日期: {信号信息}}
        只计算一次，供每日回测使用
        """
        if not kl or len(kl) < 60:
            return {}

        adj = self.market_env.get_threshold_adjustment(env_score)
        vol_min = adj['vol_ratio_min']
        min_dd = adj['min_drawdown']
        n = len(kl)
        signals = {}  # {date_str: signal_info}

        for i in range(10, n - 1):
            v_prev = kl[i-1].get('volume', 0)
            v_curr = kl[i].get('volume', 0)
            if v_prev <= 0:
                continue
            ratio = v_curr / v_prev
            close_p, open_p = kl[i].get('close', 0), kl[i].get('open', 0)
            if ratio < vol_min or close_p < open_p:
                continue

            dbl_high, dbl_low = kl[i].get('high', 0), kl[i].get('low', 0)
            dbl_body = dbl_high - dbl_low
            if dbl_body <= 0:
                continue

            for j in range(i + 1, min(i + 10, n)):
                k = kl[j]
                if k.get('volume', 0) >= v_curr * 0.9:
                    continue
                drawdown = (dbl_high - k['low']) / dbl_body
                if drawdown > 1.0:
                    break

                if drawdown < min_dd:
                    key_type = '黄金柱'
                elif drawdown <= 0.5:
                    key_type = '元帅柱' if drawdown >= 1/3 else '黄金柱'
                else:
                    key_type = '将军柱'

                buy_idx = j + 1
                if buy_idx >= n:
                    break

                buy_date = kl[buy_idx].get('day', '')[:10]
                buy_price = kl[buy_idx].get('open', kl[buy_idx].get('close', 0))
                if buy_price <= 0:
                    continue

                stop_loss = k['low'] * 0.98
                take_profit = buy_price * 1.15

                signals[buy_date] = {
                    'code': code, 'name': name, 'action': 'BUY',
                    'price': buy_price, 'key_type': key_type,
                    'drawdown': round(drawdown, 3),
                    'stop_loss': round(stop_loss, 2),
                    'take_profit': round(take_profit, 2),
                    'reason': f'{key_type}信号，回调{drawdown:.0%}实体',
                }
                break  # 每个倍量柱只产生一个信号

        return signals

    def run_simulation(self, max_days=60):
        """
        运行模拟交易：按K线日期顺序逐日回测
        """
        env_info, pos_config = self.analyze_market_env()
        env_score = env_info['score']

        # 收集所有股票的最新日期
        all_dates = set()
        stock_kl = {}
        for code, name in self.stocks.items():
            kl = self.load_kline(code)
            if kl:
                stock_kl[code] = kl
                for k in kl:
                    all_dates.add(k.get('day', '')[:10])

        sorted_dates = sorted(all_dates, reverse=True)  # 从最新到最旧
        sorted_dates = sorted_dates[:max_days]  # 只回测最近max_days天

        print(f"\n{'='*70}")
        print(f"  模拟盘回测 | 资金: 100,000 | 环境: {env_info['state']}({env_info['score']}) "
              f"周期: {sorted_dates[0]} ~ {sorted_dates[-1]} ({len(sorted_dates)}天)")
        print(f"{'='*70}")

        # 预构建所有信号
        for code, name in self.stocks.items():
            if code in stock_kl:
                sigs = self.build_signal_map(stock_kl[code], env_score, code, name)
                self._signal_cache.update(sigs)

        executed_buys = set()  # 记录已执行的买入日期+代码，防重复

        for date_str in sorted_dates:
            # --- 获取当日收盘价 ---
            current_prices = {}
            for code, kl in stock_kl.items():
                for k in kl:
                    if k.get('day', '')[:10] == date_str:
                        current_prices[code] = k.get('close', k.get('open', 0))
                        break

            # --- 检查持仓止损止盈 ---
            for code in list(self.account.positions.keys()):
                if code not in current_prices:
                    continue
                price = current_prices[code]
                pos = self.account.positions[code]
                sl, tp = pos.get('stop_loss'), pos.get('take_profit')
                if sl and price <= sl:
                    ok, msg = self.account.sell(code, pos['shares'], price, f"止损 @{sl:.2f}")
                    if ok:
                        print(f"  [{date_str}] 止损 {pos.get('name', code)} @{price:.2f}")
                elif tp and price >= tp:
                    ok, msg = self.account.sell(code, pos['shares'], price, f"止盈 @{tp:.2f}")
                    if ok:
                        print(f"  [{date_str}] 止盈 {pos.get('name', code)} @{price:.2f}")

            # --- 执行买入（仅当日有信号且未执行过）---
            if date_str in self._signal_cache:
                sig = self._signal_cache[date_str]
                key = (sig['code'], date_str)
                if key in executed_buys:
                    continue
                executed_buys.add(key)
                if sig['code'] not in self.account.positions:
                    buy_price = sig['price'] * 1.001
                    available = self.account.cash * pos_config['factor']
                    single_max = available * 0.5  # 单只最大50%
                    shares = int(single_max / buy_price / 100) * 100
                    if shares > 0:
                        ok, msg = self.account.buy(
                            sig['code'], sig['name'], shares, buy_price,
                            sig['reason'], strategy=sig['key_type'],
                            stop_loss=sig['stop_loss'], take_profit=sig['take_profit'])
                        if ok:
                            print(f"  [{date_str}] 买入 {sig['name']} {shares}股 @{buy_price:.2f} ({sig['key_type']})")

            # --- 记录净值 ---
            self.account.record_daily_nav(date_str, current_prices)

        self._print_final_report()

    def analyze_market_env(self):
        env_info = self.market_env.get_env_score()
        pos_config = self.market_env.get_position_adjustment(env_info['score'])
        print(f"[市场环境] {env_info['state']} 得分:{env_info['score']} "
              f"仓位系数:{pos_config['factor']:.0%} | {pos_config['reason']}")
        return env_info, pos_config

    def _print_final_report(self):
        equity = self.account.get_total_equity()
        pnl = equity - self.account.initial_capital
        pnl_pct = pnl / self.account.initial_capital

        sells = [t for t in self.account.trades if t.get('action') == 'SELL']
        wins = [t for t in sells if t.get('pnl', 0) > 0]
        losses = [t for t in sells if t.get('pnl', 0) <= 0]
        win_rate = len(wins) / len(sells) * 100 if sells else 0

        avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else -0.01
        pl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 999

        print(f"\n{'='*70}")
        print(f"  模拟盘结束")
        print(f"  初始资金: {self.account.initial_capital:,.0f}")
        print(f"  最终净值: {equity:,.0f}")
        print(f"  总盈亏:   {pnl:+,.0f} ({pnl_pct:+.2%})")
        print(f"  最大回撤: {self.account.max_drawdown:.2%}")
        print(f"  交易次数: {len(self.account.trades)} | 胜率: {win_rate:.1f}%")
        print(f"  平均盈利: {avg_win:+.0f} | 平均亏损: {avg_loss:+.0f} | 盈亏比: {pl_ratio:.2f}")
        print(f"{'='*70}")

        report = {
            'initial_capital': self.account.initial_capital,
            'final_equity': round(equity, 2),
            'total_pnl': round(pnl, 2),
            'total_pnl_pct': round(pnl_pct, 4),
            'max_drawdown': round(self.account.max_drawdown, 4),
            'total_trades': len(self.account.trades),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_loss_ratio': round(pl_ratio, 2),
            'daily_nav': self.account.daily_nav[-20:],
            'timestamp': datetime.now().isoformat(),
        }
        with open('/workspace/行情数据库/sim_report.json', 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已保存: /workspace/行情数据库/sim_report.json")


def main():
    trader = SimTrader(initial_capital=100000)
    trader.run_simulation(max_days=60)


if __name__ == '__main__':
    main()
