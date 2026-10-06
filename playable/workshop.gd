extends Node3D
# This is a world-authoring tool. Gameplay always runs in the authentic THUG process.
const View = preload("res://world_view.gd")
var world: Dictionary
var edited_rails: Array = []
var spawn: Array
var facing: Array
var pending: Array = []
var history: Array = []
var camera := Camera3D.new()
var overlay := Node3D.new()
var cursor := Node3D.new()
var panel := PanelContainer.new()
var rail_list := ItemList.new()
var mode := OptionButton.new()
var offset := SpinBox.new()
var snap := CheckBox.new()
var name_entry := LineEdit.new()
var status := Label.new()
var save_button: Button
var finish_button: Button
var undo_button: Button
var pick: Dictionary = {}
var controller = preload("res://controller_input.gd").new()
var previous_buttons := 0
var speed := 8.0
var saved := false
var dirty := false
var failed := false

func _ready() -> void:
	world = JSON.parse_string(FileAccess.get_file_as_string(OS.get_environment("GONK_WORLD_JSON")))
	if world.is_empty():
		failed = true
		get_tree().quit(1)
		return
	edited_rails = world["rails"].duplicate(true)
	spawn = world["spawn"].duplicate()
	facing = world["facing"].duplicate()
	View.build(self,world,true)
	View.lighting(self)
	add_child(overlay)
	add_child(cursor)
	View.marker(cursor,Vector3.ZERO,Color("7ce8d5"),0.08)
	camera.current = true
	camera.far = 800
	add_child(camera)
	home()
	build_ui()
	redraw()

