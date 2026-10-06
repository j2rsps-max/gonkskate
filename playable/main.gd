extends Node3D
# Presentation and input only. The separate THUG process owns every motion step.
const INCH_TO_METER := 0.0254
const WorldView = preload("res://world_view.gd")
var process: Dictionary = {}
var stream: FileAccess
var trace: FileAccess
var skater := Node3D.new()
var body := Node3D.new()
var camera := Camera3D.new()
var floor_mesh: MeshInstance3D
var hud := Label.new()
var status := Label.new()
var frame := 0
var autotest := false
var apex := 0.0
var landings := 0
var failed := false
var rail_frames := 0
var wants_reset := false
var controller = preload("res://controller_input.gd").new()
var controller_trace: FileAccess
var paused := false
var wants_pause := false
var area_test := false
var controller_test := false
var controller_ticks := 0
var trace_path := ""
var camera_yaw := 0.0
var camera_pitch := 0.0
var area: Dictionary
var spawn_y := 0.0
var recoveries := 0
var session_failures: Array = []
var retired_error_pipes: Array[FileAccess] = []
var lowest_surface := 0.0
var previous_state := -1
var previous_position := Vector3.ZERO
var pending_auto_reset := false
var metrics := {"frames":0,"landings":0,"rail_entries":0,"rail_frames":0,"resets":0,
	"automatic_fall_resets":0,"max_speed_kmh":0.0,"travel_meters":0.0,
	"ground_frames":0,"air_frames":0}
const CONTROLS := "W / ↑ push     A D / ← → steer     S / ↓ brake\nHold Space to crouch; release to ollie. E holds grind. R resets.\nEsc quits.\nController: X push, A ollie, Y grind. Start pauses; Back resets. Right stick looks."

func mesh(parent: Node3D, shape: Mesh, color: Color, at: Vector3) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.mesh = shape
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.82
	node.material_override = material
	node.position = at
	parent.add_child(node)
	return node

func box(parent: Node3D, size: Vector3, at: Vector3, color: Color) -> MeshInstance3D:
	var shape := BoxMesh.new()
	shape.size = size
	return mesh(parent, shape, color, at)

func _ready() -> void:
	controller_test = "--controller-autotest" in OS.get_cmdline_user_args()
	area_test = "--area-autotest" in OS.get_cmdline_user_args() or controller_test
	autotest = "--autotest" in OS.get_cmdline_user_args() or area_test
	var world_path := OS.get_environment("GONK_WORLD_JSON")
	if world_path.is_empty():
		world_path = "res://../worlds/test_area.json"
	var parsed_world = JSON.parse_string(FileAccess.get_file_as_string(world_path))
	if not parsed_world is Dictionary:
		stop_with_error("Cannot read the selected world. Run the playable launcher.")
		return
	area = parsed_world
	spawn_y = float(area.get("spawn",[0,0,0])[1])
	lowest_surface = spawn_y
	for triangle in area["triangles"]:
		for v in triangle["vertices"]:
			lowest_surface = minf(lowest_surface,v[1])
	add_child(skater)
	skater.add_child(body)
	box(skater, Vector3(0.23,0.035,0.81), Vector3(0,0.06,0), Color("ffb546"))
	for x in [-0.105, 0.105]:
		for z in [-0.24, 0.24]:
			var wheel := CylinderMesh.new()
			wheel.top_radius = 0.028
			wheel.bottom_radius = 0.028
			wheel.height = 0.025
			mesh(skater, wheel, Color("dde0e1"), Vector3(x,0.035,z)).rotation.z = PI/2
	box(body, Vector3(0.35,0.53,0.24), Vector3(0,1.18,0), Color("449cc5"))
	for x in [-0.11, 0.11]:
		box(body, Vector3(0.13,0.72,0.15), Vector3(x,0.59,0), Color("25394b"))
		box(body, Vector3(0.17,0.1,0.29), Vector3(x,0.17,0), Color("eff3f0"))
	for x in [-0.26, 0.26]:
		box(body, Vector3(0.13,0.48,0.14), Vector3(x,1.1,0), Color("bd8e73"))
	var head := SphereMesh.new()
	head.radius = 0.13
	head.height = 0.26
	mesh(body, head, Color("bd8e73"), Vector3(0,1.59,0))
	floor_mesh = WorldView.build(self,area)
	WorldView.rails(self,area["rails"])
	WorldView.lighting(self)
	camera.position = Vector3(0,3.4,-6)
	camera.current = true
	camera.far = 450
	add_child(camera)
	camera.look_at(Vector3(0,0.9,0))
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := Panel.new()
	panel.position = Vector2(22,20)
	panel.size = Vector2(700,250)
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color("263746")
	panel.add_theme_stylebox_override("panel",panel_style)
	layer.add_child(panel)
	hud.position = Vector2(38,32)
	hud.add_theme_font_size_override("font_size",22)
	layer.add_child(hud)
	status.position = Vector2(38,140)
	status.add_theme_font_size_override("font_size",15)
	status.text = CONTROLS
	if area["rails"].is_empty():
		status.text += "\nNo rail annotations yet. Add them in Map library → Map workshop."
	layer.add_child(status)
	start_native()

