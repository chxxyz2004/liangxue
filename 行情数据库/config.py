#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量学系统统一配置中心（v3.7 融合版）
=====================================
特性：dataclass类型安全 + 环境变量覆盖 + 全面启动自校验 + logging日志
融合来源：智谱(dataclass/校验/LX_前缀) + Claude(环境封装/目录自动创建) + Gemini(logging)

使用示例：
    from config import HOLDINGS, SPOOFING_THRESHOLDS
    print(HOLDINGS['sh603516'].name)          # '淳中科技'
    print(SPOOFING_THRESHOLDS.vol_ratio_min)  # 2.0

环境变量覆盖规则（前缀 LX_）：
    LX_DATA_DIR                    : 覆盖数据路径
    LX_THRESHOLD_VOL_RATIO_MIN     : 覆盖量比下限
    LX_THRESHOLD_PCT_MAX           : 覆盖最大涨跌幅
    LX_THRESHOLD_UPPER_SHADOW_RATIO: 覆盖上影线/实体比值
    LX_THRESHOLD_PCT_PULSE_MIN     : 覆盖脉冲最小涨幅
    LX_THRESHOLD_PCT_DROP_RETRACE  : 覆盖回撤比例下限
    LX_REPORT_MORNING/NOON/CLOSE/EVENING : 覆盖报告生成时间(HH:MM)
