# 用 HRRR 预报降雨代替实测降雨

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前模型（无降雨） 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|---|
| 全部 | 847 | 4.51 | 4.28 (-0.12) | 4.51 (-0.02) | 4.48 (-0.01) | 4.52 (+0.02) |
| tide gauge | 51 | 4.38 | 4.30 (-0.01) | 4.38 (+0.01) | 4.41 (+0.01) | 4.40 (-0.01) |
| marsh | 413 | 3.03 | 2.96 (-0.09) | 3.04 (-0.01) | 3.04 (-0.01) | 3.03 (+0.00) |
| estuary / tidal channel | 44 | 6.37 | 5.95 (-0.09) | 6.35 (+0.00) | 6.30 (+0.06) | 6.19 (+0.02) |
| lake | 12 | 2.77 | 2.72 (-0.04) | 2.74 (-0.01) | 2.74 (+0.01) | 2.76 (+0.01) |
| river / canal | 256 | 5.68 | 5.07 (-0.51) | 5.58 (-0.08) | 5.62 (-0.01) | 5.73 (+0.03) |
| urban creek (Houston) | 71 | 12.86 | 7.86 (-5.03) | 12.33 (-0.67) | 12.95 (-0.07) | 13.58 (+0.48) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|
| 全部 | 847 | 203 好 / 6 差 | 112 好 / 30 差 | 75 好 / 53 差 | 16 好 / 66 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| marsh | 413 | 2 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| estuary / tidal channel | 44 | 8 好 / 1 差 | 6 好 / 2 差 | 4 好 / 6 差 | 2 好 / 6 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| river / canal | 256 | 131 好 / 5 差 | 64 好 / 19 差 | 49 好 / 27 差 | 12 好 / 26 差 |
| urban creek (Houston) | 71 | 62 好 / 0 差 | 42 好 / 9 差 | 22 好 / 20 差 | 2 好 / 34 差 |

## 按 domain

| 分组 | 站数 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.82 (-0.11) | 3.91 (-0.01) | 3.93 (-0.01) | 3.94 (+0.00) |
| Galveston100m | 152 | 9.46 | 7.35 (-1.84) | 9.62 (-0.22) | 9.71 (+0.05) | 9.88 (+0.29) |
| Texas100m | 79 | 5.26 | 5.09 (-0.12) | 5.24 (-0.04) | 5.24 (+0.00) | 5.41 (-0.01) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|
| 1 h | 1.22 | 1.21 | 1.26 | 1.28 | 1.23 |
| 3 h | 2.78 | 2.65 | 2.78 | 2.77 | 2.77 |
| 6 h | 4.51 | 4.28 | 4.51 | 4.48 | 4.52 |

## AORC实测未来雨（完美预报）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | 差 |
|---|---|---|---|---|---|
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 28.06 | 13.0 | -15.06 |
| 07379050 | Ward Creek at Essen Lane near Baton Rouge, LA | river / canal | 24.85 | 10.17 | -14.68 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 19.97 | -13.27 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 21.26 | 8.41 | -12.85 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 22.65 | 11.31 | -11.34 |
| 08075110 | Brays Bayou at MLK Jr Blvd, Houston, TX | estuary / tidal channel | 27.57 | 16.26 | -11.3 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 9.53 | -11.24 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.98 | 10.08 | -10.9 |
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 21.75 | 10.91 | -10.85 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | urban creek (Houston) | 30.34 | 19.51 | -10.84 |
| 08073700 | Buffalo Bayou at Piney Point, TX | urban creek (Houston) | 31.43 | 20.62 | -10.81 |
| 08068325 | Willow Ck nr Tomball, TX | urban creek (Houston) | 19.47 | 9.02 | -10.45 |

## HRRR预报雨（起报时刻周期）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | HRRR预报雨（起报时刻周期） | 差 |
|---|---|---|---|---|---|
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.24 | 29.33 | -3.92 |
| 08066200 | Long King Ck at Livingston, TX | river / canal | 22.19 | 18.78 | -3.41 |
| 07375222 | Abita River north of Abita Springs, LA | river / canal | 17.06 | 13.68 | -3.38 |
| 08075900 | Greens Bayou nr US Hwy 75 nr Houston, TX | urban creek (Houston) | 19.82 | 16.58 | -3.25 |
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 13.04 | 9.96 | -3.08 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 21.26 | 18.22 | -3.04 |
| 08069000 | Cypress Ck nr Westfield, TX | urban creek (Houston) | 18.45 | 15.44 | -3.0 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 20.77 | 17.83 | -2.94 |
| 08078000 | Chocolate Bayou nr Alvin, TX | river / canal | 14.96 | 12.31 | -2.65 |
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.79 | 9.19 | -2.61 |
| 08076180 | Garners Bayou nr Humble, TX | urban creek (Houston) | 20.98 | 18.47 | -2.51 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 17.55 | 15.1 | -2.45 |

## HRRR预报雨（前1h周期）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | HRRR预报雨（前1h周期） | 差 |
|---|---|---|---|---|---|
| 08066200 | Long King Ck at Livingston, TX | river / canal | 22.19 | 19.34 | -2.84 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 20.73 | 18.27 | -2.46 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 17.7 | 15.33 | -2.37 |
| 07375222 | Abita River north of Abita Springs, LA | river / canal | 17.06 | 14.71 | -2.35 |
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 13.04 | 10.85 | -2.18 |
| 08177500 | Coleto Ck nr Victoria, TX | river / canal | 9.89 | 7.71 | -2.18 |
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.79 | 9.66 | -2.13 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 17.55 | 15.44 | -2.1 |
| 08164504 | E Mustang Ck nr Louise, TX | river / canal | 15.74 | 13.69 | -2.05 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.17 | 15.31 | -1.86 |
| 08068090 | W Fk San Jacinto Rv abv Lk Houston nr Porter, TX | urban creek (Houston) | 10.94 | 9.2 | -1.74 |
| 08078000 | Chocolate Bayou nr Alvin, TX | river / canal | 14.96 | 13.28 | -1.68 |

## 未来雨置零：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 未来雨置零 | 差 |
|---|---|---|---|---|---|
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 13.04 | 11.09 | -1.95 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 6.51 | 5.3 | -1.21 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 17.7 | 16.9 | -0.8 |
| 08076700 | Greens Bayou at Ley Rd, Houston, TX | estuary / tidal channel | 24.7 | 23.91 | -0.79 |
| 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 4.81 | 4.03 | -0.78 |
| 08073100 | Langham Ck at Addicks Res Outflow nr Addicks, TX | urban creek (Houston) | 18.63 | 17.86 | -0.77 |
| 08110100 | Davidson Ck nr Lyons, TX | river / canal | 11.36 | 10.61 | -0.75 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.17 | 16.43 | -0.74 |
| 08189700 | Aransas Rv nr Skidmore, TX | river / canal | 10.07 | 9.33 | -0.74 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 6.6 | 5.95 | -0.65 |
| 08206910 | Choke Canyon Res OWC nr Three Rivers, TX | river / canal | 3.36 | 2.71 | -0.65 |
| 07378000 | Comite River near Comite, LA | river / canal | 19.49 | 18.84 | -0.65 |
