import asyncio
from contextlib import asynccontextmanager
import json
import shutil
import time
from pathlib import Path
from typing import Literal
from urllib.parse import unquote
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict
from .core import DATA, FFMPEG, FFPROBE, db, initialize, uid, projects, project, put_project, probe, enqueue, job, update_job

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title='Clippa local', lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
ORIGINS = ['http://127.0.0.1:4322', 'http://localhost:4322', 'http://127.0.0.1:4323']
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=['GET', 'POST', 'PUT'], allow_headers=['Content-Type', 'X-File-Name', 'X-Clippa-Client'])

@app.middleware('http')
async def origin_guard(request, call_next):
    if request.method in ('POST', 'PUT'):
        if request.headers.get('origin') not in (None, *ORIGINS) or request.headers.get('x-clippa-client') != 'studio':
            return JSONResponse({'detail': 'Origen no autorizado'}, status_code=403)
    return await call_next(request)

@app.exception_handler(KeyError)
async def missing(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=404)

class Point(BaseModel):
    x: float = Field(default=.5, ge=0, le=1, allow_inf_nan=False)
    y: float = Field(default=.5, ge=0, le=1, allow_inf_nan=False)

class Edit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(default='Mi clip', min_length=1, max_length=150)
    start: float = Field(default=0, ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    layout: Literal['fit', 'single', 'split'] = 'fit'
    a: Point = Point(x=.3)
    b: Point = Point(x=.7)
    revision: int = Field(default=0, ge=0)

def valid_edit(pid, edit):
    p = project(pid)
    if not p.get('media'):
        raise HTTPException(409, 'Primero importa un vídeo válido.')
    if edit.end <= edit.start or edit.end > p['media']['duration'] + .05:
        raise HTTPException(422, 'El final debe ir después del inicio y dentro del vídeo.')
    return p

@app.get('/api/health')
def health():
    return {'ok': True, 'service': 'clippa-python', 'version': '0.2.0'}

@app.get('/api/capabilities')
def capabilities():
    return {'ffmpeg': Path(FFMPEG).is_file(), 'ffprobe': Path(FFPROBE).is_file(), 'transcription': False, 'faceTracking': False, 'diarization': False, 'storage': 'SQLite', 'engine': 'Python · FastAPI', 'freeBytes': shutil.disk_usage(DATA).free}

@app.get('/api/projects')
def list_projects():
    return {'projects': projects()}

@app.post('/api/projects')
async def create_project(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 10000:
            raise HTTPException(413, 'Solicitud demasiado grande')
    try:
        data = json.loads(raw)
        name = str(data.get('name', 'Nuevo proyecto')).strip()[:160] or 'Nuevo proyecto'
    except (ValueError, AttributeError):
        raise HTTPException(422, 'Nombre de proyecto inválido')
    p = {'id': uid(), 'name': name, 'status': 'empty', 'createdAt': time.time(), 'media': None, 'edit': None}
    put_project(p)
    return p

@app.get('/api/projects/{pid}')
def get_project(pid: str):
    return project(pid)

@app.post('/api/projects/{pid}/assets')
async def upload(pid: str, request: Request):
    p = project(pid)
    if p.get('media'):
        raise HTTPException(409, 'Este proyecto ya tiene un vídeo. Crea otro proyecto.')
    folder = DATA / pid
    folder.mkdir(exist_ok=True)
    temp = folder / f'{uid()}.upload'
    total = 0
    limit = min(5 * 1024**3, max(0, shutil.disk_usage(DATA).free - 512 * 1024**2))
    try:
        with temp.open('wb') as out:
            async for chunk in request.stream():
                total += len(chunk)
                if total > limit:
                    raise HTTPException(413, 'Archivo demasiado grande o espacio insuficiente.')
                await asyncio.to_thread(out.write, chunk)
        meta = await asyncio.to_thread(probe, temp)
        if meta['hdr'] or meta['sar'] not in ('1:1', '0:1', 'N/A'):
            raise HTTPException(422, 'Este vídeo usa HDR o píxeles no cuadrados. Convierte una copia a SDR con píxeles cuadrados antes de importarlo.')
        # Only one successful source per project. Exclusive link prevents concurrent replacement.
        source = folder / 'source'
        try:
            source.hardlink_to(temp)
        except FileExistsError:
            raise HTTPException(409, 'Ya se ha importado un vídeo en este proyecto.')
        meta.update({'bytes': total, 'originalName': unquote(request.headers.get('x-file-name', p['name']))[:200]})
        p.update(media=meta, status='processing', edit={'title': Path(p['name']).stem[:150], 'start': 0, 'end': min(30, meta['duration']), 'layout': 'fit', 'a': {'x': .3, 'y': .5}, 'b': {'x': .7, 'y': .5}, 'revision': 0})
        put_project(p)
        enqueue(pid, 'proxy', {})
        return p
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    finally:
        temp.unlink(missing_ok=True)

@app.put('/api/projects/{pid}/edit')
def save_edit(pid: str, edit: Edit):
    valid_edit(pid, edit)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT document FROM projects WHERE id=?', (pid,)).fetchone()
        p = json.loads(row['document'])
        if p['edit']['revision'] != edit.revision:
            raise HTTPException(409, 'El proyecto ha cambiado. Vuelve a abrirlo antes de guardar.')
        p['edit'] = edit.model_dump()
        p['edit']['revision'] += 1
        conn.execute('UPDATE projects SET document=? WHERE id=?', (json.dumps(p), pid))
    return p

@app.post('/api/projects/{pid}/exports')
def export(pid: str, edit: Edit):
    p = valid_edit(pid, edit)
    if p['status'] != 'ready':
        raise HTTPException(409, 'Espera a que termine la preparación del vídeo.')
    return enqueue(pid, 'export', edit.model_dump())

@app.get('/api/jobs')
def get_jobs():
    with db() as conn:
        ids = [r[0] for r in conn.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT 100')]
    return {'jobs': [job(jid) for jid in ids]}

@app.post('/api/jobs/{jid}/cancel')
def cancel(jid: str):
    j = job(jid)
    if j['status'] in ('queued', 'running'):
        update_job(jid, status='cancelled' if j['status'] == 'queued' else 'cancel_requested')
    return job(jid)

@app.post('/api/jobs/{jid}/retry')
def retry(jid: str):
    j = job(jid)
    if j['status'] not in ('failed', 'cancelled', 'interrupted'):
        raise HTTPException(409, 'Este trabajo no necesita reintento.')
    return enqueue(j['project_id'], j['kind'], j['spec'])

@app.get('/api/media/{pid}/{kind}')
def media(pid: str, kind: Literal['proxy', 'poster']):
    project(pid)
    file = DATA / pid / ('proxy.mp4' if kind == 'proxy' else 'poster.jpg')
    if not file.is_file():
        raise HTTPException(404, 'Medio no disponible todavía')
    return FileResponse(file, media_type='video/mp4' if kind == 'proxy' else 'image/jpeg')

@app.get('/api/exports/{jid}')
def download(jid: str):
    j = job(jid)
    if j['status'] != 'succeeded' or j['kind'] != 'export':
        raise HTTPException(404, 'Exportación no disponible')
    return FileResponse(DATA / j['project_id'] / f'{jid}.mp4', media_type='video/mp4', filename='clippa-' + jid[:8] + '.mp4')
