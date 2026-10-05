# v0.5.1 hotfix notes

The second user test reached Rust successfully but stopped immediately when
Cargo printed:

`Updating crates.io index`

Windows PowerShell 5.1 converted that stderr record into a terminating error
because the outer test script used `$ErrorActionPreference = "Stop"`.

This was a harness bug, not a Cargo/Rust failure.

The same run also showed version probes returning command help/usage text rather
than versions. The helper function used a parameter named `$Args`, which
conflicted with PowerShell's automatic `$Args` variable. v0.5.1 renames that
parameter and validates native stderr behavior before running the real pipeline.
