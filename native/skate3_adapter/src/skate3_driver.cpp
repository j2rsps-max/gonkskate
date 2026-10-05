#include "gonkskate_skate3_driver.h"

#include <cstring>
#include <stdexcept>

using namespace rex;
using namespace rex::input;

namespace gonkskate::skate3 {

HostInputDriver::HostInputDriver(GonkSkate3Input* input, bool rumble_enabled)
    : InputDriver(nullptr, 0), input_(input), rumble_enabled_(rumble_enabled) {}

X_STATUS HostInputDriver::Setup() {
  return input_ ? X_STATUS_SUCCESS : X_STATUS_INVALID_PARAMETER;
}

X_RESULT HostInputDriver::GetCapabilities(uint32_t user, uint32_t flags,
                                         X_INPUT_CAPABILITIES* out) {
  if (!out || (flags & ~uint32_t(X_INPUT_FLAG_GAMEPAD))) return X_ERROR_BAD_ARGUMENTS;
  const auto result = gonk_skate3_input_poll(input_, user, 1, nullptr);
  if (result != X_ERROR_SUCCESS) return result;
  X_INPUT_CAPABILITIES caps{};
  caps.type = XINPUT_DEVTYPE_GAMEPAD;
  caps.sub_type = 1;  // Standard Xbox gamepad, not a specialized controller.
  caps.flags = rumble_enabled_ ? X_INPUT_CAPS_FFB_SUPPORTED : 0;
  caps.gamepad.buttons = 0xF7FF;  // Supported Xbox button bits, including Guide.
  caps.gamepad.left_trigger = caps.gamepad.right_trigger = 255;
  caps.gamepad.thumb_lx = caps.gamepad.thumb_ly = 32767;
  caps.gamepad.thumb_rx = caps.gamepad.thumb_ry = 32767;
  if (rumble_enabled_) {
    caps.vibration.left_motor_speed = caps.vibration.right_motor_speed = 65535;
  }
  *out = caps;
  return X_ERROR_SUCCESS;
}

X_RESULT HostInputDriver::GetState(uint32_t user, X_INPUT_STATE* out) {
  // Return raw input here, just like the upstream XInput driver. InputSystem
  // detects the settings chord BEFORE applying its active callback. Self-gating
  // this method would prevent the same chord from closing the settings menu.
  return gonk_skate3_input_poll(input_, user, 1, reinterpret_cast<uint8_t*>(out));
}

X_RESULT HostInputDriver::GetStateUi(uint32_t user, X_INPUT_STATE* out) {
  return GetState(user, out);
}

X_RESULT HostInputDriver::SetState(uint32_t user, X_INPUT_VIBRATION* vibration) {
  if (!vibration) return X_ERROR_BAD_ARGUMENTS;
  const auto status = gonk_skate3_input_poll(input_, user, 1, nullptr);
  if (status != X_ERROR_SUCCESS) return status;
  if (!rumble_enabled_) return X_ERROR_FUNCTION_FAILED;
  return gonk_skate3_input_set_rumble(input_, user, vibration->left_motor_speed,
                                    vibration->right_motor_speed);
}

X_RESULT HostInputDriver::GetKeystroke(uint32_t user, uint32_t,
                                      X_INPUT_KEYSTROKE* out) {
  if (!out) return X_ERROR_BAD_ARGUMENTS;
  const auto status = gonk_skate3_input_poll(input_, user == 0xFF ? 0 : user, 1, nullptr);
  // Gameplay reads full pad state. No fabricated UI keystroke events or repeats.
  return status == X_ERROR_SUCCESS ? X_ERROR_EMPTY : status;
}

std::unique_ptr<InputSystem> CreateHostInputSystem(GonkSkate3Input* input,
                                                  bool tool_mode, bool rumble_enabled) {
  auto system = std::make_unique<InputSystem>(nullptr);
  if (!tool_mode) {
    auto driver = std::make_unique<HostInputDriver>(input, rumble_enabled);
    if (driver->Setup() != X_STATUS_SUCCESS) throw std::invalid_argument("Null Skate host input");
    system->AddDriver(std::move(driver));
  }
  return system;
}

}  // namespace gonkskate::skate3
