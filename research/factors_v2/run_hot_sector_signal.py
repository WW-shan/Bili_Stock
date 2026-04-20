"""
Hot Sector Signal — 板块资金流 + 涨停分布 × Factor A干净池
============================================================
每次rebalance前运行（每12个交易日），找出当前热点板块，
从Factor A干净池里筛出这些板块的候选股。

两个信号：
  1. 近3日板块净资金流入排名（东方财富，via AKShare）
  2. 今日/近3日涨停股按板块统计（哪个板块涨停最多）

T+1操作逻辑：
  收盘后（15:00）运行本脚本 → 得到热点板块 → 次日开盘买入

Run:
    python research/factors_v2/run_hot_sector_signal.py
"""

import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

STOCK_DATA_DIR = os.path.join(ROOT, "data", "stock_data")
OUT_DIR        = os.path.join(ROOT, "research", "factors_v2", "output", "live")
TOP_SECTOR_N   = 5      # 取前N个热点板块
TOP_STOCK_N    = 30     # 每个板块最多取N只候选股


# ── AKShare数据获取 ─────────────────────────────────────────────────── #

def _get_sector_fund_flow() -> pd.DataFrame:
    """近3日行业/概念板块净流入排名（东方财富）。"""
    try:
        import akshare as ak
    except ImportError:
        print("  [!] akshare未安装，运行: pip install akshare")
        return pd.DataFrame()

    dfs = []

    # 行业板块资金流
    try:
        df_ind = ak.stock_board_industry_fund_flow_rank(symbol="3日")
        df_ind = df_ind[["名称", "3日主力净流入-净额"]].copy()
        df_ind.columns = ["板块名称", "净流入3日(亿)"]
        df_ind["净流入3日(亿)"] = pd.to_numeric(
            df_ind["净流入3日(亿)"], errors="coerce") / 1e8
        df_ind["类型"] = "行业"
        dfs.append(df_ind)
        print(f"  行业板块资金流: {len(df_ind)} 条")
    except Exception as e:
        print(f"  行业板块资金流获取失败: {e}")

    # 概念板块资金流
    try:
        df_con = ak.stock_board_concept_fund_flow_rank(symbol="3日")
        df_con = df_con[["名称", "3日主力净流入-净额"]].copy()
        df_con.columns = ["板块名称", "净流入3日(亿)"]
        df_con["净流入3日(亿)"] = pd.to_numeric(
            df_con["净流入3日(亿)"], errors="coerce") / 1e8
        df_con["类型"] = "概念"
        dfs.append(df_con)
        print(f"  概念板块资金流: {len(df_con)} 条")
    except Exception as e:
        print(f"  概念板块资金流获取失败: {e}")

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = df.dropna(subset=["净流入3日(亿)"])
    df = df.sort_values("净流入3日(亿)", ascending=False).reset_index(drop=True)
    return df


def _get_zt_raw(days_back: int = 3) -> pd.DataFrame:
    """返回原始涨停记录（含代码、名称、板块、日期）。"""
    try:
        import akshare as ak
    except ImportError:
        return pd.DataFrame()
    records = []
    today = datetime.today().date()
    for d in range(days_back + 2):
        target = today - timedelta(days=d)
        if target.weekday() >= 5:
            continue
        date_str = target.strftime("%Y%m%d")
        try:
            df = ak.stock_zt_pool_em(date=date_str)
            if df is None or df.empty:
                continue
            sector_col = next((c for c in df.columns if "行业" in c or "板块" in c), None)
            code_col   = next((c for c in df.columns if c in ("代码", "股票代码")), None)
            name_col   = next((c for c in df.columns if c in ("名称", "股票名称")), None)
            for _, row in df.iterrows():
                records.append({
                    "date":       target,
                    "stock_code": str(row[code_col]) if code_col else "",
                    "stock_name": str(row[name_col]) if name_col else "",
                    "sector":     str(row[sector_col]) if sector_col else "未知",
                })
            if len(records) > 0 and d == 0:
                break  # 今日有数据就够了，只补历史
        except Exception:
            pass
    return pd.DataFrame(records) if records else pd.DataFrame()


