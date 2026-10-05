# Modelos locales instalados

## Transcripción

faster-whisper 1.2.1 con Whisper Base multilingüe convertido por Systran, CPU int8. Descarga administrada en `.clippa-data/models/faster-whisper-base`; ejecución con `local_files_only=True`. No se suben audios ni vídeos. El idioma puede detectarse o elegirse. `transcribe` conserva idioma; `translate` traduce a inglés, no a cualquier idioma de destino.

Fuentes: [implementación oficial](https://github.com/SYSTRAN/faster-whisper), [pesos](https://huggingface.co/Systran/faster-whisper-base). Registrar/retener la caché de descarga para reproducibilidad. Código y pesos deben revisarse antes de una redistribución empaquetada.

Validación de esta entrega: voz sintética de Windows en español e inglés, detección del idioma correcta, palabras reconocidas, subtítulos reales y exportación. Esto no equivale a una evaluación de precisión con acentos, ruido, conversaciones solapadas o todos los idiomas reconocidos por el modelo. Base prioriza un tamaño razonable; puede equivocarse y admite corrección de texto.

## Caras

OpenCV 5.0.0.93 y YuNet 2026may con entrada dinámica, análisis 640×640 manteniendo proporciones y relleno. Fuente: [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet). El repositorio declara MIT para esta carpeta. URL y SHA256 de la descarga quedan en `.clippa-data/models/yunet-source.json`.

Muestrea hasta 120 fotogramas del intervalo seleccionado. Propone un encuadre fijo a partir del número de caras más frecuente (0, 1 o 2+). Para más caras selecciona las dos de mayor área de la muestra de referencia. No identifica a la persona real, no mantiene trayectorias y no determina quién habla.

## Instalar o preparar otro equipo

`python -m pip install -r requirements.txt` dentro de `.venv`, después `python scripts/setup-analysis.py`. La descarga usa internet; el procesamiento posterior es local. `CLIPPA_MODEL_DIR` permite separar modelos y datos para pruebas. No añadir tokens al proyecto.

La transcripción y detección se ejecutan en procesos separados, supervisados por el worker para que se puedan cancelar incluso durante inferencia.
