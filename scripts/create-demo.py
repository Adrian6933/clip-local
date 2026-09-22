"""Create an explicitly labelled synthetic local sample for manual UI verification."""
from pathlib import Path
import subprocess
import sys
import httpx

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from engine.core import FFMPEG, NO_WINDOW

folder = root / '.test-data'
folder.mkdir(exist_ok=True)
path = folder / 'ensayo-encuadres.mp4'
subprocess.run([FFMPEG, '-y', '-v', 'error', '-f', 'lavfi', '-i',
    'testsrc2=size=1280x720:rate=30:duration=8', '-f', 'lavfi', '-i',
    'sine=frequency=440:duration=8', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-shortest', str(path)], check=True, creationflags=NO_WINDOW)
with httpx.Client(base_url='http://127.0.0.1:4323/api', headers={'X-Clippa-Client':'studio'}, timeout=60) as client:
    response = client.post('/projects', json={'name':'Ensayo técnico · vídeo sintético'})
    response.raise_for_status()
    pid = response.json()['id']
    with path.open('rb') as video:
        response = client.post(f'/projects/{pid}/assets', content=video, headers={'X-File-Name':path.name})
    response.raise_for_status()
    print('Ensayo técnico importado:', pid)
