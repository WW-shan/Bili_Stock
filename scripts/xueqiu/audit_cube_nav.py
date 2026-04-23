"""
雪球 291 cube 自报业绩 vs 真实 NAV 审计
=============================================
目的: 验证 data/cubes.db 里 291 个有交易数据 cube 的 annualized_gain_rate
     是不是真实的 (还是回填/粉饰).

流程:
  1. 从 DB 取 291 cube (有 RH 的子集)
  2. 对每个 cube 调雪球 nav_daily/all.json 抓每日 NAV
  3. 从 NAV 重算年化收益 (last/first)^(1/years) - 1
  4. 和 annualized_gain_rate 字段对比

用法:
  python scripts/xueqiu/audit_cube_nav.py --probe 5   # 先探 5 个
  python scripts/xueqiu/audit_cube_nav.py             # 全部 291
"""
import argparse
import json
import os
import sqlite3
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

for _k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "*"

import pandas as pd
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB = os.path.join(ROOT, "data", "cubes.db")
OUT = os.path.join(ROOT, "research", "factors_v2", "output", "cube_nav_audit.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://xueqiu.com/",
    "Origin": "https://xueqiu.com",
    "X-Requested-With": "XMLHttpRequest",
}

def get_session():
    # 从 config.py 读 cookie (gitignored)
    sys.path.insert(0, ROOT)
    try:
        from config import XUEQIU_COOKIE as raw
    except Exception:
        print("[x] config.py 里没找到 XUEQIU_COOKIE")
        sys.exit(1)
    s = requests.Session()
    s.headers.update(HEADERS)
    for c in raw.split("; "):
        if "=" in c:
            k, v = c.split("=", 1); s.cookies.set(k, v)
    return s


