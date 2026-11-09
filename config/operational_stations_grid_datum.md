# operational_stations_grid_datum.csv 说明

业务系统能用的站（训练集里的 USGS 403 + NOAA 54 = 457 站）在三个 100 m ROMS 子网格里的格点编号，以及垂直基准的换算。一行一个（站，网格）组合，595 行，435 个站落在至少一个网格里（22 个在三个网格之外，主要是东德州和密西西比州内陆）。生成脚本 `scripts/data/station_grid_map.py`（2026-11-09）。

## 网格

| domain 列的值 | 网格文件（QBD，只读） | 大小 eta × xi | 范围 |
|---|---|---|---|
| Louisiana100m | `/project/zlei2/LSU_operational_system_qbd/grid/Louisiana100m/Louisiana100m_roms_grid.nc`（→ `.sub`，业务在用） | 1837 × 5510 | 94.11W–88.39W, 28.74N–30.40N |
| Louisiana100m_full | 同目录 `.full` | 2680 × 5510 | 北到 31.14N |
| Texas100m | `grid/Texas100m/Texas100m_roms_grid.nc` | 3592 × 2517 | 97.75W–95.23W, 25.85N–29.04N |
| Galveston100m | `grid/Galveston100m/Galveston100m_roms_grid.nc`（→ `.full`） | 2690 × 2540 | 96.71W–94.04W, 28.74N–31.16N |

格点坐标、掩膜和水深用 NCO 抽出来放在 `config/gridmap/<domain>_grid_small.nc`（不进 git，sv7 和 QBD `/work/yixuan97/subdomainLSTM/gridmap/` 各一份）。

## 列

| 列 | 含义 |
|---|---|
| `i_xi`, `j_eta` | 离站点最近的 rho 格点，**0 起算**（Python / netCDF 下标；ROMS Fortran 下标 +1）。i 沿 xi，j 沿 eta |
| `cell_is_wet` | 该格点 `mask_rho` 是否为水（1 = 水） |
| `dist_cell_km` | 站点到该格点中心的距离 |
| `h_cell_m` | 该格点的模式水深 `h`（米，向下为正；负值是干地高程，用于干湿） |
| `i_xi_wet`, `j_eta_wet`, `dist_wet_km`, `h_wet_m`, `cell_lon`, `cell_lat` | 最近的**水格点**。站点本身就在水格点时和上面相同 |
| `station_datum` | 站点数据的基准：`NAVD88`、`MSL`（NOAA 11 站没有 NAVD88 基准）、`gauge_datum(NGVD29;alt_ft=…)`（USGS 水尺零点高程，NGVD29，英尺）或未知 |
| `to_navd88_add_m` | **把该站的水位值换成 NAVD88 要加的数**：NAVD88 站 0；MSL 站 = CO-OPS 的 MSL − NAVD88；水尺站 = 水尺零点的 NAVD88 高程（VDatum 把 NGVD29 转 NAVD88）。空值 = 基准未知，换不了 |
| `grid_vertical_reference_assumed` | 网格水深的垂直基准。Texas100m 网格文件写明水深来自 NCEI 1/9 和 1/3 弧秒 DEM，这些 DEM 以 NAVD88 为基准；Louisiana、Galveston 的网格文件没写来源，**按同样假设处理，需要组里确认** |
| `station_to_grid_ref_add_m` | 站点值换到网格基准要加的数。在"网格基准 = NAVD88"的假设下等于 `to_navd88_add_m` |
| `obs_mean_2019_2023_navd88_m` | 该站 2019–2023 年观测水位的平均值（已换成 NAVD88）。这是站点处**当前的平均水面高出 NAVD88 零点多少**，等价于当地现在的平均海面相对 NAVD88 |
| `obs_mean_2012_2016_navd88_m` | 同上，2012–2016 年 |
| `obs_frac_2019_2023` | 2019–2023 有观测的时间比例，低于 0.5 的均值已置空 |
| `coops_msl_minus_navd88_m` | NOAA 官方基准表里 MSL 减 NAVD88（米）。注意 CO-OPS 的 MSL 多数站仍是 1983–2001 潮汐基准期（`coops_epoch` 列），比现在的平均水面低 0.1–0.15 m |
| `coops_MSL_m_stnd`, `coops_NAVD88_m_stnd`, `coops_MLLW_m_stnd` | NOAA 基准表原值（相对 STND，米） |
| `gauge_zero_ngvd29_ft`, `gauge_zero_navd88_m` | USGS 水尺零点高程：原始 NGVD29 英尺，和 VDatum 换算的 NAVD88 米 |

