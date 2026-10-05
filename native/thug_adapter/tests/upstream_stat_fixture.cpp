// Compile the upstream GetScriptedStat function unmodified against a tiny
// script/object facade, then compare it with our adapter. No game assets/VM.
#include "gonkskate_thug_params.h"
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#define NONAME 0
#define CRCD(checksum, name) checksum
#define Dbg_MsgAssert(condition, message) do { if (!(condition)) std::abort(); } while (0)
namespace Script {
struct CPair { float mX, mY; };
struct CStruct {
    GonkThugScriptedStat p;
    bool GetPair(uint32_t key, CPair* out) {
        if (key == NONAME) *out = {p.low, p.high};
        else if (key == 0x9016b4e7 && p.has_switch) *out = {p.switch_low, p.switch_high};
        else if (key == 0xba8fb854 && p.has_difficulty) *out = {p.difficulty_low, p.difficulty_high};
        else return false;
        return true;
    }
    bool GetInteger(uint32_t, int* out) { if (p.stat_index < 0) return false; *out=p.stat_index; return true; }
    bool GetFloat(uint32_t, float* out) { if (!p.has_limit) return false; *out=p.limit; return true; }
};
}
namespace Game {
enum GOAL_MANAGER_DIFFICULTY_LEVEL { GOAL_MANAGER_DIFFICULTY_LOW, GOAL_MANAGER_DIFFICULTY_MEDIUM, GOAL_MANAGER_DIFFICULTY_HIGH };
}
GonkThugStatContext context;
namespace Mdl {
struct GoalManager { Game::GOAL_MANAGER_DIFFICULTY_LEVEL GetDifficultyLevel() { return static_cast<Game::GOAL_MANAGER_DIFFICULTY_LEVEL>(context.difficulty); } };
struct Skate {
    static Skate* Instance() { static Skate s; return &s; }
    GoalManager* GetGoalManager() { static GoalManager g; return &g; }
};
}
struct Core { bool IsSwitched() { return context.switched; } };
struct CSkater {
    enum EStat { STATS_SWITCH = 6 };
    float GetStat(EStat stat) { return context.stats[static_cast<int>(stat)]; }
    Core core;
    Core* mp_skater_core_physics_component = &core;
    float GetScriptedStat(Script::CStruct*);
};
#include "upstream_get_scripted_stat.inc"
int main() {
    std::mt19937 rng(0x601);
    std::uniform_real_distribution<float> range(-2000, 2000), stat(0, 13), multiplier(-1, 2);
    CSkater skater;
    for (int i=0; i<20000; ++i) {
        for (float& s : context.stats) s = stat(rng);
        context.switched = rng()%2; context.difficulty = rng()%3;
        Script::CStruct s{{range(rng), range(rng), int(rng()%11)-1,
            uint8_t(rng()%2), multiplier(rng), multiplier(rng),
            uint8_t(rng()%2), multiplier(rng), multiplier(rng), uint8_t(rng()%2), range(rng)}};
        if (i%20 == 0) s.p.high=s.p.low;
        float expected=skater.GetScriptedStat(&s), actual=0;
        if (!gonk_thug_evaluate_stat(&s.p, &context, &actual) || actual != expected) {
            std::cerr << "Differential mismatch at case " << i << '\n'; return 1;
        }
    }
    std::cout << "UPSTREAM_STAT_DIFFERENTIAL_PASS cases=20000\n";
}
