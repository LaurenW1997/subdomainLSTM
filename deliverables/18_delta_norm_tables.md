# 按 6 小时变化量归一化

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前业务模型 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前业务模型 | 只修缺测填充 | 换尺子一半 | 换尺子四分之三 | 完全换尺子 | 完全换尺子（无新通道） |
|---|---|---|---|---|---|---|---|
| 全部 | 847 | 4.51 | 4.48 (-0.01) | 4.37 (-0.06) | 4.40 (-0.06) | 4.44 (-0.05) | 4.50 (-0.04) |
| tide gauge | 51 | 4.39 | 4.33 (-0.01) | 4.30 (+0.05) | 4.42 (+0.13) | 4.76 (+0.30) | 4.69 (+0.38) |
| marsh | 413 | 3.03 | 3.03 (-0.01) | 2.98 (-0.04) | 3.03 (-0.03) | 3.08 (-0.01) | 3.13 (+0.01) |
| estuary / tidal channel | 44 | 6.37 | 6.19 (+0.00) | 5.99 (-0.01) | 6.29 (+0.07) | 6.44 (+0.09) | 6.59 (+0.11) |
| lake | 12 | 2.77 | 2.78 (-0.01) | 2.69 (-0.08) | 2.72 (-0.06) | 2.81 (-0.04) | 2.80 (-0.03) |
| river / canal | 256 | 5.68 | 5.63 (-0.01) | 5.49 (-0.19) | 5.45 (-0.21) | 5.50 (-0.21) | 5.57 (-0.22) |
| urban creek (Houston) | 71 | 12.86 | 13.02 (+0.09) | 12.67 (-0.11) | 12.58 (-0.21) | 12.48 (-0.22) | 12.80 (-0.22) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | 只修缺测填充 | 换尺子一半 | 换尺子四分之三 | 完全换尺子 | 完全换尺子（无新通道） |
|---|---|---|---|---|---|---|
| 全部 | 847 | 9 好 / 11 差 | 80 好 / 1 差 | 95 好 / 9 差 | 107 好 / 30 差 | 87 好 / 52 差 |
| tide gauge | 51 | 0 好 / 0 差 | 1 好 / 0 差 | 1 好 / 6 差 | 1 好 / 17 差 | 1 好 / 18 差 |
| marsh | 413 | 0 好 / 0 差 | 1 好 / 0 差 | 1 好 / 0 差 | 1 好 / 6 差 | 1 好 / 15 差 |
| estuary / tidal channel | 44 | 3 好 / 0 差 | 5 好 / 0 差 | 5 好 / 2 差 | 6 好 / 4 差 | 3 好 / 14 差 |
| lake | 12 | 0 好 / 0 差 | 2 好 / 0 差 | 2 好 / 0 差 | 1 好 / 1 差 | 1 好 / 1 差 |
| river / canal | 256 | 3 好 / 2 差 | 59 好 / 1 差 | 68 好 / 1 差 | 75 好 / 2 差 | 62 好 / 4 差 |
| urban creek (Houston) | 71 | 3 好 / 9 差 | 12 好 / 0 差 | 18 好 / 0 差 | 23 好 / 0 差 | 19 好 / 0 差 |

## 按 domain

| 分组 | 站数 | 当前业务模型 | 只修缺测填充 | 换尺子一半 | 换尺子四分之三 | 完全换尺子 | 完全换尺子（无新通道） |
|---|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.90 (-0.01) | 3.84 (-0.05) | 3.90 (-0.04) | 3.98 (-0.03) | 3.98 (-0.02) |
| Galveston100m | 152 | 9.46 | 9.50 (+0.06) | 9.17 (-0.15) | 9.25 (-0.23) | 9.13 (-0.23) | 9.11 (-0.22) |
| Texas100m | 79 | 5.26 | 5.19 (-0.03) | 5.03 (-0.08) | 5.30 (-0.13) | 5.16 (-0.11) | 5.38 (-0.08) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前业务模型 | 只修缺测填充 | 换尺子一半 | 换尺子四分之三 | 完全换尺子 | 完全换尺子（无新通道） |
|---|---|---|---|---|---|---|
| 1 h | 1.22 | 1.17 | 1.16 | 1.15 | 1.16 | 1.18 |
| 3 h | 2.78 | 2.79 | 2.71 | 2.72 | 2.78 | 2.76 |
| 6 h | 4.51 | 4.48 | 4.37 | 4.4 | 4.44 | 4.5 |

## 只修缺测填充：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 只修缺测填充 | 差 |
|---|---|---|---|---|---|
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 5.88 | -2.53 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 4.15 | -2.36 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 5.27 | -1.33 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.8 | 3.89 | -0.92 |
| 08116850 | Brazos Rv nr West Columbia, TX | estuary / tidal channel | 9.42 | 8.56 | -0.86 |
| 08066500 | Trinity Rv at Romayor, TX | urban creek (Houston) | 5.64 | 4.96 | -0.68 |
| 08074598 | Whiteoak Bayou at Main St, Houston, TX | estuary / tidal channel | 21.64 | 21.0 | -0.64 |
| 08070000 | E Fk San Jacinto Rv nr Cleveland, TX | urban creek (Houston) | 7.77 | 7.22 | -0.55 |
| 08070200 | E Fk San Jacinto Rv nr New Caney, TX | urban creek (Houston) | 10.8 | 10.29 | -0.52 |
| 02479500 | ESCATAWPA RIVER NEAR WILMER, AL | river / canal | 6.36 | 5.87 | -0.49 |
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.8 | 11.32 | -0.49 |
| 08161000 | Colorado Rv at Columbus, TX | river / canal | 4.96 | 4.49 | -0.47 |

