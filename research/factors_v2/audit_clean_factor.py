"""
Clean Factor Audit -- 2019起真实回测 + 净值图 + 最新持仓
=========================================================
Run:
    python research/factors_v2/audit_clean_factor.py
"""

import glob, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
matplotlib.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

STOCK_DATA_DIR = os.path.join(ROOT, "data", "stock_data")
HS300_CACHE    = os.path.join(ROOT, "data", "market_cache", "hs300_daily_cache.csv")
OUT_DIR        = os.path.join(ROOT, "research", "factors_v2", "output")

START_DATE    = "2019-01-01"
END_DATE      = "2026-04-18"
ROUND_TRIP_BP = 56      # 买13bp + 卖43bp，真实A股成本
BUY_BP        = 13
SELL_BP       = 43
HOLD_STEP     = 12
K             = 10
INIT_CAPITAL  = 100_000
OVERLAY_THR   = -0.07
ENTER_Q       = 0.80


# ─── 未来函数检查 ────────────────────────────────────────────────── #
LOOKAHEAD_NOTES = """
未来函数审计：
  factor_a = -cnt28
    cnt28 = rolling(28日内高位放量阴线数量)
    所有输入：open[t], close[t], vol[t]，均为t日已知数据
    rolling(28) 向过去看，无未来数据 -> OK

  fwd_ret（回测用，不是因子）
    = open[t+13] / open[t+1] - 1
    = 次日开盘买入，12个交易日后次日开盘卖出
    这是"结果"变量，回测引擎用它衡量持有收益，不是用来选股的 -> OK

  HS300 overlay
    ret20 = close[t] / close[t-20] - 1，只用t及之前数据 -> OK

  结论：因子计算和Overlay均无未来函数。
"""


# ─── 因子 ───────────────────────────────────────────────────────── #

def compute_factor_a(o, c, v):
    """-cnt28: 28日内高位放量阴线数，取负（越少越好）。纯历史数据。"""
    prev_c = c.shift(1)
    hi28_o = o.rolling(28, min_periods=1).max()
    lo28_o = o.rolling(28, min_periods=1).min()
    o85    = lo28_o + 0.95 * (hi28_o - lo28_o)
    top15o = (o >= o85).astype(float)
    fd15   = ((c < prev_c) & (c <= o) & (v >= 1.15 * v.shift(1))).astype(float)
    cnt28  = (top15o * fd15).rolling(28, min_periods=1).sum()
    return -cnt28


# ─── 面板 ────────────────────────────────────────────────────────── #

