extends SceneTree
# Test the exported GLB through Godot's actual GLTF importer. This is a
# character-format fixture, not a second frontend or a playable character.

var failed := false

func check(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failed = true

func deform(skeleton: Skeleton3D, skin: Skin, vertex: Vector3, joints: PackedInt32Array, weights: PackedFloat32Array, offset: int) -> Vector3:
	var value := Vector3.ZERO
	for influence in range(4):
		var weight := weights[offset + influence]
		if weight > 0.0:
			var bind_index := joints[offset + influence]
			var bone := skin.get_bind_bone(bind_index)
			# The actual importer may use named binds instead of integer binds.
			if bone < 0:
				bone = skeleton.find_bone(skin.get_bind_name(bind_index))
			check(bone >= 0, "Imported skin bind could not resolve its bone")
			if bone >= 0:
				value += (skeleton.get_bone_global_pose(bone) * skin.get_bind_pose(bind_index) * vertex) * weight
	return value

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 3:
		push_error("Pass GLB path, output report path and expected bone count")
		quit(2)
		return
	var state := GLTFState.new()
	var document := GLTFDocument.new()
	GLTFDocument.register_gltf_document_extension(GLTFDocumentExtensionConvertImporterMesh.new())
	var result := document.append_from_file(arguments[0], state)
	check(result == OK, "Actual GLTFDocument failed to parse the character")
	if result != OK:
		quit(1)
		return
	var scene := document.generate_scene(state)
	root.add_child(scene)
	var skeletons := scene.find_children("*", "Skeleton3D", true, false)
	var meshes := scene.find_children("*", "MeshInstance3D", true, false)
	check(skeletons.size() == 1 and meshes.size() == 1, "Expected one imported skeleton and one skinned mesh")
	if skeletons.size() != 1 or meshes.size() != 1:
		scene.print_tree_pretty()
		print("Found skeletons: ", skeletons.size(), "; meshes: ", meshes.size(), "; root class: ", scene.get_class())
		quit(1)
		return
	var skeleton := skeletons[0] as Skeleton3D
	var geometry := meshes[0] as MeshInstance3D
	check(skeleton.get_bone_count() == int(arguments[2]), "Skeleton lost source bones")
	check(geometry.skin != null and geometry.skin.get_bind_count() == int(arguments[2]), "GLB inverse-bind skin was not imported")
	check(skeleton.find_bone("bone_00000014") >= 0, "Source checksum bone identity was lost")
	var max_rest_error := 0.0
	var max_posed_movement := 0.0
	var vertex_count := 0
	var index_count := 0
	var held_vertex_error := 0.0
	var maximum_vertex_length := 0.0
	var maximum_imported_weight_sum_error := 0.0
	for surface in range(geometry.mesh.get_surface_count()):
		var arrays := geometry.mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var joints: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
		var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
		check(joints.size() == vertices.size() * 4 and weights.size() == joints.size(), "Actual importer lost influence streams")
		vertex_count += vertices.size()
		index_count += arrays[Mesh.ARRAY_INDEX].size()
		skeleton.reset_bone_poses()
		for index in range(vertices.size()):
			maximum_vertex_length = maxf(maximum_vertex_length, vertices[index].length())
			var weight_sum := 0.0
			for influence in range(4):
				var weight := weights[index * 4 + influence]
				# Godot's imported ArrayMesh quantizes weights to UNORM16.
				check(absf(weight * 65535.0 - roundf(weight * 65535.0)) < 0.005, "Expected actual importer weight quantization")
				weight_sum += weight
			maximum_imported_weight_sum_error = maxf(maximum_imported_weight_sum_error, absf(1.0 - weight_sum))
			var error := deform(skeleton, geometry.skin, vertices[index], joints, weights, index * 4).distance_to(vertices[index])
			max_rest_error = maxf(max_rest_error, error)
		var child := skeleton.find_bone("bone_00000014")
		skeleton.set_bone_pose_rotation(child, Quaternion(Vector3.FORWARD, PI / 2.0))
		for index in range(vertices.size()):
			var movement := deform(skeleton, geometry.skin, vertices[index], joints, weights, index * 4).distance_to(vertices[index])
			max_posed_movement = maxf(max_posed_movement, movement)
			if vertices[index].length() < 0.000001:
				held_vertex_error = maxf(held_vertex_error, movement)
	var quantization_bound := maximum_vertex_length * 4.0 / 65535.0 + 0.000001
	check(maximum_imported_weight_sum_error < 4.0 / 65535.0, "Actual importer weight sum exceeds UNORM16 rounding bounds")
	check(max_rest_error < quantization_bound, "Neutral skinning changed the imported shape beyond actual importer weight rounding")
	check(max_posed_movement > 0.1, "Changing a real imported bone did not deform its influenced vertices")
	check(held_vertex_error < 0.00001, "Child-bone movement incorrectly moved the root-only vertex")
	check(index_count == geometry.mesh.get_surface_count() * 6, "Triangle conversion was lost on actual import")
	var report := {"passed": not failed, "actual_glb_import": "PASS" if not failed else "FAIL",
		"bones": skeleton.get_bone_count(), "skin_binds": geometry.skin.get_bind_count(),
		"vertices": vertex_count, "indices": index_count, "surfaces": geometry.mesh.get_surface_count(),
		"maximum_neutral_pose_error_meters": max_rest_error, "maximum_posed_movement_meters": max_posed_movement,
		"importer_weight_storage": "UNORM16", "neutral_pose_quantization_bound_meters": quantization_bound,
		"maximum_imported_weight_sum_error": maximum_imported_weight_sum_error,
		"root_only_vertex_error_meters": held_vertex_error, "retail_character_validated": false}
	var output := FileAccess.open(arguments[1], FileAccess.WRITE)
	check(output != null, "Cannot write import validation report")
	if output != null:
		output.store_string(JSON.stringify(report, "\t") + "\n")
		output.close()
	print(JSON.stringify(report))
	scene.queue_free()
	quit(1 if failed else 0)
