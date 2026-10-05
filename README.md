# Clippa Local

Estudio personal de clips: **Astro + React + TypeScript**, **Python + FastAPI**, SQLite y procesador independiente FFmpeg. Vídeos y tipografías se sirven localmente.

## Arranque en Windows

Acceso directo instalado: **Clippa** en el escritorio. Abre una ventana de aplicación del navegador e inicia API, procesador y web compilada sin consola. **Detener Clippa** detiene esos procesos e interrumpe trabajos activos: úsalo cuando hayan terminado. Cerrar la ventana deja el motor disponible en segundo plano. Sigue dependiendo de esta carpeta, Node y `.venv`; no es todavía un instalador independiente. Para recrear los accesos: `powershell -File scripts/install-shortcut.ps1`. Diagnóstico del lanzador: `.clippa-data/desktop/studio.log`.

Requisitos: Node.js compatible con Astro 7 y Python 3.13. Desde esta carpeta:

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm run dev:full
```

Abre http://127.0.0.1:4322. El comando inicia web, API en 4323 y procesador. FFmpeg y ffprobe se instalan con npm. Los servicios escuchan solamente en la interfaz local.

## Flujo disponible

1. Importar vídeo real de hasta 5 GB, sujeto a espacio libre. Se valida con ffprobe.
2. Esperar la preparación de copia ligera y miniatura. El original se conserva.
3. Elegir inicio, final, título y composición: imagen completa, recorte individual o dos zonas del mismo vídeo apiladas.
4. Ajustar manualmente el centro de cada zona y comprobar la reproducción con audio.
5. Guardar y exportar a MP4 H.264/AAC, 1080 × 1920 a 30 fps desde el original. Descargar desde editor o Exportaciones.

Los trabajos persisten en SQLite, muestran progreso real y permiten cancelar o reintentar. Tras reiniciar, un trabajo sin actividad durante 90 segundos queda interrumpido y se puede reintentar. Originales, proxies, miniaturas y exportaciones viven en `.clippa-data/<id>`; registro en `.clippa-data/studio.sqlite3`.

## Límites actuales

Actualización 23/09: ya hay transcripción local multilingüe y detección de idioma, corrección/búsqueda de texto, descarga SRT y subtítulos incrustados. En el editor, usa «Tu mesa de análisis», guarda correcciones y activa «Mostrar e incrustar subtítulos». La traducción disponible tiene inglés como destino. Preparar modelos en otro equipo: `.\.venv\Scripts\python.exe scripts/setup-analysis.py`.

También hay detección de caras del intervalo seleccionado con una propuesta de encuadre fijo individual/dividido. Los fragmentos sugeridos usan pausas y duración flexible (hasta 10 minutos configurables); no son una selección semántica de los mejores momentos. Seguimiento del movimiento, identificación de hablante y dirección automática siguen pendientes.

Seguimiento automático, asociación de voces y caras, propuestas semánticas e instalador Tauri **siguen pendientes**. La pantalla dividida usa centros fijos, manuales o propuestos por detección. Se rechazan HDR y píxeles no cuadrados hasta implementar conversión controlada. La vista previa reducida puede tener diferencias de redondeo y de composición tipográfica respecto al render ASS final.

Plan completo: `../PLAN_CLIP_LOCAL_PARA_LUNA.md`. Estado verificable: `docs/STATUS.md`. Los JSON antiguos se conservan sin migración automática: no representaban importaciones validadas.

## Verificación

```powershell
npx tsc --noEmit
npm run build
.\.venv\Scripts\python.exe -m pytest -q
```

Tests con vídeo sintético y audio en directorio temporal: importación, rangos HTTP, conflictos de edición, tres composiciones, duración, resolución, audio y orden de zonas. No usan vídeos personales.

Para crear una muestra técnica en la biblioteca, con el estudio iniciado: `.\.venv\Scripts\python.exe scripts/create-demo.py`. Cada ejecución crea un proyecto nuevo.

Para comprobar la compilación: mantener `npm run server` y `npm run worker`, y ejecutar `npm run preview -- --port 4322` con el servidor de desarrollo detenido.
