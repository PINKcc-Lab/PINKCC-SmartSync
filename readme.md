# SmartSync CLI

A lightweight Python utility to synchronize files between two directories. It ensures both folders contain the same data by performing a bidirectional sync, with support for ignoring specific files, extensions, and hidden directories.

## Features

* **Bidirectional Sync**: Copies missing files from Folder A to Folder B, and vice versa.
* **Smart Pruning**: Efficiently ignores hidden folders (like `.git`) and user-defined paths to save time and space.
* **Version Control**: Optional flag to overwrite files only if the source is more recently modified.
* **Progress Tracking**: Uses `tqdm` to show a real-time progress bar during the sync process.
* **Detailed Logging**: Automatically generates timestamps logs in a `.sync_logs` folder within both directories for audit purposes.

---

## Installation

1. **Clone the repository:**
```bash
git clone github.com/ChadEstoupStreiff/PINKCC-SmartSync
cd foldersync
```

2. **Install dependencies:**
This project requires `tqdm` for the progress bars.
```bash
pip install tqdm
```

---

## Usage

Run the script from your terminal by providing the paths to the two folders you wish to sync.

### Basic Command

```bash
python sync.py /path/to/folderA /path/to/folderB

```

### Advanced Options

| Argument | Description |
| --- | --- |
| `--sync_most_recent` | If a file exists in both, update the older version with the newer one. |
| `--ignore_files` | List specific relative paths or folders to skip (e.g., `node_modules`). |
| `--ignore_extensions` | List extensions to skip (e.g., `.tmp` `.log`). |
| `--ignore_hidden` | (Default: True) Skip any file or folder starting with a dot `.`. |

### Example

To sync two projects while ignoring the `build` folder and all `.mp4` files:

```bash
python sync.py ./Project_Alpha ./Project_Beta --ignore_files build --ignore_extensions .mp4 --sync_most_recent
```

---

## How it Works

1. **Scanning**: The script walks through both directories, building a map of relative file paths.
2. **Filtering**: It prunes hidden folders and ignored items immediately to avoid unnecessary processing.
3. **A → B Sync**: Any file found in A but missing in B (or newer in A, if enabled) is copied to B.
4. **B → A Sync**: Any file found in B but missing in A is copied to A.
5. **Logging**: A log file is created detailing every file copied and the reason (e.g., "new" or "more recent").

## Requirements

* Python 3.6+
* `tqdm` library

## License

MIT License. Feel free to use and modify for your own needs.
