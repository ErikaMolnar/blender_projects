import bpy
import math
import random
import numpy as np


def purge_orphans():
    """
    Remove all orphan data blocks
    """
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def delete_materials():
    obj = bpy.data.objects['textured']
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select the object and make it active
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Loop through the object's material slots and clear them
    for i in range(len(obj.data.materials)):
        bpy.context.object.active_material_index = 0
        bpy.ops.object.material_slot_remove()


def delete_nodes():
    obj = bpy.data.objects['textured']
    for modifier in obj.modifiers:
        if modifier.type == 'NODES':
            obj.modifiers.remove(modifier)
    

def clean_scene():
    """
    Removing all of the objects, collection, materials, particles,
    textures, images, curves, meshes, actions, nodes, and worlds from the scene
    """
    # make sure the active object is not in Edit Mode
    if bpy.context.active_object and bpy.context.active_object.mode == "EDIT":
        bpy.ops.object.editmode_toggle()

    # Deselect all objects first
    bpy.ops.object.select_all(action='DESELECT')
    
    # make sure non of the objects are hidden from the viewport, selection, or disabled
    for obj in bpy.data.objects:
        if obj.name != 'textured':
            print(obj)
            obj.hide_set(False)
            obj.hide_select = False
            obj.hide_viewport = False
            obj.select_set(True)

    # select all the object and delete them
    bpy.ops.object.delete()

    delete_materials()
    delete_nodes()

    # in the case when you modify the world shader
    # delete and recreate the world object
    world_names = [world.name for world in bpy.data.worlds]
    for name in world_names:
        bpy.data.worlds.remove(bpy.data.worlds[name])
    # create a new world data block
    bpy.ops.world.new()
    bpy.context.scene.world = bpy.data.worlds["World"]

    purge_orphans()


def render_loop():
    bpy.ops.render.render(animation=True)


def save_as_mp4(name="golden_loop"):
    project_name = name
    bpy.context.scene.render.image_settings.file_format = "FFMPEG"
    bpy.context.scene.render.ffmpeg.format = "MPEG4"
    bpy.context.scene.render.filepath = f"/<path>/Disolve/render/disolve_anim.mp4"


def set_environment(frame_count, fps=30):
    # Set up sframe information
    scene = bpy.context.scene
    scene.frame_end = frame_count - 540
    scene.render.fps = fps
    scene.frame_current = 1
    scene.frame_start = 1
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1920
    
    scene.render.engine = "CYCLES"

    # Use the GPU to render
    scene.cycles.device = "GPU"
    scene.cycles.samples = 1024

    scene.view_settings.look = "AgX - Very High Contrast"
    
    # set the world background to black
    world = bpy.data.worlds["World"]
    if "Background" in world.node_tree.nodes:
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.02, 0.01, 1)


def make_active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def track_empty(obj):
    bpy.ops.object.empty_add(location=(0,0,30), type="PLAIN_AXES", align="WORLD")
    empty = bpy.context.active_object
    empty.name = f"empty.tracker-target.{obj.name}"

    make_active(obj)
    bpy.ops.object.constraint_add(type="TRACK_TO")
    bpy.context.object.constraints["Track To"].target = empty

    return empty


def set_camera(loc, rot):
    bpy.ops.object.camera_add(location=loc, rotation=rot)
    camera = bpy.context.active_object

    # set the camera as "active"
    bpy.context.scene.camera = camera

    # set focal lenght
    camera.data.lens = 70

    camera.data.passepartout_alpha = 0.9