def build_panel():
    files    = glob.glob(os.path.join(STOCK_DATA_DIR, "S[HZ]*.csv"))
    start_dt = pd.Timestamp(START_DATE) - pd.Timedelta(days=120)
    end_dt   = pd.Timestamp(END_DATE)
    rows, skipped = [], 0

    for fp in files:
        sym  = os.path.splitext(os.path.basename(fp))[0].upper()
        code = sym[2:]
        if sym.startswith("SH") and (code[:3] in {"510","511","512","513","514",
                "515","516","517","518","519","588"} or code[:2] == "56"):
            continue
        if sym.startswith("SZ") and code[:3] == "159":
            continue
        try:
            df = pd.read_csv(fp, encoding="utf-8-sig")
        except Exception:
            skipped += 1; continue

        col_map = {}
        for col in df.columns:
            lc = col.strip()
            if lc == "日期":     col_map[col] = "date"
            elif lc == "开盘":   col_map[col] = "open"
            elif lc == "收盘":   col_map[col] = "close"
            elif lc == "成交量": col_map[col] = "vol"
        df = df.rename(columns=col_map)
        if not all(c in df.columns for c in ["date","open","close","vol"]):
            skipped += 1; continue

        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
        for c in ["open","close","vol"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["date","open","close","vol"]).query("close>0").sort_values("date")
        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
        if len(df) < 80:
            continue

        df = df.set_index("date")
        fa  = compute_factor_a(df["open"], df["close"], df["vol"])

        # T+1: 次日开盘买，HOLD_STEP日后次日开盘卖
        next_open = df["open"].shift(-1)
        exit_open = df["open"].shift(-(HOLD_STEP + 1))
        fwd_ret   = exit_open / next_open - 1.0

        out = pd.DataFrame({
            "factor_a":   fa,
            "fwd_ret":    fwd_ret,
            "close":      df["close"],
            "stock_name": "",        # 名称暂空，最新持仓时用code查
        }, index=df.index)
        out["stock_symbol"] = sym
        out["date"]         = df.index
        rows.append(out.reset_index(drop=True))

    print(f"  Loaded {len(rows)} stocks, skipped {skipped}", flush=True)
    panel = pd.concat(rows, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    panel = panel[panel["date"] >= pd.Timestamp(START_DATE)]
    panel["rank_pct"] = panel.groupby("date")["factor_a"].rank(pct=True, method="first")
    return panel


def load_hs300():
    hs = pd.read_csv(HS300_CACHE)
    hs["date"] = pd.to_datetime(hs["date"])
    hs = hs.sort_values("date")
    if "ret20" not in hs.columns:
        hs["ret20"] = hs["close"].pct_change(20)
    return hs[["date","close","ret20"]].dropna().set_index("date")


# ─── 回测引擎 ────────────────────────────────────────────────────── #

def simulate(panel, hs300, start_offset=0, verbose_latest=False):
    sub = panel.dropna(subset=["factor_a","fwd_ret","rank_pct"]).copy()
    dates       = sorted(sub["date"].unique())
    rebal_dates = dates[start_offset::HOLD_STEP]

    capital   = float(INIT_CAPITAL)
    records   = []
    prev_hold: set = set()
    latest_holdings = []

    for d in rebal_dates:
        g = sub[sub["date"] == d]
        if len(g) < 50:
            continue

        hs_rows = hs300[hs300.index <= d]
        ret20   = float(hs_rows["ret20"].iloc[-1]) if not hs_rows.empty else 0.0
        in_overlay = ret20 < OVERLAY_THR

        if in_overlay:
            records.append({"date": d, "year": d.year, "capital": capital,
                            "gross_ret": 0.0, "net_ret": 0.0,
                            "win_cnt": 0, "lose_cnt": 0, "overlay": True})
            prev_hold = set()
            continue

        top_pool = g[g["rank_pct"] >= ENTER_Q]
        keep_set = set(g[(g["rank_pct"] >= 0.70) &
                         g["stock_symbol"].isin(prev_hold)]["stock_symbol"])
        new_pool = (top_pool[~top_pool["stock_symbol"].isin(keep_set)]
                    .sort_values("rank_pct", ascending=False))
        need     = max(0, K - len(keep_set))
        new_set  = set(new_pool.head(need)["stock_symbol"])
        holdings = list(keep_set | new_set)[:K]
        if not holdings:
            continue

        held_g    = g[g["stock_symbol"].isin(holdings)]
        rets      = held_g["fwd_ret"].dropna().values
        if len(rets) == 0:
            continue

        gross_ret = float(rets.mean())
        # 不对称成本：新买 = BUY_BP，全部要卖 = SELL_BP
        n_new   = len(set(holdings) - prev_hold)
        n_keep  = len(set(holdings) & prev_hold)
        n_exit  = len(prev_hold - set(holdings)) if prev_hold else 0
        cost    = ((n_new * BUY_BP + (n_new + n_exit) * SELL_BP)
                   / max(len(holdings), 1) / 1e4) if prev_hold else BUY_BP / 1e4
        net_ret = gross_ret - cost
        capital *= (1 + net_ret)

        records.append({
            "date":      d,
            "year":      d.year,
            "capital":   capital,
            "gross_ret": gross_ret,
            "net_ret":   net_ret,
            "cost":      cost,
            "win_cnt":   int((rets > 0).sum()),
            "lose_cnt":  int((rets <= 0).sum()),
            "overlay":   False,
        })

        # 保存最新一期持仓
        latest_holdings = []
        for sym in holdings:
            row = held_g[held_g["stock_symbol"] == sym]
            price = float(row["close"].iloc[0]) if not row.empty else np.nan
            latest_holdings.append({
                "stock_symbol": sym,
                "close":        price,
                "rank_pct":     float(g[g["stock_symbol"] == sym]["rank_pct"].iloc[0])
                                if not g[g["stock_symbol"] == sym].empty else np.nan,
                "is_new":       sym in new_set,
            })

        prev_hold = set(holdings)

    return pd.DataFrame(records), latest_holdings


# ─── 绘图 ────────────────────────────────────────────────────────── #

def plot_equity(df_sim, hs300, out_path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                    gridspec_kw={"height_ratios": [3, 1]},
                                    sharex=True)
    fig.patch.set_facecolor("#0d1117")
    for ax in (ax1, ax2):
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="white")
        ax.spines[:].set_color("#333")

    # 净值曲线
    eq = df_sim.set_index("date")["capital"] / INIT_CAPITAL
    ax1.plot(eq.index, eq.values, color="#00d4aa", linewidth=1.5, label="Factor A (K=10)")
    ax1.fill_between(eq.index, 1, eq.values,
                     where=(eq.values >= 1), alpha=0.1, color="#00d4aa")
    ax1.fill_between(eq.index, 1, eq.values,
                     where=(eq.values < 1), alpha=0.1, color="#ff4444")

    # HS300 benchmark
    hs_sub = hs300[(hs300.index >= pd.Timestamp(START_DATE)) &
                   (hs300.index <= pd.Timestamp(END_DATE))]["close"]
    if not hs_sub.empty:
        hs_norm = hs_sub / hs_sub.iloc[0]
        ax1.plot(hs_norm.index, hs_norm.values,
                 color="#aaaaaa", linewidth=1.0, linestyle="--", label="HS300", alpha=0.7)

    ax1.axhline(1, color="#555", linewidth=0.5, linestyle=":")
    ax1.set_ylabel("净值（倍）", color="white")
    ax1.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="white")
    ax1.set_title(f"Factor A (-cnt28)  K={K}  T+1执行  56bp成本  {START_DATE[:4]}-{END_DATE[:4]}",
                  color="white", pad=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}x"))

    # 回撤
    peak = eq.cummax()
    dd   = (eq - peak) / peak * 100
    ax2.fill_between(dd.index, dd.values, 0, color="#ff4444", alpha=0.6)
    ax2.axhline(0, color="#555", linewidth=0.5)
    ax2.set_ylabel("回撤 (%)", color="white")
    ax2.set_xlabel("")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

    # 标注最大回撤
    mdd_idx = dd.idxmin()
    ax2.annotate(f"  MDD {dd.min():.1f}%",
                 xy=(mdd_idx, dd.min()),
                 color="#ff8888", fontsize=9)

    # X轴格式
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax2.xaxis.get_majorticklabels(), color="white")

    # 逐年标注（在净值图上）
    by_year = df_sim.groupby("year")["net_ret"].apply(
        lambda r: float(np.prod(1 + r) - 1))
    for yr, yr_ret in by_year.items():
        mid = pd.Timestamp(f"{yr}-07-01")
        if mid < eq.index[0] or mid > eq.index[-1]:
            continue
        idx = eq.index.searchsorted(mid)
        if idx >= len(eq):
            continue
        color = "#00d4aa" if yr_ret >= 0 else "#ff4444"
        ax1.text(mid, eq.iloc[idx] * 1.02, f"{yr_ret:+.0%}",
                 color=color, fontsize=7.5, ha="center", va="bottom")

    plt.tight_layout(pad=1.5)
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  图表已保存 -> {out_path}")


