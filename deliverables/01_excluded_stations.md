# 01 被筛掉的站点

普查到 **2018** 个水位站（普查表 2057 条记录，去掉同一 USACE 测站被两个办公室重复列出的条目，加上 7 个只在 CRMS 周报里出现、CIMS 站表里没有的站），进入训练集 **1010** 个，筛掉 **1008** 个。完整清单见 `01_excluded_stations.csv`（每站一行：来源、编号、名称、经纬度、所在 domain、在哪一步被筛掉、原因、补充说明）。

## 进入训练集的站

| 来源 | 站数 |
|---|---|
| CRMS | 552 |
| NOAA_COOPS | 54 |
| USACE_MVN | 1 |
| USGS | 403 |

## 筛掉的站：原因 × 来源

| 原因 | CRMS | NOAA_COOPS | TCOON | USACE_MVK | USACE_MVN | USACE_SWF | USACE_SWG | USGS | total |
|---|---|---|---|---|---|---|---|---|---|
| inactive | 208 | 0 | 105 | 14 | 194 | 46 | 24 | 47 | 638 |
| catalog_record_too_short | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 2 |
| no_data_downloaded | 46 | 0 | 0 | 3 | 6 | 0 | 0 | 0 | 55 |
| too_short | 115 | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 169 |
| too_short_in_train | 23 | 1 | 0 | 0 | 0 | 0 | 0 | 72 | 96 |
| flat | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| source_excluded | 0 | 0 | 0 | 0 | 0 | 0 | 47 | 0 | 47 |

## 原因说明

- **inactive**：普查时站已停测（目录里 record_end 早于 2026 年，或近 30 天没有数据）
- **catalog_record_too_short**：目录记录长度不足 3 年（站仍在测）
- **no_data_downloaded**：目录上有、但下载不到 2010 年以来的小时水位（USACE 只有日均序列、CRMS 周报里没有该站、USGS 没有 00065 要素等）
- **too_short**：下载到的有效小时数据不足 3 年
- **too_short_in_train**：训练期 2010–2022 内有效数据不足 1 年（多为 2022 年后新建站）
- **flat**：训练期标准差小于 2 cm，水位基本不动
- **source_excluded**：USACE SWG 整个来源不用：47 站中 37 站含填充值，10 个是水库库水位，23 个与 USGS 站是同一仪器

## 补充

- `inactive` 里的 TCOON 105 站：TCOON 项目 2014 年起停止资助，其中还在运行的仪器已并入 NOAA CO-OPS，所以这 105 个编号本身不算丢站。
- USACE MVN/MVK/SWF 的站绝大多数只有日均或已停测，所以几乎全部在 `inactive` / `no_data_downloaded`。
- CRMS 的 `too_short` / `too_short_in_train`：CRMS 站表有 937 站，周报里能取到小时数据的 690 站，其中不少是近几年新建或已改为间歇观测。
- 筛掉的站只是**不参与训练**，下载的数据都还在 sv7 上，后面随时可以放回来。