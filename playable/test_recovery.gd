extends SceneTree
# Fault injection against the real native process, never used by normal play.
class TestController extends "res://controller_input.gd":
	func read(_connected_ids = null) -> Dictionary:
		return super.read([7])

func _initialize() -> void:
	call_deferred("run")

func require(ok: bool, message: String) -> bool:
	if not ok:
		push_error(message)
		quit(1)
	return ok

func run() -> void:
	var scene = load("res://main.tscn").instantiate()
	scene.controller = TestController.new()
	root.add_child(scene)
	scene.set_physics_process(false)
	for i in range(20):
		scene._physics_process(1.0/60)
	if not require(scene.frame == 20 and not scene.failed,"Initial real-core process did not run"):
		return
	OS.kill(int(scene.process["pid"]))
	await create_timer(0.1).timeout
	scene._physics_process(1.0/60)
	if not require(scene.failed,"Native death was not detected"):
		return
	var back := InputEventJoypadButton.new()
	back.device = 7
	back.button_index = int(scene.controller.config["thug_buttons"]["reset"])
	back.pressed = true
	Input.parse_input_event(back)
	Input.flush_buffered_events()
	scene._physics_process(1.0/60)
	if not require(not scene.failed and scene.recoveries == 1,"Controller Back did not recover"):
		return
	var release := back.duplicate()
	release.pressed = false
	Input.parse_input_event(release)
	Input.flush_buffered_events()
	for i in range(20):
		scene._physics_process(1.0/60)
	if not require(scene.frame == 20,"Recovered process did not simulate"):
		return
	OS.kill(int(scene.process["pid"]))
	await create_timer(0.1).timeout
	scene._physics_process(1.0/60)
	var reset := InputEventKey.new()
	reset.physical_keycode = KEY_R
	reset.pressed = true
	scene._unhandled_key_input(reset)
	scene._physics_process(1.0/60)
	if not require(not scene.failed and scene.recoveries == 2,"Keyboard R did not recover"):
		return
	for i in range(10):
		scene._physics_process(1.0/60)
	scene.queue_free()
	await process_frame
	var report = JSON.parse_string(FileAccess.get_file_as_string(OS.get_environment("GONK_SCENE_RESULT")))
	if not require(report != null and report["failed"] and report["recoveries"] == 2 and report["failures"].size() == 2,"Recovered failures were lost from health report"):
		return
	print("RECOVERY_TEST passed: real child death, controller Back, keyboard R, resumed native ticks and retained failures")
	quit()
