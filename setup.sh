#!/usr/bin/env bash
# setup.sh — SHAPE Agent 16 one-command bootstrap for Kali / Debian / Ubuntu
# Usage:  bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

VENV_DIR=".venv"
PYTHON=$(which python3)

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        SHAPE Agent 16 — Setup Bootstrap                  ║"
echo "║        ITAI2376_14562  |  Group: Michael, Cherluk,       ║"
echo "║                          Olu, Taki                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Create virtual environment ────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/4] Creating virtual environment in $VENV_DIR ..."
    $PYTHON -m venv "$VENV_DIR"
else
    echo "[1/4] Virtual environment already exists — skipping."
fi

# ── 2. Install dependencies ───────────────────────────────────────────────────
echo "[2/4] Installing dependencies (groq, gradio, python-dotenv) ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r requirements.txt
echo "      Done."

# ── 3. Prompt for Groq API key ────────────────────────────────────────────────
echo ""
echo "[3/4] Groq API key setup"
echo "      ► Get a FREE key at: https://console.groq.com"
echo "      ► No credit card required."
echo ""

if [ -f ".env" ] && grep -q "GROQ_API_KEY" .env; then
    echo "      Found existing .env with GROQ_API_KEY — skipping."
else
    read -rp "      Paste your Groq API key now (or press Enter to skip): " GROQ_KEY
    if [ -n "$GROQ_KEY" ]; then
        echo "GROQ_API_KEY=$GROQ_KEY" > .env
        echo "      Saved to .env"
    else
        echo "      Skipped. Run:  export GROQ_API_KEY=\"gsk_...\"  before launching."
    fi
fi

# ── 4. Seed the database ──────────────────────────────────────────────────────
echo ""
echo "[4/4] Seeding curriculum database ..."

# Load .env if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

"$VENV_DIR/bin/python" src/shape_main.py --seed

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Setup complete!                                         ║"
echo "║                                                          ║"
echo "║  To launch the web UI:                                   ║"
echo "║    bash run.sh                                           ║"
echo "║                                                          ║"
echo "║  Or manually:                                            ║"
echo "║    source .venv/bin/activate                             ║"
echo "║    python src/shape_main.py                              ║"
echo "║                                                          ║"
echo "║  Then open:  http://localhost:7860                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
