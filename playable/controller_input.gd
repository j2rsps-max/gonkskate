extends RefCounted
# Device readings stay independent of the selected gameplay backend.
var config: Dictionary
var previous_buttons := 0
var device := -1

func _init() -> void:
	config = JSON.parse_string(FileAccess.get_file_as_string("res://controller_bindings.json"))
	assert(config["schema_version"]==1)
	assert(float(config["stick_deadzone"])>=0 and float(config["stick_deadzone"])<1)
	for key in ["direction_threshold","brake_threshold"]:
		assert(float(config[key])>=0 and float(config[key])<1)
	for button in config["thug_buttons"].values():
		assert(int(button)>=0 and int(button)<32)

func stick(x: float, y: float) -> Vector2:
	var v := Vector2(x,y).limit_length(1.0)
	var deadzone: float = config["stick_deadzone"]
	if v.length()<=deadzone:
		return Vector2.ZERO
	return v.normalized()*(v.length()-deadzone)/(1.0-deadzone)

func actions(snapshot: Dictionary) -> Dictionary:
	var buttons: int = snapshot["buttons"]
	var bindings: Dictionary = config["thug_buttons"]
	var result := {}
	for action in bindings:
		var mask: int = 1<<int(bindings[action])
		result[action] = (buttons&mask)!=0
		if action in ["pause","reset"]:
			result[action] = result[action] and (previous_buttons&mask)==0
	previous_buttons = buttons
	var left: Vector2 = snapshot["left_stick"]
	result["left"] = left.x < -float(config["direction_threshold"])
	result["right"] = left.x > float(config["direction_threshold"])
	result["brake"] = left.y > float(config["brake_threshold"])
	result["left"] = result["left"] or (buttons&(1<<JOY_BUTTON_DPAD_LEFT))!=0
	result["right"] = result["right"] or (buttons&(1<<JOY_BUTTON_DPAD_RIGHT))!=0
	result["brake"] = result["brake"] or (buttons&(1<<JOY_BUTTON_DPAD_DOWN))!=0
	return result

func read(connected: Variant = null) -> Dictionary:
	# Discovery can be supplied by deterministic tests; normal play polls Godot.
	var devices: Array = Input.get_connected_joypads() if connected==null else connected
	var disconnected := device>=0 and not devices.has(device)
	if not devices.has(device):
		device = -1 if devices.is_empty() else devices[0]
		previous_buttons = 0
	var buttons := 0
	if device>=0:
		for button in range(mini(JOY_BUTTON_MAX,32)):
			if Input.is_joy_button_pressed(device,button):
				buttons |= 1<<button
	var snapshot := {"device":device,"disconnected":disconnected,"buttons":buttons,
		"left_stick":Vector2.ZERO,"right_stick":Vector2.ZERO,"left_stick_raw":Vector2.ZERO,"right_stick_raw":Vector2.ZERO,"left_trigger":0.0,"right_trigger":0.0}
	if device>=0:
		snapshot["left_stick_raw"] = Vector2(Input.get_joy_axis(device,JOY_AXIS_LEFT_X),Input.get_joy_axis(device,JOY_AXIS_LEFT_Y))
		snapshot["left_stick"] = stick(snapshot["left_stick_raw"].x,snapshot["left_stick_raw"].y)
		snapshot["right_stick_raw"] = Vector2(Input.get_joy_axis(device,JOY_AXIS_RIGHT_X),Input.get_joy_axis(device,JOY_AXIS_RIGHT_Y))
		snapshot["right_stick"] = stick(snapshot["right_stick_raw"].x,snapshot["right_stick_raw"].y)
		snapshot["left_trigger"] = clampf(Input.get_joy_axis(device,JOY_AXIS_TRIGGER_LEFT),0,1)
		snapshot["right_trigger"] = clampf(Input.get_joy_axis(device,JOY_AXIS_TRIGGER_RIGHT),0,1)
	return snapshot
