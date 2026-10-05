# GonkSkate v0.6.0-dev

Experimental host/runtime research project for loading skating gameplay systems
independently from map origin.

## Current project rule

- maps are data;
- gameplay/physics is a selectable backend;
- only one skating backend is authoritative at a time.

Long-term combinations include:

- THUG map + THUG physics
- THUG map + Skate 3 physics
- Skate 3 map + THUG physics
- Skate 3 map + Skate 3 physics

## v0.5 focus

This is the first **Windows integration-readiness test package**.

Start with:

`START_HERE.md`

or simply run:

`RUN_FIRST_TEST.cmd`

v0.5 is cumulative and includes exact v0.1–v0.4 archives under `history/`.

## Legal/content boundary

This package contains no retail THUG/THUG2/Skate 3 game assets. Future import
tools should operate on files supplied locally by the user from their own copies.

## Current native progress

See [v0.6 native progress](docs/V06_NATIVE_PROGRESS.md). The Rust FFI crate now
links the native THUG parameter evaluator. Skating simulation is still a
prototype until the real THUG core is integrated.
