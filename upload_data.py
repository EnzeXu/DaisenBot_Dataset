
import os
import io
import json
from typing import Optional, List, Tuple
from pathlib import Path
from tqdm import tqdm
from google_drive import get_service, upload_files

DRIVE_BASE = "My Drive/Workspace/Daisenbot_Dataset"

def upload(benchmark: str, service=None, overwrite: bool = True):
    """
    Read data_record/{benchmark}.json and upload:
      - every file listed in "data" -> into remote folder "data/"
      - every file listed in "data_record" -> into remote folder "data_record/"
    Returns the list of results from upload_files: (local_src, drive_target, success_bool, file_id_or_error)
    Raises FileNotFoundError if the local summary or any listed file is missing.
    """
    summary_path = Path("data_record") / f"{benchmark}.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary file not found: {summary_path}")

    with open(summary_path, "r", encoding="utf-8") as sf:
        summary = json.load(sf)

    data_list = summary.get("data", [])
    record_list = summary.get("data_record", [])

    pairs = []
    missing = []

    for name in data_list:
        src = Path("data") / name
        if not src.exists():
            missing.append(str(src))
        else:
            # upload into remote folder "data/"
            pairs.append((str(src), f"{DRIVE_BASE}/data/"))

    for name in record_list:
        src = Path("data_record") / name
        if not src.exists():
            missing.append(str(src))
        else:
            # upload into remote folder "data_record/"
            pairs.append((str(src), f"{DRIVE_BASE}/data_record/"))

    if missing:
        raise FileNotFoundError(f"Missing local files referenced by {summary_path}: {', '.join(missing)}")

    if service is None:
        service, _ = get_service()

    print(f"[upload] uploading {len(pairs)} files for benchmark '{benchmark}'")
    # print(f"pairs: {pairs}")
    results = upload_files(pairs, service=service, overwrite=overwrite)
    return results

upload("fir")