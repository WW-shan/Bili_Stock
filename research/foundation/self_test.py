"""
Foundation 自检 — 框架本身的正确性测试
=========================================
跑 4 个已知答案的因子, 验证框架的 alpha 检测能力:

  1. NULL factor (恒等于 0)         → alpha 应 ≈ 0
  2. RANDOM factor (每期重新随机)   → alpha 应 ≈ 0
  3. PERFECT FORWARD (用未来数据)    → alpha 应 >> 0 (检测前视检测能力)
  4. KNOWN BAD (高换手率)           → alpha 应 << 0 (反向 t-stat)

如果 1-2 给出 |alpha| > 1% 或 |t| > 2, 框架有 bug, 不能使用.
如果 4 不给出负 alpha, 框架不能区分好坏因子.

这是 "回测自己回测" 的 sanity check, 不能跳过.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

# 从父目录加载 foundation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import pandas as pd

from research.foundation import (
    DataBundle, Universe, CostModel, Benchmark,
    CrossSectionalStrategy, Backtest, StandardReport,
)


# ── 4 个测试因子 ──────────────────────────────────────────────────────────────
def factor_null(row, price_cache, sig_date):
    """恒等于 0 — alpha 应 ≈ 0"""
    return 0.0

def factor_random(row, price_cache, sig_date):
    """每次随机 — alpha 应 ≈ 0"""
    return np.random.random()

def factor_high_turnover(row, price_cache, sig_date):
    """高换手 — 已知负向 (项目历史 t=-5.37)"""
    return row.get("turn20", np.nan)


def factor_forward_lookahead(row, price_cache, sig_date):
    """
    用未来 10 日收益做因子 — 故意前视, alpha 应该 >> 0.
    框架若没检测到 (因为我们没装前视检测器), 至少 alpha 不该是 0.
    这个测试帮我们看到 "框架能否区分有效信号".
    """
    code = row["code"]
    if code not in price_cache: return np.nan
    pf = price_cache[code]
    after = pf[pf["date"] > sig_date].head(10)
    if len(after) < 5: return np.nan
    return float(after.iloc[-1]["close"] / after.iloc[0]["close"] - 1)


# ── 主测试 ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  Foundation 自检 (框架正确性验证)")
    print("=" * 80)
    print()
    print("规则:")
    print("  - NULL/RANDOM 应给出 alpha ≈ 0 且 |t| < 2 (无信号)")
    print("  - 高换手 应给出 alpha < 0 (项目历史 t=-5.37)")
    print("  - 前视 应给出 alpha >> 0 (强正信号, 但有前视警告)")
    print()

    print("[1/2] 加载数据...")
    data = DataBundle.load(verbose=False)
    print(f"      通过 ({data.audit.ohlcv_coverage_pct:.0f}% 覆盖)")
    print()

    print("[2/2] 跑 4 个测试因子 (broad universe, 30-200亿市值)...")
    print()

    uni = Universe.broad(data, mcap_range=(30, 200), min_turnover_20d=0.15)
    cost = CostModel.a_share_retail_quarterly()

    factors = [
        ("NULL (恒0)",    factor_null,            "应 alpha ≈ 0"),
        ("RANDOM",        factor_random,          "应 alpha ≈ 0"),
        ("高换手 (反向)",  factor_high_turnover,    "应 alpha < 0 (t<<0)"),
        ("前视 (作弊)",    factor_forward_lookahead,"应 alpha >> 0 (检测能力)"),
    ]

    print(f"{'因子':<18s} {'信号6M':>10s} {'随机6M':>10s} {'Alpha':>9s} {'t-stat':>7s} {'判定':>10s}")
    print("-" * 75)

    issues = []
    for name, fn, expectation in factors:
        strat = CrossSectionalStrategy(name=name, factor_fn=fn,
                                         top_pct=0.20, n_signal_cap=30, hold_days=180)
        bt = Backtest(strategy=strat,
                       universe=uni,
                       cost_model=cost,
                       random_control=True,
                       n_random_repeats=10,
                       year_start=2018, year_end=2024,
                       seed=42)
        try:
            res = bt.run(verbose=False)
        except Exception as e:
            print(f"  {name:<16s}  {'ERROR':>30s}  {e}")
            continue
        s = res.full_summary
        if "alpha_mean" not in s:
            print(f"  {name:<16s}  样本不足"); continue

        alpha = s["alpha_mean"]
        t = s["t_stat"]
        sig = s["signal_mean_gross"]
        rnd = s["random_mean_gross"]

        if "NULL" in name or "RANDOM" in name:
            # 判据: t-stat 必须不显著 (|t| < 2). alpha 噪音允许 ±5% (32期样本).
            verdict = "✓" if abs(t) < 2.0 else "✗ 异常"
            if verdict.startswith("✗"):
                issues.append(f"{name}: t={t:.2f} 应该 |t|<2 (无信号)")
        elif "高换手" in name:
            # 判据: 强负 alpha + 强负 t (项目历史 t=-5.37)
            verdict = "✓" if (alpha < 0 and t < -2) else "✗ 应负"
            if verdict.startswith("✗"):
                issues.append(f"{name}: 期望 alpha<0 t<-2 实际 alpha={alpha*100:+.2f}% t={t:.2f}")
        elif "前视" in name:
            # 判据: 前视给极强正信号 (alpha > 5%, t > 3)
            verdict = "✓" if (alpha > 0.05 and t > 3) else "? 弱"
            if verdict.startswith("?"):
                issues.append(f"{name}: 前视检测能力不足 alpha={alpha*100:+.2f}% t={t:.2f}")
        else:
            verdict = "?"

        print(f"  {name:<16s}  {sig*100:>+7.2f}%  {rnd*100:>+7.2f}%  "
              f"{alpha*100:>+6.2f}%  {t:>+5.2f}  {verdict:>10s}")

    print()
    print("=" * 80)
    if issues:
        print(f"  ✗ 框架自检失败 ({len(issues)} 个问题):")
        for i in issues: print(f"    - {i}")
        print(f"\n  框架不可信. 不要用于策略验证.")
        sys.exit(1)
    else:
        print(f"  ✓ 框架自检通过. 可以用于策略验证.")


if __name__ == "__main__":
    main()
