# operational

`forecast.py` — 业务化推断。每个周期：从 USGS NWIS IV 和 NOAA CO-OPS 实时接口取各站最近 72 小时水位，
模型需要的话再取风（HRRR）、降雨（MRMS + HRRR）和上游流量（USGS 00060），喂给训练好的 global LSTM，
输出全部站未来 1–6 小时的水位（米，站点各自的基准面）。

所有输出都写在 `--out` 指定的目录下（默认是自己名下的 `/data/ywan245/subdomainLSTM/operational`），不接组里的业务系统。

```bash
cd scripts/operational
# 风 + 流量模型（当前）
python forecast.py --model /data/ywan245/subdomainLSTM/runs/v6_wind_q --out /data/ywan245/subdomainLSTM/operational
# 6 h-change scaling + gap filling + HRRR rainfall（实际运行的一版，输出放在单独的目录）
python forecast.py --model /data/ywan245/subdomainLSTM/runs/v11_fc1_t45 --out /data/ywan245/subdomainLSTM/operational_rain
# 只用水位的模型
python forecast.py --model /data/ywan245/subdomainLSTM/runs/v2_e40 --out /data/ywan245/subdomainLSTM/operational_v2
# 指定起报时刻（UTC 整点）
python forecast.py --model ... --cycle 2026-11-08T17
```

脚本从 `best.pt` 里的训练参数自动判断要不要风、未来风、流量、降雨、缺测填充方式、是否按 6 小时变化量缩放，不用再传开关。
模型用了脚本不支持的训练开关（7 天 / 30 天摘要、上下游参考水位站、站点子集、未来 6 小时用实测雨）时，脚本直接报错停下，不会悄悄喂错输入。

## 模型目录要有的文件

| 文件 | 用途 | 来源 |
|---|---|---|
| `best.pt` | 权重 + 训练参数 | train.py |
| `stations.csv` | 训练时的站点顺序（= embedding 编号）、mean/std | dataset 目录 |
| `wind_coverage.csv` | 每站训练期有风的比例；为 0 的站（离岸、AORC 无格点）不出预报，标 `no_wind_in_training` | build_extras.py |
| `q_norm.csv` | 每个流量控制站训练期 log1p(Q) 的均值 / 标准差，实时流量按同样方式标准化 | build_extras.py |

已有的 dataset 补这两个文件：`python scripts/train/build_extras.py --src dataset_v2 --out dataset_v3 --meta-only`。

## 风：HRRR（`hrrr_wind.py`）

训练用的是 AORC 1 km 再分析，业务上没有实时的 AORC，用 NOAA HRRR（3 km、逐小时）代替：

- 来源 `s3://noaa-hrrr-bdp-pds`（AWS 公开、免账号，约 1 小时延迟），只按 `.idx` 的字节范围下载 10 m 的 UGRD / VGRD 两条 GRIB 消息（各约 1 MB），用 pygrib 解。
- 过去 72 小时：每小时的分析场（f00）；缺哪个小时就退到最近一个周期的短时预报（最多 f06）。
- 未来 6 小时：起报时已经发布的最新 HRRR 周期的 f01–f06；周期还没出来就退到上一个周期（f02–f07）。
- 每站取最近格点（`<out>/wind/hrrr_cells.csv`，格点距离中位 1.2 km、最大 2.1 km），每个有效小时存一个 `<out>/wind/hrrr/<时刻>_f<FF>.npz`。
  第一次跑要下 78 个小时（约 15 秒），之后每个周期只下新的 7 个小时。
- 没选系统驱动 ROMS 用的大气强迫（原来是 NAM；NWS 在 2026-11-03 用 RRFS 取代了 NAM，组里的系统 11-04 起改取 RRFS 13 km、3 小时一场，仍放在 `NAM` 分支名下）：3 小时一场、NOMADS 只留两天，不够拼 72 小时逐时。HRRR 和 AORC 都是数值模式产品，分辨率也接近。
- HRRR 目前照常发布，NWS 还没有公布它的退役日期，但 RRFS 最终会取代它。到时风和未来 6 小时降雨都要换成 RRFS 3 km，其中降雨那一段需要用 RRFS 的预报重新训练。

