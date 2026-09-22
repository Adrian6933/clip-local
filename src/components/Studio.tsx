import { useEffect, useRef, useState, type DragEvent } from 'react';
import { ArrowDownToLine, ArrowLeft, ArrowRight, Check, CheckCheck, ChevronRight, CircleHelp, Clapperboard, Cpu, FileVideo, Film, FolderOpen, HardDrive, LayoutGrid, LoaderCircle, MonitorPlay, Pause, Play, Plus, RefreshCw, Save, Scissors, Search, Settings2, ShieldCheck, SlidersHorizontal, Sparkles, Upload, X } from 'lucide-react';

type Point = { x: number; y: number };
type Edit = { title: string; start: number; end: number; layout: 'fit' | 'single' | 'split'; a: Point; b: Point; revision: number };
type Project = { id: string; name: string; status: string; createdAt: number; media: null | {duration: number; width: number; height: number; bytes: number; originalName: string}; edit: Edit | null };
type Job = { id: string; project_id: string; kind: string; status: string; progress: number; error?: string; spec: Edit; created: number };
type Capabilities = { ffmpeg: boolean; ffprobe: boolean; transcription: boolean; faceTracking: boolean; engine: string; freeBytes: number };
const running = (j: Job) => ['queued', 'running', 'cancel_requested'].includes(j.status);
const formatTime = (t: number) => `${Math.floor(t / 60).toString().padStart(2, '0')}:${Math.floor(t % 60).toString().padStart(2, '0')}`;
const sizes = (n: number) => n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(1)} GB` : `${(n / 1024 ** 2).toFixed(1)} MB`;
const date = (n: number) => new Date(n * 1000).toLocaleDateString('es', {day: 'numeric', month: 'short'});

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {...options, headers: {'X-Clippa-Client': 'studio', 'Content-Type': 'application/json', ...options.headers}});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : `No se pudo completar la operación (${response.status}).`);
  }
  return response.json();
}

function Preview({project, edit}: {project: Project; edit: Edit}) {
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const currentEdit = useRef(edit);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(edit.start);
  const [error, setError] = useState('');
  currentEdit.current = edit;
  useEffect(() => {
    let frame: number;
    function draw() {
      const v = video.current, c = canvas.current, ctx = c?.getContext('2d');
      if (v && c && ctx && v.readyState >= 2) {
        const e = currentEdit.current;
        ctx.fillStyle = '#111216'; ctx.fillRect(0, 0, c.width, c.height);
        const w = v.videoWidth, h = v.videoHeight;
        const drawCrop = (point: Point, targetY: number, targetH: number) => {
          const ratio = c.width / targetH;
          const cw = Math.floor(Math.min(w, h * ratio) / 2) * 2;
          const ch = Math.floor(Math.min(h, w / ratio) / 2) * 2;
          const x = Math.floor(Math.max(0, Math.min(w - cw, point.x * w - cw / 2)) / 2) * 2;
          const y = Math.floor(Math.max(0, Math.min(h - ch, point.y * h - ch / 2)) / 2) * 2;
          ctx.drawImage(v, x, y, cw, ch, 0, targetY, c.width, targetH);
        };
        if (e.layout === 'fit') {
          const scale = Math.min(c.width / w, c.height / h);
          ctx.drawImage(v, (c.width - w * scale) / 2, (c.height - h * scale) / 2, w * scale, h * scale);
        } else { drawCrop(e.a, 0, e.layout === 'split' ? c.height / 2 : c.height); if (e.layout === 'split') drawCrop(e.b, c.height / 2, c.height / 2); }
        if (!v.paused && v.currentTime >= e.end) { v.pause(); v.currentTime = e.start; }
      }
      frame = requestAnimationFrame(draw);
    }
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [project.id]);
  useEffect(() => { if (video.current) {video.current.pause(); video.current.currentTime = edit.start;} }, [edit.start, project.id]);
  const toggle = async () => { const v = video.current; if (!v) return; if (v.paused) {if (v.currentTime < edit.start || v.currentTime >= edit.end) v.currentTime = edit.start; try { await v.play(); } catch {setError('No se puede reproducir este vídeo.');}} else v.pause(); };
  return <>
    <div className="preview-stage">
      <div className="preview-top"><span><i /> PREVISUALIZACIÓN</span><span>9:16 <span className="slash">/</span> 1080p</span></div>
      <div className="canvas-frame"><canvas ref={canvas} width={540} height={960} aria-label="Vista previa del encuadre vertical" /><button className="canvas-play" aria-label={playing ? 'Pausar vídeo' : 'Reproducir vídeo'} onClick={toggle}>{playing ? <Pause size={20}/> : <Play size={20}/>}</button></div>
      <video className="source-video" ref={video} src={`/api/media/${project.id}/proxy`} preload="auto" playsInline onLoadedMetadata={() => { if (video.current) video.current.currentTime = edit.start; }} onTimeUpdate={() => setTime(video.current?.currentTime ?? 0)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onError={() => setError('La copia de reproducción no está disponible. Revisa el trabajo de preparación.')} />
      {error && <p className="error-text">{error}</p>}
      <div className="player-controls"><button className="icon-button" onClick={toggle} aria-label={playing ? 'Pausar' : 'Reproducir'}>{playing ? <Pause size={16}/> : <Play size={16}/>}</button><span>{formatTime(time)}</span><input aria-label="Posición de reproducción" type="range" min={edit.start} max={edit.end} step="0.01" value={Math.min(edit.end, Math.max(edit.start, time))} onChange={e => { if (video.current) video.current.currentTime = +e.target.value; setTime(+e.target.value); }}/><span>{formatTime(edit.end)}</span></div>
    </div>
    <p className="preview-note"><MonitorPlay size={13}/> Vista previa a resolución reducida · exportación desde el original</p>
  </>;
}

export default function Studio() {
  const [page, setPage] = useState<'projects' | 'exports' | 'settings'>('projects');
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [cap, setCap] = useState<Capabilities | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [edit, setEdit] = useState<Edit | null>(null);
  const [dirty, setDirty] = useState(false);
  const [query, setQuery] = useState('');
  const [order, setOrder] = useState('new');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadName, setUploadName] = useState('');
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [help, setHelp] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const xhr = useRef<XMLHttpRequest | null>(null);
  const editGeneration = useRef(0);
  const saving = useRef(false);
  const project = projects.find(p => p.id === selected);

  async function refresh() {
    const [p, j, c] = await Promise.all([api<{projects: Project[]}>('/projects'), api<{jobs: Job[]}>('/jobs'), api<Capabilities>('/capabilities')]);
    setProjects(p.projects); setJobs(j.jobs); setCap(c); setOnline(true);
  }
  useEffect(() => { refresh().catch(() => setOnline(false)); const id = setInterval(() => refresh().catch(() => setOnline(false)), 2500); return () => clearInterval(id); }, []);
  useEffect(() => { if (!notice) return; const id = setTimeout(() => setNotice(''), 4000); return () => clearTimeout(id); }, [notice]);
  useEffect(() => { const handler = (event: BeforeUnloadEvent) => { if (dirty || uploading) { event.preventDefault(); event.returnValue = ''; } }; window.addEventListener('beforeunload', handler); return () => window.removeEventListener('beforeunload', handler); }, [dirty, uploading]);
  useEffect(() => { const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setHelp(false); }; window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, []);
  useEffect(() => {
    if (!help) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('.help-modal');
    const focusable = () => Array.from(dialog?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled)') ?? []);
    focusable()[0]?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      const items = focusable(), first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first?.focus();}
    };
    document.addEventListener('keydown', trap);
    return () => {document.removeEventListener('keydown', trap); previous?.focus();};
  }, [help]);

  async function save() {
    if (!selected || !edit) return;
    if (saving.current) throw new Error('Espera a que termine el guardado.');
    saving.current = true;
    const generation = editGeneration.current;
    try {
      const p = await api<Project>(`/projects/${selected}/edit`, {method: 'PUT', body: JSON.stringify(edit)});
      setProjects(all => all.map(v => v.id === p.id ? p : v));
      if (generation !== editGeneration.current) {
        setEdit(current => current && p.edit ? {...current, revision:p.edit.revision} : current);
        throw new Error('Has añadido cambios durante el guardado. Guárdalos antes de continuar.');
      }
      setEdit(p.edit); setDirty(false); return p;
    } finally {saving.current = false;}
  }
  async function navigate(next: typeof page, p?: Project) {
    try { if (dirty) await save(); setPage(next); setSelected(p?.id ?? null); setEdit(p?.edit ?? null); setDirty(false); setError(''); } catch(e) {setError((e as Error).message);}
  }
  function change(patch: Partial<Edit>) { editGeneration.current += 1; setEdit(e => e ? {...e, ...patch} : e); setDirty(true); }
  async function action(fn: () => Promise<unknown>) { setBusy(true); setError(''); try { await fn(); } catch(e) {setError((e as Error).message);} finally {setBusy(false);} }
  async function upload(file?: File) {
    if (!file || uploading) return;
    setError(''); setNotice(''); setUploading(true); setUploadName(file.name); setUploadProgress(0);
    try {
      if (dirty) await save();
      const p = await api<Project>('/projects', {method: 'POST', body: JSON.stringify({name: file.name})});
      const result = await new Promise<Project>((resolve, reject) => {
        const request = new XMLHttpRequest(); xhr.current = request;
        request.open('POST', `/api/projects/${p.id}/assets`);
        request.setRequestHeader('X-Clippa-Client', 'studio'); request.setRequestHeader('X-File-Name', encodeURIComponent(file.name)); request.setRequestHeader('Content-Type', 'application/octet-stream');
        request.upload.onprogress = e => { if (e.lengthComputable) setUploadProgress(Math.round(e.loaded / e.total * 100)); };
        request.onerror = () => reject(new Error('Se ha perdido la conexión con el motor local.'));
        request.onabort = () => reject(new Error('Importación cancelada.'));
        request.onload = () => { let data; try {data = JSON.parse(request.responseText);} catch {reject(new Error('Respuesta inválida del motor local.')); return;} request.status < 300 ? resolve(data) : reject(new Error(data.detail || 'No se pudo importar el vídeo.')); };
        request.send(file);
      });
      await refresh(); setSelected(result.id); setEdit(result.edit); setDirty(false); setPage('projects'); setNotice('Vídeo importado. Preparando la reproducción.');
    } catch(e) { setError((e as Error).message); await refresh().catch(() => {}); } finally {setUploading(false); xhr.current = null; if (fileInput.current) fileInput.current.value = '';}
  }
  const drop = (e: DragEvent) => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files[0]); };
  const exports = jobs.filter(j => j.kind === 'export');
  const completed = exports.filter(j => j.status === 'succeeded').length;
  const activeJobs = jobs.filter(running);
  const visible = projects.filter(p => p.name.toLowerCase().includes(query.toLowerCase())).sort((a,b) => order === 'name' ? a.name.localeCompare(b.name) : b.createdAt-a.createdAt);
  const readyCount = projects.filter(p => p.status === 'ready').length;
  const choose = () => fileInput.current?.click();

  return <div className="app-shell">
    <aside className="sidebar">
      <button className="brand" onClick={() => navigate('projects')} aria-label="Clippa, ir a proyectos"><span className="brand-mark"><Clapperboard size={22}/></span>clippa<span className="brand-dot">.</span></button>
      <div className="workspace-switch"><span className="workspace-avatar">A</span><div><strong>Mi estudio</strong><small>Espacio personal</small></div><span className="local-tag">LOCAL</span></div>
      <button className="primary import-side" onClick={choose} disabled={uploading || !online}><Plus size={17}/> Nuevo proyecto</button>
      <span className="nav-label">ESPACIO DE TRABAJO</span>
      <nav aria-label="Navegación principal">
        <button className={page === 'projects' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('projects')}><LayoutGrid size={18}/> Proyectos <span>{projects.length}</span></button>
        <button className={page === 'exports' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('exports')}><ArrowDownToLine size={18}/> Exportaciones {activeJobs.length > 0 && <span className="activity-count">{activeJobs.length}</span>}</button>
        <button className={page === 'settings' ? 'nav-item active' : 'nav-item'} onClick={() => navigate('settings')}><Settings2 size={18}/> Ajustes del estudio</button>
      </nav>
      <div className="sidebar-tip"><div className="tip-icon"><Scissors size={18}/></div><strong>Tu siguiente buen clip<br/>empieza aquí.</strong><p>Elige un momento. Dale su propio espacio.</p><button onClick={() => setHelp(true)}>Cómo funciona <ArrowRight size={13}/></button></div>
      <div className="sidebar-bottom"><span className={`status-dot ${online ? 'ready' : ''}`}/><div><strong>{online === null ? 'Conectando…' : online ? 'Estudio conectado' : 'Motor desconectado'}</strong><small>Tus vídeos se quedan aquí</small></div><ShieldCheck size={16}/></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb"><span>Mi estudio</span><ChevronRight size={13}/><strong>{project ? 'Editor' : page === 'projects' ? 'Proyectos' : page === 'exports' ? 'Exportaciones' : 'Ajustes'}</strong></div><div className="top-right"><span className="privacy-badge"><HardDrive size={13}/> Guardado local</span><button className="icon-button" aria-label="Ayuda" onClick={() => setHelp(true)}><CircleHelp size={18}/></button><span className="profile-avatar">A</span></div></header>
      <input aria-label="Seleccionar vídeo" ref={fileInput} type="file" accept="video/*,.mkv,.mov" hidden onChange={e => upload(e.target.files?.[0])}/>
      <div className="page-content">
        {!online && online !== null && <div className="alert" role="status"><Cpu size={18}/><div><strong>El motor local está desconectado</strong><span>Inicia el estudio con npm run dev:full para importar y editar vídeos.</span></div><button className="secondary" onClick={() => action(refresh)}>Reconectar</button></div>}
        {error && <div className="alert danger" role="alert"><span>{error}</span><button className="icon-button" aria-label="Cerrar error" onClick={() => setError('')}><X size={16}/></button></div>}
        {uploading && <div className="upload-progress" role="status"><LoaderCircle className="spin" size={20}/><div><strong>{uploadProgress === 100 ? 'Comprobando el vídeo…' : `Importando · ${uploadProgress}%`}</strong><span>{uploadName}</span><progress max={100} value={uploadProgress}/></div><button className="icon-button" aria-label="Cancelar importación" onClick={() => xhr.current?.abort()}><X size={18}/></button></div>}

        {page === 'projects' && !project && <>
          <div className="page-heading"><div><div className="eyebrow">DALE OTRA VIDA A TUS VÍDEOS</div><h1>Grandes momentos.<br/><span>Clips a tu manera.</span></h1><p>Tu espacio para convertir vídeos largos en historias que conectan.</p></div><div className="heading-note"><span className="status-dot ready"/> Tu estudio, en tu ordenador</div></div>
          <div className={`import-hero ${dragging ? 'dragging' : ''}`} onDragOver={e => {e.preventDefault(); setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={drop}>
            <div className="hero-copy"><span className="pill"><Film size={13}/> DE VÍDEO A CLIP</span><h2>Todo empieza<br/>con un buen vídeo.</h2><p>Arrastra tu archivo aquí, elige el mejor momento<br className="desktop-break"/> y encuentra el encuadre perfecto.</p><button className="primary" onClick={choose} disabled={uploading || !online}><Upload size={16}/> Importar vídeo <ArrowRight size={15}/></button><small>MP4, MOV, MKV y más · hasta 5 GB</small></div>
            <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="art-source"><div className="art-window"><span/><span/><span/></div><div className="art-mountain"/><div className="art-sun"/><div className="art-time">01:24:08</div></div><div className="art-vertical"><div className="art-window"><span/><span/></div><div className="art-mountain"/><div className="art-sun"/><span className="art-play"><Play size={22} fill="currentColor"/></span><div className="art-caption"><i/><i/></div><span className="art-duration">00:32</span></div><span className="art-badge"><Scissors size={14}/> Un momento. Una historia.</span><span className="art-star star-one">✦</span><span className="art-star star-two">✧</span></div>
          </div>
          <div className="stats-strip"><div><FolderOpen size={18}/><strong>{projects.length}</strong><span>proyectos en tu estudio</span></div><div><CheckCheck size={18}/><strong>{readyCount}</strong><span>listos para editar</span></div><div><ArrowDownToLine size={18}/><strong>{completed}</strong><span>clips exportados</span></div></div>
          <div className="section-header"><div><h2>Tus proyectos <span className="number-badge">{projects.length}</span></h2><p>Retoma una idea donde la dejaste.</p></div><div className="library-controls"><label className="search-field"><Search size={15}/><input placeholder="Buscar proyecto…" value={query} onChange={e => setQuery(e.target.value)} aria-label="Buscar proyecto"/></label><select value={order} onChange={e => setOrder(e.target.value)} aria-label="Ordenar proyectos"><option value="new">Más recientes</option><option value="name">Por nombre</option></select></div></div>
          {visible.length === 0 ? <div className="empty-library"><span className="empty-icon"><FolderOpen size={23}/></span><div><h3>{query ? 'No hay coincidencias' : 'El primer proyecto siempre es especial'}</h3><p>{query ? 'Prueba con otro nombre para encontrar tu vídeo.' : 'Importa un vídeo y todos tus proyectos aparecerán aquí.'}</p></div>{!query && <button className="text-button" onClick={choose} disabled={!online}>Crear mi primer proyecto <ArrowRight size={15}/></button>}</div> : <div className="project-grid">{visible.map((p, index) => <button className="project-card" key={p.id} onClick={() => navigate('projects', p)}><div className={`project-poster poster-${index%3}`}>{p.status === 'ready' ? <img src={`/api/media/${p.id}/poster`} alt=""/> : <FileVideo size={36}/>}<span className={`project-state ${p.status === 'ready' ? 'ready' : ''}`}>{p.status === 'ready' ? 'Listo para editar' : p.status === 'processing' ? 'Preparando' : 'Sin vídeo'}</span>{p.media && <span className="duration-chip">{formatTime(p.media.duration)}</span>}<span className="open-project"><ArrowRight size={18}/></span></div><div className="project-card-info"><h3>{p.name}</h3><p>{date(p.createdAt)}<span>·</span>{p.media ? `${p.media.width} × ${p.media.height}` : 'Importación pendiente'}<ChevronRight size={16}/></p></div></button>)}</div>}
          <div className="local-footer"><ShieldCheck size={14}/> Hecho para crear a tu ritmo. Tus archivos permanecen en este equipo.<span>CLIPPA STUDIO / 0.2</span></div>
        </>}

        {page === 'projects' && project && <>
          <div className="editor-heading"><button className="icon-button" aria-label="Volver a proyectos" onClick={() => navigate('projects')}><ArrowLeft size={19}/></button><div><span className="eyebrow">TU MESA DE EDICIÓN</span><h1>{project.name}</h1></div><div className="editor-actions"><span className="save-status">{dirty ? 'Cambios sin guardar' : 'Guardado'}{!dirty && <Check size={13}/>}</span><button className="secondary" disabled={!dirty || busy} onClick={() => action(async () => {await save(); setNotice('Edición guardada.');})}><Save size={15}/> Guardar</button><button className="primary" disabled={project.status !== 'ready' || !edit || busy || !online} onClick={() => action(async () => { const p = dirty ? await save() : project; await api(`/projects/${project.id}/exports`, {method: 'POST', body: JSON.stringify(p?.edit || edit)}); await refresh(); setNotice('Exportación añadida a la cola.'); })}><ArrowDownToLine size={15}/> Exportar clip</button></div></div>
          {project.status !== 'ready' || !edit ? <div className="preparing"><LoaderCircle className={project.status === 'processing' ? 'spin' : ''} size={34}/><h2>{project.status === 'processing' ? 'Preparando tu vídeo' : 'Este proyecto necesita un vídeo'}</h2><p>{project.status === 'processing' ? 'Creando una copia ligera para que la edición vaya fluida.' : 'Puedes importar de nuevo desde la biblioteca.'}</p>{jobs.filter(j => j.project_id === project.id).map(j => <JobRow key={j.id} j={j} projects={projects} action={action} refresh={refresh}/>)}</div> : <div className="editor-grid"><section><Preview key={project.id} project={project} edit={edit}/><div className="trim-panel"><div className="section-header"><h3><Scissors size={16}/> Elige tu momento</h3><span className="muted">{formatTime(edit.end-edit.start)} de clip</span></div><div className="trim-track"><div style={{left: `${edit.start / project.media!.duration * 100}%`, width: `${(edit.end-edit.start) / project.media!.duration * 100}%`}}/></div><div className="trim-inputs"><label>Inicio (segundos)<input type="number" step="0.1" min="0" max={edit.end-.1} value={edit.start} onChange={e => change({start: Math.max(0, Math.min(edit.end-.1, Number(e.target.value)))})}/></label><ArrowRight size={16}/><label>Final (segundos)<input type="number" step="0.1" min={edit.start+.1} max={project.media!.duration} value={edit.end} onChange={e => change({end: Math.min(project.media!.duration, Math.max(edit.start+.1, Number(e.target.value)))})}/></label></div><label className="range-label">Inicio<input type="range" min="0" max={Math.max(0,edit.end-.1)} step="0.1" value={edit.start} onChange={e => change({start: +e.target.value})}/></label><label className="range-label">Final<input type="range" min={edit.start+.1} max={project.media!.duration} step="0.1" value={edit.end} onChange={e => change({end: +e.target.value})}/></label></div></section><aside className="inspector"><div className="inspector-title"><SlidersHorizontal size={17}/><h2>A tu manera</h2></div><label className="field-label">Nombre del clip<input maxLength={150} value={edit.title} onChange={e => change({title: e.target.value})}/></label><div className="control-section"><h3>Composición <span>9:16</span></h3><div className="layout-grid">{([['fit','Completo'],['single','Un encuadre'],['split','Dividido']] as const).map(([id,label]) => <button key={id} className={edit.layout === id ? 'layout-choice selected' : 'layout-choice'} onClick={() => change({layout:id})}><span className={`layout-glyph ${id}`}><i/><i/></span>{label}</button>)}</div><p className="control-hint">{edit.layout === 'split' ? 'Dos zonas del mismo vídeo, una arriba y otra abajo. Ajusta cada centro.' : edit.layout === 'single' ? 'Desplaza el centro del encuadre para destacar lo importante.' : 'Conserva toda la imagen con espacio arriba y abajo.'}</p></div>{edit.layout !== 'fit' && (edit.layout === 'split' ? ['a','b'] as const : ['a'] as const).map(key => <div className="control-section" key={key}><h3><span className={`subject-dot ${key}`}/>{key === 'a' ? edit.layout === 'split' ? 'Encuadre superior' : 'Centro del encuadre' : 'Encuadre inferior'}</h3>{(['x','y'] as const).map(axis => <label className="range-label" key={axis}>{axis === 'x' ? 'Horizontal' : 'Vertical'}<span>{Math.round(edit[key][axis]*100)}%</span><input type="range" min="0" max="1" step=".005" value={edit[key][axis]} onChange={e => change({[key]: {...edit[key], [axis]: +e.target.value}})}/></label>)}</div>)}<div className="control-section"><h3><Sparkles size={15}/> Asistencia con IA <span className="soon">Pendiente</span></h3><p className="control-hint">La detección de personas y la transcripción todavía no están conectadas. Los encuadres de este editor se ajustan manualmente.</p></div><div className="export-spec"><Check size={15}/><div><strong>Listo para formato vertical</strong><small>MP4 · 1080 × 1920 · 30 fps</small></div></div></aside></div>}
          {jobs.some(j => j.project_id === project.id && j.kind === 'export') && <div className="recent-exports"><h3>Exportaciones de este proyecto</h3>{jobs.filter(j => j.project_id === project.id && j.kind === 'export').map(j => <JobRow key={j.id} j={j} projects={projects} action={action} refresh={refresh}/>)}</div>}
        </>}

        {page === 'exports' && <><div className="page-heading compact"><div><div className="eyebrow">DE LA IDEA AL ARCHIVO</div><h1>Tus exportaciones<span>.</span></h1><p>El último paso antes de compartir una buena historia.</p></div></div><div className="jobs-list">{jobs.length ? jobs.map(j => <JobRow key={j.id} j={j} projects={projects} action={action} refresh={refresh}/>) : <div className="empty-library"><ArrowDownToLine size={30}/><div><h3>Aquí llegarán tus clips</h3><p>Abre un proyecto y exporta tu primer momento.</p></div></div>}</div></>}
        {page === 'settings' && <><div className="page-heading compact"><div><div className="eyebrow">TODO EN SU SITIO</div><h1>Tu estudio, por dentro<span>.</span></h1><p>Herramientas disponibles y estado del procesamiento local.</p></div></div><div className="settings-grid"><section className="settings-card"><HardDrive size={23}/><h2>Almacenamiento local</h2><p>Originales, proyectos y clips permanecen en este ordenador.</p><strong className="storage-value">{cap ? sizes(cap.freeBytes) : '—'} <span>disponibles</span></strong><div className="setting-line"><span>Proyectos</span><strong>SQLite</strong></div><div className="setting-line"><span>Ubicación</span><code>.clippa-data</code></div></section><section className="settings-card"><Cpu size={23}/><h2>Motor de procesamiento</h2><p>Capacidades comprobadas en este equipo.</p>{[['Vídeo y exportación',cap?.ffmpeg],['Lectura de metadatos',cap?.ffprobe],['Transcripción automática',cap?.transcription],['Seguimiento de personas',cap?.faceTracking]].map(([name,value]) => <div className="setting-line" key={String(name)}><span>{name}</span><span className={value ? 'available' : 'pending'}>{value ? 'Disponible' : 'Pendiente'}</span></div>)}</section></div></>}
      </div>
    </main>
    {notice && <div className="toast" role="status"><Check size={17}/>{notice}</div>}
    {help && <div className="modal-backdrop" onClick={() => setHelp(false)}><section className="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title" onClick={e => e.stopPropagation()}><button autoFocus className="icon-button modal-close" aria-label="Cerrar ayuda" onClick={() => setHelp(false)}><X size={19}/></button><span className="pill">TU PRIMER CLIP</span><h2 id="help-title">Un buen momento.<br/>Tres pasos.</h2>{[['01','Importa tu vídeo','Se guarda y se prepara en tu ordenador.'],['02','Encuentra el encuadre','Elige inicio y final. Prueba un plano o dos zonas divididas.'],['03','Guárdalo y expórtalo','Obtén un MP4 vertical desde el vídeo original.']].map(([n,title,desc]) => <div className="help-step" key={n}><span>{n}</span><div><h3>{title}</h3><p>{desc}</p></div></div>)}<button className="primary" onClick={() => {setHelp(false); choose();}} disabled={!online}>Vamos a crear <ArrowRight size={16}/></button></section></div>}
  </div>;
}

function JobRow({j, projects, action, refresh}: {j: Job; projects: Project[]; action: (fn: () => Promise<unknown>) => Promise<void>; refresh: () => Promise<void>}) {
  const statuses: Record<string,string> = {queued:'En cola', running:'Procesando', succeeded:'Completado', failed:'No se pudo completar', cancelled:'Cancelado', cancel_requested:'Cancelando', interrupted:'Interrumpido'};
  return <div className="job-row"><div className={`job-icon ${j.status === 'succeeded' ? 'done' : ''}`}>{running(j) ? <LoaderCircle className="spin" size={19}/> : j.status === 'succeeded' ? <Check size={19}/> : <Film size={19}/>}</div><div className="job-copy"><strong>{j.kind === 'proxy' ? 'Preparar vídeo' : j.spec.title || 'Exportar clip'} <span>· {projects.find(p => p.id === j.project_id)?.name}</span></strong><small>{statuses[j.status]}{running(j) && ` · ${Math.round(j.progress*100)}%`}{j.error && ` — ${j.error}`}</small>{running(j) && <progress max="1" value={j.progress}/>}</div>{running(j) && <button className="text-button" disabled={j.status === 'cancel_requested'} onClick={() => action(async () => {await api(`/jobs/${j.id}/cancel`,{method:'POST'}); await refresh();})}>Cancelar</button>}{['failed','cancelled','interrupted'].includes(j.status) && <button className="secondary" onClick={() => action(async () => {await api(`/jobs/${j.id}/retry`,{method:'POST'}); await refresh();})}><RefreshCw size={14}/> Reintentar</button>}{j.kind === 'export' && j.status === 'succeeded' && <a className="secondary" href={`/api/exports/${j.id}`} download><ArrowDownToLine size={15}/> Descargar</a>}</div>;
}
