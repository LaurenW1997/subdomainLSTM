# 用 HRRR 预报降雨代替实测降雨（起报对齐到 00/06/12/18 UTC）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 当前模型（无降雨） 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|---|
| 全部 | 847 | 4.47 | 4.25 (-0.12) | 4.47 (-0.01) | 4.49 (+0.00) | 4.50 (+0.00) |
| tide gauge | 51 | 4.42 | 4.40 (-0.03) | 4.39 (-0.01) | 4.41 (+0.00) | 4.36 (-0.00) |
| marsh | 413 | 3.06 | 2.95 (-0.09) | 3.06 (-0.00) | 3.05 (-0.00) | 3.10 (-0.00) |
| estuary / tidal channel | 44 | 6.26 | 6.01 (-0.11) | 6.34 (+0.01) | 6.38 (+0.06) | 6.28 (+0.01) |
| lake | 12 | 2.78 | 2.72 (-0.06) | 2.75 (-0.01) | 2.76 (+0.01) | 2.76 (-0.01) |
| river / canal | 256 | 5.82 | 5.06 (-0.52) | 5.73 (-0.04) | 5.95 (+0.01) | 5.87 (+0.03) |
| urban creek (Houston) | 71 | 12.36 | 7.96 (-4.90) | 12.82 (-0.65) | 13.10 (+0.12) | 13.32 (+0.44) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|
| 全部 | 847 | 202 好 / 6 差 | 100 好 / 49 差 | 64 好 / 70 差 | 27 好 / 61 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 1 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| marsh | 413 | 1 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 | 1 好 / 0 差 |
| estuary / tidal channel | 44 | 8 好 / 1 差 | 5 好 / 4 差 | 3 好 / 8 差 | 2 好 / 5 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 0 差 |
| river / canal | 256 | 130 好 / 4 差 | 57 好 / 32 差 | 42 好 / 36 差 | 19 好 / 23 差 |
| urban creek (Houston) | 71 | 63 好 / 1 差 | 38 好 / 12 差 | 19 好 / 26 差 | 5 好 / 33 差 |

## 按 domain

| 分组 | 站数 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.96 | 3.84 (-0.10) | 3.95 (-0.01) | 3.96 (+0.00) | 3.95 (-0.00) |
| Galveston100m | 152 | 8.98 | 7.42 (-1.85) | 9.39 (-0.11) | 9.14 (+0.12) | 9.52 (+0.25) |
| Texas100m | 79 | 5.39 | 5.05 (-0.11) | 5.28 (-0.03) | 5.29 (-0.03) | 5.32 (-0.05) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | HRRR预报雨（起报时刻周期） | HRRR预报雨（前1h周期） | 未来雨置零 |
|---|---|---|---|---|---|
| 1 h | 1.2 | 1.18 | 1.24 | 1.27 | 1.23 |
| 3 h | 2.77 | 2.68 | 2.81 | 2.83 | 2.76 |
| 6 h | 4.47 | 4.25 | 4.47 | 4.49 | 4.5 |

## AORC实测未来雨（完美预报）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | AORC实测未来雨（完美预报） | 差 |
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

## HRRR预报雨（起报时刻周期）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | HRRR预报雨（起报时刻周期） | 差 |
|---|---|---|---|---|---|
| 08075000 | Brays Bayou at Houston, TX | urban creek (Houston) | 27.67 | 23.89 | -3.78 |
| 07375222 | Abita River north of Abita Springs, LA | river / canal | 16.96 | 13.36 | -3.59 |
| 08075110 | Brays Bayou at MLK Jr Blvd, Houston, TX | estuary / tidal channel | 27.65 | 24.11 | -3.54 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 30.64 | 27.12 | -3.52 |
| 08074810 | Brays Bayou at Gessner Dr, Houston, TX | urban creek (Houston) | 20.94 | 18.05 | -2.9 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 20.98 | -2.8 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 15.76 | 13.1 | -2.66 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.01 | 14.41 | -2.6 |
| 08072680 | S Mayde Ck at Heathergold Dr nr Addicks, TX | urban creek (Houston) | 19.6 | 17.02 | -2.58 |
| 08066200 | Long King Ck at Livingston, TX | river / canal | 22.84 | 20.33 | -2.51 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 16.23 | -2.47 |
| 08074000 | Buffalo Bayou at Houston, TX | estuary / tidal channel | 27.37 | 25.02 | -2.35 |

## HRRR预报雨（前1h周期）：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | HRRR预报雨（前1h周期） | 差 |
|---|---|---|---|---|---|
| 08164504 | E Mustang Ck nr Louise, TX | river / canal | 14.9 | 11.48 | -3.42 |
| 08111051 | Carters Ck at FM 60 nr College Station, TX | river / canal | 23.78 | 20.75 | -3.03 |
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 12.34 | 9.69 | -2.65 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 18.26 | 15.67 | -2.59 |
| 08066175 | Kickapoo Ck at Onalaska, TX | river / canal | 15.76 | 13.31 | -2.44 |
| 07375222 | Abita River north of Abita Springs, LA | river / canal | 16.96 | 14.65 | -2.31 |
| 08177500 | Coleto Ck nr Victoria, TX | river / canal | 9.87 | 8.14 | -1.73 |
| 08078000 | Chocolate Bayou nr Alvin, TX | river / canal | 16.05 | 14.36 | -1.69 |
| 02492360 | WEST HOBOLOCHITTO CREEK NR MCNEILL, MS | river / canal | 10.88 | 9.21 | -1.66 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.01 | 15.43 | -1.59 |
| 08066300 | Menard Ck nr Rye, TX | urban creek (Houston) | 11.56 | 9.99 | -1.57 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 17.14 | -1.56 |

## 未来雨置零：变好最多的 12 个站

| 站号 | 站名 | 类型 | 当前模型（无降雨） | 未来雨置零 | 差 |
|---|---|---|---|---|---|
| 07378000 | Comite River near Comite, LA | river / canal | 20.33 | 18.61 | -1.72 |
| 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.7 | 17.28 | -1.42 |
| 08164800 | Placedo Ck nr Placedo, TX | river / canal | 17.01 | 15.73 | -1.28 |
| 07377210 | Sandy Creek nr Pride, LA | river / canal | 12.0 | 10.78 | -1.22 |
| 08073500 | Buffalo Bayou nr Addicks, TX | urban creek (Houston) | 23.24 | 22.09 | -1.15 |
| 08073100 | Langham Ck at Addicks Res Outflow nr Addicks, TX | urban creek (Houston) | 19.68 | 18.58 | -1.1 |
| 07377243 | Sandy Ck at Alph. Forbes nr Greenwell Springs, LA | river / canal | 8.2 | 7.22 | -0.98 |
| 08068700 | Cypress Ck at Sharp Rd nr Hockley, TX | urban creek (Houston) | 8.91 | 7.98 | -0.93 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 5.86 | 4.95 | -0.91 |
| 08076700 | Greens Bayou at Ley Rd, Houston, TX | estuary / tidal channel | 24.97 | 24.09 | -0.89 |
| 08177500 | Coleto Ck nr Victoria, TX | river / canal | 9.87 | 9.14 | -0.73 |
| 08072800 | Langham Ck nr Addicks, TX | urban creek (Houston) | 14.1 | 13.44 | -0.66 |
