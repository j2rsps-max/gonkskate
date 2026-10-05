# v0.7.0 milestone: one hub, repeatable local-world tests

GonkSkate now has one Windows entry point, `GONKSKATE.cmd`, rather than requiring
the owner to choose among developer scripts. The hub saves the installed
Skate3Recomp executable and a local map library. Capture/import performs an
acceptance check before opening the THUG test window, and every action exports
one `logs/GonkSkate-milestone-results-TIMESTAMP.zip`, including failures.

## What the area check proves

The actual native `CSkaterCorePhysicsComponent::Update()` runs 180 fixed 60 Hz
ticks. It idles for 30 frames, crouches for 15, releases a standing ollie, flies
and lands. Acceptance requires a supported flat spawn, finite state, one landing,
a 60–66 inch apex, return to ground, and identical CSV on a second execution.
Each run retains terrain, rail, collision and parameter/stub diagnostics from the
native trace. This deliberately narrow test catches a bad capture origin before
the owner starts skating. Passing it does not establish support for every THUG
state or for all triangles in the imported area.

Failed checks preserve the imported map. Adjust the spawn by creating a new
library copy, or recapture on a flat outdoor surface. The collision world has no
hidden infinite floor. Back/View or R resets after leaving the captured area.

## Verification

- Nine hub tests cover persistence, map preservation, path containment, bounded
  discovery, native stderr/exit-code handling, timeout reporting and asset exclusion.
- A source-format Skate scene/buffer/memory fixture passes capture → import →
  authentic THUG acceptance → library registration → one results ZIP. A deliberately
  unsupported spawn fails and produces its results ZIP.
- The imported-area acceptance check passes on the Windows native executable
  under Wine, with exact replay. Existing Windows native/runtime-world and SDK
  input binaries remain hash-verified.
- Linux hub startup and its full automated THUG/controller/Skate SDK path are
  exercised. Workspace Rust tests and importer/native-world regressions pass.
- The owner validated v0.6.6 courtyard/controller gameplay on actual Windows;
  its 2,234-frame trace replays exactly on Linux. The new Windows hub UI and a
  retail Skate capture still need this release's owner test.

## Command-line equivalents

From the extracted Windows folder:

```powershell
.\GONKSKATE.cmd --self-test
.\GONKSKATE.cmd --skate-exe "C:\path\to\Skate3Recomp\skate3.exe" --capture
.\GONKSKATE.cmd --scene "C:\path\to\snapshot.scene.jsonl" --no-play
.\GONKSKATE.cmd --check-world "local-worlds\my-area.json"
```

`--no-play` imports/checks without opening the playable window. The flat-spawn
check intentionally rejects slopes and unsupported spawns. Existing lower-level
scripts continue working. Packed THUG/THUG Pro/Skate/Session/Skater XL mod archives
still require their own decoders; accepting OBJ does not imply compatibility
with those game formats.

## Local data and remaining integration

Settings are in ignored `user/hub.json`; imported worlds are in ignored
`local-worlds/`. Raw capture data stays under ignored logs. Result exporters
allow only reports, traces and known diagnostic bundles; they exclude ISO/XEX,
memory snapshots, recorded mesh buffers and imported world geometry. Never send
the raw capture folder. Normal startup of the installed game can update its own
saves/settings, just as launching it directly does.

This is a static render-geometry bridge to the authentic THUG test process. It
does not embed Skate's guest physics or replace the live guest skater. The next
integration work remains identifying authoritative guest player, tick/scheduler
and collision hooks in a source-built Skate3Recomp. The original Skate app keeps
its usual gameplay and controller path. Skater assets, full animation/trick/
scoring/bail systems, and source-game collision/material/rail import remain
future work.
