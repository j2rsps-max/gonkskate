extends RefCounted
# Shared presentation. Optional Godot collision is used solely for editor picking.
const SCALE := 0.0254

static func point(v: Array) -> Vector3:
	return Vector3(v[0],v[1],v[2])*SCALE

static func material(color: Color) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.roughness = 0.85
	return result

static func line(parent: Node3D, a: Vector3, b: Vector3, color: Color, width := 0.06) -> void:
	if a.distance_to(b) < 0.0001:
		return
	var shape := BoxMesh.new()
	shape.size = Vector3(width,width,a.distance_to(b))
	var node := MeshInstance3D.new()
	node.mesh = shape
	node.material_override = material(color)
	node.position = (a+b)/2
	node.basis = Basis.looking_at(a-b,Vector3.RIGHT if absf((a-b).normalized().y)>0.99 else Vector3.UP)
	parent.add_child(node)

static func marker(parent: Node3D, at: Vector3, color: Color, radius := 0.12) -> void:
	var node := MeshInstance3D.new()
	var shape := SphereMesh.new()
	shape.radius = radius
	shape.height = radius*2
	node.mesh = shape
	node.material_override = material(color)
	node.position = at
	parent.add_child(node)

static func rails(parent: Node3D, values: Array, color := Color("f4bf60")) -> void:
	for rail in values:
		for i in range(rail["points"].size()-1):
			line(parent,point(rail["points"][i]),point(rail["points"][i+1]),color)

static func build(parent: Node3D, world: Dictionary, picking := false) -> MeshInstance3D:
	var shader := Shader.new()
	shader.code = "shader_type spatial; varying vec3 world; void vertex(){world=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;} void fragment(){vec2 d=abs(fract(world.xz/5.0+0.5)-0.5); float line=1.0-step(0.008,min(d.x,d.y)); float checker=mod(floor(world.x/5.0)+floor(world.z/5.0),2.0); ALBEDO=mix(vec3(0.22+checker*0.025),vec3(0.45,0.49,0.51),line); ROUGHNESS=0.95;}"
	var grid := ShaderMaterial.new()
	grid.shader = shader
	var floor_node := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(400,400)
	floor_node.mesh = plane
	floor_node.material_override = grid
	floor_node.visible = world["floor"]
	parent.add_child(floor_node)
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	for triangle in world["triangles"]:
		var v: Array = triangle["vertices"]
		var a := point(v[0])
		var b := point(v[1])
		var c := point(v[2])
		var n := (b-a).cross(c-a).normalized()
		# Godot front faces are clockwise. Native collision uses the source normals.
		vertices.append_array(PackedVector3Array([a,c,b]))
		normals.append_array(PackedVector3Array([n,n,n]))
	if not vertices.is_empty():
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = vertices
		arrays[Mesh.ARRAY_NORMAL] = normals
		var geometry := MeshInstance3D.new()
		var shape := ArrayMesh.new()
		shape.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		geometry.mesh = shape
		geometry.material_override = grid
		parent.add_child(geometry)
		if picking:
			var collision := ConcavePolygonShape3D.new()
			collision.set_faces(vertices)
			collision.backface_collision = true
			add_picker(parent,collision)
	if picking and world["floor"]:
		var collision := WorldBoundaryShape3D.new()
		collision.plane = Plane(Vector3.UP,0)
		add_picker(parent,collision)
	return floor_node

static func add_picker(parent: Node3D, shape: Shape3D) -> void:
	var body := StaticBody3D.new()
	var node := CollisionShape3D.new()
	node.shape = shape
	body.add_child(node)
	parent.add_child(body)

static func lighting(parent: Node3D) -> void:
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-45,-30,0)
	light.light_energy = 1.5
	light.shadow_enabled = true
	parent.add_child(light)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("7792ac")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("d2e3f4")
	env.environment.ambient_light_energy = 0.55
	parent.add_child(env)
