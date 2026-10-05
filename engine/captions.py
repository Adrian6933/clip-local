"""Caption timing shared by API and immutable export snapshots."""
import re


def cues_from_words(words):
    cues, group = [], []
    for word in words:
        if word['end'] <= word['start'] or not word['text'].strip():
            continue
        if group and (len(group) >= 7 or len(' '.join(w['text'] for w in group)) + len(word['text']) > 44
                      or word['start'] - group[-1]['end'] > .65 or word['end'] - group[0]['start'] > 4.5):
            cues.append({'start': group[0]['start'], 'end': group[-1]['end'], 'text': ' '.join(w['text'].strip() for w in group)})
            group = []
        group.append(word)
        if re.search(r'[.!?。！？]$', word['text'].strip()):
            cues.append({'start': group[0]['start'], 'end': group[-1]['end'], 'text': ' '.join(w['text'].strip() for w in group)})
            group = []
    if group:
        cues.append({'start': group[0]['start'], 'end': group[-1]['end'], 'text': ' '.join(w['text'].strip() for w in group)})
    return cues


def clip_cues(cues, start, end):
    return [{'start': max(c['start'], start)-start, 'end': min(c['end'], end)-start, 'text': c['text']}
            for c in cues if c['end'] > start and c['start'] < end and c['text'].strip()]


def timestamp(t, ass=False):
    total = max(0, round(t * (100 if ass else 1000)))
    unit = 100 if ass else 1000
    seconds, fraction = divmod(total, unit)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}:{minutes:02}:{seconds:02}.{fraction:02}' if ass else f'{hours:02}:{minutes:02}:{seconds:02},{fraction:03}'


def srt(cues):
    return '\n\n'.join(f"{i+1}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues)) + '\n'


def ass(cues):
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,64,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,85,85,220,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = []
    for cue in cues:
        # User text cannot inject ASS override tags or line escapes.
        text = cue['text'].replace('\\', '＼').replace('{', '｛').replace('}', '｝').replace('\r', '').replace('\n', r'\N')
        lines.append(f"Dialogue: 0,{timestamp(cue['start'], True)},{timestamp(cue['end'], True)},Default,,0,0,0,,{text}")
    return header + '\n'.join(lines) + '\n'


def moment_candidates(cues, minimum=20, maximum=180):
    """Transparent pause/sentence heuristic; not a semantic/virality model."""
    if not cues:
        return []
    groups, current = [], []
    for cue in cues:
        if current and cue['end'] - current[0]['start'] > maximum:
            groups.append(current)
            current = []
        current.append(cue)
    if current:
        groups.append(current)
    # A second pass splits at pauses only after a complete minimum-length block.
    output = []
    for group in groups:
        block = []
        for idx, cue in enumerate(group):
            block.append(cue)
            pause = idx == len(group)-1 or group[idx+1]['start'] - cue['end'] >= 1.0
            if pause and (cue['end'] - block[0]['start'] >= minimum or idx == len(group)-1):
                text = ' '.join(c['text'] for c in block)
                output.append({'start': block[0]['start'], 'end': cue['end'], 'title': text[:90],
                               'reason': 'Bloque de discurso delimitado por pausas; revisa si la idea está completa.',
                               'method': 'pauses-and-sentences', 'text': text})
                block = []
    return output[:100]
