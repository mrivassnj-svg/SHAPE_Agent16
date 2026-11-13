#!/usr/bin/env bash
# rpg_run.sh — Launch SHAPE Agent 16 RPG (Streamlit)
# Usage:  bash rpg_run.sh
set -e

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run:  bash setup.sh"
    exit 1
fi

# Install streamlit if not already present
.venv/bin/pip install "streamlit>=1.35.0" --quiet

# Create assets directory for your Blender sprites
mkdir -p assets/sprites

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  SHAPE Agent 16 RPG                                      ║"
echo "║  Place your Blender sprite PNGs in: assets/sprites/      ║"
echo "║                                                          ║"
echo "║  Expected filenames:                                     ║"
echo "║    player.png  slime.png   crab.png   imp.png            ║"
echo "║    wyrm.png    wraith.png  lich.png   ogre.png           ║"
echo "║    specter.png knight.png  hydra.png  drake.png          ║"
echo "║    boss.png                                              ║"
echo "║                                                          ║"
echo "║  (Emoji fallbacks used if files are missing)             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Starting RPG at http://localhost:8501 ..."
echo ""

.venv/bin/streamlit run src/shape_rpg_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --theme.base dark \
    --theme.primaryColor "#e94560" \
    --theme.backgroundColor "#1a1a2e" \
    --theme.secondaryBackgroundColor "#16213e" \
    --theme.textColor "#eeeeee"
