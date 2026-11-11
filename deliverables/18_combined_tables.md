# 新基础（换一半尺子、缺测前值填充）叠加降雨

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前业务模型 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前业务模型 | 新基础 | 旧基础+HRRR雨 | 新基础+HRRR雨 | 旧基础+实测雨 | 新基础+实测雨 |
|---|---|---|---|---|---|---|---|
| 全部 | 847 | 4.51 | 4.37 (-0.06) | 4.57 (-0.01) | 4.38 (-0.07) | 4.28 (-0.12) | 4.15 (-0.20) |
| tide gauge | 51 | 4.39 | 4.30 (+0.05) | 4.48 (+0.07) | 4.39 (+0.19) | 4.30 (-0.01) | 4.40 (+0.07) |
| marsh | 413 | 3.03 | 2.98 (-0.04) | 3.02 (+0.01) | 3.12 (-0.01) | 2.96 (-0.09) | 2.91 (-0.12) |
| estuary / tidal channel | 44 | 6.37 | 5.99 (-0.01) | 6.33 (+0.07) | 6.17 (+0.08) | 5.95 (-0.09) | 5.97 (-0.10) |
| lake | 12 | 2.77 | 2.69 (-0.08) | 2.81 (+0.10) | 2.79 (-0.12) | 2.72 (-0.04) | 2.76 (-0.12) |
| river / canal | 256 | 5.68 | 5.49 (-0.19) | 5.89 (-0.10) | 5.37 (-0.46) | 5.07 (-0.51) | 4.72 (-1.03) |
| urban creek (Houston) | 71 | 12.86 | 12.67 (-0.11) | 11.43 (-1.04) | 11.08 (-1.53) | 7.86 (-5.02) | 7.40 (-5.68) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | 新基础 | 旧基础+HRRR雨 | 新基础+HRRR雨 | 旧基础+实测雨 | 新基础+实测雨 |
|---|---|---|---|---|---|---|
| 全部 | 847 | 80 好 / 1 差 | 117 好 / 46 差 | 186 好 / 29 差 | 202 好 / 6 差 | 262 好 / 2 差 |
| tide gauge | 51 | 1 好 / 0 差 | 0 好 / 1 差 | 1 好 / 4 差 | 0 好 / 0 差 | 1 好 / 1 差 |
| marsh | 413 | 1 好 / 0 差 | 0 好 / 13 差 | 0 好 / 13 差 | 2 好 / 0 差 | 3 好 / 1 差 |
| estuary / tidal channel | 44 | 5 好 / 0 差 | 5 好 / 3 差 | 9 好 / 2 差 | 8 好 / 1 差 | 12 好 / 0 差 |
| lake | 12 | 2 好 / 0 差 | 0 好 / 1 差 | 2 好 / 0 差 | 0 好 / 0 差 | 2 好 / 0 差 |
| river / canal | 256 | 59 好 / 1 差 | 65 好 / 22 差 | 122 好 / 7 差 | 130 好 / 5 差 | 175 好 / 0 差 |
| urban creek (Houston) | 71 | 12 好 / 0 差 | 47 好 / 6 差 | 52 好 / 3 差 | 62 好 / 0 差 | 69 好 / 0 差 |

## 按 domain

| 分组 | 站数 | 当前业务模型 | 新基础 | 旧基础+HRRR雨 | 新基础+HRRR雨 | 旧基础+实测雨 | 新基础+实测雨 |
|---|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.84 (-0.05) | 3.99 (+0.00) | 3.91 (-0.04) | 3.82 (-0.10) | 3.69 (-0.16) |
| Galveston100m | 152 | 9.46 | 9.17 (-0.15) | 8.88 (-0.36) | 8.57 (-0.88) | 7.34 (-1.87) | 7.05 (-2.47) |
| Texas100m | 79 | 5.26 | 5.03 (-0.08) | 5.58 (-0.00) | 5.01 (-0.19) | 5.09 (-0.12) | 4.93 (-0.35) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前业务模型 | 新基础 | 旧基础+HRRR雨 | 新基础+HRRR雨 | 旧基础+实测雨 | 新基础+实测雨 |
|---|---|---|---|---|---|---|
| 1 h | 1.22 | 1.16 | 1.29 | 1.16 | 1.21 | 1.13 |
| 3 h | 2.78 | 2.71 | 2.83 | 2.71 | 2.65 | 2.58 |
| 6 h | 4.51 | 4.37 | 4.57 | 4.38 | 4.28 | 4.15 |

## 新基础：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 新基础 | 差 |
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

## 旧基础+HRRR雨：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 旧基础+HRRR雨 | 差 |
|---|---|---|---|---|---|
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 27.36 | -5.88 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 19.82 | 15.12 | -4.7 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 16.08 | -4.7 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.97 | 16.35 | -4.62 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.84 | 20.29 | -4.56 |
| 08069000 | Cypress Ck nr Westfield, TX | urban creek (Houston) | 18.44 | 13.89 | -4.55 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 17.54 | 13.07 | -4.47 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 30.34 | 26.2 | -4.14 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 28.06 | 24.22 | -3.84 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.75 | 18.21 | -3.54 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 25.4 | 21.96 | -3.44 |
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 13.01 | 9.71 | -3.29 |

## 新基础+HRRR雨：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 新基础+HRRR雨 | 差 |
|---|---|---|---|---|---|
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 26.14 | -7.1 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 30.34 | 24.95 | -5.39 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.42 | 26.29 | -5.14 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.84 | 19.81 | -5.03 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 28.06 | 23.07 | -4.99 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 17.54 | 12.68 | -4.86 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 16.04 | -4.74 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 25.4 | 20.86 | -4.54 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 19.82 | 15.37 | -4.45 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.97 | 16.58 | -4.39 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 21.26 | 17.06 | -4.21 |
| 08068325 | Willow Ck nr Tomball, TX | urban creek (Houston) | 19.47 | 15.63 | -3.83 |

## 旧基础+实测雨：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 旧基础+实测雨 | 差 |
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

## 新基础+实测雨：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前业务模型 | 新基础+实测雨 | 差 |
|---|---|---|---|---|---|
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 28.06 | 13.14 | -14.91 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.84 | 10.19 | -14.65 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 21.26 | 8.32 | -12.94 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 20.32 | -12.92 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.75 | 9.36 | -12.38 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.42 | 19.51 | -11.91 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 30.34 | 18.54 | -11.8 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 9.05 | -11.72 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 22.65 | 11.31 | -11.34 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.97 | 10.0 | -10.97 |
| 08068325 | Willow Ck nr Tomball, TX | urban creek (Houston) | 19.47 | 8.82 | -10.65 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 19.82 | 9.22 | -10.6 |