def fetch_nav(session, symbol: str, max_retries: int = 3) -> pd.DataFrame | None:
    """抓 cube 全部每日 NAV. 遇到 rate limit 自动退避重试."""
    url = f"https://xueqiu.com/cubes/nav_daily/all.json?cube_symbol={symbol}"
    for attempt in range(max_retries):
        try:
            r = session.get(url, timeout=15)
            # 400016 = 需重新登录 / rate limit; 429 = too many
            if r.status_code in (429, 400) or '400016' in r.text[:200]:
                wait = 30 * (attempt + 1)
                print(f"  [~] {symbol} rate-limited, 等 {wait}s 重试 ({attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                return None
            data = r.json()
            break
        except Exception as e:
            print(f"  [!] {symbol} 第 {attempt+1} 次异常: {str(e)[:60]}")
            time.sleep(10)
    else:
        return None
    try:
        if isinstance(data, list) and data and isinstance(data[0], dict) and "list" in data[0]:
            data = data[0]["list"]
        elif isinstance(data, dict) and "list" in data:
            data = data["list"]
        if not isinstance(data, list) or not data:
            return None
        df = pd.DataFrame(data)
        if "date" not in df.columns:
            return None
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        # Xueqiu 返回 net_value 或 value
        nv_col = next((c for c in ["net_value","value","nav"] if c in df.columns), None)
        if nv_col is None:
            return None
        df["nav"] = pd.to_numeric(df[nv_col], errors="coerce")
        return df[["date","nav"]].dropna()
    except Exception as e:
        print(f"  [!] {symbol}: {str(e)[:80]}")
        return None


def compute_real_stats(df: pd.DataFrame) -> dict:
    if len(df) < 20: return {}
    first, last = df.iloc[0], df.iloc[-1]
    years = (last["date"] - first["date"]).days / 365.25
    if years <= 0 or first["nav"] <= 0: return {}
    total_ret = last["nav"] / first["nav"] - 1
    cagr = (1 + total_ret) ** (1/years) - 1 if years >= 0.5 else total_ret / max(years, 0.01)
    mdd = (df["nav"] / df["nav"].cummax() - 1).min()
    return {
        "real_start": str(first["date"].date()),
        "real_end": str(last["date"].date()),
        "real_years": round(years, 2),
        "real_total_ret": round(total_ret * 100, 2),
        "real_cagr": round(cagr * 100, 2),
        "real_mdd": round(mdd * 100, 2),
        "nav_first": round(first["nav"], 4),
        "nav_last": round(last["nav"], 4),
        "nav_days": len(df),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", type=int, default=0, help="只抓前 N 个试水")
    ap.add_argument("--sleep", type=float, default=0.8, help="每次请求间隔秒")
    args = ap.parse_args()

    # 取 291
    con = sqlite3.connect(DB)
    cubes = pd.read_sql("""
        SELECT DISTINCT c.symbol, c.name, c.annualized_gain_rate, c.total_gain, c.followers_count, c.created_at
        FROM cubes c
        WHERE c.symbol IN (SELECT DISTINCT cube_symbol FROM rebalancing_history WHERE status='success')
        ORDER BY c.followers_count DESC
    """, con)
    con.close()
    print(f"[+] 候选 cube: {len(cubes)}")

    if args.probe > 0:
        cubes = cubes.head(args.probe)
        print(f"[+] PROBE 模式, 只抓前 {len(cubes)}")

    session = get_session()

    # 先试一个, 验 cookie
    first = cubes.iloc[0]
    print(f"\n[+] 试抓 {first['symbol']} 验证 cookie...")
    df = fetch_nav(session, first["symbol"])
    if df is None or df.empty:
        print(f"[x] cookie 可能过期 / endpoint 变化, 停")
        sys.exit(1)
    print(f"    OK: {len(df)} 天 NAV, {df['date'].min().date()} → {df['date'].max().date()}")

    # 已有成功结果 → 续跑 (跳过已成功的)
    done_syms = set()
    if os.path.exists(OUT):
        prev = pd.read_csv(OUT, encoding="utf-8-sig")
        ok_prev = prev.dropna(subset=["real_cagr"])
        done_syms = set(ok_prev["symbol"].astype(str))
        print(f"[+] 发现上次结果 {len(prev)} 行, 其中 {len(done_syms)} 已成功, 将跳过")
        rows = ok_prev.to_dict("records")
    else:
        rows = []

    batch_n = 0
    for i, row in cubes.iterrows():
        sym = row["symbol"]
        if sym in done_syms:
            continue
        df = fetch_nav(session, sym)
        stats = compute_real_stats(df) if df is not None else {}
        out = {
            "symbol": sym,
            "name": row["name"],
            "self_ann_gain": row["annualized_gain_rate"],
            "self_total_gain": row["total_gain"],
            "followers": row["followers_count"],
            "created_at": str(row["created_at"])[:10],
            **stats,
        }
        if stats:
            diff = out["real_cagr"] - out["self_ann_gain"]
            out["diff_pp"] = round(diff, 2)
            print(f"  {sym:10s} self={row['annualized_gain_rate']:>7.2f}%  real={stats['real_cagr']:>7.2f}%  "
                  f"diff={diff:>+7.2f}pp  MDD={stats['real_mdd']:>6.1f}%  {stats['real_years']}y", flush=True)
        else:
            print(f"  {sym:10s} [无 NAV 数据]", flush=True)
        rows.append(out)
        batch_n += 1
        # 每 30 个断点写盘 + 喘口气 (避免 rate limit)
        if batch_n % 30 == 0:
            pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig")
            print(f"  [~] 完成 {batch_n} 个, checkpoint 写盘, 休 25s 避限流", flush=True)
            time.sleep(25)
        else:
            time.sleep(args.sleep)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\n[+] 写入 {OUT}")

    # 总览
    hit = out_df.dropna(subset=["real_cagr"])
    print(f"\n=== 总览 ({len(hit)}/{len(out_df)} 抓到) ===")
    if len(hit) > 0:
        print(f"  自报年化中位: {hit['self_ann_gain'].median():.2f}%")
        print(f"  真实年化中位: {hit['real_cagr'].median():.2f}%")
        print(f"  差值 (real - self) 中位: {hit['diff_pp'].median():+.2f}pp")
        print(f"  差值 >+5pp (真实更好): {(hit['diff_pp']>5).sum()}")
        print(f"  差值 <-5pp (真实更差): {(hit['diff_pp']<-5).sum()}")
        print(f"  |差值| <2pp (基本对得上): {(hit['diff_pp'].abs()<2).sum()}")


if __name__ == "__main__":
    main()
