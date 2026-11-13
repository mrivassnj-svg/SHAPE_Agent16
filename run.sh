#!/usr/bin/env bash
# run.sh — Launch SHAPE Agent 16 web UI
# Usage:  bash run.sh
set -e

# Load .env if present
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run:  bash setup.sh"
    exit 1
fi

echo "Starting SHAPE Agent 16 at http://localhost:7860 ..."
.venv/bin/python src/shape_main.py
