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
    bpy.context.scene.render.filepath = f"/<path>/GoldenSpiral/render/golden_loop.mp4"


def set_environment(frame_count, fps=30):
    # Set up sframe information
    scene = bpy.context.scene
    scene.frame_end = frame_count - 540
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
        world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)


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


def create_camera_path():
    # Create NURBS curve
    bpy.ops.curve.primitive_nurbs_path_add(radius=1, enter_editmode=False, align="WORLD", location=(0, 0, 0))
    nurbs_curve = bpy.context.active_object.data

    # Configure NURBS curve settings
    nurbs_curve.splines.new("NURBS")
    nurbs_spline = nurbs_curve.splines.active
    nurbs_spline.points.add(count=71)  # Number of control points

    scale=30
    depth=-80
    z=0
    # Generate camera path
    for node in range(1, 70):
        th = node * 0.3
        x = scale * th * np.cos(th)
        y = scale * th * np.sin(th)
        z = depth + (node * 9)
        nurbs_spline.points[node].co = (x, y, z, 1)
        
    nurbs_spline.points[70].co = (0, 0, z, 1)

    return nurbs_curve
    

def camera_animation(camera, param_name):
    camera_path = create_camera_path()
    
    bpy.context.view_layer.objects.active = camera
    bpy.ops.object.constraint_add(type="FOLLOW_PATH")
    bpy.context.object.constraints["Follow Path"].target = bpy.data.objects["NurbsPath"]
    follow_path_constraint = camera.constraints[0]

    camera_path.path_duration = 450
    print(follow_path_constraint)
    empty = track_empty(camera)

    bpy.ops.constraint.followpath_path_animate(constraint="Follow Path", owner="OBJECT")


def set_camera(loc, rot):
    bpy.ops.object.camera_add(location=loc, rotation=rot)
    camera = bpy.context.active_object

    # set the camera as "active"
    bpy.context.scene.camera = camera

    # set focal lenght
    camera.data.lens = 70

    camera.data.passepartout_alpha = 0.9

    camera_animation(camera, "location")


def create_reflective_plane():
    bpy.ops.mesh.primitive_plane_add(size=1000)
    plane = bpy.context.active_object
    mat = bpy.data.materials.new(name="ReflectiveMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    # Create a Glossy BSDF shader node (specular reflection)
    glossy_shader = mat.node_tree.nodes.new(type="ShaderNodeBsdfGlossy")
    glossy_shader.location = (0, 0)

    # Set roughness to control
    glossy_shader.inputs["Roughness"].default_value = 0.7
    glossy_shader.inputs["Color"].default_value = (0.799999, 0, 0.594171, 1)


    # Create a Material Output
    material_output = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    material_output.location = (200, 0)

    # Link the Glossy BSDF node to the Material Output
    mat.node_tree.links.new(glossy_shader.outputs["BSDF"], material_output.inputs["Surface"])

    plane.data.materials.append(mat)


def scene_setup(num_points=1000):
    save_as_mp4()
    clean_scene()
    create_reflective_plane()
    set_environment(num_points)
    
    # Position camera
    loc = (0, 0, 0)
    rot = (math.radians(0), 0, 0)
    set_camera(loc, rot)
    
    
def add_lights():
    rotation = (0.0, 0.0, math.radians(180))
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 800), rotation=rotation)
    bpy.context.object.data.energy = 100
    bpy.context.object.data.diffuse_factor = 0.05
    bpy.context.object.data.angle = math.radians(45)


def apply_emission_material(obj):
    color = (0.913041, 0.1996, 1, 1)

    mat = bpy.data.materials.new(name="NeonMaterial")
    mat.use_nodes = True
    emission_shader = mat.node_tree.nodes.new(type="ShaderNodeEmission")
    emission_shader.inputs["Color"].default_value = color # Purple color
    emission_shader.inputs["Strength"].default_value = 7.0
    
    # Link emission shader to Material Output
    mat.node_tree.links.new(emission_shader.outputs["Emission"], mat.node_tree.nodes["Material Output"].inputs["Surface"])

    obj.data.materials.append(mat)


def generate_coordonates(num_points=1000, scale_factor=0.7, pitch=0.005):
    golden_angle = 180 * (3 - np.sqrt(5))
    theta = np.array([x * golden_angle for x in range(num_points)])
    radius = scale_factor * np.sqrt(theta)

    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    z = pitch * theta
    
    return x, y, z


def generate_golden_spiral():
    X, Y, Z = generate_coordonates()
    current_frame = 0

    for x, y, z in zip(X, Y, Z):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=3.5, enter_editmode=False, align="WORLD", location=(0, 0, -10))
        sphere = bpy.context.active_object

        sphere.keyframe_insert(data_path="location", frame=current_frame)
        current_frame += 1
        sphere.location = (x, y, z)
        apply_emission_material(sphere)

        sphere.keyframe_insert(data_path="location", frame=current_frame)
    

def main():
    """
    Python code that creates a Fibinacci Spiral
    """
    scene_setup()
    generate_golden_spiral()
    render_loop()
    

if __name__ == "__main__":
    main()
