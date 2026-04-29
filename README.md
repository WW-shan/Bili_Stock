# Bili_Stock — An Honest A-Share Quant Case Study

A 9-month build (2025-08 → 2026-04) of a quantitative system on the Chinese A-share market. The journey: Bilibili stock-tip uploaders (cumulative −91.85%) → Xueqiu retail-consensus signal (audited down to ~2% net) → factor research (12 factors, all `t<2`) → first-board / 一进二 event strategies (systematically falsified) → **finally settled on a static 30/30/40 all-weather ETF portfolio with no timing and no stock picking**.

**The strategies do not make money on top of the market. The infrastructure, the audit framework, and the post-mortems do.** Six categories of strategy were systematically falsified before settling on the simplest possible answer.

> 🇨🇳 中文长文反思: [`docs/quant_strategy_lessons.md`](docs/quant_strategy_lessons.md). 这是这个项目最重要的产出, 比代码更值得读.

---

## What is the current production?

**Static 30/30/40 all-weather ETF portfolio, quarterly rebalance.**

| Asset | Weight | ETF |
|---|---:|---|
| Equity (70% Dividend-LowVol + 30% ChiNext) | 30% | 512890 / 159915 |
| Bond (5Y treasury) | 30% | 511010 |
| Gold | 40% | 518880 |

**16-year backtest (2010-06 → 2026-04):** CAGR 8.11% / MDD −19.4% / Calmar 0.42 / Sharpe 0.69 — survives 2015 股灾 (−19%), 2018 trade war (+1%), 2020 COVID (−7%), 2022-23 bear (−5%).

```bash
# Daily diagnostic / quarterly rebalance signal
python research/factors_v2/run_all_weather_signal.py
python research/factors_v2/run_all_weather_signal.py --t2     # opt-in T2 momentum overlay
python research/factors_v2/run_all_weather_signal.py --push   # DingTalk push
```

The previous default was T2 dual-momentum overlay (CAGR 8.59% / Calmar 0.49). Alpha-decomposition on 2026-04-28 found T2 OOS Calmar is **0.18 lower** than static (0.96 vs 1.13 on 2018-2026): one missed V-shaped recovery (2020-04, STK OFF when STK +29.6% next quarter) cancels years of small correct calls. Static is the new default; `--t2` keeps the overlay available for users who want a 2015-style crash insurance.

---

## What was systematically falsified

This is the gold of the repo. Every entry below has a rigorous random-control + OOS test in [`research/foundation/`](research/foundation/).