"""

import os
import re
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 类型定义（dataclass 不可变，类型安全）
# ============================================================

@dataclass(frozen=True)
class StockInfo:
    """单只股票的持仓/关注信息。

    Attributes:
        name: 股票中文名。
        cost: 持仓成本价（元）。None 表示未持仓。
        shares: 持仓股数。0 表示未持仓。
        stop_loss: 止损价（元）。None 表示未设置。
        life_line: 生死线价位（元）。None 表示未设置。
        take_profit: 止盈区间（下限, 上限）。None 表示未设置。
    """
    name: str
    cost: Optional[float] = None
    shares: int = 0
    stop_loss: Optional[float] = None
    life_line: Optional[float] = None
    take_profit: Optional[Tuple[float, float]] = None


@dataclass(frozen=True)
class SpoofingThresholds:
    """量化对倒检测阈值（detect_spoofing.py 使用，基于5分钟K线）。"""
    vol_ratio_min: float = 2.0        # 量比下限（成交量 > 5日均量 × 此值）
    pct_max: float = 1.0              # 最大涨跌幅（%），超过则排除对倒
    upper_shadow_ratio: float = 2.0   # 上影线/实体比值下限
    pct_pulse_min: float = 3.0        # 脉冲最小涨幅（%）
    pct_drop_retrace: int = 70        # 回撤比例下限（%）


@dataclass(frozen=True)
class ReportConfig:
    """报告生成时间配置（HH:MM格式）。"""
    morning: str = "09:25"  # 盘前预案
    noon: str = "11:30"     # 午间资金识别
    close: str = "15:00"    # 收盘资金识别
    evening: str = "21:00"  # 联网复盘


# ============================================================
# 环境变量读取辅助函数（带类型转换和默认值）
# ============================================================

def _get_env_str(key: str, default: str) -> str:
    """获取字符串环境变量，不存在返回默认值。"""
    return os.environ.get(key, default)

def _get_env_float(key: str, default: float) -> float:
    """获取浮点环境变量，非法值返回默认值。"""
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        logger.warning(f"环境变量 {key} 值非法，使用默认值 {default}")
        return default

def _get_env_int(key: str, default: int) -> int:
    """获取整数环境变量，非法值返回默认值。"""
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        logger.warning(f"环境变量 {key} 值非法，使用默认值 {default}")
        return default


# ============================================================
# 核心配置（唯一数据源）
# ============================================================

# 持仓股票配置（唯一数据源，所有脚本从此读取，禁止硬编码）
HOLDINGS: Dict[str, StockInfo] = {
    'sh603516': StockInfo(name='淳中科技', cost=98.50, shares=900,
                          stop_loss=90.63, life_line=92.6),
    'sh601138': StockInfo(name='工业富联', cost=58.20, shares=1100),
    'sz002156': StockInfo(name='通富微电', cost=45.80, shares=700),
    'sh601231': StockInfo(name='环旭电子', cost=28.50, shares=800),
    'sz300476': StockInfo(name='胜宏科技', cost=230.00, shares=100,
                          take_profit=(256, 260)),
    'sh603283': StockInfo(name='赛腾股份', cost=52.30, shares=400),
}

# 关注股票池（未持仓）
WATCH_LIST: Dict[str, StockInfo] = {
    'sz300394': StockInfo(name='天孚通信'),
    'sh600584': StockInfo(name='长电科技'),
}

# 大盘指数
INDEXES: Dict[str, str] = {
    'sh000001': '上证指数',
    'sz399001': '深证成指',
    'sz399006': '创业板指',
}

# 数据路径（环境变量 LX_DATA_DIR 覆盖）
DATA_DIR: str = _get_env_str('LX_DATA_DIR', '/workspace/行情数据库/kline')

# 量化对倒检测阈值（环境变量 LX_THRESHOLD_* 覆盖）
SPOOFING_THRESHOLDS: SpoofingThresholds = SpoofingThresholds(
    vol_ratio_min=_get_env_float('LX_THRESHOLD_VOL_RATIO_MIN', 2.0),
    pct_max=_get_env_float('LX_THRESHOLD_PCT_MAX', 1.0),
    upper_shadow_ratio=_get_env_float('LX_THRESHOLD_UPPER_SHADOW_RATIO', 2.0),
    pct_pulse_min=_get_env_float('LX_THRESHOLD_PCT_PULSE_MIN', 3.0),
    pct_drop_retrace=_get_env_int('LX_THRESHOLD_PCT_DROP_RETRACE', 70),
)

# 报告生成配置（环境变量 LX_REPORT_* 覆盖）
REPORT_CONFIG: ReportConfig = ReportConfig(
    morning=_get_env_str('LX_REPORT_MORNING', '09:25'),
    noon=_get_env_str('LX_REPORT_NOON', '11:30'),
    close=_get_env_str('LX_REPORT_CLOSE', '15:00'),
    evening=_get_env_str('LX_REPORT_EVENING', '21:00'),
)


# ============================================================
# 配置验证（启动时自动执行）
# ============================================================

def validate_config() -> None:
    """启动时校验配置完整性与合法性，失败时打印友好错误并退出。"""
    errors = []

    # --- 校验持仓 ---
    if not HOLDINGS:
        errors.append("HOLDINGS 不能为空，请至少配置一只持仓股票")
    for code, info in HOLDINGS.items():
        if not isinstance(code, str) or len(code) != 8 or not code[:2].lower() in ('sh', 'sz'):
            errors.append(f"股票代码格式错误：{code}（应为8位，sh/sz前缀）")
        if info.shares < 0:
            errors.append(f"{info.name}({code}) 持仓股数不能为负")
        if info.cost is not None and info.cost <= 0:
            errors.append(f"{info.name}({code}) 成本价必须为正数")
        if info.take_profit is not None:
            lo, hi = info.take_profit
            if lo >= hi:
                errors.append(f"{info.name}({code}) 止盈区间下限 {lo} 应小于上限 {hi}")

    # --- 校验关注池 ---
    for code, info in WATCH_LIST.items():
        if not isinstance(code, str) or len(code) != 8:
            errors.append(f"关注池代码格式错误：{code}")

    # --- 校验指数 ---
    if not INDEXES:
        errors.append("INDEXES 不能为空")

    # --- 校验数据路径（不存在则自动创建） ---
    if not os.path.isdir(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            logger.warning(f"数据目录 {DATA_DIR} 不存在，已自动创建")
        except OSError:
            errors.append(f"无法创建数据目录 {DATA_DIR}")

    # --- 校验对倒阈值 ---
    t = SPOOFING_THRESHOLDS
    if t.vol_ratio_min <= 0:
        errors.append(f"量比下限必须为正数，当前 {t.vol_ratio_min}")
    if not (0 < t.pct_max < 10):
        errors.append(f"最大涨跌幅应在0-10%之间，当前 {t.pct_max}")
    if not (0 < t.pct_pulse_min < 20):
        errors.append(f"脉冲最小涨幅应在0-20%之间，当前 {t.pct_pulse_min}")
    if not (0 < t.pct_drop_retrace <= 100):
        errors.append(f"回撤比例应在0-100之间，当前 {t.pct_drop_retrace}")

    # --- 校验报告时间格式 ---
    time_pattern = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
    for label, time_str in [('morning', REPORT_CONFIG.morning),
                            ('noon', REPORT_CONFIG.noon),
                            ('close', REPORT_CONFIG.close),
                            ('evening', REPORT_CONFIG.evening)]:
        if not time_pattern.match(time_str):
            errors.append(f"报告时间 {label} 格式错误：{time_str}（应为 HH:MM）")

    # --- 输出结果 ---
    if errors:
        logger.error(f"配置验证失败，共 {len(errors)} 项错误：")
        for i, err in enumerate(errors, 1):
            logger.error(f"  {i}. {err}")
        raise SystemExit(1)
    else:
        logger.info(f"✓ config.py 加载成功（{len(HOLDINGS)}只持仓、{len(WATCH_LIST)}只关注、{len(INDEXES)}个指数）")


# 启动自动校验
validate_config()