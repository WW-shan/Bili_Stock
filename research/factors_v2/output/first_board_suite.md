# 首板事件回测套件 (H1 / H1b / H3)

事件数: 65,503 (主板沪/深 2014-2025)

## H1 次日 open 买 (cost 33bp)

# Backtest Report: H1 首板·次日开盘买

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 65503
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 19101
- 信号 gross 均值: +0.01%/期
- 信号 net 均值: -0.32%/期
- 信号胜率 (>0): 43.9%
- Random 对照 gross: +0.01%/期
- **Alpha vs random**: +0.01%/期
- **t-stat**: 0.20
- Alpha 胜率: 47%

## Test 段
- 期数: 46402
- 信号 gross 均值: -0.28%/期
- 信号 net 均值: -0.60%/期
- 信号胜率 (>0): 38.3%
- Random 对照 gross: -0.03%/期
- **Alpha vs random**: -0.25%/期
- **t-stat**: -10.69
- Alpha 胜率: 46%

## Full 段
- 期数: 65503
- 信号 gross 均值: -0.19%/期
- 信号 net 均值: -0.52%/期
- 信号胜率 (>0): 39.9%
- Random 对照 gross: -0.02%/期
- **Alpha vs random**: -0.18%/期
- **t-stat**: -8.74
- Alpha 胜率: 46%

## 判定
- ✗ **负 alpha**: 不可作系统策略

## H1b 尾盘抢板 (cost 186bp)

# Backtest Report: H1b 首板·尾盘抢板

**宇宙**: Universe(size_tier=broad, mcap=5-100000亿, min_turn=0.00%)
**成本**: A股散户短线: round-trip 1.63% (滑点 1.00+0.50, 佣金 2×0.013, 印花税 0.10)
**期数**: 65503
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 19137
- 信号 gross 均值: +2.05%/期
- 信号 net 均值: +0.43%/期
- 信号胜率 (>0): 58.4%
- Random 对照 gross: -0.19%/期
- **Alpha vs random**: +2.30%/期
- **t-stat**: 31.83
- Alpha 胜率: 61%

## Test 段
- 期数: 46366
- 信号 gross 均值: +1.48%/期
- 信号 net 均值: -0.15%/期
- 信号胜率 (>0): 51.9%
- Random 对照 gross: -0.22%/期
- **Alpha vs random**: +1.70%/期
- **t-stat**: 57.85
- Alpha 胜率: 59%

## Full 段
- 期数: 65503
- 信号 gross 均值: +1.65%/期
- 信号 net 均值: +0.02%/期
- 信号胜率 (>0): 53.8%
- Random 对照 gross: -0.21%/期
- **Alpha vs random**: +1.87%/期
- **t-stat**: 63.45
- Alpha 胜率: 59%

## 判定
- ✓ **强信号**: t > 3.5 (Harvey 多重检验通过), net α > 0.5%/期

