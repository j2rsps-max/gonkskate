extends Node3D
# Presentation and input only. The separate THUG process owns every motion step.
const INCH_TO_METER := 0.0254
var process: Dictionary = {}
var stream: FileAccess
var trace: FileAccess
var skater := Node3D.new()
var body := Node3D.new()
var camera := Camera3D.new()
var floor_mesh := MeshInstance3D.new()
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
	var plane := PlaneMesh.new()
	plane.size = Vector2(400,400)
	floor_mesh.mesh = plane
	var shader := Shader.new()
	shader.code = "shader_type spatial; varying vec3 world; void vertex(){world=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;} void fragment(){vec2 d=abs(fract(world.xz/5.0+0.5)-0.5); float line=1.0-step(0.008,min(d.x,d.y)); float checker=mod(floor(world.x/5.0)+floor(world.z/5.0),2.0); ALBEDO=mix(vec3(0.22+checker*0.025),vec3(0.45,0.49,0.51),line); ROUGHNESS=0.95;}"
	var floor_material := ShaderMaterial.new()
	floor_material.shader = shader
	floor_mesh.material_override = floor_material
	add_child(floor_mesh)
	var area: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../worlds/test_area.json"))
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	for triangle in area["triangles"]:
		var v: Array = triangle["vertices"]
		var a := Vector3(v[0][0],v[0][1],v[0][2])*INCH_TO_METER
		var b := Vector3(v[1][0],v[1][1],v[1][2])*INCH_TO_METER
		var c := Vector3(v[2][0],v[2][1],v[2][2])*INCH_TO_METER
		var n := (b-a).cross(c-a).normalized()
		# Godot's front-face winding is clockwise; physics normals remain explicit.
		vertices.append_array(PackedVector3Array([a,c,b]))
		normals.append_array(PackedVector3Array([n,n,n]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	var ramp := ArrayMesh.new()
	ramp.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	mesh(self,ramp,Color("9ca89b"),Vector3.ZERO)
	for rail in area["rails"]:
		var start: Array = rail["points"][0]
		var end: Array = rail["points"][1]
		var a := Vector3(start[0],start[1],start[2])*INCH_TO_METER
		var b := Vector3(end[0],end[1],end[2])*INCH_TO_METER
		var bar := box(self,Vector3(0.06,0.06,a.distance_to(b)),(a+b)/2,Color("f4bf60"))
		bar.basis = Basis.looking_at(a-b)
		for point in [a,b]:
			box(self,Vector3(0.04,point.y,0.04),Vector3(point.x,point.y/2,point.z),Color("8a969e"))
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-45,-30,0)
	light.light_energy = 1.5
	light.shadow_enabled = true
	add_child(light)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("7792ac")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("d2e3f4")
	env.environment.ambient_light_energy = 0.55
	add_child(env)
	camera.position = Vector3(0,3.4,-6)
	camera.current = true
	camera.far = 450
	add_child(camera)
	camera.look_at(Vector3(0,0.9,0))
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := Panel.new()
	panel.position = Vector2(22,20)
	panel.size = Vector2(625,190)
	layer.add_child(panel)
	hud.position = Vector2(38,32)
	hud.add_theme_font_size_override("font_size",22)
	layer.add_child(hud)
	status.position = Vector2(38,110)
	status.add_theme_font_size_override("font_size",15)
	status.text = "W / ↑ push     A D / ← → steer     S / ↓ brake\nHold Space to crouch; release to ollie. E holds grind. R resets.
Ramp is beside the rail; rail is straight ahead. Esc quits.\nController: X push, A ollie, Y grind. Start pauses; Back resets. Right stick looks."
	layer.add_child(status)
	var exe := OS.get_environment("GONK_THUG_EXE")
	if exe.is_empty():
		exe = ProjectSettings.globalize_path("res://../build/thug-headless/gonkskate-thug-test")
		if OS.get_name() == "Windows":
			exe = ProjectSettings.globalize_path("res://../build/thug-headless-windows/gonkskate-thug-test.exe")
	if not FileAccess.file_exists(exe):
		stop_with_error("Native executable missing. Run the playable launcher.\n" + exe)
		return
	process = OS.execute_with_pipe(exe, ["--pipe"], true)
	if process.is_empty():
		stop_with_error("Could not start the native THUG process.")
		return
	stream = process["stdio"]
	var header := stream.get_line()
	if not header.begins_with("frame,push,crouch"):
		stop_with_error("Native process did not provide a valid trace header.")
		return
	var logs := ProjectSettings.globalize_path("res://../logs")
	DirAccess.make_dir_recursive_absolute(logs)
	trace_path = logs.path_join("playable-%s.csv" % Time.get_datetime_string_from_system().replace(":","-"))
	trace = FileAccess.open(trace_path,FileAccess.WRITE)
	if trace == null:
		stop_with_error("Cannot create the session trace: " + trace_path)
		return
	controller_trace = FileAccess.open(trace_path+".controller.jsonl",FileAccess.WRITE)
	trace.store_line(header)
	print("Session trace: ",trace_path)

func pressed(key: Key) -> bool:
	return Input.is_physical_key_pressed(key)

func _physics_process(delta: float) -> void:
	if failed or stream == null:
		return
	if pressed(KEY_ESCAPE):
		get_tree().quit()
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
	stream.store_line("%d %d %d %d %d %d %d" % [int(push),int(crouch),int(left),int(right),int(brake),int(grind),int(wants_reset)])
	wants_reset = false
	stream.flush()
	var line := stream.get_line()
	var fields := line.split(",")
	if fields.size()!=27 or not fields[0].is_valid_int() or int(fields[0])!=frame:
		stop_with_error("Native process stopped at frame %d. See session logs." % frame)
		return
	trace.store_line(line)
	trace.flush()
	var position_inches := Vector3(float(fields[6]),float(fields[7]),float(fields[8]))
	skater.position = position_inches*INCH_TO_METER
	apex = maxf(apex,position_inches.y)
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
	camera.position = camera.position.lerp(skater.position+camera_back*6+Vector3.UP*(3.4+camera_pitch*3),1-exp(-6*delta))
	camera.look_at(skater.position+Vector3.UP*0.95)
	var velocity := Vector3(float(fields[9]),float(fields[10]),float(fields[11]))
	hud.text = "GONKSKATE  /  THUG test area\n%s   %.1f km/h   frame %d\n" % ["RAIL" if int(fields[15])==4 else ("AIR" if int(fields[15])==1 else "GROUND"),velocity.length()*INCH_TO_METER*3.6,frame]
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
	push_error(message)
	status.text = message
	if autotest:
		get_tree().quit(1)

func _exit_tree() -> void:
	if controller_trace != null:
		controller_trace.close()
	if trace != null:
		trace.close()
	if not process.is_empty():
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
		errors.close()
		if report != null:
			report.close()
