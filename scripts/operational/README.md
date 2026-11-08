# operational

`forecast.py` — 业务化推断骨架。每个周期：从 USGS NWIS IV 和 NOAA CO-OPS 实时接口取各站最近 72 小时水位，
喂给训练好的 global LSTM，输出全部站未来 1–6 小时的水位（米，站点各自的基准面）。

```bash
cd scripts/operational
python forecast.py --model /data/ywan245/subdomainLSTM/runs/v2_e40 --out /data/ywan245/subdomainLSTM/operational
# 指定起报时刻（UTC 整点）
python forecast.py --model ... --cycle 2026-11-08T12
```

输出 `<out>/<cycle>/forecast.csv`、`manifest.json`、`raw/`（原始 API 返回）。
模型目录需要 `best.pt` 和训练时的 `stations.csv`（站点顺序 = embedding 编号）。
CRMS、USACE 站没有实时源，输出里标 `no_realtime_source`。