func start_native() -> void:
	frame = 0
	failed = false
	paused = false
	wants_reset = false
	previous_state = -1
	pending_auto_reset = false
	var logs := ProjectSettings.globalize_path("res://../logs")
	DirAccess.make_dir_recursive_absolute(logs)
	trace_path = logs.path_join("playable-%s-%d-segment%d.csv" % [Time.get_datetime_string_from_system().replace(":","-"),OS.get_process_id(),recoveries])
	var exe := OS.get_environment("GONK_THUG_EXE")
	if exe.is_empty():
		exe = ProjectSettings.globalize_path("res://../build/thug-headless/gonkskate-thug-test")
		if OS.get_name() == "Windows":
			exe = ProjectSettings.globalize_path("res://../build/thug-headless-windows/gonkskate-thug-test.exe")
	if not FileAccess.file_exists(exe):
		stop_with_error("Native executable missing. Run the playable launcher.\n" + exe)
		return
	var native_args := PackedStringArray(["--pipe"])
	var binary_world := OS.get_environment("GONK_WORLD_BINARY")
	if not binary_world.is_empty():
		native_args.append_array(PackedStringArray(["--world",binary_world]))
	process = OS.execute_with_pipe(exe, native_args, true)
	if process.is_empty():
		stop_with_error("Could not start the native THUG process.")
		return
	stream = process["stdio"]
	var header := stream.get_line()
	if not header.begins_with("frame,push,crouch"):
		stop_with_error("Native process did not provide a valid trace header.")
		return
	trace = FileAccess.open(trace_path,FileAccess.WRITE)
	if trace == null:
		stop_with_error("Cannot create the session trace: " + trace_path)
		return
	controller_trace = FileAccess.open(trace_path+".controller.jsonl",FileAccess.WRITE)
	if controller_trace == null:
		stop_with_error("Cannot create the controller trace.")
		return
	trace.store_line(header)
	print("Session trace: ",trace_path)

func pressed(key: Key) -> bool:
	return Input.is_physical_key_pressed(key)