def create_mesh_sand_shader(obj):
    make_active(obj)
    mat = bpy.data.materials.new(name="SandMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    # Create a Principled BSDF shader node 
    sand_shader = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    sand_shader.inputs["Base Color"].default_value = (0.8, 0.7, 0.5, 1.0)
    sand_shader.location = (0, 0)
    
    noise_texture = mat.node_tree.nodes.new(type="ShaderNodeTexNoise")
    noise_texture.inputs["Scale"].default_value = 150
    noise_texture.inputs["Detail"].default_value = 15
    noise_texture.inputs["Roughness"].default_value = 0.8
    noise_texture.location = (-400, 0)
    
    node_mapping = mat.node_tree.nodes.new(type="ShaderNodeMapping")
    node_mapping.location = (-600, 0)
    
    node_tex_coord = mat.node_tree.nodes.new(type="ShaderNodeTexCoord")
    node_tex_coord.location = (-800, 0)
    
    node_bump = mat.node_tree.nodes.new(type="ShaderNodeBump")
    node_bump.inputs["Strength"].default_value = 0.1
    node_bump.location = (-200, 40)

    # Create a Material Output
    material_output = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    material_output.location = (250, 0)

    # Link the Principled BSDF node to the Material Output
    mat.node_tree.links.new(noise_texture.outputs["Fac"], node_bump.inputs["Height"])
    mat.node_tree.links.new(node_bump.outputs["Normal"], sand_shader.inputs["Normal"])
    mat.node_tree.links.new(node_tex_coord.outputs["Generated"], node_mapping.inputs["Vector"])
    mat.node_tree.links.new(node_mapping.outputs["Vector"], noise_texture.inputs["Vector"])
    mat.node_tree.links.new(sand_shader.outputs["BSDF"], material_output.inputs["Surface"])

    obj.data.materials.append(mat)


def create_empty_sphere():
    empty_sphere = bpy.ops.object.empty_add(type='SPHERE', align='WORLD',
                                            location=(-0.75, 0, 3), scale=(0.9, 0.9, 0.9))
    empty_sphere = bpy.context.object
    empty_sphere.name = 'Disolve_sphere'
    
    return empty_sphere


def create_disolve_effect(mesh):
    # Add a Geometry Nodes modifier to the base sphere
    sphere = create_empty_sphere()
    mod = mesh.modifiers.new(name="GeometryNodes", type='NODES')
    node_tree = bpy.data.node_groups.new(name="DisolveNodes", type='GeometryNodeTree')
    mod.node_group = node_tree

    # Create Group Input and Output nodes
    group_input = node_tree.nodes.new(type='NodeGroupInput')
    node_tree.interface.new_socket('Mesh', in_out='INPUT', socket_type='NodeSocketGeometry')
    node_tree.interface.new_socket('Object', in_out='INPUT', socket_type='NodeSocketObject')
    node_tree.interface.new_socket('Value', in_out='INPUT', socket_type='NodeSocketFloat')
    node_tree.interface.new_socket('Material', in_out='INPUT', socket_type='NodeSocketMaterial')
    group_input.location = (-200, 0)
    
    # Create MeshBoolean
    mesh_boolean = node_tree.nodes.new(type='GeometryNodeMeshBoolean')
    mesh_boolean.inputs['Hole Tolerant']. default_value = True
    mesh_boolean.location = (900, 0)
    
    # Create Object Info Node
    obj_info = node_tree.nodes.new(type='GeometryNodeObjectInfo')
    obj_info.inputs[0].default_value = bpy.data.objects["Disolve_sphere"]
    obj_info.transform_space = 'RELATIVE'
    obj_info.location = (0, 200)
    
    # Create Ico Sphere
    ico_sphere = node_tree.nodes.new(type="GeometryNodeMeshIcoSphere")
    ico_sphere.inputs['Subdivisions'].default_value = 6
    ico_sphere.location = (70, 400)
    
    # Create Transform Ico Sphere
    transf_ico_sphere = node_tree.nodes.new(type="GeometryNodeTransform")
    transf_ico_sphere.location = (300, 200)
    
    # Create Distribute Points on Face
    dist_points_f = node_tree.nodes.new(type="GeometryNodeDistributePointsOnFaces")
    dist_points_f.inputs['Density'].default_value = 2500.0
    dist_points_f.location = (1100, 400)
    
    # Create Geometry Proximity
    geo_proxim = node_tree.nodes.new(type="GeometryNodeProximity")
    geo_proxim.target_element = 'POINTS'
    geo_proxim.location = (700, 400)
    
    # Create Geometry Proximity
    math_less_than = node_tree.nodes.new(type="ShaderNodeMath")
    math_less_than.inputs[1].default_value = 0.0001
    math_less_than.operation = 'LESS_THAN'
    math_less_than.location = (900, 600)
    
    # Create Simulation Zone TODO::
    
    # Create Join Geometry
    join_geo = node_tree.nodes.new(type="GeometryNodeJoinGeometry")
    join_geo.location = (1600, 500)
    
    # Create Set Points
    set_points = node_tree.nodes.new(type="GeometryNodeSetPosition")
    set_points.location = (1800, 500)
    
    # Create Store Named Attribute
    store_n_attr = node_tree.nodes.new(type="GeometryNodeStoreNamedAttribute")
    store_n_attr.location = (2000, 500)
    store_n_attr.data_type = 'FLOAT_VECTOR'
    store_n_attr.inputs['Name'].default_value = 'Val'
    
    # Create Named Attribute
    named_attr = node_tree.nodes.new(type="GeometryNodeInputNamedAttribute")
    named_attr.location = (1100, 100)
    named_attr.data_type = 'FLOAT_VECTOR'
    named_attr.inputs['Name'].default_value = 'Val'
    
    # Create Route
    route = node_tree.nodes.new(type="NodeReroute")
    route.location = (1600, 200)
    
    # Create Vector Math Add
    vect_math = node_tree.nodes.new(type="ShaderNodeVectorMath")
    vect_math.location = (1650, -250)
    
    # Create Vector Math Normalize
    vect_math_norm = node_tree.nodes.new(type="ShaderNodeVectorMath")
    vect_math_norm.location = (1300, 350)
    vect_math_norm.operation = 'NORMALIZE'
    
    # Create Vector Math Scale
    vect_math_scale = node_tree.nodes.new(type="ShaderNodeVectorMath")
    vect_math_scale.location = (1350, 150)
    vect_math_scale.operation = 'SCALE'
    
    # Create Random Value 
    rand_val = node_tree.nodes.new(type="FunctionNodeRandomValue")
    rand_val.location = (1150, -70)
    rand_val.inputs['Min'].default_value = 0.005
    rand_val.inputs['Max'].default_value = 0.02
    
    # Create Index
    indx = node_tree.nodes.new(type="GeometryNodeInputIndex")
    indx.location = (900, -300)
    
    # Create Scene Time
    scene_time = node_tree.nodes.new(type="GeometryNodeInputSceneTime")
    scene_time.location = (800, 200)
    
    # Create Point Radius
    p_radius = node_tree.nodes.new(type="GeometryNodeSetPointRadius")
    p_radius.location = (2300, 500)
    
    # Create Point Radius
    p_radius_dist = node_tree.nodes.new(type="GeometryNodeSetPointRadius")
    p_radius_dist.location = (1300, 700)
    p_radius_dist.inputs['Radius'].default_value = 0.08
    
    # Create Math Substract 
    math_node_sub = node_tree.nodes.new(type="ShaderNodeMath")
    math_node_sub.location = (2150, 200)
    math_node_sub.operation = 'SUBTRACT'
    math_node_sub.inputs[1].default_value = 0.002
    
    # Create Radius for Math Node
    math_radius = node_tree.nodes.new(type="GeometryNodeInputRadius")
    math_radius.location = (1900, 200)
    
    # Delete Geometry Node
    del_geo = node_tree.nodes.new(type="GeometryNodeDeleteGeometry")
    del_geo.location = (2700, 500)
    
    # Create Delete Geometry Condition 
    del_less_than = node_tree.nodes.new(type="ShaderNodeMath")
    del_less_than.location = (2450, 200)
    del_less_than.operation = 'LESS_THAN'
    del_less_than.inputs[1].default_value = 0.01
    
    # Make fine Particles
    out_point_radius = node_tree.nodes.new(type="GeometryNodeSetPointRadius")
    out_point_radius.location = (3000, 500)
    out_point_radius.inputs['Radius'].default_value = 0.08
    
    # Create Math Divide for particles
    math_node_div = node_tree.nodes.new(type="ShaderNodeMath")
    math_node_div.location = (2850, 300)
    math_node_div.operation = 'DIVIDE'
    math_node_div.inputs[1].default_value = 35
    
    # Create Radius for Math Node
    math_radius_part = node_tree.nodes.new(type="GeometryNodeInputRadius")
    math_radius_part.location = (2700, 200)
    
    # Add Randomness
    vect_math_add_rand = node_tree.nodes.new(type="ShaderNodeVectorMath")
    vect_math_add_rand.location = (1350, -150)
    
    # Generate Noise in the particles
    noise_text_part = node_tree.nodes.new(type="ShaderNodeTexNoise")
    noise_text_part.location = (800, -600)
    noise_text_part.noise_dimensions = '4D'
    noise_text_part.inputs['Scale'].default_value = 0.9
    
    # Math node for randomness
    math_div_rand = node_tree.nodes.new(type="ShaderNodeMath")
    math_div_rand.location = (600, -800)
    math_div_rand.operation = 'DIVIDE'
    math_div_rand.inputs[1].default_value = 2
    
    # Math node for randomness
    math_add_rand = node_tree.nodes.new(type="ShaderNodeMath")
    math_add_rand.location = (400, -900)
    math_add_rand.inputs[1].default_value = 6
    
    # Add Scene Time
    scene_time_rand = node_tree.nodes.new(type="GeometryNodeInputSceneTime")
    scene_time_rand.location = (200, -900)
    
    # Subtract
    vect_math_sub_rand = node_tree.nodes.new(type="ShaderNodeVectorMath")
    vect_math_sub_rand.location = (1000, -450)
    vect_math_sub_rand.operation = 'SUBTRACT'
    vect_math_sub_rand.inputs[1].default_value[0] = 0.5
    vect_math_sub_rand.inputs[1].default_value[1] = 0.5
    vect_math_sub_rand.inputs[1].default_value[2] = 0.5
    
    # Scale Randomness
    vect_math_scale_rand = node_tree.nodes.new(type="ShaderNodeVectorMath")
    vect_math_scale_rand.location = (1200, -450)
    vect_math_scale_rand.operation = 'SCALE'
    vect_math_scale_rand.inputs['Scale'].default_value = 0.03
    
    # Make mesh visible
    mesh_visible = node_tree.nodes.new(type="GeometryNodeJoinGeometry")
    mesh_visible.location = (4500, 0)
    
    # Make particles editables
    store_output_attr = node_tree.nodes.new(type="GeometryNodeStoreNamedAttribute")
    store_output_attr.location = (3300, 400)
    store_output_attr.inputs['Name'].default_value = 'PR'
    
    # Set Material Node
    set_output_material = node_tree.nodes.new(type="GeometryNodeSetMaterial")
    set_output_material.location = (3600, 200)
    
    # Create group for particles
    group_input_part = node_tree.nodes.new(type="NodeGroupInput")
    group_input_part.location = (2600, 100)
    
    # Create Group input for density
    group_input_dens = node_tree.nodes.new(type="NodeGroupInput")
    group_input_dens.location = (600, 600)
    
    group_output = node_tree.nodes.new(type='NodeGroupOutput')
    node_tree.interface.new_socket('Mesh', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    group_output.location = (5000, 0)
    
    # Link nodes together
    node_tree.links.new(group_input.outputs['Mesh'], mesh_boolean.inputs['Mesh 1'])
    node_tree.links.new(out_point_radius.outputs['Points'], store_output_attr.inputs['Geometry'])
    node_tree.links.new(store_output_attr.outputs['Geometry'], set_output_material.inputs['Geometry'])
    node_tree.links.new(set_output_material.outputs['Geometry'], mesh_visible.inputs['Geometry'])
    node_tree.links.new(group_input_part.outputs['Value'], math_node_div.inputs[1])
    node_tree.links.new(group_input_part.outputs['Material'], set_output_material.inputs['Material'])
    node_tree.links.new(math_radius_part.outputs['Radius'], store_output_attr.inputs['Value'])
    node_tree.links.new(group_input_dens.outputs['Value'], dist_points_f.inputs['Density'])
    node_tree.links.new(mesh_visible.outputs['Geometry'], group_output.inputs['Mesh'])
    node_tree.links.new(mesh_boolean.outputs['Mesh'], mesh_visible.inputs['Geometry'])
    node_tree.links.new(ico_sphere.outputs['Mesh'], transf_ico_sphere.inputs['Geometry'])
    node_tree.links.new(obj_info.outputs['Location'], transf_ico_sphere.inputs['Translation'])
    node_tree.links.new(obj_info.outputs['Rotation'], transf_ico_sphere.inputs['Rotation'])
    node_tree.links.new(obj_info.outputs['Scale'], transf_ico_sphere.inputs['Scale'])
    node_tree.links.new(transf_ico_sphere.outputs['Geometry'], mesh_boolean.inputs['Mesh 2'])
    node_tree.links.new(mesh_boolean.outputs['Mesh'], dist_points_f.inputs['Mesh'])
    node_tree.links.new(transf_ico_sphere.outputs['Geometry'], geo_proxim.inputs['Target'])
    node_tree.links.new(geo_proxim.outputs['Distance'], math_less_than.inputs['Value'])
    node_tree.links.new(math_less_than.outputs['Value'], dist_points_f.inputs['Selection'])
    node_tree.links.new(join_geo.outputs['Geometry'], set_points.inputs['Geometry'])
    node_tree.links.new(set_points.outputs['Geometry'], store_n_attr.inputs['Geometry'])
    node_tree.links.new(named_attr.outputs['Attribute'], vect_math.inputs[0])
    node_tree.links.new(vect_math.outputs['Vector'], route.inputs['Input'])
    node_tree.links.new(route.outputs['Output'], set_points.inputs['Offset'])
    node_tree.links.new(route.outputs['Output'], store_n_attr.inputs['Value'])
    node_tree.links.new(dist_points_f.outputs['Normal'], vect_math_norm.inputs['Vector'])
    node_tree.links.new(vect_math_norm.outputs['Vector'], vect_math_scale.inputs['Vector'])
    node_tree.links.new(vect_math_scale.outputs['Vector'], vect_math_add_rand.inputs['Vector'])
    node_tree.links.new(vect_math_add_rand.outputs['Vector'], vect_math.inputs[1])
    node_tree.links.new(scene_time_rand.outputs['Seconds'], math_add_rand.inputs['Value'])
    node_tree.links.new(math_add_rand.outputs['Value'], math_div_rand.inputs['Value'])
    node_tree.links.new(math_div_rand.outputs['Value'], noise_text_part.inputs['W'])
    node_tree.links.new(noise_text_part.outputs['Color'], vect_math_sub_rand.inputs['Vector'])
    node_tree.links.new(vect_math_sub_rand.outputs['Vector'], vect_math_scale_rand.inputs['Vector'])
    node_tree.links.new(vect_math_scale_rand.outputs['Vector'], vect_math_add_rand.inputs[1])
    node_tree.links.new(indx.outputs['Index'], rand_val.inputs['Seed'])
    node_tree.links.new(rand_val.outputs['Value'], vect_math_scale.inputs['Scale'])
    node_tree.links.new(scene_time.outputs['Frame'], dist_points_f.inputs['Seed'])
    node_tree.links.new(store_n_attr.outputs['Geometry'], p_radius.inputs['Points'])
    node_tree.links.new(dist_points_f.outputs['Points'], p_radius_dist.inputs['Points'])
    node_tree.links.new(p_radius_dist.outputs['Points'], join_geo.inputs['Geometry'])
    node_tree.links.new(math_radius.outputs['Radius'], math_node_sub.inputs['Value'])
    node_tree.links.new(math_node_sub.outputs['Value'], p_radius.inputs['Radius'])
    node_tree.links.new(p_radius.outputs['Points'], del_geo.inputs['Geometry'])
    node_tree.links.new(math_node_sub.outputs['Value'], del_less_than.inputs['Value'])
    node_tree.links.new(del_less_than.outputs['Value'], del_geo.inputs['Selection'])
    node_tree.links.new(math_radius_part.outputs['Radius'], math_node_div.inputs['Value'])
    node_tree.links.new(math_node_div.outputs['Value'], out_point_radius.inputs['Radius'])
    node_tree.links.new(del_geo.outputs['Geometry'], out_point_radius.inputs['Points'])
    

    
def scene_setup(num_points=1000):
    save_as_mp4()
    clean_scene()
    set_environment(num_points)
    
    for light in range(0, 3):
        add_lights()

    # Position camera
    loc = (2.9, -6.4, 1.32)
    rot = (math.radians(91), 0, math.radians(24))
    set_camera(loc, rot)
    mesh = bpy.data.objects['textured']
    create_mesh_sand_shader(mesh)
    create_disolve_effect(mesh)
    
    
def add_lights():
    bpy.ops.object.light_add(type="AREA", location=(0, -7.7, 2.3))
    bpy.context.object.data.color = (1, 0.7, 0.7)
    bpy.context.object.data.energy = 1060
    bpy.context.object.data.diffuse_factor = 1.0


def main():
    """
    Python code that creates a Fibinacci Spiral
    """
    scene_setup()
#    render_loop()


if __name__ == "__main__":
    main()