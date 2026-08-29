-- 个人量化交易系统数据库 schema
-- 版本：v1.0 · 2026-08-29

-- 1. 股票基本信息表
CREATE TABLE IF NOT EXISTS stocks (
    code TEXT PRIMARY KEY,           -- 股票代码 e.g. sh601138
    name TEXT NOT NULL,              -- 股票名称
    industry TEXT,                   -- 所属行业
    chain TEXT,                      -- 产业链 e.g. 英伟达/华为/长鑫/特斯拉
    market TEXT,                     -- 市场 e.g. 主板/创业板/科创板
    list_date TEXT,                  -- 上市日期
    created_at TEXT DEFAULT (datetime('now'))
);

-- 2. 日线K线数据表
CREATE TABLE IF NOT EXISTS daily_kline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,              -- YYYY-MM-DD
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,                  -- 成交量（手）
    amount REAL,                     -- 成交额（元，估算值）
    turnover_rate REAL,              -- 换手率%
    pe_ttm REAL,                     -- PE-TTM
    pb REAL,                         -- PB
    source TEXT DEFAULT 'tencent',   -- 数据源
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

-- 3. 5分钟K线数据表
CREATE TABLE IF NOT EXISTS kline_5min (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    datetime TEXT NOT NULL,          -- YYYY-MM-DD HH:MM:SS
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    amount REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, datetime)
);

-- 4. 技术指标表
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,
    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    ma60 REAL,
    ma120 REAL,
    ma250 REAL,
    vol_ma5 REAL,
    vol_ma20 REAL,
    rsi_14 REAL,
    macd REAL,
    macd_signal REAL,
    macd_hist REAL,
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code, date)
);

-- 5. 量学信号表
CREATE TABLE IF NOT EXISTS liangxue_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,              -- 信号日期
    signal_type TEXT NOT NULL,       -- doubling/golden/marshal/general
    bar_type TEXT,                   -- 倍量柱/黄金柱/元帅柱/将军柱
    volume_ratio REAL,               -- 量比
    drawdown_ratio REAL,             -- 回调幅度
    key_price REAL,                  -- 关键价位（最高价/最低价）
    position_pct REAL,               -- 250日位置百分位
    trend_status TEXT,               -- 趋势状态 bull/bear/sideways
    env_score REAL,                  -- 环境得分
    filter_result TEXT,              -- 五层过滤结果 pass/fail
    filter_reason TEXT,              -- 过滤原因
    created_at TEXT DEFAULT (datetime('now'))
);

-- 6. 模拟交易记录表
CREATE TABLE IF NOT EXISTS sim_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_no TEXT UNIQUE,            -- 交易编号 e.g. T20260829001
    code TEXT NOT NULL,
    name TEXT,
    action TEXT NOT NULL,            -- BUY/SELL
    shares INTEGER,
    price REAL,
    amount REAL,                     -- 交易金额
    commission REAL,                 -- 佣金
    slippage REAL,                   -- 滑点
    pnl REAL,                        -- 盈亏
    pnl_pct REAL,                    -- 盈亏百分比
    strategy TEXT,                   -- 使用的策略
    reason TEXT,                     -- 交易原因
    stop_loss REAL,                  -- 止损价
    take_profit REAL,                -- 止盈价
    hold_days INTEGER,               -- 持有天数
    entry_date TEXT,
    exit_date TEXT,
    status TEXT DEFAULT 'completed', -- pending/completed/cancelled
    created_at TEXT DEFAULT (datetime('now'))
);

-- 7. 模拟账户净值表
CREATE TABLE IF NOT EXISTS sim_portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    cash REAL,
    position_value REAL,
    total_equity REAL,
    daily_return REAL,
    max_equity REAL,
    max_drawdown REAL,
    total_return REAL,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 8. 回测结果表
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_no TEXT UNIQUE,         -- 回测编号 e.g. BT20260829
    code TEXT,
    strategy TEXT,                   -- doubling/golden/marshal/general
    start_date TEXT,
    end_date TEXT,
    total_signals INTEGER,
    total_trades INTEGER,
    win_count INTEGER,
    loss_count INTEGER,
    win_rate REAL,
    avg_return REAL,
    total_return REAL,
    max_profit_loss_ratio REAL,
    max_drawdown REAL,
    sharpe_ratio REAL,
    env_score REAL,                  -- 回测时市场环境得分
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 9. 持仓状态表（当前持仓）
CREATE TABLE IF NOT EXISTS current_positions (
    code TEXT PRIMARY KEY,
    name TEXT,
    shares INTEGER,
    cost_price REAL,
    current_price REAL,
    market_value REAL,
    unrealized_pnl REAL,
    unrealized_pnl_pct REAL,
    stop_loss REAL,
    take_profit REAL,
    entry_date TEXT,
    strategy TEXT,
    last_updated TEXT DEFAULT (datetime('now'))
);

-- 10. 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_level TEXT,                  -- INFO/WARNING/ERROR
    module TEXT,
    message TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 11. 报告发布记录表
CREATE TABLE IF NOT EXISTS report_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT,                -- daily_prep/daily_review/weekly/monthly
    report_date TEXT,
    file_path TEXT,
    status TEXT DEFAULT 'published', -- draft/published/failed
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_daily_kline_code_date ON daily_kline(code, date);
CREATE INDEX IF NOT EXISTS idx_kline_5min_code_datetime ON kline_5min(code, datetime);
CREATE INDEX IF NOT EXISTS idx_liangxue_signals_code_date ON liangxue_signals(code, date);
CREATE INDEX IF NOT EXISTS idx_sim_trades_code_date ON sim_trades(code, created_at);
CREATE INDEX IF NOT EXISTS idx_backtest_results_code_strategy ON backtest_results(code, strategy);
