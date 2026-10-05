# Skate host controller driver (v0.6.5)

GonkSkate now implements the actual pinned ReXGlue `InputDriver` interface and
registers it with the original, unmodified `InputSystem`. This is an input
integration milestone, not authentic Skate simulation inside GonkSkate or a
patch to an already-installed Skate3Recomp executable.

## Verified path

```text
Host controller frame
  -> latest-state mailbox
  -> HostInputDriver
  -> original SDK InputSystem
  -> guest state / settings UI
```

The driver reports slot 0 connection and gamepad capabilities, including both
sticks and both triggers. Raw state remains available to settings navigation.
The SDK checks the menu chord before applying its gameplay-active callback;
the driver intentionally does not self-gate its GetState method. Tests open and
close settings using RB+Start, check one toggle per press, and verify that guest
axes/buttons are suppressed while settings retains raw controls.

`CreateHostInputSystem()` replaces the default input factory. It registers only
the host driver. Adding it to the stock physical-driver list would OR buttons
and merge axes from multiple sources, defeating exclusive host input. Install
the normal upstream settings/XAM/freecam active callback after setup. Tool mode
registers no driver. Polls never advance simulation or consume a frame queue.

Keystroke queries return empty for a connected controller: full-state gameplay
and host UI navigation are supported; synthetic keyboard-style pad events and
repeat timing are not implemented.

## Embedding in a future source build

After upstream defines `rex::runtime`, add this directory with CMake and link
`gonkskate_skate3_input` into the guest executable. The production library uses
the SDK already linked by that executable; do not compile another InputSystem.

ReXApp calls `OnPreSetup(rex::RuntimeConfig&)` after selecting its default input
factory and before constructing the runtime. Override that hook in the Skate
host application and set:

```cpp
config.input_factory = [host_input](bool tool_mode)
    -> std::unique_ptr<rex::system::IInputSystem> {
  return gonkskate::skate3::CreateHostInputSystem(host_input, tool_mode);
};
```

`host_input` is a mailbox created by `gonk_skate3_input_create()`. Feed physical
controller snapshots through `gonk_skate3_input_submit()` on the host's capture
thread. Submit connected=0 on device/transport loss. **Stop submission, shut down
and destroy the guest runtime/drivers, then destroy the mailbox.** It is borrowed
by the driver and must outlive every caller. Do not destroy it in a derived-app
member destructor while the base app still owns a live runtime.

The source integration hook is verified by inspection. The complete retail guest
build and execution have not been run here; that requires local game data and
the guest's code-generation/build toolchain. No binary injection is provided.

## Rumble

Rumble is disabled in capabilities by default. Enable the factory's third
argument only when a host really forwards feedback to its physical device.
The SDK applies its existing vibration toggle and motor threshold, then the
driver stores host-order 16-bit speeds. `gonk_skate3_input_get_rumble()` returns a
coherent latest request with a change sequence. Reads do not consume requests.
Disconnect publishes zero motor speeds. The host must apply those zeros, send a
stop on shutdown, and avoid applying a previously cached request to another
device after switching controllers. Physical rumble delivery is not implemented
by this library.

## Validation and remaining combination work

Build and run:

```sh
python3 scripts/setup-skate3-source.py
python3 tools/build_skate3_input.py
build/skate3-input/gonkskate-skate3-input-test
```

The same tests are cross-compiled for Windows. They use original SDK InputSystem
methods, configuration and logging code, not a replacement input-system facade.
On Linux the linker discards the unused physical-driver factory. Windows COFF
still requires its unused symbols, so the test builder generates a translation
unit omitting only `CreateDefaultInputSystem()`, preserving every InputSystem
method byte-for-byte. The manifest records this omission. Production CMake uses
the complete original SDK, and neither build edits the reference checkout.
These tests need no SDL window, GPU, generated retail code or game assets.

Next: connect a live host transport to a source-built Skate guest, identify an
authoritative simulation/player-state hook, and adapt world collision queries.
Only that collision work can make Skate physics consume normalized THUG worlds.
THUG remains the authentic playable backend on the shared synthetic floor,
ramp and rail. The owner's separate Skate reference confirms real controller
play, not the GonkSkate guest hookup.