def _get_zt_by_sector(days_back: int = 3) -> pd.DataFrame:
    """近N日涨停股按板块统计，返回板块-涨停数量排名。"""
    try:
        import akshare as ak
    except ImportError:
        return pd.DataFrame()

    records = []
    today = datetime.today().date()
    for d in range(days_back):
        target = today - timedelta(days=d)
        date_str = target.strftime("%Y%m%d")
        if target.weekday() >= 5:   # 跳过周末
            continue
        try:
            df = ak.stock_zt_pool_em(date=date_str)
            if df is None or df.empty:
                continue
            # 东方财富涨停池包含"所属行业"列
            sector_col = None
            for col in df.columns:
                if "行业" in col or "板块" in col:
                    sector_col = col
                    break
            if sector_col:
                for _, row in df.iterrows():
                    records.append({
                        "date": target,
                        "stock_code": str(row.get("代码", "")),
                        "stock_name": str(row.get("名称", "")),
                        "sector": str(row.get(sector_col, "未知")),
                    })
            print(f"  涨停池 {date_str}: {len(df)} 只")
        except Exception as e:
            print(f"  涨停池 {date_str} 获取失败: {e}")

    if not records:
        return pd.DataFrame()

    df_all = pd.DataFrame(records)
    sector_cnt = (df_all.groupby("sector")
                  .agg(涨停次数=("stock_code", "count"),
                       涨停股=("stock_name", lambda x: "、".join(x.head(5))))
                  .sort_values("涨停次数", ascending=False)
                  .reset_index())
    return sector_cnt


# ── Factor A 干净池计算 ──────────────────────────────────────────────── #

def _build_clean_pool() -> pd.DataFrame:
    """计算当前Factor A干净池（cnt28=0的股票）。"""
    import glob

    files  = glob.glob(os.path.join(STOCK_DATA_DIR, "S[HZ]*.csv"))
    today  = pd.Timestamp(datetime.today().date())
    cutoff = today - timedelta(days=60)     # 只需要最近60天数据

    rows = []
    for fp in files:
        sym = os.path.splitext(os.path.basename(fp))[0].upper()
        if sym.endswith(".HK"):
            continue
        code = sym[2:]
        if (sym.startswith("SH") and (
                code[:3] in {"510","511","512","513","514","515","516","517","518","519","588"}
                or code[:2] == "56")):
            continue
        if sym.startswith("SZ") and code[:3] == "159":
            continue

        try:
            df = pd.read_csv(fp, encoding="utf-8-sig")
        except Exception:
            continue

        col_map = {}
        for col in df.columns:
            lc = col.strip()
            if lc == "日期":      col_map[col] = "date"
            elif lc == "开盘":    col_map[col] = "open"
            elif lc == "收盘":    col_map[col] = "close"
            elif lc == "最低":    col_map[col] = "low"
            elif lc == "成交量":  col_map[col] = "vol"
        df = df.rename(columns=col_map)

        needed = ["date", "open", "close", "low", "vol"]
        if not all(c in df.columns for c in needed):
            continue

        df["date"]  = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
        for c in needed[1:]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=needed).query("close > 0").sort_values("date")
        df = df[df["date"] >= cutoff]
        if len(df) < 30:
            continue

        o, c, v = df["open"], df["close"], df["vol"]
        prev_c  = c.shift(1)
        real_yin = ((c < o) & ~(c > prev_c)).astype(float)
        hi28_o   = o.rolling(28, min_periods=1).max()
        lo28_o   = o.rolling(28, min_periods=1).min()
        o85      = lo28_o + 0.95 * (hi28_o - lo28_o)
        top15o   = (o >= o85).astype(float)
        fd15     = ((c < prev_c) & (c <= o) & (v >= 1.15 * v.shift(1))).astype(float)
        cnt28    = (top15o * fd15).rolling(28, min_periods=1).sum()

        latest   = df["date"].max()
        cnt_val  = float(cnt28.iloc[-1]) if len(cnt28) > 0 else np.nan
        close_val = float(c.iloc[-1])

        rows.append({
            "stock_symbol": sym,
            "latest_date":  latest,
            "cnt28":        cnt_val,
            "close":        close_val,
        })

    if not rows:
        return pd.DataFrame()

    pool = pd.DataFrame(rows)
    pool = pool[pool["latest_date"] >= today - timedelta(days=10)]  # 数据不太旧
    pool["is_clean"] = (pool["cnt28"] == 0)
    return pool


