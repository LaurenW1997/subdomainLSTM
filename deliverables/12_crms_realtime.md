# 12 CRMS 站点能不能进业务系统

调查日期 2026-11-09，只读。结论先说：**绝大多数 CRMS 站物理上没有实时数据，不是接口问题**。

## 查到的事实

1. **CPRA 自己的站点数据库里，CRMS 水文站只有 10 个标为实时（real-time），9 个在用。** 来源是 CPRA 的 ArcGIS 服务 `prot_rest/real_time_stats`（字段 `mondata.REAL_TIME`）。全部约 400 个在用的 CRMS 水文站里，其余都是记录仪现场采集、巡站时下载，所以数据要几个月后才进数据库。10 个实时站：CRMS0061、0282、0411、0465（已停）、0568、0609、0615、0651、2418、5373，就是以前 USGS 替 CPRA 运行的 CRMS-RT 那批。
2. **CIMS 的数据下载工具里，数据库的最新数据也只到 2026 年 7 到 8 月**（项目列表里每个项目都标着数据截止日期，例如 AT-0002 到 07/16/2026，AT-0015 到 08/24/2026）。我们 11 月 7 日下的周导出同样截止在 6 到 8 月。也就是说即使是那 9 个实时站，CPRA 现在也没有公开的近实时发布渠道；以前走 USGS 接口的那条路 2026 年 7 到 8 月断了。
3. CIMS 网站没有 Web 服务或 API，只有网页表单下载（ASP.NET，按项目 / CRMS 站 / 站号和日期范围）、周导出、GIS 图层和"其他数据申请"。ArcGIS 服务只有站点位置和属性，没有观测值。
4. CPRA 2026 年 7 月的在用水文站表（Table B-4）里写明 CRMS0061、CRMS0282 等是"new station replaces USGS Real-time"，印证了接管关系。

## 对我们的影响

| | 站数 | 现状 |
|---|---|---|
| 训练集里的 CRMS 站 | 552 | 13 年历史数据完整，训练继续用 |
| 其中 CPRA 标为实时的 | 10（9 在用） | 目前没有公开近实时渠道，业务上也拿不到 |
| 业务脚本能出预报的 CRMS 站 | 0 | 全部标 `no_realtime_source` |

## 建议

1. **业务站点清单去掉 CRMS**（用户决定，2026-11-09）：业务系统只对 USGS 和 NOAA 的 457 个站（现有实时数据的 418 个左右）出预报。
2. **训练集是否保留 CRMS 另算。** 保留的理由：552 个湿地站让共享网络学到了湿地和浅水区的行为，对附近 NOAA、USGS 站也有帮助；去掉后要重训并重新评估。去掉的理由：模型更小更快，评价口径和业务范围一致。建议先保留，下一次重训时做一组"不含 CRMS"的对照再定。
3. **如果以后想把那 9 个实时站接进来**：要问 CPRA 要近实时数据访问（他们内部有，DCP 站的数据能到当周），或者等 CPRA 开通发布。这是组织层面的事，不是技术问题。
4. 评价报告（02 到 11）里 CRMS 站的结果仍然有效，是模型能力的证明，只是业务上用不上。

## 接口备忘

- CPRA 站点库：`https://cimsgeo.coastal.louisiana.gov/arcgis/rest/services/prot_rest/real_time_stats/MapServer/0/query?where=mondata.REAL_TIME=1 AND mondata.PROJ_TYPE='CRMS'&outFields=*&f=pjson`
- CIMS 下载表单：`https://cims.coastal.louisiana.gov/DataDownload/DataDownload.aspx?type=hydro_hourly`（ASP.NET 回传，可脚本化，但数据库本身滞后）
- 周导出：`https://cims.coastal.louisiana.gov/FullTableExports.aspx`（我们训练数据的来源）
