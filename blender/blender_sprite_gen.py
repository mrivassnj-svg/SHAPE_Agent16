"""
blender_sprite_gen.py
---------------------
Run this script INSIDE Blender's scripting tab (or via command line below)
to procedurally build and render all SHAPE Agent 16 RPG sprites.

COMMAND-LINE RENDER (headless, no GUI needed):
    blender --background --python blender/blender_sprite_gen.py

Each character is built from Blender primitives (no external assets needed).
Rendered PNGs land in:  assets/sprites/<name>.png  (160 x 160 px, transparent bg)

Characters generated:
  Humanoids (Agent 16 style rig):
    player.png   — Agent 16 hero (blue hoodie, visor)

  Enemies:
    slime.png    — Syntax Slime      (green blob, googly eyes)
    crab.png     — Comment Crab      (red crab, # symbol shell)
    imp.png      — Infinite Imp      (purple imp, loop horns)
    wyrm.png     — While Wyrm        (teal wyrm, coiled body)
    wraith.png   — Recursion Wraith  (dark ghost, fractal tail)
    lich.png     — Lambda Lich       (grey skeleton, λ staff)
    ogre.png     — Index Error Ogre  (orange brute, [] fists)
    specter.png  — Slice Specter     (cyan ghost, blade arm)
    knight.png   — KeyError Knight   (silver armour, key sword)
    hydra.png    — Hash Hydra        (green multi-head, # scales)
    drake.png    — Exception Drake   (red dragon, error flames)
    boss.png     — BOSS: NullByte    (black void giant, 0 eye)

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import bpy
import math
import os
from pathlib import Path

# ── Output directory ──────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
OUT_DIR     = SCRIPT_DIR.parent / "assets" / "sprites"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RENDER_SIZE   = 160     # px — square sprite
RENDER_SAMPLES= 64      # cycles samples (fast but clean enough for 160px)


# ══════════════════════════════════════════════════════════════════════════════
# BLENDER SCENE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)


def setup_render(filepath: str) -> None:
    scene = bpy.context.scene
    scene.render.engine             = "CYCLES"
    scene.cycles.samples            = RENDER_SAMPLES
    scene.cycles.use_denoising      = True
    scene.render.resolution_x       = RENDER_SIZE
    scene.render.resolution_y       = RENDER_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent   = True          # PNG alpha background
    scene.render.image_settings.file_format   = "PNG"
    scene.render.image_settings.color_mode    = "RGBA"
    scene.render.image_settings.compression   = 15
    scene.render.filepath           = filepath


def add_camera(location=(0, -4.5, 1.2), rotation_deg=(80, 0, 0)) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.active_object
    cam.rotation_euler = [math.radians(r) for r in rotation_deg]
    bpy.context.scene.camera = cam
    return cam


def add_key_light(location=(3, -3, 5), energy=400, color=(1, 0.95, 0.85)) -> None:
    bpy.ops.object.light_add(type="SUN", location=location)
    light = bpy.context.active_object
    light.data.energy = energy
    light.data.color  = color


def add_fill_light(location=(-3, -2, 3), energy=150) -> None:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.active_object
    light.data.energy = energy
    light.data.size   = 4


def mat(name: str, color: tuple, metallic=0.0, roughness=0.5,
        emission=None) -> bpy.types.Material:
    """Create or reuse a simple Principled BSDF material."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Metallic"].default_value   = metallic
    bsdf.inputs["Roughness"].default_value  = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[:3], 1.0)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    return m


def apply_mat(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def ico(location, radius, material, subdivisions=2) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions, radius=radius, location=location)
    obj = bpy.context.active_object
    apply_mat(obj, material)
    return obj


