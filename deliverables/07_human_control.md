# 07 误差大的站里，哪些是人工调度造成的，调度数据能不能拿到

调查日期 2026-11-08。对象是 06 里 6 h RMSE ≥ 10 cm 的河流 / 溪流站加上所有大河站，逐个查上游有没有大坝、船闸、泵站、分水口，谁在管，调度数据有没有公开接口。逐站表：`07_controlled_stations.csv`。

## 结论

1. **误差最大的一批站（Houston 城市溪流、Baton Rouge 小溪、东 Texas 小溪）上游没有任何人工结构**，涨水就是本地暴雨。这部分占全部误差平方和的一半以上，和调度无关，流量和调度数据都补不了。
2. **确实有人工调度的站有 12 个左右**，分三类：
   - **水库放水**：Addicks / Barker（Buffalo Bayou 4 个站）、Lake Conroe（West Fork San Jacinto）、Toledo Bend（Sabine Burkeville、Bon Wier）、Lake Livingston（Trinity Goodrich、Romayor）、Town Bluff（Neches Town Bluff）、Old River Control（Atchafalaya Simmesport）。
   - **船闸**：Pearl River 航道 1、2、3 号船闸——闸室充放水造成 3–5 m 的阶跃，两年里 2 号闸 42 次、3 号闸 24 次，RMSE 16 / 13 cm 几乎全由这些阶跃贡献。
   - **抽水 / 引水**：GBRA Calhoun 灌溉渠（泵开关，两年 359 次 0.3 m 以上的跳变，单站误差全域最大 32 cm）、LCRA 在 Colorado Bay City 上游的灌溉引水、Bayou Des Cannes 的稻田抽水、Teche-Vermilion 泵站。
3. **数据能拿到的只有水库放水这一类**，而且比预想的好：
   - **USACE CWMS 公开接口**（`cwms-data.usace.army.mil`，免账号）有 Addicks / Barker **每个闸门的逐时流量**，还有 **未来 5 天的放水预报**（`Flow-Out ... National-CWMS-Forecast`，15 分钟一个值），今天实测可取。Town Bluff 有逐时流量；Old River 三个结构有逐日分流量；Pearl 三个船闸有闸室和上池 15 分钟水位。
   - **USGS 实时接口**里有 Toledo Bend 大坝总出流（08025360）、Addicks / Barker 闸门开度和出流（08073000、08072500）、Livingston / Conroe / Houston 三个湖的水位。
   - **NWS 河流预报**（`api.water.noaa.gov/nwps`）：域内 128 个点有当前预报，其中 69 个就是我们的站，Burkeville、Goodrich、Bay City、Richmond、Rosharon、Comite、Denham Springs、Simmesport、Baton Rouge 都在内，6 小时一个值、一天出 1–2 次。RFC 做预报时已经拿到了 TRA / SRA / USACE 的放水计划，所以这是**把调度信息间接拿进来最省事的一条路**。
   - 拿不到的：Lake Livingston 的闸门数据页要登录（TRA 只在 X 账号 @LivingstonDam 发文字）；Lake Conroe 放水量只在 SJRA 的仪表盘上，没有导出；Lake Houston 闸门没有任何公开数据；Toledo Bend 的发电计划只有文字（"Generator 1: No Run / Spillway Gates: Closed"）和电话录音；GBRA 泵站虽然有 USGS 站号 08188600 但近 30 天没有实时数据；LCRA 引水、稻田抽水、船闸操作记录都没有。

## 逐类说明

### 水库放水（可以接数据）

| 站 | 6 h RMSE (cm) | 两年里 0.3 m 以上的小时跳变 | 结构 / 管理方 | 过去 72 h 能用的信号 | 未来 6 h 能用的信号 |
|---|---|---|---|---|---|
| Buffalo Bayou nr Addicks（= Barker 出口）、Langham Ck（Addicks 出口）、W Belt、Piney Point | 21 / 18 / 32 / 32 | 230 / 140 / 301 / 269 | Addicks、Barker 大坝，USACE Galveston | 闸门开度 + 每闸流量（USGS、CWMS） | CWMS 放水预报（到 +5 天） |
| Sabine nr Burkeville、Bon Wier | 19.6 / 8.0 | 152 / — | Toledo Bend，SRA TX+LA，水电调峰 | 大坝总出流 08025360 | NWS BRVT2 / BWRT2 预报 |
| Trinity nr Goodrich、Romayor | 10.4 / 5.3 | 19 / — | Lake Livingston，TRA，12 扇弧门 | 湖水位 08066190；Goodrich 本身就是放水量 | NWS GRIT2 / RMYT2 预报 |
| W Fk San Jacinto bl Lk Conroe、abv Lk Houston | 17.6 / 11.3 | 81 / — | Lake Conroe，SJRA | 湖水位 08067600；下游站用 08067650 流量 | 无（SJRA 不导出） |
| Neches nr Town Bluff、Evadale | 10.2 / 2.5 | 14 / 0 | Town Bluff 坝，USACE Fort Worth，再调节 Sam Rayburn 发电放水 | CWMS TBFT2 流量 | NWS EVDT2 预报 |
| Atchafalaya Simmesport、Butte La Rose、Morgan City | 8.2 / 3.9 / 4.2 | — | Old River Control，USACE New Orleans | CWMS 逐日分流量 | NWS SMML1 / BLRL1 / MCGL1 预报（LMRFC 出 28 天） |

Burkeville 是最典型的调峰信号：两年里 152 次 0.3 m 以上的小时跳变，p99 小时变幅 0.28 m，而紧挨着的 Toledo Bend 大坝出流 USGS 有 15 分钟实时值。Addicks / Barker 那几个站有闸门预报，是唯一能拿到"未来放水"数值的地方。

