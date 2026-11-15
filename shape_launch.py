import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from shape.store import init_db
init_db('shape.db')

from shape.ui import build_demo
import gradio as gr

demo = build_demo()
demo.launch(
    server_name="0.0.0.0",
    server_port=8502,
    share=True,
    theme=gr.themes.Soft(),
    quiet=False
)
