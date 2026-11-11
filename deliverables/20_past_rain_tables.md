# 过去 72 小时降雨换成实时产品（模型不重训）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 AORC (training product) 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | AORC (training product) | MRMS radar rainfall | HRRR short-range forecast | no past rainfall |
|---|---|---|---|---|---|
| 全部 | 847 | 4.38 | 4.38 (+0.00) | 4.42 (+0.02) | 4.95 (+0.35) |
| tide gauge | 51 | 4.39 | 4.39 (-0.00) | 4.41 (+0.01) | 5.00 (+0.36) |
| marsh | 413 | 3.12 | 3.18 (+0.00) | 3.18 (+0.01) | 3.50 (+0.25) |
| estuary / tidal channel | 44 | 6.17 | 6.17 (-0.00) | 6.19 (+0.02) | 6.80 (+0.54) |
| lake | 12 | 2.79 | 2.79 (+0.00) | 2.77 (+0.01) | 3.10 (+0.15) |
| river / canal | 256 | 5.37 | 5.35 (+0.00) | 5.51 (+0.08) | 6.20 (+0.63) |
| urban creek (Houston) | 71 | 11.08 | 11.18 (+0.03) | 11.82 (+0.44) | 12.24 (+0.94) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | MRMS radar rainfall | HRRR short-range forecast | no past rainfall |
|---|---|---|---|---|
| 全部 | 847 | 1 好 / 0 差 | 4 好 / 93 差 | 1 好 / 303 差 |
| tide gauge | 51 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 12 差 |
| marsh | 413 | 0 好 / 0 差 | 0 好 / 1 差 | 0 好 / 69 差 |
| estuary / tidal channel | 44 | 0 好 / 0 差 | 0 好 / 4 差 | 0 好 / 24 差 |
| lake | 12 | 0 好 / 0 差 | 0 好 / 0 差 | 0 好 / 1 差 |
| river / canal | 256 | 1 好 / 0 差 | 3 好 / 55 差 | 1 好 / 144 差 |
| urban creek (Houston) | 71 | 0 好 / 0 差 | 1 好 / 33 差 | 0 好 / 53 差 |

## 按 domain

| 分组 | 站数 | AORC (training product) | MRMS radar rainfall | HRRR short-range forecast | no past rainfall |
|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.91 | 3.92 (+0.00) | 3.94 (+0.01) | 4.28 (+0.30) |
| Galveston100m | 152 | 8.57 | 8.56 (+0.02) | 8.70 (+0.24) | 9.34 (+0.85) |
| Texas100m | 79 | 5.01 | 5.00 (-0.00) | 5.07 (+0.02) | 5.57 (+0.42) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | AORC (training product) | MRMS radar rainfall | HRRR short-range forecast | no past rainfall |
|---|---|---|---|---|
| 1 h | 1.16 | 1.15 | 1.18 | 1.3 |
| 3 h | 2.71 | 2.72 | 2.75 | 2.96 |
| 6 h | 4.38 | 4.38 | 4.42 | 4.95 |

## MRMS radar rainfall：变好最多的 12 个站

| 站号 | 站名 | 类型 | AORC (training product) | MRMS radar rainfall | 差 |
|---|---|---|---|---|---|
| 08211520 | Oso Ck at Corpus Christi, TX | river / canal | 7.05 | 6.04 | -1.01 |
| 08068390 | Bear Br at Research Blvd, The Woodlands, TX | urban creek (Houston) | 18.42 | 17.98 | -0.44 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 20.86 | 20.57 | -0.29 |
| 08028000 | Bayou Anacoco near Rosepine, LA | river / canal | 8.69 | 8.43 | -0.26 |
| 08110100 | Davidson Ck nr Lyons, TX | river / canal | 9.58 | 9.35 | -0.23 |
| 02481000 | BILOXI RIVER AT WORTHAM, MS | river / canal | 8.69 | 8.5 | -0.19 |
| 07383500 | Bayou Des Glaises Diversion Ch. at Moreauville, LA | river / canal | 7.86 | 7.67 | -0.19 |
| 08075763 | Hunting Bayou at Hoffman St, Houston, TX | urban creek (Houston) | 13.18 | 13.0 | -0.19 |
| 08189200 | Copano Ck nr Refugio, TX | river / canal | 3.65 | 3.47 | -0.18 |
| 07375480 | CHAPPEPEELA CREEK SOUTHEAST OF LORANGER, LA. | river / canal | 5.82 | 5.65 | -0.17 |
| 08077600 | Clear Ck nr Friendswood, TX | urban creek (Houston) | 9.08 | 8.92 | -0.16 |
| 02479130 | BLACK CREEK NR BROOKLYN, MS | river / canal | 7.09 | 6.93 | -0.16 |

