"""Integration evidence using local synthetic speech, real models and FFmpeg."""
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import json
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
run = tempfile.TemporaryDirectory(prefix='clippa-analysis-')
os.environ['CLIPPA_DATA_DIR'] = run.name
os.environ['CLIPPA_MODEL_DIR'] = str(root / '.clippa-data/models')
from fastapi.testclient import TestClient
from engine.api import app
from engine.core import FFMPEG, NO_WINDOW, DATA, job, transcript, probe
from engine.worker import process, claim

headers = {'X-Clippa-Client':'studio'}
report = []
with TestClient(app) as client:
    for lang in ('es','en'):
        source = DATA / f'speech-{lang}.mp4'
        subprocess.run([FFMPEG,'-y','-v','error','-f','lavfi','-i','color=c=0x203322:s=640x360:r=25','-i',str(root / f'.test-data/speech-{lang}.wav'),'-c:v','libx264','-c:a','aac','-shortest',str(source)],check=True,creationflags=NO_WINDOW)
        p = client.post('/api/projects',headers=headers,json={'name':f'Speech test {lang}'}).json()
        pid = p['id']
        response=client.post(f'/api/projects/{pid}/assets',headers=headers,content=source.read_bytes())
        assert response.status_code==200,response.text
        process(claim())
        j=client.post(f'/api/projects/{pid}/transcribe',headers=headers,json={'language':None,'task':'transcribe'}).json()
        process(claim())
        assert job(j['id'])['status']=='succeeded', (job(j['id']),list((DATA/pid).glob('*.log')))
        doc=transcript(pid)
        text=' '.join(c['text'] for c in doc['cues'])
        assert doc['language']==lang,doc['language']
        assert ('historia' in text.lower()) if lang=='es' else ('story' in text.lower()),text
        assert all(c['start']<c['end'] for c in doc['cues'])
        edit=client.get(f'/api/projects/{pid}').json()['edit']
        edit.update(subtitles=True,end=min(8,probe(source)['duration']),layout='single')
        response=client.post(f'/api/projects/{pid}/exports',headers=headers,json=edit)
        assert response.status_code==200,response.text
        export=response.json();process(claim())
        assert job(export['id'])['status']=='succeeded',job(export['id'])
        output=DATA/pid/f"{export['id']}.mp4"
        destination=root/f'.test-data/subtitles-{lang}.mp4'
        import shutil
        shutil.copy2(output,destination)
        assert client.get(f'/api/projects/{pid}/subtitles.srt').status_code==200
        if lang=='es':
            face=client.post(f'/api/projects/{pid}/faces',headers=headers,json={'start':0,'end':3}).json()
            process(claim())
            assert job(face['id'])['status']=='succeeded',job(face['id'])
            assert client.get(f'/api/projects/{pid}/faces').json()['analysis']['count']==0
        report.append({'language':lang,'detected':doc['language'],'cues':len(doc['cues']),'text':text,'export':str(destination)})
        print(json.dumps(report[-1],ensure_ascii=True),flush=True)
(root/'.test-data/analysis-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
run.cleanup()