## 怎么理解"datum offset"

模型里每个点的水位 zeta 是相对于网格的零面；站点水位是相对于站点自己的基准。要把两者对上，要走两步：

1. **站点基准 → 网格基准**（几何的、固定的）：`station_to_grid_ref_add_m`。假设网格基准是 NAVD88，那 369 个 NAVD88 的 USGS 站和 43 个 NAVD88 的 NOAA 站加 0，11 个 MSL 的 NOAA 站加 CO-OPS 的 MSL − NAVD88，20 个水尺站加水尺零点高程。
2. **模式自己的平均水面 ≠ 网格零面**（动态的）：即使水深是 NAVD88 基准，模式跑出来的平均 zeta 也不是 0，而是当地平均海面相对 NAVD88 的高度再加上模式自身偏差。用同一段时间的平均值去掉这一项：`offset_obs_minus_model_m = 观测(NAVD88) − 模式 zeta`，见下一节。

两个数都在这张表里，拼起来就是每个站的总偏移。

## 第二部分：模式平均水面（2026-11-09 补上）

从组里的 ROMS 预报存档（QBD `results/<domain>/<周期>/NAM/ocean_his_*.nc`，只读）抽了每个站最近水格点的 zeta：每个周期取前 24 小时，Louisiana 51 个周期（2026-07 起）、Texas 68 个（2026-04 起）、Galveston 51 个，脚本 `scripts/data/roms_zeta_at_stations.py`（在 QBD 用 `/work/yixuan97/conda_envs/cfml` 的 python 跑）和 `scripts/data/model_offset.py`。只对站点本身在水格点、或离最近水格点不到 1 km 的站算（52 行：NOAA 31、USGS 21）；河流站在 ROMS 里是陆地，这一项为空。

| 列 | 含义 |
|---|---|
| `n_hours_matched` | 观测和模式都有值的小时数 |
| `cell_dry_frac`, `model_bad_frac` | 格点干出（zeta ≤ −h + 0.1）和模式值不合理（|zeta| > 5 m）的小时比例，这些小时已剔除。Texas100m 的 2026-04-15 周期是发散的（zeta 100 多米），已剔除 |
| `model_zeta_mean_m` | 同期模式 zeta 平均 |
| `obs_mean_matched_navd88_m` | 同期观测平均（NAVD88） |
| `offset_obs_minus_model_m` | **观测减模式的中位数**，就是偏移的第二部分；`_mean_m` 是均值 |
| `corr_obs_model` | 两者逐小时的相关系数，低于 0.3 说明格点或模式有问题，偏移不可信 |
| `rmse_model_after_offset_cm` | 去掉偏移后模式对观测的 RMSE，供参考 |

结果：三个域的模式平均 zeta 都在 −0.1 到 −0.2 m，观测平均在 +0.3 到 +0.55 m（NAVD88），所以 **观测 − 模式 ≈ +0.3 到 +0.55 m**，Louisiana 中位 0.37、Galveston 0.34、Texas 0.47；潮位站相关系数 0.6–0.85。也就是说不管网格零面名义上是什么，把模式 zeta 换到 NAVD88 要加 0.3 到 0.5 m，各站的具体值在表里。异常：Packery Channel（8775792）模式值 1.3 m、相关 0.1，格点落在结构物上，不要用；Sargent（8772985）在 Galveston 网格里相关 0，用 Texas 网格那一行；New Canal、Bayou Perot 相关偏低。

把两部分合起来：**站点值 + `to_navd88_add_m` = NAVD88 值；模式 zeta + `offset_obs_minus_model_m` ≈ 同一站的 NAVD88 值。**

## 注意

- 大部分 USGS 河流站在 ROMS 网格里是**陆地格点**（100 m 网格不解析小河道）：Galveston 域 138 个 USGS 站没有一个落在水格点上，最近水格点中位 47 km。这些站属于 WRF-Hydro 河网而不是 ROMS，表里仍给出 ROMS 的最近格点和最近水格点，但距离大的不应该用 ROMS 的 zeta 去比。给 WRF-Hydro 河网配格点是另一张表（没做）。
- NOAA 潮位站和海湾里的 USGS 站绝大多数落在水格点上，距离 20–50 m。
- Louisiana 业务网格（`.sub`）北界 30.40N，Baton Rouge、Pontchartrain 北岸等站只在 `_full` 网格里。
- 13 个 USGS 站基准未知（`gauge_datum(nan)`），1 个（Old Brazos nr Freeport 08079120）VDatum 换算失败，这些行的换算列为空。
- CRMS 站不在这张表里（业务系统不用）。
