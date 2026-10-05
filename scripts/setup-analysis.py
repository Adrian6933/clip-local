"""Download only public model weights; never upload media."""
import os
from pathlib import Path
import urllib.request
import hashlib
import json
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
from faster_whisper.utils import download_model

root = Path(__file__).resolve().parents[1]
target = root / '.clippa-data/models/faster-whisper-base'
target.mkdir(parents=True, exist_ok=True)
download_model('base', output_dir=str(target))
print('Modelo multilingüe local preparado:', target)
url = 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2026may.onnx'
face = root / '.clippa-data/models/yunet-2026.onnx'
if not face.is_file():
    temporary = face.with_name('yunet.partial.onnx')
    urllib.request.urlretrieve(url, temporary)
    import cv2
    import numpy as np
    detector=cv2.FaceDetectorYN.create(str(temporary), '', (640,640))
    detector.detect(np.zeros((640,640,3),dtype=np.uint8))
    temporary.replace(face)
(face.parent / 'yunet-source.json').write_text(json.dumps({'url':url,'sha256':hashlib.sha256(face.read_bytes()).hexdigest(),'license':'MIT'}),encoding='utf8')
print('Detector local de caras preparado:', face)
