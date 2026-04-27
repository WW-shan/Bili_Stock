"""
低波 baseline 在 foundation 下重新验证
========================================
低波因子定义 (CLAUDE.md 中描述):
  - 60 日收益标准差, 取最低 (波动率倒数 → 低波得分高)
  - 入选: 顶 80th 百分位
  - hold_step: 12 个交易日

CLAUDE.md 报告: CAGR 13.17% / 14.65% (含 overlay) / MDD -64% / -56% / Calmar 0.86

**怀疑点**: 这个数字从未跑过 random control. 项目教训说明小盘宇宙 + HS300 基准会
虚高 alpha 5pp. 13.17% 可能实际是 7-9% (接近随机).
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd

from research.foundation import (
    DataBundle, Universe, CostModel,
    CrossSectionalStrategy, Backtest, StandardReport,
)


def factor_low_vol(row, price_cache, sig_date):
    """低波因子: -60日收益std (越大越好 = 越低波越好)"""
    code = row["code"]
    if code not in price_cache: return np.nan
    pf = price_cache[code]
    sub = pf[pf["date"] <= sig_date].tail(61)
    if len(sub) < 40: return np.nan
    vol = sub["close"].pct_change().std()
    if pd.isna(vol) or vol == 0: return np.nan
    return -float(vol)  # 取负: 低波 → 因子大 → 被选中


def main():
    print("=" * 80)
    print("  低波 baseline — foundation 严格验证")
    print("=" * 80)
    print("  CLAUDE.md 声称: CAGR 13.17% (无 overlay), Calmar 0.86")
    print("  本次验证: 加 random control + OOS 拆分, 看真 alpha")
    print()

    data = DataBundle.load(verbose=False)
    print(f"  数据加载完成 ({data.audit.ohlcv_coverage_pct:.0f}% OHLCV 覆盖)")
    print()

    # CLAUDE.md 中: 用 top 1000 流动性股 (broad), 实际是中小盘
    # 我们用 broad universe 30-200亿对应 top 流动性中小盘
    uni = Universe.broad(data, mcap_range=(30, 500), min_turnover_20d=0.15,
                          exclude_st=True, exclude_new_listing_days=180)

    strat = CrossSectionalStrategy(
        name="低波 60d (top 20%)",
        factor_fn=factor_low_vol,
        top_pct=0.20,           # CLAUDE.md: enter_q=0.80 → top 20%
        n_signal_cap=30,        # 实际可投 30 只
        hold_days=12 * 5,       # 12 交易日 ≈ 17 自然日 (约 hold_step=12)
                                # 用 60 自然日做半年级别 baseline 比较
    )
    # 注: CLAUDE.md 用 hold_step=12 交易日, 这里设 60 自然日 ≈ 季度
    # 主要是为了和其他 cross-sectional 对比一致

    cost = CostModel.a_share_retail_quarterly()

    bt = Backtest(
        strategy=strat,
        universe=uni,
        cost_model=cost,
        random_control=True,                                  # 强制对照
        train_test_split=("2018-12-31", "2019-01-01"),       # OOS 拆分
        n_random_repeats=30,
        year_start=2017, year_end=2025,
        seed=42,
    )
    result = bt.run(verbose=True)

    # 标准报告
    report = StandardReport.from_result(result)
    report.print()

    out_path = os.path.join(
        os.path.dirname(__file__), "..", "factors_v2", "output",
        "low_vol_foundation_validation.md"
    )
    report.save(out_path)
    print(f"\n[+] 报告写入 {out_path}")


if __name__ == "__main__":
    main()
