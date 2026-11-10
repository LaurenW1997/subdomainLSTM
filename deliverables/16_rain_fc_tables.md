# 用 HRRR 预报降雨训练

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前模型（无降雨） 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前模型（无降雨） | 逐小时15km | 总量15km | 逐小时45km | 总量45km | 逐小时15km（起报周期） | 实测雨（上限） |
|---|---|---|---|---|---|---|---|---|
| 全部 | 847 | 4.47 | 4.56 (-0.02) | 4.52 (-0.02) | 4.55 (-0.02) | 4.57 (-0.01) | 4.50 (-0.03) | 4.25 (-0.12) |
| tide gauge | 51 | 4.42 | 4.56 (+0.09) | 4.52 (+0.06) | 4.53 (+0.08) | 4.48 (+0.06) | 4.50 (+0.08) | 4.40 (-0.03) |
| marsh | 413 | 3.06 | 3.05 (-0.01) | 3.00 (-0.00) | 3.04 (-0.01) | 3.02 (+0.01) | 3.03 (-0.01) | 2.95 (-0.09) |
| estuary / tidal channel | 44 | 6.26 | 6.28 (+0.01) | 6.19 (+0.04) | 6.19 (+0.02) | 6.33 (+0.07) | 6.41 (+0.03) | 6.01 (-0.11) |
| lake | 12 | 2.78 | 2.78 (+0.03) | 2.77 (+0.02) | 2.82 (+0.02) | 2.81 (+0.11) | 2.79 (+0.05) | 2.72 (-0.06) |
| river / canal | 256 | 5.82 | 5.66 (-0.09) | 5.86 (-0.10) | 5.73 (-0.10) | 5.89 (-0.11) | 5.70 (-0.14) | 5.06 (-0.52) |
| urban creek (Houston) | 71 | 12.36 | 11.71 (-0.85) | 11.56 (-0.92) | 11.64 (-0.78) | 11.43 (-1.04) | 11.57 (-1.13) | 7.96 (-4.90) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | 逐小时15km | 总量15km | 逐小时45km | 总量45km | 逐小时15km（起报周期） | 实测雨（上限） |
|---|---|---|---|---|---|---|---|
| 全部 | 847 | 116 好 / 28 差 | 114 好 / 22 差 | 115 好 / 25 差 | 118 好 / 31 差 | 114 好 / 26 差 | 202 好 / 6 差 |
| tide gauge | 51 | 0 好 / 2 差 | 0 好 / 1 差 | 0 好 / 2 差 | 0 好 / 0 差 | 0 好 / 1 差 | 0 好 / 0 差 |
| marsh | 413 | 0 好 / 2 差 | 1 好 / 0 差 | 1 好 / 1 差 | 0 好 / 10 差 | 1 好 / 1 差 | 1 好 / 0 差 |
| estuary / tidal channel | 44 | 4 好 / 4 差 | 3 好 / 1 差 | 5 好 / 2 差 | 4 好 / 2 差 | 1 好 / 2 差 | 8 好 / 1 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 1 差 | 0 好 / 0 差 | 0 好 / 1 差 | 0 好 / 1 差 | 0 好 / 0 差 |
| river / canal | 256 | 66 好 / 16 差 | 63 好 / 15 差 | 64 好 / 18 差 | 66 好 / 17 差 | 65 好 / 18 差 | 130 好 / 4 差 |
| urban creek (Houston) | 71 | 46 好 / 4 差 | 47 好 / 4 差 | 45 好 / 2 差 | 48 好 / 1 差 | 47 好 / 3 差 | 63 好 / 1 差 |

## 按 domain

| 分组 | 站数 | 当前模型（无降雨） | 逐小时15km | 总量15km | 逐小时45km | 总量45km | 逐小时15km（起报周期） | 实测雨（上限） |
|---|---|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.95 (-0.01) | 3.97 (-0.01) | 3.98 (-0.02) | 3.99 (+0.01) | 3.95 (-0.01) | 3.84 (-0.10) |
| Galveston100m | 152 | 8.98 | 9.33 (-0.43) | 8.95 (-0.32) | 9.00 (-0.33) | 8.88 (-0.38) | 8.99 (-0.36) | 7.42 (-1.85) |
| Texas100m | 79 | 5.39 | 5.37 (+0.01) | 5.34 (-0.01) | 5.45 (-0.02) | 5.58 (-0.02) | 5.26 (-0.05) | 5.05 (-0.11) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前模型（无降雨） | 逐小时15km | 总量15km | 逐小时45km | 总量45km | 逐小时15km（起报周期） | 实测雨（上限） |
|---|---|---|---|---|---|---|---|
| 1 h | 1.2 | 1.27 | 1.28 | 1.26 | 1.29 | 1.26 | 1.18 |
| 3 h | 2.77 | 2.81 | 2.84 | 2.81 | 2.83 | 2.81 | 2.68 |
| 6 h | 4.47 | 4.56 | 4.52 | 4.55 | 4.57 | 4.5 | 4.25 |

