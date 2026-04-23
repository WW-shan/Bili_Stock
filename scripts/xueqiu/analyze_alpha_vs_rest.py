"""
45 pure-alpha vs 166 其他 — 行为特征对比
==============================================
pure_alpha: 真实 CAGR > 3.5% (跑赢 HS300) 且 MDD > -45% (比大盘回撤小)
rest:       211 干净子集里剩下的 166 个 (CAGR 赢或 MDD 赢但非两者都赢)

对比四大特征:
  1. 持仓股票数 (集中度)
  2. 换手率 (|target-prev| 求和 / 年)
  3. 行业分布 (Top-3 行业占比 / 行业偏离度)
  4. 持仓类型 (A股 / 美股 / 港股 / ETF 比例)
"""
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

import numpy as np
import pandas as pd
pd.set_option("display.width", 200)
pd.options.display.float_format = "{:.2f}".format

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB = os.path.join(ROOT, "data", "cubes.db")
AUDIT = os.path.join(ROOT, "research", "factors_v2", "output", "cube_nav_audit.csv")
IND = os.path.join(ROOT, "research", "baseline_v1", "data_delivery", "industry_mapping_v2.csv")
OUT = os.path.join(ROOT, "research", "factors_v2", "output", "alpha_vs_rest.csv")

# 加载
audit = pd.read_csv(AUDIT, encoding="utf-8-sig")
ind_map = pd.read_csv(IND, encoding="utf-8-sig")
ind_map["industry_l2"] = ind_map["industry_l2"].fillna("未知")

# 筛选干净子集 (同审计报告)
clean = audit[(audit["real_years"] >= 5)
              & (audit["real_cagr"] >= -20)
              & (audit["real_cagr"] <= 50)].copy()

# 分组: pure_alpha = 跑赢 HS300 (3.5%) + MDD > -45%
clean["group"] = np.where(
    (clean["real_cagr"] > 3.5) & (clean["real_mdd"] > -45),
    "pure_alpha", "rest"
)
print(f"干净子集 {len(clean)} = pure_alpha {(clean.group=='pure_alpha').sum()} "
      f"+ rest {(clean.group=='rest').sum()}\n")

syms = set(clean["symbol"])

# 读 rebalancing_history
con = sqlite3.connect(DB)
rh = pd.read_sql(f"""
    SELECT cube_symbol, stock_symbol, stock_name, prev_weight_adjusted, target_weight, created_at
    FROM rebalancing_history
    WHERE status='success' AND cube_symbol IN ({','.join('?'*len(syms))})
""", con, params=list(syms))
con.close()
rh["created_at"] = pd.to_datetime(rh["created_at"], errors="coerce")
print(f"加载 {len(rh):,} 条 rebalance 记录 ({rh.cube_symbol.nunique()} cube)")

# ── 特征 1: 平均持仓数 ──
# 每次 rebalance 是一条 record, 但一个持仓可能分散在多条 (每条 = 一只股的调整)
# 用 created_at date 作为单次 rebalance 时间点
# 一个时间点 + 一个 cube = 一次快照. 快照内股票数 = 该次持仓数
rh["date"] = rh["created_at"].dt.date
snap = rh.groupby(["cube_symbol","date"]).size().reset_index(name="n_stocks_in_batch")
# 注: 这是"批次操作的股数",不是组合总持仓. 但大部分 cube 的 rebalance 是一次性调整,可做近似
avg_batch = snap.groupby("cube_symbol")["n_stocks_in_batch"].mean().rename("avg_batch_size")

# 更准: 每个 cube 的 "独立股票池" 大小
unique_stk = rh.groupby("cube_symbol")["stock_symbol"].nunique().rename("unique_stocks_ever")

# ── 特征 2: 换手率 (每次 rebalance 的 |target - prev| / 2, 求和除年数) ──
rh["chg"] = (rh["target_weight"].fillna(0) - rh["prev_weight_adjusted"].fillna(0)).abs() / 2
# 每个 cube: 总换手 / 实际年数
cube_years = rh.groupby("cube_symbol")["created_at"].agg(
    lambda x: (x.max() - x.min()).days / 365.25
).rename("years")
cube_turnover = rh.groupby("cube_symbol")["chg"].sum().rename("total_chg_sum")
# 注: weight 是 % 级 (0-100),总换手 / 100 = 组合换手次数; /年 = 年化换手
turn_ann = (cube_turnover / 100 / cube_years).rename("turnover_per_year")

# ── 特征 3: 行业分布 ──
# 把 stock_symbol 转成 standard (去掉雪球的 SH/SZ 前缀可能已是标准)
# 雪球格式应该是 SH600000 / SZ000001 直接匹配
rh2 = rh.merge(ind_map, left_on="stock_symbol", right_on="stock_symbol_standard", how="left")
rh2["industry_l2"] = rh2["industry_l2"].fillna("非A股/ETF/其他")
# 用 target_weight 权重加权
rh2["w_target"] = rh2["target_weight"].fillna(0) / 100.0
ind_weight = rh2.groupby(["cube_symbol","industry_l2"])["w_target"].sum().reset_index()
# 每 cube 归一化
tot_w = ind_weight.groupby("cube_symbol")["w_target"].sum().rename("tot_w")
ind_weight = ind_weight.merge(tot_w, on="cube_symbol")
ind_weight["share"] = ind_weight["w_target"] / ind_weight["tot_w"]
# Top3 行业占比
top3 = (ind_weight.sort_values(["cube_symbol","share"], ascending=[True,False])
        .groupby("cube_symbol").head(3).groupby("cube_symbol")["share"].sum()
        .rename("top3_ind_share"))
