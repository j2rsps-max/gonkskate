#pragma once

#include "gonkskate_skate3_pad.h"
#include <rex/input/input_driver.h>
#include <rex/input/input_system.h>

namespace gonkskate::skate3 {

// Borrows the mailbox: stop the runtime and destroy every driver before freeing
// it. Rumble must only be enabled when a host actually forwards motor requests.
class HostInputDriver final : public rex::input::InputDriver {
 public:
  explicit HostInputDriver(GonkSkate3Input* input, bool rumble_enabled = false);
  rex::X_STATUS Setup() override;
  rex::X_RESULT GetCapabilities(uint32_t user, uint32_t flags,
                              rex::input::X_INPUT_CAPABILITIES* out) override;
  rex::X_RESULT GetState(uint32_t user, rex::input::X_INPUT_STATE* out) override;
  rex::X_RESULT GetStateUi(uint32_t user, rex::input::X_INPUT_STATE* out) override;
  rex::X_RESULT SetState(uint32_t user, rex::input::X_INPUT_VIBRATION* vibration) override;
  rex::X_RESULT GetKeystroke(uint32_t user, uint32_t flags,
                           rex::input::X_INPUT_KEYSTROKE* out) override;

 private:
  GonkSkate3Input* input_;
  bool rumble_enabled_;
};

// Exclusive host input: physical SDK drivers are deliberately not added, since
// InputSystem otherwise merges them with the host's authoritative snapshots.
// Use this in RuntimeConfig::input_factory before runtime setup. The application
// still installs its normal active/menu-chord callbacks in OnPostSetup().
std::unique_ptr<rex::input::InputSystem> CreateHostInputSystem(
    GonkSkate3Input* input, bool tool_mode = false, bool rumble_enabled = false);

}  // namespace gonkskate::skate3
