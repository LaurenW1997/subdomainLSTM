# 09 一个全局模型 对 两个分组模型（表格）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站三组都有 ≥ 720 个样本。6 h RMSE 各站中位数，cm。

分组模型：潮汐组（潮位站、湿地、湖、河口，674 站）只用水位 + 过去和未来的风；河流组（河流、城市溪流，336 站）只用水位 + 同河上游流量，不用风。

## 全部站

| 分组 | 站数 | 只用水位（全局模型） | 全局模型（风+流量） | 分组模型（潮汐组：风；河流组：流量） | 分组 − 全局 (6 h) | 变好 ≥0.5 | 变差 ≥0.5 | < 5 cm 的站 (全局 → 分组) |
|---|---|---|---|---|---|---|---|---|
| 全部 | 847 | 5.15 | 4.54 | 4.49 | -0.04 | 28 | 68 | 56% → 57% |
| 潮汐组 | 520 | 4.36 | 3.68 | 3.63 | -0.06 | 6 | 2 | 70% → 72% |
| 河流组 | 327 | 7.34 | 7.22 | 7.27 | +0.08 | 22 | 66 | 34% → 32% |
| 其中大河站 | 38 | 5.06 | 4.93 | 4.66 | -0.18 | 9 | 4 | 50% → 53% |

## 按站点类型

| 分组 | 站数 | 只用水位（全局模型） | 全局模型（风+流量） | 分组模型（潮汐组：风；河流组：流量） | 分组 − 全局 (6 h) | 变好 ≥0.5 | 变差 ≥0.5 | < 5 cm 的站 (全局 → 分组) |
|---|---|---|---|---|---|---|---|---|
| tide gauge | 51 | 5.05 | 4.38 | 4.24 | -0.13 | 1 | 0 | 59% → 69% |
| marsh | 413 | 3.69 | 3.03 | 2.97 | -0.05 | 3 | 0 | 76% → 77% |
| estuary / tidal channel | 44 | 7.46 | 6.28 | 6.33 | -0.02 | 1 | 2 | 27% → 30% |
| lake | 12 | 3.47 | 2.73 | 2.67 | -0.06 | 1 | 0 | 75% → 83% |
| river / canal | 256 | 5.9 | 5.81 | 6.05 | +0.06 | 10 | 33 | 41% → 39% |
| urban creek (Houston) | 71 | 13.53 | 12.91 | 13.55 | +0.42 | 12 | 33 | 7% → 8% |

## 按 domain

| 分组 | 站数 | 只用水位（全局模型） | 全局模型（风+流量） | 分组模型（潮汐组：风；河流组：流量） | 分组 − 全局 (6 h) | 变好 ≥0.5 | 变差 ≥0.5 | < 5 cm 的站 (全局 → 分组) |
|---|---|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 4.48 | 3.94 | 3.88 | -0.04 | 8 | 26 | 66% → 67% |
| Galveston100m | 152 | 10.2 | 9.78 | 9.93 | +0.01 | 17 | 38 | 14% → 15% |
| Texas100m | 79 | 5.77 | 5.29 | 5.18 | -0.06 | 3 | 6 | 47% → 49% |

## 1 / 3 / 6 h（全部站中位数）

| 提前 | 只用水位（全局模型） | 全局模型（风+流量） | 分组模型（潮汐组：风；河流组：流量） |
|---|---|---|---|
| 1 h | 1.24 | 1.23 | 1.24 |
| 3 h | 3.0 | 2.78 | 2.73 |
| 6 h | 5.15 | 4.54 | 4.49 |

## 河流组：分组的作用 和 去掉风的作用 分开看

| 分组 | 站数 | 只用水位（全局模型） | 全局模型（风+流量） | 河流组（风+流量） | 河流组（只流量，无风） |
|---|---|---|---|---|---|
| 河流组全部 | 327 | 7.34 | 7.22 | 7.17 | 7.27 |
| 大河站 | 38 | 5.06 | 4.93 | 5.53 | 4.66 |
| 河流 / 运河（非大河） | 223 | 6.08 | 5.89 | 5.95 | 6.19 |
| Houston 城市溪流 | 71 | 13.53 | 12.91 | 12.89 | 13.55 |

