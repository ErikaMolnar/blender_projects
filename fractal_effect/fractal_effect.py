import bpy
import math
import random
import numpy as np


def purge_orphans():
    """
    Remove all orphan data blocks
    """
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def clean_scene():
    """
    Removing all of the objects, collection, materials, particles,
    textures, images, curves, meshes, actions, nodes, and worlds from the scene
    """
    # make sure the active object is not in Edit Mode
    if bpy.context.active_object and bpy.context.active_object.mode == "EDIT":
        bpy.ops.object.editmode_toggle()

    # make sure non of the objects are hidden from the viewport, selection, or disabled
    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_select = False
        obj.hide_viewport = False

    # select all the object and delete them
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    # find all the collections and remove them
    collection_names = [col.name for col in bpy.data.collections]
    for name in collection_names:
        bpy.data.collections.remove(bpy.data.collections[name])

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
    bpy.context.scene.render.filepath = f"<path>/Fractal_effect/render/fractal_effect.mp4"


def set_environment(frame_count, fps=30):
    # Set up sframe information
    scene = bpy.context.scene
    scene.frame_end = frame_count
    scene.render.fps = fps
    scene.frame_current = 1
    scene.frame_start = 1
    
    scene.render.engine = "BLENDER_EEVEE"

    # Use the GPU to render
    scene.cycles.device = "GPU"
    scene.cycles.samples = 1024
    
    scene.eevee.use_bloom = True
    scene.eevee.bloom_color = (0.913041, 0.1996, 1)
    scene.eevee.bloom_intensity = 0.1
    scene.eevee.bloom_radius = 8.72222
    scene.eevee.use_ssr = True

    scene.view_settings.look = "AgX - Very High Contrast"
    
    # set the world background to black
    world = bpy.data.worlds["World"]
    if "Background" in world.node_tree.nodes:
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.06, 0.4, 1)
        world.node_tree.nodes["Background"].inputs[1].default_value = 6
    world.node_tree.nodes["World Output"].target = 'EEVEE'


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


def add_lights():
    rotation = (0.0, 0.0, math.radians(180))
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 800), rotation=rotation)
    bpy.context.object.data.energy = 100
    bpy.context.object.data.color = (1, 0.373605, 0.873059)
    bpy.context.object.data.diffuse_factor = 0.1
    bpy.context.object.data.angle = math.radians(45)


def scene_setup(frame_count=140):
    save_as_mp4()
    clean_scene()
    add_lights()
    set_environment(frame_count)
    
    # Position camera
    loc = (0.0, -11.0, 9.2)
    rot = (math.radians(50), 0, 0)
    set_camera(loc, rot)


def generate_sphere():
    # Create a UV sphere that will be the base of our spiked object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=8, ring_count=4)
    base_sphere = bpy.context.object
    base_sphere.name = 'BaseSphere'
    
    return base_sphere


def create_animation_loop(obj, 
                            data_path, 
                            start_value, 
                            mid_value,
                            end_value,
                            start_frame, 
                            loop_length=140):
    # set the start value
    setattr(obj, data_path, start_value)
    # add a keyframe at the start
    obj.keyframe_insert(data_path, frame=start_frame)

    # set the middle value
    setattr(obj, data_path, mid_value)
    # add a keyframe in the middle
    mid_frame = start_frame + (loop_length) / 2
    obj.keyframe_insert(data_path, frame=mid_frame)

    # set the end value
    setattr(obj, data_path, end_value)
    # add a keyframe in the end
    end_frame = start_frame + loop_length
    obj.keyframe_insert(data_path, frame=end_frame)


