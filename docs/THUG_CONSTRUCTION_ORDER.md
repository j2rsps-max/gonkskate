# THUG skater construction order — v0.4

Recovered from `CSkater::CSkater(...)`.

Original local-skater component order:

1. SkaterState
2. Input
3. SkaterScore
4. SkaterMatrixQueries
5. Trick
6. SkaterPhysicsControl
7. SkaterCorePhysics
8. SkaterRotate
9. SkaterGap
10. SkaterAdjustPhysics
11. Trigger
12. SkaterFinalizePhysics
13. SkaterCleanupState
14. Walk
15. SkaterLocalNetLogic
16. SkaterEndRun
17. SkaterBalanceTrick
18. SkaterLoopingSound
19. StatsManager
20. MovableContact
21. SkaterRunTimer
22. SkaterStateHistory
23. SkaterFlipAndRotate

For the headless GonkSkate bring-up, preserve the real transform/state, SkaterState,
adapted Input, SkaterPhysicsControl, SkaterCorePhysics, and SkaterRotate first.
Use thin/inert peers for sound, score, triggers, walking, moving contacts, and
nonessential trick bookkeeping. Omit rendering/model/camera/network components
from the first test.

Any stub that gets called during the ground/air test should log the call so we
can promote only the dependencies that are actually required.
