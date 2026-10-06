"""Validate a bounded presentation trace without inferring player/tick ownership."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from stage_skate3_probe import HOOKS, SKATE_PIN

KINDS = {kind: int(address, 16) for address, (_, before, after) in HOOKS.items()
         for kind in (before, after) if kind}
POSE_NAMES = ["none", "valid", "unreadable", "unstable", "invalid"]


def uint(value, bits=64):
    return type(value) is int and 0 <= value < 2**bits


def analyze(path):
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Trace exceeds the 64 MiB analysis limit")
    errors, header, summary = [], None, None
    events, poses = Counter(), Counter()
    actors, current, generations = [], {}, Counter()
    callers, threads = Counter(), set()
    expected, last_time, epoch = 0, 0, 0
    records = 0
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if len(line) > 65536:
                raise ValueError("Oversized trace line")
            try:
                record = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except json.JSONDecodeError:
                errors.append(f"Unreadable JSON at line {number}; remaining data ignored")
                break
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object at line {number}")
            kind = record.get("kind")
            if header is None:
                if (kind != "header" or record.get("schema_version") != 1 or
                    record.get("scope") != "presentation-only" or record.get("units") != "meter" or
                    record.get("player_identity") != "unresolved" or record.get("simulation_tick") != "unresolved" or
                    record.get("skate3_commit") != SKATE_PIN):
                    raise ValueError("Unsupported or misleading probe header")
                header = record
                continue
            if summary is not None:
                errors.append("Data follows the final summary")
                break
            if kind == "summary":
                for key in ["written_events", "accepted_events", "dropped_events", "invalid_matrices"]:
                    if not uint(record.get(key)):
                        raise ValueError(f"Invalid summary field: {key}")
                for key in ["limit_reached", "io_error", "worker_error"]:
                    if type(record.get(key)) is not bool:
                        raise ValueError(f"Invalid summary field: {key}")
                summary = record
                continue
            if kind not in KINDS:
                raise ValueError(f"Unknown probe event at line {number}")
            for key in ["sequence", "mono_ns", "render_epoch", "host_thread_tag"]:
                if not uint(record.get(key)):
                    raise ValueError(f"Invalid event field: {key}")
            for key in ["entity", "hook", "caller", "detail"]:
                if not uint(record.get(key), 32):
                    raise ValueError(f"Invalid event field: {key}")
            if record["hook"] != KINDS[kind]:
                raise ValueError(f"Event hook/kind mismatch at line {number}")
            if record["sequence"] != expected:
                errors.append(f"Sequence discontinuity at line {number}")
            if record["mono_ns"] < last_time:
                errors.append(f"Host observation time reversed at line {number}")
            if record["render_epoch"] != epoch:
                errors.append(f"Accepted swap epoch mismatch at line {number}")
            expected = record["sequence"] + 1
            last_time = record["mono_ns"]
            if kind == "swap_begin":
                epoch += 1
            status = record.get("pose_status")
            if not uint(status, 32) or status >= len(POSE_NAMES):
                raise ValueError(f"Invalid pose status at line {number}")
            rows = record.get("world_rows")
            if status == 1:
                if (not isinstance(rows, list) or len(rows) != 12 or
                    any(type(v) not in (int, float) or not math.isfinite(v) for v in rows)):
                    raise ValueError(f"Invalid pose rows at line {number}")
                for row in range(3):
                    norm = sum(v*v for v in rows[4*row:4*row+3])
                    if not 0.0025 < norm < 400 or abs(rows[4*row+3]) >= 20000:
                        raise ValueError(f"Pose exceeds upstream structural bounds at line {number}")
            elif rows is not None:
                raise ValueError(f"Non-valid pose carries rows at line {number}")
            events[kind] += 1
            poses[POSE_NAMES[status]] += 1
            threads.add(record["host_thread_tag"])
            callers[f"{kind}:0x{record['caller']:08X}"] += 1
            records += 1
            if records > 1000000:
                raise ValueError("Too many probe records")
            entity = record["entity"]
            if not entity:
                if kind != "swap_begin":
                    errors.append(f"Null entity observation at line {number}")
                continue
            actor = current.get(entity)
            if actor is None or (not actor["active"] and kind != "view_remove"):
                generations[entity] += 1
                actor = {"entity": f"0x{entity:08X}", "observed_generation": generations[entity],
                         "active": True, "view_balance": 0, "first_sequence": record["sequence"],
                         "last_sequence": record["sequence"], "class_tags": [], "pose_samples": 0,
                         "pose_changes": 0, "observed_path_m": 0.0, "last_position_m": None}
                actors.append(actor)
                current[entity] = actor
            actor["last_sequence"] = record["sequence"]
            if kind == "view_add":
                actor["view_balance"] += 1
            elif kind == "view_remove":
                actor["view_balance"] = max(0, actor["view_balance"]-1)
                if actor["view_balance"] == 0:
                    actor["active"] = False
            if kind.startswith("bind_") and kind not in actor["class_tags"]:
                actor["class_tags"].append(kind)
            if status == 1:
                position = [rows[3], rows[7], rows[11]]
                previous = actor["last_position_m"]
                actor["pose_samples"] += 1
                if previous is not None and previous != position:
                    actor["pose_changes"] += 1
                    actor["observed_path_m"] += math.dist(previous, position)
                actor["last_position_m"] = position
    if header is None:
        raise ValueError("Empty probe trace")
    if summary is None:
        errors.append("Missing final summary; recording may have crashed or been interrupted")
    else:
        if summary["written_events"] != records or summary["accepted_events"] != records:
            errors.append("Written/accepted counts do not match the observed stream")
        if summary["dropped_events"]:
            errors.append(f"{summary['dropped_events']} observations dropped by the bounded queue")
        invalid_count = sum(poses[v] for v in ["unreadable", "unstable", "invalid"])
        if (summary["invalid_matrices"] < invalid_count or
            (summary["accepted_events"] == records and summary["invalid_matrices"] != invalid_count)):
            errors.append("Invalid-pose count is inconsistent")
        for key in ["limit_reached", "io_error", "worker_error"]:
            if summary[key]:
                errors.append(f"Recording reports {key}")
    return {"schema_version": 1, "scope": "presentation-only", "player_identity": "unresolved",
            "simulation_tick": "unresolved", "recording_complete": not errors, "integrity_issues": errors,
            "observed_events": records, "event_counts": dict(events), "pose_counts": dict(poses),
            "accepted_swaps": events["swap_begin"], "host_observation_seconds": last_time/1e9,
            "host_thread_tags": len(threads), "callers": dict(sorted(callers.items())),
            "actors": actors, "recorder_summary": summary,
            "limitations": ["Presentation poses and job/cloth/swap events do not establish a physics tick.",
                            "No actor is automatically identified as the controlled player.",
                            "Two equal guarded copies do not guarantee an atomic game update.",
                            "Generations follow observed view membership, not proven object allocation lifetimes.",
                            "Observed paths can include teleports; they are not gameplay distance or velocity."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.trace)
        text = json.dumps(result, indent=2, allow_nan=False)+"\n"
        if args.output:
            # Never replace an owner's earlier diagnostics.
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Analysis failed: {error}\n")
    return 0 if result["recording_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
