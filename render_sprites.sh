#!/usr/bin/env bash
# render_sprites.sh — Render all RPG sprites with Blender (headless)
# Usage:  bash render_sprites.sh
# Requires Blender 3.x or 4.x installed.  No GUI needed.
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER_SCRIPT="$SCRIPT_DIR/blender/blender_sprite_gen.py"
OUT_DIR="$SCRIPT_DIR/assets/sprites"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   SHAPE Agent 16 — Sprite Renderer                      ║"
echo "║   Blender headless render — 13 characters               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Find Blender executable ───────────────────────────────────────────────────
if command -v blender &>/dev/null; then
    BLENDER="blender"
elif [ -f "/usr/bin/blender" ]; then
    BLENDER="/usr/bin/blender"
elif [ -f "/snap/bin/blender" ]; then
    BLENDER="/snap/bin/blender"
elif [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
else
    echo "❌  Blender not found in PATH."
    echo ""
    echo "Install Blender and try again:"
    echo "  sudo apt install blender          # Debian/Ubuntu/Kali"
    echo "  sudo snap install blender --classic"
    echo "  https://www.blender.org/download/"
    exit 1
fi

BLENDER_VER=$("$BLENDER" --version 2>/dev/null | head -1)
echo "Using: $BLENDER_VER"
echo "Script: $BLENDER_SCRIPT"
echo "Output: $OUT_DIR"
echo ""
echo "⏳  Rendering 13 sprites (this takes 1-3 minutes)..."
echo ""

mkdir -p "$OUT_DIR"

"$BLENDER" \
    --background \
    --python "$BLENDER_SCRIPT" \
    2>&1 | grep -E "(Building|Rendered|ERROR|Error|✓|✅|Warning)" || true

echo ""
echo "Checking output..."
COUNT=$(ls "$OUT_DIR"/*.png 2>/dev/null | wc -l)
echo "✅  $COUNT sprite(s) rendered in $OUT_DIR"
echo ""
ls -1 "$OUT_DIR"/*.png 2>/dev/null || echo "(none found — check errors above)"
echo ""
echo "Now launch the RPG:"
echo "  bash rpg_run.sh"
echo ""
