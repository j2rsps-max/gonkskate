#!/usr/bin/env python3
"""Produce a diagnostic-only inventory of a locally selected THUG installation."""
import argparse
import datetime
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from thug_file_inventory import inventory, pick_game_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, help="Actual installed/extracted THUG folder; otherwise Browse opens")
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    log = ROOT / "logs" / ("thug-files-" + stamp)
    log.mkdir(parents=True)
    report = {"schema_version": 1, "scope": "local THUG file inventory", "file_contents_included": False,
              "source_formats_verified": False, "character_pairs_verified": False}
    status = 0
    try:
        selected = args.game_root if args.game_root is not None else pick_game_directory()
        if selected is None:
            report.update({"status": "CANCELLED_BY_USER", "passed": True})
            print("Folder selection cancelled. No game files were read.", flush=True)
        else:
            result = inventory(selected)
            (log / "file-inventory.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            report.update({"passed": result["complete"], "status": "COMPLETE" if result["complete"] else "INCOMPLETE",
                           "files_counted": result["files_counted"], "kind_counts": result["kind_counts"]})
            status = 0 if result["complete"] else 2
            print("THUG file inventory:", json.dumps(result["kind_counts"]), flush=True)
            print("Names are candidates only; matching characters and source formats still need verification.", flush=True)
            if not result["complete"]:
                print("Inventory is incomplete; limits or inaccessible paths are recorded in the results ZIP.", flush=True)
            if not result["kind_counts"]["ske"] or not result["kind_counts"]["skin"]:
                print("No loose skeleton/mesh pair is visible yet. Return the ZIP so we can inspect the archive names.", flush=True)
    except Exception as error:
        status = 1
        report.update({"passed": False, "status": "FAILED", "error": str(error)})
        print(str(error), file=sys.stderr, flush=True)
    finally:
        report["exit_code"] = status
        (log / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        bundle = ROOT / "logs" / ("GonkSkate-thug-files-results-" + stamp + ".zip")
        with zipfile.ZipFile(bundle, "x", zipfile.ZIP_DEFLATED) as archive:
            for name in ("report.json", "file-inventory.json"):
                if (log / name).is_file():
                    archive.write(log / name, name)
        print("Results ZIP:", bundle, flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
