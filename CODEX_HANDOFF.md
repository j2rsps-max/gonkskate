# GonkSkate Codex handoff — 2026-10-07

This is a continuation of an existing project. The owner supplies ideas and
tests; Codex is expected to inspect, implement, build, fix failures and make
routine engineering decisions. Read the current source and repository-specific
instructions before making changes. This document records the handoff state;
later commits and owner results may supersede it.

## Open the actual source project

Repository: <https://github.com/j2rsps-max/gonkskate>, development on `main`.
Code-only Windows packages are preserved on the `downloads` branch. `VERSION`
is `0.8.0`; subsequent development ZIPs use source commit IDs until a meaningful
new playable release is ready. Read each ZIP's `RELEASE_INFO.json` for provenance.

The owner wants local and cloud Codex work sharing this GitHub project. The
Windows parent is **`Z:\Games\GonkSkate`**. The owner reports THUG is installed
inside its existing Tony Hawk's Underground subfolder, whose exact name and
contents have not been inspected from the cloud. Do not rename or overwrite it.

Recommended layout:

```text
Z:\Games\GonkSkate\
  existing THUG game folder\
  Source\        full repository, used by local Codex
  Integration\   portable development check, its .cmd files at this level
  Playable\      portable v0.8.0 workshop, GONKSKATE.cmd at this level
```

If `Source` does not exist, the owner can create the checkout with:

```powershell
git clone --single-branch --branch main https://github.com/j2rsps-max/gonkskate.git 'Z:\Games\GonkSkate\Source'
```

Set the local Codex project's working directory to `Source`, or tell the new
chat to use that repository if its project points to the parent. Paste
`CODEX_START_PROMPT.txt` into the first chat. The full repository contains this
handoff; the small Integration Check ZIP ships copies for convenience but omits
most source. Do not try to develop the whole runtime from that subset.
The clone selects `main` so the large historical binary packages stay in the
separate download workflow. It preserves the source branch's history.
The owner confirms the existing Codex project already points at
`Z:\Games\GonkSkate`; it can stay there. Use the `Source` child as the working
Git repository. The exact walkthrough is in
[docs/LOCAL_CODEX_SETUP.md](docs/LOCAL_CODEX_SETUP.md).

If a checkout already exists, inspect `git status`, its remotes and recent commits
before updating. Preserve local work. Pull clean source with `git pull --ff-only`;
use separate branches when local and cloud sessions work simultaneously. Do not
force-push or discard another session's edits to synchronize them.

Cloud work uses the same repository, not the owner's Windows drive. Cloud Codex
has no automatic access to `Z:`, the desktop's Downloads folder or installed
games. Local Codex should inspect the actual accessible folders. Neither
environment should claim access or a test result it has not demonstrated.

## Accepted direction and owner preferences

- Main playable frontend: Skate3Recomp, preserving original Skate gameplay and
  presentation, with authentic THUG gameplay as an alternate authoritative mode.
- Map, skating backend, appearance and eventually scoring, camera, bail and rules
  are independent choices. Do not run two authoritative physics simulations on
  the same player. Mode changes initially reset to a known spawn.
- Preserve authentic THUG C++ state-machine/physics code and normal `Update()`
  ordering. Adapt input, time and environmental queries. Do not replace it with
  Rapier or a home-made approximation or rewrite it into Rust for style alone.
- Rust host/common work remains useful. Its earlier THUG/Skate backend prototypes
  are not authentic game physics. Native C/C++ adapters are appropriate.
- Godot is the existing standalone collision/controller/workshop regression
  client. Keep it cumulative while advancing the main Skate frontend.
- Controller support is required for both games. Original Skate controls work
  on the owner's existing recompilation. Do not collapse Skate's dual sticks
  into THUG's digital controls.
- Long-term characters include Tony Hawk guest/hidden characters such as
  Spider-Man, Skate 1–3 and compatible modded Skate 3 characters. Broader THPS,
  THUG Pro, Session and Skater XL map formats are desired. Each format needs
  evidence and a real converter; these are not supported universally today.
- Keep retail assets, captures, generated retail guest code and derived worlds/
  characters local. Publish code, tooling, adapters, patches and diagnostic-only
  results. No ISO or retail asset upload is needed for routine metadata diagnosis.
- Keep the project cumulative and preserve old working packages. Ask for owner
  direction when needed, otherwise continue implementing and investigating.
- After a usable release is verified, create a public GitHub installation page
  explaining requirements, local asset setup, controllers, testing and support.
  Do not present that later release/documentation as completed now.