func _physics_process(delta: float) -> void:
	if pressed(KEY_ESCAPE):
		get_tree().quit(0 if session_failures.is_empty() else 1)
		return
	if failed:
		var recovery: Dictionary = controller.actions(controller.read())
		if wants_reset or recovery["reset"]:
			recoveries += 1
			finish_native()
			start_native()
			if not failed:
				status.text = "Recovered at the selected spawn. The earlier failure stays in your results.\n" + CONTROLS
		return
	if stream == null:
		return
	var push := pressed(KEY_W) or pressed(KEY_UP)
	var crouch := pressed(KEY_SPACE)
	var left := pressed(KEY_A) or pressed(KEY_LEFT)
	var right := pressed(KEY_D) or pressed(KEY_RIGHT)
	var grind := pressed(KEY_E)
	var brake := pressed(KEY_S) or pressed(KEY_DOWN)
	if controller_test:
		# Exercise Godot joypad events and real mapping, without a physical device.
		for action in ["push","crouch","grind","pause"]:
			var event := InputEventJoypadButton.new()
			event.device = 7
			event.button_index = int(controller.config["thug_buttons"][action])
			event.pressed = (action=="push" and frame>=30) or (action=="crouch" and frame>=150 and frame<165) or (action=="grind" and frame>=165) or (action=="pause" and controller_ticks in [70,75])
			Input.parse_input_event(event)
		for axis in [JOY_AXIS_RIGHT_X,JOY_AXIS_RIGHT_Y]:
			var motion := InputEventJoypadMotion.new()
			motion.device = 7
			motion.axis = axis
			motion.axis_value = 0.7 if axis==JOY_AXIS_RIGHT_X and frame>=40 and frame<100 else 0.5 if axis==JOY_AXIS_RIGHT_Y and frame>=100 and frame<120 else 0.0
			Input.parse_input_event(motion)
		Input.flush_buffered_events()
		controller_ticks += 1
	var snapshot: Dictionary = controller.read([7] if controller_test else null)
	var pad: Dictionary = controller.actions(snapshot)
	if not autotest or controller_test:
		if snapshot["disconnected"]:
			paused = true
		if pad["pause"] or wants_pause:
			paused = not paused
		wants_pause = false
		if paused:
			hud.text = "GONKSKATE / PAUSED — Start or Enter to resume"
			return
		push = push or pad["push"]
		grind = grind or pad["grind"]
		crouch = crouch or pad["crouch"]
		left = left or pad["left"]
		right = right or pad["right"]
		brake = brake or pad["brake"]
		wants_reset = wants_reset or pad["reset"]
	if autotest and not controller_test:
		push = frame>=30
		crouch = frame>=150 and frame<165
		left = false
		right = false
		brake = false
		grind = area_test and frame>=165
	var ls: Vector2 = snapshot["left_stick"]
	var rs: Vector2 = snapshot["right_stick"]
	var raw_ls: Vector2 = snapshot["left_stick_raw"]
	var raw_rs: Vector2 = snapshot["right_stick_raw"]
	controller_trace.store_line(JSON.stringify({"frame":frame,"device":snapshot["device"],"buttons":snapshot["buttons"],"left_stick":[ls.x,ls.y],"right_stick":[rs.x,rs.y],"left_stick_raw":[raw_ls.x,raw_ls.y],"right_stick_raw":[raw_rs.x,raw_rs.y],"left_trigger":snapshot["left_trigger"],"right_trigger":snapshot["right_trigger"]}))
	controller_trace.flush()
	var reset_this_tick := wants_reset
	var auto_reset_this_tick := reset_this_tick and pending_auto_reset
	stream.store_line("%d %d %d %d %d %d %d" % [int(push),int(crouch),int(left),int(right),int(brake),int(grind),int(reset_this_tick)])
	wants_reset = false
	pending_auto_reset = false
	stream.flush()
	var line := stream.get_line()
	var fields := line.split(",")
	if fields.size()!=27 or not fields[0].is_valid_int() or int(fields[0])!=frame:
		print("Native pipe failure: io_error=",stream.get_error()," child_exit=",OS.get_process_exit_code(int(process["pid"]))," reply=",line)
		stop_with_error("Native process stopped at frame %d. See session logs." % frame)
		return
	trace.store_line(line)
	trace.flush()
	var position_inches := Vector3(float(fields[6]),float(fields[7]),float(fields[8]))
	var state := int(fields[15])
	var velocity := Vector3(float(fields[9]),float(fields[10]),float(fields[11]))
	metrics["frames"] += 1
	metrics["landings"] += int(fields[18])
	metrics["rail_frames"] += int(state==4)
	metrics["rail_entries"] += int(state==4 and previous_state!=4)
	metrics["ground_frames"] += int(state==0)
	metrics["air_frames"] += int(state==1)
	metrics["resets"] += int(reset_this_tick)
	metrics["automatic_fall_resets"] += int(auto_reset_this_tick)
	metrics["max_speed_kmh"] = maxf(metrics["max_speed_kmh"],velocity.length()*INCH_TO_METER*3.6)
	if previous_state>=0 and not reset_this_tick:
		metrics["travel_meters"] += position_inches.distance_to(previous_position)*INCH_TO_METER
	previous_position = position_inches
	previous_state = state
	if not area["floor"] and position_inches.y<lowest_surface-600 and not autotest:
		# Ask the original core's Reset path on the next tick. Do not teleport
		# the presentation independently or add a fabricated landing.
		wants_reset = true
		pending_auto_reset = true
	skater.position = position_inches*INCH_TO_METER
	apex = maxf(apex,position_inches.y-spawn_y)
	landings += int(fields[18])
	var forward := Vector3(float(fields[12]),float(fields[13]),float(fields[14])).normalized()
	var up := Vector3(float(fields[24]),float(fields[25]),float(fields[26])).normalized()
	skater.basis = Basis(up.cross(forward).normalized(),up,forward)
	if int(fields[15])==4:
		rail_frames += 1
	body.position.y = -0.3 if crouch else 0.0
	floor_mesh.position = Vector3(roundf(skater.position.x/100)*100,0,roundf(skater.position.z/100)*100)
	camera_yaw += -rs.x*delta*1.8
	camera_pitch = clampf(camera_pitch-rs.y*delta*1.2,-0.4,0.7)
	var camera_back := (-forward).rotated(Vector3.UP,camera_yaw)
	var camera_target := skater.position+camera_back*6+Vector3.UP*(3.4+camera_pitch*3)
	camera.position = camera_target if reset_this_tick or frame==0 else camera.position.lerp(camera_target,1-exp(-6*delta))
	camera.look_at(skater.position+Vector3.UP*0.95)
	hud.text = "GONKSKATE  /  %s\nTHUG  ·  %s   %.1f km/h   frame %d\nLandings %d   Grinds %d   Rail time %.1f s" % [area.get("name","Test area"),"RAIL" if state==4 else ("AIR" if state==1 else "GROUND"),velocity.length()*INCH_TO_METER*3.6,frame,metrics["landings"],metrics["rail_entries"],metrics["rail_frames"]/60.0]
	frame += 1
	if frame==185 and "--screenshot" in OS.get_cmdline_user_args():
		capture_preview()
	if autotest and frame==360:
		if landings!=1 or apex<60 or apex>66 or (area_test and rail_frames<40):
			stop_with_error("Scene integration failed: apex=%f landings=%d" % [apex,landings])
		else:
			if controller_test and (controller_ticks!=365 or absf(camera_yaw)<0.3 or absf(camera_pitch)<0.1):
				stop_with_error("Controller pause/resume or right-stick camera check failed")
				return
			print("PLAYABLE_AUTOTEST passed: 360 native ticks, one ollie and landing, rail ticks=",rail_frames,", apex=",apex)
			get_tree().quit()

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.physical_keycode==KEY_ENTER and event.pressed and not event.echo:
		wants_pause = true
	if event is InputEventKey and event.physical_keycode==KEY_R and event.pressed and not event.echo:
		wants_reset = true

