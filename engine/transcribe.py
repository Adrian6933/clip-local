"""Isolated local ASR process; the queue worker supervises lifetime/cancellation."""
import json
import os
from pathlib import Path
import sys
from .core import DATA, MODELS, project, job, update_job
from .captions import cues_from_words

MODEL = MODELS / 'faster-whisper-base'


def main(jid):
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from faster_whisper import WhisperModel
    j = job(jid)
    p = project(j['project_id'])
    if not (MODEL / 'model.bin').is_file():
        raise RuntimeError('Falta el modelo local. Ejecuta scripts/setup-analysis.py antes de transcribir.')
    model = WhisperModel(str(MODEL), device='cpu', compute_type='int8', cpu_threads=min(6, os.cpu_count() or 2), local_files_only=True)
    segments, info = model.transcribe(str(DATA / p['id'] / 'source'),
        language=j['spec'].get('language') or None, task=j['spec'].get('task', 'transcribe'),
        word_timestamps=True, vad_filter=True, beam_size=5, condition_on_previous_text=False)
    words = []
    for segment in segments:
        for w in segment.words or []:
            start, end = max(0, w.start, words[-1]['end'] if words else 0), min(p['media']['duration'], w.end)
            if end > start:
                words.append({'start': round(start,3), 'end': round(end,3), 'text': w.word.strip(), 'confidence': round(w.probability,3)})
        print(json.dumps({'progress': min(.98, segment.end / p['media']['duration'])}), flush=True)
        update_job(jid, progress=min(.98, segment.end / p['media']['duration']))
    result = {'language': info.language, 'languageProbability': info.language_probability,
              'task': j['spec'].get('task', 'transcribe'), 'model': 'faster-whisper-base',
              'words': words, 'cues': cues_from_words(words)}
    path = DATA / p['id'] / f'{jid}.analysis.json'
    path.write_text(json.dumps(result, ensure_ascii=False), encoding='utf8')


if __name__ == '__main__':
    main(sys.argv[1])