func add_button(parent: Control, text: String, action: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.pressed.connect(action)
	parent.add_child(button)
	return button

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	layer.add_child(panel)
	panel.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	panel.offset_left = 16
	panel.offset_right = 350
	panel.offset_top = 16
	panel.offset_bottom = -16
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color("1d2a38")
	panel.add_theme_stylebox_override("panel",panel_style)
	var margin := MarginContainer.new()
	for key in ["margin_left","margin_right","margin_top","margin_bottom"]:
		margin.add_theme_constant_override(key,12)
	panel.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation",9)
	margin.add_child(column)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(scroll)
	var layout := VBoxContainer.new()
	layout.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	layout.add_theme_constant_override("separation",9)
	scroll.add_child(layout)
	var title := Label.new()
	title.text = "GONKSKATE / Map workshop"
	title.add_theme_font_size_override("font_size",20)
	layout.add_child(title)
	name_entry.text = str(world.get("name","Area")).left(85)+" · edited"
	name_entry.max_length = 100
	layout.add_child(name_entry)
	mode.add_item("Place rail points")
	mode.add_item("Set spawn on flat surface")
	layout.add_child(mode)
	var row := HBoxContainer.new()
	layout.add_child(row)
	var label := Label.new()
	label.text = "Rail height (inches)"
	row.add_child(label)
	offset.min_value = -120
	offset.max_value = 240
	offset.value = 24
	offset.step = 1
	row.add_child(offset)
	snap.text = "Snap to nearby mesh vertices (0.3 m)"
	snap.button_pressed = true
	layout.add_child(snap)
	finish_button = add_button(layout,"Finish rail / Enter",finish_rail)
	undo_button = add_button(layout,"Undo / Z",undo)
	add_button(layout,"Add short test rail ahead",quick_rail)
	rail_list.custom_minimum_size = Vector2(0,110)
	layout.add_child(rail_list)
	add_button(layout,"Remove selected rail",remove_rail)
	add_button(layout,"View spawn / Home",home)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.custom_minimum_size = Vector2(300,58)
	status.text = "Click the scenery to mark points. Set height to 0 when tracing the top of an existing rail."
	layout.add_child(status)
	var controls := Label.new()
	controls.text = "WASD fly · Q/E down/up · Shift faster\nHold right mouse to look · wheel: speed\nLeft click places · Enter finishes · Z undo\nPad: left stick moves, right stick looks\nLT/RT down/up · A places at screen center\nX finishes · Y undo · Start saves\nBack/Escape returns without saving"
	controls.add_theme_font_size_override("font_size",13)
	layout.add_child(controls)
	save_button = add_button(column,"Save copy and test with THUG",save_copy)
	add_button(column,"Cancel",cancel)
	var notice := Label.new()
	notice.text = "Rails are your annotations. Original game rails\nare not extracted. The source map is preserved."
	notice.add_theme_font_size_override("font_size",12)
	column.add_child(notice)

func home() -> void:
	var target := View.point(spawn)+Vector3.UP
	camera.position = target-Vector3(facing[0],0,facing[2])*9+Vector3.UP*7
	camera.look_at(target)

func checkpoint() -> void:
	history.append({"rails":edited_rails.duplicate(true),"spawn":spawn.duplicate(),
		"facing":facing.duplicate(),"pending":pending.duplicate(true)})
	if history.size()>100:
		history.pop_front()
	dirty = true

func redraw() -> void:
	for child in overlay.get_children():
		child.free()
	View.rails(overlay,edited_rails)
	if pending.size()>1:
		View.rails(overlay,[{"points":pending}],Color("7ce8d5"))
	for value in pending:
		View.marker(overlay,View.point(value),Color("7ce8d5"))
	var at := View.point(spawn)
	View.marker(overlay,at+Vector3.UP*0.15,Color("68a8ff"),0.16)
	View.line(overlay,at+Vector3.UP*0.1,at+Vector3(facing[0],0,facing[2])*1.5+Vector3.UP*0.1,Color("68a8ff"),0.1)
	rail_list.clear()
	for i in range(edited_rails.size()):
		rail_list.add_item("Rail %d · %d points" % [i+1,edited_rails[i]["points"].size()])
	finish_button.disabled = pending.size()<2
	undo_button.disabled = history.is_empty()

func pick_ray(origin: Vector3, direction: Vector3) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(origin,origin+direction*800)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty() and snap.button_pressed and mode.selected==0:
		var closest: Vector3 = hit["position"]
		var distance := 0.3
		var face := int(hit.get("face_index",-1))
		if face>=0 and face<world["triangles"].size():
			var triangle: Dictionary = world["triangles"][face]
			for v in triangle["vertices"]:
				var vertex := View.point(v)
				var d := vertex.distance_to(hit["position"])
				if d<distance:
					closest = vertex
					distance = d
		hit["position"] = closest
	return hit

func place_hit(hit: Dictionary) -> void:
	if hit.is_empty():
		status.text = "Aim at a collision surface before placing a point."
		return
	var at: Vector3 = hit["position"]/View.SCALE
	if mode.selected==1:
		var normal: Vector3 = hit["normal"]
		if normal.y<0.98:
			status.text = "Choose a flat upward surface for the first-test spawn."
			return
		checkpoint()
		spawn = [at.x,at.y,at.z]
		var forward := -camera.global_basis.z
		forward.y = 0
		if forward.length()>0.001:
			forward = forward.normalized()
			facing = [forward.x,0,forward.z]
		status.text = "Spawn set. The blue arrow follows your viewing direction."
	else:
		at.y += offset.value
		var value := [at.x,at.y,at.z]
		if not pending.is_empty() and at.distance_to(Vector3(pending[-1][0],pending[-1][1],pending[-1][2]))<0.1:
			status.text = "Choose a different point; rail segments need length."
			return
		checkpoint()
		pending.append(value)
		status.text = "%d rail points. Continue along a ledge, or press Enter to finish." % pending.size()
	redraw()

func finish_rail() -> void:
	if pending.size()<2:
		return
	checkpoint()
	edited_rails.append({"points":pending.duplicate(true),"terrain":3})
	pending.clear()
	status.text = "Rail saved in this draft. Ollie near it and hold Y / E in the THUG test."
	redraw()

func quick_rail() -> void:
	if not pending.is_empty():
		status.text = "Finish or undo the current rail before adding the test line."
		return
	checkpoint()
	var points: Array = []
	for distance in [540,780]:
		points.append([spawn[0]+facing[0]*distance,spawn[1]+24,spawn[2]+facing[2]*distance])
	edited_rails.append({"points":points,"terrain":3})
	status.text = "Test rail added 14 m ahead, 24 inches high. Check that it has clear flat ground below."
	redraw()

func remove_rail() -> void:
	var selected := rail_list.get_selected_items()
	if selected.is_empty():
		return
	checkpoint()
	edited_rails.remove_at(selected[0])
	redraw()

func undo() -> void:
	if history.is_empty():
		return
	var previous: Dictionary = history.pop_back()
	edited_rails = previous["rails"]
	spawn = previous["spawn"]
	facing = previous["facing"]
	pending = previous["pending"]
	status.text = "Last edit undone."
	redraw()

func save_copy() -> void:
	if not pending.is_empty():
		status.text = "Finish this rail or undo its points before saving."
		return
	if name_entry.text.strip_edges().is_empty():
		status.text = "Give the new map copy a name."
		return
	var path := OS.get_environment("GONK_WORKSHOP_PATCH")
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file==null:
		status.text = "Cannot save the draft. Check available disk space."
		failed = true
		return
	file.store_string(JSON.stringify({"schema_version":1,"source_sha256":OS.get_environment("GONK_WORLD_SHA"),
		"name":name_entry.text,"spawn":spawn,"facing":facing,"rails":edited_rails}))
	file.close()
	saved = true
	get_tree().quit()

func cancel() -> void:
	get_tree().quit()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index==MOUSE_BUTTON_RIGHT:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
		if event.pressed and event.button_index==MOUSE_BUTTON_LEFT:
			place_hit(pick_ray(camera.project_ray_origin(event.position),camera.project_ray_normal(event.position)))
		if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			speed = clampf(speed*(1.2 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.0/1.2),1,80)
	if event is InputEventMouseMotion and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		look(event.relative*0.003)
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_ESCAPE: cancel()
			KEY_ENTER: finish_rail()
			KEY_Z: undo()
			KEY_HOME: home()

func look(value: Vector2) -> void:
	camera.rotation.y -= value.x
	camera.rotation.x = clampf(camera.rotation.x-value.y,-1.5,1.5)

func pad_tick(snapshot: Dictionary, delta: float) -> void:
	var buttons: int = snapshot["buttons"]
	var edges := buttons & ~previous_buttons
	previous_buttons = buttons
	var left: Vector2 = snapshot["left_stick"]
	var right: Vector2 = snapshot["right_stick"]
	look(right*delta*2)
	var forward := -camera.basis.z
	forward.y = 0
	forward = forward.normalized()
	var horizontal := camera.basis.x
	camera.position += (horizontal*left.x-forward*left.y+Vector3.UP*(snapshot["right_trigger"]-snapshot["left_trigger"]))*speed*delta
	if edges & (1<<JOY_BUTTON_A):
		var center := get_viewport().get_visible_rect().size/2
		place_hit(pick_ray(camera.project_ray_origin(center),camera.project_ray_normal(center)))
	if edges & (1<<JOY_BUTTON_X): finish_rail()
	if edges & (1<<JOY_BUTTON_Y): undo()
	if edges & (1<<JOY_BUTTON_START): save_copy()
	if edges & (1<<JOY_BUTTON_BACK): cancel()

func _physics_process(delta: float) -> void:
	if failed: return
	var focus := get_viewport().gui_get_focus_owner()
	if not focus is LineEdit:
		var motion := Vector3.ZERO
		motion.x = float(Input.is_physical_key_pressed(KEY_D))-float(Input.is_physical_key_pressed(KEY_A))
		motion.z = float(Input.is_physical_key_pressed(KEY_S))-float(Input.is_physical_key_pressed(KEY_W))
		motion.y = float(Input.is_physical_key_pressed(KEY_E))-float(Input.is_physical_key_pressed(KEY_Q))
		var horizontal := camera.basis * Vector3(motion.x,0,motion.z)
		camera.position += (horizontal+Vector3.UP*motion.y)*speed*delta*(3 if Input.is_physical_key_pressed(KEY_SHIFT) else 1)
	pad_tick(controller.read(),delta)
	var screen := get_viewport().get_mouse_position()
	if controller.device>=0 or Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		screen = get_viewport().get_visible_rect().size/2
	pick = pick_ray(camera.project_ray_origin(screen),camera.project_ray_normal(screen))
	cursor.visible = not pick.is_empty()
	if cursor.visible:
		cursor.position = pick["position"]+Vector3.UP*(offset.value*View.SCALE if mode.selected==0 else 0.05)

func _exit_tree() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var path := OS.get_environment("GONK_WORKSHOP_RESULT")
	if not path.is_empty():
		var file := FileAccess.open(path,FileAccess.WRITE)
		if file!=null:
			file.store_string(JSON.stringify({"saved":saved,"failed":failed,"rails":edited_rails.size(),
				"pending_points":pending.size(),"changed":dirty}))
			file.close()
