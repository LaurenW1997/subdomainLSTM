# 参考水位站输入和长期摘要（带 HRRR 降雨）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 scaling + gap filling + HRRR rainfall 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | scaling + gap filling + HRRR rainfall | + downstream and upstream gauge | + 7-day and 30-day summaries |
|---|---|---|---|---|
| 全部 | 847 | 4.38 | 4.32 (-0.02) | 4.38 (-0.01) |
| tide gauge | 51 | 4.39 | 4.44 (-0.02) | 4.39 (-0.00) |
| marsh | 413 | 3.12 | 3.02 (-0.01) | 3.03 (-0.00) |
| estuary / tidal channel | 44 | 6.17 | 6.20 (-0.09) | 6.27 (+0.00) |
| lake | 12 | 2.79 | 2.81 (-0.01) | 2.87 (+0.00) |
| river / canal | 256 | 5.37 | 5.39 (-0.04) | 5.34 (-0.03) |
| urban creek (Houston) | 71 | 11.08 | 10.69 (-0.11) | 11.04 (+0.03) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | + downstream and upstream gauge | + 7-day and 30-day summaries |
|---|---|---|---|
| 全部 | 847 | 50 好 / 17 差 | 23 好 / 22 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 0 差 |
| marsh | 413 | 4 好 / 0 差 | 2 好 / 0 差 |
| estuary / tidal channel | 44 | 6 好 / 1 差 | 0 好 / 2 差 |
| lake | 12 | 1 好 / 0 差 | 0 好 / 0 差 |
| river / canal | 256 | 26 好 / 15 差 | 16 好 / 11 差 |
| urban creek (Houston) | 71 | 13 好 / 1 差 | 5 好 / 9 差 |

## 按 domain

| 分组 | 站数 | scaling + gap filling + HRRR rainfall | + downstream and upstream gauge | + 7-day and 30-day summaries |
|---|---|---|---|---|
| Louisiana100m | 633 | 3.91 | 3.91 (-0.01) | 3.89 (-0.01) |
| Galveston100m | 152 | 8.57 | 8.17 (-0.12) | 8.56 (-0.01) |
| Texas100m | 79 | 5.01 | 4.88 (-0.03) | 5.01 (-0.00) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | scaling + gap filling + HRRR rainfall | + downstream and upstream gauge | + 7-day and 30-day summaries |
|---|---|---|---|
| 1 h | 1.16 | 1.15 | 1.16 |
| 3 h | 2.71 | 2.71 | 2.72 |
| 6 h | 4.38 | 4.32 | 4.38 |

## + downstream and upstream gauge：变好最多的 12 个站

| 站号 | 站名 | 类型 | scaling + gap filling + HRRR rainfall | + downstream and upstream gauge | 差 |
|---|---|---|---|---|---|
| 08076700 | Greens Bayou at Ley Rd, Houston, TX | estuary / tidal channel | 21.78 | 18.19 | -3.59 |
| 08068090 | W Fk San Jacinto Rv abv Lk Houston nr Porter, TX | urban creek (Houston) | 9.89 | 7.7 | -2.19 |
| 08068390 | Bear Br at Research Blvd, The Woodlands, TX | urban creek (Houston) | 18.42 | 16.25 | -2.17 |
| 08108700 | Brazos Rv at SH 21 nr Bryan, TX | river / canal | 7.76 | 5.72 | -2.05 |
| 08076000 | Greens Bayou nr Houston, TX | urban creek (Houston) | 19.85 | 18.25 | -1.6 |
| 08074000 | Buffalo Bayou at Houston, TX | estuary / tidal channel | 25.4 | 24.01 | -1.39 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 20.86 | 19.5 | -1.36 |
| 07377750 | Comite River near Zachary, LA | river / canal | 9.55 | 8.2 | -1.35 |
| 08188500 | San Antonio Rv at Goliad, TX | river / canal | 7.6 | 6.25 | -1.34 |
| 02479130 | BLACK CREEK NR BROOKLYN, MS | river / canal | 7.09 | 5.77 | -1.31 |
| 07377243 | Sandy Ck at Alph. Forbes nr Greenwell Springs, LA | river / canal | 7.47 | 6.2 | -1.27 |
| 07377150 | Amite River at Grangeville, LA | river / canal | 5.26 | 4.06 | -1.2 |

## + 7-day and 30-day summaries：变好最多的 12 个站

| 站号 | 站名 | 类型 | scaling + gap filling + HRRR rainfall | + 7-day and 30-day summaries | 差 |
|---|---|---|---|---|---|
| 02479130 | BLACK CREEK NR BROOKLYN, MS | river / canal | 7.09 | 5.87 | -1.22 |
| CRMS6299-H01 | CRMS6299-H01 | marsh | 4.08 | 3.01 | -1.06 |
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.59 | 10.62 | -0.97 |
| 07386600 | Vermilion River (B. Vermilion) near Carencro, LA | river / canal | 10.82 | 9.88 | -0.95 |
| 08115000 | Big Ck nr Needville, TX | urban creek (Houston) | 15.16 | 14.27 | -0.89 |
| 08111085 | New Year Ck at SH 105 nr Brenham, TX | river / canal | 8.56 | 7.77 | -0.79 |
| 08066250 | Trinity Rv nr Goodrich, TX | river / canal | 9.67 | 8.95 | -0.72 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 20.07 | 19.37 | -0.7 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 19.36 | 18.69 | -0.67 |
| 07375222 | Abita River north of Abita Springs, LA | river / canal | 13.85 | 13.18 | -0.67 |
| 08164000 | Lavaca Rv nr Edna, TX | river / canal | 7.02 | 6.35 | -0.67 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 15.37 | 14.71 | -0.66 |
