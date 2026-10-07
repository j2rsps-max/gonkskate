"""Inventory local THUG filenames and sizes; never read retail file contents."""
import os
from pathlib import Path
import re
import stat

MAX_FILES = 100000
MAX_DIRECTORIES = 10000
SOURCE_PATTERN = re.compile(r"\.(ske|skin|tex|ska)(\.[^.]+)?$", re.IGNORECASE)
ARCHIVE_PATTERN = re.compile(r"\.(pre|prx|pak|zip|7z|rar|iso|cab)(\.[^.]+)?$", re.IGNORECASE)
PACKAGE_MARKERS = {"RUN_CHARACTER_CHECK.CMD", "RUN_THUG_FILE_CHECK.CMD", "GONKSKATE.CMD"}


def inventory(folder):
    root = Path(folder).resolve()
    if not root.is_dir():
        raise ValueError("Select the installed/extracted THUG folder, not an ISO or installer file.")
    pending = [root]
    files, errors, skipped = [], [], []
    directory_count, capped = 0, False
    while pending:
        current = pending.pop()
        if directory_count >= MAX_DIRECTORIES:
            capped = True
            break
        directory_count += 1
        try:
            with os.scandir(current) as scan:
                entries = sorted(scan, key=lambda item: item.name.casefold())
        except OSError as error:
            errors.append({"path": current.relative_to(root).as_posix(), "error_type": type(error).__name__})
            continue
        # A common parent may contain both the game and GonkSkate packages.
        # Exclude our packages entirely, including their synthetic fixtures/logs.
        if PACKAGE_MARKERS.intersection(entry.name.upper() for entry in entries):
            if current == root:
                raise ValueError("This is a GonkSkate tools folder. Select the Tony Hawk's Underground game folder beside it.")
            skipped.append({"path": current.relative_to(root).as_posix(), "reason": "gonkskate-package"})
            continue
        children = []
        for entry in entries:
            relative = (current / entry.name).relative_to(root).as_posix()
            try:
                info = entry.stat(follow_symlinks=False)
                # Windows reparse points include directory junctions. Do not
                # follow them out of the selected game tree or into a loop.
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    skipped.append({"path": relative, "reason": "link-or-reparse-point"})
                    continue
                if stat.S_ISDIR(info.st_mode):
                    children.append(current / entry.name)
                elif stat.S_ISREG(info.st_mode):
                    if len(files) >= MAX_FILES:
                        capped = True
                        break
                    source = SOURCE_PATTERN.search(entry.name)
                    archive = ARCHIVE_PATTERN.search(entry.name)
                    kind = source.group(1).lower() if source else "archive" if archive else "other"
                    files.append({"path": relative, "size_bytes": info.st_size, "kind_hint": kind})
            except OSError as error:
                errors.append({"path": relative, "error_type": type(error).__name__})
        if capped:
            break
        pending.extend(reversed(children))
    files.sort(key=lambda row: row["path"].casefold())
    counts = {kind: sum(row["kind_hint"] == kind for row in files) for kind in ("ske", "skin", "tex", "ska", "archive", "other")}
    return {"schema_version": 1, "scope": "THUG local file metadata inventory",
            "file_contents_read": False, "source_formats_verified": False,
            "character_pairs_verified": False, "complete": not capped and not errors,
            "limit_reached": capped, "files_counted": len(files), "directories_visited": directory_count,
            "kind_counts": counts, "files": files, "errors": errors, "skipped": skipped}


def pick_game_directory():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as error:
        raise RuntimeError("Folder selection requires Python Tcl/Tk support. "
                           "Alternatively pass --game-root with your actual THUG folder.") from error
    try:
        window = tk.Tk()
    except tk.TclError as error:
        raise RuntimeError("Folder selection is unavailable. Pass --game-root with your actual THUG folder.") from error
    try:
        window.withdraw()
        return filedialog.askdirectory(parent=window, mustexist=True,
            title="Select installed/extracted Tony Hawk's Underground folder") or None
    finally:
        window.destroy()
