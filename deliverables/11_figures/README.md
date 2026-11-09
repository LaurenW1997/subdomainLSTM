# 11 论文风格的图和幻灯片

和 10 同一批 23 个代表站、同样三个窗口（飓风 / 涨水 / 平常），换成研究论文常用的画法：

- `station_<站号>.png` / `.pdf`：一站一张三联图。黑线观测；三条蓝线从浅到深是提前 1、3、6 小时的预报，每条是连续线（某小时的值 = 1、3 或 6 小时前发出的预报）；灰底是峰值前后 24 小时；RMSE 写在面板标题第二行。只画加风和上游流量的模型。
- `rmse_vs_lead.png`：RMSE 随提前量（1–6 h）变化，六类站各一条，实线加风和流量，虚线只用水位，阴影四分位范围。
- `rmse_box_by_type.png`：各类站逐站 6 h RMSE 的箱线图，有无风和流量对比。
- `rmse_map.png`：847 个站的 6 h RMSE 地图，方框是 23 个代表站。
- `forecast_figures.pptx`：28 页，白底黑字 Times New Roman，无标题页，每页一张图加一两句话。
- `data/<前缀>_<站号>.csv`：三联图用的数据（每小时观测和各提前量有效的预报），由 `scripts/report/extract_windows.py` 在 sv7 生成。

脚本：`scripts/report/paper_figs.py`（station / lead / box / map）、`scripts/report/slides_figures.py`。
