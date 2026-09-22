# Estado verificable · 19 de septiembre de 2026

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
