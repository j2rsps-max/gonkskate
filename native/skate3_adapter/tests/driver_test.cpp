#include "gonkskate_skate3_driver.h"
#include <rex/cvar.h>
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>

using namespace rex;
using namespace rex::input;
using gonkskate::skate3::CreateHostInputSystem;

namespace {
void expect(bool value, const char* message) {
  if (!value) { std::cerr << "SDK driver: " << message << '\n'; std::exit(1); }
}
bool neutral(const X_INPUT_GAMEPAD& pad) {
  const std::array<uint8_t, 12> zero{};
  return std::memcmp(&pad, zero.data(), zero.size()) == 0;
}
}  // namespace

void test_skate3_driver() {
  auto* input = gonk_skate3_input_create();
  expect(input, "mailbox allocation");
  {
    // Every InputSystem method uses its original SDK implementation.
    auto system = CreateHostInputSystem(input, false, true);
    expect(system->Setup() == X_STATUS_SUCCESS, "setup");
    X_INPUT_STATE state{};
    X_INPUT_CAPABILITIES caps{};
    expect(system->GetState(0, &state) == X_ERROR_DEVICE_NOT_CONNECTED, "starts disconnected");
    expect(system->GetCapabilities(0, 0, &caps) == X_ERROR_DEVICE_NOT_CONNECTED, "disconnected capabilities");
    GonkSkate3PadFrame frame{0, 1, 0.5f, -1, -1, 0.5f, 0.5f, 1};
    expect(gonk_skate3_input_submit(input, 1, &frame), "host submission");
    expect(system->GetCapabilities(0, X_INPUT_FLAG_GAMEPAD, &caps) == X_ERROR_SUCCESS,
           "connected gamepad capabilities");
    expect(caps.type == 1 && caps.sub_type == 1 &&
               uint16_t(caps.flags) == X_INPUT_CAPS_FFB_SUPPORTED &&
               uint16_t(caps.vibration.left_motor_speed) == 65535,
           "capabilities byte order and feedback support");
    expect(system->GetState(0, &state) == X_ERROR_SUCCESS, "SDK state poll");
    expect(uint16_t(state.gamepad.buttons) == X_INPUT_GAMEPAD_A &&
               int16_t(state.gamepad.thumb_lx) == 16384 &&
               int16_t(state.gamepad.thumb_ly) == 32767 &&
               int16_t(state.gamepad.thumb_rx) == -32768 &&
               int16_t(state.gamepad.thumb_ry) == -16384 &&
               state.gamepad.left_trigger == 128 && state.gamepad.right_trigger == 255,
           "host dual sticks and triggers through original SDK");
    auto held = state;
    for (int i = 0; i < 1000; ++i) {
      expect(system->GetState(0, &state) == X_ERROR_SUCCESS &&
                 std::memcmp(&state, &held, sizeof(state)) == 0,
             "SDK polls do not consume snapshots");
    }

    bool active = true;
    int menu_toggles = 0;
    expect(cvar::SetFlagByName("menu_chord", "rb+start"), "real SDK menu configuration");
    system->SetActiveCallback([&] { return active; });
    system->SetMenuChordCallback([&] { ++menu_toggles; active = !active; });
    frame.godot_buttons = (1u << 10) | (1u << 6);  // RB + Start
    expect(gonk_skate3_input_submit(input, 1, &frame), "menu chord submit");
    expect(system->GetState(0, &state) == X_ERROR_SUCCESS && !active && neutral(state.gamepad),
           "opening settings suppresses guest input on that poll");
    expect(menu_toggles == 1, "one menu edge");
    X_INPUT_GAMEPAD ui{};
    expect(system->GetUiGamepadState(&ui) &&
               uint16_t(ui.buttons) == (X_INPUT_GAMEPAD_RIGHT_SHOULDER | X_INPUT_GAMEPAD_START) &&
               int16_t(ui.thumb_rx) == -32768,
           "settings UI still receives raw pad state");
    expect(system->GetState(0, &state) == X_ERROR_SUCCESS && menu_toggles == 1,
           "held chord does not retrigger");
    frame.godot_buttons = 0;
    expect(gonk_skate3_input_submit(input, 1, &frame), "release menu chord");
    expect(system->GetState(0, &state) == X_ERROR_SUCCESS && neutral(state.gamepad), "UI gates axes too");
    frame.godot_buttons = (1u << 10) | (1u << 6);
    expect(gonk_skate3_input_submit(input, 1, &frame), "close chord submit");
    expect(system->GetState(0, &state) == X_ERROR_SUCCESS && active && menu_toggles == 2 &&
               uint16_t(state.gamepad.buttons) == (X_INPUT_GAMEPAD_RIGHT_SHOULDER | X_INPUT_GAMEPAD_START),
           "same controller chord can close settings and resume guest input");

    X_INPUT_VIBRATION vibration{};
    vibration.left_motor_speed = 0x1234;
    vibration.right_motor_speed = 0xABCD;
    expect(cvar::SetFlagByName("hid_rumble_enabled", "true"), "rumble on");
    expect(cvar::SetFlagByName("hid_rumble_min_motor_speed", "4096"), "SDK rumble threshold");
    expect(system->SetState(0, &vibration) == X_ERROR_SUCCESS, "guest vibration through SDK");
    GonkSkate3Rumble feedback{};
    expect(gonk_skate3_input_get_rumble(input, &feedback) == X_ERROR_SUCCESS &&
               feedback.left_motor == 0x1234 && feedback.right_motor == 0xABCD,
           "big endian guest speeds become host-order feedback");
    auto sequence = feedback.sequence;
    expect(system->SetState(0, &vibration) == X_ERROR_SUCCESS, "repeat vibration");
    expect(gonk_skate3_input_get_rumble(input, &feedback) == X_ERROR_SUCCESS && feedback.sequence == sequence,
           "unchanged request retains sequence");
    vibration.left_motor_speed = 0xFFF;
    expect(system->SetState(0, &vibration) == X_ERROR_SUCCESS, "threshold filter");
    expect(gonk_skate3_input_get_rumble(input, &feedback) == X_ERROR_SUCCESS && feedback.left_motor == 0,
           "SDK minimum motor threshold preserved");
    expect(cvar::SetFlagByName("hid_rumble_enabled", "false"), "rumble off");
    expect(system->SetState(0, &vibration) == X_ERROR_SUCCESS, "disabled rumble sends stop");
    expect(gonk_skate3_input_get_rumble(input, &feedback) == X_ERROR_SUCCESS &&
               feedback.left_motor == 0 && feedback.right_motor == 0,
           "SDK rumble toggle preserved");
    expect(cvar::SetFlagByName("hid_rumble_enabled", "true"), "restore rumble");
    vibration.left_motor_speed = 65535;
    expect(system->SetState(0, &vibration) == X_ERROR_SUCCESS, "rumble before disconnect");
    expect(gonk_skate3_input_submit(input, 0, nullptr), "disconnect");
    expect(gonk_skate3_input_get_rumble(input, &feedback) == X_ERROR_SUCCESS &&
               feedback.left_motor == 0 && feedback.right_motor == 0,
           "disconnect publishes stop motors");
    expect(system->GetState(0, &state) == X_ERROR_DEVICE_NOT_CONNECTED &&
               !system->GetUiGamepadState(&ui), "guest and UI see disconnect");
    expect(system->SetState(0, &vibration) == X_ERROR_DEVICE_NOT_CONNECTED, "no stale feedback while disconnected");
    expect(gonk_skate3_input_submit(input, 1, &frame), "reconnect");
    expect(system->GetState(1, &state) == X_ERROR_DEVICE_NOT_CONNECTED, "unsupported slot");
    X_INPUT_KEYSTROKE key{};
    expect(system->GetKeystroke(0xFF, 0, &key) == X_ERROR_EMPTY, "no fabricated any-user keystrokes");
    system->Shutdown();
    expect(system->GetState(0, &state) == X_ERROR_DEVICE_NOT_CONNECTED, "shutdown removes driver");
  }
  {
    auto system = CreateHostInputSystem(input);  // No host rumble transport.
    X_INPUT_CAPABILITIES caps{};
    expect(system->GetCapabilities(0, 0, &caps) == X_ERROR_SUCCESS &&
               uint16_t(caps.flags) == 0 && uint16_t(caps.vibration.left_motor_speed) == 0,
           "default driver does not promise hardware rumble");
    X_INPUT_VIBRATION vibration{};
    expect(system->SetState(0, &vibration) != X_ERROR_SUCCESS, "unsupported feedback is not silently accepted");
  }
  {
    auto tool = CreateHostInputSystem(input, true);
    expect(tool->GetState(0, nullptr) == X_ERROR_DEVICE_NOT_CONNECTED, "tool mode has no controller");
    gonkskate::skate3::HostInputDriver invalid(nullptr);
    expect(invalid.Setup() == X_STATUS_INVALID_PARAMETER, "invalid setup rejected");
  }
  gonk_skate3_input_destroy(input);
  std::cout << "SKATE3_DRIVER_TEST passed: original SDK InputSystem registration, dual sticks, "
               "settings open/close, raw UI, connection, capabilities, filtered rumble, shutdown\n";
}
