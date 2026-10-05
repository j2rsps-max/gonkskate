# v0.6.3: verified Skate 3 controller boundary

This update compiles a controller packet encoder against actual ReXGlue types,
adds a live controller lab and local retail-file checks, and provides an optional
launcher for a separately installed Skate3Recomp. It does not run authentic Skate
physics inside GonkSkate. The Rust Skate backend remains a prototype.

## Inspected upstream

- Skate3: `f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd`
- Its ReXGlue submodule: `7eb0faf7787f5e01333c228b8e3f03c32f7295ea`

Both were fetched and inspected on 2026-10-05. The THUG upstream is still at the
previous inspected pin. Source checkouts are ignored dependencies; no retail
assets or Skate3Recomp executable are redistributed in this package.

The verified guest-controller path is:

```text
SDK XInput / SDL driver
  -> rex::input::InputSystem::GetState()
  -> rex::kernel::xam::XamInputGetState_entry()
  -> guest X_INPUT_STATE
```

Relevant source locations at these pins:

| Source | Finding |
| --- | --- |
| SDK `include/rex/input/input.h` | 16-byte big-endian state: packet, button bits, byte triggers, signed 16-bit sticks |
| SDK `src/input/input_system.cpp` | Merges drivers, applies menu chords and active-callback suppression |
| SDK `src/kernel/xam/xam_input.cpp` | Normalizes guest user slot and obtains controller state, then applies synthetic input on success |
| SDK `include/rex/kernel/xam/input_injection.h` | Existing synthetic steps contain buttons/triggers and poll counts; no stick fields |
| Skate3 `src/skate3_app_common.cpp` | `OnPostSetup()` gates input while settings, XAM UI or freecam owns it |

The existing synthetic helper ORs buttons and maximizes triggers with physical
input. It does not replace the full controller state. Its poll counts are not
simulation ticks. Simply extending those steps would not establish deterministic
Skate simulation. A future host input driver or explicitly gated override must
preserve these UI rules and implement connection status, capabilities and rumble.

## What the new bridge proves

`native/skate3_adapter/src/skate3_pad.cpp` includes the unmodified SDK input header
and constructs its actual `X_INPUT_STATE`. It maps standard Godot button IDs to
SDK constants, flips Y from Godot down-positive to Xbox up-positive, converts both
sticks to signed 16-bit values and both triggers to bytes, then copies the guest
state bytes. Raw axes bypass the THUG deadzone; extra filtering belongs to a
verified backend profile. Unknown extra buttons remain in diagnostic raw traces
but have no corresponding Xbox packet bit.

The included Linux/Windows test executable validates golden bytes, all 15 standard
buttons, asymmetric signed endpoints, half-range sticks, trigger clamping and
non-finite rejection. Linux and Windows packets from a dual-stick/trigger session
match exactly. SDK licensing is retained beside the adapter.

The packet preview is not yet submitted to a running Skate guest. A disconnected
controller must produce a device-not-connected result at runtime; a zero packet
alone is not a connection-status substitute. Preview JSON records that status
separately. Frame numbers are capture sequence numbers, not verified Skate ticks.

## Local game readiness

The checker reads only metadata from optional `--game-root` input: XEX headers,
execution-info title/media IDs, presence of the content directory and the two
known TU3 patch hashes from the current upstream installer. It does not copy
retail files, enumerate a whole library, download title updates, or prove that a
dump will boot. Current upstream code generation needs `default.xex` and
`data/webkit/EAWebkit.xex`; current releases require matching staged TU3 patches.
An extracted dump and the installed recompilation may differ in update staging.

## Next work

1. Validate real controller captures and a local upstream reference run.
2. Implement a complete host controller driver/transport at this verified seam.
3. Locate the authoritative player state and simulation scheduler using a running
   guest and trace probes. Render entity poses are research leads, not proven
   authoritative player transforms.
4. Research collision-world coupling before defining the full physics adapter.

Map mixing, imported characters and Skate 1/2 format compatibility remain later
milestones. See [test notes](../TEST_NOTES.md) for exact Windows commands.