“河流组（风+流量）”和全局模型的差别只在于单独训练；“河流组（只流量）”再去掉风。

## 大河站逐站（6 h RMSE，cm）

| 站号 | 站名 | 只用水位 | 全局模型（风+流量） | 河流组（风+流量） | 河流组（只流量） | 分组 − 全局 |
|---|---|---|---|---|---|---|
| 08026000 | Sabine Rv nr Burkeville, TX | 19.34 | 19.88 | 20.17 | 19.8 | -0.08 |
| 02492100 | Pearl River Navigation Canal Lock and Dam No. 2 | 16.58 | 15.74 | 16.22 | 17.07 | 1.34 |
| 02490200 | Pearl River Navigation Canal Lock and Dam No. 3 | 13.11 | 13.17 | 13.11 | 13.28 | 0.11 |
| 08162500 | Colorado Rv nr Bay City, TX | 12.99 | 12.89 | 13.16 | 12.88 | -0.01 |
| 08066250 | Trinity Rv nr Goodrich, TX | 10.43 | 10.63 | 10.03 | 10.23 | -0.4 |
| 08040600 | Neches Rv nr Town Bluff, TX | 10.71 | 10.48 | 10.33 | 10.27 | -0.21 |
| 08116650 | Brazos Rv nr Rosharon, TX | 6.5 | 10.33 | 18.92 | 6.38 | -3.95 |
| 08114100 | Brazos Rv nr Sugar Land, TX | 5.98 | 9.68 | 15.46 | 5.94 | -3.74 |
| 08098450 | Brazos Rv at FM 485 near Hearne, TX | 9.0 | 9.62 | 10.51 | 7.51 | -2.11 |
| 08108700 | Brazos Rv at SH 21 nr Bryan, TX | 8.88 | 9.07 | 9.48 | 10.16 | 1.09 |
| 07381490 | Atchafalaya River at Simmesport, LA | 7.8 | 8.34 | 11.57 | 8.53 | 0.18 |
| 08028500 | Sabine Rv nr Bon Wier, TX | 7.56 | 8.07 | 8.21 | 7.16 | -0.91 |
| 08110200 | Brazos Rv at Washington, TX | 7.97 | 7.92 | 8.56 | 7.63 | -0.29 |
| 073816525 | Mouth of Atchafalaya River at Atchafalaya Bay | 9.96 | 7.3 | 8.29 | 10.0 | 2.7 |
| 08108780 | Little Brazos Rv at FM 485 nr Hearne, TX | 6.48 | 6.95 | 6.55 | 6.47 | -0.48 |
| 08114000 | Brazos Rv at Richmond, TX | 4.36 | 6.85 | 23.98 | 3.97 | -2.88 |
| 08111500 | Brazos Rv nr Hempstead, TX | 5.26 | 6.03 | 7.72 | 5.62 | -0.4 |
| 08066500 | Trinity Rv at Romayor, TX | 5.02 | 5.4 | 5.49 | 4.77 | -0.62 |
| 08033500 | Neches Rv nr Rockland, TX | 5.44 | 5.27 | 5.03 | 5.26 | -0.01 |
| 08161000 | Colorado Rv at Columbus, TX | 5.19 | 4.59 | 5.08 | 4.55 | -0.04 |
| 07374000 | Mississippi River at Baton Rouge, LA | 3.7 | 4.56 | 8.97 | 3.91 | -0.65 |
| 08162000 | Colorado Rv at Wharton, TX | 4.31 | 4.46 | 5.09 | 3.97 | -0.49 |
| 07381600 | Lower Atchafalaya River at Morgan City, LA | 5.11 | 4.39 | 5.57 | 5.23 | 0.84 |
| 07374525 | Mississippi River at Belle Chasse, LA | 4.31 | 4.36 | 5.49 | 4.49 | 0.13 |
| 02492511 | East Pearl River at I-59 near Nicholson, MS | 3.75 | 3.9 | 3.89 | 4.09 | 0.2 |
| 08067000 | Trinity Rv at Liberty, TX | 3.46 | 3.85 | 5.5 | 2.72 | -1.13 |
| 08111850 | Brazos Rv at San Felipe, TX | 3.14 | 3.7 | 5.37 | 2.75 | -0.94 |
| 07381515 | Atchafalaya River at Butte La Rose, LA | 3.42 | 3.54 | 5.22 | 3.34 | -0.19 |
| 08030500 | Sabine Rv nr Ruliff, TX | 4.08 | 3.37 | 4.07 | 3.61 | 0.24 |
| 08033000 | Neches Rv nr Diboll, TX | 3.22 | 3.14 | 3.63 | 3.34 | 0.2 |
| 02489500 | Pearl River near Bogalusa, LA | 2.81 | 2.96 | 3.85 | 2.62 | -0.34 |
| 08066000 | Trinity Rv at Riverside, TX | 2.72 | 2.75 | 2.48 | 2.58 | -0.16 |
| 02492519 | Pearl River Navigation Canal Lock and Dam No. 1 | 2.08 | 2.47 | 2.27 | 2.1 | -0.36 |
| 08041000 | Neches Rv at Evadale, TX | 2.07 | 2.22 | 2.67 | 1.99 | -0.23 |
| 08030520 | Sabine Rv at Intl Paper nr Orange, TX | 1.85 | 1.99 | 2.16 | 1.92 | -0.07 |
| 02492600 | Pearl River at Pearl River, LA | 1.91 | 1.98 | 2.28 | 1.97 | -0.01 |
| 02490193 | Pearl River at Pools Bluff near Bogalusa, LA | 1.5 | 1.55 | 1.81 | 1.5 | -0.05 |
| 02492700 | Pearl River at I-10 near Slidell, LA | 1.17 | 1.16 | 1.27 | 1.22 | 0.07 |

