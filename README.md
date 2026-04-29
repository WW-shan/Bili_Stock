# Bili_Stock — A 股量化诚实复盘

历时 9 个月 (2025-08 → 2026-04) 在中国 A 股市场搭建的量化系统。一路走来: B 站荐股博主 (累计 −91.85%) → 雪球散户共识信号 (审计后跌到 ~2% 净) → 因子研究 (12 因子全部 `t<2`) → 一进二/打板事件战法 (系统证伪) → **最终落到一个静态 30/30/40 全天候 ETF 组合, 不择时不选股**。

**这些策略本身不赚超额, 真正有价值的是基础设施、审计框架、和复盘文档。** 在settle 到最简单的答案之前, 6 类策略被系统证伪。

> 🇨🇳 中文长文反思 (最重要的产出, 比代码值得读): [`docs/quant_strategy_lessons.md`](docs/quant_strategy_lessons.md)

---

## 当前生产策略

**静态 30/30/40 全天候 ETF 组合, 季度再平衡**.

| 资产 | 权重 | ETF |
|---|---:|---|
| 股票 (70% 红利低波 + 30% 创业板) | 30% | 512890 / 159915 |
| 国债 (5 年期) | 30% | 511010 |
| 黄金 | 40% | 518880 |

**16 年回测 (2010-06 → 2026-04)**: CAGR 8.11% / MDD −19.4% / Calmar 0.42 / Sharpe 0.69 — 历经 2015 股灾 (−19%)、2018 贸易战 (+1%)、2020 疫情 (−7%)、2022-23 熊市 (−5%) 全部活下来。

```bash
# 日常诊断 / 季末调仓信号
python research/factors_v2/run_all_weather_signal.py
python research/factors_v2/run_all_weather_signal.py --t2     # 可选: 启用 T2 双动量 overlay
python research/factors_v2/run_all_weather_signal.py --push   # 推钉钉
```

之前默认是 T2 双动量 overlay (CAGR 8.59% / Calmar 0.49). 2026-04-28 做了 alpha 解构, 发现 T2 在 OOS 段 Calmar 比静态低 **0.18** (0.96 vs 1.13, 2018-2026 段): 一次错判 V 型反弹 (2020-04 STK OFF, 但下季 STK +29.6%) 把多年小对全部抵消. 静态成为新默认, `--t2` 保留为可选 (适合想要 2015 股灾保险的用户).

---

## 系统证伪的策略 (这才是真宝藏)

下面每一项都有 [`research/foundation/`](research/foundation/) 框架做的严格随机对照 + OOS 测试.

| 策略类别 | 判定 | 证据 |
|---|---|---|
| 雪球散户共识 (Top30) | ⛔ 信号反向 — Top30 +0.7%/年, Bottom30 +7.5%/年 | `docs/quant_strategy_lessons.md` |
| 12 个单因子 (BM, ROE, 动量, 低波, BAB, MAX, 反转 …) | ⛔ 全 `t<2`. 最强信号是**反向** (避开高换手, `t=−5.37`) | `memory/factor_battery_findings.md` |
| 低波 baseline (60d std, top 20%) | ⛔ Train Calmar +1.79 → **Test Calmar −0.71**, OOS 反转 | `research/factors_v2/output/low_vol_foundation_validation.md` |
| 一进二板 / 打板战法 (H1, H8 V1/V2/V3) | ⛔ 65,503 事件 / 16 年 — 所有变体负 alpha. +1.87% alpha 集中在 T close→T+1 open 的隔夜跳空 (limits to arbitrage, 散户拿不到) | `research/factors_v2/output/first_board_research_summary.md` |
| 教学视频规则 (H9: 量能 2x / 小盘低价 / 历史涨停 / 次日高开 4%+) | ⛔ 5 条规则在日级**全部反向**. 全叠加 `α=−1.75% t=−8.23` | `research/factors_v2/output/h9_textbook_rules.md` |
| T2 双动量 overlay (全天候) | ⚠️ Train alpha 真实, **Test OOS Calmar 比静态低 0.18**. 生产已降级为可选 | `research/factors_v2/output/all_weather_alpha_decomp.md` |

反复出现的模式: 回测显示 5-20% alpha → 加随机对照 + OOS 后缩到 0-2% → 成本吃掉剩下的 → 真实 alpha 其实是宇宙 beta 或前视泄漏.

---

## 基础设施 (这才是真正的交付物)

### `research/foundation/` — 强制审计的回测框架

经过 5 个 bug 修复 (B1-B4 + 防御保护) 和 7 段 self-test 全过, 现在是**新策略的唯一通道**。**没有随机对照 + OOS 切分 + 基准匹配 + 成本模型, 框架直接拒跑**。

