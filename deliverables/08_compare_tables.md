# 08 流量改配同河上游站之后的对比（表格）

测试集 2024-01 → 2025-12（起报 ≤ 2025-12-31T17），847 个站在三组里都有 ≥ 720 个样本。RMSE 单位 cm，各站中位数。

## 全部站

| 提前 | +风（无流量） | +风+流量（HUC8 配站） | +风+流量（同河上游配站） |
|---|---|---|---|
| 1 h | 1.26 | 1.23 | 1.23 |
| 3 h | 2.8 | 2.78 | 2.78 |
| 6 h | 4.53 | 4.56 | 4.54 |

## 改配的 49 个站（same_river_upstream）

| 提前 | +风（无流量） | +风+流量（HUC8 配站） | +风+流量（同河上游配站） |
|---|---|---|---|
| 1 h | 1.46 | 1.37 | 1.25 |
| 3 h | 4.5 | 4.43 | 4.18 |
| 6 h | 8.13 | 8.17 | 8.07 |

6 h：比 HUC8 配站 变好 ≥ 0.5 cm 的站 4，变差 ≥ 0.5 cm 的站 0；比不加流量 变好 12，变差 0。

## 改配的站按河流

| chain | 站数 | +风（无流量） | +风+流量（HUC8 配站） | +风+流量（同河上游配站） | 变好 ≥0.5 cm | 变差 ≥0.5 cm |
|---|---|---|---|---|---|---|
| Amite / Comite | 7 | 11.73 | 11.5 | 11.72 | 0 | 0 |
| Atchafalaya | 1 | 8.13 | 8.17 | 8.34 | 0 | 0 |
| Brazos | 9 | 9.09 | 8.68 | 7.92 | 1 | 0 |
| Buffalo Bayou | 4 | 27.17 | 26.43 | 26.14 | 2 | 0 |
| Colorado | 4 | 5.74 | 5.61 | 5.26 | 0 | 0 |
| Guadalupe | 2 | 7.65 | 7.63 | 7.69 | 0 | 0 |
| Mississippi | 1 | 4.44 | 4.4 | 4.36 | 0 | 0 |
| Neches | 4 | 5.26 | 5.28 | 5.28 | 0 | 0 |
| Pearl | 7 | 3.05 | 3.21 | 2.96 | 0 | 0 |
| Sabine | 3 | 8.03 | 8.0 | 8.07 | 0 | 0 |
| Trinity | 4 | 4.91 | 4.85 | 4.62 | 1 | 0 |
| W Fk San Jacinto | 3 | 11.92 | 11.93 | 11.85 | 0 | 0 |

## 没改配的站（应当基本不变）

| 提前 | +风（无流量） | +风+流量（HUC8 配站） | +风+流量（同河上游配站） |
|---|---|---|---|
| 1 h | 1.24 | 1.22 | 1.23 |
| 3 h | 2.77 | 2.75 | 2.75 |
| 6 h | 4.38 | 4.4 | 4.38 |

## 按 domain（全部站）

| domains | 站数 | +风（无流量） | +风+流量（HUC8 配站） | +风+流量（同河上游配站） | 变好 ≥0.5 cm | 变差 ≥0.5 cm |
|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 3.92 | 3.96 | 3.94 | 0 | 2 |
| Galveston100m | 152 | 10.26 | 9.69 | 9.78 | 6 | 3 |
| Texas100m | 79 | 5.36 | 5.33 | 5.29 | 0 | 1 |

## 按站点类型（全部站）

| type | 站数 | +风（无流量） | +风+流量（HUC8 配站） | +风+流量（同河上游配站） | 变好 ≥0.5 cm | 变差 ≥0.5 cm |
|---|---|---|---|---|---|---|
| tide gauge | 51 | 4.34 | 4.44 | 4.38 | 0 | 0 |
| marsh | 413 | 3.04 | 3.09 | 3.03 | 0 | 0 |
| estuary / tidal channel | 44 | 6.17 | 6.18 | 6.28 | 0 | 0 |
| lake | 12 | 2.73 | 2.76 | 2.73 | 0 | 1 |
| river / canal | 256 | 5.66 | 5.75 | 5.81 | 0 | 3 |
| urban creek (Houston) | 71 | 13.03 | 12.92 | 12.91 | 6 | 2 |

## 改配的站逐站（按 6 h 变化排序，负 = 变好）

