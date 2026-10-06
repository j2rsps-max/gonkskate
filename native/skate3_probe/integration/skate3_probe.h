#pragma once
#include "gonkskate_probe.h"

namespace gonkskate::guest_probe {
// Opt-in through GONKSKATE_GUEST_PROBE_DIR before launching the source build.
// Start and Stop run on the application lifecycle thread. Stop disables and
// drains recording, but retains the Recorder until guest threads have exited.
void Start() noexcept;
void Stop() noexcept;
void Observe(uint8_t* base, uint32_t entity, probe::Kind kind,
             uint32_t hook, uint32_t caller, uint32_t detail = 0) noexcept;
}