```python
from research.foundation import (
    DataBundle, Universe, CostModel,
    CrossSectionalStrategy, EventDrivenStrategy,
    Backtest, StandardReport,
)

data = DataBundle.load()                                 # 自动审计 OHLCV 覆盖率 / 一致性
uni  = Universe.broad(data, mcap_range=(30, 500))         # 显式市值层级
strat = CrossSectionalStrategy(name="my_factor",
                                factor_fn=my_fn,
                                top_pct=0.20, hold_days=180)
bt = Backtest(strategy=strat, universe=uni,
              cost_model=CostModel.a_share_retail_quarterly(),  # 33-73bp 真实成本
              random_control=True,                                # 必填, 否则抛异常
              train_test_split=("2018-12-31", "2019-01-01"),     # 必填
              n_random_repeats=1)                                  # 不要调高, 会人为缩 random std 抬 t-stat
result = bt.run()
StandardReport.from_result(result).print()
```

**改框架后必跑 self-test**:
```bash
python research/foundation/self_test.py
# 7 段必须全过: NULL, RANDOM, 高换手 (反向), 前视 (正向), EventDriven NULL (18,972 事件), 成本一致性, 拆分严格性
```

完整 bug 清单和数据偏差: [`research/foundation/AUDIT_FINDINGS_2026_04_27.md`](research/foundation/AUDIT_FINDINGS_2026_04_27.md).

### `data/cubes.db` — 55,000 条雪球数据集

虽然衍生信号是反向的, 但这数据集本身在公网上独一无二:

- 8,070 笔去重后的 smart-money 调仓事件 (剔除 887 笔重复)
- 1,373 只独立股票, 2014–2026
- 14 个月 live 验证标签 (2025-Jan → 2026-Feb 模拟交易胜率 53.76%)

适合做行为/情绪类研究, **不要**当可交易信号用.

---

## 项目时间线 (post-audit 数字)

| 阶段 | 时间 | 结果 |
|---|---|---|
| v1–v4 B 站/早期雪球 | 2025-08 → 2025-12 | 前视, 指标错. 修前 Calmar 0.99, 修后 ~0.05 |
| v5 多空对冲变种 | 2026-01 | 年化 31% → 23% (真实成本) → 报废 (A 股不能做空) |
| v6.1 SRF + go-flat | 2026-02 | 修前 Calmar 1.13 → 修后 0.07 (go-flat 用了当期未来收益) |
| 因子库 (factors_v2) | 2026-03 → 2026-04 | 12 因子加随机对照测试. **全 `t<2`**. 转向 ETF 配置 |
| 全天候发现 | 2026-04-21 | 30/30/40 → CAGR 8.13%, MDD −19.4%, Calmar 0.42 (vs 此前 70/30 纯股 Calmar 0.18) |
| T2 动量 overlay | 2026-04-23 | Full Calmar 0.49, Test OOS Calmar 0.96 |
| Foundation 框架 | 2026-04-27 | 修 5 个引擎 bug, 7 段 self-test, 低波 OOS 证伪 |
| H8 / H9 一进二板 | 2026-04-27 → 28 | 65k 事件, 教学规则 6 个变体全部负 alpha |
| **T2 解构 + 简化** | 2026-04-28 | T2 OOS alpha 转负, 生产降级为静态 30/30/40 默认 |

git log 中的审计轨迹:
- `1a1fb68` 修前视 · `9a88817` long-only · `25c2684` 真实成本
- `dd71ccd` foundation v1 · `8e44ad6` H8/H9 证伪 · `2b6551d` T2 alpha 解构 + 静态默认

---

## 复现实验

```bash
# Python 3.12, Windows/Linux
pip install -r requirements.txt

# 1. 一次性建好数据基础 (~10 分钟)
python research/data_prep/build_data_foundation.py
python research/data_prep/update_stock_data.py

# 2. 跑框架自检 (必须全过)
python research/foundation/self_test.py

# 3. 复现全天候生产
python research/factors_v2/all_weather_oos.py                # 6 个动量变体的 OOS
python research/factors_v2/all_weather_alpha_decomp.py       # T2 vs 静态 alpha 解构 (★ 关键这一个)

# 4. 复现各种证伪
python research/foundation/strategies_first_board_executable.py    # H8 (V1/V2/V3)
python research/foundation/strategies_h9_textbook_rules.py         # H9 (5 条教学规则)
python research/foundation/strategies_lowvol.py                    # 低波 OOS 反转

# 5. 日常生产 (季末跑一次出调仓单)
python research/factors_v2/run_all_weather_signal.py              # 静态 30/30/40 (默认)
python research/factors_v2/run_all_weather_signal.py --t2         # 可选 T2 overlay
python research/factors_v2/run_all_weather_signal.py --push       # 推钉钉
```

上面所有数字四舍五入误差内可复现.

---

## 5 条非显然发现