## 换尺子一半：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 换尺子一半 | 差 |
|---|---|---|---|---|---|
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 5.52 | -2.88 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 3.67 | -2.84 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.8 | 2.5 | -2.3 |
| 08028500 | Sabine Rv nr Bon Wier, TX | river / canal | 8.08 | 6.14 | -1.95 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 4.95 | -1.65 |
| 02479000 | PASCAGOULA RIVER AT MERRILL, MS | river / canal | 5.03 | 3.52 | -1.51 |
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 7.25 | 5.75 | -1.5 |
| 08116850 | Brazos Rv nr West Columbia, TX | estuary / tidal channel | 9.42 | 7.93 | -1.49 |
| 07381515 | Atchafalaya River at Butte La Rose, LA | river / canal | 4.1 | 2.67 | -1.43 |
| 08068390 | Bear Br at Research Blvd, The Woodlands, TX | urban creek (Houston) | 20.7 | 19.42 | -1.28 |
| 08067000 | Trinity Rv at Liberty, TX | urban creek (Houston) | 3.93 | 2.67 | -1.26 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.75 | 20.5 | -1.24 |

## 换尺子四分之三：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 换尺子四分之三 | 差 |
|---|---|---|---|---|---|
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 5.25 | -3.16 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.8 | 2.24 | -2.56 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 3.98 | -2.52 |
| 08028500 | Sabine Rv nr Bon Wier, TX | river / canal | 8.08 | 6.02 | -2.06 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 4.82 | -1.78 |
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 7.25 | 5.66 | -1.59 |
| 02479000 | PASCAGOULA RIVER AT MERRILL, MS | river / canal | 5.03 | 3.46 | -1.57 |
| 07381515 | Atchafalaya River at Butte La Rose, LA | river / canal | 4.1 | 2.61 | -1.49 |
| 08067000 | Trinity Rv at Liberty, TX | urban creek (Houston) | 3.93 | 2.46 | -1.47 |
| 08162500 | Colorado Rv nr Bay City, TX | river / canal | 13.23 | 11.77 | -1.47 |
| 08116850 | Brazos Rv nr West Columbia, TX | estuary / tidal channel | 9.42 | 7.99 | -1.43 |
| 08068390 | Bear Br at Research Blvd, The Woodlands, TX | urban creek (Houston) | 20.7 | 19.29 | -1.41 |

## 完全换尺子：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 完全换尺子 | 差 |
|---|---|---|---|---|---|
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 5.22 | -3.19 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 3.74 | -2.76 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.8 | 2.21 | -2.59 |
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 7.25 | 5.06 | -2.18 |
| 08028500 | Sabine Rv nr Bon Wier, TX | river / canal | 8.08 | 5.95 | -2.14 |
| 02479000 | PASCAGOULA RIVER AT MERRILL, MS | river / canal | 5.03 | 3.16 | -1.87 |
| 08067000 | Trinity Rv at Liberty, TX | urban creek (Houston) | 3.93 | 2.29 | -1.64 |
| 08116850 | Brazos Rv nr West Columbia, TX | estuary / tidal channel | 9.42 | 7.82 | -1.6 |
| 02475000 | LEAF RIVER NR MCLAIN, MS | river / canal | 6.01 | 4.46 | -1.55 |
| 07378000 | Comite River near Comite, LA | river / canal | 19.48 | 17.95 | -1.53 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 5.08 | -1.52 |
| 07381515 | Atchafalaya River at Butte La Rose, LA | river / canal | 4.1 | 2.64 | -1.46 |

## 完全换尺子（无新通道）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 完全换尺子（无新通道） | 差 |
|---|---|---|---|---|---|
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 5.17 | -3.23 |
| 08028500 | Sabine Rv nr Bon Wier, TX | river / canal | 8.08 | 5.19 | -2.89 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 3.85 | -2.66 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.8 | 2.23 | -2.57 |
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 7.25 | 4.75 | -2.5 |
| 02479000 | PASCAGOULA RIVER AT MERRILL, MS | river / canal | 5.03 | 3.25 | -1.78 |
| 08162500 | Colorado Rv nr Bay City, TX | river / canal | 13.23 | 11.69 | -1.54 |
| 08108700 | Brazos Rv at SH 21 nr Bryan, TX | river / canal | 9.1 | 7.58 | -1.52 |
| 07381515 | Atchafalaya River at Butte La Rose, LA | river / canal | 4.1 | 2.6 | -1.5 |
| 02489500 | Pearl River near Bogalusa, LA | river / canal | 3.2 | 1.8 | -1.41 |
| 08067000 | Trinity Rv at Liberty, TX | urban creek (Houston) | 3.93 | 2.53 | -1.4 |
| 07378000 | Comite River near Comite, LA | river / canal | 19.48 | 18.13 | -1.35 |
