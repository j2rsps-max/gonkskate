# GonkSkate v0.6.0

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

## First playable preview

Run `RUN_PLAYABLE.cmd` from the full Windows preview package. It includes a
synthetic floor, placeholder skater, follow camera, keyboard/controller input
and authentic THUG ground/air movement. Hold Space and release to ollie.
Read [START_HERE.md](START_HERE.md) and [first playable test](docs/FIRST_PLAYABLE_TEST.md).
The historical archives under `history/` remain unchanged.

## Legal/content boundary

This package contains no retail THUG/THUG2/Skate 3 game assets. Future import
tools should operate on files supplied locally by the user from their own copies.

## Current native progress

The standalone executable compiles real THUG core/state/rotation/math code at
60 Hz. The presentation client sends input and reads authoritative native state.
The Rust FFI links the tested native stat evaluator; integrating the full native
runtime into the Rust backend is next. Rust's selectable THUG/Skate3 simulation
backends are still prototypes. Rails and imported collision remain future work.