def create_extrude_group(node_tree, to=[0, 0, 250, 0]):
    # Create Extrude Mesh
    extrude_mesh = node_tree.nodes.new(type="GeometryNodeExtrudeMesh")
    extrude_mesh.location = (to[0], to[1])
    extrude_mesh.inputs["Offset Scale"].default_value=0.2
    to[0] += 500
    
    # Scale extrusion
    scale_extr = node_tree.nodes.new(type="GeometryNodeScaleElements")
    scale_extr.location = (to[2], to[3])
    scale_extr.inputs["Scale"].default_value = 0.5
    to[2] += 500
    
    node_tree.links.new(extrude_mesh.outputs["Mesh"], scale_extr.inputs["Geometry"])
    node_tree.links.new(extrude_mesh.outputs["Top"], scale_extr.inputs["Selection"])
    
    return extrude_mesh, scale_extr


def geometry_node_setup(base_sphere):
    extrude_nodes = {}
    # Add a Geometry Nodes modifier to the base sphere
    mod = base_sphere.modifiers.new(name="GeometryNodes", type='NODES')
    node_tree = bpy.data.node_groups.new(name="FractalNodes", type='GeometryNodeTree')
    mod.node_group = node_tree
    node_tree.interface.new_socket('Mesh', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    node_tree.interface.new_socket('Mesh', in_out='INPUT', socket_type='NodeSocketGeometry')

    # Create Group Input and Output nodes
    group_input = node_tree.nodes.new(type='NodeGroupInput')
    group_input.location = (-300, 0)

    group_output = node_tree.nodes.new(type='NodeGroupOutput')
    group_output.location = (3500, 0)
    
    extrude, scale = create_extrude_group(node_tree)
    extrude_nodes['Extrude_0'] = extrude
    extrude_nodes['Scale_0'] = scale
    
    node_tree.links.new(group_input.outputs["Mesh"], extrude.inputs["Mesh"])
    
    for i in range(1, 7):
        extrude_mesh, scale_extr = create_extrude_group(node_tree)
        extrude_nodes[f'Extrude_{i}'] = extrude_mesh
        extrude_nodes[f'Scale_{i}'] = scale_extr
        node_tree.links.new(scale.outputs["Geometry"], extrude_mesh.inputs["Mesh"])
        scale = scale_extr
    
    node_tree.links.new(scale.outputs["Geometry"], group_output.inputs["Mesh"])
    
    create_animation_loop(
        extrude_nodes['Scale_6'].inputs["Scale"],
        "default_value",
        start_value=0.0,
        mid_value=0.5,
        end_value=1.0,
        start_frame=1
    )
    
    create_animation_loop(
        extrude_nodes['Scale_1'].inputs["Scale"],
        "default_value",
        start_value=0.0,
        mid_value=0.5,
        end_value=1.0,
        start_frame=1
    )
    
    create_animation_loop(
        extrude_nodes['Scale_4'].inputs["Scale"],
        "default_value",
        start_value=0.0,
        mid_value=0.5,
        end_value=1.0,
        start_frame=1
    )


def create_sphere_shader(sphere):
    sphere = bpy.context.active_object
    mat = bpy.data.materials.new(name="ReflectiveMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    # Create a Principled BSDF shader node 
    shader = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    shader.location = (0, 0)
    
    # Create Color Ramp
    color_ramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
    color_ramp.location = (-400, 0)
    
    # Create Layer Weight
    layer_weight = mat.node_tree.nodes.new(type="ShaderNodeLayerWeight")
    layer_weight.location = (-600, 0)
    layer_weight.inputs["Blend"].default_value = 0.4

    # Create a Material Output
    material_output = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    material_output.location = (400, 0)

    # Link the Principled BSDF node to the Material Output
    mat.node_tree.links.new(shader.outputs["BSDF"], material_output.inputs["Surface"])
    mat.node_tree.links.new(layer_weight.outputs["Fresnel"], color_ramp.inputs["Fac"])
    mat.node_tree.links.new(color_ramp.outputs["Color"], shader.inputs["Base Color"])

    sphere.data.materials.append(mat)


def generate_fractal_sphere():
    sphere = generate_sphere()
    geometry_node_setup(sphere)
    create_sphere_shader(sphere)


def main():
    """
    Python code that creates a Spike Sphere
    """
    scene_setup()
    generate_fractal_sphere()
    render_loop()
    

if __name__ == "__main__":
    main()