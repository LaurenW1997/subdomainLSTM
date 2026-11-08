## 四组模型对比（测试集 2024-01 → 2025-12，提前 6 小时，各站 RMSE 的中位数，cm）

只统计四组里都有 ≥ 720 个 6 h 样本的 847 个站；四组用同一测试窗口、同一网络、同样训练 40 轮，只有输入不同。

| 分组 | 站数 | 只用水位 | +过去风 | +过去风+未来风 | +风+流量 | 6 h RMSE < 5 cm 的站 (只用水位 → +风+流量) | < 10 cm 的站 |
|---|---|---|---|---|---|---|---|
| **全部** | 847 | 5.15 | 4.78 | 4.53 | 4.56 | 48% → 55% | 85% → 88% |

### 按 domain

| 分组 | 站数 | 只用水位 | +过去风 | +过去风+未来风 | +风+流量 | 6 h RMSE < 5 cm 的站 (只用水位 → +风+流量) | < 10 cm 的站 |
|---|---|---|---|---|---|---|---|
| Louisiana100m | 633 | 4.48 | 4.07 | 3.92 | 3.96 | 57% → 66% | 93% → 96% |
| Galveston100m | 152 | 10.20 | 9.84 | 10.26 | 9.69 | 12% → 13% | 49% → 52% |
| Texas100m | 79 | 5.77 | 5.61 | 5.36 | 5.33 | 43% → 44% | 89% → 91% |

### 按站点类型

| 分组 | 站数 | 只用水位 | +过去风 | +过去风+未来风 | +风+流量 | 6 h RMSE < 5 cm 的站 (只用水位 → +风+流量) | < 10 cm 的站 |
|---|---|---|---|---|---|---|---|
| tide gauge | 51 | 5.05 | 4.43 | 4.34 | 4.44 | 49% → 59% | 98% → 100% |
| marsh | 413 | 3.69 | 3.30 | 3.04 | 3.09 | 64% → 75% | 97% → 100% |
| estuary / tidal channel | 44 | 7.46 | 6.67 | 6.17 | 6.18 | 16% → 30% | 80% → 89% |
| lake | 12 | 3.47 | 2.82 | 2.73 | 2.76 | 75% → 75% | 100% → 100% |
| river / canal | 256 | 5.90 | 5.85 | 5.66 | 5.75 | 39% → 40% | 79% → 80% |
| urban creek (Houston) | 71 | 13.53 | 13.14 | 13.03 | 12.92 | 7% → 7% | 30% → 31% |

### 按数据源

| 分组 | 站数 | 只用水位 | +过去风 | +过去风+未来风 | +风+流量 | 6 h RMSE < 5 cm 的站 (只用水位 → +风+流量) | < 10 cm 的站 |
|---|---|---|---|---|---|---|---|
| CRMS | 404 | 3.87 | 3.39 | 3.10 | 3.15 | 63% → 75% | 97% → 100% |
| NOAA_COOPS | 51 | 5.05 | 4.43 | 4.34 | 4.44 | 49% → 59% | 98% → 100% |
| USGS | 392 | 7.12 | 6.66 | 6.39 | 6.44 | 33% → 35% | 71% → 73% |

### 按流量配站方式（same_huc8 = 同一 HUC8 的上游控制站；manual_coastal_basin = 手工配的大河；none = 没配）

| 分组 | 站数 | 只用水位 | +过去风 | +过去风+未来风 | +风+流量 | 6 h RMSE < 5 cm 的站 (只用水位 → +风+流量) | < 10 cm 的站 |
|---|---|---|---|---|---|---|---|
| manual_coastal_basin | 352 | 4.32 | 3.87 | 3.59 | 3.56 | 58% → 71% | 97% → 99% |
| none | 40 | 4.61 | 4.25 | 4.09 | 4.07 | 60% → 62% | 98% → 98% |
| same_huc8 | 455 | 6.15 | 5.82 | 5.57 | 5.70 | 40% → 43% | 74% → 78% |

### 1 / 3 / 6 h 中位数（全部站）

| 模型 | 1 h | 3 h | 6 h |
|---|---|---|---|
| 只用水位 | 1.24 | 3.00 | 5.15 |
| +过去风 | 1.24 | 2.86 | 4.78 |
| +过去风+未来风 | 1.26 | 2.80 | 4.53 |
| +风+流量 | 1.23 | 2.78 | 4.56 |

### 逐站变化（6 h RMSE，cm）

| 对比 | 中位变化 | 变好 > 0.5 cm 的站 | 变差 > 0.5 cm 的站 | 变好的站占比 |
|---|---|---|---|---|
| 只用水位 → +风 | -0.34 | 361 | 25 | 83% |
| 只用水位 → +风+流量 | -0.35 | 373 | 15 | 85% |
| +风 → +风+流量（流量单独的贡献） | +0.01 | 18 | 4 | 46% |