| 站号 | 站名 | 河流 | 新配的上游站 | +风 | HUC8 配站 | 同河上游 | 新 − 旧 |
|---|---|---|---|---|---|---|---|
| 08114000 | Brazos Rv at Richmond, TX | Brazos | Brazos Rv at San Felipe, TX | 9.09 | 8.68 | 6.85 | -1.82 |
| 08073700 | Buffalo Bayou at Piney Point, TX | Buffalo Bayou | Buffalo Bayou at W Belt Dr, Houston, TX | 33.01 | 32.35 | 31.71 | -0.64 |
| 08073600 | Buffalo Bayou at W Belt Dr, Houston, TX | Buffalo Bayou | Buffalo Bayou nr Addicks, TX | 32.22 | 31.58 | 31.02 | -0.56 |
| 08067000 | Trinity Rv at Liberty, TX | Trinity | Trinity Rv at Romayor, TX | 4.46 | 4.41 | 3.85 | -0.56 |
| 08161000 | Colorado Rv at Columbus, TX | Colorado | Colorado Rv abv La Grange, TX | 5.17 | 5.06 | 4.59 | -0.48 |
| 08162000 | Colorado Rv at Wharton, TX | Colorado | Colorado Rv at Columbus, TX | 5.06 | 4.93 | 4.46 | -0.47 |
| 02492100 | Pearl River Navigation Canal Lock and Dam No. 2 | Pearl | Pearl River near Bogalusa, LA | 16.39 | 16.21 | 15.74 | -0.47 |
| 07378050 | Comite R. at Greenwell Spg Rd near Baton Rouge, LA | Amite / Comite | Comite River near Comite, LA | 21.23 | 21.08 | 20.7 | -0.38 |
| 08111850 | Brazos Rv at San Felipe, TX | Brazos | Brazos Rv nr Hempstead, TX | 3.68 | 4.05 | 3.7 | -0.35 |
| 08162500 | Colorado Rv nr Bay City, TX | Colorado | Colorado Rv at Wharton, TX | 12.89 | 13.22 | 12.89 | -0.32 |
| 07378000 | Comite River near Comite, LA | Amite / Comite | Comite River near Olive Branch, LA | 19.27 | 19.25 | 18.93 | -0.31 |
| 08041000 | Neches Rv at Evadale, TX | Neches | Neches Rv nr Town Bluff, TX | 2.21 | 2.51 | 2.22 | -0.29 |
| 08068090 | W Fk San Jacinto Rv abv Lk Houston nr Porter, TX | W Fk San Jacinto | W Fk San Jacinto Rv nr Conroe, TX | 11.47 | 11.27 | 11.01 | -0.26 |
| 02489500 | Pearl River near Bogalusa, LA | Pearl | PEARL RIVER NR COLUMBIA, MS | 3.05 | 3.21 | 2.96 | -0.26 |
| 08162501 | Colorado Rv nr Wadsworth, TX | Colorado | Colorado Rv nr Bay City, TX | 6.3 | 6.15 | 5.94 | -0.21 |
| 08030500 | Sabine Rv nr Ruliff, TX | Sabine | Sabine Rv nr Bon Wier, TX | 3.54 | 3.57 | 3.37 | -0.2 |
| 08067650 | W Fk San Jacinto Rv bl Lk Conroe nr Conroe, TX | W Fk San Jacinto | W Fk San Jacinto Rv nr Huntsville, TX | 17.85 | 17.57 | 17.39 | -0.18 |
| 08110200 | Brazos Rv at Washington, TX | Brazos | Brazos Rv at SH 21 nr Bryan, TX | 8.06 | 8.07 | 7.92 | -0.16 |
| 02492600 | Pearl River at Pearl River, LA | Pearl | Pearl River near Bogalusa, LA | 1.95 | 2.13 | 1.98 | -0.14 |
| 07377870 | Comite River at Hooper Road near Baton Rouge, LA | Amite / Comite | Comite River near Olive Branch, LA | 13.04 | 13.02 | 12.89 | -0.13 |
| 07377750 | Comite River near Zachary, LA | Amite / Comite | Comite River near Olive Branch, LA | 11.31 | 10.98 | 10.85 | -0.13 |
| 08111500 | Brazos Rv nr Hempstead, TX | Brazos | Brazos Rv at Washington, TX | 5.8 | 6.13 | 6.03 | -0.1 |
| 08068000 | W Fk San Jacinto Rv nr Conroe, TX | W Fk San Jacinto | W Fk San Jacinto Rv bl Lk Conroe nr Conroe, TX | 11.92 | 11.93 | 11.85 | -0.09 |
| 08108700 | Brazos Rv at SH 21 nr Bryan, TX | Brazos | Brazos Rv nr Highbank, TX | 9.62 | 9.15 | 9.07 | -0.08 |
| 02490193 | Pearl River at Pools Bluff near Bogalusa, LA | Pearl | Pearl River near Bogalusa, LA | 1.61 | 1.62 | 1.55 | -0.07 |
| 07377000 | Amite River near Darlington, LA | Amite / Comite | Amite River at Magnolia, LA | 6.25 | 6.22 | 6.17 | -0.05 |
| 08033500 | Neches Rv nr Rockland, TX | Neches | Neches Rv nr Diboll, TX | 5.33 | 5.32 | 5.27 | -0.05 |
| 07374525 | Mississippi River at Belle Chasse, LA | Mississippi | Mississippi River at Baton Rouge, LA | 4.44 | 4.4 | 4.36 | -0.04 |
| 08073500 | Buffalo Bayou nr Addicks, TX | Buffalo Bayou | Barker Res nr Addicks, TX | 22.12 | 21.29 | 21.25 | -0.03 |
| 02492511 | East Pearl River at I-59 near Nicholson, MS | Pearl | Pearl River near Bogalusa, LA | 3.96 | 3.92 | 3.9 | -0.03 |
| 08098450 | Brazos Rv at FM 485 near Hearne, TX | Brazos | Brazos Rv nr Highbank, TX | 9.39 | 9.63 | 9.62 | -0.01 |
| 07380120 | Amite River at Port Vincent, LA | Amite / Comite | Amite River near Denham Springs, LA | 2.76 | 2.78 | 2.8 | 0.02 |
| 08176500 | Guadalupe Rv at Victoria, TX | Guadalupe | Guadalupe Rv at Cuero, TX | 9.26 | 9.28 | 9.32 | 0.03 |
| 08041780 | Neches Rv Saltwater Barrier at Beaumont, TX | Neches | Neches Rv at Evadale, TX | 5.19 | 5.24 | 5.28 | 0.05 |
| 08079120 | Old Brazos Rv nr Freeport, TX | Brazos | Brazos Rv nr West Columbia, TX | 6.06 | 5.89 | 5.95 | 0.06 |
| 08028500 | Sabine Rv nr Bon Wier, TX | Sabine | Sabine Rv nr Burkeville, TX | 8.03 | 8.0 | 8.07 | 0.07 |
| 08175800 | Guadalupe Rv at Cuero, TX | Guadalupe | Guadalupe Rv at Gonzales, TX | 6.03 | 5.98 | 6.07 | 0.09 |
| 02490200 | Pearl River Navigation Canal Lock and Dam No. 3 | Pearl | Pearl River near Bogalusa, LA | 13.28 | 13.08 | 13.17 | 0.09 |
| 08066000 | Trinity Rv at Riverside, TX | Trinity | Trinity Rv nr Crockett, TX | 2.67 | 2.64 | 2.75 | 0.11 |
| 08066500 | Trinity Rv at Romayor, TX | Trinity | Trinity Rv nr Goodrich, TX | 5.35 | 5.28 | 5.4 | 0.11 |
| 07381490 | Atchafalaya River at Simmesport, LA | Atchafalaya | Old River Outflow Channel below Hydropower Channel | 8.13 | 8.17 | 8.34 | 0.17 |
| 08066250 | Trinity Rv nr Goodrich, TX | Trinity | Trinity Rv nr Crockett, TX | 10.61 | 10.43 | 10.63 | 0.21 |
| 07378500 | Amite River near Denham Springs, LA | Amite / Comite | Amite River near Darlington, LA | 11.73 | 11.5 | 11.72 | 0.23 |
| 08026000 | Sabine Rv nr Burkeville, TX | Sabine | Sabine Rv at Toledo Bd Res nr Burkeville, TX | 20.08 | 19.64 | 19.88 | 0.25 |
| 08040600 | Neches Rv nr Town Bluff, TX | Neches | Neches Rv nr Rockland, TX | 10.37 | 10.18 | 10.48 | 0.3 |
| 02492519 | Pearl River Navigation Canal Lock and Dam No. 1 | Pearl | Pearl River near Bogalusa, LA | 2.11 | 2.15 | 2.47 | 0.31 |
| 08073100 | Langham Ck at Addicks Res Outflow nr Addicks, TX | Buffalo Bayou | Addicks Res nr Addicks, TX | 18.82 | 18.36 | 18.71 | 0.35 |
| 08114100 | Brazos Rv nr Sugar Land, TX | Brazos | Brazos Rv at Richmond, TX | 11.39 | 9.31 | 9.68 | 0.37 |
| 08116650 | Brazos Rv nr Rosharon, TX | Brazos | Brazos Rv nr Sugar Land, TX | 12.79 | 9.94 | 10.33 | 0.39 |