def _get_zt_stocks_in_clean_pool(zt_sectors: pd.DataFrame,
                                   zt_raw: pd.DataFrame,
                                   clean_syms: set) -> pd.DataFrame:
    """
    直接从涨停池提取热点板块的涨停股代码，
    再反查干净池中同板块的其他股票（非涨停，可能明天补涨）。
    """
    if zt_raw.empty or zt_sectors.empty:
        return pd.DataFrame()

    rows = []
    top_sectors = zt_sectors.head(TOP_SECTOR_N)["sector"].tolist()

    for sector in top_sectors:
        # 本板块的涨停股
        zt_in_sector = zt_raw[zt_raw["sector"] == sector].copy()
        zt_codes = set(zt_in_sector["stock_code"].tolist())

        # 在干净池里 且 不是已经涨停的（涨停股次日可能高开低走）
        # 只保留干净池中 "同板块但未涨停" 的股票
        clean_in_sector = [s for s in clean_syms
                           if s[2:] in zt_codes or  # 本身就是涨停股（保留供参考）
                           False]  # 非涨停同板块股下面单独处理

        # 也保留涨停股本身（供参考，但标注已涨停）
        for _, r in zt_in_sector.iterrows():
            code = r["stock_code"]
            sym  = ("SH" + code) if code.startswith("6") else ("SZ" + code)
            rows.append({
                "stock_symbol": sym,
                "stock_name":   r["stock_name"],
                "sector":       sector,
                "status":       "昨日涨停",
            })

    return pd.DataFrame(rows).drop_duplicates("stock_symbol") if rows else pd.DataFrame()


