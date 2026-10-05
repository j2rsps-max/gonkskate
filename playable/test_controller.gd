extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok:
		push_error(message)
		failures += 1
func _initialize() -> void:
	var input = preload("res://controller_input.gd").new()
	check(input.stick(float(input.config["stick_deadzone"])*0.3,-float(input.config["stick_deadzone"])*0.3)==Vector2.ZERO,"small drift must be neutral")
	check(input.stick(1,0)==Vector2.RIGHT,"full stick must preserve full range")
	check(is_equal_approx(input.stick((1+float(input.config["stick_deadzone"]))/2,0).x,0.5),"deadzone must rescale analog magnitude")
	check(is_equal_approx(input.stick(1,1).length(),1),"diagonal magnitude must be bounded")
	var bindings: Dictionary = input.config["thug_buttons"]
	var snapshot := {"buttons":(1<<int(bindings["crouch"]))|(1<<int(bindings["push"]))|(1<<int(bindings["grind"])),"left_stick":Vector2(-1,1)}
	var actions: Dictionary = input.actions(snapshot)
	check(actions["push"] and actions["crouch"] and actions["grind"] and actions["left"] and actions["brake"],"THUG face/stick mapping")
	snapshot["buttons"] = (1<<int(bindings["pause"]))|(1<<int(bindings["reset"]))
	actions = input.actions(snapshot)
	check(actions["pause"] and actions["reset"],"pause/reset first edge")
	actions = input.actions(snapshot)
	check(not actions["pause"] and not actions["reset"],"held buttons must not repeat pause/reset")
	input.config["thug_buttons"]["push"] = JOY_BUTTON_B
	snapshot["buttons"] = 1<<JOY_BUTTON_B
	check(input.actions(snapshot)["push"],"remapped binding must be applied")
	var raw_axis: float = (1+float(input.config["stick_deadzone"]))/2
	for axis in [JOY_AXIS_LEFT_X,JOY_AXIS_RIGHT_Y,JOY_AXIS_TRIGGER_LEFT,JOY_AXIS_TRIGGER_RIGHT]:
		var event := InputEventJoypadMotion.new()
		event.device = 7
		event.axis = axis
		event.axis_value = raw_axis if axis<4 else 0.6
		Input.parse_input_event(event)
	Input.flush_buffered_events()
	var reading: Dictionary = input.read([7])
	check(reading["device"]==7,"connected pad selection")
	check(is_equal_approx(reading["left_stick"].x,0.5) and is_equal_approx(reading["right_stick"].y,0.5),"both independent sticks must be retained")
	check(is_equal_approx(reading["left_stick_raw"].x,raw_axis) and is_equal_approx(reading["right_stick_raw"].y,raw_axis),"raw axes must be retained before deadzone filtering")
	check(is_equal_approx(reading["left_trigger"],0.6) and is_equal_approx(reading["right_trigger"],0.6),"both independent triggers must be retained")
	reading = input.read([])
	check(reading["disconnected"] and reading["device"]==-1 and reading["buttons"]==0 and reading["left_stick"]==Vector2.ZERO,"disconnect must clear stale controls")
	if failures==0:
		print("CONTROLLER_TEST passed: mappings, edges, deadzone, dual sticks/triggers, connection and disconnect")
	quit(1 if failures else 0)
