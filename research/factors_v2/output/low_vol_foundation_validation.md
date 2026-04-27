# Backtest Report: 低波 60d (top 20%)

**宇宙**: Universe(size_tier=broad, mcap=30-500亿, min_turn=0.15%)
**成本**: A股散户季度: round-trip 0.33% (滑点 0.10+0.10, 佣金 2×0.013, 印花税 0.10)
**期数**: 32
**OOS Split**: train ≤ 2018-12-31  /  test ≥ 2019-01-01

## Train 段
- 期数: 7
- 信号 gross 均值: -4.57%/期
- 信号 net 均值: -4.89%/期
- 信号胜率 (>0): 28.6%
- Random 对照 gross: -5.37%/期
- **Alpha vs random**: +0.80%/期
- **t-stat**: 0.81
- Alpha 胜率: 57%

## Test 段
- 期数: 25
- 信号 gross 均值: +4.06%/期
- 信号 net 均值: +3.73%/期
- 信号胜率 (>0): 64.0%
- Random 对照 gross: +6.22%/期
- **Alpha vs random**: -2.16%/期
- **t-stat**: -1.78
- Alpha 胜率: 40%

## Full 段
- 期数: 32
- 信号 gross 均值: +2.17%/期
- 信号 net 均值: +1.85%/期
- 信号胜率 (>0): 56.2%
- Random 对照 gross: +3.68%/期
- **Alpha vs random**: -1.51%/期
- **t-stat**: -1.53
- Alpha 胜率: 44%

## 判定
- ✗ **负 alpha**: 不可作系统策略