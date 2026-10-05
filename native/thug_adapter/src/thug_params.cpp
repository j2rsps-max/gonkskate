#include "gonkskate_thug_params.h"
#include <cmath>
#include <cstddef>

namespace {
struct NamedStat { const char* name; GonkThugScriptedStat definition; };
#include "thug_scripted_stats.inc"
// Q checksum names are case-insensitive ASCII.
bool equal_name(const char* a, const char* b) {
    while (*a && *b) {
        const auto lower = [](unsigned char c) { return c >= 'A' && c <= 'Z' ? c + 32 : c; };
        if (lower(*a++) != lower(*b++)) return false;
    }
    return *a == *b;
}
}

extern "C" uint8_t gonk_thug_evaluate_stat(const GonkThugScriptedStat* p,
                                          const GonkThugStatContext* c, float* out) {
    if (!p || !c || !out || p->stat_index < -1 || p->stat_index >= 10 ||
        c->difficulty < 0 || c->difficulty > 2) return 0;
    const float stat = p->stat_index == -1 ? 10.0f : c->stats[p->stat_index];
    if (!std::isfinite(stat) || !std::isfinite(p->low) || !std::isfinite(p->high)) return 0;
    float value = p->low + ((p->high - p->low) * stat / 10);
    if (c->switched && p->has_switch) {
        if (!std::isfinite(c->stats[6]) || !std::isfinite(p->switch_low) ||
            !std::isfinite(p->switch_high)) return 0;
        float mult = p->switch_low + (p->switch_high - p->switch_low) * c->stats[6] / 10.0f;
        if (mult < 0.0f) mult = 0.0f;
        if (mult > 1.0f) mult = 1.0f;
        value *= mult;
    }
    if (c->difficulty != 1 && p->has_difficulty) {
        const float mult = c->difficulty == 0 ? p->difficulty_low : p->difficulty_high;
        if (!std::isfinite(mult)) return 0;
        value *= mult;
    }
    if (p->has_limit) {
        if (!std::isfinite(p->limit)) return 0;
        if (p->low < p->high) { if (value > p->limit) value = p->limit; }
        else { if (value < p->limit) value = p->limit; }
    }
    if (!std::isfinite(value)) return 0;
    *out = value;
    return 1;
}

extern "C" uint8_t gonk_thug_get_scripted_stat(const char* name,
                                              const GonkThugStatContext* c, float* out) {
    if (!name) return 0;
    for (const auto& p : kStats)
        if (equal_name(name, p.name)) return gonk_thug_evaluate_stat(&p.definition, c, out);
    return 0;
}

extern "C" void gonk_thug_default_stat_context(GonkThugStatContext* c) {
    if (!c) return;
    for (float& stat : c->stats) stat = 5.0f;
    c->switched = 0;
    c->difficulty = 1;
}
