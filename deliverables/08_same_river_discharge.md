# 08 流量改配同河上游站之后的结果（v4 对 v3）

07 的第一步：把河流链上的 49 个站的流量输入从"同一 HUC8 里汇水面积最大的站"改成"同一条河紧挨着的上游站或大坝放水站"，其余 961 个站配法不变，其他一切（网络、划分、40 轮、测试截止 2025-12-31T17）和 v3_wind_q 相同。QBD 作业 1170403，run `v4_wind_q`。表格：`08_compare_tables.md`；逐站：`08_compare_per_station.csv`。

## 结论

| | +风（无流量） | +风+流量，HUC8 配站（v3） | +风+流量，同河上游配站（v4） |
|---|---|---|---|
| 全部 847 站 6 h RMSE 中位数 (cm) | 4.53 | 4.56 | 4.54 |
| 改配的 49 站 1 h | 1.46 | 1.37 | **1.25** |
| 改配的 49 站 3 h | 4.50 | 4.43 | **4.18** |
| 改配的 49 站 6 h | 8.13 | 8.17 | **8.07** |

- **改配有效但幅度小**：改配的 49 个站 1 h 和 3 h 的中位误差降了 9% 和 6%，6 h 降 1%；误差平方和降 2%。49 个站里 6 h 变好 0.5 cm 以上的 4 个，变差的 0 个；和不加流量比，变好 12 个、变差 0 个。没改配的站 6 h 变化中位 0.05 cm、90% 分位 0.19 cm，是训练随机性的量级，所以上面这些差异大部分是真的。
- **见效的是大河中游站**：Brazos at Richmond 8.7 → 6.9 cm（逐小时全评 7.7 → 7.1；2024-07 Beryl 月 27 → 25 cm，风造成的假涨水尖峰还在，上游 San Felipe 的流量只压回去一点，其余月份普遍降 0.3–1 cm），Trinity at Liberty 4.4 → 3.9，Colorado at Columbus / Wharton 5.1 → 4.6 / 4.9 → 4.5，Buffalo Bayou W Belt / Piney Point 各降 0.6。
- **大坝正下游的站没有变好**：Burkeville（Toledo Bend）19.6 → 19.9，Goodrich（Livingston）10.4 → 10.6，Town Bluff 10.2 → 10.5。原因和 07 判断的一样：放水量的变化是调度决定，不是上游来水决定的。Burkeville 配的 Toledo Bend 出流站离它只有一小时，和它自己的水位是同一个信号；Goodrich 配的 Crockett 在湖上游 100 多公里，经过水库的调蓄后和放水没有关系。要预报这几个站只能接放水计划（NWS 预报或 CWMS 放水预报）。
- **Amite / Comite 的小溪没有变好**（11.5 → 11.7）：上游站到它只有几小时，涨水同时发生，流量不比水位早。这批站只有降雨能补。
- 全部站的中位数几乎不动（4.56 → 4.54），因为改的只有 49 个站。总的来看这一步该做、代价小，但不是能让总体误差明显下降的那一步。

![](08_compare_bars.png)

## 按河流（改配的站，6 h RMSE 中位数，cm）

| 河流 | 站数 | +风 | HUC8 配站 | 同河上游 |
|---|---|---|---|---|
| Brazos | 9 | 9.09 | 8.68 | **7.92** |
| Colorado | 4 | 5.74 | 5.61 | **5.26** |
| Trinity | 4 | 4.91 | 4.85 | **4.62** |
| Buffalo Bayou | 4 | 27.17 | 26.43 | **26.14** |
| Pearl | 7 | 3.05 | 3.21 | 2.96 |
| W Fk San Jacinto | 3 | 11.92 | 11.93 | 11.85 |
| Mississippi（Belle Chasse） | 1 | 4.44 | 4.40 | 4.36 |
| Neches | 4 | 5.26 | 5.28 | 5.28 |
| Sabine | 3 | 8.03 | 8.00 | 8.07 |
| Guadalupe | 2 | 7.65 | 7.63 | 7.69 |
| Amite / Comite | 7 | 11.73 | 11.50 | 11.72 |
| Atchafalaya（Simmesport） | 1 | 8.13 | 8.17 | 8.34 |

## 几个站的图（蓝 = HUC8 配站 v3，红 = 同河上游 v4）

- `08_station_08114000.png` Brazos at Richmond：改善最大的站，上游 San Felipe 的流量；逐月看是每个月都略好，不是单一事件。
- `08_station_08162000.png` Colorado at Wharton：上游 Columbus。
- `08_station_08067000.png` Trinity at Liberty：上游 Romayor。
- `08_station_08073700.png` Buffalo Bayou at Piney Point：上游 W Belt；暴雨涨水还是报不到。
- `08_station_08026000.png` Sabine nr Burkeville：Toledo Bend 出流，没有变化——调峰放水预报不了。
- `08_station_08066250.png` Trinity nr Goodrich：Lake Livingston 下游，同样没有变化。

## 下一步

1. 业务模型换成 v4_wind_q（和 v3 持平或略好，配站物理上说得通）。`runs/v4_wind_q` 已含 `stations.csv`、`wind_coverage.csv`、`q_norm.csv`，业务脚本直接 `--model runs/v4_wind_q` 即可；新增的 34 个控制站走同一个 USGS 接口。
2. 大坝下游站要接放水计划才有用，07 第二步：NWS NWPS 预报（6 小时一个值，Burkeville、Goodrich、Evadale、Bay City 等 69 个站有）或 CWMS 放水预报（Addicks / Barker），作为未来输入。
3. Pearl 三个船闸和 GBRA 灌溉渠从统计里拿掉（07 建议 1）。
4. 剩下最大的一块误差（Houston、Baton Rouge、东 Texas 小溪的暴雨涨水）在当前输入下就是上限，是否加降雨要组里定。

## 文件

| 文件 | 内容 |
|---|---|
| `08_compare_tables.md` | 全部站 / 改配站 / 按河流 / 按 domain / 按类型 / 逐站 表格 |
| `08_compare_per_station.csv` | 847 站三组的 1 / 3 / 6 h RMSE、新旧配站、变化 |
| `08_compare_bars.png` | 改配的站按河流的 6 h RMSE |
| `08_station_*.png` / `08_station_compare.csv` | 六个站两组模型的逐小时预报和逐月 RMSE |

配站脚本 `scripts/data/remap_same_river.py`；改配清单在 `config/station_discharge_map.csv`（assignment = same_river_upstream）；新增控制站在 `config/discharge_gauges.csv`。训练记录 QBD 作业 1170403（40 轮，每轮 48 秒，最优验证轮 39）。
