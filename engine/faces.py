"""Sample faces to propose a static crop. Does not infer speaker identity."""
import json
import sys
from collections import Counter
from .core import DATA, MODELS, job, update_job


def main(jid):
    import cv2
    cv2.setNumThreads(2)
    j = job(jid)
    folder = DATA / j['project_id']
    detector = cv2.FaceDetectorYN.create(str(MODELS / 'yunet-2026.onnx'), '', (640,640), .85, .3, 500)
    cap = cv2.VideoCapture(str(folder / 'proxy.mp4'))
    if not cap.isOpened():
        raise ValueError('No se pudo abrir el proxy de vídeo.')
    start, end = j['spec']['start'], j['spec']['end']
    total = min(120, max(1, int((end-start)*2)))
    samples = []
    try:
        for i in range(total):
            t = start + (end-start)*(i+.5)/total
            cap.set(cv2.CAP_PROP_POS_MSEC, t*1000)
            ok, frame = cap.read()
            if not ok:
                continue
            h,w = frame.shape[:2]
            scale = min(640/w,640/h)
            rw,rh = round(w*scale),round(h*scale)
            left,top=(640-rw)//2,(640-rh)//2
            scaled = cv2.copyMakeBorder(cv2.resize(frame,(rw,rh)),top,640-rh-top,left,640-rw-left,cv2.BORDER_CONSTANT,value=(0,0,0))
            _, detections = detector.detect(scaled)
            boxes = []
            for face in detections if detections is not None else []:
                x,y,bw,bh = float(face[0]-left)/rw,float(face[1]-top)/rh,float(face[2])/rw,float(face[3])/rh
                boxes.append({'x': min(1,max(0,x+bw/2)), 'y': min(1,max(0,y+bh*.8)), 'area':bw*bh, 'confidence':float(face[-1])})
            samples.append({'time':t,'faces':boxes})
            update_job(jid, progress=(i+1)/total*.98)
    finally:
        cap.release()
    if not samples:
        raise ValueError('No se pudieron leer fotogramas del intervalo.')
    counts = Counter(min(len(s['faces']),2) for s in samples)
    count = counts.most_common(1)[0][0]
    choices = [s for s in samples if min(len(s['faces']),2)==count]
    reference = max(choices,key=lambda s:sum(f['area'] for f in s['faces']))
    faces = sorted(sorted(reference['faces'],key=lambda f:f['area'],reverse=True)[:2],key=lambda f:f['x'])
    points = [{'x':f['x'],'y':f['y']} for f in faces]
    doc = {'count':count,'samples':len(samples),'start':start,'end':end,'referenceTime':reference['time'],
           'a':points[0] if points else {'x':.3,'y':.5}, 'b':points[-1] if points else {'x':.7,'y':.5},
           'note':'Propuesta fija basada en el número de caras más frecuente. Revisa todo el clip: no sigue movimientos ni identifica al hablante.',
           'counts':dict(counts),'model':'YuNet-2026may','samplesWithFaces':sum(bool(s['faces']) for s in samples)}
    (folder / f'{jid}.analysis.json').write_text(json.dumps(doc),encoding='utf8')


if __name__ == '__main__':
    main(sys.argv[1])
