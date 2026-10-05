extends Control
# Live input diagnostics only; this scene never runs skating physics.
var controller = preload("res://controller_input.gd").new()
var readings := Label.new()
var buttons := Label.new()
var trace: FileAccess
var frame := 0
var test_mode := false
var trace_path := ""
func _ready() -> void:
	test_mode = "--lab-autotest" in OS.get_cmdline_user_args()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var background := ColorRect.new()
	background.color = Color("132434")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var title := Label.new()
	title.position = Vector2(45,30)
	title.add_theme_font_size_override("font_size",30)
	title.text = "GONKSKATE  /  CONTROLLER LAB"
	add_child(title)
	var help := Label.new()
	help.position = Vector2(45,85)
	help.add_theme_font_size_override("font_size",18)
	help.text = "Skate 3 input preparation — no Skate gameplay is running.\nCircle BOTH sticks, squeeze LT/RT separately and together, press every button.\nDisconnect/reconnect once. Press Esc when finished; return the results ZIP."
	add_child(help)
	readings.position = Vector2(45,190)
	readings.add_theme_font_size_override("font_size",22)
	add_child(readings)
	buttons.position = Vector2(45,390)
	buttons.add_theme_font_size_override("font_size",18)
	add_child(buttons)
	var logs := ProjectSettings.globalize_path("res://../logs")
	DirAccess.make_dir_recursive_absolute(logs)
	trace_path = OS.get_environment("GONK_CONTROLLER_LAB_TRACE")
	if trace_path.is_empty():
		trace_path = logs.path_join("controller-lab-%s-%d.jsonl" % [Time.get_datetime_string_from_system().replace(":","-"),OS.get_process_id()])
	trace = FileAccess.open(trace_path,FileAccess.WRITE)
	if trace==null:
		push_error("Cannot create controller lab trace")
		get_tree().quit(1)
	print("Controller lab trace: ",trace_path)
func _physics_process(_delta: float) -> void:
	if trace==null:
		return
	if Input.is_physical_key_pressed(KEY_ESCAPE):
		get_tree().quit()
		return
	if test_mode:
		for axis in [JOY_AXIS_LEFT_X,JOY_AXIS_LEFT_Y,JOY_AXIS_RIGHT_X,JOY_AXIS_RIGHT_Y,JOY_AXIS_TRIGGER_LEFT,JOY_AXIS_TRIGGER_RIGHT]:
			var event := InputEventJoypadMotion.new()
			event.device = 7
			event.axis = axis
			event.axis_value = sin(float(frame+axis*15)/20.0) if axis<4 else float((frame+axis*15)%60)/59.0
			Input.parse_input_event(event)
		for button in range(15):
			var event := InputEventJoypadButton.new()
			event.device = 7
			event.button_index = button
			event.pressed = frame%15==button
			Input.parse_input_event(event)
		Input.flush_buffered_events()
	var s: Dictionary = controller.read([7] if test_mode and (frame<90 or frame>=100) else [] if test_mode else null)
	var ls: Vector2 = s["left_stick_raw"]
	var rs: Vector2 = s["right_stick_raw"]
	var left: Vector2 = s["left_stick"]
	var right: Vector2 = s["right_stick"]
	var name := "No controller connected" if int(s["device"])<0 else Input.get_joy_name(s["device"])
	readings.text = "Device: %s   |   sample %d\nLeft stick  raw (%+.3f, %+.3f)   filtered (%+.3f, %+.3f)\nRight stick raw (%+.3f, %+.3f)   filtered (%+.3f, %+.3f)\nLT %.3f    RT %.3f\nButton mask: 0x%08X   |   Deadzone: %.2f" % [name,frame,ls.x,ls.y,left.x,left.y,rs.x,rs.y,right.x,right.y,s["left_trigger"],s["right_trigger"],s["buttons"],controller.config["stick_deadzone"]]
	var held := PackedStringArray()
	for button in range(15):
		if int(s["buttons"])&(1<<button):
			held.append(str(button))
	buttons.text = "Held Godot button IDs: " + ", ".join(held) + "\n\nRaw stick Y: up is negative; the Skate guest packet flips Y.\nBoth raw and filtered values are saved. Physical device mappings still need testing."
	trace.store_line(JSON.stringify({"frame":frame,"device":s["device"],"device_name":name,"buttons":s["buttons"],"left_stick_raw":[ls.x,ls.y],"right_stick_raw":[rs.x,rs.y],"left_stick":[left.x,left.y],"right_stick":[right.x,right.y],"left_trigger":s["left_trigger"],"right_trigger":s["right_trigger"],"disconnected":s["disconnected"]}))
	trace.flush()
	frame += 1
	if test_mode and frame==180:
		print("CONTROLLER_LAB_AUTOTEST passed: 180 samples with dual sticks/triggers, all standard buttons and reconnect")
		get_tree().quit()
func _exit_tree() -> void:
	if trace!=null:
		trace.close()
