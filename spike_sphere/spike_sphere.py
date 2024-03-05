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
    bpy.context.scene.render.filepath = f"./Users/erikamolnar/Blender_Projects/SpikeSphere/spike_sphere_loop.mp4"


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
#        world.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.5, 0.8, 1)
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.1, 0.1, 0.4, 1)
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.06, 0.4, 1)
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


def scene_setup(frame_count=90):
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
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16)
    base_sphere = bpy.context.object
    base_sphere.name = 'BaseSphere'
    
    return base_sphere


def create_animation_loop(obj, 
                            data_path, 
                            start_value, 
                            mid_value,
                            end_value,
                            start_frame, 
                            loop_length=90):
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


def geometry_node_setup(base_sphere):
    # Add a Geometry Nodes modifier to the base sphere
    mod = base_sphere.modifiers.new(name="GeometryNodes", type='NODES')
    node_tree = bpy.data.node_groups.new(name="SpikeNodes", type='GeometryNodeTree')
    mod.node_group = node_tree

    # Create Group Input and Output nodes
    group_input = node_tree.nodes.new(type='NodeGroupInput')
    group_input.location = (-300, 0)

    group_output = node_tree.nodes.new(type='NodeGroupOutput')
    node_tree.interface.new_socket('Mesh', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    group_output.location = (300, 0)

    # Create IcoSphere
    ico_sphere_node = node_tree.nodes.new(type='GeometryNodeMeshIcoSphere')
    ico_sphere_node.inputs['Subdivisions'].default_value = 6
    ico_sphere_node.location = (-100, 0)

    # Create Extrude Mesh
    extrude_node = node_tree.nodes.new(type='GeometryNodeExtrudeMesh')
    extrude_node.location = (100, 30)
    
    # Create Noise Texture for Extrude Mesh
    noise_tex_node = node_tree.nodes.new(type='ShaderNodeTexNoise')
    noise_tex_node.inputs['Roughness'].default_value = 0.0
    noise_tex_node.location = (-100, -200)
    
    # Link nodes together
    node_tree.links.new(ico_sphere_node.outputs['Mesh'], extrude_node.inputs['Mesh'])
    node_tree.links.new(extrude_node.outputs['Mesh'], group_output.inputs['Mesh'])
    node_tree.links.new(noise_tex_node.outputs['Fac'], extrude_node.inputs['Offset Scale'])
    
    create_animation_loop(
        noise_tex_node.inputs["Scale"],
        "default_value",
        start_value=-15.0,
        mid_value=0.0,
        end_value=15.0,
        start_frame=1
    )


def create_sphere_shader2(sphere):
    sphere = bpy.context.active_object
    mat = bpy.data.materials.new(name="ReflectiveMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    # Create a Principled BSDF shader node 
    glossy_shader = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    glossy_shader.location = (0, 0)

    # Set roughness to control
    glossy_shader.inputs["Metallic"].default_value = 1
    glossy_shader.inputs["Base Color"].default_value = (0.8, 0, 0.6, 1)


    # Create a Material Output
    material_output = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    material_output.location = (200, 0)

    # Link the Glossy BSDF node to the Material Output
    mat.node_tree.links.new(glossy_shader.outputs["BSDF"], material_output.inputs["Surface"])

    sphere.data.materials.append(mat)


def create_sphere_shader(sphere):
    sphere = bpy.context.active_object
    mat = bpy.data.materials.new(name="ReflectiveMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    # Create a Principled BSDF shader node 
    glossy_shader = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    glossy_shader.location = (0, 0)

    # Set roughness to control
    glossy_shader.distribution = 'GGX'
    glossy_shader.inputs["Metallic"].default_value = 1
    glossy_shader.inputs["Base Color"].default_value = (0.8, 0, 0.6, 1)
    glossy_shader.inputs["Coat Weight"].default_value = 1


    # Create a Material Output
    material_output = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    material_output.location = (200, 0)

    # Link the Glossy BSDF node to the Material Output
    mat.node_tree.links.new(glossy_shader.outputs["BSDF"], material_output.inputs["Surface"])

    sphere.data.materials.append(mat)


def generate_spike_sphere():
    sphere = generate_sphere()
    geometry_node_setup(sphere)
    create_sphere_shader(sphere)


def main():
    """
    Python code that creates a Fibinacci Spiral
    """
    scene_setup()
    generate_spike_sphere()
    render_loop()
    

if __name__ == "__main__":
    main()