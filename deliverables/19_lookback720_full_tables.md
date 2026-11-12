# 回看 720 小时对比 72 小时（各训练 40 轮）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），846 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 look-back 72 h 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | look-back 72 h | look-back 720 h |
|---|---|---|---|
| 全部 | 846 | 4.39 | 4.31 (-0.06) |
| tide gauge | 51 | 4.39 | 4.33 (-0.13) |
| marsh | 412 | 3.13 | 3.00 (-0.06) |
| estuary / tidal channel | 44 | 6.17 | 6.09 (-0.10) |
| lake | 12 | 2.79 | 2.74 (-0.04) |
| river / canal | 256 | 5.37 | 5.38 (-0.01) |
| urban creek (Houston) | 71 | 11.08 | 11.12 (+0.19) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | look-back 720 h |
|---|---|---|
| 全部 | 846 | 26 好 / 34 差 |
| tide gauge | 51 | 0 好 / 0 差 |
| marsh | 412 | 7 好 / 1 差 |
| estuary / tidal channel | 44 | 2 好 / 2 差 |
| lake | 12 | 1 好 / 0 差 |
| river / canal | 256 | 14 好 / 18 差 |
| urban creek (Houston) | 71 | 2 好 / 13 差 |

## 按 domain

| 分组 | 站数 | look-back 72 h | look-back 720 h |
|---|---|---|---|
| Louisiana100m | 632 | 3.92 | 3.80 (-0.06) |
| Galveston100m | 152 | 8.57 | 8.41 (-0.03) |
| Texas100m | 79 | 5.01 | 4.92 (-0.04) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | look-back 72 h | look-back 720 h |
|---|---|---|
| 1 h | 1.16 | 1.18 |
| 3 h | 2.71 | 2.72 |
| 6 h | 4.39 | 4.31 |

## look-back 720 h：变好最多的 12 个站

| 站号 | 站名 | 类型 | look-back 72 h | look-back 720 h | 差 |
|---|---|---|---|---|---|
| 0738022395 | Black Bayou at Hwy 621 near Prairieville, LA | river / canal | 11.67 | 9.49 | -2.18 |
| CRMS6299-H01 | CRMS6299-H01 | marsh | 4.08 | 2.81 | -1.27 |
| 08162600 | Tres Palacios Rv nr Midfield, TX | river / canal | 12.98 | 11.8 | -1.18 |
| CRMS0541-H01 | CRMS0541-H01 | marsh | 11.5 | 10.37 | -1.13 |
| 08014800 | Bundick Creek near DeRidder, LA | river / canal | 8.51 | 7.48 | -1.03 |
| 08026000 | Sabine Rv nr Burkeville, TX | river / canal | 21.58 | 20.59 | -0.98 |
| 073802225 | Bayou Conway near Sorrento, LA | river / canal | 5.87 | 4.94 | -0.93 |
| 08078000 | Chocolate Bayou nr Alvin, TX | river / canal | 14.95 | 14.08 | -0.87 |
| 02490200 | Pearl River Navigation Canal Lock and Dam No. 3 | river / canal | 19.06 | 18.19 | -0.87 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 5.35 | 4.52 | -0.82 |
| 07377230 | Little Sandy Creek at Peairs Rd SE of Milldale, LA | river / canal | 9.25 | 8.45 | -0.8 |
| 08162500 | Colorado Rv nr Bay City, TX | river / canal | 12.63 | 11.87 | -0.76 |
