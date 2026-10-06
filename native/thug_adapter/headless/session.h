#pragma once
#include <gonkskate_thug.h>
#include <memory>
#include <cstdint>

namespace Headless {
struct Controls { uint8_t push=0,crouch=0,left=0,right=0,brake=0,grind=0,reset=0; };
struct Snapshot {
    GonkVec3 position{},velocity{},forward{},up{};
    int32_t state=0,terrain=0,rail=-1;
    bool landed=false;
    uint64_t queries=0,lookups=0,adapter_calls=0;
};
// One real skater session. The environment/time facades are process-global;
// the embedded API deliberately permits only one live session on its owner thread.
class Session {
public:
    explicit Session(bool rails,bool ramp=false);
    ~Session();
    Snapshot tick(const Controls& input);
    Snapshot state() const;
    void probe_peripheral();
#ifdef GONK_THUG_RUNTIME_TESTING
    void probe_tick_collision_failure();
#endif
    Session(const Session&)=delete;
    Session& operator=(const Session&)=delete;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
void clear_environment();
}
