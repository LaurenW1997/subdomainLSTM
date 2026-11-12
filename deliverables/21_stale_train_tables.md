# 训练时随机缺最近 1–3 小时（25% 样本）对比当前版本，数据完整时

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 current version 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | current version | trained with missing newest hours |
|---|---|---|---|
| 全部 | 847 | 4.38 | 4.35 (-0.02) |
| tide gauge | 51 | 4.39 | 4.48 (-0.01) |
| marsh | 413 | 3.12 | 3.07 (-0.01) |
| estuary / tidal channel | 44 | 6.17 | 6.20 (+0.01) |
| lake | 12 | 2.79 | 2.76 (-0.02) |
| river / canal | 256 | 5.37 | 5.40 (-0.05) |
| urban creek (Houston) | 71 | 11.08 | 10.89 (-0.03) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | trained with missing newest hours |
|---|---|---|
| 全部 | 847 | 34 好 / 10 差 |
| tide gauge | 51 | 0 好 / 0 差 |
| marsh | 413 | 3 好 / 0 差 |
| estuary / tidal channel | 44 | 0 好 / 0 差 |
| lake | 12 | 0 好 / 0 差 |
| river / canal | 256 | 22 好 / 3 差 |
| urban creek (Houston) | 71 | 9 好 / 7 差 |

## 按 domain

| 分组 | 站数 | current version | trained with missing newest hours |
|---|---|---|---|
| Louisiana100m | 633 | 3.91 | 3.91 (-0.02) |
| Galveston100m | 152 | 8.57 | 8.43 (-0.05) |
| Texas100m | 79 | 5.01 | 5.02 (-0.01) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | current version | trained with missing newest hours |
|---|---|---|
| 1 h | 1.16 | 1.15 |
| 3 h | 2.71 | 2.71 |
| 6 h | 4.38 | 4.35 |

## trained with missing newest hours：变好最多的 12 个站

| 站号 | 站名 | 类型 | current version | trained with missing newest hours | 差 |
|---|---|---|---|---|---|
| CRMS6299-H01 | CRMS6299-H01 | marsh | 4.08 | 2.58 | -1.5 |
| 02479130 | BLACK CREEK NR BROOKLYN, MS | river / canal | 7.09 | 5.8 | -1.29 |
| 08068390 | Bear Br at Research Blvd, The Woodlands, TX | urban creek (Houston) | 18.42 | 17.16 | -1.26 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 15.73 | 14.52 | -1.21 |
| 08014800 | Bundick Creek near DeRidder, LA | river / canal | 8.51 | 7.41 | -1.1 |
| 08065925 | Nelson Ck at FM 247 nr Huntsville, TX | river / canal | 17.97 | 16.93 | -1.04 |
| CRMS5255-H01 | CRMS5255-H01 | marsh | 3.08 | 2.14 | -0.94 |
| 02492343 | EAST HOBOLOCHITTO CREEK NR CAESAR, MS | river / canal | 7.4 | 6.51 | -0.89 |
| 07378050 | Comite R. at Greenwell Spg Rd near Baton Rouge, LA | river / canal | 18.06 | 17.17 | -0.89 |
| 08110100 | Davidson Ck nr Lyons, TX | river / canal | 9.58 | 8.75 | -0.83 |
| 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.59 | 10.78 | -0.82 |
| 08111085 | New Year Ck at SH 105 nr Brenham, TX | river / canal | 8.56 | 7.76 | -0.8 |
