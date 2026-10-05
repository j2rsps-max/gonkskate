
# Changelog

## v0.6.6
- Added validated runtime world loading with shared float32 collision/render geometry, spawn/facing and original multi-rail ingestion.
- Added an indexed triangle bridge with 15,000 seeded differential queries and stable nearest/farthest/flag/tie behavior.
- Added local triangulated OBJ and Skate3Recomp scene/buffer/memory-snapshot importers, with authentic fingerprint checks.
- Added a Windows F10 capture launcher that opens imported scenery using real THUG physics. Retail capture validation remains pending.
- Added an original raised courtyard OBJ demo and world selection without rebuilding the native executable.
- Tested imported-format ground/air, landing, reset, multiple rails, replay and malformed-world rejection on Linux/Windows under Wine.
- Excluded captured memory and imported world geometry from diagnostic ZIPs and release packages.
- Original Skate collision/materials/rails and live Skate physics integration remain pending.

## v0.6.5
- Implemented a host controller driver using the actual ReXGlue InputDriver interface and original InputSystem.
- Added an exclusive host input factory, connection/capabilities reporting, raw settings input and optional rumble request feedback.
- Tested controller settings open/close ordering and preserved the SDK's vibration toggle/threshold behavior.
- Added an embeddable CMake library and documented the pre-runtime factory hook and mailbox lifetime.
- Initialized pinned SDK header dependencies and cached compilation by compiler, source, headers and flags.
- Live guest transport, authoritative Skate simulation hooks and cross-game collision integration remain pending.

## v0.6.4
- Added automatic discovery of the running Windows Skate3Recomp and an inspection-only reference report.
- Reported executable identity and local game metadata without launching another game instance or bundling assets.
- Added a thread-safe latest-controller-state API with stable polls, packet change tracking, disconnect clearing and UI suppression.
- Verified the new state API against real SDK types on Linux and Windows; guest runtime hookup remains pending.
- Added a small standalone reference-check download for the owner’s working PC installation.

## v0.6.3
- Verified current Skate3 and pinned ReXGlue guest input path at XamInputGetState.
- Compiled a dual-stick/trigger controller packet encoder against real SDK types with Linux/Windows equality checks.
- Added a visible controller lab, captured guest packet previews, local XEX/TU3 metadata checks and automatic result ZIPs.
- Added an optional launcher for a separately installed authentic upstream Skate3Recomp reference run.
- Added right-stick camera look to the THUG playable preview and tested it alongside original movement/grind behavior.
- Corrected controller tests to respect configured deadzones rather than assuming the default.
- Added an exact Windows test/return checklist; authentic Skate physics integration remains pending.

## v0.6.2
- Made controller support a required milestone for both THUG and Skate backends.
- Added configurable THUG controller bindings, radial deadzones and independent dual-stick/trigger capture.
- Added controller pause/reset, D-pad directions and disconnect-to-pause behavior.
- Added deterministic Godot controller-event tests and a real-core controller integration scenario with pause/resume.
- Saved per-tick controller snapshots alongside native traces in diagnostic ZIPs.

## v0.6.1
- Compiled original THUG rail manager and ran original rail acquisition, grind movement, rail exits and grind ollies.
- Added a shared test-area definition with a straight rail and six-triangle ramp for collision and rendering.
- Added finite segment/triangle collision queries with nearest/farthest and flag-mask checks.
- Added keyboard/controller grind input, reset, slope orientation and deterministic rail/ramp/replay checks.
- Preserved original grind selection; instrumented absent balance, animation and scoring behavior explicitly.
- Added native ABI-header/compiler cache invalidation and world-hash validation before launch.

## v0.6.0
- Compiled and executed the real THUG core Update with original state, rotation, math and button code.
- Added fixed 60 Hz time, versioned CFeeler collision callback and synthetic flat-floor world.
- Preserved crouch timing and release-event/public Jump path; restored original previous-position lifecycle.
- Added deterministic ground/air, steering, braking, replay, long-run and fail-fast dependency checks.
- Added a follow-camera Godot presentation client, keyboard/controller input and recorded native session traces.
- Built a self-contained Windows x64 native executable; native behavior checks pass under Wine.
- Added one-command Windows preview launcher and automatic diagnostic ZIPs.
- Added reusable signed-repository local compiler installation and cumulative packaging.
- Recorded independent character appearance/import roadmap across Tony Hawk and Skate games.

## v0.6.0-dev
- Added native scripted-stat evaluation and Rust C ABI integration.
- Captured 18 active core stat definitions with provenance; retained unresolved references.
- Verified interpolation against exact upstream code across 20,000 cases.
- Corrected parameter comparison to ignore comments and non-skating overrides.
- Added portable readiness runner, Cargo.lock, native parameter tests, and cloud setup instructions.
- Preserved existing upstream checkouts during bootstrap.
- Authentic native ground/air simulation remains under development.

## v0.5.1
- Fixed false Cargo failure caused by Windows PowerShell 5.1 converting benign native stderr to `NativeCommandError`.
- Added shared native-command wrapper that logs stdout/stderr but judges success by process exit code.
- Fixed version probes by replacing the conflicting `$Args` parameter name.
- Added a native stderr harness self-test.
- Applied exit-code-safe handling to Cargo, CMake, Git, smoke executable and Python comparison.
- Preserved the exact v0.5 full package in `history/`.

## v0.5
- Added cumulative historical archive folder containing exact v0.1–v0.4 ZIPs.
- Added Windows prerequisite checker.
- Added one-click `RUN_FIRST_TEST.cmd`.
- Added Rust workspace test stage.
- Added native C/C++ ABI smoke project.
- Added automatic `kisak-thug` reference-source checkout/update.
- Added source-layout and expected-symbol validation.
- Added captured-parameter comparison tool.
- Added automatic result/log ZIP creation.
- Added clear installation and user-handoff documentation.

## v0.4
- Captured direct THUG core physics constants from `physics.q`.
- Documented stat-backed physics behavior and skater construction order.

## v0.3
- Defined native THUG ABI and Rust FFI world-query boundary.
- Added synthetic flat-floor callback design.

## v0.2
- Located THUG core physics and collision seams.
- Added concrete C ABI integration plan.

## v0.1
- Created Rust host architecture with independent map and physics backends.
