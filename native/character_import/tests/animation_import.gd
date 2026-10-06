extends SceneTree
# Actual GLTF AnimationPlayer playback against source-derived expected bone
# transforms and skinned vertices. A format test, not a second game frontend.

var failed := false

func check(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failed = true

func matrix(values: Array) -> Transform3D:
	return Transform3D(Basis(Vector3(values[0], values[4], values[8]),
		Vector3(values[1], values[5], values[9]), Vector3(values[2], values[6], values[10])),
		Vector3(values[3], values[7], values[11]))

func matrix_error(a: Transform3D, b: Transform3D) -> float:
	var error := a.origin.distance_to(b.origin)
	for axis in range(3):
		error = maxf(error, a.basis[axis].distance_to(b.basis[axis]))
	return error

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 3:
		quit(2)
		return
	var expectation: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[1]))
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	GLTFDocument.register_gltf_document_extension(GLTFDocumentExtensionConvertImporterMesh.new())
	if document.append_from_file(args[0], state) != OK:
		quit(1)
		return
	var scene := document.generate_scene(state, 60.0)
	root.add_child(scene)
	var skeletons := scene.find_children("*", "Skeleton3D", true, false)
	var players := scene.find_children("*", "AnimationPlayer", true, false)
	var meshes := scene.find_children("*", "MeshInstance3D", true, false)
	check(skeletons.size() == 1 and players.size() == 1 and meshes.size() == 1, "Animated scene lost its skeleton, mesh or actual AnimationPlayer")
	if failed:
		quit(1)
		return
	var skeleton := skeletons[0] as Skeleton3D
	var player := players[0] as AnimationPlayer
	var geometry := meshes[0] as MeshInstance3D
	var names := player.get_animation_list()
	check(names.size() == 1, "Expected exactly one imported original clip")
	if failed:
		quit(1)
		return
	player.play(names[0])
	var max_pose_error := 0.0
	var max_vertex_error := 0.0
	var maximum_movement := 0.0
	var reference_vertices := []
	var sampled_vertices := 0
	var sample_errors := []
	for pose in expectation["samples"]:
		player.seek(float(pose["time"]), true)
		player.advance(0.0)
		var pose_error := 0.0
		for bone in range(skeleton.get_bone_count()):
			var expected := matrix(pose["global_bone_matrices"][bone])
			pose_error = maxf(pose_error, matrix_error(skeleton.get_bone_global_pose(bone), expected))
		max_pose_error = maxf(max_pose_error, pose_error)
		sample_errors.append({"time": pose["time"], "held_source_time": pose["held_source_time"], "maximum_bone_error": pose_error})
		var vertex_index := 0
		for surface in range(geometry.mesh.get_surface_count()):
			var arrays := geometry.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var joints: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
			var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
			for index in range(vertices.size()):
				var actual := Vector3.ZERO
				var expected := Vector3.ZERO
				for influence in range(4):
					var weight := weights[index * 4 + influence]
					if weight > 0:
						var bind := joints[index * 4 + influence]
						var bone := geometry.skin.get_bind_bone(bind)
						if bone < 0:
							bone = skeleton.find_bone(geometry.skin.get_bind_name(bind))
						check(bone >= 0, "Cannot resolve an animated skin binding")
						if bone >= 0:
							var inverse := matrix(expectation["inverse_bind_matrices"][bone])
							actual += (skeleton.get_bone_global_pose(bone) * geometry.skin.get_bind_pose(bind) * vertices[index]) * weight
							expected += (matrix(pose["global_bone_matrices"][bone]) * inverse * vertices[index]) * weight
				max_vertex_error = maxf(max_vertex_error, actual.distance_to(expected))
				if reference_vertices.size() <= vertex_index:
					reference_vertices.append(actual)
				else:
					maximum_movement = maxf(maximum_movement, actual.distance_to(reference_vertices[vertex_index]))
				vertex_index += 1
				sampled_vertices += 1
	check(max_pose_error < 0.00003, "Playback pose diverges from the original bone-local sampling/parent composition")
	check(max_vertex_error < 0.0001, "Actual animation playback deforms vertices differently from the source-derived pose")
	check(maximum_movement > 0.01, "Imported clip did not animate the actual weighted mesh")
	var report := {"passed": not failed, "actual_animation_playback": "PASS" if not failed else "FAIL",
		"bones": skeleton.get_bone_count(), "sampled_times": expectation["samples"].size(),
		"sampled_vertices": sampled_vertices, "maximum_bone_transform_error": max_pose_error,
		"maximum_skinned_vertex_error_meters": max_vertex_error, "maximum_animated_movement_meters": maximum_movement,
		"animation_tracks": player.get_animation(names[0]).get_track_count(), "retail_animation_validated": false}
	report["samples"] = sample_errors
	var file := FileAccess.open(args[2], FileAccess.WRITE)
	check(file != null, "Cannot write animation validation report")
	if file != null:
		file.store_string(JSON.stringify(report, "\t") + "\n")
		file.close()
	print(JSON.stringify(report))
	scene.queue_free()
	quit(1 if failed else 0)
