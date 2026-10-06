extends SceneTree
# Validate embedded decoded character textures through Godot's actual GLTF path.

var failed := false
func check(value: bool, message: String) -> void:
	if not value:
		push_error(message)
		failed = true

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 5:
		quit(2)
		return
	var state := GLTFState.new()
	var document := GLTFDocument.new()
	GLTFDocument.register_gltf_document_extension(GLTFDocumentExtensionConvertImporterMesh.new())
	check(document.append_from_file(args[0], state) == OK, "Actual GLTF importer rejected textured character")
	if failed:
		quit(1)
		return
	var scene := document.generate_scene(state)
	root.add_child(scene)
	var meshes := scene.find_children("*", "MeshInstance3D", true, false)
	check(meshes.size() == 1, "Expected one textured mesh")
	if failed:
		quit(1)
		return
	var geometry := meshes[0] as MeshInstance3D
	var material := geometry.mesh.surface_get_material(0) as StandardMaterial3D
	check(material != null and material.albedo_texture != null, "First-pass texture did not bind to the imported material")
	var image := material.albedo_texture.get_image()
	check(image != null and image.get_width() == int(args[1]) and image.get_height() == int(args[2]), "Imported texture dimensions changed")
	var expected := args[3].split(",")
	var wanted := Color(float(expected[0]) / 255.0, float(expected[1]) / 255.0, float(expected[2]) / 255.0, float(expected[3]) / 255.0)
	var max_error := 0.0
	for y in range(image.get_height()):
		for x in range(image.get_width()):
			var actual := image.get_pixel(x, y)
			max_error = maxf(max_error, maxf(maxf(absf(actual.r-wanted.r), absf(actual.g-wanted.g)),
				maxf(absf(actual.b-wanted.b), absf(actual.a-wanted.a))))
	check(max_error <= 1.0 / 255.0 + 0.00001, "Decoded texture pixels changed in the actual engine importer")
	var report := {"passed": not failed, "actual_texture_import": "PASS" if not failed else "FAIL",
		"width": image.get_width(), "height": image.get_height(), "maximum_channel_error": max_error,
		"material_texture_bound": material != null and material.albedo_texture != null,
		"retail_texture_validated": false}
	var file := FileAccess.open(args[4], FileAccess.WRITE)
	check(file != null, "Cannot write texture validation report")
	if file != null:
		file.store_string(JSON.stringify(report, "\t") + "\n")
		file.close()
	print(JSON.stringify(report))
	quit(1 if failed else 0)