### 船闸（数据有，但阶跃本身没法预报）

Pearl River 航道三个船闸 1995 年起只按预约过船。闸室水位 3–5 m 的阶跃是过船时充放水，没有操作日志。CWMS 有闸室和上池各一条 15 分钟水位，可以用上池水位把"河的信号"和"闸的信号"分开，但阶跃何时发生预报不了。建议：这三个站的评价单独列，或从误差统计里剔除。

### 抽水 / 引水（没有数据）

- GBRA Calhoun 灌溉渠（32 cm，全域最大）：这是人工渠道不是水体，泵的开关不公开。建议**从站点集里排除**，或者只当作参考站不进统计。
- Colorado Bay City（13 cm）：上游 Wharton 的流量能当输入，LCRA 的引水量只能在网页上看。
- Bayou Des Cannes（16 cm）、Vermilion Carencro（13 cm）：稻田抽水和 Teche-Vermilion 泵站，没有记录。

### 没有人工结构的站（误差最大的那批）

Whiteoak、Brays、Greens、Sims、Hunting Bayou 等 Houston 溪流，Ward Creek、Comite、Beaver Bayou、Hurricane Creek 等 Baton Rouge 溪流，Long King、Nelson、Kickapoo、Carters Creek 等东 Texas 小溪。Comite River 分洪渠还在修（2026-08 完成 67%，预计 2028 年底），目前不影响。这些站只有降雨能补。NWS 对 Comite、Denham Springs、Natalbany 有常规预报，对 Houston 溪流只在事件中出预报。

## 对下一步的建议

1. **先把站点分开评价**：Pearl 三个船闸、GBRA 灌溉渠这 4 个站和水体无关，建议从统计里拿掉（和 01 排除站一样写明原因）。拿掉后河流类的 6 h RMSE 中位数几乎不变，但 Texas100m 的最大误差站就消失了。
2. **接放水数据可以分两步**，都只改配站表和 `build_extras.py`：
   - 第一步（简单）：把流量控制站改成**同河上游的放水站**——Burkeville 配 08025360，West Fork San Jacinto 下游站配 08067650，Romayor 配 Goodrich，Evadale 配 Town Bluff，Buffalo Bayou 四站配 Addicks / Barker 出流（USGS 08073000 + 08072500）。这些都是 USGS 实时接口里已有的 00060，不用新写下载器。历史训练数据同样从 USGS 取。
   - 第二步（更有用，要新写一个下载器）：给水库下游站加**未来 6 小时的放水或水位预报**作为未来输入，和未来风一样喂给输出头。来源两个：CWMS 的 Flow-Out 预报（只有 Addicks / Barker），NWS NWPS 预报（69 个站有，6 小时一个值，插值到逐时）。NWS 预报有历史存档（IEM / NWS archive）可以做训练，但要先查存档的完整程度。
3. **大河站（Mississippi Baton Rouge、Belle Chasse、Atchafalaya）不需要调度数据**，误差 4–5 cm 已经很小；它们在 06 里被风弄差了 0.5–1.4 cm，更该做的是对这类站把风输入置零。

## 进度

- 2026-11-08：第一步已执行。`scripts/data/remap_same_river.py` 把 49 个河流链上的站改配成同一条河上游的站或放水站（Sabine、Neches、Trinity、West Fork San Jacinto、Buffalo Bayou、Brazos、Colorado、Guadalupe、Pearl、Amite / Comite、Atchafalaya），流量控制站从 58 个增加到 92 个（87 个有数据）。原来的 HUC8 规则给这些站配的几乎都是**下游**站（Burkeville → Ruliff、Goodrich → Romayor、Town Bluff → 盐水坝、Addicks 出口 → Piney Point），没有任何提前量，这也是 06 里"流量没用"的一个原因。Addicks / Barker 两个闸门出流站 USGS 只从 2023-11 开始有数据，训练期全空，自动被跳过（Buffalo Bayou 上游两站暂无流量输入）。新数据集 dataset_v4（= v3 换 q），QBD 作业 1170403，run `v4_wind_q`，和 v3_wind_q 同样 40 轮、同样的测试截止，结果出来后写进 08。

## 数据接口备忘

- USACE CWMS：`https://cwms-data.usace.army.mil/cwms-data/catalog/TIMESERIES?office=SWG&like=.*Addicks.*`，取数 `/timeseries?office=SWG&name=ADDT2-Gated_Total.Flow.Inst.1Hour.0.USGS-Rev&begin=...&end=...&unit=cms`，请求头 `accept: application/json;version=2`。办公室代码：SWG Galveston、SWF Fort Worth、MVN New Orleans、MVK Vicksburg。
- NWS NWPS：`https://api.water.noaa.gov/nwps/v1/gauges?bbox.xmin=-99.1&bbox.ymin=25.8&bbox.xmax=-88.3&bbox.ymax=31.2&srid=EPSG_4326` 列站，`/gauges/{lid}/stageflow` 取观测 + 预报（ft、kcfs）。
- USGS 水库站：08025360（Toledo Bend 出流）、08025350（Toledo Bend 水位）、08066190（Livingston 水位）、08067600（Conroe 水位）、08072000（Lake Houston 水位）、08073000 / 08072500（Addicks / Barker 闸门开度 45592、出流 00060、池位 62615）。
- SRA-LA 发电状态文字页：`srala-toledo.com`；TRA 闸门页 `lakedata.traweb.net`（需登录）；SJRA 仪表盘 `sanjacinto.onerain.com`（无导出）。
