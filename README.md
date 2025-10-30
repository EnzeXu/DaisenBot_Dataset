# DaisenBot Dataset

Usage and Setup Instructions of create_data.py

## Prerequisites
- Install Go and Python 3, and ensure `go` and `python3` are in your PATH

## Prepare mgpusim
Clone mgpusim and checkout the required commit:
```bash
git clone https://github.com/sarchlab/mgpusim.git ../mgpusim
cd ../mgpusim
git checkout 8ef2478f927933de2711ddea400927453079955c
```
If `mgpusim` is not next to this repo, edit `benchmark_path` in `data_config.json` to point to the samples directory (e.g. `/full/path/to/mgpusim/amd/samples/`).

## Run create_data.py
From the repository root (where `create_data.py` and `data_config.json` live):

Non-interactive (one or more benchmarks):
```bash
python3 create_data.py --benchmarks kmeans fir
```

Interactive prompt (multiple names allowed, space or comma separated):
```bash
python3 create_data.py
```

## What the script does
- Builds each benchmark (`go build` inside each benchmark dir).
- Runs the benchmark executable.
- Detects produced `akita_sim_*.sqlite3` files, renames/moves them into `./data/` using names like `D<id><type><index>.sqlite3`.
- Writes per-trace JSON records into `./data_record/` and a per-benchmark summary file `data_record/<benchmark>.json`.

## Files created
- `data/` — generated `.sqlite3` trace files.
- `data_record/` — per-trace `.json` records and `data_record/<benchmark>.json` summaries.

## Example run (command + sample output)
Run:
```bash
python create_data.py --benchmarks fir kmeans
```

Sample output:
```text
receive 2 benchmarks to process: fir, kmeans
[fir build] building benchmark in ../mgpusim/amd/samples/fir
[fir base] base size -length 32: 0.59 MB (< 200 MB)
[fir base] base size -length 64: 0.73 MB (< 200 MB)
[fir base] base size -length 128: 1.33 MB (< 200 MB)
[fir base] base size -length 256: 2.58 MB (< 200 MB)
[fir base] base size -length 512: 5.05 MB (< 200 MB)
[fir base] base size -length 1024: 10.01 MB (< 200 MB)
[fir base] base size -length 2048: 20.13 MB (< 200 MB)
[fir base] base size -length 4096: 40.51 MB (< 200 MB)
[fir base] base size -length 8192: 81.52 MB (< 200 MB)
[fir base] base size -length 16384: 165.15 MB (< 200 MB)
[fir base] base size -length 32768: 331.21 MB (>= 200 MB)
[fir base] base size is set to -length 32768
[fir base] D0200000.sqlite3 (331.21 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768
[fir special] D0210001.sqlite3 (331.21 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768 -use-unified-memory
[fir special] D0210002.sqlite3 (333.84 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768 -gpus 1,2,3
[fir special] D0210003.sqlite3 (336.07 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768 -unified-gpus 1,2
[fir special] D0210004.sqlite3 (331.21 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768 -wf-sampling
[fir special] D0210005.sqlite3 (331.21 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768 -sampled-granulary 2048
[fir special] D0210006.sqlite3 (331.21 MB): /path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 32768 -sampled-threshold 0.05
[fir] All done. Generated 7 trace files (including base). Data stored in ./data, records in ./data_record.
[kmeans build] building benchmark in ../mgpusim/amd/samples/kmeans
[kmeans base] base size -points 32: 18.79 MB (< 200 MB)
[kmeans base] base size -points 64: 27.72 MB (< 200 MB)
[kmeans base] base size -points 128: 80.42 MB (< 200 MB)
[kmeans base] base size -points 256: 166.89 MB (< 200 MB)
[kmeans base] base size -points 512: 336.83 MB (>= 200 MB)
[kmeans base] base size is set to -points 512
[kmeans base] D1100000.sqlite3 (336.83 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512
[kmeans normal] D1100001.sqlite3 (336.83 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -clusters 5 -features 32
[kmeans normal] D1100002.sqlite3 (667.82 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -clusters 5 -features 64
[kmeans normal] D1100003.sqlite3 (1369.66 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -clusters 5 -features 128
[kmeans normal] D1100004.sqlite3 (586.03 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -clusters 10 -features 32
[kmeans normal] D1100005.sqlite3 (1172.42 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -clusters 10 -features 64
[kmeans normal] D1100006.sqlite3 (2380.27 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -clusters 10 -features 128
[kmeans special] D1110007.sqlite3 (336.83 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -use-unified-memory
[kmeans special] D1110008.sqlite3 (399.55 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -gpus 1,2,3
[kmeans special] D1110009.sqlite3 (351.4 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -unified-gpus 1,2
[kmeans special] D1110010.sqlite3 (336.83 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -wf-sampling
[kmeans special] D1110011.sqlite3 (336.83 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -sampled-granulary 2048
[kmeans special] D1110012.sqlite3 (336.83 MB): /path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 512 -sampled-threshold 0.05
[kmeans] All done. Generated 13 trace files (including base). Data stored in ./data, records in ./data_record.
```