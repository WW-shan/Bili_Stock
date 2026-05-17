# Backtest Report: 52W-High Top20% (hold 180d)

**宇宙**: Universe(size_tier=broad, mcap=30-500亿, min_turn=0.15%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 32
**OOS Split**: train ≤ 2020-12-31  /  test ≥ 2021-01-01

## Train 段
- 期数: 15
- 信号 gross 均值: +9.95%/期
- 信号 net 均值: +9.62%/期
- 信号胜率 (>0): 86.7%
- Random 对照 gross: +0.05%/期
- **Alpha vs random**: +9.89%/期
- **t-stat**: 4.56
- Alpha 胜率: 93%

## Test 段
- 期数: 17
- 信号 gross 均值: +8.97%/期
- 信号 net 均值: +8.65%/期
- 信号胜率 (>0): 47.1%
- Random 对照 gross: +11.76%/期
- **Alpha vs random**: -2.79%/期
- **t-stat**: -0.47
- Alpha 胜率: 41%

## Full 段
- 期数: 32
- 信号 gross 均值: +9.43%/期
- 信号 net 均值: +9.10%/期
- 信号胜率 (>0): 65.6%
- Random 对照 gross: +6.27%/期
- **Alpha vs random**: +3.16%/期
- **t-stat**: 0.92
- Alpha 胜率: 66%

## 判定
- ✗ **负 alpha**: 不可作系统策略