## 逐小时15km：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 逐小时15km | 差 |
|---|---|---|---|---|---|
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 23.49 | -4.18 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 30.64 | 26.5 | -4.14 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.78 | 18.05 | -3.72 |
| 07378050 | Comite R. at Greenwell Spg Rd near Baton Rouge, LA | river / canal | 21.01 | 17.64 | -3.38 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 18.97 | 15.63 | -3.34 |
| 07378000 | Comite River near Comite, LA | river / canal | 20.33 | 17.08 | -3.25 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 26.17 | 23.04 | -3.13 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 21.37 | 18.35 | -3.02 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 20.94 | 18.05 | -2.89 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 20.89 | -2.89 |
| 08031000 | Cow Bayou nr Mauriceville, TX | river / canal | 12.9 | 10.11 | -2.79 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 19.6 | 16.93 | -2.66 |

## 总量15km：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 总量15km | 差 |
|---|---|---|---|---|---|
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 26.17 | 21.7 | -4.47 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 21.37 | 17.46 | -3.91 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 15.02 | -3.68 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 24.01 | -3.67 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 18.97 | 15.36 | -3.61 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 15.76 | 12.16 | -3.59 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.78 | 18.3 | -3.48 |
| 07378000 | Comite River near Comite, LA | river / canal | 20.33 | 16.99 | -3.34 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 28.86 | 25.76 | -3.1 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 20.93 | -2.85 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 19.6 | 16.89 | -2.71 |
| 08069000 | Cypress Ck nr Westfield, TX | urban creek (Houston) | 17.55 | 14.92 | -2.63 |

## 逐小时45km：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 逐小时45km | 差 |
|---|---|---|---|---|---|
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 19.35 | -4.43 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 23.8 | -3.87 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 14.83 | -3.87 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 21.37 | 17.51 | -3.86 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.78 | 18.33 | -3.45 |
| 07378000 | Comite River near Comite, LA | river / canal | 20.33 | 17.22 | -3.11 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 26.17 | 23.09 | -3.09 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 18.97 | 16.02 | -2.95 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 30.64 | 27.74 | -2.9 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 15.76 | 12.86 | -2.9 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.01 | 14.24 | -2.78 |
| 08076700 | Greens Bayou at Ley Rd, Houston, TX | estuary / tidal channel | 24.97 | 22.22 | -2.76 |

## 总量45km：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 总量45km | 差 |
|---|---|---|---|---|---|
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 21.37 | 16.35 | -5.02 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 26.17 | 21.96 | -4.21 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 19.88 | -3.9 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 18.97 | 15.12 | -3.85 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 14.92 | -3.78 |
| 08069000 | Cypress Ck nr Westfield, TX | urban creek (Houston) | 17.55 | 13.89 | -3.66 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.78 | 18.21 | -3.57 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 19.6 | 16.08 | -3.52 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 24.22 | -3.45 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 30.64 | 27.36 | -3.28 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 23.4 | 20.29 | -3.11 |
| 08162600 | Tres Palacios Rv nr Midfield, TX | river / canal | 15.71 | 12.8 | -2.92 |

## 逐小时15km（起报周期）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 逐小时15km（起报周期） | 差 |
|---|---|---|---|---|---|
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 26.17 | 21.59 | -4.59 |
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 23.59 | -4.08 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 20.94 | 17.21 | -3.73 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 30.64 | 27.18 | -3.46 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 20.6 | -3.18 |
| 07378050 | Comite R. at Greenwell Spg Rd near Baton Rouge, LA | river / canal | 21.01 | 17.86 | -3.16 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 15.55 | -3.15 |
| 08069000 | Cypress Ck nr Westfield, TX | urban creek (Houston) | 17.55 | 14.4 | -3.14 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 19.6 | 16.58 | -3.01 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 28.86 | 25.86 | -3.0 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 30.05 | 27.13 | -2.92 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.78 | 18.86 | -2.91 |

## 实测雨（上限）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 实测雨（上限） | 差 |
|---|---|---|---|---|---|
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 12.96 | -14.72 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 23.4 | 10.28 | -13.11 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 20.94 | 7.88 | -13.06 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 30.64 | 18.52 | -12.12 |
| 08075110 | Brays Bayou at MLK Jr Blvd, Houston, TX | estuary / tidal channel | 27.65 | 15.66 | -12.0 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 21.37 | 9.8 | -11.57 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 21.9 | 10.42 | -11.48 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.78 | 10.45 | -11.33 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 13.04 | -10.74 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 30.05 | 19.38 | -10.67 |
| 08075770 | Hunting Bayou at IH 610, Houston, TX | urban creek (Houston) | 19.85 | 9.27 | -10.58 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 19.6 | 9.05 | -10.55 |
