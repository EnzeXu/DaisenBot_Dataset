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
# then enter, for example:
# Enter benchmark name(s) (e.g., kmeans or kmeans,svm): kmeans, fir
```

## What the script does
- Builds each benchmark (`go build` inside each benchmark dir).
- Runs the benchmark executable.
- Detects produced `akita_sim_*.sqlite3` files, renames/moves them into `./data/` using names like `D<id><type><index>.sqlite3`.
- Writes per-trace JSON records into `./data_record/` and a per-benchmark summary file `data_record/<benchmark>.json`.

## Files created
- `data/` — generated `.sqlite3` trace files.
- `data_record/` — per-trace `.json` records and `data_record/<benchmark>.json` summaries.
