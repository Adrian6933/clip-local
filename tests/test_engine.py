import os
from pathlib import Path
import tempfile
import subprocess

# Isolate every test run from user projects.
run_dir = tempfile.TemporaryDirectory(prefix='clippa-tests-')
os.environ['CLIPPA_DATA_DIR'] = run_dir.name
from fastapi.testclient import TestClient
from engine.api import app
from engine.core import FFMPEG, DATA, NO_WINDOW, probe, crop_box, job, db
from engine.worker import claim, process

HEADERS = {'X-Clippa-Client': 'studio'}

def make_video():
    path = DATA / 'test.mp4'
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=640x360:r=30:d=3', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', '-vf', 'drawbox=x=320:y=0:w=320:h=360:color=blue:t=fill', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(path)], check=True, creationflags=NO_WINDOW)
    return path

def test_complete_pipeline_and_guards():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['service'] == 'clippa-python'
        assert client.post('/api/projects', json={'name':'denied'}).status_code == 403
        assert client.post('/api/projects', headers={**HEADERS,'Origin':'https://untrusted.example'},json={}).status_code == 403
        source = make_video()
        p = client.post('/api/projects', headers=HEADERS, json={'name':'Ensayo técnico · dos colores.mp4'}).json()
        pid = p['id']
        bad = client.post(f'/api/projects/{pid}/assets', headers=HEADERS, content=b'not a video')
        assert bad.status_code == 422
        assert not list((DATA / pid).glob('*.upload'))
        uploaded = client.post(f'/api/projects/{pid}/assets', headers={**HEADERS,'X-File-Name':'ensayo.mp4'},content=source.read_bytes())
        assert uploaded.status_code == 200, uploaded.text
        p = uploaded.json()
        assert p['media']['hasAudio']
        pending = claim()
        process(pending)
        assert job(pending['id'])['status'] == 'succeeded', job(pending['id'])
        assert client.get(f'/api/projects/{pid}').json()['status'] == 'ready'
        ranged = client.get(f'/api/media/{pid}/proxy', headers={'Range':'bytes=0-99'})
        assert ranged.status_code == 206 and len(ranged.content) == 100
        edit = p['edit'] | {'start':.5,'end':2.5,'layout':'split','a':{'x':0,'y':.5},'b':{'x':1,'y':.5}}
        saved = client.put(f'/api/projects/{pid}/edit', headers=HEADERS, json=edit)
        assert saved.status_code == 200
        assert client.put(f'/api/projects/{pid}/edit', headers=HEADERS, json=edit).status_code == 409
        assert client.post(f'/api/projects/{pid}/exports',headers=HEADERS,json=edit|{'end':999}).status_code == 422
        for mode in ['split','single','fit']:
            result = client.post(f'/api/projects/{pid}/exports', headers=HEADERS, json=edit|{'layout':mode})
            assert result.status_code == 200, result.text
            j = result.json()
            process(claim())
            assert job(j['id'])['status'] == 'succeeded', job(j['id'])
            path = DATA / pid / f"{j['id']}.mp4"
            meta = probe(path)
            assert (meta['width'],meta['height']) == (1080,1920)
            assert meta['hasAudio'] and abs(meta['duration']-2) < .15
            assert client.get(f"/api/exports/{j['id']}").status_code == 200
            subprocess.run([FFMPEG,'-v','error','-i',str(path),'-f','null','-'], check=True, creationflags=NO_WINDOW)
            if mode == 'split':
                pix = subprocess.check_output([FFMPEG,'-v','error','-i',str(path),'-frames:v','1','-vf','scale=1:2','-pix_fmt','rgb24','-f','rawvideo','-'],creationflags=NO_WINDOW)
                assert pix[0] > pix[2], list(pix)  # top predominantly red
                assert pix[5] > pix[3], list(pix)  # bottom predominantly blue
        queued = client.post(f'/api/projects/{pid}/exports',headers=HEADERS,json=edit).json()
        assert client.post(f"/api/jobs/{queued['id']}/cancel",headers=HEADERS).json()['status'] == 'cancelled'
        assert client.get('/api/media/../../source/proxy').status_code != 200

def test_crop_limits():
    for x in (0,.3,.5,1):
        for y in (0,.5,1):
            w,h,left,top = crop_box(1920,1080,9/16,x,y)
            assert left >= 0 and top >= 0 and left+w <= 1920 and top+h <= 1080
            assert all(n%2 == 0 for n in [w,h,left,top])
