"""Local storage and media composition shared by API and worker."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('CLIPPA_DATA_DIR', str(ROOT / '.clippa-data'))).resolve()
FFMPEG = os.environ.get('CLIPPA_FFMPEG', str(ROOT / 'node_modules/ffmpeg-static/ffmpeg.exe'))
FFPROBE = os.environ.get('CLIPPA_FFPROBE', str(ROOT / 'node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe'))
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def uid():
    return str(uuid.uuid4())

@contextmanager
def db():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA / 'studio.sqlite3', timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def initialize():
    with db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, document TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, project_id TEXT, kind TEXT, status TEXT, progress REAL DEFAULT 0, error TEXT, spec TEXT, output TEXT, created REAL, heartbeat REAL)')

def projects():
    with db() as conn:
        return [json.loads(row['document']) for row in conn.execute('SELECT document FROM projects ORDER BY rowid DESC')]

def project(pid):
    with db() as conn:
        row = conn.execute('SELECT document FROM projects WHERE id=?', (pid,)).fetchone()
    if not row:
        raise KeyError('Proyecto no encontrado')
    return json.loads(row['document'])

def put_project(doc):
    with db() as conn:
        conn.execute('INSERT OR REPLACE INTO projects VALUES (?, ?)', (doc['id'], json.dumps(doc, ensure_ascii=False)))

def update_job(jid, **values):
    allowed = {'status', 'progress', 'error', 'output', 'heartbeat'}
    assert set(values) <= allowed
    with db() as conn:
        conn.execute('UPDATE jobs SET ' + ','.join(f'{key}=?' for key in values) + ' WHERE id=?', (*values.values(), jid))

def job(jid):
    with db() as conn:
        row = conn.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
    if not row:
        raise KeyError('Trabajo no encontrado')
    result = dict(row)
    result['spec'] = json.loads(result['spec'])
    return result

def enqueue(pid, kind, spec):
    jid = uid()
    with db() as conn:
        conn.execute('INSERT INTO jobs (id,project_id,kind,status,spec,created,heartbeat) VALUES (?,?,?,?,?,?,?)', (jid, pid, kind, 'queued', json.dumps(spec), time.time(), time.time()))
    return job(jid)

def probe(path):
    proc = subprocess.run([FFPROBE, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, timeout=45, creationflags=NO_WINDOW)
    if proc.returncode:
        raise ValueError('El archivo no es un vídeo válido o está dañado.')
    raw = json.loads(proc.stdout)
    videos = [s for s in raw.get('streams', []) if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')]
    if not videos:
        raise ValueError('El archivo no contiene una pista de vídeo.')
    v = videos[0]
    duration = float(raw.get('format', {}).get('duration') or v.get('duration') or 0)
    if duration <= 0:
        raise ValueError('No se puede determinar la duración del vídeo.')
    rotation = next((s.get('rotation', 0) for s in v.get('side_data_list', []) if 'rotation' in s), 0)
    w, h = v['width'], v['height']
    if abs(rotation) % 180 == 90:
        w, h = h, w
    return {'duration': duration, 'width': w, 'height': h, 'fps': v.get('avg_frame_rate'), 'hasAudio': any(s['codec_type'] == 'audio' for s in raw['streams']), 'hdr': v.get('color_transfer') in ('smpte2084', 'arib-std-b67'), 'sar': v.get('sample_aspect_ratio', '1:1')}

def crop_box(width, height, target_ratio, x, y):
    cw = min(width, height * target_ratio)
    ch = min(height, width / target_ratio)
    cw, ch = max(2, int(cw) // 2 * 2), max(2, int(ch) // 2 * 2)
    left = int(max(0, min(width - cw, x * width - cw / 2))) // 2 * 2
    top = int(max(0, min(height - ch, y * height - ch / 2))) // 2 * 2
    return cw, ch, left, top

def composition(meta, edit, width=1080, height=1920):
    if edit['layout'] == 'fit':
        return f'[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x111216,setsar=1[v]'
    def crop(subject, target_h):
        box = crop_box(meta['width'], meta['height'], width / target_h, subject['x'], subject['y'])
        return 'crop=' + ':'.join(str(n) for n in box) + f',scale={width}:{target_h},setsar=1'
    if edit['layout'] == 'split':
        return f"[0:v]split=2[a][b];[a]{crop(edit['a'], height//2)}[a1];[b]{crop(edit['b'], height//2)}[b1];[a1][b1]vstack=inputs=2[v]"
    return f"[0:v]{crop(edit['a'], height)}[v]"

def run_ffmpeg(args, jid, duration):
    work = DATA / 'work'
    work.mkdir(exist_ok=True)
    log = work / f'{jid}.log'
    with log.open('wb') as stderr:
        proc = subprocess.Popen([FFMPEG, '-hide_banner', '-y', '-nostdin', '-progress', 'pipe:1', '-stats_period', '0.5', *args], stdout=subprocess.PIPE, stderr=stderr, creationflags=NO_WINDOW)
        try:
            for raw in iter(proc.stdout.readline, b''):
                if job(jid)['status'] == 'cancel_requested':
                    proc.kill()
                    proc.wait()
                    raise InterruptedError('Trabajo cancelado')
                line = raw.decode('utf8', errors='replace').strip()
                progress = {}
                if line.startswith('out_time_us='):
                    try:
                        progress['progress'] = min(.99, max(0, int(line.split('=')[1]) / 1e6 / duration))
                    except ValueError:
                        pass
                update_job(jid, heartbeat=time.time(), **progress)
            if proc.wait() != 0:
                raise ValueError('No se pudo procesar el vídeo. Revisa el archivo y el diagnóstico local.')
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