### 加风后改善最大的站

| 站 | 名称 | 类型 | 只用水位 | +风 | +风+流量 |
|---|---|---|---|---|---|
| USGS 301912088583300 | MISSISSIPPI SOUND AT USGS GULFPORT LIGHT, MS | estuary / tidal channel | 10.0 | 6.6 | 6.4 |
| CRMS CRMS0517-H01 | CRMS0517-H01 (Teche/Vermilion) | marsh | 12.9 | 9.7 | 9.7 |
| USGS 08194200 | San Casimiro Ck nr Freer, TX | river / canal | 8.8 | 5.5 | 5.8 |
| CRMS TV21CR02-H01 | TV21CR02-H01 (Teche/Vermilion) | marsh | 9.7 | 6.7 | 6.7 |
| NOAA_COOPS 8747437 | Bay Waveland Yacht Club | tide gauge | 9.4 | 6.4 | 6.5 |
| NOAA_COOPS 8770971 | Rollover Pass | tide gauge | 9.9 | 6.9 | 7.0 |
| USGS 08074500 | Whiteoak Bayou at Houston, TX | urban creek (Houston) | 35.5 | 32.9 | 32.7 |
| CRMS CRMS0523-H01 | CRMS0523-H01 (Teche/Vermilion) | marsh | 10.6 | 7.6 | 7.8 |
| CRMS CRMS0341-H01 | CRMS0341-H01 (Terrebonne) | marsh | 8.7 | 6.1 | 6.0 |
| CRMS CRMS0527-H03 | CRMS0527-H03 (Teche/Vermilion) | marsh | 10.3 | 7.4 | 7.5 |
| CRMS CRMS0355-H01 | CRMS0355-H01 (Terrebonne) | marsh | 8.8 | 6.0 | 6.1 |
| CRMS CRMS0545-H01 | CRMS0545-H01 (Teche/Vermilion) | marsh | 11.3 | 8.6 | 8.6 |

### 加风后变差最大的站

| 站 | 名称 | 类型 | 只用水位 | +风 | +风+流量 |
|---|---|---|---|---|---|
| USGS 08114000 | Brazos Rv at Richmond, TX | urban creek (Houston) | 4.4 | 9.1 | 8.7 |
| USGS 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 6.5 | 12.8 | 9.9 |
| USGS 08114100 | Brazos Rv nr Sugar Land, TX | urban creek (Houston) | 6.0 | 11.4 | 9.3 |
| USGS 07374000 | Mississippi River at Baton Rouge, LA | river / canal | 3.7 | 5.1 | 4.7 |
| USGS 08067000 | Trinity Rv at Liberty, TX | urban creek (Houston) | 3.5 | 4.5 | 4.4 |
| USGS 08111850 | Brazos Rv at San Felipe, TX | river / canal | 3.1 | 3.7 | 4.0 |
| USGS 08111500 | Brazos Rv nr Hempstead, TX | river / canal | 5.3 | 5.8 | 6.1 |
| USGS 08117500 | San Bernard Rv nr Boling, TX | urban creek (Houston) | 11.0 | 11.6 | 11.8 |

### 流量贡献最大的站（+风 → +风+流量）

| 站 | 名称 | 类型 | 只用水位 | +风 | +风+流量 |
|---|---|---|---|---|---|
| USGS 08116650 | Brazos Rv nr Rosharon, TX | urban creek (Houston) | 6.5 | 12.8 | 9.9 |
| USGS 08075400 | Sims Bayou at Hiram Clarke St, Houston, TX | urban creek (Houston) | 22.2 | 24.5 | 22.2 |
| USGS 08114100 | Brazos Rv nr Sugar Land, TX | urban creek (Houston) | 6.0 | 11.4 | 9.3 |
| USGS 08116850 | Brazos Rv nr West Columbia, TX | estuary / tidal channel | 10.6 | 11.3 | 9.6 |
| USGS 08206910 | Choke Canyon Res OWC nr Three Rivers, TX | river / canal | 3.3 | 3.8 | 3.0 |
| USGS 08073500 | Buffalo Bayou nr Addicks, TX | urban creek (Houston) | 21.5 | 22.1 | 21.3 |
| USGS 08074000 | Buffalo Bayou at Houston, TX | estuary / tidal channel | 29.6 | 28.9 | 28.1 |
| USGS 08068740 | Cypress Ck at House-Hahl Rd nr Cypress, TX | urban creek (Houston) | 18.8 | 18.6 | 17.9 |
| USGS 08070200 | E Fk San Jacinto Rv nr New Caney, TX | urban creek (Houston) | 10.8 | 11.3 | 10.6 |
| USGS 08065820 | Larrison Ck at FM 1428 nr Midway, TX | river / canal | 17.8 | 18.0 | 17.3 |