## HRRR short-range forecast：变好最多的 12 个站

| 站号 | 站名 | 类型 | AORC (training product) | HRRR short-range forecast | 差 |
|---|---|---|---|---|---|
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.59 | 10.32 | -1.27 |
| 07376500 | Natalbany River at Baptist, LA | river / canal | 9.3 | 8.49 | -0.82 |
| 08078000 | Chocolate Bayou nr Alvin, TX | river / canal | 14.95 | 14.25 | -0.7 |
| 02492343 | EAST HOBOLOCHITTO CREEK NR CAESAR, MS | river / canal | 7.4 | 6.85 | -0.55 |
| 08211520 | Oso Ck at Corpus Christi, TX | river / canal | 7.05 | 6.57 | -0.48 |
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 6.12 | 5.73 | -0.4 |
| 08189200 | Copano Ck nr Refugio, TX | river / canal | 3.65 | 3.25 | -0.4 |
| 08014800 | Bundick Creek near DeRidder, LA | river / canal | 8.51 | 8.14 | -0.38 |
| 08186000 | Cibolo Ck nr Falls City, TX | river / canal | 6.41 | 6.03 | -0.37 |
| 08072600 | Buffalo Bayou at State Hwy 6 nr Addicks, TX | urban creek (Houston) | 13.05 | 12.77 | -0.29 |
| 08116400 | Dry Ck nr Rosenberg, TX | urban creek (Houston) | 17.03 | 16.76 | -0.28 |
| CRMS0369-H01 | CRMS0369-H01 | marsh | 5.22 | 4.94 | -0.27 |

## no past rainfall：变好最多的 12 个站

| 站号 | 站名 | 类型 | AORC (training product) | no past rainfall | 差 |
|---|---|---|---|---|---|
| 08211520 | Oso Ck at Corpus Christi, TX | river / canal | 7.05 | 6.29 | -0.77 |
| 08189200 | Copano Ck nr Refugio, TX | river / canal | 3.65 | 3.2 | -0.45 |
| 08075780 | Greens Bayou at Cutten Rd nr Houston, TX | urban creek (Houston) | 8.57 | 8.25 | -0.32 |
| 08111085 | New Year Ck at SH 105 nr Brenham, TX | river / canal | 8.56 | 8.32 | -0.25 |
| 08188590 | North end of GBRA Calhoun Canal nr Long Mott,TX | river / canal | 32.15 | 31.91 | -0.24 |
| 07378100 | Beaver Bayou at Wax Rd near Baton Rouge, LA | river / canal | 7.76 | 7.54 | -0.22 |
| 073802225 | Bayou Conway near Sorrento, LA | river / canal | 5.87 | 5.69 | -0.19 |
| 02492343 | EAST HOBOLOCHITTO CREEK NR CAESAR, MS | river / canal | 7.4 | 7.24 | -0.16 |
| 08212300 | Tranquitas Ck at Kingsville, TX | river / canal | 5.7 | 5.55 | -0.15 |
| 08076997 | Clear Ck at Mykawa St nr Pearland, TX | urban creek (Houston) | 6.77 | 6.62 | -0.14 |
| CRMS0589-H01 | CRMS0589-H01 | marsh | 2.55 | 2.41 | -0.14 |
| 08067650 | W Fk San Jacinto Rv bl Lk Conroe nr Conroe, TX | urban creek (Houston) | 16.12 | 15.99 | -0.12 |
