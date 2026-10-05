
# Changelog

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
