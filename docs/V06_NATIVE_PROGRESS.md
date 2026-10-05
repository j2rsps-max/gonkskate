# v0.6.0-dev: native parameter bridge and validated cloud workflow

This is cumulative development based on the supplied v0.5.1 ZIP. The exact
historical archives remain unchanged. This is **not** the authentic ground/air
release: `CSkaterCorePhysicsComponent::Update()` is not yet running in GonkSkate.
Both selectable Rust physics backends remain explicitly labeled prototypes.

## Implemented

- A compiled C++ parameter library and C ABI, linked from `gonkskate-thug-ffi`.
- 18 active scripted-stat definitions required by the core, with ranges, stat
  indices, switch pairs, optional difficulty pairs, and directional limits.
- Source-scoped extraction: `skater_physics` overrides globals; bike/walk data
  and commented definitions cannot supply skating values.
- Original evaluation order: interpolate (allow special stats >10), clamp the
  switch multiplier to [0,1], apply difficulty, apply the directional limit.
  An absent unnamed stat uses 10; the default skater profile uses 5/medium.
- Exact upstream `CSkater::GetScriptedStat(CStruct*)` compiled into an isolated
  test fixture, compared with the adapter in 20,000 deterministic cases.
  That test generates upstream code only under ignored `build/`; it is not
  copied into the distributed project sources.
- Python readiness harness with command exit codes, merged stdout/stderr logs,
  and a ZIP on success/failure. Existing Windows stderr and `$Arguments` fixes
  are retained. Windows's existing harness now runs native parameter tests.
- Upstream bootstrap preserves existing checkouts rather than resetting them.
- Cargo.lock for reproducible dependency installation.

## Evidence and source pin

THUG source inspected: `98b4e24921446ccd4b157453e25697f9574f0053`.
Skate3 remote HEAD observed: `f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd`.
No Skate3 physics boundaries are claimed; THUG remains the priority.

Verified on Linux: Rust workspace tests (3), C++ parameter test, C++ ABI smoke,
Q parser tests (3), upstream differential (20,000 cases), source/symbol checks,
and all four map/backend prototype combinations. Prototype runs do not prove
native skating. Windows PowerShell 5.1 execution remains untested on this machine.
The differential helper currently requires GNU/Clang command syntax; the portable
harness marks it unrun on Windows rather than silently calling it passed.

## Corrected parameter coverage

The old comparison tool reported 106 matches. The scoped parser instead finds
104 matching active definitions. `Physics_Ground_Snap_Up_SKITCHING` and
`Physics_Ground_Snap_Down_Skitching` exist only as commented definitions in the
inspected physics.q. Their original captured values remain preserved for
research, but they are not certified active defaults. `--strict` exits nonzero.

`Physics_spine_lean_stat` is referenced by core code but its physics.q definition
is commented out. It is recorded as unresolved. Native lookup fails explicitly
rather than inventing a value. The flat-floor profile must instrument and prove
that this transfer path is not reached, or recover its real configuration.

## Real-core integration findings and remaining work

A direct Linux compilation of the real component failed. A generated include
view resolved case mismatches and Windows include separators without modifying
upstream files. It exposed further platform requirements: no Linux type/math
profile, `core/thread.h`'s unsupported-platform error, and legacy debug macros.
Upstream's supported whole-game build is Windows x86/MSVC with DirectX9; simply
setting the Windows platform macro on Linux is not a valid headless solution.

Next native work must provide a supported headless platform header/math/time
profile, then compile the **whole** real component and resolve its dependency
cone. The parameter library is a usable prerequisite, not a substitute for core
physics. Do not call private ground/air functions instead of Update().

Important details recovered from the current source:

- `do_kick()` uses standing/crouching scripted acceleration and frame length;
  `m_auto_kick` or square input controls kick eligibility. Forward alone should
  not be assumed to initiate a push in every profile.
- `do_jump()` is called by the public `CallMemberFunction("Jump")` route. It is
  a script command, not an automatic consequence of setting the ollie byte.
  The headless input bridge must preserve tense timing and issue that command
  at the correct release boundary; it should not write a fake upward velocity.
- Jump checks triggers and `HaveBeenReset()` even on a flat floor. Instrument
  these peers rather than assuming they are never consulted.
- FrameLength is read at Update entry, but jump/state/button timing also uses
  `Tmr::GetTime()`. A deterministic clock must cover both clocks.
- CFeeler carries 16-bit flags, terrain, distance, trigger/script/node metadata,
  movable object and sector data. The current ABI lacks ignore masks and far
  query semantics. Extend it before making it the authoritative collision seam.
- Public GonkThugState and THUG's internal state enums require explicit mapping;
  do not cast them based on apparent names/order.

## Reproduce

Cloud installation: `bash scripts/setup-cloud.sh` (tools live in
`/workspace/tooling`). For an already prepared shell:

```bash
export RUSTUP_HOME=/workspace/tooling/rustup
export CARGO_HOME=/workspace/tooling/cargo
export PATH=/workspace/tooling/cargo/bin:/workspace/tooling/python/bin:$PATH
cd /workspace/gonkskate
python3 scripts/test-all.py
```

Windows: `RUN_FIRST_TEST.cmd` remains the supported PowerShell 5.1 entry point.
With Python and the C++/Rust/CMake tools available, the portable runner can also
be run as `py -3 scripts/test-all.py`. Return the result ZIP under `logs/`.

To verify captured stats against the pinned source:

```bash
python3 tools/extract_thug_stats.py external/kisak-thug --check
python3 tools/test_thug_stat_semantics.py external/kisak-thug
python3 tools/compare_thug_params.py . logs/parameter-audit --strict
```

The last command currently fails for the two explicitly documented missing
active skitch constants. This is a research/configuration gap, not an install
failure. No retail assets are required or included in these checks.
