import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
logdir = Path(sys.argv[2]).resolve()

q_path = root / "external" / "kisak-thug" / "Scripts" / "game" / "skater" / "physics.q"
cfg_path = root / "native" / "thug_adapter" / "config" / "thug_core_physics_defaults.json"

q = q_path.read_text(encoding="utf-8", errors="replace")
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

def strip_inline_comment(s: str) -> str:
    # Q files use both ; and // comments.
    cut = len(s)
    for marker in (";", "//"):
        i = s.find(marker)
        if i >= 0:
            cut = min(cut, i)
    return s[:cut].strip()

mismatches = []
found = 0

for p in cfg["parameters"]:
    name = p["name"]
    expected = p["value"]
    # Case-insensitive because some entries vary capitalization in source/code.
    pattern = re.compile(r"^\s*" + re.escape(name) + r"\s*=\s*(.+?)\s*$", re.I | re.M)
    m = pattern.search(q)
    if not m:
        mismatches.append({"name": name, "reason": "not found in physics.q"})
        continue

    raw = strip_inline_comment(m.group(1))
    token = raw.split()[0] if raw else ""
    try:
        # Leading zeros in Q source are decimal-looking values, not Python octal.
        actual = float(token)
    except ValueError:
        mismatches.append({"name": name, "reason": f"non-scalar source value: {raw}"})
        continue

    found += 1
    if abs(float(expected) - actual) > max(1e-6, abs(float(expected)) * 1e-6):
        mismatches.append({
            "name": name,
            "expected": expected,
            "actual": actual,
            "source": raw
        })

result = {
    "captured_parameter_count": len(cfg["parameters"]),
    "found_in_physics_q": found,
    "mismatch_count": len(mismatches),
    "mismatches": mismatches,
}
(logdir / "thug-param-compare.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

print(json.dumps(result, indent=2))
# Some parameters are globals or may have duplicate/commented declarations.
# We report mismatches for research, but do not fail the whole v0.5 environment test.