# ─── 主程序 ──────────────────────────────────────────────────────── #

def cagr(rets, ppy):
    r = np.clip(np.asarray(rets, dtype=float), -0.99, None)
    if not len(r): return np.nan
    cum = float(np.prod(1 + r))
    return cum ** (ppy / len(r)) - 1 if cum > 0 else -1.0


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── 未来函数声明 ──────────────────────────────────────────────
    print(LOOKAHEAD_NOTES)

    # ── 成本说明 ──────────────────────────────────────────────────
    print("成本模型（每期）：")
    print(f"  买入 {BUY_BP}bp（佣金3 + 过户0.2 + 滑点10）")
    print(f"  卖出 {SELL_BP}bp（佣金3 + 印花10 + 过户0.2 + 滑点10 + 冲击20）")
    print(f"  完整换手一次成本 = {BUY_BP+SELL_BP}bp = {(BUY_BP+SELL_BP)/100:.2f}%\n")

    # ── 面板构建 ──────────────────────────────────────────────────
    print("Building panel ...", flush=True)
    panel = build_panel()
    hs300 = load_hs300()
    n_stocks = panel["stock_symbol"].nunique()
    n_dates  = panel["date"].nunique()
    print(f"Panel: {n_stocks} stocks, {n_dates} dates, {len(panel):,} rows\n")

    # ── 主回测 ────────────────────────────────────────────────────
    df_sim, latest = simulate(panel, hs300, start_offset=0, verbose_latest=True)

    ppy     = 252 / HOLD_STEP
    rets    = df_sim["net_ret"].tolist()
    c_net   = cagr(rets, ppy)
    cap_s   = df_sim.set_index("date")["capital"]
    peak    = cap_s.cummax()
    dd      = (cap_s - peak) / peak
    mdd_val = float(dd.min())
    mdd_end = dd.idxmin()
    mdd_pk  = cap_s[:mdd_end].idxmax()

    final_cap  = float(df_sim["capital"].iloc[-1])
    total_win  = int(df_sim["win_cnt"].sum())
    total_lose = int(df_sim["lose_cnt"].sum())
    win_rate   = total_win / max(total_win + total_lose, 1)
    avg_cost   = float(df_sim["cost"].mean()) * ppy

    by_year = df_sim.groupby("year").apply(
        lambda g: float(np.prod(1 + g["net_ret"]) - 1)).sort_index()

    print("=" * 60)
    print(f"回测结果  {START_DATE[:4]}-{END_DATE[:4]}  T+1执行  K={K}  56bp")
    print("=" * 60)
    print(f"  起始资金   : {INIT_CAPITAL:>10,.0f} 元")
    print(f"  期末资金   : {final_cap:>10,.0f} 元  ({final_cap/INIT_CAPITAL:.1f}x)")
    print(f"  年化净收益 : {c_net:>+.1%}")
    print(f"  最大回撤   : {mdd_val:>+.1%}  ({mdd_pk.date()} -> {mdd_end.date()})")
    print(f"  Calmar     : {c_net/abs(mdd_val):.2f}" if mdd_val < 0 else "")
    print(f"  单票胜率   : {win_rate:.1%}  ({total_win}赢 / {total_lose}输)")
    print(f"  年化成本   : {avg_cost:.1%}")

    print(f"\n  逐年净收益（含成本）:")
    for yr, r in by_year.items():
        bar  = "#" * max(0, int(abs(r) * 100 / 5))
        sign = "+" if r >= 0 else ""
        print(f"    {yr}: {sign}{r:.1%}  {bar}")

    # ── 随机起点QC ────────────────────────────────────────────────
    print(f"\n随机起点稳定性（12个offset）:")
    cagr_list = []
    for off in range(12):
        d2, _ = simulate(panel, hs300, start_offset=off)
        if not d2.empty:
            cagr_list.append(cagr(d2["net_ret"].tolist(), ppy))
    pos = sum(1 for x in cagr_list if x > 0)
    print(f"  正收益比例 : {pos}/{len(cagr_list)} = {pos/len(cagr_list):.0%}")
    print(f"  CAGR range : {min(cagr_list):+.1%} ~ {max(cagr_list):+.1%}")
    print(f"  均值CAGR   : {np.mean(cagr_list):+.1%}")

    # ── 最新持仓 ──────────────────────────────────────────────────
    latest_date = df_sim["date"].iloc[-1].date() if not df_sim.empty else "N/A"
    print(f"\n最新一期持仓（{latest_date} 信号，次日开盘买入）:")
    print(f"  {'代码':<12s} {'收盘价':>8s}  {'状态'}")
    print(f"  {'-'*38}")
    for h in sorted(latest, key=lambda x: -x["rank_pct"]):
        status = "新买入" if h["is_new"] else "续持"
        print(f"  {h['stock_symbol']:<12s} {h['close']:>8.2f}  {status}")

    # ── 已知偏差汇总 ──────────────────────────────────────────────
    print(f"\n已知偏差（必须说清楚）:")
    print(f"  1. 幸存者偏差  -- 退市股未纳入，收益被高估（估计5-10个点）")
    print(f"  2. 2019年数据  -- 覆盖更充分，但仍非完整市场")
    print(f"  3. 流动性      -- K=10每只1万，小盘股实际滑点>10bp")
    print(f"  4. 信号粒度    -- 收盘后才有信号，次日开盘才能执行")

    # ── 绘图 ──────────────────────────────────────────────────────
    out_img = os.path.join(OUT_DIR, "audit_equity_curve.png")
    plot_equity(df_sim, hs300, out_img)


if __name__ == "__main__":
    main()
