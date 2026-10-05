#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct GonkThugParamProvider {
    void* user;
    uint8_t (*get_float)(void* user, const char* name, float* out_value);
    uint8_t (*get_int)(void* user, const char* name, int32_t* out_value);
} GonkThugParamProvider;
#ifdef __cplusplus
}
#endif

#ifdef __cplusplus
extern "C" {
#endif
/* Mirrors GetScriptedStat: stats may exceed 10 (special uses 13).
 * stat_index=-1 means an unnamed stat was absent: use 10, not profile default.
 * Difficulty: 0=low, 1=medium, 2=high. Units remain THUG inches/seconds.
 */
typedef struct {
    float low, high;
    int32_t stat_index;
    uint8_t has_switch;
    float switch_low, switch_high;
    uint8_t has_difficulty;
    float difficulty_low, difficulty_high;
    uint8_t has_limit;
    float limit;
} GonkThugScriptedStat;

typedef struct {
    float stats[10];
    uint8_t switched;
    int32_t difficulty;
} GonkThugStatContext;

/* Return 0 on invalid input or unknown names; output remains unchanged. */
uint8_t gonk_thug_evaluate_stat(const GonkThugScriptedStat*, const GonkThugStatContext*, float*);
uint8_t gonk_thug_get_scripted_stat(const char*, const GonkThugStatContext*, float*);
void gonk_thug_default_stat_context(GonkThugStatContext*);
#ifdef __cplusplus
}
#endif
