import argparse
import logging
import os
import shutil
import time
from datetime import datetime

from tqdm import tqdm
import filecmp


def walk_folder(folder, ignore_files=None, ignore_extensions=None, ignore_hidden=True):
    file_paths = []
    ignore_files = ignore_files or []
    ignore_extensions = ignore_extensions or []

    all_files = []
    for root, dirs, files in os.walk(folder):
        for d in dirs[::-1]:
            rel_dir_path = os.path.relpath(os.path.join(root, d), folder)
            if ignore_hidden and d.startswith("."):
                dirs.remove(d)
                continue
            if any(
                rel_dir_path == ign or rel_dir_path.startswith(os.path.join(ign, ""))
                for ign in ignore_files
            ):
                dirs.remove(d)
                continue
        for file in files:
            all_files.append((root, file))

    for root, file in tqdm(all_files, desc=f"Walking {folder}", unit="file"):
        if ignore_hidden and file.startswith("."):
            continue
        relative_path = os.path.relpath(os.path.join(root, file), folder)
        if any(relative_path == ign for ign in ignore_files):
            continue
        if any(relative_path.endswith(ext) for ext in ignore_extensions):
            continue
        file_paths.append(relative_path)

    return file_paths


def sync_folders(
    folderA,
    folderB,
    sync_most_recent=False,
    ignore_files=None,
    ignore_extensions=None,
    ignore_hidden=True,
):
    def loop_folder(rootA, rootB):
        dirs_to_create = []
        for root, dirs, _ in os.walk(rootA):
            for d in dirs:
                rel_dir_path = os.path.relpath(os.path.join(root, d), rootA)
                target_dir_path = os.path.join(rootB, rel_dir_path)
                if not os.path.exists(target_dir_path):
                    dirs_to_create.append(target_dir_path)
        for target_dir_path in tqdm(dirs_to_create, desc=f"Creating dirs in {rootB}", unit="dir"):
            os.makedirs(target_dir_path, exist_ok=True)

    def filter_files(files, rootA, rootB):
        """
        Determines which files need to be copied from rootA to rootB,
        computing the total size in the same pass — no separate size loop.

        Returns:
            to_copy (list): List of (file, status) tuples for files that need copying.
            total_size (int): Total byte size of those files.
        """
        to_copy = []
        total_size = 0
        for file in tqdm(files, desc=f"Filtering files in {rootA}", unit="file"):
            file_path = os.path.join(rootA, file)
            target_path = os.path.join(rootB, file)
            if not os.path.exists(target_path):
                to_copy.append((file, "new"))
                total_size += os.path.getsize(file_path)
            elif sync_most_recent and os.path.getmtime(file_path) > os.path.getmtime(target_path):
                same = filecmp.cmp(file_path, target_path, shallow=False)
                status = "more recent (same content)" if same else "more recent"
                to_copy.append((file, status))
                total_size += os.path.getsize(file_path)
        return to_copy, total_size

    def copy_files(to_copy, rootA, rootB, total_size):
        """
        Copies only the pre-filtered files, updating the progress bar by bytes.
        """
        with tqdm(
            total=total_size,
            desc=f"Syncing to {rootB}",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for file, status in tqdm(to_copy, desc=f"Copying files to {rootB}", unit="file"):
                file_path = os.path.join(rootA, file)
                target_path = os.path.join(rootB, file)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                if status == "more recent (same content)":
                    os.utime(target_path, None)
                else:
                    shutil.copy2(file_path, target_path)
                pbar.update(os.path.getsize(file_path))

    logging.info(f"Copying arborescence structure between {folderA} and {folderB}...")
    loop_folder(folderA, folderB)
    loop_folder(folderB, folderA)

    logging.info("Walking through folders to get file lists...")
    folderA_files = walk_folder(folderA, ignore_files, ignore_extensions, ignore_hidden)
    folderB_files = walk_folder(folderB, ignore_files, ignore_extensions, ignore_hidden)

    logging.info("Starting sync process...")
    start = time.time()

    to_copy_A_to_B, size_A_to_B = filter_files(folderA_files, folderA, folderB)
    to_copy_B_to_A, size_B_to_A = filter_files(folderB_files, folderB, folderA)
    copy_files(to_copy_A_to_B, folderA, folderB, size_A_to_B)
    copy_files(to_copy_B_to_A, folderB, folderA, size_B_to_A)

    synced_A_to_B = to_copy_A_to_B
    synced_B_to_A = to_copy_B_to_A

    full_time = time.time() - start
    logging.info(f"Sync completed in {int(full_time)} seconds. Saving logs...")

    log_filename = datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + "_sync.log"
    for folder in (folderA, folderB):
        os.makedirs(os.path.join(folder, ".sync_logs"), exist_ok=True)

    with open(os.path.join(folderA, ".sync_logs", log_filename), "w") as log_file:
        log_file.write("Parameters:\n")
        log_file.write(f"  folderA: {folderA}\n")
        log_file.write(f"  folderB: {folderB}\n")
        log_file.write(f"  sync_most_recent: {sync_most_recent}\n")
        log_file.write(f"  ignore_files: {ignore_files}\n")
        log_file.write(f"  ignore_extensions: {ignore_extensions}\n")
        log_file.write(f"  ignore_hidden: {ignore_hidden}\n\n")
        log_file.write(
            f"Synced {len(folderA_files) + len(folderB_files)} files "
            f"({len(synced_A_to_B) + len(synced_B_to_A)} copied) "
            f"between {folderA} and {folderB} in {int(full_time)} seconds.\n\n"
        )
        for file, status in synced_A_to_B:
            log_file.write(f"Because of '{status}': {os.path.join(folderA, file)} ==> {os.path.join(folderB, file)}\n")
        for file, status in synced_B_to_A:
            log_file.write(f"Because of '{status}': {os.path.join(folderB, file)} ==> {os.path.join(folderA, file)}\n")

    shutil.copy2(
        os.path.join(folderA, ".sync_logs", log_filename),
        os.path.join(folderB, ".sync_logs", log_filename),
    )
    logging.info(
        f"Logs saved to {os.path.join(folderA, '.sync_logs', log_filename)} "
        f"and {os.path.join(folderB, '.sync_logs', log_filename)}."
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    parser = argparse.ArgumentParser(
        description="SmartSync - Folder Synchronization Tool"
    )

    parser.add_argument("A", type=str, help="Path to the first folder.")
    parser.add_argument("B", type=str, help="Path to the second folder.")
    parser.add_argument(
        "--sync_most_recent",
        action="store_true",
        default=False,
        help="Sync the most recently modified files.",
    )
    parser.add_argument(
        "--ignore_files",
        type=str,
        nargs="*",
        default=None,
        help="List of file paths to ignore during sync.",
    )
    parser.add_argument(
        "--ignore_extensions",
        type=str,
        nargs="*",
        default=None,
        help="List of file extensions to ignore during sync.",
    )
    parser.add_argument(
        "--ignore_hidden",
        action="store_true",
        default=True,
        help="Ignore hidden files and folders during sync.",
    )

    args = parser.parse_args()
    if os.path.exists(args.A) is False:
        logging.error(f"Folder A does not exist: {args.A}")
        exit(1)
    if os.path.exists(args.B) is False:
        logging.error(f"Folder B does not exist: {args.B}")
        exit(1)

    sync_most_recent = args.sync_most_recent
    ignore_files = (
        args.ignore_files + [".sync_logs/"] if args.ignore_files else [".sync_logs/"]
    )
    ignore_extensions = args.ignore_extensions
    ignore_hidden = args.ignore_hidden

    logging.info(f"Starting sync between {args.A} and {args.B} with parameters:\n")
    logging.info(f"  sync_most_recent: {sync_most_recent}")
    logging.info(f"  ignore_files: {ignore_files}")
    logging.info(f"  ignore_extensions: {ignore_extensions}")
    logging.info(f"  ignore_hidden: {ignore_hidden}")

    sync_folders(
        args.A,
        args.B,
        sync_most_recent=sync_most_recent,
        ignore_files=ignore_files,
        ignore_extensions=ignore_extensions,
        ignore_hidden=ignore_hidden,
    )