| Strategy category | Verdict | Evidence |
|---|---|---|
| Xueqiu retail consensus (Top30) | ⛔ Inverted signal — Top30 +0.7%/yr, Bottom30 +7.5%/yr | `docs/quant_strategy_lessons.md` |
| 12 single factors (BM, ROE, momentum, low-vol, BAB, MAX, reversal, …) | ⛔ All `t<2`. Strongest signal is **inverse** (avoid high turnover, `t=−5.37`) | `memory/factor_battery_findings.md` |
| Low-vol baseline (60-day std, top 20%) | ⛔ Train Calmar +1.79 → **Test Calmar −0.71** OOS reversal | `research/factors_v2/output/low_vol_foundation_validation.md` |
| 一进二板 / 打板战法 (H1, H8 V1/V2/V3) | ⛔ 65,503 events / 16 years — all variants negative alpha. +1.87% alpha exists in T close → T+1 open overnight gap (limits to arbitrage, retail can't capture) | `research/factors_v2/output/first_board_research_summary.md` |
| Textbook board rules (H9: volume 2x / small-cap+low-price / history limit-ups / next-day +4% gap) | ⛔ All 5 rules **reverse-direction** at daily frequency. ALL stack `α=−1.75% t=−8.23` | `research/factors_v2/output/h9_textbook_rules.md` |
| T2 dual-momentum overlay on all-weather | ⚠️ Train alpha valid, **Test OOS Calmar −0.18 vs static**. Production demoted to opt-in | `research/factors_v2/output/all_weather_alpha_decomp.md` |

The pattern that recurs: backtest shows 5-20% alpha → random-control + OOS shrinks it to 0-2% → cost eats the rest → real alpha was structural beta or look-ahead leakage.

---

## The infrastructure (this is the actual deliverable)

### `research/foundation/` — the audit-enforced backtest framework

After 5 fixed bugs (B1-B4 + defensive guards) and 7-segment self-test, this is now the only path for new strategies. **It refuses to run without random control + OOS split + benchmark match + cost model.**

```python
from research.foundation import (
    DataBundle, Universe, CostModel,
    CrossSectionalStrategy, EventDrivenStrategy,
    Backtest, StandardReport,
)

data = DataBundle.load()                                # auto-audits OHLCV coverage / consistency
uni  = Universe.broad(data, mcap_range=(30, 500))        # explicit size tier
strat = CrossSectionalStrategy(name="my_factor",
                                factor_fn=my_fn,
                                top_pct=0.20, hold_days=180)
bt = Backtest(strategy=strat, universe=uni,
              cost_model=CostModel.a_share_retail_quarterly(),  # 33-73 bp realistic
              random_control=True,                                # required, raises if missing
              train_test_split=("2018-12-31", "2019-01-01"),     # required
              n_random_repeats=1)                                  # do NOT raise; inflates t
result = bt.run()
StandardReport.from_result(result).print()
```

**Self-test the framework after any change:**
```bash
python research/foundation/self_test.py
# 7 segments must all pass: NULL, RANDOM, high-turnover (negative), look-ahead (positive),
# EventDriven NULL (18,972 events), cost consistency, train/test split.
```

Documented bugs and data-layer biases: [`research/foundation/AUDIT_FINDINGS_2026_04_27.md`](research/foundation/AUDIT_FINDINGS_2026_04_27.md).

### `data/cubes.db` — 55,000-record Xueqiu dataset

Even though the derived signal is inverted, this dataset is genuinely unique:

- 8,070 deduplicated smart-money rebalance events (887 duplicates removed)
- 1,373 unique stocks, 2014–2026
- Live validation labels on 14 months (53.76% win rate on 2025-Jan → 2026-Feb paper trades)

Use it for behavioral / sentiment research; do not use it as a tradable signal.

---

## The journey (post-audit numbers only)

| Phase | Period | Outcome |
|---|---|---|
| v1–v4 Bilibili/early Xueqiu | 2025-08 → 2025-12 | Look-ahead, broken metrics. Pre-audit Calmar 0.99, post-audit ~0.05 |
| v5 long-short pivot | 2026-01 | Ann ret 31% → 23% after realistic costs → broken (A-shares can't short) |
| v6.1 SRF + go-flat | 2026-02 | Pre-audit Calmar 1.13 → post-audit Calmar 0.07 (go-flat used current period's forward return) |
| Factor library (factors_v2) | 2026-03 → 2026-04 | 12 factors tested with random control. **All `t<2`**. Pivot to ETF allocation |
| All-weather discovery | 2026-04-21 | 30/30/40 → CAGR 8.13%, MDD −19.4%, Calmar 0.42 (vs prior 70/30 stock-only Calmar 0.18) |
| T2 momentum overlay | 2026-04-23 | Full Calmar 0.49, OOS Test Calmar 0.96 |
| Foundation framework | 2026-04-27 | 5 engine bugs fixed, 7-segment self-test, low-vol falsified OOS |
| H8 / H9 first-board | 2026-04-27→28 | 65k events, 6 textbook rule variants, all negative alpha |
| **T2 decomp + simplification** | 2026-04-28 | T2 OOS alpha turns negative; production demoted to static 30/30/40 |

Audit narrative in git log:
- `1a1fb68` look-ahead fix · `9a88817` long-only · `25c2684` realistic costs
- `dd71ccd` foundation v1 · `8e44ad6` H8/H9 falsification · `2b6551d` T2 alpha decomp + static default

---

## Reproducing the results

```bash
# Python 3.12, Windows/Linux
pip install -r requirements.txt

# 1. Build data foundation (one-time, ~10 min)
python research/data_prep/build_data_foundation.py
python research/data_prep/update_stock_data.py

# 2. Run the foundation self-test (must all pass)
python research/foundation/self_test.py

# 3. Reproduce the all-weather production
python research/factors_v2/all_weather_oos.py                # OOS for 6 momentum variants
python research/factors_v2/all_weather_alpha_decomp.py       # T2 vs static decomposition (this is the key one)

# 4. Reproduce the falsifications
python research/foundation/strategies_first_board_executable.py    # H8 (V1/V2/V3)
python research/foundation/strategies_h9_textbook_rules.py         # H9 (5 textbook rules)
python research/foundation/strategies_lowvol.py                    # low-vol OOS reversal

# 5. Daily production (run at quarter-end for rebalance)
python research/factors_v2/run_all_weather_signal.py              # static 30/30/40 (default)
python research/factors_v2/run_all_weather_signal.py --t2         # opt-in T2 overlay
python research/factors_v2/run_all_weather_signal.py --push       # DingTalk push
```

All numbers above are reproducible within rounding.

---

## Five non-obvious findings (updated)

1. **Retail consensus is a *negative* signal**, exactly as Barber-Odean (2000) predicted. Top30 picks underperform Bottom30 by 6.8pp/yr. No regime adaptation rescues this.
2. **Cost dominates everything for retail.** Raw Top30 alpha is +14-17% gross; 56 bp round-trip × 83% turnover = 9.8%/yr cost. Net alpha is marginally negative. This is why most retail "alpha" disappears at honest cost models.
3. **The +2% overnight gap on A-share limit-ups is real but unrealizable.** Foundation tests on 65,503 first-board events: a strategy entering at T-day close captures +1.87% (`t=+63`), but T-day close requires ex-post knowledge of whether the seal held. Strategies entering at T+1 open all show negative alpha — retail stands on the wrong side of the trade.
4. **Trend-following momentum kills you in V-shaped recoveries.** T2 had Train Calmar +0.18 vs static (alpha was real in 2010-2018). 2020-04 V-rebound: T2 was STK OFF, STK delivered +29.6% next quarter, BOND +1.2% — one missed V-bottom canceled all small correct calls. OOS Calmar −0.18.
5. **Five fixed engine bugs all flowed in the alpha-inflating direction.** B1: EventDriven holding +1 day inflates returns. B2: `n_random_repeats=30` shrinks random std → t-inflated. B3: event random baseline pulled from full timeline → market-environment alpha leaks in as signal alpha. B4: cross-sectional random pool overlapped with picks. B5: t-stat divides by zero on degenerate samples. There is no symmetry: bugs that *deflate* alpha are noticed and fixed by the user; bugs that *inflate* alpha sit silently in the engine for months.

---

## What I would do differently (still true after 9 months)

Documented in [`docs/quant_strategy_lessons.md`](docs/quant_strategy_lessons.md):

1. **Replicate a known academic result before inventing anything.** Validate the engine on Fama-French / Jegadeesh-Titman first.
2. **Pre-register one hypothesis at a time.** 81+ parameter experiments self-defeats statistically. Harvey-Liu-Zhu (2016) sets `t > 3.5` after multiple-testing correction.
3. **Out-of-sample is sacred.** Choose holdout on day one; do not peek.
4. **Cost is a parameter, not an afterthought.** Optimizing on 10 bp grids and shipping at 56 bp is the most common retail mistake.
5. **Economic intuition gates statistics.** "Why should retail consensus predict returns?" had no good answer in 2025; we measured it anyway, and the data agreed with theory in 2026.

---

## Repository structure

```
research/
  foundation/                  ★ The audit-enforced backtest framework. New strategies MUST go here.
    data.py                    DataBundle.load() with built-in audit
    universe.py                Size-tier explicit Universe class
    benchmark.py               Auto-matched benchmarks (raises on mismatch)
    backtest.py                Required random_control + OOS + cost
    strategies.py              CrossSectional / EventDriven base classes
    self_test.py               7-segment framework health check
    AUDIT_FINDINGS_2026_04_27.md  All known engine + data biases
  factors_v2/                  Production all-weather + falsification reports
    run_all_weather_signal.py  ★ Production quarterly rebalance signal
    all_weather_alpha_decomp.py  T2 vs static alpha decomposition
    output/                    All study reports as Markdown
  baseline_v6_1/               Legacy Xueqiu strategy (preserved for audit reproducibility)
  data_prep/                   Panel construction, OHLCV refresh
  factors/                     Signal generators (mostly legacy)
docs/
  quant_strategy_lessons.md    ★ The Chinese-language structural reflection
  factor_learning_notes_2026_04.md  Factor taxonomy reference
archive/bilibili_legacy/       Earliest pipeline (preserved for context)
data/                          SQLite DBs and OHLCV caches (gitignored)
config.py                      Capital, ETF tickers, DingTalk webhook (gitignored)
CLAUDE.md                      AI-assistant project rules + 4 hard production rules
```

The 4 hard production rules in `CLAUDE.md` are reproduced here, since they survived 8 rounds of falsification:

1. **No stock picking.** Any factor combination CAGR ≤ 12% — cannot beat a 70% DIV / 30% ChiNext static portfolio.
2. **No timing / no rotation.** SMA60/120 trends, regime gates, momentum rotation — all whipsawed away.
3. **No target-vol / no DD-brake.** Active de-risking misses rebounds; static rebalancing is structurally superior.
4. **Quarterly is enough.** Daily/weekly bleed cost; monthly/quarterly differ negligibly.

---

## Tech stack

Python 3.12 · Pandas · NumPy · BaoStock / AkShare / TuShare · SQLite / SQLAlchemy · Matplotlib

---

## Citation

```
Zhang, J. (2026). Bili_Stock: An honest A-share retail quant case study —
six categories of strategy systematically falsified, settling on a static
30/30/40 all-weather ETF portfolio. https://github.com/Soli22de/Bili_Stock
```

---

*Last updated: 2026-04-28. Production: static 30/30/40, quarterly rebalance, no timing, no picking. Every claim above is reproducible from the scripts in this repo.*