func capture_preview() -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../logs/playable-preview.png"))
	get_tree().quit()

func stop_with_error(message: String) -> void:
	failed = true
	session_failures.append({"frame":frame,"segment":recoveries,"message":message})
	push_error(message)
	status.text = message + "\nBack/View or R restarts at spawn. Escape finishes and saves results."
	if autotest:
		get_tree().quit(1)

func finish_native() -> void:
	if controller_trace != null:
		controller_trace.close()
		controller_trace = null
	if trace != null:
		trace.close()
		trace = null
	if not process.is_empty():
		if stream != null:
			stream.close()
		# The child exits on stdin EOF. Save its complete peripheral-call report.
		var errors: FileAccess = process["stderr"]
		var report := FileAccess.open(trace_path + ".adapters.log",FileAccess.WRITE)
		while true:
			var line := errors.get_line()
			if line.is_empty():
				break
			if report != null and not line.is_empty():
				report.store_line(line)
		if OS.get_name() == "Windows":
			errors.close()
		else:
			# Godot 4.4.1 OS_Unix opens stderr with write fd 0, so closing
			# that FileAccess closes parent stdin and breaks the next child.
			# Retain its EOF pipe until this window exits; no private physics changes.
			retired_error_pipes.append(errors)
		if report != null:
			report.close()
	process = {}
	stream = null

func _exit_tree() -> void:
	finish_native()
	for errors in retired_error_pipes:
		errors.close()
	retired_error_pipes.clear()
	var result_path := OS.get_environment("GONK_SCENE_RESULT")
	if not result_path.is_empty():
		var result := FileAccess.open(result_path,FileAccess.WRITE)
		if result != null:
			result.store_string(JSON.stringify({"failed":not session_failures.is_empty(),"failures":session_failures,"recoveries":recoveries,"last_segment_frames":frame,"metrics":metrics}))
			result.close()
