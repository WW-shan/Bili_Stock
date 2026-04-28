# H9 教学规则全叠加版 (2026-04-28)

Base = H8 V2 烂板 (盘中跌破涨停再封, T+1 open 进场).
叠加教学视频 5 条 TIER 1 规则: 量能/小盘低价/近期人气/次日高开.

## 总览

| 变体 | n | sig% | rand% | alpha% | t | win% | 净% |
|---|---:|---:|---:|---:|---:|---:|---:|
| base 烂板 | 55,344 | -0.17 | -0.03 | -0.14 | -6.26 | 44.8 | -0.50 |
| +A 量能2x | 27,265 | -0.07 | +0.07 | -0.13 | -4.34 | 44.6 | -0.39 |
| +B 小盘低价 | 17,070 | -0.37 | +0.02 | -0.39 | -9.00 | 41.6 | -0.70 |
| +C 历史涨停40d | 34,953 | -0.13 | +0.06 | -0.19 | -6.34 | 45.9 | -0.46 |
| +D 次日高开4% | 11,588 | -1.44 | +0.12 | -1.57 | -29.54 | 33.8 | -1.77 |
| ALL 全叠加 | 737 | -1.56 | +0.27 | -1.75 | -8.23 | 32.7 | -1.89 |

## 详情

### base 烂板

# Backtest Report: base 烂板

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 55344
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 15571
- 信号 gross 均值: +0.06%/期
- 信号 net 均值: -0.26%/期
- 信号胜率 (>0): 48.1%
- Random 对照 gross: +0.04%/期
- **Alpha vs random**: +0.02%/期
- **t-stat**: 0.43
- Alpha 胜率: 49%

## Test 段
- 期数: 39773
- 信号 gross 均值: -0.26%/期
- 信号 net 均值: -0.59%/期
- 信号胜率 (>0): 43.5%
- Random 对照 gross: -0.06%/期
- **Alpha vs random**: -0.20%/期
- **t-stat**: -7.80
- Alpha 胜率: 47%

## Full 段
- 期数: 55344
- 信号 gross 均值: -0.17%/期
- 信号 net 均值: -0.50%/期
- 信号胜率 (>0): 44.8%
- Random 对照 gross: -0.03%/期
- **Alpha vs random**: -0.14%/期
- **t-stat**: -6.26
- Alpha 胜率: 47%

## 判定
- ✗ **负 alpha**: 不可作系统策略

### +A 量能2x

# Backtest Report: +A 量能2x

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 27265
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 7942
- 信号 gross 均值: +0.18%/期
- 信号 net 均值: -0.15%/期
- 信号胜率 (>0): 49.3%
- Random 对照 gross: +0.11%/期
- **Alpha vs random**: +0.07%/期
- **t-stat**: 1.33
- Alpha 胜率: 50%

## Test 段
- 期数: 19323
- 信号 gross 均值: -0.17%/期
- 信号 net 均值: -0.50%/期
- 信号胜率 (>0): 42.7%
- Random 对照 gross: +0.05%/期
- **Alpha vs random**: -0.22%/期
- **t-stat**: -5.95
- Alpha 胜率: 46%

## Full 段
- 期数: 27265
- 信号 gross 均值: -0.07%/期
- 信号 net 均值: -0.39%/期
- 信号胜率 (>0): 44.6%
- Random 对照 gross: +0.07%/期
- **Alpha vs random**: -0.13%/期
- **t-stat**: -4.34
- Alpha 胜率: 47%

## 判定
- ✗ **负 alpha**: 不可作系统策略

### +B 小盘低价

# Backtest Report: +B 小盘低价

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 17070
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 3174
- 信号 gross 均值: -0.03%/期
- 信号 net 均值: -0.35%/期
- 信号胜率 (>0): 46.2%
- Random 对照 gross: +0.19%/期
- **Alpha vs random**: -0.21%/期
- **t-stat**: -1.70
- Alpha 胜率: 47%

