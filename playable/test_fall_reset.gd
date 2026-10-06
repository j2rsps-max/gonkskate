extends SceneTree
var failures: Array = []

class TestController extends "res://controller_input.gd":
	func read(_connected: Variant = null) -> Dictionary:
		var result := super.read([])
		result["buttons"] = 1<<int(config["thug_buttons"]["push"])
		return result

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var scene: Node3D = load("res://main.gd").new()
	scene.controller = TestController.new()
	root.add_child(scene)
	scene.set_physics_process(false)
	for i in range(400):
		scene._physics_process(1.0/60)
		if scene.failed:
			push_error("Native failed during fall-reset test")
			scene.free()
			quit(1)
			return
	var metrics: Dictionary = scene.metrics
	var passed: bool = metrics["frames"]==400 and metrics["automatic_fall_resets"]>=2 and metrics["resets"]==metrics["automatic_fall_resets"] and metrics["landings"]==0 and metrics["rail_frames"]==0 and metrics["max_speed_kmh"]>20 and metrics["travel_meters"]>10
	print("FALL_RESET_TEST ","passed" if passed else "FAILED",": ",JSON.stringify(metrics))
	scene.free()
	quit(0 if passed else 1)
