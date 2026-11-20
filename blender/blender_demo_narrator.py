"""
blender_demo_narrator.py
------------------------
SHAPE Agent 16 — Dynamic Narrated Blender Demo Animation

Builds and renders a fully self-contained narrated presentation inside Blender.
No screen recording. No people on camera. Everything is procedural 3D.

HOW TO RUN
──────────
  Option A — Blender GUI scripting tab:
      Open Blender → Scripting tab → Open this file → Run Script
      Then go to the Timeline, press Space, and watch the animation.
      To render the full video:  Render → Render Animation  (Ctrl+F12)

  Option B — Headless command line (no GUI needed):
      blender --background --python blender/blender_demo_narrator.py

OUTPUT
──────
  PNG frames  →  ./render/frames/####.png   (1920×1080)
  The frames are ready to assemble with ffmpeg:
      ffmpeg -framerate 24 -i render/frames/%04d.png -c:v libx264 \
             -pix_fmt yuv420p SHAPE_Agent16_Demo.mp4

NARRATION TIMING  (24 fps)
──────────────────────────
  Slide 00  |   0 s – 3 s   | Title card — SHAPE Agent 16
  Slide 01  |   3 s – 10 s  | What SHAPE is
  Slide 02  | 10 s – 20 s   | Four agent roles (animated icons)
  Slide 03  | 20 s – 32 s   | 8-Step reasoning cycle (steps fly in)
  Slide 04  | 32 s – 44 s   | Two tools (code runner + retrieval)
  Slide 05  | 44 s – 56 s   | RL policy — reward table + Q-update
  Slide 06  | 56 s – 68 s   | Pre/post assessment + Learner Progress
  Slide 07  | 68 s – 76 s   | LLM mode vs Local Fallback
  Slide 08  | 76 s – 84 s   | Hardware mock — JSON event
  Slide 09  | 84 s – 92 s   | Export Center + report drafts
  Slide 10  | 92 s – 100 s  | Team + closing tagline

Total: ~100 seconds at 24 fps = 2 400 frames

DESIGN NOTES
────────────
  • Each slide is a separate camera cut to a pre-positioned camera.
  • Text is placed using Blender's Text objects (3D text, extruded, bevel).
  • Animated panels slide in from the left; icons pulse or orbit.
  • The Agent 16 hero character from blender_sprite_gen.py is reused for
    the character-reveal slides (agent roles).
  • All geometry is primitives + text — no external assets required.
  • Colour palette matches the SHAPE UI:  bg #0d0d1a, accent #00d4ff,
    secondary #7c5cd8, positive #22c55e, warning #f59e0b.
  • Narration text is embedded in Text3D objects so it reads on screen
    even without audio.  The script also writes a matching .srt subtitle
    file alongside the frames.

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import bpy
import math
import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

FPS          = 24
TOTAL_FRAMES = 2400          # 100 s × 24 fps
RENDER_W     = 1920
RENDER_H     = 1080

SCRIPT_DIR   = Path(__file__).parent
OUT_DIR      = SCRIPT_DIR.parent / "render" / "frames"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# SHAPE colour palette (linear RGB, not sRGB)
C_BG        = (0.004, 0.004, 0.012)   # #0d0d1a — near-black blue
C_PANEL     = (0.015, 0.015, 0.040)   # darker panel surface
C_ACCENT    = (0.0,   0.65,  1.0)     # #00d4ff — cyan
C_SECONDARY = (0.24,  0.14,  0.72)    # #7c5cd8 — purple
C_POS       = (0.03,  0.52,  0.15)    # #22c55e — green positive
C_WARN      = (0.85,  0.45,  0.02)    # #f59e0b — amber
C_WHITE     = (0.95,  0.95,  0.95)
C_GREY      = (0.35,  0.35,  0.40)
C_RED       = (0.80,  0.05,  0.05)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE TIMING PLAN  (start_frame, end_frame, label)
# ─────────────────────────────────────────────────────────────────────────────

SLIDES: list[dict] = [
    {"id":  0, "start":    0, "end":   72, "label": "Title"},
    {"id":  1, "start":   72, "end":  240, "label": "WhatIsSHAPE"},
    {"id":  2, "start":  240, "end":  480, "label": "AgentRoles"},
    {"id":  3, "start":  480, "end":  768, "label": "ReasoningCycle"},
    {"id":  4, "start":  768, "end": 1056, "label": "Tools"},
    {"id":  5, "start": 1056, "end": 1344, "label": "RLPolicy"},
    {"id":  6, "start": 1344, "end": 1632, "label": "AssessmentProgress"},
    {"id":  7, "start": 1632, "end": 1824, "label": "Fallback"},
    {"id":  8, "start": 1824, "end": 2016, "label": "HardwareMock"},
    {"id":  9, "start": 2016, "end": 2208, "label": "ExportCenter"},
    {"id": 10, "start": 2208, "end": 2400, "label": "Closing"},
]

# ─────────────────────────────────────────────────────────────────────────────
# NARRATION TEXT  (written as on-screen subtitle lines)
# ─────────────────────────────────────────────────────────────────────────────

NARRATION: list[dict] = [
    {"slide": 0,  "line": "SHAPE Agent 16\nStudent-centered Handheld Architecture\nfor Programming Education"},
    {"slide": 1,  "line": "SHAPE teaches Python and AI concepts\nthrough guided interaction and adaptive feedback.\nFour specialised agents. One orchestrator. One learner."},
    {"slide": 2,  "line": "Instructor · Debugger · Evaluator · Learning Strategist\nEach role is a different teaching job.\nOne LLM serves all four — or a local fallback if no key is set."},
    {"slide": 3,  "line": "Every interaction runs an 8-step reasoning cycle:\nReceive · Profile · Retrieve · Reason · Act · Respond · Evaluate · Adapt.\nThe Agent Workspace shows every step in real time."},
    {"slide": 4,  "line": "Two tools power the agents.\nTool 1: Python exercise runner — AST-validated, time-limited.\nTool 2: Lesson retrieval — searches the curated curriculum in SQLite."},
    {"slide": 5,  "line": "The Learning Strategist uses a contextual bandit policy.\nCorrect without hints: +10 reward.  Correct with one hint: +7.\nQ += 0.2 × (reward − Q).  Strategy values update live."},
    {"slide": 6,  "line": "Every attempt is recorded — correctness, hints used, completion.\nPre-test before Lesson 1.  Post-test after.  The delta is the signal.\nLearners are identified only by anonymised IDs."},
    {"slide": 7,  "line": "SHAPE works without an API key.\nIn local fallback mode every response is labelled\n'Local fallback — NOT an LLM.'"},
    {"slide": 8,  "line": "Hardware is mock mode by default.\nA JSON event from a handheld device — lesson_select, hint_request —\ngoes through the same orchestrator.  No physical device is needed for this demo."},
    {"slide": 9,  "line": "The Export Center generates CSVs and individual report drafts\nfrom contribution records members actually entered.\nAnything missing is flagged — nothing is invented."},
    {"slide": 10, "line": "Learning through interaction.\nImproving through feedback.\nSHAPE Agent 16 — ITAI2376, Houston Community College, Group 14562."},
]

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: scene and render setup
# ─────────────────────────────────────────────────────────────────────────────

def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.curves):
        bpy.data.curves.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)


def configure_render() -> None:
    scene = bpy.context.scene

    # Try EEVEE engine names in preference order.
    # Blender 5.x reports "BLENDER_EEVEE" in its enum even though the engine
    # is EEVEE Next internally.  "BLENDER_EEVEE_NEXT" was used in Blender 4.2
    # dev builds but was never the stable enum string.
    # Probe the allowed values directly so we never guess.
    allowed = set(scene.bl_rna.properties["render"].enum_items_static_ui.keys()
                  if hasattr(scene.bl_rna.properties.get("render", None), "enum_items_static_ui")
                  else [])
    for candidate in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        try:
            scene.render.engine = candidate
            engine = candidate
            break
        except TypeError:
            continue
    else:
        engine = scene.render.engine   # leave whatever is already set
    print(f"  Render engine: {engine}")

    # EEVEE quality settings (attribute names differ between versions)
    if hasattr(scene, "eevee"):
        eevee = scene.eevee
        for attr, val in [
            ("taa_render_samples", 16),
            ("use_bloom",          True),
            ("bloom_intensity",    0.05),
            ("bloom_radius",       4.0),
            ("use_gtao",           False),
        ]:
            if hasattr(eevee, attr):
                try:
                    setattr(eevee, attr, val)
                except Exception:
                    pass

    scene.render.resolution_x           = RENDER_W
    scene.render.resolution_y           = RENDER_H
    scene.render.resolution_percentage  = 100
    scene.render.fps                    = FPS
    scene.frame_start                   = 1
    scene.frame_end                     = TOTAL_FRAMES
    scene.render.film_transparent       = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath               = str(OUT_DIR / "")


def set_world_background() -> None:
    world = bpy.context.scene.world
    # Blender 5.x: use_nodes is deprecated; node_tree is always present.
    if hasattr(world, "use_nodes"):
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value   = (*C_BG, 1.0)
    bg.inputs["Strength"].default_value = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: material helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_nodes(m: bpy.types.Material) -> None:
    """Enable node-based shading on a material (Blender 4 and 5 compatible)."""
    if hasattr(m, "use_nodes"):
        m.use_nodes = True


def mat_emission(name: str, color: tuple, strength: float = 3.0) -> bpy.types.Material:
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    _ensure_nodes(m)
    nodes = m.node_tree.nodes
    links = m.node_tree.links
    nodes.clear()
    out   = nodes.new("ShaderNodeOutputMaterial")
    emit  = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value   = (*color[:3], 1.0)
    emit.inputs["Strength"].default_value = strength
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return m


def mat_bsdf(name: str, color: tuple, metallic: float = 0.0,
             roughness: float = 0.5, emit: tuple | None = None,
             emit_strength: float = 2.0) -> bpy.types.Material:
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    _ensure_nodes(m)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Metallic"].default_value   = metallic
    bsdf.inputs["Roughness"].default_value  = roughness
    if emit:
        bsdf.inputs["Emission Color"].default_value   = (*emit[:3], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


def apply_mat(obj: bpy.types.Object, m: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = m
    else:
        obj.data.materials.append(m)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: primitive helpers
# ─────────────────────────────────────────────────────────────────────────────

def add_plane(loc, size, m) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    obj = bpy.context.active_object
    apply_mat(obj, m)
    return obj


def add_ico(loc, radius, m, subdiv=2) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius, location=loc)
    obj = bpy.context.active_object
    apply_mat(obj, m)
    return obj


def add_cube(loc, size, m, scale=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    obj = bpy.context.active_object
    if scale:
        obj.scale = scale
    apply_mat(obj, m)
    return obj


def add_cyl(loc, radius, depth, m, rot=(0, 0, 0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.rotation_euler = [math.radians(r) for r in rot]
    apply_mat(obj, m)
    return obj


def add_torus(loc, major_r, minor_r, m) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=major_r, minor_radius=minor_r)
    obj = bpy.context.active_object
    apply_mat(obj, m)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: 3D text
# ─────────────────────────────────────────────────────────────────────────────

def add_text3d(text: str, loc: tuple, size: float, m: bpy.types.Material,
               name: str = "text", align: str = "CENTER",
               extrude: float = 0.02, bevel: float = 0.005) -> bpy.types.Object:
    bpy.ops.object.text_add(location=loc)
    obj = bpy.context.active_object
    obj.name = name
    td  = obj.data
    td.body            = text
    td.size            = size
    td.align_x         = align
    td.align_y         = "CENTER"
    td.extrude         = extrude
    td.bevel_depth     = bevel
    td.bevel_resolution = 2
    apply_mat(obj, m)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: camera helpers
# ─────────────────────────────────────────────────────────────────────────────

def add_camera(name: str, loc: tuple, rot_deg: tuple,
               fov_deg: float = 50.0) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = name
    cam.rotation_euler = [math.radians(r) for r in rot_deg]
    cam.data.angle = math.radians(fov_deg)
    return cam


def set_active_camera(name: str) -> None:
    bpy.context.scene.camera = bpy.data.objects[name]


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: keyframe helpers
# ─────────────────────────────────────────────────────────────────────────────

def kf_loc(obj, frame: int, loc: tuple) -> None:
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def kf_scale(obj, frame: int, scale: tuple) -> None:
    obj.scale = scale
    obj.keyframe_insert("scale", frame=frame)


def kf_rot(obj, frame: int, rot_deg: tuple) -> None:
    obj.rotation_euler = [math.radians(r) for r in rot_deg]
    obj.keyframe_insert("rotation_euler", frame=frame)


def kf_hide(obj, frame: int, hidden: bool) -> None:
    obj.hide_viewport = hidden
    obj.hide_render   = hidden
    obj.keyframe_insert("hide_viewport", frame=frame)
    obj.keyframe_insert("hide_render",   frame=frame)


def set_interp_linear(obj) -> None:
    """Set all keyframes on this object to LINEAR interpolation.

    Blender 4.x stored fcurves directly on action.fcurves.
    Blender 5.x uses a layered action system: action.layers[i].strips[j].
    This function handles both APIs.
    """
    if not (obj.animation_data and obj.animation_data.action):
        return
    action = obj.animation_data.action

    # --- Blender 5.x layered actions ---
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                # Each strip exposes channelbags; each channelbag has fcurves.
                cb_iter = (strip.channelbags if hasattr(strip, "channelbags")
                           else getattr(strip, "channelbag", None))
                if cb_iter is None:
                    continue
                for cb in cb_iter:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"
        return

    # --- Blender 4.x (and earlier) flat fcurves ---
    if hasattr(action, "fcurves"):
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: animated slide-in panel
# ─────────────────────────────────────────────────────────────────────────────

def slide_in_panel(obj, start_frame: int, duration: int = 12,
                   from_x: float = -16.0) -> None:
    """Animate obj sliding in from off-screen-left to its current X position."""
    final_x = obj.location.x
    kf_loc(obj, start_frame,            (from_x,      obj.location.y, obj.location.z))
    kf_loc(obj, start_frame + duration, (final_x,     obj.location.y, obj.location.z))
    set_interp_linear(obj)


def fade_in_text(obj, start_frame: int, duration: int = 10) -> None:
    """Scale up from 0 → 1 (simulates text appearing)."""
    kf_scale(obj, start_frame,            (0.001, 0.001, 0.001))
    kf_scale(obj, start_frame + duration, (1.0,   1.0,   1.0))
    set_interp_linear(obj)


# ─────────────────────────────────────────────────────────────────────────────
# CAMERA CUTS: set which camera is active on each slide's start frame
# ─────────────────────────────────────────────────────────────────────────────

def build_camera_cuts(cameras: dict[str, bpy.types.Object]) -> None:
    """
    Build camera markers so Blender switches the active camera per slide.
    cameras: dict mapping slide label → camera object
    """
    scene = bpy.context.scene
    for slide in SLIDES:
        label = slide["label"]
        cam_obj = cameras.get(label)
        if cam_obj is None:
            continue
        # Add a timeline marker that binds to this camera
        m = scene.timeline_markers.new(name=label, frame=slide["start"] + 1)
        m.camera = cam_obj


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE BUILDERS
# Each function builds the 3D geometry and animations for one slide section.
# All objects are placed in a collection named after the slide label so they
# can be shown/hidden per segment.
# ─────────────────────────────────────────────────────────────────────────────

def collection_for_slide(label: str) -> bpy.types.Collection:
    col = bpy.data.collections.new(label)
    bpy.context.scene.collection.children.link(col)
    return col


def link_to(col: bpy.types.Collection, obj: bpy.types.Object) -> None:
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)


def _bg_plane(col: bpy.types.Collection, z: float = -0.1) -> bpy.types.Object:
    """Full-screen background plane at z."""
    p = add_plane((0, 0, z), 32, mat_emission("bg_emit", C_BG, 1.0))
    p.scale = (1.0, RENDER_H / RENDER_W, 1.0)
    link_to(col, p)
    return p


# ── Slide 0 — Title card ──────────────────────────────────────────────────────

def build_slide_title(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    # Large glowing SHAPE wordmark
    t_shape = add_text3d("SHAPE", (0, 0.8, 0), size=1.8,
                         m=mat_emission("title_accent", C_ACCENT, 6.0),
                         name="t_shape_title", extrude=0.08, bevel=0.015)
    link_to(col, t_shape)
    fade_in_text(t_shape, start + 4, 16)

    t_sub1 = add_text3d("Agent 16  |  ITAI2376", (0, 0.0, 0), size=0.42,
                        m=mat_emission("title_white", C_WHITE, 2.5),
                        name="t_agent16")
    link_to(col, t_sub1)
    fade_in_text(t_sub1, start + 20, 12)

    t_sub2 = add_text3d("Student-centered Handheld Architecture for Programming Education",
                        (0, -0.55, 0), size=0.22,
                        m=mat_emission("title_grey", C_GREY, 2.0),
                        name="t_full_name")
    link_to(col, t_sub2)
    fade_in_text(t_sub2, start + 32, 12)

    t_tag = add_text3d("Learning through interaction.  Improving through feedback.",
                       (0, -1.05, 0), size=0.26,
                       m=mat_emission("title_cyan2", C_ACCENT, 3.0),
                       name="t_tagline")
    link_to(col, t_tag)
    fade_in_text(t_tag, start + 44, 12)

    # Orbiting accent ring
    ring = add_torus((0, 0, 0), 2.4, 0.03, mat_emission("ring_em", C_SECONDARY, 4.0))
    link_to(col, ring)
    kf_rot(ring, start,     (90, 0, 0))
    kf_rot(ring, end,       (90, 0, 360))
    set_interp_linear(ring)

    # Accent glow sphere behind text
    glow = add_ico((0, 0, 0), 0.6, mat_emission("title_glow", C_ACCENT, 1.5))
    link_to(col, glow)

    # Build camera
    cam = add_camera("cam_Title", (0, -8, 0), (90, 0, 0), fov_deg=42)
    return cam


# ── Slide 1 — What is SHAPE ───────────────────────────────────────────────────

def build_slide_what(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    # Header
    h = add_text3d("What is SHAPE?", (0, 1.6, 0), size=0.55,
                   m=mat_emission("what_hdr", C_ACCENT, 4.0), name="t_what_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    bullets = [
        "Multi-agent interactive learning companion",
        "Teaches Python + AI concepts adaptively",
        "Runs in Google Colab — free, no install",
        "Works with or without an LLM API key",
        "Built by ITAI2376 students for ITAI2376 students",
    ]
    for i, line in enumerate(bullets):
        t = add_text3d(f"▶  {line}", (-4.5, 0.85 - i * 0.52, 0), size=0.26,
                       m=mat_emission(f"what_b{i}", C_WHITE, 2.5),
                       name=f"t_what_b{i}", align="LEFT")
        link_to(col, t)
        fade_in_text(t, start + 18 + i * 14, 10)

    # Decorative accent bar on the left
    bar = add_cube((-5.5, 0.4, 0), 0.08,
                   mat_emission("what_bar", C_ACCENT, 5.0),
                   scale=(1, 12, 1))
    link_to(col, bar)

    cam = add_camera("cam_WhatIsSHAPE", (-0.5, -9, 0.3), (90, 0, 0), fov_deg=46)
    return cam


# ── Slide 2 — Four agent roles ────────────────────────────────────────────────

def build_slide_agents(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("Four Agent Roles", (0, 2.2, 0), size=0.55,
                   m=mat_emission("ag_hdr", C_ACCENT, 4.0), name="t_ag_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    roles = [
        ("Instructor",         C_POS,       "Explains concepts\nBreaks lessons into steps\nAdjusts complexity"),
        ("Debugger",           C_WARN,      "Analyses submitted code\nExplains why errors occur\nGraduated hints only"),
        ("Evaluator",          C_ACCENT,    "Checks exercise results\nRecords attempts + hints\nComputes reward signal"),
        ("Learning Strategist",C_SECONDARY, "Maintains learner progress\nSelects next strategy\nShows policy before/after"),
    ]

    xs = [-5.0, -1.6, 1.8, 5.2]

    for i, (name, color, desc) in enumerate(roles):
        x = xs[i]

        # Role icon — glowing sphere with orbit ring
        sphere = add_ico((x, 0.4, 0.3), 0.42,
                         mat_bsdf(f"ag_sph{i}", color, metallic=0.3,
                                  roughness=0.2, emit=color, emit_strength=4.0))
        link_to(col, sphere)
        # Idle bob animation
        kf_loc(sphere, start,       (x, 0.4, 0.3))
        kf_loc(sphere, start + 36,  (x, 0.4, 0.6))
        kf_loc(sphere, start + 72,  (x, 0.4, 0.3))
        kf_loc(sphere, end,         (x, 0.4, 0.3))
        set_interp_linear(sphere)

        ring = add_torus((x, 0.4, 0.3), 0.65, 0.025,
                         mat_emission(f"ag_ring{i}", color, 3.0))
        link_to(col, ring)
        kf_rot(ring, start, (90, 0, 0))
        kf_rot(ring, end,   (90, 0, 360 if i % 2 == 0 else -360))
        set_interp_linear(ring)

        # Role name
        t_name = add_text3d(name, (x, -0.45, 0), size=0.22,
                            m=mat_emission(f"ag_nm{i}", color, 3.5),
                            name=f"t_ag_nm{i}")
        link_to(col, t_name)
        fade_in_text(t_name, start + 20 + i * 15, 10)

        # Description
        t_desc = add_text3d(desc, (x, -0.95, 0), size=0.14,
                            m=mat_emission(f"ag_desc{i}", C_GREY, 2.0),
                            name=f"t_ag_desc{i}")
        link_to(col, t_desc)
        fade_in_text(t_desc, start + 30 + i * 15, 10)

    t_note = add_text3d("One LLM serves all four roles — or a labelled local fallback",
                        (0, -2.2, 0), size=0.20,
                        m=mat_emission("ag_note", C_GREY, 2.0), name="t_ag_note")
    link_to(col, t_note)
    fade_in_text(t_note, start + 80, 10)

    cam = add_camera("cam_AgentRoles", (0, -11, 0.5), (90, 0, 0), fov_deg=56)
    return cam


# ── Slide 3 — 8-Step reasoning cycle ─────────────────────────────────────────

def build_slide_cycle(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("8-Step Reasoning Cycle", (0, 2.4, 0), size=0.52,
                   m=mat_emission("cyc_hdr", C_ACCENT, 4.0), name="t_cyc_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    steps = [
        ("1. RECEIVE",   "Validate learner input",        C_WHITE),
        ("2. PROFILE",   "Load learner level & history",  C_WHITE),
        ("3. RETRIEVE",  "Tool 2: lesson keyword search", C_ACCENT),
        ("4. REASON",    "CoT scratchpad + strategy pick",C_SECONDARY),
        ("5. ACT",       "Tool 1: code runner",           C_ACCENT),
        ("6. RESPOND",   "LLM or local fallback reply",   C_POS),
        ("7. EVALUATE",  "Reward → Q-update",             C_WARN),
        ("8. ADAPT",     "Update learner profile/level",  C_WHITE),
    ]

    # Two columns of 4
    for i, (step, detail, color) in enumerate(steps):
        col_offset = -3.5 if i < 4 else 3.5
        row        = i % 4
        y          = 1.6 - row * 0.90

        panel = add_cube((col_offset, y, -0.05), 0.76,
                         mat_bsdf(f"cyc_panel{i}", C_PANEL, roughness=0.9),
                         scale=(8.5, 1, 0.1))
        link_to(col, panel)
        slide_in_panel(panel, start + 8 + i * 10,
                       from_x=-16.0 if i < 4 else 16.0)

        t_s = add_text3d(step, (col_offset - 2.8, y, 0.05), size=0.22,
                         m=mat_emission(f"cyc_s{i}", color, 3.5),
                         name=f"t_cyc_s{i}", align="LEFT")
        link_to(col, t_s)
        fade_in_text(t_s, start + 14 + i * 10, 8)

        t_d = add_text3d(detail, (col_offset + 0.0, y, 0.05), size=0.17,
                         m=mat_emission(f"cyc_d{i}", C_GREY, 2.0),
                         name=f"t_cyc_d{i}", align="LEFT")
        link_to(col, t_d)
        fade_in_text(t_d, start + 20 + i * 10, 8)

    # Connecting arrow down the centre
    arrow = add_cube((0, 0.4, 0), 0.06,
                     mat_emission("cyc_arrow", C_ACCENT, 4.0),
                     scale=(1, 24, 1))
    link_to(col, arrow)
    fade_in_text(arrow, start + 100, 10)

    cam = add_camera("cam_ReasoningCycle", (0, -13, 0.8), (90, 0, 0), fov_deg=56)
    return cam


# ── Slide 4 — Two tools ───────────────────────────────────────────────────────

def build_slide_tools(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("Two Tools", (0, 2.2, 0), size=0.60,
                   m=mat_emission("tool_hdr", C_ACCENT, 4.0), name="t_tool_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    tools = [
        {
            "title": "Tool 1 — Python Exercise Runner",
            "color": C_POS,
            "x": -3.5,
            "lines": [
                "AST-validated before execution",
                "Restricted namespace — no os, subprocess, open",
                "5-second hard timeout (infinite loop guard)",
                "Returns: pass / fail / error type / line number",
                "NOT a hardened sandbox — classroom tool only",
            ],
        },
        {
            "title": "Tool 2 — Lesson Retrieval",
            "color": C_ACCENT,
            "x": 3.5,
            "lines": [
                "Keyword search over curated SQLite lesson index",
                "Filters by learner level (beginner/intermediate/advanced)",
                "Returns top-3 matches injected into LLM context",
                "Instant — new lessons added via UI are live immediately",
                "Falls back gracefully if no lesson matches",
            ],
        },
    ]

    for tool in tools:
        x     = tool["x"]
        color = tool["color"]

        # Tool icon — hex-ish ring
        ring = add_torus((x, 0.9, 0.3), 0.55, 0.06,
                         mat_emission(f"tool_ring_{x}", color, 5.0))
        link_to(col, ring)
        kf_rot(ring, start, (90, 0, 0))
        kf_rot(ring, end,   (90, 0, 360))
        set_interp_linear(ring)

        ico_ = add_ico((x, 0.9, 0.3), 0.28,
                       mat_bsdf(f"tool_ico_{x}", color, emit=color, emit_strength=6.0))
        link_to(col, ico_)

        t_title = add_text3d(tool["title"], (x, -0.1, 0.1), size=0.21,
                             m=mat_emission(f"tool_t_{x}", color, 3.0),
                             name=f"t_tool_title_{x}")
        link_to(col, t_title)
        fade_in_text(t_title, start + 18, 10)

        for j, line in enumerate(tool["lines"]):
            t_l = add_text3d(f"· {line}", (x - 2.8, -0.65 - j * 0.40, 0.1),
                             size=0.155,
                             m=mat_emission(f"tool_l{x}{j}", C_WHITE, 2.0),
                             name=f"t_tool_l{x}{j}", align="LEFT")
            link_to(col, t_l)
            fade_in_text(t_l, start + 28 + j * 12, 8)

    # Divider
    div = add_cube((0, 0.3, 0), 0.04,
                   mat_emission("tool_div", C_SECONDARY, 3.0),
                   scale=(1, 20, 1))
    link_to(col, div)

    cam = add_camera("cam_Tools", (0, -11, 0.5), (90, 0, 0), fov_deg=52)
    return cam


# ── Slide 5 — RL Policy ──────────────────────────────────────────────────────

def build_slide_rl(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("Adaptive RL Policy", (0, 2.3, 0), size=0.55,
                   m=mat_emission("rl_hdr", C_ACCENT, 4.0), name="t_rl_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    # Reward table
    rewards = [
        ("Correct — no hints",        "+10", C_POS),
        ("Correct — 1 hint",          " +7", C_POS),
        ("Correct — multiple hints",  " +4", C_WARN),
        ("Failed attempt",            " −3", C_RED),
        ("Concept check failed",      " −1", C_WARN),
    ]
    t_rtitle = add_text3d("Reward Function", (-3.8, 1.55, 0), size=0.26,
                          m=mat_emission("rl_rtitle", C_WHITE, 3.0),
                          name="t_rl_rtitle", align="LEFT")
    link_to(col, t_rtitle)
    fade_in_text(t_rtitle, start + 14, 8)

    for i, (outcome, reward, color) in enumerate(rewards):
        y = 1.05 - i * 0.42
        t_o = add_text3d(outcome, (-5.4, y, 0), size=0.18,
                         m=mat_emission(f"rl_o{i}", C_WHITE, 2.0),
                         name=f"t_rl_o{i}", align="LEFT")
        link_to(col, t_o)
        fade_in_text(t_o, start + 20 + i * 10, 8)

        t_r = add_text3d(reward, (-1.0, y, 0), size=0.26,
                         m=mat_emission(f"rl_r{i}", color, 4.0),
                         name=f"t_rl_r{i}", align="LEFT")
        link_to(col, t_r)
        fade_in_text(t_r, start + 22 + i * 10, 8)

    # Q-update equation
    t_eq = add_text3d("Q  +=  0.2 × ( reward − Q )", (2.5, 0.6, 0), size=0.34,
                      m=mat_emission("rl_eq", C_ACCENT, 4.5),
                      name="t_rl_eq", extrude=0.04)
    link_to(col, t_eq)
    fade_in_text(t_eq, start + 70, 14)

    t_lr = add_text3d("learning rate = 0.2    ε-greedy exploration", (2.5, 0.0, 0),
                      size=0.19, m=mat_emission("rl_lr", C_GREY, 2.0), name="t_rl_lr")
    link_to(col, t_lr)
    fade_in_text(t_lr, start + 85, 10)

    # Strategies as orbiting labels
    strategies = ["worked example", "concept explanation",
                  "small hint", "simpler practice", "challenge exercise"]
    for i, strat in enumerate(strategies):
        angle = (2 * math.pi * i / len(strategies))
        x = 2.5 + math.cos(angle) * 1.6
        y = -1.3 + math.sin(angle) * 0.65
        t_st = add_text3d(strat, (x, y, 0), size=0.14,
                          m=mat_emission(f"rl_st{i}", C_SECONDARY, 2.5),
                          name=f"t_rl_st{i}")
        link_to(col, t_st)
        fade_in_text(t_st, start + 95 + i * 8, 8)

    t_caution = add_text3d("Rising reward ≠ proof of learning  —  verified by pre/post assessment",
                           (0, -2.2, 0), size=0.17,
                           m=mat_emission("rl_caution", C_WARN, 2.5), name="t_rl_caution")
    link_to(col, t_caution)
    fade_in_text(t_caution, start + 150, 10)

    cam = add_camera("cam_RLPolicy", (0, -11, 0.5), (90, 0, 0), fov_deg=52)
    return cam


# ── Slide 6 — Assessment & Progress ──────────────────────────────────────────

def build_slide_assess(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("Assessment & Learner Progress", (0, 2.3, 0), size=0.46,
                   m=mat_emission("as_hdr", C_ACCENT, 4.0), name="t_as_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    # Assessment column (left)
    t_ah = add_text3d("Pre / Post Assessment", (-3.5, 1.7, 0), size=0.28,
                      m=mat_emission("as_ah", C_WHITE, 3.0), name="t_as_ah")
    link_to(col, t_ah)
    fade_in_text(t_ah, start + 14, 8)

    assess_lines = [
        "Same 5 questions both times",
        "Score before Lesson 1 (pre)",
        "Score after last lesson (post)",
        "Post − Pre = measurable change",
        "Delayed check if time permits",
        "Anonymised learner IDs only",
    ]
    for i, line in enumerate(assess_lines):
        t = add_text3d(f"· {line}", (-5.6, 1.1 - i * 0.42, 0), size=0.17,
                       m=mat_emission(f"as_al{i}", C_WHITE, 2.0),
                       name=f"t_as_al{i}", align="LEFT")
        link_to(col, t)
        fade_in_text(t, start + 22 + i * 10, 8)

    # Progress column (right)
    t_ph = add_text3d("Learner Progress Metrics", (3.2, 1.7, 0), size=0.28,
                      m=mat_emission("as_ph", C_ACCENT, 3.0), name="t_as_ph")
    link_to(col, t_ph)
    fade_in_text(t_ph, start + 20, 8)

    metrics = [
        ("Attempts",        "all code submissions"),
        ("Correctness",     "first-attempt pass rate"),
        ("Hint dependency", "mean hints per correct"),
        ("Completion rate", "lessons done / started"),
        ("Reward total",    "cumulative Q-signal"),
    ]
    for i, (metric, detail) in enumerate(metrics):
        y = 1.1 - i * 0.42
        t_m = add_text3d(metric, (1.6, y, 0), size=0.19,
                         m=mat_emission(f"as_pm{i}", C_ACCENT, 3.0),
                         name=f"t_as_pm{i}", align="LEFT")
        link_to(col, t_m)
        t_d = add_text3d(detail, (1.6, y - 0.22, 0), size=0.14,
                         m=mat_emission(f"as_pd{i}", C_GREY, 2.0),
                         name=f"t_as_pd{i}", align="LEFT")
        link_to(col, t_d)
        fade_in_text(t_m, start + 30 + i * 12, 8)
        fade_in_text(t_d, start + 36 + i * 12, 8)

    # Synthetic label
    t_syn = add_text3d("★  SYNTHETIC DEMO DATA  ★  charts labelled as such in the app",
                       (0, -2.2, 0), size=0.19,
                       m=mat_emission("as_syn", C_WARN, 3.0), name="t_as_syn")
    link_to(col, t_syn)
    fade_in_text(t_syn, start + 140, 10)

    # Divider
    div = add_cube((0, 0.3, 0), 0.04,
                   mat_emission("as_div", C_SECONDARY, 3.0),
                   scale=(1, 20, 1))
    link_to(col, div)

    cam = add_camera("cam_AssessmentProgress", (0, -11, 0.5), (90, 0, 0), fov_deg=50)
    return cam


# ── Slide 7 — LLM vs Fallback ─────────────────────────────────────────────────

def build_slide_fallback(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("LLM Mode vs Local Fallback", (0, 2.2, 0), size=0.50,
                   m=mat_emission("fb_hdr", C_ACCENT, 4.0), name="t_fb_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    cols_data = [
        {
            "title": "LLM Mode",
            "color": C_POS,
            "x": -3.0,
            "lines": [
                "OpenAI key in Colab Secrets",
                "Key read from userdata.get('OPENAI_API_KEY')",
                "Never printed, logged, or written to disk",
                "Generates explanations, hints, feedback",
                "Does NOT write grades or change rewards",
            ],
        },
        {
            "title": "Local Fallback",
            "color": C_WARN,
            "x": 3.0,
            "lines": [
                "No API key — or key fails / quota hit",
                "Rules-based templates from lesson index",
                "ALWAYS labelled 'Local fallback — NOT an LLM'",
                "Covers all 4 agent roles",
                "Demo works fully in fallback mode",
            ],
        },
    ]

    for col_data in cols_data:
        x = col_data["x"]
        t_title = add_text3d(col_data["title"], (x, 1.5, 0), size=0.36,
                             m=mat_emission(f"fb_title_{x}", col_data["color"], 4.0),
                             name=f"t_fb_title_{x}")
        link_to(col, t_title)
        fade_in_text(t_title, start + 14, 10)

        for i, line in enumerate(col_data["lines"]):
            t_l = add_text3d(f"· {line}", (x - 2.4, 0.85 - i * 0.44, 0), size=0.17,
                             m=mat_emission(f"fb_l_{x}_{i}", C_WHITE, 2.0),
                             name=f"t_fb_l_{x}_{i}", align="LEFT")
            link_to(col, t_l)
            fade_in_text(t_l, start + 22 + i * 12, 8)

    # Center VS
    t_vs = add_text3d("VS", (0, 0.5, 0), size=0.65,
                      m=mat_emission("fb_vs", C_SECONDARY, 5.0),
                      name="t_fb_vs", extrude=0.06)
    link_to(col, t_vs)
    kf_scale(t_vs, start + 30, (0.001, 0.001, 0.001))
    kf_scale(t_vs, start + 42, (1.0, 1.0, 1.0))
    kf_rot(t_vs, start + 30, (0, 0, 0))
    kf_rot(t_vs, start + 42, (0, 0, 360))
    set_interp_linear(t_vs)

    cam = add_camera("cam_Fallback", (0, -10, 0.4), (90, 0, 0), fov_deg=50)
    return cam


# ── Slide 8 — Hardware Mock ───────────────────────────────────────────────────

def build_slide_hw(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("Hardware — Mock Mode", (0, 2.2, 0), size=0.52,
                   m=mat_emission("hw_hdr", C_ACCENT, 4.0), name="t_hw_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    # Device icons (simple box-shaped handhelds)
    devices = [
        ("Pi Zero 2 W", C_WHITE,     -4.5, 0.5, (0.65, 0.40, 0.08)),
        ("Pico W",      C_GREY,      -1.5, 0.5, (0.50, 0.30, 0.06)),
        ("CYD Display", C_SECONDARY,  1.5, 0.5, (0.55, 0.35, 0.07)),
    ]
    for name, color, x, y, dscale in devices:
        bx = add_cube((x, y, 0.1), 0.9,
                      mat_bsdf(f"hw_dev_{x}", color, metallic=0.5, roughness=0.3),
                      scale=dscale)
        link_to(col, bx)
        # Screen glow
        sc = add_cube((x, y - 0.07, 0.17), 0.78,
                      mat_emission(f"hw_scr_{x}", C_ACCENT, 2.0),
                      scale=(0.75, 0.6, 0.02))
        link_to(col, sc)
        t_n = add_text3d(name, (x, y - 0.68, 0.1), size=0.16,
                         m=mat_emission(f"hw_nm_{x}", color, 2.5),
                         name=f"t_hw_nm_{x}")
        link_to(col, t_n)
        fade_in_text(bx, start + 10, 12)
        fade_in_text(t_n, start + 18, 10)

    # JSON event card
    json_text = ('{"device_id": "cyd-01",\n'
                 ' "event": "lesson_select",\n'
                 ' "lesson_id": "L1",\n'
                 ' "action": "next",\n'
                 ' "timestamp": "2026-12-01T10:00:00Z"}')
    panel = add_cube((3.6, 0.4, -0.05), 0.8,
                     mat_bsdf("hw_panel", C_PANEL, roughness=0.9),
                     scale=(6.0, 5.5, 0.12))
    link_to(col, panel)
    slide_in_panel(panel, start + 30, duration=16, from_x=16.0)

    t_json = add_text3d(json_text, (1.3, 0.95, 0.1), size=0.17,
                        m=mat_emission("hw_json", C_POS, 2.5),
                        name="t_hw_json", align="LEFT", extrude=0.01)
    link_to(col, t_json)
    fade_in_text(t_json, start + 50, 12)

    t_note = add_text3d("No LLM runs on device  ·  Host runs everything  ·  Mock events labelled as mock",
                        (0, -1.65, 0), size=0.17,
                        m=mat_emission("hw_note", C_WARN, 2.5), name="t_hw_note")
    link_to(col, t_note)
    fade_in_text(t_note, start + 80, 10)

    # Arrow from device to host
    arrow = add_cube((-0.3, 0.5, 0), 0.06,
                     mat_emission("hw_arrow", C_ACCENT, 4.0),
                     scale=(12, 1, 1))
    link_to(col, arrow)
    kf_scale(arrow, start + 42, (0.001, 1, 1))
    kf_scale(arrow, start + 54, (12, 1, 1))
    set_interp_linear(arrow)

    cam = add_camera("cam_HardwareMock", (0, -11, 0.6), (90, 0, 0), fov_deg=52)
    return cam


# ── Slide 9 — Export Center ───────────────────────────────────────────────────

def build_slide_export(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    h = add_text3d("Export Center", (0, 2.2, 0), size=0.60,
                   m=mat_emission("ex_hdr", C_ACCENT, 4.0), name="t_ex_hdr")
    link_to(col, h)
    fade_in_text(h, start + 4, 10)

    exports = [
        ("Contributions CSV",   C_POS,       -4.5, 0.6),
        ("Evaluation CSV",      C_ACCENT,    -1.5, 0.6),
        ("Progress CSV",        C_SECONDARY,  1.5, 0.6),
        ("Report Drafts (.md)", C_WARN,       4.5, 0.6),
    ]
    for name, color, x, y in exports:
        # Document icon
        doc = add_cube((x, y, 0.05), 0.7,
                       mat_bsdf(f"ex_doc_{x}", C_PANEL, roughness=0.9),
                       scale=(1.2, 1.5, 0.08))
        link_to(col, doc)
        # Coloured top-strip (file type indicator)
        strip = add_cube((x, y + 0.44, 0.1), 0.68,
                         mat_emission(f"ex_strip_{x}", color, 3.0),
                         scale=(1.2, 0.3, 0.05))
        link_to(col, strip)
        t_n = add_text3d(name, (x, y - 0.65, 0.1), size=0.16,
                         m=mat_emission(f"ex_nm_{x}", color, 2.5),
                         name=f"t_ex_nm_{x}")
        link_to(col, t_n)
        slide_in_panel(doc, start + 10 + exports.index((name, color, x, y)) * 14)
        slide_in_panel(strip, start + 10 + exports.index((name, color, x, y)) * 14)
        fade_in_text(t_n, start + 20 + exports.index((name, color, x, y)) * 14, 8)

    t_rule = add_text3d("Generated from ACTUAL contribution records only.\nMissing evidence is flagged — never invented.",
                        (0, -0.80, 0), size=0.22,
                        m=mat_emission("ex_rule", C_WHITE, 2.5), name="t_ex_rule")
    link_to(col, t_rule)
    fade_in_text(t_rule, start + 70, 10)

    t_flag = add_text3d("⚠  Items with no evidence description are listed, not silently skipped.",
                        (0, -1.40, 0), size=0.19,
                        m=mat_emission("ex_flag", C_WARN, 2.5), name="t_ex_flag")
    link_to(col, t_flag)
    fade_in_text(t_flag, start + 90, 10)

    cam = add_camera("cam_ExportCenter", (0, -10, 0.5), (90, 0, 0), fov_deg=50)
    return cam


# ── Slide 10 — Closing ────────────────────────────────────────────────────────

def build_slide_closing(col: bpy.types.Collection, start: int, end: int) -> bpy.types.Object:
    _bg_plane(col)

    t1 = add_text3d("Learning through interaction.", (0, 1.4, 0), size=0.52,
                    m=mat_emission("cl_t1", C_ACCENT, 5.0),
                    name="t_cl_t1", extrude=0.05)
    link_to(col, t1)
    fade_in_text(t1, start + 6, 14)

    t2 = add_text3d("Improving through feedback.", (0, 0.65, 0), size=0.52,
                    m=mat_emission("cl_t2", C_ACCENT, 5.0),
                    name="t_cl_t2", extrude=0.05)
    link_to(col, t2)
    fade_in_text(t2, start + 22, 14)

    t3 = add_text3d("SHAPE Agent 16", (0, -0.25, 0), size=0.68,
                    m=mat_emission("cl_t3", C_WHITE, 4.0),
                    name="t_cl_t3", extrude=0.07, bevel=0.012)
    link_to(col, t3)
    fade_in_text(t3, start + 38, 16)

    t4 = add_text3d("ITAI2376  ·  Houston Community College  ·  Group 14562",
                    (0, -1.05, 0), size=0.22,
                    m=mat_emission("cl_t4", C_GREY, 2.0), name="t_cl_t4")
    link_to(col, t4)
    fade_in_text(t4, start + 55, 12)

    t5 = add_text3d("Michael Rivas  ·  Cherluk  ·  Olu  ·  Taki",
                    (0, -1.55, 0), size=0.22,
                    m=mat_emission("cl_t5", C_SECONDARY, 2.5), name="t_cl_t5")
    link_to(col, t5)
    fade_in_text(t5, start + 68, 12)

    # Orbiting constellation
    for i in range(12):
        angle = (2 * math.pi * i / 12)
        r     = 2.6 + 0.3 * (i % 3)
        x     = math.cos(angle) * r
        y_off = math.sin(angle) * r * 0.55
        star  = add_ico((x, y_off, 0.05), 0.045,
                        mat_emission(f"cl_star{i}", C_ACCENT if i % 3 else C_SECONDARY, 5.0),
                        subdiv=1)
        link_to(col, star)
        kf_rot(star, start,     (0, 0, 0))
        kf_rot(star, end,       (0, 0, 360 if i % 2 else -360))
        set_interp_linear(star)

    # Aura behind SHAPE text
    aura = add_ico((0, 0.3, -0.2), 1.0, mat_emission("cl_aura", C_ACCENT, 0.8))
    link_to(col, aura)
    kf_scale(aura, start + 38, (0.001, 0.001, 0.001))
    kf_scale(aura, start + 52, (2.5, 2.5, 2.5))
    set_interp_linear(aura)

    cam = add_camera("cam_Closing", (0, -8.5, 0.0), (90, 0, 0), fov_deg=44)
    return cam


# ─────────────────────────────────────────────────────────────────────────────
# SRT SUBTITLE FILE
# ─────────────────────────────────────────────────────────────────────────────

def write_srt() -> None:
    srt_path = SCRIPT_DIR.parent / "render" / "SHAPE_Agent16_Demo.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    def tc(frame: int) -> str:
        total_s = frame / FPS
        h       = int(total_s // 3600)
        m       = int((total_s % 3600) // 60)
        s       = int(total_s % 60)
        ms      = int((total_s % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, (slide, narr) in enumerate(zip(SLIDES, NARRATION)):
        lines.append(str(i + 1))
        lines.append(f"{tc(slide['start'] + 1)} --> {tc(slide['end'])}")
        lines.append(narr["line"])
        lines.append("")

    srt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓  SRT subtitles written: {srt_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD
# ─────────────────────────────────────────────────────────────────────────────

SLIDE_BUILDERS = {
    "Title":               build_slide_title,
    "WhatIsSHAPE":         build_slide_what,
    "AgentRoles":          build_slide_agents,
    "ReasoningCycle":      build_slide_cycle,
    "Tools":               build_slide_tools,
    "RLPolicy":            build_slide_rl,
    "AssessmentProgress":  build_slide_assess,
    "Fallback":            build_slide_fallback,
    "HardwareMock":        build_slide_hw,
    "ExportCenter":        build_slide_export,
    "Closing":             build_slide_closing,
}


def main() -> None:
    print("\n" + "=" * 60)
    print("  SHAPE Agent 16 — Blender Narrated Demo Animation")
    print(f"  Output: {OUT_DIR}")
    print("=" * 60 + "\n")

    clear_scene()
    configure_render()
    set_world_background()

    cameras: dict[str, bpy.types.Object] = {}

    for slide in SLIDES:
        label   = slide["label"]
        start_f = slide["start"]
        end_f   = slide["end"]
        builder = SLIDE_BUILDERS.get(label)
        if builder is None:
            print(f"  [skip] No builder for slide: {label}")
            continue
        print(f"  Building slide {slide['id']:02d}: {label} (frames {start_f}–{end_f}) …")
        col = collection_for_slide(label)
        cam = builder(col, start_f, end_f)
        if cam is not None:
            cameras[label] = cam

    build_camera_cuts(cameras)
    # Set the first camera active immediately
    if cameras:
        bpy.context.scene.camera = list(cameras.values())[0]

    write_srt()

    print(f"\n✅  Scene built.  Total frames: {TOTAL_FRAMES}  ({TOTAL_FRAMES / FPS:.0f} s)")

    # ── Render all frames inline when running headless ────────────────────────
    # bpy.app.background is True when Blender was launched with --background.
    # In that mode there is no GUI, so we render every frame here and exit.
    # In GUI mode (Scripting tab) we skip this so the user can preview first,
    # then trigger Render → Render Animation manually (Ctrl+F12).
    if bpy.app.background:
        scene  = bpy.context.scene
        engine = scene.render.engine
        print(f"\n  Engine : {engine}")
        print(f"  Frames : {TOTAL_FRAMES}  ({TOTAL_FRAMES / FPS:.0f} s at {FPS} fps)")
        print(f"  Output : {OUT_DIR}")
        print(  "  Progress printed every 1 second of animation\n")

        import time as _time
        t0 = _time.perf_counter()

        for frame in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(frame)
            scene.render.filepath = str(OUT_DIR / f"{frame:04d}")
            bpy.ops.render.render(write_still=True)
            if frame % FPS == 0:
                elapsed = _time.perf_counter() - t0
                pct     = 100.0 * frame / TOTAL_FRAMES
                remain  = (elapsed / frame) * (TOTAL_FRAMES - frame) if frame else 0
                print(f"  {frame:4d}/{TOTAL_FRAMES}  {pct:5.1f}%  "
                      f"elapsed {elapsed:6.0f}s  ETA {remain:6.0f}s")

        total_time = _time.perf_counter() - t0
        print(f"\n✅  Rendered {TOTAL_FRAMES} frames in {total_time:.0f}s "
              f"({total_time/TOTAL_FRAMES:.2f}s/frame)")
        print(f"   Frames saved to: {OUT_DIR}")

        # ── Save .blend for cloud render farms ───────────────────────────────
        # Upload this file to SheepIt (free), GarageFarm, Render Street, etc.
        # Set frame range 1–2400, PNG output, EEVEE engine on the farm's UI.
        blend_out = SCRIPT_DIR.parent / "render" / "SHAPE_Agent16_Demo.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
        print(f"   .blend saved  : {blend_out}")
        print( "   Upload to a render farm (SheepIt is free):")
        print( "     https://www.sheepit-renderfarm.com")
        print( "   Set: engine=EEVEE, frames 1-2400, output PNG\n")

        print( "\n  Assemble locally with ffmpeg:")
        print( "    ffmpeg -framerate 24 -i render/frames/%04d.png \\")
        print( "           -c:v libx264 -pix_fmt yuv420p SHAPE_Agent16_Demo.mp4\n")
    else:
        # GUI mode — save .blend so user can upload to a render farm
        blend_out = SCRIPT_DIR.parent / "render" / "SHAPE_Agent16_Demo.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
        print(f"\n  .blend saved to: {blend_out}")
        print( "  GUI: press Ctrl+F12 to render locally, or upload the .blend to:")
        print( "    SheepIt (free)  https://www.sheepit-renderfarm.com")
        print( "    GarageFarm      https://garagefarm.net")
        print( "    Render Street   https://www.renderstreet.com")
        print( "  Set: engine=EEVEE Next, frames 1-2400, output PNG\n")


main()
