# Current upstream research targets

## THUG
Repository: `SwagSoftware/kisak-thug`

Important paths:
- `Code/Sk/Components/SkaterCorePhysicsComponent.cpp`
- `Code/Sk/Components/SkaterCorePhysicsComponent.h`
- `Code/Sk/Engine/feeler.cpp`
- `Code/Sk/Engine/feeler.h`
- `Code/Sk/Objects/skater.h`
- `Code/Sk/Objects/rail.*`

## Skate 3
Repository: `Yoraikou/Skate3`

Current structure confirms:
- native PC host / application layer in `src/`
- additional native support code in `src/native/`
- generated/recompiled Xbox 360 game code is handled via the ReXGlue toolchain/submodule flow
- native scene / rendering code is separate from the recompiled guest logic

Research priority is not renderer work. We need the smallest hook surface for:
1. input injection,
2. simulation stepping,
3. player/board transform observation,
4. world collision coupling.
