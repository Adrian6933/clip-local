"""Separate durable SQLite queue worker. One heavy process at a time."""
import json
import time
from .core import DATA, db, initialize, project, run_ffmpeg, composition, probe, update_job, job

def claim():
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute("UPDATE jobs SET status='interrupted', error='El procesamiento se interrumpió. Puedes reintentarlo.' WHERE status IN ('running','cancel_requested') AND heartbeat < ?", (time.time()-90,))
        if conn.execute("SELECT 1 FROM jobs WHERE status IN ('running','cancel_requested') LIMIT 1").fetchone():
            return None
        row = conn.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if row:
            conn.execute("UPDATE jobs SET status='running', heartbeat=? WHERE id=?", (time.time(), row['id']))
    return job(row['id']) if row else None

def process(j):
    p = project(j['project_id'])
    folder = DATA / p['id']
    source = folder / 'source'
    temp = folder / f"{j['id']}.partial.mp4"
    try:
        if j['kind'] == 'proxy':
            args = ['-i', str(source), '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(temp)]
            duration = p['media']['duration']
            final = folder / 'proxy.mp4'
        else:
            edit = j['spec']
            duration = edit['end'] - edit['start']
            graph = composition(p['media'], edit)
            args = ['-ss', str(edit['start']), '-i', str(source), '-t', str(duration), '-filter_complex', graph, '-map', '[v]', '-map', '0:a:0?', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(temp)]
            final = folder / f"{j['id']}.mp4"
        run_ffmpeg(args, j['id'], duration)
        result = probe(temp)
        if abs(result['duration'] - duration) > .3:
            raise ValueError('La duración exportada no coincide con el recorte solicitado.')
        if job(j['id'])['status'] == 'cancel_requested':
            raise InterruptedError('Trabajo cancelado')
        temp.replace(final)
        if j['kind'] == 'proxy':
            run_ffmpeg(['-ss', str(min(1, duration/2)), '-i', str(final), '-frames:v', '1', '-update', '1', str(folder / 'poster.jpg')], j['id'], duration)
            with db() as conn:
                conn.execute('BEGIN IMMEDIATE')
                current = json.loads(conn.execute('SELECT document FROM projects WHERE id=?', (p['id'],)).fetchone()[0])
                current['status'] = 'ready'
                conn.execute('UPDATE projects SET document=? WHERE id=?', (json.dumps(current), p['id']))
        update_job(j['id'], status='succeeded', progress=1, output=final.name, heartbeat=time.time())
    except InterruptedError:
        update_job(j['id'], status='cancelled')
    except Exception as exc:
        update_job(j['id'], status='failed', error=str(exc))
    finally:
        temp.unlink(missing_ok=True)

def main():
    initialize()
    print('Clippa worker: preparado', flush=True)
    while True:
        j = claim()
        if j:
            process(j)
        else:
            time.sleep(.75)

if __name__ == '__main__':
    main()
