# 结构实验

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前模型（v6） 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前模型（v6） | 回看168h | 回看336h | 3层LSTM |
|---|---|---|---|---|---|
| 全部 | 847 | 4.51 | 4.48 (-0.04) | 4.49 (-0.04) | 4.54 (+0.00) |
| tide gauge | 51 | 4.39 | 4.31 (-0.06) | 4.22 (-0.09) | 4.47 (+0.01) |
| marsh | 413 | 3.03 | 3.03 (-0.05) | 3.00 (-0.06) | 3.06 (-0.00) |
| estuary / tidal channel | 44 | 6.37 | 5.93 (-0.08) | 5.92 (-0.09) | 6.14 (-0.01) |
| lake | 12 | 2.77 | 2.69 (-0.05) | 2.69 (-0.06) | 2.75 (-0.03) |
| river / canal | 256 | 5.68 | 5.75 (+0.00) | 5.81 (+0.02) | 5.71 (-0.00) |
| urban creek (Houston) | 71 | 12.86 | 12.97 (+0.13) | 13.03 (+0.11) | 12.92 (+0.09) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | 回看168h | 回看336h | 3层LSTM |
|---|---|---|---|---|
| 全部 | 847 | 14 好 / 30 差 | 17 好 / 27 差 | 5 好 / 11 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 1 差 |
| marsh | 413 | 0 好 / 1 差 | 3 好 / 1 差 | 0 好 / 0 差 |
| estuary / tidal channel | 44 | 3 好 / 0 差 | 3 好 / 2 差 | 2 好 / 1 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| river / canal | 256 | 10 好 / 15 差 | 9 好 / 16 差 | 3 好 / 5 差 |
| urban creek (Houston) | 71 | 1 好 / 14 差 | 2 好 / 8 差 | 0 好 / 4 差 |

## 按 domain

| 分组 | 站数 | 当前模型（v6） | 回看168h | 回看336h | 3层LSTM |
|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.82 (-0.04) | 3.78 (-0.06) | 3.94 (-0.00) |
| Galveston100m | 152 | 9.46 | 9.65 (+0.07) | 9.42 (+0.07) | 9.58 (+0.07) |
| Texas100m | 79 | 5.26 | 5.21 (-0.05) | 5.36 (-0.00) | 5.40 (+0.02) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前模型（v6） | 回看168h | 回看336h | 3层LSTM |
|---|---|---|---|---|
| 1 h | 1.22 | 1.25 | 1.24 | 1.23 |
| 3 h | 2.78 | 2.8 | 2.77 | 2.75 |
| 6 h | 4.51 | 4.48 | 4.49 | 4.54 |

## 回看168h：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（v6） | 回看168h | 差 |
|---|---|---|---|---|---|
| 0738022395 | Black Bayou at Hwy 621 near Prairieville, LA | river / canal | 13.3 | 10.7 | -2.6 |
| 302318088512600 | BILOXI BAY AT POINT CADET HARBOR AT BILOXI, MS | estuary / tidal channel | 7.83 | 6.61 | -1.22 |
| 08074598 | Whiteoak Bayou at Main St, Houston, TX | estuary / tidal channel | 21.64 | 20.56 | -1.08 |
| 02492100 | Pearl River Navigation Canal Lock and Dam No. 2 | river / canal | 16.09 | 15.11 | -0.98 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 17.54 | 16.7 | -0.84 |
| 08188800 | Guadalupe Rv nr Tivoli, TX | river / canal | 6.04 | 5.21 | -0.83 |
| 08162500 | Colorado Rv nr Bay City, TX | river / canal | 13.23 | 12.41 | -0.82 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 5.85 | -0.76 |
| 08026000 | Sabine Rv nr Burkeville, TX | river / canal | 20.48 | 19.75 | -0.73 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 17.7 | 16.97 | -0.73 |
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 7.71 | -0.7 |
| 08066500 | Trinity Rv at Romayor, TX | urban creek (Houston) | 5.64 | 5.02 | -0.61 |

## 回看336h：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（v6） | 回看336h | 差 |
|---|---|---|---|---|---|
| 07375105 | Bogue Falaya River near Camp Covington | river / canal | 8.38 | 6.92 | -1.46 |
| 07375222 | Abita River north of Abita Springs, LA | river / canal | 17.06 | 15.64 | -1.42 |
| 302318088512600 | BILOXI BAY AT POINT CADET HARBOR AT BILOXI, MS | estuary / tidal channel | 7.83 | 6.51 | -1.32 |
| 0738022395 | Black Bayou at Hwy 621 near Prairieville, LA | river / canal | 13.3 | 12.2 | -1.1 |
| 07381490 | Atchafalaya River at Simmesport, LA | river / canal | 8.41 | 7.52 | -0.89 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 5.88 | -0.72 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 5.87 | -0.64 |
| 08017118 | Calcasieu River at Cameron, LA | estuary / tidal channel | 6.6 | 5.98 | -0.62 |
| CRMS4938-H01 | CRMS4938-H01 | marsh | 5.82 | 5.23 | -0.59 |
| 08066500 | Trinity Rv at Romayor, TX | urban creek (Houston) | 5.64 | 5.05 | -0.59 |
| CRMS0386-H01 | CRMS0386-H01 | marsh | 4.24 | 3.68 | -0.56 |
| 02480590 | TCHOUTACABOUFFA RIVER NR D'IBERVILLE, MS | river / canal | 9.9 | 9.34 | -0.56 |

## 3层LSTM：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（v6） | 3层LSTM | 差 |
|---|---|---|---|---|---|
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 5.42 | -1.19 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 17.7 | 16.99 | -0.71 |
| 08074598 | Whiteoak Bayou at Main St, Houston, TX | estuary / tidal channel | 21.64 | 20.94 | -0.7 |
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 13.01 | 12.43 | -0.58 |
| 07378000 | Comite River near Comite, LA | river / canal | 19.48 | 18.95 | -0.53 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.8 | 4.3 | -0.5 |
| 08066380 | Big Ck at SH 150 nr Shepherd, TX | river / canal | 12.02 | 11.56 | -0.46 |
| 08041500 | Village Ck nr Kountze, TX | river / canal | 6.18 | 5.72 | -0.46 |
| 08017118 | Calcasieu River at Cameron, LA | estuary / tidal channel | 6.6 | 6.16 | -0.43 |
| 08066500 | Trinity Rv at Romayor, TX | urban creek (Houston) | 5.64 | 5.2 | -0.43 |
| 08206600 | Frio Rv at Tilden, TX | river / canal | 4.61 | 4.2 | -0.42 |
| 08068390 | Bear Br at Research Blvd, The Woodlands, TX | urban creek (Houston) | 20.7 | 20.32 | -0.39 |
