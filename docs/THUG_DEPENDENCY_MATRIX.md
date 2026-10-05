# THUG core physics dependency matrix

`CSkaterCorePhysicsComponent::Finalize()` currently demands these peer components.

The key is to distinguish **required object shape** from **required full behavior**.

| Component | First bring-up treatment | Why |
|---|---|---|
| `CInputComponent` | REAL/ADAPTED | Physics reads the control pad and tense/brake/steer inputs. |
| `CSkaterStateComponent` | REAL | Owns skating state, terrain, timestamped flags, spine state, physics-state selector. |
| `CSkaterPhysicsControlComponent` | REAL/MINIMAL | Determines skating vs walking and suspension/reset state. |
| `CSkaterRotateComponent` | REAL or thin-compatible | Core physics queries rotation state and coordinates some transitions. |
| `CTriggerComponent` | STUB FIRST | Needed for callbacks/events, but a flat-floor movement test can safely swallow triggers. |
| `CSkaterSoundComponent` | STUB FIRST | Sound side effects are not needed to validate movement. |
| `CTrickComponent` | STUB/MINIMAL FIRST | Needed by some trick/rail paths, but basic ground/air movement can start with inert behavior. |
| `CSkaterScoreComponent` | STUB FIRST | Score bookkeeping is not required for motion correctness. |
| `CSkaterBalanceTrickComponent` | STUB/MINIMAL | Needed for real grinds/manuals later; not essential for first ground/air test. |
| `CMovableContactComponent` | STUB FIRST | Moving platforms/vehicles can initially report no contact. |
| `CWalkComponent` | STUB FIRST | The first milestone is skating only; walking transitions remain disabled. |

## Minimum bring-up profile

The first target should instantiate or faithfully preserve:

1. base composite object transform (`m_pos`, `m_old_pos`, `m_vel`, `m_matrix`);
2. `CSkaterStateComponent`;
3. `CInputComponent` or an adapter that produces a valid `CControlPad`;
4. `CSkaterPhysicsControlComponent`;
5. `CSkaterCorePhysicsComponent`;
6. enough `CSkaterRotateComponent` behavior for state queries;
7. inert peer components for sound, triggers, score, moving contact and walk.

## Why we should not fork the physics function-by-function

`Update()` already performs the authoritative order:

1. frame timing;
2. clear one-frame state;
3. tense/input handling;
4. speed limiting;
5. collision-cache setup;
6. dispatch based on current state;
7. transfer-limit cleanup;
8. rail acquisition;
9. friction-state maintenance;
10. vert-air event transition;
11. collision-cache teardown.

Keeping this ordering is important. The adapter should drive the component as a unit and replace environmental services beneath it rather than manually invoking the private state functions.