## Verified state at handoff

The original floor/air milestone is already achieved. Real
`Obj::CSkaterCorePhysicsComponent::Update()` runs at a controlled 60 Hz against
synthetic/normalized world queries. Ground movement, original stat interpolation,
ollie, air gravity, landing, rail acquisition/grind movement and rail exit have
deterministic tests. Core/state/rotation/math components and tested environmental
facades are shared by the CLI and Windows DLL/Linux library. Do not restart
this extraction from the v0.5.1 placeholder backend.

The native library exposes a versioned C ABI, state/error reporting and
creator-thread session ownership. Existing executable/library comparisons pass
for idle, ollie, steer, 10,000-tick soak, rail and rail jump. Full balance, tricks,
scoring, animation selection, bails and moving-object behavior remain incomplete.

The owner tested the Windows courtyard/controller path. Its 2,234 input/state
ticks replayed byte-for-byte in Linux. A later v0.7.1 retail Skate render capture
imported 857 triangles and completed 1,308 play ticks with 12 landings and no
native stops. It was a different area from the initial freeze report, so the
earlier problematic geometry has not been reproduced in the cloud. Captures
contain render triangles and generic concrete, not original Skate collision or
rails. v0.8.0 adds a rail/spawn workshop, whose owner retest remains outstanding.

Character import supports inspected THUG v2 SKE skeletons, little-endian Xbox/DX9
skin streams, explicit platform weight decoding, original full skeletal clips
and texture dictionaries. Rigged GLBs retain source axes and convert inches to
meters. Animation previews use original sampling baked at 60 Hz with STEP
channels. Optional Q48/T48 tables must be original matching tables. First-pass
textures support swizzled P8/A1R5G5B5/A8R8G8B8 and linear DXT1/DXT5. Original
multipass effects/appearance scripts and retargeting remain pending.

Differential fixtures execute original skeleton/skin/animation code or the exact
texture unswizzle routine against synthetic inputs. Godot imports/deforms the
GLBs, and independent Khronos checks have zero errors/warnings for the tested
fixtures. This validates format interchange; retail appearance is still pending.

Owner result ZIPs from `5299504` confirm **26/26 synthetic character checks
passed on Windows**. One run completed with exit code 0; another failed only
when opening `C:\path\...` example files afterward. No decoder failure was found.
`f7782c7` added a local file picker and clear path errors. Its first owner Windows
run with real files has not happened. The owner has now installed THUG; no
matching retail rig/mesh/texture/clip has yet been verified.

The next tool is `RUN_THUG_FILE_CHECK.cmd`. It selects a game folder and returns
filenames, sizes and counts only. It skips GonkSkate packages and links; errors
and limits produce an incomplete result rather than a claimed successful scan.
Names are hints, not verified source formats or character pair identities.

The owner has now run that inventory successfully. The returned
`GonkSkate-thug-files-results-20261007-163554-841393.zip` reports 6,829 files,
635 `.skin`, 812 `.tex`, no loose `.ske`/`.ska`, 182 archive candidates and no
scan errors/limits. Relevant actual relative paths are
`Game/Data/pre/skeletons.pre` (34,380 bytes), `anims.pre` (651,024),
`netanims.pre` (2,970,968), `unloadableanims.pre` (2,807,884) and
`skaterparts.pre` (10,338,660). Source formats and archive contents have not
been read by the cloud agent. The local next task is to inspect the PRE loader
and actual archive headers, then expose a verified rig/clip for the importer.

The embedded runtime can be linked by source staging into the pinned Skate
frontend with an ABI startup handshake. The staged input driver and read-only
presentation probe have fixture coverage. The complete retail frontend build,
live controlled-player identity, authoritative scheduler and original collision
world remain unverified. Animation, cloth, view and swap observations do not
establish those simulation boundaries. No live backend switch is implemented.

## Source and documentation to read

Start with `docs/CURRENT_CHECKPOINT.md`, `START_HERE.md`, `README.md`,
`CHANGELOG.md`, `TEST_NOTES.md` and `docs/ROADMAP.md`. Then read:

- `docs/INTEGRATION_DIRECTION.md` and `docs/WINDOWS_VALIDATION.md`.
- `docs/CHARACTER_IMPORT_PROGRESS.md` and `tools/import_thug_{rig,skin,animation,texture,character}.py`.
- `docs/THUG_EMBEDDED_RUNTIME.md`, native adapter headers, session/runtime code
  and `tools/build_thug_headless.py`.
