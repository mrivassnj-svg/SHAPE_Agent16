import sys, os, socket

# resolve project root regardless of cwd
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# find the first free port starting at 8502
def _free_port(start=8502, end=8600):
    for p in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise RuntimeError(f"No free port found in {start}-{end}")

PORT = _free_port()

from shape.store import init_db
init_db("shape.db")

from shape.ui import build_demo
import gradio as gr

demo = build_demo()

print(f"\n{'='*55}")
print(f"  SHAPE Agent 16  --  starting on port {PORT}")
print(f"  Local:   http://localhost:{PORT}")
print(f"  Network: http://0.0.0.0:{PORT}")
print(f"{'='*55}\n")

demo.launch(
    server_name="0.0.0.0",
    server_port=PORT,
    share=True,
    theme=gr.themes.Soft(),
    quiet=False,
)