## 降雨（`mrms_rain.py`、`hrrr_rain.py`）

降雨模型训练时：过去 72 小时用 AORC 再分析的 15 km 方框平均；未来 6 小时用 HRRR 预报的 45 km 方框 6 小时总量（起报前 1 小时发布的周期）。
AORC 没有实时产品，业务上这样替代（依据和对比数字见 `deliverables/20_operational_rain.md`）：

- **过去 72 小时：MRMS**（雷达 + 雨量计，1 km，逐小时）。来源 `s3://noaa-mrms-pds`，`MultiSensor_QPE_01H_Pass1`，整点后约 16 分钟发布；
  缺这个产品的小时退到 `RadarOnly_QPE_01H`；两个都没有的小时用 HRRR 上一个周期的 1 小时预报补。每站取周围 15 × 15 个格点的平均。
  每个小时缓存一个 `<out>/rain/mrms/<时刻>_b15.npz`，第一次下 72 个小时约 10–20 秒，之后每个周期只下 1 个。
- **未来 6 小时：HRRR**。起报前 1 小时发布的周期的第 2–7 小时预报（和训练一致），取 45 km 方框平均后求 6 小时总量；
  这个周期还没发布就依次退到更早的周期（最多再早 5 个）。只下 `APCP` 一条 GRIB 消息（约 0.2 MB）。
- `--past-rain hrrr` 可以让过去 72 小时也全部用 HRRR（不建议，见对比数字）。

`forecast.csv` 里多三列：`rain_valid_frac`、`rain_past72h_mm`、`rain_next6h_mm`。过去降雨有效率 < 70% 或未来 6 小时拿不到时该站标 `insufficient_rain`。

## 缺测填充和按 6 小时变化量缩放

模型训练时用了 `--fill ffill` 的话，窗口里缺测的小时填最近一次有效水位（为此多取窗口前 24 小时的数据）；缺测标志位照常给。
用了 `--delta-norm` / `--delta-feat` 的话，每站的缩放系数存在 `best.pt` 里，脚本直接读，不需要额外文件。

## 整条流程的回算检验（`hindcast_check.py`）

`forecast.py --cycle <过去的时刻>` 用的就是实时系统当时能拿到的输入。`hindcast_check.py` 把这些预报和数据集里的观测比，
同时在完全相同的（站，起报时刻）上算同一个模型用训练输入（AORC）时的误差，两者之差就是「训练输入换成实时输入」的代价。

## 流量

`config/station_discharge_map.csv` 给每个站配一个上游控制站；脚本一次取所有控制站最近 72 小时的 00060（cfs → m³/s，
负值截 0，log1p，按 `q_norm.csv` 标准化）。控制站没数据的站，流量输入全标"无"，和训练时缺数据一样处理。

## 输出

`<out>/<cycle>/forecast.csv`、`manifest.json`（取数情况、每个小时用的 HRRR 周期和预报时效、流量控制站情况）、`raw/`（原始 API 返回）。

状态列：`ok` / `no_realtime_source`（CRMS、USACE）/ `no_data_returned` / `insufficient_input`（72 小时有效率 < 70%）/ `stale`（最后一个观测早于起报 3 小时）/
`insufficient_wind` / `no_wind_in_training` / `insufficient_rain`。

2026-11-08 17Z 实跑：v3_wind_q 418 站 `ok`，USGS 372/403、NOAA 52/54 有数，风过去 72 小时 71 个分析场 + 1 个 f01，流量 53/55 个控制站有数；取数 + 推断 48 秒。
和只用水位的模型同周期对比：6 小时预报相差中位 0.9 cm、90% 分位 3.3 cm、最大 19 cm（Texas 海湾站，当天有风）。
