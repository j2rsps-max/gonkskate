# GonkSkate v0.5.1 — Windows Test Hotfix

This is the cumulative v0.5 package with two harness fixes discovered by the
first two real Windows runs.

## Fixed in v0.5.1

1. Windows PowerShell 5.1 no longer treats normal native-program stderr as a
   test failure. Cargo is expected to write messages such as
   `Updating crates.io index` to stderr.
2. The prerequisite version probe no longer collides with PowerShell's automatic
   `$Args` variable, so `git --version`, `cargo --version`, etc. now receive the
   intended arguments.
3. A harness self-test intentionally writes one line to stdout and one line to
   stderr, exits with code 0, and verifies that both were captured without
   failing.
4. Git, Cargo, CMake, the native smoke executable and Python comparison are all
   judged by their actual exit codes.

## What to do

You do not need to reinstall Rust, Git, CMake, Python, or Visual Studio based on
the previous v0.5 result.

Extract this package to a normal writable folder and run:

`RUN_FIRST_TEST.cmd`

When it finishes, send back:

`logs\GonkSkate-v0.5.1-results-*.zip`

Even a failed run is useful; the harness will package the exact failure.

## Package history

This ZIP still contains all cumulative project files plus exact historical
archives for v0.1, v0.2, v0.3, v0.4, and the original v0.5 full test package.
