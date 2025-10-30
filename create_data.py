import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from itertools import product
from pathlib import Path

# Fixed values per your request
MGPUSIM_COMMIT_SHA = "8ef2478f927933de2711ddea400927453079955c"
DATA_TASK_PREFIX = "D"   # always "D"

def load_profile(profile_path="data_config.json"):
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dirs(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def run_go_build(benchmark_dir):
    # print(f"[build] Running 'go build' in {benchmark_dir}")
    res = subprocess.run(["go", "build"], cwd=benchmark_dir)
    if res.returncode != 0:
        raise RuntimeError(f"go build failed in {benchmark_dir} (return code {res.returncode})")
    # print("[build] build finished successfully")

def run_benchmark_and_get_size(cmd_list, timeout=None):
    """
    Run the benchmark command (list form). Wait for completion.
    Returns (succeeded_bool, size_in_MB, produced_trace_path_or_none).
    """
    # The benchmark may produce substantial stdout/stderr. Redirect both to
    # `logs.txt` in append mode so the console isn't flooded. The benchmark is
    # expected to produce an `akita_sim_*.sqlite3` file in the cwd; we'll detect
    # and move it after the run.
    # Note: We'll run the process and allow it to create the file (may take long).
    with open("logs.txt", "ab") as logf:
        proc = subprocess.run(cmd_list, stdout=logf, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        # command failed
        print(f"[warning] command exited with code {proc.returncode}: {' '.join(cmd_list)}")
        return False, 0, None

    # After running the process, look for akita_sim_*.sqlite3
    # choose the most recently modified one if multiple match.
    cwd = Path(os.getcwd())
    matches = list(cwd.glob("akita_sim_*.sqlite3"))
    if not matches:
        print("[warning] No akita_sim_*.sqlite3 file found after running command.")
        return True, 0, None

    # pick newest by modification time
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    src = matches[0]

    size_bytes = src.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)
    return True, size_mb, src


def format_data_filename(bench_id: str, type_id: str, index: int) -> str:
    # D {id} {index:04d} -> e.g., D03 0000 -> D030000.sqlite3
    return f"{DATA_TASK_PREFIX}{bench_id}{type_id}{index:04d}.sqlite3"

def format_data_record_filename(bench_id: str, index: int) -> str:
    return f"{DATA_TASK_PREFIX}{bench_id}{index:04d}.json"

def build_base_benchmark_cmd(exe_path, base_args, trace_arg_flag, trace_file_path, size_arg_name, size_value):
    """
    Return a list of tokens for subprocess.run.
    exe_path should be path to binary (string).
    base_args is a string like "-timing -trace-vis" (we will split it).
    trace_arg_flag e.g. "-trace-vis-db-file"
    trace_file_path e.g. "./data/D030000.sqlite3"
    size_arg_name e.g. "-points"
    """
    cmd = [exe_path]
    if base_args:
        cmd += shlex.split(base_args)
    # size arg
    cmd.append(size_arg_name)
    cmd.append(str(size_value))
    return cmd

def write_data_record(data_record_dir, record):
    # record["id"] like "D030001"
    out_path = Path(data_record_dir) / (record["id"] + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return out_path

def strip_leading_dot_slash(s: str):
    # if s.startswith("./"):
    #     return s[2:]
    return s

def process_benchmark(profile, bench_name):
    # load config for this benchmark
    if bench_name not in profile.get("benchmark_config", {}):
        print(f"Benchmark '{bench_name}' not found in profile['benchmark_config']. Exiting.")
        return 1

    bconf = profile["benchmark_config"][bench_name]
    bench_id = bconf["id"]              # e.g. "03"
    base_script = bconf["base_script"]  # e.g. "./kmeans"
    size_arg_name = bconf["size_arg"]   # e.g. "-points"
    size_arg_start = int(bconf.get("size_arg_start", 0))
    normal_arg_list = bconf.get("normal_arg_list", [])
    normal_arg_values = bconf.get("normal_arg_values", {})
    special_arg_list = bconf.get("special_arg_list", [])

    data_save_path = profile.get("data_save_path", "./data")
    data_record_save_path = profile.get("data_record_save_path", "./data_record")
    benchmark_path = profile.get("benchmark_path", ".")
    benchmark_base_arg = profile.get("benchmark_base_arg", "")
    benchmark_trace_filename_arg = profile.get("benchmark_trace_filename_arg", "-trace-vis-db-file")
    benchmark_trace_min_size_MB = int(profile.get("benchmark_trace_min_size_MB", 0))

    # create data and data_record directories if not exists (step 2)
    ensure_dirs(data_save_path, data_record_save_path)

    # keep track of produced trace filenames and record filenames for summary
    produced_traces = []
    produced_records = []

    # 0. remove files starting with akita_sim* in cwd
    cwd = os.getcwd()
    # remove leftover akita_sim* files in cwd before running
    cwd_path = Path(cwd)
    akita_matches = list(cwd_path.glob("akita_sim*"))
    if akita_matches:
        removed = 0
        for p in akita_matches:
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass
        if removed > 0:
            print(f"[{bench_name} clean] remove {removed} files starting by \"akita_sim\"")

    # 1. build the benchmark (go build in benchmark_path/bench_name)
    benchmark_dir = os.path.join(benchmark_path, bench_name)
    if not os.path.isdir(benchmark_dir):
        print(f"[{bench_name} build] benchmark directory does not exist: {benchmark_dir}")
        return 1
    try:
        print(f"[{bench_name} build] building benchmark in {benchmark_dir}")
        run_go_build(benchmark_dir)
    except Exception as e:
        print("Build failed:", e)
        return 1

    # determine path to executable: prefer benchmark_dir + base_script (strip leading ./)
    exe_name = strip_leading_dot_slash(base_script)
    exe_path = os.path.join(benchmark_dir, exe_name)
    if not os.path.exists(exe_path):
        # maybe go build put executable with package name; as fallback try benchmark_dir/exe_name without join
        print(f"[warning] executable not found at {exe_path}. Trying benchmark_dir/{exe_name}")
        exe_path = os.path.join(benchmark_dir, exe_name)
    if not os.path.exists(exe_path):
        print(f"[warning] executable still not found at {exe_path}. Attempting to run using './{exe_name}' from cwd.")
        exe_path = os.path.join(benchmark_dir, exe_name)
    # use absolute path to executable so that working dir of the process is current cwd
    exe_path = os.path.abspath(exe_path)

    # We'll run commands from the script's cwd so that data_save_path and data_record_save_path (which are "./data" etc) match expectations
    cwd = os.getcwd()

    # 3. iterate the prob size to find the good prob size (start from size_arg_start)
    cur_size = int(size_arg_start)
    idx_counter = 0  # start index for data generation. base is index 0.
    base_found = False
    base_size = None

    while True:
        # construct trace file name and command
        trace_filename = format_data_filename(bench_id, "0", idx_counter)  # e.g., D030000.sqlite3
        trace_file_rel = os.path.join(data_save_path, trace_filename)  # e.g., ./data/D030000.sqlite3
        cmd_list = build_base_benchmark_cmd(
            exe_path=exe_path,
            base_args=benchmark_base_arg,
            trace_arg_flag=benchmark_trace_filename_arg,
            trace_file_path=trace_file_rel,
            size_arg_name=size_arg_name,
            size_value=cur_size
        )
        # run the command; stdout/stderr redirected to logs.txt inside run_benchmark_and_get_size
        succeeded, size_mb, produced_path = run_benchmark_and_get_size(cmd_list)
        if not succeeded:
            # If command failed in a way that produced no trace, stop and bail out
            print(f"[{bench_name} base] command failed for size {cur_size}. Aborting base-size search.")
            return 1

        # size_mb might be 0 if file missing; handle that as "< min" and delete if exists
        if produced_path is None:
            print(f"[{bench_name} base] base size {size_arg_name} {cur_size}: 0 MB (< {benchmark_trace_min_size_MB} MB)")
            # increase size
            cur_size = cur_size * 2
            continue

        # print status exactly as requested:
        if size_mb < benchmark_trace_min_size_MB:
            print(f"[{bench_name} base] base size {size_arg_name} {cur_size}: {size_mb} MB (< {benchmark_trace_min_size_MB} MB)")
            # delete the produced akita file since it's too small
            try:
                produced_path.unlink()
            except Exception:
                pass
            # double size and repeat
            cur_size = cur_size * 2
            continue
        else:
            # found base size
            print(f"[{bench_name} base] base size {size_arg_name} {cur_size}: {size_mb} MB (>= {benchmark_trace_min_size_MB} MB)")
            print(f"[{bench_name} base] base size is set to {size_arg_name} {cur_size}")
            # move/rename produced file to data_save_path/trace_filename
            dest_path = Path(data_save_path) / trace_filename
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                # use shutil.move for cross-filesystem safety
                shutil.move(str(produced_path), str(dest_path))
            except Exception as e:
                print(f"[warning] failed to move produced trace {produced_path} to {dest_path}: {e}")
                # if move fails, leave produced_path as-is and use its path for size
                dest_path = produced_path

            # Keep this trace (index 0) as the base file
            base_found = True
            base_size = cur_size
            # Print the summary command line as requested:
            cmd_line_str = " ".join(shlex.quote(tok) for tok in cmd_list)
            print(f"[{bench_name} base] {dest_path.name} ({f'{size_mb} MB' if size_mb is not None else '0 MB'}): {cmd_line_str}")
            # write the data record for the base trace
            record = {
                "id": format_data_filename(bench_id, "0", idx_counter).replace(".sqlite3", ""),
                "benchmark": bench_name,
                "benchmark_cmd": " ".join([strip_leading_dot_slash(os.path.basename(exe_path))] + shlex.split(benchmark_base_arg) + [
                    f"{size_arg_name} {base_size}"
                ]),
                "trace_file": dest_path.name,
                "mgpusim_commit_SHA": MGPUSIM_COMMIT_SHA,
                "size": f"{size_mb} MB" if size_mb is not None else "0 MB",
                "comment": "base trace"
            }
            out = write_data_record(data_record_save_path, record)
            produced_records.append(out.name)
            produced_traces.append(Path(dest_path).name)
            break

    # After base found, next indices for generated traces start at 1
    idx_counter = 1

    # 4. generate normal traces -- combinations from normal_arg_list & normal_arg_values
    # Prepare list of args and values in the same order as normal_arg_list
    normal_keys = []
    normal_values_lists = []
    for arg in normal_arg_list:
        key = arg.lstrip("-")
        normal_keys.append(arg)  # store the full arg name like "-clusters"
        vals = normal_arg_values.get(key, [])
        normal_values_lists.append(vals)

    # generate all combinations
    normal_combinations = list(product(*normal_values_lists)) if normal_values_lists else []

    for combo in normal_combinations:
        # build command tokens
        trace_filename = format_data_filename(bench_id, "0", idx_counter)
        trace_file_rel = os.path.join(data_save_path, trace_filename)
        cmd = [exe_path]
        if benchmark_base_arg:
            cmd += shlex.split(benchmark_base_arg)
        # fixed base size
        cmd.append(size_arg_name)
        cmd.append(str(base_size))
        # append normal args corresponding to this combo
        for arg_name, arg_val in zip(normal_arg_list, combo):
            cmd.append(arg_name)
            cmd.append(str(arg_val))

        # run
        succeeded, size_mb, produced_path = run_benchmark_and_get_size(cmd)
        if not succeeded:
            print(f"[{bench_name} normal] Warning: normal trace generation failed for index {idx_counter}. Continuing.")
        # print the full command as requested
        cmd_line_str = " ".join(shlex.quote(tok) for tok in cmd)
        print(f"[{bench_name} normal] {trace_filename} ({f'{size_mb} MB' if size_mb is not None else '0 MB'}): {cmd_line_str}")

        # write data_record JSON
        record = {
            "id": format_data_filename(bench_id, "0", idx_counter).replace(".sqlite3", ""),  # like "D030001"
            "benchmark": bench_name,
            "benchmark_cmd": " ".join([strip_leading_dot_slash(os.path.basename(exe_path))] + shlex.split(benchmark_base_arg) + [
                f"{arg} {val}" for arg, val in zip(normal_arg_list, combo)
            ]),
            "trace_file": trace_filename,
            "mgpusim_commit_SHA": MGPUSIM_COMMIT_SHA,
            "size": f"{size_mb} MB" if size_mb is not None else "0 MB",
            "comment": ""
        }
        # move/rename the produced akita file to the expected location
        if produced_path is not None:
            dest = Path(data_save_path) / trace_filename
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(produced_path), str(dest))
            except Exception as e:
                print(f"[warning] failed to move produced trace {produced_path} to {dest}: {e}")

        out = write_data_record(data_record_save_path, record)
        produced_records.append(out.name)
        produced_traces.append(trace_filename)
        idx_counter += 1

    # 5. special traces: each time try exactly 1 arg from special_arg_list (append it to base cmd)
    for special in special_arg_list:
        # special might include spaces (e.g., "-unified-gpus 1,2,3"), so split with shlex
        special_tokens = shlex.split(special)
        trace_filename = format_data_filename(bench_id, "1", idx_counter)
        trace_file_rel = os.path.join(data_save_path, trace_filename)
        cmd = [exe_path]
        if benchmark_base_arg:
            cmd += shlex.split(benchmark_base_arg)
        cmd.append(size_arg_name)
        cmd.append(str(base_size))
        # append special tokens
        cmd += special_tokens

        succeeded, size_mb, produced_path = run_benchmark_and_get_size(cmd)
        if not succeeded:
            print(f"[{bench_name} special] Warning: special trace generation failed for special '{special}'. Continuing.")
        cmd_line_str = " ".join(shlex.quote(tok) for tok in cmd)
        print(f"[{bench_name} special] {trace_filename} ({f'{size_mb} MB' if size_mb is not None else '0 MB'}): {cmd_line_str}")

        # Reconstruct a human-friendly benchmark_cmd:
        benchmark_cmd_parts = [strip_leading_dot_slash(os.path.basename(exe_path))]
        if benchmark_base_arg:
            benchmark_cmd_parts += shlex.split(benchmark_base_arg)
        # include size and special tokens
        benchmark_cmd_parts += [size_arg_name, str(base_size)]
        benchmark_cmd_parts += special_tokens
        benchmark_cmd_str = " ".join(benchmark_cmd_parts)

        record = {
            "id": format_data_filename(bench_id, "1", idx_counter).replace(".sqlite3", ""),
            "benchmark": bench_name,
            "benchmark_cmd": benchmark_cmd_str,
            "trace_file": trace_filename,
            "mgpusim_commit_SHA": MGPUSIM_COMMIT_SHA,
            "size": f"{size_mb} MB" if size_mb is not None else "0 MB",
            "comment": ""
        }
        # move produced akita file to expected destination
        if produced_path is not None:
            dest = Path(data_save_path) / trace_filename
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(produced_path), str(dest))
            except Exception as e:
                print(f"[warning] failed to move produced trace {produced_path} to {dest}: {e}")

        out = write_data_record(data_record_save_path, record)
        produced_records.append(out.name)
        produced_traces.append(trace_filename)
        idx_counter += 1

    print(f"[{bench_name}] All done. Generated {idx_counter} trace files (including base). Data stored in {data_save_path}, records in {data_record_save_path}.")

    # write per-benchmark summary file data_record/{benchmark}.json
    try:
        summary = {
            "benchmark": bench_name,
            "data": produced_traces,
            "data_record": produced_records
        }
        summary_path = Path(data_record_save_path) / f"{bench_name}.json"
        with open(summary_path, "w", encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2)
    except Exception as e:
        print(f"[warning] failed to write summary {bench_name}.json: {e}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate traces for one or more benchmarks")
    parser.add_argument("--benchmarks", nargs="+", help="List of benchmark names to run (e.g., --benchmarks fir kmeans)")
    args = parser.parse_args()

    try:
        profile = load_profile("data_config.json")
    except FileNotFoundError:
        print("data_config.json not found in current working directory.")
        sys.exit(1)

    if args.benchmarks:
        benchmarks = args.benchmarks
    else:
        s = input("Enter benchmark name(s) (e.g., \"fir\" or \"fir,kmeans\" or \"fir kmeans\"): ").strip()
        benchmarks = [x for x in re.split(r'[\s,]+', s) if x]
    print(f"receive {len(benchmarks)} benchmarks to process: {', '.join(benchmarks)}")

    if not benchmarks:
        print("No benchmarks specified. Exiting.")
        sys.exit(1)

    # validate benchmarks exist
    missing = [b for b in benchmarks if b not in profile.get("benchmark_config", {})]
    if missing:
        print(f"Benchmark(s) not found in profile['benchmark_config']: {', '.join(missing)}")
        sys.exit(1)

    rc = 0
    for bench in benchmarks:
        rc |= process_benchmark(profile, bench)

    sys.exit(rc)