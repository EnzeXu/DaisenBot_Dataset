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
[fir base] base size -length 32: 0.59 MB (< 10 MB)
[fir base] base size -length 64: 0.73 MB (< 10 MB)
[fir base] base size -length 128: 1.33 MB (< 10 MB)
[fir base] base size -length 256: 2.58 MB (< 10 MB)
[fir base] base size -length 512: 5.05 MB (< 10 MB)
[fir base] base size -length 1024: 10.01 MB (>= 10 MB)
[fir base] base size is set to -length 1024
[fir base] D0200000.sqlite3 (10.01 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024
[fir special] D0210001.sqlite3 (10.01 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024 -use-unified-memory
[fir special] D0210002.sqlite3 (10.98 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024 -gpus 1,2,3
[fir special] D0210003.sqlite3 (10.12 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024 -unified-gpus 1,2
[fir special] D0210004.sqlite3 (10.01 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024 -wf-sampling
[fir special] D0210005.sqlite3 (10.01 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024 -sampled-granulary 2048
[fir special] D0210006.sqlite3 (10.01 MB): /your/path/to/mgpusim/amd/samples/fir/fir -timing -trace-vis -length 1024 -sampled-threshold 0.05
[fir] All done. Generated 7 trace files (including base). Data stored in ./data, records in ./data_record.
[kmeans build] building benchmark in ../mgpusim/amd/samples/kmeans
[kmeans base] base size -points 32: 18.79 MB (>= 10 MB)
[kmeans base] base size is set to -points 32
[kmeans base] D1100000.sqlite3 (18.79 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32
[kmeans normal] D1100001.sqlite3 (14.14 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -clusters 5 -features 32
[kmeans normal] D1100002.sqlite3 (28.23 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -clusters 5 -features 64
[kmeans normal] D1100003.sqlite3 (56.18 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -clusters 5 -features 128
[kmeans normal] D1100004.sqlite3 (23.03 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -clusters 10 -features 32
[kmeans normal] D1100005.sqlite3 (46.12 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -clusters 10 -features 64
[kmeans normal] D1100006.sqlite3 (92.17 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -clusters 10 -features 128
[kmeans special] D1110007.sqlite3 (14.14 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -use-unified-memory
[kmeans special] D1110008.sqlite3 (31.02 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -gpus 1,2,3
[kmeans special] D1110009.sqlite3 (19.09 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -unified-gpus 1,2
[kmeans special] D1110010.sqlite3 (18.79 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -wf-sampling
[kmeans special] D1110011.sqlite3 (14.14 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -sampled-granulary 2048
[kmeans special] D1110012.sqlite3 (14.14 MB): /your/path/to/mgpusim/amd/samples/kmeans/kmeans -timing -trace-vis -points 32 -sampled-threshold 0.05
[kmeans] All done. Generated 13 trace files (including base). Data stored in ./data, records in ./data_record.
```