def cube(location, size, material, scale=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.active_object
    if scale:
        obj.scale = scale
    apply_mat(obj, material)
    return obj


def cyl(location, radius, depth, material, rot=(0,0,0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location)
    obj = bpy.context.active_object
    obj.rotation_euler = [math.radians(r) for r in rot]
    apply_mat(obj, material)
    return obj


def cone(location, radius1, depth, material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        radius1=radius1, radius2=0, depth=depth, location=location)
    obj = bpy.context.active_object
    apply_mat(obj, material)
    return obj


def torus(location, major_r, minor_r, material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        location=location, major_radius=major_r, minor_radius=minor_r)
    obj = bpy.context.active_object
    apply_mat(obj, material)
    return obj


def render(name: str) -> None:
    path = str(OUT_DIR / f"{name}.png")
    setup_render(path)
    bpy.ops.render.render(write_still=True)
    print(f"  ✓  Rendered: {path}")


# ══════════════════════════════════════════════════════════════════════════════
# CHARACTER BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_humanoid_base(skin_color, suit_color, visor_color,
                        accent_color=None, glow=None) -> None:
    """
    Generic humanoid rig (Agent 16 / Knight / Lich style).
    Proportions: chibi RPG — big head, stubby body.
    """
    skin  = mat("skin",  skin_color)
    suit  = mat("suit",  suit_color, roughness=0.4)
    visor = mat("visor", visor_color, metallic=0.8, roughness=0.1,
                emission=glow if glow else visor_color)
    acc   = mat("acc",   accent_color or suit_color)

    # Head
    ico((0, 0, 1.55), 0.42, skin)
    # Visor strip
    cube((0, -0.32, 1.58), 0.01, visor, scale=(0.55, 0.08, 0.18))
    # Torso
    cube((0, 0, 0.85), 1.0, suit, scale=(0.42, 0.28, 0.45))
    # Hips
    cube((0, 0, 0.42), 1.0, suit, scale=(0.38, 0.26, 0.18))
    # Left leg
    cyl((-0.18, 0, 0.08), 0.13, 0.52, suit)
    # Right leg
    cyl((0.18, 0, 0.08), 0.13, 0.52, suit)
    # Left arm
    cyl((-0.52, 0, 0.85), 0.10, 0.55, suit, rot=(0, 90, 15))
    # Right arm
    cyl((0.52, 0, 0.85), 0.10, 0.55, suit, rot=(0, 90, -15))
    # Feet
    cube((-0.18, -0.06, -0.22), 0.28, acc, scale=(1, 1.4, 0.5))
    cube(( 0.18, -0.06, -0.22), 0.28, acc, scale=(1, 1.4, 0.5))


def sprite_player() -> None:
    """Agent 16 — blue tech hoodie, cyan visor, white trim."""
    build_humanoid_base(
        skin_color   = (0.85, 0.70, 0.58),
        suit_color   = (0.10, 0.25, 0.70),
        visor_color  = (0.0,  0.85, 1.0),
        accent_color = (0.9,  0.9,  0.9),
        glow         = (0.0,  0.85, 1.0),
    )
    # Hood
    ico((0, 0.06, 1.72), 0.46, mat("hood", (0.08, 0.18, 0.58)))
    # Backpack / gear
    cube((0, 0.26, 0.92), 0.38, mat("pack", (0.05, 0.12, 0.40)),
         scale=(0.7, 0.4, 0.7))
    # Emblem on chest (small bright disc)
    cyl((0, -0.30, 0.90), 0.10, 0.04,
        mat("emblem", (0.0, 0.85, 1.0), emission=(0.0, 0.85, 1.0)))


def sprite_slime() -> None:
    """Syntax Slime — green wobbly blob with # pupils."""
    body = mat("sbody", (0.15, 0.75, 0.20), roughness=0.2)
    eye  = mat("seye",  (0.9,  0.9,  0.9))
    pupil= mat("spup",  (0.05, 0.05, 0.05))

    ico((0, 0, 0.55), 0.55, body, subdivisions=3)
    # Eyes
    ico((-0.20, -0.42, 0.75), 0.12, eye)
    ico(( 0.20, -0.42, 0.75), 0.12, eye)
    ico((-0.20, -0.50, 0.75), 0.07, pupil)
    ico(( 0.20, -0.50, 0.75), 0.07, pupil)
    # Highlight bumps
    ico((-0.30, -0.15, 1.0), 0.18, body)
    ico(( 0.28, -0.10, 0.98), 0.14, body)
    # Drip at bottom
    cone((0, 0, -0.05), 0.30, 0.30, body)


def sprite_crab() -> None:
    """Comment Crab — red shell with # emblem."""
    shell   = mat("cshell",  (0.80, 0.12, 0.08), roughness=0.3)
    claw_m  = mat("cclaw",   (0.90, 0.20, 0.10))
    eye_m   = mat("ceye",    (0.1,  0.1,  0.1))
    hash_m  = mat("chash",   (1.0,  0.95, 0.2), emission=(1.0, 0.9, 0.0))

    # Body
    ico((0, 0, 0.6), 0.55, shell, subdivisions=2)
    cube((0, -0.08, 0.60), 0.9, shell, scale=(1.1, 0.6, 0.7))
    # Eyes on stalks
    cyl((-0.28, -0.45, 0.90), 0.05, 0.25, shell)
    cyl(( 0.28, -0.45, 0.90), 0.05, 0.25, shell)
    ico((-0.28, -0.45, 1.05), 0.10, eye_m)
    ico(( 0.28, -0.45, 1.05), 0.10, eye_m)
    # Claws
    cyl((-0.70, -0.05, 0.55), 0.15, 0.40, claw_m, rot=(0, 75, 20))
    cyl(( 0.70, -0.05, 0.55), 0.15, 0.40, claw_m, rot=(0, 75, -20))
    ico((-0.92, -0.05, 0.65), 0.20, claw_m)
    ico(( 0.92, -0.05, 0.65), 0.20, claw_m)
    # # emblem on shell
    cyl((0, -0.52, 0.65), 0.18, 0.04, hash_m)


def sprite_imp() -> None:
    """Infinite Imp — purple body, loop-shaped horns."""
    body_m = mat("ibody", (0.45, 0.10, 0.60), roughness=0.4)
    horn_m = mat("ihorn", (0.25, 0.05, 0.35))
    eye_m  = mat("ieye",  (1.0,  0.6,  0.0), emission=(1.0, 0.5, 0.0))

    # Body — stubby biped
    ico((0, 0, 0.50), 0.42, body_m)
    cube((0, 0, 0.85), 0.7, body_m, scale=(0.55, 0.40, 0.45))
    # Head
    ico((0, 0, 1.42), 0.40, body_m)
    # Glowing eyes
    ico((-0.14, -0.32, 1.50), 0.10, eye_m)
    ico(( 0.14, -0.32, 1.50), 0.10, eye_m)
    # Loop horns — torus
    torus((-0.22, 0, 1.82), 0.14, 0.04, horn_m)
    torus(( 0.22, 0, 1.82), 0.14, 0.04, horn_m)
    # Tail
    cyl((0, 0.30, 0.20), 0.06, 0.55, body_m, rot=(35, 0, 0))
    cone((0, 0.55, -0.05), 0.12, 0.22, horn_m)
    # Arms
    cyl((-0.55, 0, 0.85), 0.09, 0.42, body_m, rot=(0, 90, 25))
    cyl(( 0.55, 0, 0.85), 0.09, 0.42, body_m, rot=(0, 90, -25))


def sprite_wyrm() -> None:
    """While Wyrm — teal segmented coil."""
    seg_m  = mat("wseg",  (0.10, 0.65, 0.60), roughness=0.35)
    eye_m  = mat("weye",  (1.0,  0.9,  0.1), emission=(1.0, 0.8, 0.0))
    fang_m = mat("wfang", (0.95, 0.95, 0.95))

    # Segments arranged in a coil
    positions = [
        (0, 0, 0.30), (-0.30, 0.10, 0.55), (-0.45, 0, 0.85),
        (-0.30, -0.15, 1.15), (0, -0.20, 1.35), (0.30, -0.10, 1.45),
    ]
    radii = [0.32, 0.28, 0.26, 0.24, 0.22, 0.38]   # last is head
    for pos, r in zip(positions, radii):
        ico(pos, r, seg_m)

    # Eyes on head
    ico((0.18, -0.52, 1.52), 0.10, eye_m)
    ico((-0.18, -0.52, 1.52), 0.10, eye_m)
    # Fangs
    cone(( 0.10, -0.72, 1.38), 0.05, 0.20, fang_m)
    cone((-0.10, -0.72, 1.38), 0.05, 0.20, fang_m)


def sprite_wraith() -> None:
    """Recursion Wraith — dark ghost, fractal-like trailing form."""
    body_m = mat("wrbody", (0.12, 0.08, 0.22), roughness=0.1, metallic=0.3)
    glow_m = mat("wrglow", (0.35, 0.05, 0.55), emission=(0.55, 0.05, 0.8))
    eye_m  = mat("wreye",  (0.8,  0.0,  1.0), emission=(0.7, 0.0, 1.0))

    # Main body — elongated upward
    ico((0, 0, 1.10), 0.52, body_m, subdivisions=3)
    # Shrinking echo copies behind
    for i, scale_f in enumerate([0.80, 0.60, 0.42, 0.28]):
        z = 0.72 - i * 0.18
        ico((0, 0.15 * i, z), 0.52 * scale_f, glow_m)
    # Eyes
    ico((-0.18, -0.40, 1.28), 0.11, eye_m)
    ico(( 0.18, -0.40, 1.28), 0.11, eye_m)
    # Wispy arms
    cyl((-0.55, 0, 1.10), 0.07, 0.45, body_m, rot=(0, 90, 30))
    cyl(( 0.55, 0, 1.10), 0.07, 0.45, body_m, rot=(0, 90, -30))


def sprite_lich() -> None:
    """Lambda Lich — skeleton with λ staff."""
    bone_m  = mat("lbone",   (0.82, 0.80, 0.72), roughness=0.5)
    robe_m  = mat("lrobe",   (0.12, 0.10, 0.18), roughness=0.6)
    staff_m = mat("lstaff",  (0.30, 0.20, 0.50), metallic=0.6)
    glow_m  = mat("lglow",   (0.55, 0.20, 0.90), emission=(0.55, 0.20, 0.90))

    # Skull head
    ico((0, 0, 1.55), 0.40, bone_m)
    # Jaw
    cube((0, -0.22, 1.32), 0.26, bone_m, scale=(1.1, 0.6, 0.45))
    # Eye sockets glow
    ico((-0.14, -0.32, 1.58), 0.09, glow_m)
    ico(( 0.14, -0.32, 1.58), 0.09, glow_m)
    # Robe body
    cone((0, 0, 0.70), 0.50, 1.10, robe_m)
    # Arm bones
    cyl((-0.52, 0, 0.96), 0.06, 0.42, bone_m, rot=(0, 90, 15))
    cyl(( 0.52, 0, 0.96), 0.06, 0.42, bone_m, rot=(0, 90, -15))
    # Staff
    cyl((0.75, 0, 1.05), 0.04, 1.10, staff_m)
    # λ orb at top of staff
    ico((0.75, 0, 1.65), 0.16, glow_m)


def sprite_ogre() -> None:
    """Index Error Ogre — massive orange brute, [] bracket fists."""
    body_m  = mat("obody", (0.80, 0.40, 0.08), roughness=0.6)
    fist_m  = mat("ofist", (0.65, 0.30, 0.05), metallic=0.3)
    eye_m   = mat("oeye",  (0.10, 0.10, 0.10))

    # Huge torso
    cube((0, 0, 0.85), 1.1, body_m, scale=(0.70, 0.50, 0.65))
    ico((0, 0, 1.58), 0.52, body_m)
    # Brow ridge
    cube((0, -0.42, 1.72), 0.80, body_m, scale=(1, 0.4, 0.25))
    # Eyes
    ico((-0.18, -0.46, 1.60), 0.12, eye_m)
    ico(( 0.18, -0.46, 1.60), 0.12, eye_m)
    # Legs
    cyl((-0.25, 0, 0.22), 0.22, 0.65, body_m)
    cyl(( 0.25, 0, 0.22), 0.22, 0.65, body_m)
    # Arms — thick
    cyl((-0.80, 0, 0.95), 0.18, 0.70, body_m, rot=(0, 88, 15))
    cyl(( 0.80, 0, 0.95), 0.18, 0.70, body_m, rot=(0, 88, -15))
    # [] bracket fists
    cube((-1.25, 0, 0.85), 0.38, fist_m, scale=(0.6, 0.55, 0.85))
    cube(( 1.25, 0, 0.85), 0.38, fist_m, scale=(0.6, 0.55, 0.85))


def sprite_specter() -> None:
    """Slice Specter — translucent cyan ghost, blade arm."""
    ghost_m = mat("sghost", (0.20, 0.85, 0.90), roughness=0.05, metallic=0.2,
                  emission=(0.10, 0.50, 0.55))
    blade_m = mat("sblade", (0.80, 0.95, 1.00), metallic=0.9, roughness=0.05)
    eye_m   = mat("seye2",  (1.0,  1.0,  0.2), emission=(1.0, 1.0, 0.0))

    # Ghost body — large teardrop
    ico((0, 0, 1.0), 0.55, ghost_m, subdivisions=3)
    # Trailing fade
    for i, r in enumerate([0.40, 0.28, 0.16]):
        ico((0, 0.18*i, 0.45 - 0.18*i), r, ghost_m)
    # Eyes
    ico((-0.16, -0.44, 1.18), 0.10, eye_m)
    ico(( 0.16, -0.44, 1.18), 0.10, eye_m)
    # Blade arm (right)
    cyl((0.55, 0, 1.0), 0.08, 0.65, ghost_m, rot=(0, 90, -20))
    cube((0.92, -0.10, 1.08), 0.55, blade_m, scale=(0.15, 0.04, 0.9))


def sprite_knight() -> None:
    """KeyError Knight — silver armour, key-shaped sword."""
    armour_m = mat("karmour", (0.72, 0.74, 0.78), metallic=0.85, roughness=0.2)
    visor_m  = mat("kvisor",  (0.10, 0.10, 0.14), metallic=0.5)
    key_m    = mat("kkey",    (0.90, 0.82, 0.20), metallic=0.9, roughness=0.1)
    cape_m   = mat("kcape",   (0.65, 0.05, 0.10))

    build_humanoid_base(
        skin_color   = (0.72, 0.74, 0.78),
        suit_color   = (0.72, 0.74, 0.78),
        visor_color  = (0.10, 0.10, 0.14),
        accent_color = (0.50, 0.52, 0.55),
    )
    # Helmet crest
    cube((0, 0, 2.02), 0.18, armour_m, scale=(0.3, 1.0, 1.0))
    # Cape
    cube((0, 0.22, 0.95), 0.8, cape_m, scale=(0.85, 0.15, 0.80))
    # Key sword (right hand)
    cyl((0.85, -0.15, 0.72), 0.04, 0.90, key_m)            # blade shaft
    torus((0.85, -0.15, 1.25), 0.14, 0.04, key_m)           # key bow (ring)
    cube((0.85, -0.15, 0.85), 0.18, key_m, scale=(1.8, 0.5, 0.3))  # crossguard
    cube((0.85, -0.15, 1.10), 0.10, key_m, scale=(1, 1, 0.5))


def sprite_hydra() -> None:
    """Hash Hydra — green three-headed serpent body."""
    body_m   = mat("hbody", (0.12, 0.55, 0.22), roughness=0.4)
    head_m   = mat("hhead", (0.08, 0.42, 0.18))
    eye_m    = mat("heye",  (1.0,  0.85, 0.0), emission=(1.0, 0.7, 0.0))
    fang_m   = mat("hfang", (0.92, 0.92, 0.85))

    # Main body coil
    ico((0, 0, 0.55), 0.50, body_m)
    ico((0, 0.10, 0.92), 0.38, body_m)
    # Three necks
    neck_pos = [(-0.35, -0.15, 1.18), (0, -0.30, 1.30), (0.35, -0.15, 1.18)]
    head_pos = [(-0.55, -0.38, 1.58), (0, -0.52, 1.72), (0.55, -0.38, 1.58)]
    for np, hp in zip(neck_pos, head_pos):
        cyl(np, 0.12, 0.40, body_m)
        ico(hp, 0.28, head_m)
        # Eyes per head
        ico((hp[0]-0.10, hp[1]-0.22, hp[2]+0.05), 0.07, eye_m)
        ico((hp[0]+0.10, hp[1]-0.22, hp[2]+0.05), 0.07, eye_m)
        # Fang
        cone((hp[0], hp[1]-0.30, hp[2]-0.10), 0.05, 0.18, fang_m)


def sprite_drake() -> None:
    """Exception Drake — red dragon, error flame breath."""
    body_m  = mat("dbody", (0.75, 0.10, 0.05), roughness=0.4)
    wing_m  = mat("dwing", (0.55, 0.06, 0.03))
    flame_m = mat("dflame",(1.0,  0.50, 0.0), emission=(1.0, 0.45, 0.0))
    eye_m   = mat("deye",  (1.0,  0.0,  0.0), emission=(1.0, 0.0, 0.0))

    # Body
    ico((0, 0, 0.85), 0.55, body_m, subdivisions=2)
    ico((0, 0.20, 0.50), 0.35, body_m)   # tail segment
    # Neck + head
    ico((0, -0.30, 1.30), 0.28, body_m)
    ico((0, -0.52, 1.62), 0.38, body_m)
    # Eyes
    ico((-0.15, -0.72, 1.70), 0.10, eye_m)
    ico(( 0.15, -0.72, 1.70), 0.10, eye_m)
    # Horns
    cone((-0.18, -0.18, 1.98), 0.06, 0.40, body_m)
    cone(( 0.18, -0.18, 1.98), 0.06, 0.40, body_m)
    # Wings
    cube((-0.90, 0.12, 1.10), 0.8, wing_m, scale=(1.0, 0.08, 0.70))
    cube(( 0.90, 0.12, 1.10), 0.8, wing_m, scale=(1.0, 0.08, 0.70))
    # Flame
    cone((0, -0.90, 1.55), 0.22, 0.55, flame_m)
    ico((0, -1.12, 1.40), 0.18, flame_m)


def sprite_boss() -> None:
    """BOSS: NullByte — massive void giant, single 0 eye."""
    void_m  = mat("vbody", (0.02, 0.02, 0.05), roughness=0.05, metallic=0.4)
    zero_m  = mat("vzero", (0.0,  0.85, 1.0),  emission=(0.0, 0.85, 1.0))
    crack_m = mat("vcrack",(0.30, 0.0,  0.55),  emission=(0.30, 0.0, 0.55))
    aura_m  = mat("vaura", (0.10, 0.0,  0.20),  roughness=0.0, metallic=0.0,
                  emission=(0.15, 0.0, 0.30))

    # Massive body
    ico((0, 0, 1.10), 0.90, void_m, subdivisions=3)
    # Shoulder mass
    ico((-0.75, 0, 1.10), 0.45, void_m)
    ico(( 0.75, 0, 1.10), 0.45, void_m)
    # Head mass
    ico((0, -0.15, 2.05), 0.60, void_m)
    # Single 0 eye — torus centre
    torus((0, -0.68, 2.15), 0.22, 0.07, zero_m)
    ico((0, -0.68, 2.15), 0.08, zero_m)    # inner dot
    # Cracks / energy lines
    cyl((-0.35, -0.60, 1.30), 0.04, 0.55, crack_m, rot=(25, 0, -20))
    cyl(( 0.35, -0.60, 1.30), 0.04, 0.55, crack_m, rot=(25, 0,  20))
    # Aura ring
    torus((0, 0, 1.10), 1.10, 0.06, aura_m)
    # Arms
    cyl((-1.15, 0, 1.10), 0.18, 0.80, void_m, rot=(0, 90, 10))
    cyl(( 1.15, 0, 1.10), 0.18, 0.80, void_m, rot=(0, 90, -10))
    # Fists
    ico((-1.60, 0, 1.18), 0.26, void_m)
    ico(( 1.60, 0, 1.18), 0.26, void_m)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — render all sprites
# ══════════════════════════════════════════════════════════════════════════════

SPRITES: list[tuple[str, callable]] = [
    ("player",  sprite_player),
    ("slime",   sprite_slime),
    ("crab",    sprite_crab),
    ("imp",     sprite_imp),
    ("wyrm",    sprite_wyrm),
    ("wraith",  sprite_wraith),
    ("lich",    sprite_lich),
    ("ogre",    sprite_ogre),
    ("specter", sprite_specter),
    ("knight",  sprite_knight),
    ("hydra",   sprite_hydra),
    ("drake",   sprite_drake),
    ("boss",    sprite_boss),
]


def main() -> None:
    print(f"\n{'='*55}")
    print(f"  SHAPE Agent 16 — Blender Sprite Generator")
    print(f"  Output: {OUT_DIR}")
    print(f"{'='*55}\n")

    for name, builder in SPRITES:
        print(f"Building: {name} ...")
        clear_scene()
        add_camera()
        add_key_light()
        add_fill_light()
        builder()
        render(name)

    print(f"\n✅  All {len(SPRITES)} sprites rendered to: {OUT_DIR}\n")


main()
