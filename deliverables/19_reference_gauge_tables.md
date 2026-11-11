# 参考水位站输入（无降雨）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 6 h-change scaling + gap filling 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 6 h-change scaling + gap filling | + downstream gauge | + downstream and upstream gauge |
|---|---|---|---|---|
| 全部 | 847 | 4.37 | 4.39 (-0.00) | 4.29 (-0.00) |
| tide gauge | 51 | 4.3 | 4.20 (-0.01) | 4.26 (+0.02) |
| marsh | 413 | 2.98 | 2.99 (-0.00) | 3.01 (-0.00) |
| estuary / tidal channel | 44 | 5.99 | 6.12 (-0.03) | 5.99 (-0.06) |
| lake | 12 | 2.69 | 2.67 (-0.00) | 2.73 (+0.02) |
| river / canal | 256 | 5.49 | 5.48 (+0.00) | 5.43 (-0.02) |
| urban creek (Houston) | 71 | 12.67 | 12.82 (-0.02) | 12.43 (-0.15) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | + downstream gauge | + downstream and upstream gauge |
|---|---|---|---|
| 全部 | 847 | 5 好 / 6 差 | 41 好 / 6 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 0 差 |
| marsh | 413 | 0 好 / 0 差 | 0 好 / 0 差 |
| estuary / tidal channel | 44 | 0 好 / 1 差 | 4 好 / 0 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 1 差 |
| river / canal | 256 | 3 好 / 4 差 | 21 好 / 4 差 |
| urban creek (Houston) | 71 | 2 好 / 1 差 | 16 好 / 1 差 |

## 按 domain

| 分组 | 站数 | 6 h-change scaling + gap filling | + downstream gauge | + downstream and upstream gauge |
|---|---|---|---|---|
| Louisiana100m | 633 | 3.84 | 3.84 (-0.00) | 3.86 (+0.00) |
| Galveston100m | 152 | 9.17 | 9.15 (+0.01) | 8.86 (-0.07) |
| Texas100m | 79 | 5.03 | 4.86 (-0.01) | 4.88 (-0.03) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 6 h-change scaling + gap filling | + downstream gauge | + downstream and upstream gauge |
|---|---|---|---|
| 1 h | 1.16 | 1.17 | 1.17 |
| 3 h | 2.71 | 2.7 | 2.68 |
| 6 h | 4.37 | 4.39 | 4.29 |

## + downstream gauge：变好最多的 12 个站

| 站号 | 站名 | 类型 | 6 h-change scaling + gap filling | + downstream gauge | 差 |
|---|---|---|---|---|---|
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.27 | 30.62 | -0.65 |
| 08164350 | Navidad Rv nr Speaks, TX | river / canal | 9.18 | 8.53 | -0.65 |
| 07378000 | Comite River near Comite, LA | river / canal | 19.04 | 18.4 | -0.64 |
| 08070200 | E Fk San Jacinto Rv nr New Caney, TX | urban creek (Houston) | 10.93 | 10.35 | -0.58 |
| 02492100 | Pearl River Navigation Canal Lock and Dam No. 2 | river / canal | 16.77 | 16.25 | -0.52 |
| 02481521 | WOLF RIVER AT BELLE FERRY ROAD NEAR LONG BEACH, MS | estuary / tidal channel | 8.74 | 8.24 | -0.5 |
| 07377750 | Comite River near Zachary, LA | river / canal | 11.22 | 10.74 | -0.49 |
| 07387050 | Vermilion Bay(B. Fearman) nr Intracoastal City, LA | estuary / tidal channel | 7.49 | 7.0 | -0.48 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 25.13 | 24.67 | -0.46 |
| 08076700 | Greens Bayou at Ley Rd, Houston, TX | estuary / tidal channel | 24.94 | 24.49 | -0.44 |
| 08078080 | Bastrop Bayou at CR 288 nr Lake Jackson, TX | river / canal | 6.44 | 6.0 | -0.44 |
| 07386980 | Vermilion River at Perry, LA | river / canal | 7.58 | 7.15 | -0.43 |

## + downstream and upstream gauge：变好最多的 12 个站

| 站号 | 站名 | 类型 | 6 h-change scaling + gap filling | + downstream and upstream gauge | 差 |
|---|---|---|---|---|---|
| 08076700 | Greens Bayou at Ley Rd, Houston, TX | estuary / tidal channel | 24.94 | 20.08 | -4.86 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 30.47 | 28.48 | -1.99 |
| 07377750 | Comite River near Zachary, LA | river / canal | 11.22 | 9.24 | -1.98 |
| 07377150 | Amite River at Grangeville, LA | river / canal | 5.76 | 4.15 | -1.6 |
| 08068090 | W Fk San Jacinto Rv abv Lk Houston nr Porter, TX | urban creek (Houston) | 10.45 | 8.9 | -1.55 |
| 07378000 | Comite River near Comite, LA | river / canal | 19.04 | 17.61 | -1.43 |
| 08074000 | Buffalo Bayou at Houston, TX | estuary / tidal channel | 27.49 | 26.06 | -1.43 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.27 | 29.91 | -1.36 |
| 08188500 | San Antonio Rv at Goliad, TX | river / canal | 8.78 | 7.43 | -1.34 |
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 5.75 | 4.51 | -1.24 |
| 07377600 | Comite R. at Pt. Hudson-Pride Rd near Milldale, LA | river / canal | 7.81 | 6.57 | -1.23 |
| 08070200 | E Fk San Jacinto Rv nr New Caney, TX | urban creek (Houston) | 10.93 | 9.7 | -1.23 |