## 变化最大的 15 个站

| 站号 | 站名 | 类型 | 全局模型 | 分组模型 | 分组 − 全局 |
|---|---|---|---|---|---|
| 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 10.33 | 6.38 | -3.95 |
| 08114100 | Brazos Rv nr Sugar Land, TX | urban creek (Houston) | 9.68 | 5.94 | -3.74 |
| 08194200 | San Casimiro Ck nr Freer, TX | river / canal | 5.72 | 8.91 | 3.19 |
| 08114000 | Brazos Rv at Richmond, TX | urban creek (Houston) | 6.85 | 3.97 | -2.88 |
| 08188590 | North end of GBRA Calhoun Canal nr Long Mott,TX | river / canal | 32.32 | 35.05 | 2.74 |
| 073816525 | Mouth of Atchafalaya River at Atchafalaya Bay | river / canal | 7.3 | 10.0 | 2.7 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 25.21 | 27.66 | 2.45 |
| 08042558 | W Fk Double Bayou at Eagle Ferry Rd nr Anahuac, TX | urban creek (Houston) | 6.16 | 8.32 | 2.16 |
| 08098450 | Brazos Rv at FM 485 near Hearne, TX | river / canal | 9.62 | 7.51 | -2.11 |
| 02481660 | JOURDAN RIVER NR BAY ST LOUIS, MS | river / canal | 9.35 | 11.44 | 2.1 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 22.74 | 24.76 | 2.02 |
| 08074250 | Brickhouse Gully at Costa Rica St, Houston, TX | urban creek (Houston) | 17.39 | 19.27 | 1.88 |
| 301141089320300 | EAST PEARL RIVER AT CSX RAILROAD NR CLAIBORNE, MS | river / canal | 5.34 | 7.17 | 1.84 |
| 08017044 | Calcasieu River at I-10 at Lake Charles, LA | river / canal | 5.47 | 7.29 | 1.81 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 33.22 | 34.93 | 1.7 |