- `docs/SKATE3_GUEST_PROBE.md`, `docs/SKATE3_DRIVER_INTEGRATION.md`,
  `native/skate3_probe/`, `tools/stage_skate3_probe.py` and
  `scripts/build-skate3-integration.py`.
- `docs/THUG_PARAMETER_MODEL.md`, `docs/THUG_DEPENDENCY_MATRIX.md` and
  `docs/THUG_CONSTRUCTION_ORDER.md` for extraction decisions.
- All relevant source under `native/thug_adapter/` and `crates/`; inspect caller
  contracts before changing environmental adapters.

Research pins at this handoff:

| Source | Commit |
| --- | --- |
| `SwagSoftware/kisak-thug` | `98b4e24921446ccd4b157453e25697f9574f0053` |
| `Yoraikou/Skate3` | `f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd` |
| `mchughalex/rexglue-skate3` | `7eb0faf7787f5e01333c228b8e3f03c32f7295ea` |

Verify checkout identities and tracked changes before source-derived work.
Do not silently update a pin to unblock compilation. Relevant Skate TU3 hashes
are in `native/skate3_adapter/config/upstream.json`.

## Immediate local task and integration gates

1. Find the actual THUG installation child under `Z:\Games\GonkSkate`.
   Use `RUN_THUG_FILE_CHECK.cmd` in `Integration`, or invoke
   `scripts/run-thug-file-check.py` from `Source`. Preserve the resulting
   `logs/GonkSkate-thug-files-results-*.zip`. Inspect loose files versus archives.
2. Identify a matching skeleton and weighted mesh from actual file/layout data.
   If packed, inspect the archive's format and original loader before writing a
   bounded extractor. There is no general game-archive decoder today.
3. Import the neutral pair with `RUN_CHARACTER_IMPORT.cmd`, inspect the GLB, then
   add matching textures and a full original clip. Character checksum names,
   compatible bone counts or extensions alone cannot verify a correct pair.
4. In parallel when inputs/tooling permit, finish a local source-built Skate
   frontend. Verify ordinary Skate controls before enabling read-only recording.
   Identify the controlled player, real tick and collision ownership.
5. Attach the original THUG runtime with explicit input/time/world ownership,
   then prove movement, landing, presentation following and mode changes. Import
   one original THUG collision area once the environmental boundary is ready.

Do not wait for retail assets to improve source, tests and tools that do not
depend on them. Do not ask the owner to run placeholder-path commands. Give an
exact command rooted in a confirmed folder or a file/folder picker.

## Build/test and handoff discipline

Owner hardware: RTX 2070 8 GB, Ryzen 3600X, 16 GB DDR4, 1080p Windows. Git,
Python, VS 2022 C++ tools, CMake and Rust were reported installed. Clang/Ninja
and the full Skate source-build prerequisites still need local verification.
Keep source-build memory use conservative; the helper defaults to one job.

For Python regression checks from the source checkout:

```text
python tools/test_thug_file_inventory.py
python tools/test_character_check.py
python tools/test_thug_rig.py
python tools/test_thug_character.py
python tools/test_thug_animation.py
python tools/test_thug_texture.py
```

`cargo test --workspace --locked` checks the Rust workspace. `scripts/test-all.py`
collects portable project checks and native behavior into logs, but its native
builders/toolchain assumptions must be inspected for the current environment.
Actual-engine and original-source differential helpers are documented beside
their importer. Run checks that apply to the change and distinguish unrun checks.

The current cloud toolchain is under `/workspace/tooling`: Cargo/Rustup have
local homes, Python supplies CMake/Ninja, Clang/MinGW are extracted locally,
Godot is checksum-verified, and Wine runs Windows fixtures. Shells may need
`PATH`, `CARGO_HOME` and `RUSTUP_HOME` restored to those paths. These caches are
not portable source dependencies and may not exist in a new cloud environment.
Use the available environment setup skill/tooling when applicable; do not assume
host installs or retail data survive a new session.

Judge native commands by exit codes, not stderr alone. Preserve the Windows
PowerShell 5.1 stderr fix and avoid `$Args`/automatic-variable collisions.
Results should capture failures and remain small; do not require hundreds of
copied console lines. Inventory/character result ZIPs contain metadata and test
diagnostics, not original files or decoded characters.

Commit meaningful changes and update checkpoint/roadmap evidence when a new
result arrives. Before publishing, check source provenance and asset-free ZIP
whitelists, preserve older releases and verify the public download hash.
An evidence-only notes update is not a new combined-game playable milestone.