1. **散户共识是负向信号**, 完全验证 Barber-Odean (2000) 的预测. Top30 比 Bottom30 跑输 6.8pp/年. regime 切换补救不了.
2. **散户的成本压制一切**. Top30 raw alpha 是 +14-17% gross, 但 56bp 双边 × 83% 换手 = 9.8%/年成本. 净 alpha 微负. 这就是为什么大部分散户"alpha"在真实成本下消失.
3. **A 股涨停股的 +2% 隔夜跳空真实存在但不可套利**. Foundation 在 65,503 笔首板事件验证: T 日 close 进场策略捕获 +1.87% (`t=+63`), 但 T 日 close 需要 ex-post 知道封单是否守住. T+1 open 进场的版本全部负 alpha — **散户站在 trade 的另一边**.
4. **趋势跟随动量在 V 型反弹中要命**. T2 在 Train 段 Calmar +0.18 (alpha 在 2010-2018 真实), 2020-04 V 型反弹时 STK OFF, 下季 STK +29.6%, BOND +1.2% — 一次错过 V 底把多次小对全抵消. OOS Calmar −0.18.
5. **修过的 5 个引擎 bug 全朝 alpha 高估方向偏**. B1: EventDriven 持仓多 1 天 → 收益虚高. B2: `n_random_repeats=30` → random std 缩小 → t-stat 虚高. B3: event random baseline 跨整个时间段抽 → 牛市信号 vs 熊市 random → 市场环境差异被算成 alpha. B4: cross-sectional random pool 没排除 picks. B5: t-stat 退化样本除零. **不存在对称: 让 alpha 缩小的 bug 用户会发现并报修, 让 alpha 膨胀的 bug 在引擎里默默躺好几个月**.

---

## 如果重做我会怎么做 (9 个月后仍然成立)

详见 [`docs/quant_strategy_lessons.md`](docs/quant_strategy_lessons.md):

1. **先复现已知学术结论再发明任何东西**. 在 Fama-French / Jegadeesh-Titman 上验证引擎. 如果复现不出, 你的引擎是坏的, 后面所有"新发现"都是噪音.
2. **预先注册一个假设**. 81 次参数实验是统计自杀. Harvey-Liu-Zhu (2016) 的标准是 multiple-testing 校正后 `t > 3.5`, 不是 3.0.
3. **OOS 是神圣的**. 第一天就划好 holdout, 不要偷看. 先跑 81 次实验再算 OOS 不是 OOS.
4. **成本是参数, 不是事后想起来的**. 用 10bp 优化, 用 56bp 上线, 是最常见的散户错误.
5. **经济直觉是统计的门**. "散户共识为什么应该预测收益?" 一句话答不上, 就别测. Barber-Odean 在 2000 年就预言了我们 2026 年的实证.

---

## 仓库结构

```
research/
  foundation/                  ★ 强制审计的回测框架. 新策略必须从这里走.
    data.py                    DataBundle.load() 内置审计
    universe.py                显式市值层级 Universe
    benchmark.py               自动匹配基准 (错配抛异常)
    backtest.py                必填 random_control + OOS + cost
    strategies.py              CrossSectional / EventDriven 基类
    self_test.py               7 段框架健康检查
    AUDIT_FINDINGS_2026_04_27.md  所有已知引擎 + 数据偏差
  factors_v2/                  生产全天候 + 各类证伪报告
    run_all_weather_signal.py  ★ 季末调仓生产信号
    all_weather_alpha_decomp.py  T2 vs 静态 alpha 解构
    output/                    所有研究 Markdown 报告
  baseline_v6_1/               遗留雪球策略 (保留以便审计可复现)
  data_prep/                   panel 构建 / OHLCV 刷新
  factors/                     信号生成器 (大部分遗留)
docs/
  quant_strategy_lessons.md    ★ 中文结构性反思
  factor_learning_notes_2026_04.md  因子分类参考
archive/bilibili_legacy/       最早的管线 (保留作上下文)
data/                          SQLite 和 OHLCV 缓存 (gitignore)
config.py                      本金 / ETF tickers / 钉钉 webhook (gitignore)
CLAUDE.md                      AI 协作规则 + 4 条硬规则
```

`CLAUDE.md` 里 4 条硬规则 (8 轮反复证伪后还活着, 在此重申):

1. **不选股**. 任何因子组合 CAGR ≤ 12% — 跑不赢 70% 红利 / 30% 创业板静态组合.
2. **不择时 / 不轮动**. SMA60/120 趋势, regime gate, 动量轮动 — 全被 whipsaw 毁掉.
3. **不 target-vol / 不 DD-brake**. 主动降仓 = 错过反弹; 静态再平衡结构上更优.
4. **季度足矣**. 日/周浪费 cost; 月/季差异微小.

---

## 技术栈

Python 3.12 · Pandas · NumPy · BaoStock / AkShare / TuShare · SQLite / SQLAlchemy · Matplotlib

---

## 引用

```
张靖恒 (2026). Bili_Stock: 一个诚实的 A 股散户量化复盘 —
6 类策略被系统证伪, 最终回到静态 30/30/40 全天候 ETF.
https://github.com/Soli22de/Bili_Stock
```

---

*最后更新: 2026-04-28. 当前生产: 静态 30/30/40, 季度再平衡, 不择时不选股. 上面所有声明均可由本仓库脚本复现.*
