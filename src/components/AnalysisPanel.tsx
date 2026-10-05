import { useEffect, useState } from 'react';
import { Captions, Download, Languages, ScanFace, Sparkles } from 'lucide-react';

export type Cue = {start:number; end:number; text:string};
type Transcript = {revision:number; language:string; task:string; cues:Cue[]};
type Moment = {start:number; end:number; title:string; reason:string; text:string};
const stamp = (n:number) => `${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
async function request(path:string, method='GET', body?:unknown) {
  const res = await fetch(`/api${path}`, {method, headers:{'Content-Type':'application/json','X-Clippa-Client':'studio'}, body:body === undefined ? undefined : JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo completar la operación.');
  return data;
}

export default function AnalysisPanel({pid, completion, running, enabled, start, end, onCues, onDirty, onPick, onSeek, onRefresh, onFace}: {
  pid:string; completion:string; running:boolean; enabled:boolean; start:number; end:number;
  onCues:(c:Cue[])=>void; onDirty:(v:boolean)=>void; onPick:(start:number,end:number,title:string)=>void;
  onSeek:(time:number)=>void; onRefresh:()=>Promise<void>; onFace:(a:{x:number;y:number},b:{x:number;y:number},count:number)=>void;
}) {
  const [transcript,setTranscript] = useState<Transcript|null>(null);
  const [language,setLanguage] = useState('');
  const [task,setTask] = useState('transcribe');
  const [replace,setReplace] = useState(false);
  const [dirty,setDirty] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [query,setQuery] = useState('');
  const [maximum,setMaximum] = useState(180);
  const [moments,setMoments] = useState<Moment[]>([]);
  const [faces,setFaces] = useState<{count:number;samples:number;start:number;end:number;note:string;a:{x:number;y:number};b:{x:number;y:number}}|null>(null);
  useEffect(() => {
    let alive = true;
    if (!dirty) request(`/projects/${pid}/transcript`).then(data => {if(alive) {setTranscript(data.transcript); onCues(data.transcript?.cues ?? []);}}).catch(e=>{if(alive)setError(e.message);});
    request(`/projects/${pid}/faces`).then(data=>{if(alive)setFaces(data.analysis);}).catch(()=>{});
    return ()=>{alive=false;};
  },[pid,completion]);
  const perform = async (fn:()=>Promise<void>) => {setBusy(true);setError('');try{await fn();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  function modify(index:number,text:string) {
    if(!transcript)return;
    const next={...transcript,cues:transcript.cues.map((c,i)=>i===index?{...c,text}:c)};
    setTranscript(next);setDirty(true);onDirty(true);onCues(next.cues);
  }
  const filtered = (transcript?.cues ?? []).map((cue,index)=>({cue,index})).filter(({cue})=>!query || cue.text.toLowerCase().includes(query.toLowerCase()));
  return <section className="analysis-panel">
    <div className="analysis-heading"><div><span className="eyebrow">DEL VÍDEO A LA HISTORIA</span><h2><Sparkles size={20}/> Tu mesa de análisis</h2><p>Texto real, encuadres y fragmentos con espacio para desarrollar la idea.</p></div><span className="pill">PROCESAMIENTO LOCAL</span></div>
    {error && <p role="alert" className="alert danger">{error}</p>}
    <div className="analysis-options"><label><Languages size={16}/> Idioma del audio<select value={language} onChange={e=>setLanguage(e.target.value)}><option value="">Detectar automáticamente</option>{[['es','Español'],['en','Inglés'],['fr','Francés'],['de','Alemán'],['it','Italiano'],['pt','Portugués'],['ca','Catalán'],['ja','Japonés'],['zh','Chino'],['ko','Coreano'],['ar','Árabe'],['ru','Ruso']].map(([id,label])=><option value={id} key={id}>{label}</option>)}</select></label><label>Texto de salida<select value={task} onChange={e=>setTask(e.target.value)}><option value="transcribe">Idioma original</option><option value="translate">Traducir al inglés</option></select></label><button className="primary" disabled={!enabled||busy||running||dirty||(!!transcript&&!replace)} onClick={()=>perform(async()=>{await request(`/projects/${pid}/transcribe`,'POST',{language:language||null,task,replace});await onRefresh();})}><Captions size={16}/>{running?'Análisis en curso…':transcript?'Volver a transcribir':'Transcribir vídeo'}</button></div>
    <p className="analysis-note">El modelo reconoce varios idiomas. La traducción automática de esta versión solo tiene inglés como destino. Revisa nombres propios y palabras dudosas.</p>
    {!enabled && <p className="error-text">El modelo de transcripción local todavía no está instalado.</p>}
    {transcript && <><label className="check-label"><input type="checkbox" checked={replace} onChange={e=>setReplace(e.target.checked)}/> Reemplazar la transcripción guardada al generar otra</label><div className="transcript-toolbar"><strong>Transcripción · {transcript.task==='translate'?'inglés':transcript.language} · {transcript.cues.length} bloques</strong><input aria-label="Buscar en transcripción" placeholder="Buscar una frase…" value={query} onChange={e=>setQuery(e.target.value)}/><button className="secondary" disabled={!dirty||busy} onClick={()=>perform(async()=>{const data=await request(`/projects/${pid}/transcript`,'PUT',{revision:transcript.revision,cues:transcript.cues});setTranscript(data.transcript);setDirty(false);onDirty(false);setMoments([]);})}>{dirty?'Guardar texto':'Texto guardado'}</button><a className="secondary" href={`/api/projects/${pid}/subtitles.srt?start=${start}&end=${end}`} download><Download size={15}/> SRT guardado del clip</a></div><div className="transcript-list">{filtered.slice(0,500).map(({cue,index})=><div className="transcript-cue" key={index}><button title="Ver este instante del vídeo" onClick={()=>onSeek(cue.start)}>{stamp(cue.start)}<small>{stamp(cue.end)}</small></button><textarea aria-label={`Subtítulo ${index+1}`} rows={2} maxLength={500} value={cue.text} onChange={e=>modify(index,e.target.value)}/><button className="text-button" onClick={()=>onPick(cue.start,cue.end,cue.text.slice(0,90))}>Usar</button></div>)}{filtered.length>500&&<p>Hay más resultados. Usa la búsqueda para localizar un fragmento concreto.</p>}{!filtered.length&&<p>No hay texto que mostrar. Puede que no se haya detectado voz.</p>}</div></>}
    <div className="moment-toolbar"><div><h3>Fragmentos para revisar</h3><p>Propuestas por pausas y continuidad del texto. Aún no valoran el interés semántico.</p></div><label>Duración máxima<select value={maximum} onChange={e=>setMaximum(+e.target.value)}><option value={90}>1 min 30 s</option><option value={180}>3 minutos</option><option value={300}>5 minutos</option><option value={600}>10 minutos</option></select></label><button className="secondary" disabled={!transcript||dirty||busy} onClick={()=>perform(async()=>{setMoments((await request(`/projects/${pid}/moments?maximum=${maximum}`)).moments);})}>Buscar fragmentos</button></div>
    <div className="moment-grid">{moments.map((m,i)=><button className="moment-card" key={i} onClick={()=>onPick(m.start,m.end,m.title)}><span>{stamp(m.start)} — {stamp(m.end)} · {stamp(m.end-m.start)}</span><h3>{m.title}</h3><p>{m.reason}</p><strong>Editar este fragmento →</strong></button>)}</div>
    <div className="face-tools"><div><h3><ScanFace size={17}/> Personas en cámara</h3><p>Detecta caras y propone un encuadre fijo del fragmento seleccionado. Seguir movimientos y elegir al hablante siguen pendientes.</p></div><button className="secondary" disabled={busy||running} onClick={()=>perform(async()=>{await request(`/projects/${pid}/faces`,'POST',{start,end});await onRefresh();})}>Analizar caras del clip</button></div>
    {faces && <div className="face-result"><span>{faces.count} {faces.count===1?'cara detectada':'caras detectadas'} en la muestra de referencia · {faces.samples} fotogramas analizados · {stamp(faces.start)}–{stamp(faces.end)}</span><p>{faces.note}</p>{faces.count>0&&<button className="secondary" onClick={()=>onFace(faces.a,faces.b,faces.count)}>Aplicar {faces.count>1?'pantalla dividida':'encuadre individual'}</button>}</div>}
  </section>;
}
