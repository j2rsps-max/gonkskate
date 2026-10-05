#include "gonkskate_thug_params.h"
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>

void require(bool ok) { if (!ok) { std::cerr << "parameter test failed\n"; std::exit(1); } }
void near(float actual, float expected) { require(std::abs(actual - expected) < 0.0002f); }
int main() {
    GonkThugStatContext c{};
    gonk_thug_default_stat_context(&c);
    float v = -123;
    require(gonk_thug_get_scripted_stat("Physics_Standing_Acceleration_stat", &c, &v)); near(v, 664.5f);
    require(gonk_thug_get_scripted_stat("Physics_Jump_Speed_stat", &c, &v)); near(v, 432);
    require(gonk_thug_get_scripted_stat("Physics_air_rotation_stat", &c, &v)); near(v, 7.3f);
    c.stats[3] = 13;
    require(gonk_thug_get_scripted_stat("Skater_Max_Max_Speed_Stat", &c, &v)); near(v, 1142.9f);
    c.switched = 1;
    require(gonk_thug_get_scripted_stat("Physics_Jump_Speed_stat", &c, &v)); near(v, 410.4f);
    GonkThugScriptedStat p{10, 20, 3, 1, -1, 2, 1, 2, 0.5f, 1, 25};
    c.stats[6] = 13; c.difficulty = 0;
    require(gonk_thug_evaluate_stat(&p, &c, &v)); near(v, 25); // clamp switch, diff, then limit
    p.low = 20; p.high = 10; p.limit = 12; c.difficulty = 1;
    require(gonk_thug_evaluate_stat(&p, &c, &v)); near(v, 12); // decreasing range
    p.low = p.high = 10; p.limit = 15;
    require(gonk_thug_evaluate_stat(&p, &c, &v)); near(v, 15); // equal range uses lower limit
    p.has_limit = 0; p.stat_index = -1; p.low = 10; p.high = 20; c.switched = 0;
    require(gonk_thug_evaluate_stat(&p, &c, &v)); near(v, 20); // no stat defaults to 10
    v = -123;
    require(!gonk_thug_get_scripted_stat("Physics_spine_lean_stat", &c, &v)); near(v, -123);
    c.stats[3] = std::numeric_limits<float>::quiet_NaN(); p.stat_index = 3;
    require(!gonk_thug_evaluate_stat(&p, &c, &v)); near(v, -123);
    require(!gonk_thug_evaluate_stat(nullptr, &c, &v));
    std::cout << "THUG_PARAMETER_TEST_PASS\n";
}