## Test 段
- 期数: 13896
- 信号 gross 均值: -0.45%/期
- 信号 net 均值: -0.78%/期
- 信号胜率 (>0): 40.6%
- Random 对照 gross: -0.02%/期
- **Alpha vs random**: -0.43%/期
- **t-stat**: -9.60
- Alpha 胜率: 45%

## Full 段
- 期数: 17070
- 信号 gross 均值: -0.37%/期
- 信号 net 均值: -0.70%/期
- 信号胜率 (>0): 41.6%
- Random 对照 gross: +0.02%/期
- **Alpha vs random**: -0.39%/期
- **t-stat**: -9.00
- Alpha 胜率: 45%

## 判定
- ✗ **负 alpha**: 不可作系统策略

### +C 历史涨停40d

# Backtest Report: +C 历史涨停40d

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 34953
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 9895
- 信号 gross 均值: +0.12%/期
- 信号 net 均值: -0.21%/期
- 信号胜率 (>0): 48.9%
- Random 对照 gross: +0.14%/期
- **Alpha vs random**: -0.02%/期
- **t-stat**: -0.31
- Alpha 胜率: 49%

## Test 段
- 期数: 25058
- 信号 gross 均值: -0.23%/期
- 信号 net 均值: -0.55%/期
- 信号胜率 (>0): 44.8%
- Random 对照 gross: +0.03%/期
- **Alpha vs random**: -0.26%/期
- **t-stat**: -7.48
- Alpha 胜率: 47%

## Full 段
- 期数: 34953
- 信号 gross 均值: -0.13%/期
- 信号 net 均值: -0.46%/期
- 信号胜率 (>0): 45.9%
- Random 对照 gross: +0.06%/期
- **Alpha vs random**: -0.19%/期
- **t-stat**: -6.34
- Alpha 胜率: 48%

## 判定
- ✗ **负 alpha**: 不可作系统策略

### +D 次日高开4%

# Backtest Report: +D 次日高开4%

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 11588
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 2829
- 信号 gross 均值: -1.01%/期
- 信号 net 均值: -1.33%/期
- 信号胜率 (>0): 40.1%
- Random 对照 gross: +0.18%/期
- **Alpha vs random**: -1.19%/期
- **t-stat**: -11.11
- Alpha 胜率: 44%

## Test 段
- 期数: 8759
- 信号 gross 均值: -1.58%/期
- 信号 net 均值: -1.91%/期
- 信号胜率 (>0): 31.8%
- Random 对照 gross: +0.11%/期
- **Alpha vs random**: -1.69%/期
- **t-stat**: -27.67
- Alpha 胜率: 40%

## Full 段
- 期数: 11588
- 信号 gross 均值: -1.44%/期
- 信号 net 均值: -1.77%/期
- 信号胜率 (>0): 33.8%
- Random 对照 gross: +0.12%/期
- **Alpha vs random**: -1.57%/期
- **t-stat**: -29.54
- Alpha 胜率: 41%

## 判定
- ✗ **负 alpha**: 不可作系统策略

### ALL 全叠加

# Backtest Report: ALL 全叠加

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 737
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 128
- 信号 gross 均值: -1.82%/期
- 信号 net 均值: -2.15%/期
- 信号胜率 (>0): 37.5%
- Random 对照 gross: +0.08%/期
- **Alpha vs random**: -1.39%/期
- **t-stat**: -2.64
- Alpha 胜率: 48%

## Test 段
- 期数: 609
- 信号 gross 均值: -1.51%/期
- 信号 net 均值: -1.83%/期
- 信号胜率 (>0): 31.7%
- Random 对照 gross: +0.31%/期
- **Alpha vs random**: -1.82%/期
- **t-stat**: -7.85
- Alpha 胜率: 41%

## Full 段
- 期数: 737
- 信号 gross 均值: -1.56%/期
- 信号 net 均值: -1.89%/期
- 信号胜率 (>0): 32.7%
- Random 对照 gross: +0.27%/期
- **Alpha vs random**: -1.75%/期
- **t-stat**: -8.23
- Alpha 胜率: 42%

## 判定
- ✗ **负 alpha**: 不可作系统策略

