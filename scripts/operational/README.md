# operational

`forecast.py` — 业务化推断。每个周期：从 USGS NWIS IV 和 NOAA CO-OPS 实时接口取各站最近 72 小时水位，
模型需要的话再取风（HRRR）和上游流量（USGS 00060），喂给训练好的 global LSTM，
输出全部站未来 1–6 小时的水位（米，站点各自的基准面）。

```bash
cd scripts/operational
# 风 + 流量模型（当前）
python forecast.py --model /data/ywan245/subdomainLSTM/runs/v3_wind_q --out /data/ywan245/subdomainLSTM/operational
# 只用水位的模型
python forecast.py --model /data/ywan245/subdomainLSTM/runs/v2_e40 --out /data/ywan245/subdomainLSTM/operational_v2
# 指定起报时刻（UTC 整点）
python forecast.py --model ... --cycle 2026-11-08T17
```

脚本从 `best.pt` 里的训练参数自动判断要不要风、未来风、流量，不用再传开关。

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
- 没选系统驱动 ROMS 用的 NAM，因为 NAM 只有 3 小时一场、NOMADS 只留两天，不够拼 72 小时逐时。HRRR 和 AORC 都是数值模式产品，分辨率也接近。

## 流量

`config/station_discharge_map.csv` 给每个站配一个上游控制站；脚本一次取所有控制站最近 72 小时的 00060（cfs → m³/s，
负值截 0，log1p，按 `q_norm.csv` 标准化）。控制站没数据的站，流量输入全标"无"，和训练时缺数据一样处理。

## 输出

`<out>/<cycle>/forecast.csv`、`manifest.json`（取数情况、每个小时用的 HRRR 周期和预报时效、流量控制站情况）、`raw/`（原始 API 返回）。

状态列：`ok` / `no_realtime_source`（CRMS、USACE）/ `no_data_returned` / `insufficient_input`（72 小时有效率 < 70%）/ `stale`（最后一个观测早于起报 3 小时）/
`insufficient_wind` / `no_wind_in_training`。

2026-11-08 17Z 实跑：v3_wind_q 418 站 `ok`，USGS 372/403、NOAA 52/54 有数，风过去 72 小时 71 个分析场 + 1 个 f01，流量 53/55 个控制站有数；取数 + 推断 48 秒。
和只用水位的模型同周期对比：6 小时预报相差中位 0.9 cm、90% 分位 3.3 cm、最大 19 cm（Texas 海湾站，当天有风）。
