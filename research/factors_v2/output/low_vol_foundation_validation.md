# Backtest Report: 低波 17d (top 20%, hold_step=12 交易日)

**宇宙**: Universe(size_tier=broad, mcap=30-500亿, min_turn=0.15%)
**成本**: A股散户波段: round-trip 0.73% (滑点 0.30+0.30, 佣金 2×0.013, 印花税 0.10)
**期数**: 32
**OOS Split**: train ≤ 2018-12-31  /  test ≥ 2019-01-01

## Train 段
- 期数: 7
- 信号 gross 均值: -1.50%/期
- 信号 net 均值: -2.23%/期
- 信号胜率 (>0): 28.6%
- Random 对照 gross: -2.63%/期
- **Alpha vs random**: +1.13%/期
- **t-stat**: 1.79
- Alpha 胜率: 57%

## Test 段
- 期数: 25
- 信号 gross 均值: +1.14%/期
- 信号 net 均值: +0.42%/期
- 信号胜率 (>0): 56.0%
- Random 对照 gross: +1.89%/期
- **Alpha vs random**: -0.75%/期
- **t-stat**: -0.71
- Alpha 胜率: 56%

## Full 段
- 期数: 32
- 信号 gross 均值: +0.56%/期
- 信号 net 均值: -0.16%/期
- 信号胜率 (>0): 50.0%
- Random 对照 gross: +0.90%/期
- **Alpha vs random**: -0.34%/期
- **t-stat**: -0.40
- Alpha 胜率: 56%

## 判定
- ✗ **负 alpha**: 不可作系统策略