# ── 主程序 ────────────────────────────────────────────────────────────── #

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.today().date()

    print(f"\n{'='*60}")
    print(f"热点板块选股信号 — {today}")
    print(f"{'='*60}\n")

    # ── Step 1: Factor A 干净池 ─────────────────────────────────────── #
    print("Step 1: 计算Factor A干净池...")
    pool = _build_clean_pool()
    clean_pool = pool[pool["is_clean"]].copy()
    print(f"  全量股票: {len(pool)}  |  干净池(cnt28=0): {len(clean_pool)}")

    clean_syms = set(clean_pool["stock_symbol"].tolist())

    # ── Step 2: 板块资金流 ──────────────────────────────────────────── #
    print("\nStep 2: 获取近3日板块资金流...")
    fund_flow = _get_sector_fund_flow()
    if not fund_flow.empty:
        hot_by_flow = fund_flow.head(TOP_SECTOR_N)
        print(f"\n  近3日净流入最多的板块 (Top {TOP_SECTOR_N}):")
        print(f"  {'板块':<20s} {'类型':>4s} {'净流入3日(亿)':>14s}")
        print(f"  {'-'*42}")
        for _, row in hot_by_flow.iterrows():
            print(f"  {row['板块名称']:<20s} {row['类型']:>4s} {row['净流入3日(亿)']:>+13.2f}")
    else:
        hot_by_flow = pd.DataFrame()
        print("  [跳过] 资金流数据不可用")

    # ── Step 3: 涨停板块分布 ───────────────────────────────────────── #
    print("\nStep 3: 统计近3日涨停板块分布...")
    zt_sectors = _get_zt_by_sector(days_back=5)
    if not zt_sectors.empty:
        hot_by_zt = zt_sectors.head(TOP_SECTOR_N)
        print(f"\n  近期涨停最集中的板块 (Top {TOP_SECTOR_N}):")
        print(f"  {'板块':<20s} {'涨停次数':>8s}  代表股")
        print(f"  {'-'*60}")
        for _, row in hot_by_zt.iterrows():
            print(f"  {row['sector']:<20s} {int(row['涨停次数']):>8d}  {row['涨停股']}")
    else:
        hot_by_zt = pd.DataFrame()
        print("  [跳过] 涨停数据不可用")

    # ── Step 4: 涨停股 × 干净池 直接交叉 ──────────────────────────── #
    print("\nStep 4: 涨停股 × Factor A干净池 直接交叉...")

    # 获取原始涨停记录（含代码）
    zt_raw = _get_zt_raw(days_back=3)

    # 涨停股里有多少在干净池
    zt_clean_overlap = []
    for _, row in zt_raw.iterrows():
        code = str(row["stock_code"])
        sym  = ("SH" + code) if code.startswith("6") else ("SZ" + code)
        if sym in clean_syms:
            cp = clean_pool[clean_pool["stock_symbol"] == sym]
            close = float(cp["close"].iloc[0]) if not cp.empty else np.nan
            zt_clean_overlap.append({
                "stock_symbol": sym,
                "stock_name":   row.get("stock_name", ""),
                "sector":       row.get("sector", ""),
                "date":         str(row.get("date", "")),
                "close":        close,
                "note":         "涨停+干净",
            })

    df_zt_clean = pd.DataFrame(zt_clean_overlap).drop_duplicates("stock_symbol") \
        if zt_clean_overlap else pd.DataFrame()

    print(f"\n{'='*60}")
    print(f"最终输出")
    print(f"{'='*60}")

    # A. 热点板块汇总
    if not zt_sectors.empty:
        print(f"\n【近3日热点板块（按涨停数量）】")
        for _, row in zt_sectors.head(TOP_SECTOR_N).iterrows():
            print(f"  {row['sector']:<12s}  涨停{int(row['涨停次数'])}次  代表股: {row['涨停股']}")

    # B. 涨停 & 干净池交集（直接候选）
    if not df_zt_clean.empty:
        print(f"\n【涨停股 × Factor A干净池 交集 — {len(df_zt_clean)}只】")
        print(f"  (这些股票：近3日涨停过 且 无出货信号，可能还有动能)")
        print(f"  {'代码':<12s} {'名称':<10s} {'板块':<12s} {'日期':<12s} {'收盘':>8s}")
        print(f"  {'-'*58}")
        for _, row in df_zt_clean.iterrows():
            print(f"  {row['stock_symbol']:<12s} {str(row['stock_name']):<10s} "
                  f"{str(row['sector']):<12s} {str(row['date']):<12s} "
                  f"{row['close']:>8.2f}")
    else:
        print("\n  涨停股与干净池无交集（或涨停数据不含代码）")

    # C. 操作建议
    print(f"\n【操作提示】")
    print(f"  · 热点板块: {', '.join(zt_sectors.head(3)['sector'].tolist()) if not zt_sectors.empty else '见上'}")
    print(f"  · 交集股票已经涨停，次日可能高开——谨慎追高")
    print(f"  · 更好的做法：找上述热点板块中 未涨停但在干净池 的股票")
    print(f"    → 对照 clean_pool CSV，筛选板块匹配的个股")
    print(f"  · 持有约12个交易日后重新运行本脚本")

    # 保存
    out_clean = os.path.join(OUT_DIR, f"clean_pool_{today}.csv")
    clean_pool[["stock_symbol", "cnt28", "close"]].to_csv(
        out_clean, index=False, encoding="utf-8-sig")

    if not df_zt_clean.empty:
        out_zt = os.path.join(OUT_DIR, f"hot_sector_picks_{today}.csv")
        df_zt_clean.to_csv(out_zt, index=False, encoding="utf-8-sig")
        print(f"\n  涨停×干净池 → {out_zt}")
    print(f"  干净池全量  → {out_clean}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
