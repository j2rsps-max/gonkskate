extends SceneTree
var editor: Node3D
var failures: Array = []

func expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)
		push_error(description)

func key(code: Key) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = true
	editor._unhandled_input(event)

func pad(buttons := 0, left := Vector2.ZERO, right := Vector2.ZERO, trigger := 0.0) -> Dictionary:
	return {"buttons":buttons,"left_stick":left,"right_stick":right,"left_trigger":0.0,"right_trigger":trigger}

func _initialize() -> void:
	# Custom SceneTree scripts do not initialize the main-scene window size.
	root.size = Vector2i(1280,720)
	root.content_scale_size = Vector2i(1280,720)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	call_deferred("run")

func run() -> void:
	editor = load("res://workshop.gd").new()
	root.add_child(editor)
	editor.set_physics_process(false)
	await physics_frame
	await physics_frame
	var height: float = editor.spawn[1]*0.0254
	var hit: Dictionary = editor.pick_ray(Vector3(0,height+8,0),Vector3.DOWN)
	expect(not hit.is_empty() and absf(hit["position"].y-height)<0.0001,"Finite imported-floor picking")
	var corner := Vector3(-3600,120,-6000)*0.0254
	var snapped: Dictionary = editor.pick_ray(corner+Vector3(0.1,8,0.1),Vector3.DOWN)
	expect(not snapped.is_empty() and snapped["position"].distance_to(corner)<0.0001,"Picked-face vertex snapping")
	editor.place_hit(hit)
	var second: Dictionary = editor.pick_ray(Vector3(0,height+8,5),Vector3.DOWN)
	editor.place_hit(second)
	expect(editor.pending.size()==2 and absf(editor.pending[0][1]-144)<0.001,"Two points and inch height offset")
	editor.finish_button.pressed.emit()
	expect(editor.edited_rails.size()==1 and editor.pending.is_empty(),"Finish chain through UI button")
	key(KEY_Z)
	expect(editor.edited_rails.is_empty() and editor.pending.size()==2,"Undo restores unfinished chain")
	editor.undo(); editor.undo(); editor.undo()
	expect(editor.pending.is_empty(),"Undo individual placement")
	editor.mode.selected = 1
	var previous_spawn: Array = editor.spawn.duplicate()
	editor.place_hit({"position":Vector3(0,height,0),"normal":Vector3.RIGHT})
	expect(editor.spawn==previous_spawn,"Reject wall spawn")
	editor.place_hit(second)
	expect(absf(editor.spawn[2]-5/0.0254)<0.001,"Spawn surface selection")
	editor.undo()
	expect(editor.spawn==previous_spawn,"Spawn undo")
	editor.mode.selected = 0
	# Use controller selection at the viewport center, then a second viewing point.
	editor.camera.position = Vector3(0,height+8,0)
	editor.camera.rotation = Vector3(-PI/2,0,0)
	editor.pad_tick(pad(1<<JOY_BUTTON_A),1.0/60)
	editor.pad_tick(pad(),1.0/60)
	editor.camera.position.z = 5
	editor.pad_tick(pad(1<<JOY_BUTTON_A),1.0/60)
	expect(editor.pending.size()==2,"Controller A places both ray hits")
	editor.pad_tick(pad(1<<JOY_BUTTON_X),1.0/60)
	expect(editor.edited_rails.size()==1,"Controller X finishes rail")
	editor.pad_tick(pad(1<<JOY_BUTTON_Y),1.0/60)
	expect(editor.edited_rails.is_empty() and editor.pending.size()==2,"Controller Y undo")
	for i in range(3): editor.undo()
	var old_position: Vector3 = editor.camera.position
	var old_rotation: Vector3 = editor.camera.rotation
	editor.pad_tick(pad(0,Vector2(0.7,-0.4),Vector2(0.6,0.2),0.8),0.1)
	expect(editor.camera.position.distance_to(old_position)>0.2 and editor.camera.rotation!=old_rotation,"Controller sticks and trigger camera navigation")
	editor.quick_rail()
	expect(editor.edited_rails.size()==1 and editor.edited_rails[0]["points"]==[[0.0,144.0,540.0],[0.0,144.0,780.0]],"Short approach rail authored relative to spawn")
	editor.rail_list.select(0)
	editor.remove_rail()
	expect(editor.edited_rails.is_empty(),"Remove selected rail")
	editor.undo_button.pressed.emit()
	expect(editor.edited_rails.size()==1,"Undo removed rail")
	editor.name_entry.text = "Workshop rail regression"
	await process_frame
	await process_frame
	print("WORKSHOP_UI bounds: viewport=",root.get_visible_rect().size," save=",editor.save_button.get_global_rect())
	expect(editor.save_button.get_global_rect().end.y<=root.get_visible_rect().size.y,"Save button remains visible in 720p window")
	if failures.is_empty():
		print("WORKSHOP_TEST passed: floor/vertex picking, spawn, rail chains, undo, removal, controller navigation and saving")
		if "--screenshot" in OS.get_cmdline_user_args():
			editor.home()
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../logs/workshop-preview.png"))
		editor.save_button.pressed.emit()
	else:
		quit(1)
	editor.free()
	editor = null
