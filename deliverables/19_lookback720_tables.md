# 回看 720 小时对比 72 小时（scaling + gap filling + HRRR rainfall，各训练 12 轮）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），846 个站所有 run 都有 ≥ 720 个样本。
6 h RMSE 各站中位数，cm；括号里是和 look-back 72 h (12 epochs) 的中位差（负 = 变好）。

## 全部站 / 按站点类型

| 分组 | 站数 | look-back 72 h (12 epochs) | look-back 720 h (12 epochs) |
|---|---|---|---|
| 全部 | 846 | 4.73 | 4.59 (-0.06) |
| tide gauge | 51 | 4.92 | 4.71 (-0.09) |
| marsh | 412 | 3.36 | 3.22 (-0.07) |
| estuary / tidal channel | 44 | 6.88 | 6.60 (-0.08) |
| lake | 12 | 3.02 | 3.00 (-0.04) |
| river / canal | 256 | 5.56 | 5.69 (-0.03) |
| urban creek (Houston) | 71 | 11.08 | 11.18 (-0.07) |

## 变好 / 变差 0.5 cm 以上的站数

| 分组 | 站数 | look-back 720 h (12 epochs) |
|---|---|---|
| 全部 | 846 | 34 好 / 33 差 |
| tide gauge | 51 | 0 好 / 0 差 |
| marsh | 412 | 4 好 / 1 差 |
| estuary / tidal channel | 44 | 2 好 / 3 差 |
| lake | 12 | 1 好 / 0 差 |
| river / canal | 256 | 22 好 / 17 差 |
| urban creek (Houston) | 71 | 5 好 / 12 差 |

## 按 domain

| 分组 | 站数 | look-back 72 h (12 epochs) | look-back 720 h (12 epochs) |
|---|---|---|---|
| Louisiana100m | 632 | 4.17 | 4.10 (-0.06) |
| Galveston100m | 152 | 8.9 | 9.08 (-0.09) |
| Texas100m | 79 | 5.52 | 5.42 (-0.07) |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | look-back 72 h (12 epochs) | look-back 720 h (12 epochs) |
|---|---|---|
| 1 h | 1.21 | 1.23 |
| 3 h | 2.92 | 2.9 |
| 6 h | 4.73 | 4.59 |

## look-back 720 h (12 epochs)：变好最多的 12 个站

| 站号 | 站名 | 类型 | look-back 72 h (12 epochs) | look-back 720 h (12 epochs) | 差 |
|---|---|---|---|---|---|
| 08065925 | Nelson Ck at FM 247 nr Huntsville, TX | river / canal | 19.8 | 17.08 | -2.71 |
| 08066087 | Gail Ck at FM 1280 nr Lovelady, TX | river / canal | 19.0 | 16.42 | -2.58 |
| 0738022395 | Black Bayou at Hwy 621 near Prairieville, LA | river / canal | 11.46 | 9.35 | -2.1 |
| 02492100 | Pearl River Navigation Canal Lock and Dam No. 2 | river / canal | 16.44 | 14.64 | -1.8 |
| 073802512 | Hackberry Bay NW of Grand Isle, LA | estuary / tidal channel | 7.44 | 5.93 | -1.51 |
| 08026000 | Sabine Rv nr Burkeville, TX | river / canal | 23.33 | 21.87 | -1.46 |
| 08164504 | E Mustang Ck nr Louise, TX | river / canal | 13.98 | 12.85 | -1.13 |
| 08066380 | Big Ck at SH 150 nr Shepherd, TX | river / canal | 11.44 | 10.33 | -1.11 |
| 02490200 | Pearl River Navigation Canal Lock and Dam No. 3 | river / canal | 19.26 | 18.16 | -1.1 |
| 08066200 | Long King Ck at Livingston, TX | river / canal | 22.31 | 21.23 | -1.08 |
| 07386600 | Vermilion River (B. Vermilion) near Carencro, LA | river / canal | 10.6 | 9.6 | -1.0 |
| 08033500 | Neches Rv nr Rockland, TX | river / canal | 4.88 | 4.06 | -0.83 |