# 非 A 股占比
non_a_share = (ind_weight[ind_weight["industry_l2"]=="非A股/ETF/其他"]
               .set_index("cube_symbol")["share"]
               .rename("non_a_share"))

# ── 特征 4: 持仓类型 ──
def mkt_class(s):
    s = str(s)
    if s.startswith(("SH","SZ")): return "A_stock"
    if s.startswith(("1","5","6")) and s[0:3] in ("512","510","511","518","588","159"):  # ETF 编号
        return "ETF"
    if len(s)==5 and s.isdigit(): return "HK"
    return "US_other"
rh2["mkt"] = rh2["stock_symbol"].apply(mkt_class)
mkt_mix = rh2.groupby(["cube_symbol","mkt"])["w_target"].sum().unstack(fill_value=0)
mkt_mix = mkt_mix.div(mkt_mix.sum(axis=1), axis=0).fillna(0)

# ── 汇总 ──
feat = pd.DataFrame({
    "avg_batch_size": avg_batch,
    "unique_stocks_ever": unique_stk,
    "turnover_per_year": turn_ann,
    "top3_ind_share": top3,
    "non_a_share": non_a_share,
}).join(mkt_mix, how="left").fillna(0)

full = clean.set_index("symbol").join(feat, how="left")

# ── 对比 ──
print("\n" + "="*90)
print("  行为特征对比 (中位数)")
print("="*90)
cols = ["avg_batch_size","unique_stocks_ever","turnover_per_year","top3_ind_share","non_a_share"]
for mkt in ["A_stock","ETF","HK","US_other"]:
    if mkt in full.columns: cols.append(mkt)

agg = full.groupby("group")[cols].median()
print(agg.T.to_string())

print("\n" + "="*90)
print("  分布对比 (25% / 中位 / 75%)")
print("="*90)
for col in cols:
    print(f"\n{col}:")
    for g in ["pure_alpha","rest"]:
        s = full[full["group"]==g][col].dropna()
        if len(s)==0: continue
        print(f"  {g:10s}  25%={s.quantile(.25):.3f}  med={s.median():.3f}  75%={s.quantile(.75):.3f}  (n={len(s)})")

# 差异性 Mann-Whitney U
print("\n" + "="*90)
print("  统计显著性 (Mann-Whitney U, p-value)")
print("="*90)
from scipy.stats import mannwhitneyu
for col in cols:
    a = full[full["group"]=="pure_alpha"][col].dropna()
    b = full[full["group"]=="rest"][col].dropna()
    if len(a)<5 or len(b)<5: continue
    try:
        u, p = mannwhitneyu(a, b, alternative="two-sided")
        sig = "***" if p<0.01 else ("**" if p<0.05 else ("*" if p<0.1 else ""))
        print(f"  {col:20s}  p={p:.4f}  {sig}  med_α={a.median():.3f}  med_rest={b.median():.3f}  diff={a.median()-b.median():+.3f}")
    except Exception as e:
        print(f"  {col}: {e}")

# ── 行业差异 top (修正: 缺失行业填 0 再求均值) ──
print("\n" + "="*90)
print("  行业偏好差异 Top 10 (pure_alpha 超配 vs rest) — 修正版")
print("="*90)
# pivot 出每 cube × 每行业的 share (缺失=0)
ind_pivot = ind_weight.pivot_table(index="cube_symbol", columns="industry_l2",
                                    values="share", fill_value=0)
ind_pivot = ind_pivot.join(clean.set_index("symbol")[["group"]])
ind_mean = ind_pivot.groupby("group").mean().T
if "pure_alpha" in ind_mean.columns and "rest" in ind_mean.columns:
    ind_mean["diff"] = ind_mean["pure_alpha"] - ind_mean["rest"]
    top = ind_mean.reindex(ind_mean["diff"].abs().sort_values(ascending=False).index).head(15)
    print(top[["pure_alpha","rest","diff"]].to_string())

# 额外: 持仓股票集合 — 45 个 pure_alpha 里谁最常被持有
print("\n" + "="*90)
print("  45 个 pure_alpha 最常持有的股票 Top 15")
print("="*90)
a_syms = clean[clean.group=="pure_alpha"]["symbol"]
rh_alpha = rh[rh.cube_symbol.isin(a_syms) & rh["target_weight"].fillna(0) > 0]
# 每 cube 持仓过的股票集合
cube_stks = rh_alpha.groupby("cube_symbol")["stock_symbol"].apply(set)
from collections import Counter
cnt = Counter()
for stks in cube_stks: cnt.update(stks)
top_stks = pd.DataFrame(cnt.most_common(15), columns=["stock","n_cubes_holding"])
top_stks["pct_of_45"] = top_stks["n_cubes_holding"] / 45
# 加 rest 里的持有比例对比
rest_syms = clean[clean.group=="rest"]["symbol"]
rh_rest = rh[rh.cube_symbol.isin(rest_syms) & rh["target_weight"].fillna(0) > 0]
rest_cube_stks = rh_rest.groupby("cube_symbol")["stock_symbol"].apply(set)
rest_cnt = Counter()
for stks in rest_cube_stks: rest_cnt.update(stks)
top_stks["n_in_rest"] = top_stks["stock"].map(lambda s: rest_cnt.get(s,0))
top_stks["pct_of_166"] = top_stks["n_in_rest"] / 166
top_stks["alpha_bias"] = top_stks["pct_of_45"] - top_stks["pct_of_166"]
# 用名字查询
stk_names = rh[["stock_symbol","stock_name"]].drop_duplicates().set_index("stock_symbol")["stock_name"]
top_stks["name"] = top_stks["stock"].map(stk_names)
print(top_stks[["stock","name","pct_of_45","pct_of_166","alpha_bias"]].to_string(index=False))

# 保存
full.reset_index().to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\n[+] 写入 {OUT}")
