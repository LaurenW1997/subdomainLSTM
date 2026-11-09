# 降雨实验

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前模型（v6） 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前模型（v6） | 降雨15km+未来6h | 降雨点值+未来6h | 降雨15km仅过去 |
|---|---|---|---|---|---|
| 全部 | 847 | 4.51 | 4.28 (-0.12) | 4.28 (-0.14) | 4.50 (-0.03) |
| tide gauge | 51 | 4.39 | 4.30 (-0.01) | 4.28 (-0.02) | 4.34 (-0.00) |
| marsh | 413 | 3.03 | 2.96 (-0.09) | 2.95 (-0.10) | 3.02 (-0.02) |
| estuary / tidal channel | 44 | 6.37 | 5.95 (-0.09) | 6.10 (-0.08) | 6.23 (-0.03) |
| lake | 12 | 2.77 | 2.72 (-0.04) | 2.76 (-0.05) | 2.76 (-0.01) |
| river / canal | 256 | 5.68 | 5.07 (-0.51) | 5.08 (-0.50) | 5.59 (-0.08) |
| urban creek (Houston) | 71 | 12.86 | 7.86 (-5.02) | 7.68 (-4.37) | 12.51 (-0.12) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | 降雨15km+未来6h | 降雨点值+未来6h | 降雨15km仅过去 |
|---|---|---|---|---|
| 全部 | 847 | 202 好 / 6 差 | 199 好 / 4 差 | 69 好 / 18 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| marsh | 413 | 2 好 / 0 差 | 1 好 / 0 差 | 0 好 / 0 差 |
| estuary / tidal channel | 44 | 8 好 / 1 差 | 8 好 / 1 差 | 4 好 / 0 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 0 差 | 1 好 / 0 差 |
| river / canal | 256 | 130 好 / 5 差 | 129 好 / 2 差 | 50 好 / 11 差 |
| urban creek (Houston) | 71 | 62 好 / 0 差 | 61 好 / 1 差 | 14 好 / 7 差 |

## 按 domain

| 分组 | 站数 | 当前模型（v6） | 降雨15km+未来6h | 降雨点值+未来6h | 降雨15km仅过去 |
|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.82 (-0.10) | 3.82 (-0.11) | 3.91 (-0.03) |
| Galveston100m | 152 | 9.46 | 7.34 (-1.87) | 7.38 (-1.81) | 9.74 (-0.09) |
| Texas100m | 79 | 5.26 | 5.09 (-0.12) | 5.04 (-0.10) | 5.47 (-0.04) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前模型（v6） | 降雨15km+未来6h | 降雨点值+未来6h | 降雨15km仅过去 |
|---|---|---|---|---|
| 1 h | 1.22 | 1.21 | 1.21 | 1.25 |
| 3 h | 2.78 | 2.65 | 2.65 | 2.76 |
| 6 h | 4.51 | 4.28 | 4.28 | 4.5 |

## 降雨15km+未来6h：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（v6） | 降雨15km+未来6h | 差 |
|---|---|---|---|---|---|
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 28.06 | 13.0 | -15.06 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.84 | 10.17 | -14.67 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 19.97 | -13.27 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 21.26 | 8.41 | -12.85 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 22.65 | 11.31 | -11.34 |
| 08075110 | Brays Bayou at MLK Jr Blvd, Houston, TX | estuary / tidal channel | 27.56 | 16.26 | -11.3 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 9.53 | -11.24 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.97 | 10.08 | -10.89 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.75 | 10.9 | -10.84 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 30.34 | 19.51 | -10.83 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.42 | 20.62 | -10.81 |
| 08068325 | Willow Ck nr Tomball, TX | urban creek (Houston) | 19.47 | 9.02 | -10.45 |

## 降雨点值+未来6h：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（v6） | 降雨点值+未来6h | 差 |
|---|---|---|---|---|---|
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.84 | 10.32 | -14.53 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 28.06 | 13.81 | -14.24 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 21.26 | 8.29 | -12.97 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 22.18 | -11.05 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 22.65 | 11.64 | -11.01 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 9.84 | -10.94 |
| 08075770 | Hunting Bayou at IH 610, Houston, TX | urban creek (Houston) | 19.55 | 8.84 | -10.71 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.97 | 10.28 | -10.7 |
| 08068325 | Willow Ck nr Tomball, TX | urban creek (Houston) | 19.47 | 8.78 | -10.69 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 19.82 | 9.23 | -10.59 |
| 08075110 | Brays Bayou at MLK Jr Blvd, Houston, TX | estuary / tidal channel | 27.56 | 17.29 | -10.28 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.42 | 21.28 | -10.14 |

## 降雨15km仅过去：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（v6） | 降雨15km仅过去 | 差 |
|---|---|---|---|---|---|
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 13.01 | 10.46 | -2.55 |
| 08066200 | Long King Ck at Livingston, TX | river / canal | 22.18 | 19.77 | -2.41 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 17.7 | 15.55 | -2.15 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.84 | 23.09 | -1.75 |
| 08028000 | Bayou Anacoco near Rosepine, LA | river / canal | 12.12 | 10.41 | -1.71 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.17 | 15.59 | -1.58 |
| 07386600 | Vermilion River (B. Vermilion) near Carencro, LA | river / canal | 12.96 | 11.4 | -1.56 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 17.54 | 15.99 | -1.55 |
| 07378500 | Amite River near Denham Springs, LA | river / canal | 11.49 | 10.13 | -1.36 |
| 02492360 | WEST HOBOLOCHITTO CREEK NR MCNEILL, MS | river / canal | 9.64 | 8.3 | -1.34 |
| 08162600 | Tres Palacios Rv nr Midfield, TX | river / canal | 13.64 | 12.38 | -1.26 |
| 08115000 | Big Ck nr Needville, TX | urban creek (Houston) | 14.55 | 13.33 | -1.21 |
