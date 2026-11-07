# subdomainLSTM

LSTM 6-hour water-level forecasts for every gauge inside the Louisiana100m,
Texas100m and Galveston100m domains of the LSU Gulf of Mexico Coastal Hazards
Forecast System (https://flood.lsu.edu/).

Independent of the operational repository maintained by zlei2; this project
only reads its published station products and grid files.

## Domains (ROMS `.full` grid extents)

| Domain        | lon              | lat            |
|---------------|------------------|----------------|
| Louisiana100m | -94.11 .. -88.39 | 28.74 .. 31.14 |
| Texas100m     | -99.03 .. -95.24 | 25.85 .. 29.13 |
| Galveston100m | -96.71 .. -94.04 | 28.74 .. 31.16 |

## Hosts

- QBD (`qbd.loni.org`): training (gpu2/gpu4 partitions), work dir under `/work/yixuan97/`
- sv7 (`comsrv7.cct.lsu.edu:2525`): operational data fetch, work dir under `/data/ywan245/`
- sv6 (`comsrv6.cct.lsu.edu:2525`): website publication (`/srv/ftp/`)

Never delete files on any of these hosts.
