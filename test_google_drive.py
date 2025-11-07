from google_drive import (
    get_service,
    upload_file,
    download_file,
    upload_files,
    download_files,
)
import os
import shutil
import random

DRIVE_BASE = "My Drive/Workspace/Daisenbot_Dataset"
DRIVE_TEST_FOLDER = f"{DRIVE_BASE}/test"

def _ensure_local_tmp():
    os.makedirs("./tmp", exist_ok=True)

def _cleanup_local_tmp():
    if os.path.isdir("./tmp"):
        shutil.rmtree("./tmp")

def _remote_delete(service, file_ids):
    for fid in file_ids:
        try:
            service.files().delete(fileId=fid).execute()
        except Exception:
            pass

def test_single_upload_download():
    # create local file with random content
    _ensure_local_tmp()
    local_src = "./test.txt"
    value = str(random.randint(0, 1_000_000))
    with open(local_src, "w", encoding="utf-8") as f:
        f.write(value)

    service, _ = get_service()
    uploaded_id = None
    try:
        # upload into DRIVE_TEST_FOLDER (folder path ending with '/')
        uploaded_id = upload_file(local_src, f"{DRIVE_TEST_FOLDER}/", service=service, overwrite=True)
        assert uploaded_id, "upload_file did not return a file id"

        # download back to ./tmp/test.txt
        local_dst = "./tmp/test.txt"
        download_file(f"{DRIVE_TEST_FOLDER}/test.txt", local_dst, service=service)
        with open(local_dst, "r", encoding="utf-8") as f:
            got = f.read()
        assert got == value, "downloaded content mismatch"
        print(f"Passed: read {local_dst}:", got)
    finally:
        # always clean up remote file
        if uploaded_id:
            _remote_delete(service, [uploaded_id])
        # remove local src
        try:
            os.remove(local_src)
        except Exception:
            pass

    # if we reached here, test passed -> remove tmp folder as requested
    _cleanup_local_tmp()

def test_multi_upload_download():
    _ensure_local_tmp()
    # prepare two local files
    src1 = "./tmp/test1.txt"
    src2 = "./tmp/test2.txt"
    val1 = str(random.randint(0, 1_000_000))
    val2 = str(random.randint(0, 1_000_000))
    with open(src1, "w", encoding="utf-8") as f:
        f.write(val1)
    with open(src2, "w", encoding="utf-8") as f:
        f.write(val2)

    service, _ = get_service()
    uploaded_ids = []
    try:
        # upload both into the drive test folder, keep same basenames
        pairs = [(src1, f"{DRIVE_TEST_FOLDER}/"), (src2, f"{DRIVE_TEST_FOLDER}/")]
        results = upload_files(pairs, service=service, overwrite=True)
        for src, target, ok, info in results:
            assert ok, f"upload failed for {src}: {info}"
            # info is file id when success
            uploaded_ids.append(info)


        # download them back to ./tmp/
        path1 = "./tmp/test1.txt"
        path2 = "./tmp/test2.txt"
        dl_pairs = [(f"{DRIVE_TEST_FOLDER}/test1.txt", path1),
                    (f"{DRIVE_TEST_FOLDER}/test2.txt", path2)]
        dl_results = download_files(dl_pairs, service=service)
        # for drive_path, local_dst, ok, err in dl_results:
        #     assert ok, f"download failed for {drive_path}: {err}"
    # finally:
    #     pass

        # verify contents
        with open(path1, "r", encoding="utf-8") as f:
            assert f.read() == val1
            print(f"Passed: read {path1}:", f.read())
        with open(path2, "r", encoding="utf-8") as f:
            assert f.read() == val2
            print(f"Passed: read {path2}:", f.read())
    finally:
        # always remove remote files and local srcs
        if uploaded_ids:
            _remote_delete(service, uploaded_ids)
        for p in (src1, src2):
            try:
                os.remove(p)
            except Exception:
                pass

    # on success remove downloaded tmp folder
    _cleanup_local_tmp()

test_single_upload_download()

test_multi_upload_download()