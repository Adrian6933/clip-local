import asyncio
from contextlib import asynccontextmanager
import json
import math
import shutil
import time
from pathlib import Path
from importlib.util import find_spec
from typing import Literal
from urllib.parse import unquote
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict
from .core import DATA, FFMPEG, FFPROBE, db, initialize, uid, projects, project, put_project, probe, enqueue, job, update_job, transcript
from .captions import clip_cues, srt, moment_candidates
from .core import MODELS

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
    subtitles: bool = False

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
    available = find_spec('faster_whisper') is not None and (MODELS / 'faster-whisper-base/model.bin').is_file()
    return {'ffmpeg': Path(FFMPEG).is_file(), 'ffprobe': Path(FFPROBE).is_file(), 'transcription': available, 'faceTracking': False, 'diarization': False, 'storage': 'SQLite', 'engine': 'Python · FastAPI', 'freeBytes': shutil.disk_usage(DATA).free}

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
    spec = edit.model_dump()
    if edit.subtitles:
        text = transcript(pid)
        if not text or not text['cues']:
            raise HTTPException(409, 'Genera o escribe los subtítulos antes de exportarlos.')
        spec['captionSnapshot'] = clip_cues(text['cues'], edit.start, edit.end)
        spec['transcriptRevision'] = text['revision']
    return enqueue(pid, 'export', spec)


class TranscriptionRequest(BaseModel):
    language: str | None = Field(default=None, max_length=8)
    task: Literal['transcribe', 'translate'] = 'transcribe'
    replace: bool = False


class FaceRequest(BaseModel):
    start: float = Field(ge=0,allow_inf_nan=False)
    end: float = Field(gt=0,allow_inf_nan=False)


@app.post('/api/projects/{pid}/faces')
def analyze_faces(pid: str, options: FaceRequest):
    p=project(pid)
    if p['status']!='ready' or options.end<=options.start or options.end>p['media']['duration']:
        raise HTTPException(422,'Selecciona un intervalo válido de un vídeo preparado.')
    if not (MODELS/'yunet-2026.onnx').is_file() or find_spec('cv2') is None:
        raise HTTPException(409,'Falta instalar el detector local de caras.')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND kind='faces' AND status IN ('queued','running','cancel_requested')",(pid,)).fetchone():
            raise HTTPException(409,'Ya hay un análisis de caras en curso.')
        jid=uid()
        conn.execute('INSERT INTO jobs (id,project_id,kind,status,spec,created,heartbeat) VALUES (?,?,?,?,?,?,?)',(jid,pid,'faces','queued',options.model_dump_json(),time.time(),time.time()))
    return job(jid)


@app.get('/api/projects/{pid}/faces')
def get_faces(pid: str):
    project(pid)
    with db() as conn:
        row=conn.execute('SELECT document FROM face_analysis WHERE project_id=?',(pid,)).fetchone()
    return {'analysis':json.loads(row[0]) if row else None}


@app.post('/api/projects/{pid}/transcribe')
def transcribe(pid: str, options: TranscriptionRequest):
    p = project(pid)
    if not p.get('media') or not p['media'].get('hasAudio'):
        raise HTTPException(422, 'Este vídeo no tiene una pista de audio para transcribir.')
    if not capabilities()['transcription']:
        raise HTTPException(409, 'Falta instalar el modelo de transcripción local.')
    if options.language:
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        if options.language not in _LANGUAGE_CODES:
            raise HTTPException(422, 'Idioma no compatible.')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('SELECT revision FROM transcripts WHERE project_id=?', (pid,)).fetchone()
        if existing and not options.replace:
            raise HTTPException(409, 'Ya hay una transcripción. Activa reemplazar para generar otra.')
        if conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND kind='transcribe' AND status IN ('queued','running','cancel_requested')", (pid,)).fetchone():
            raise HTTPException(409, 'Ya hay una transcripción en curso.')
        jid = uid()
        spec = dict(options.model_dump(), baseRevision=existing[0] if existing else -1)
        conn.execute('INSERT INTO jobs (id,project_id,kind,status,spec,created,heartbeat) VALUES (?,?,?,?,?,?,?)', (jid,pid,'transcribe','queued',json.dumps(spec),time.time(),time.time()))
    return job(jid)


@app.get('/api/projects/{pid}/transcript')
def get_transcript(pid: str):
    project(pid)
    return {'transcript': transcript(pid)}


class Cue(BaseModel):
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    text: str = Field(max_length=500)


class TranscriptEdit(BaseModel):
    revision: int = Field(ge=0)
    cues: list[Cue] = Field(max_length=30000)


@app.put('/api/projects/{pid}/transcript')
def edit_transcript(pid: str, edit: TranscriptEdit):
    p = project(pid)
    previous_end = 0
    for cue in edit.cues:
        if cue.start < previous_end or cue.end <= cue.start or cue.end > p['media']['duration']+.05:
            raise HTTPException(422, 'Los subtítulos deben estar ordenados, sin solaparse y dentro del vídeo.')
        previous_end = cue.end
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT revision,document FROM transcripts WHERE project_id=?', (pid,)).fetchone()
        if not row or row['revision'] != edit.revision:
            raise HTTPException(409, 'La transcripción ha cambiado. Recárgala antes de guardar.')
        doc = json.loads(row['document'])
        doc['cues'] = [c.model_dump() for c in edit.cues]
        conn.execute('UPDATE transcripts SET revision=revision+1,document=? WHERE project_id=?', (json.dumps(doc),pid))
    return {'transcript': transcript(pid)}


@app.get('/api/projects/{pid}/subtitles.srt')
def download_srt(pid: str, start: float = 0, end: float | None = None):
    p = project(pid)
    doc = transcript(pid)
    if not doc:
        raise HTTPException(404, 'Todavía no hay subtítulos.')
    end = end if end is not None else p['media']['duration']
    if not math.isfinite(start) or not math.isfinite(end) or start<0 or end<=start or end>p['media']['duration']+.05:
        raise HTTPException(422, 'Intervalo de subtítulos inválido.')
    return Response(srt(clip_cues(doc['cues'], start, end)),
                    media_type='application/x-subrip', headers={'Content-Disposition':'attachment; filename="clippa-subtitulos.srt"'})


@app.get('/api/projects/{pid}/moments')
def moments(pid: str, maximum: int = 180):
    project(pid)
    if not 30 <= maximum <= 600:
        raise HTTPException(422, 'La duración máxima debe estar entre 30 y 600 segundos.')
    doc = transcript(pid)
    return {'moments': moment_candidates(doc['cues'], maximum=maximum) if doc else [], 'method':'pauses-and-sentences'}

@app.get('/api/jobs')
def get_jobs():
    with db() as conn:
        ids = [r[0] for r in conn.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT 100')]
    return {'jobs': [job(jid) for jid in ids]}

@app.post('/api/jobs/{jid}/cancel')
def cancel(jid: str):
    with db() as conn:
        conn.execute("UPDATE jobs SET status=CASE WHEN status='queued' THEN 'cancelled' ELSE 'cancel_requested' END WHERE id=? AND status IN ('queued','running')", (jid,))
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
