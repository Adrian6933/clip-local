# Estado verificable · 19 de septiembre de 2026

## Actualización funcional · 23 de septiembre de 2026

Implementados: transcripción local con faster-whisper Base, detección de idioma, transcripción multilingüe y traducción al inglés; palabras con tiempos y bloques de subtítulos; editor de texto con búsqueda, salto temporal, corrección, guardado con revisión y descarga SRT del intervalo; previsualización textual y exportación ASS incrustada con instantánea inmutable. La exportación desde la UI se deshabilita mientras hay texto sin guardar.

Nueva mesa de análisis con duraciones flexibles de propuestas (90, 180, 300 o 600 segundos). Las propuestas usan pausas y bloques de discurso: **no puntúan interés semántico ni viralidad**. El editor permite intervalos de otras duraciones dentro del original. Una prueba conserva un bloque de 90 segundos sin convertirlo en tres clips de 30.

Detector YuNet local sobre hasta 120 muestras del fragmento; propone un encuadre fijo individual o dividido, aplicable por el usuario. Conserva proporciones durante detección. **No hay seguimiento temporal ni reconocimiento del hablante activo**. La imagen de referencia pública anotada de OpenCV produjo 10 detecciones, y un vídeo sin caras produjo cero; esto comprueba integración, no precisión sobre un corpus. En el vídeo de ocho minutos ya importado, los primeros 30 segundos dieron una cara como caso más frecuente sobre 60 muestras.

Comprobado: 4 tests aprobados, TypeScript sin errores y compilación de producción. Ensayos de inferencia local sobre voz sintética de Windows en español e inglés: idiomas reconocidos y subtítulos exportados. Traducción ES→EN ejecutada con resultado coherente. Fotograma del MP4 con subtítulos revisado visualmente. Evidencia técnica en `.test-data/analysis-validation.json`, `subtitles-es.mp4`, `subtitles-en.mp4`, `translation-validation.txt` y `face-validation.json`. Los ensayos sintéticos no certifican calidad en conversaciones con ruido o solapamiento.

La cancelación de jobs usa transición SQL condicional. Análisis en proceso separado con heartbeat y cancelación independientes de stdout. FFmpeg tiene lectura de progreso separada para poder cancelar aunque deje de emitir salida. Todavía no hay leases con propietario ni recuperación por etapas completa.

El siguiente bloque importante sigue siendo seguimiento por escenas, asociación audiovisual y dirección al hablante, junto con selección semántica de momentos completos. La transcripción, subtítulos y detector descritos aquí sustituyen los pendientes homónimos de la fotografía histórica inferior. Modelos y límites en MODELS.md.

Prueba adicional con el vídeo real de 8:28 ya importado: transcripción completa terminada en local, idioma inglés detectado, 1849 palabras y 325 bloques. Se generaron propuestas desde la UI, se activaron subtítulos, se guardó y se exportó el intervalo inicial de 30 segundos con descarga disponible. No se ha anotado el vídeo para medir WER o sincronía; el resultado requiere revisión editorial normal. El original permanece intacto.

F1 funcional y parte manual de F2 implementadas. El plan completo todavía no está terminado.

## Continuación planificada

El plan ampliado está en [PLAN_MAESTRO_V2.md](PLAN_MAESTRO_V2.md): 11 hitos, auditoría de riesgos del código, diseño, varios clips, seguimiento, subtítulos, propuestas, escritorio y matriz de pruebas. La siguiente tarea es FIX-01, transición atómica de cancelación con reproducción de carreras. La revisión de planificación repitió TypeScript sin errores y pytest con 2 tests aprobados y 2 avisos de deprecación; no volvió a validar navegador, compilación ni calidad de IA. Las nuevas funciones descritas son pendientes de implementación.

## Construido

- Astro 7 + React, TypeScript, diseño adaptable oscuro, acento verde y fuentes locales.
- Biblioteca persistente, búsqueda, ordenación, ajustes, ayuda y exportaciones.
- Python/FastAPI, SQLite con transacciones, cola persistente con un trabajo pesado simultáneo.
- Carga con progreso/cancelación, validación, proxy H.264/AAC, miniatura y reproducción por rangos.
- Editor con inicio/final, guardado con revisión, reproducción real, composición manual completa, individual y dividida.
- Exportación desde original, cancelación, reintento y recuperación explícita de trabajos interrumpidos.
- API localhost con validación de origen y cabecera de cliente para escrituras.

## Comprobado

Prueba integrada con vídeo sintético y audio: importación, rechazo de contenido inválido, protección de origen, rangos HTTP, conflicto de revisiones, validación temporal, MP4 en tres modos, resolución 1080×1920, audio, duración y decodificación completa; en dividido, orden superior/inferior de colores. TypeScript y compilación de producción. Dependencias npm actualizadas sin vulnerabilidades notificadas durante esta revisión.

La biblioteca puede contener «Ensayo técnico · vídeo sintético» para verificar el navegador. No representa contenido de usuario ni resultados de IA.

Revisión en navegador a 1440×1000 y 390×844: biblioteca, búsqueda sin resultados, ajustes, editor dividido, guardado y exportación final disponible para descargar. Sin errores de consola durante la comprobación. Tipografías locales y favicon propio. El lanzador mantiene Astro en primer plano para que `concurrently` no cierre prematuramente API y procesador.

## Pendiente del plan

Transcripción real y subtítulos; detección/seguimiento; diarización y asociación voz/cara; planos dinámicos y corrección por tramos; selección de momentos; formatos adicionales; gestión de almacenamiento; empaquetado Tauri. Validación con conversaciones reales y vídeos largos.

La implementación Node antigua está retirada; `server/index.mjs` inicia ahora Python. Los antiguos JSON y sus archivos se conservan sin presentarlos como proyectos verificados.