## 没改配却变化最大的 10 个站（训练随机性的量级）

| 站号 | 站名 | 类型 | HUC8 配站 | 同河上游 | 新 − 旧 |
|---|---|---|---|---|---|
| 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 22.16 | 21.39 | -0.77 |
| 08186500 | Ecleto Ck nr Runge, TX | river / canal | 9.57 | 10.29 | 0.72 |
| 2951190901217 | L. Cataouatche at Whiskey Canal S of Waggaman, LA | lake | 3.54 | 4.15 | 0.61 |
| 08109310 | Thompsons Ck at SH 47 nr Bryan, TX | river / canal | 17.37 | 17.97 | 0.6 |
| 08068900 | Cypress Ck at Stuebner-Airline Rd nr Westfield, TX | urban creek (Houston) | 25.75 | 25.21 | -0.54 |
| 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 32.69 | 33.22 | 0.53 |
| 08015500 | Calcasieu River near Kinder, LA | river / canal | 5.75 | 6.27 | 0.53 |
| 08115000 | Big Ck nr Needville, TX | urban creek (Houston) | 14.27 | 14.8 | 0.53 |
| 08074540 | Little Whiteoak Bayou at Trimble St, Houston, TX | urban creek (Houston) | 22.24 | 22.74 | 0.5 |
| 02492343 | EAST HOBOLOCHITTO CREEK NR CAESAR, MS | river / canal | 6.02 | 6.49 | 0.46 |
