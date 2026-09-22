# Clippa — plan maestro de ampliación, diseño y validación

Fecha: 19 de septiembre de 2026. Destinatario: Luna o la siguiente sesión de implementación. Estado: planificación; las tareas siguientes están pendientes salvo la base descrita expresamente como existente.

Este documento amplía `../../PLAN_CLIP_LOCAL_PARA_LUNA.md` y concreta la continuación desde el código actual. No reiniciar el proyecto. Ante diferencias, conservar Astro como frontend y usar el orden de trabajo de este documento. `STATUS.md` registra evidencia, no intenciones.

## 1. Resultado que debe conseguir el producto

Importar una conversación larga, encontrar momentos aprovechables, obtener varios clips, mantener bien encuadradas a las personas, corregir texto y montaje y exportar resultados reutilizables. La automatización tiene que ahorrar tiempo y permitir corregir cualquier decisión.

Recorrido objetivo: biblioteca → vídeo → análisis → candidatos → editor → revisión → exportaciones. El usuario puede saltarse el análisis y empezar manualmente. Si dos personas aparecen juntas, debe poder colocar una arriba y otra abajo, intercambiarlas, seguir sus movimientos y decidir cuándo mostrar solo a una. Una voz fuera de plano nunca justifica inventar una persona visible.

La web local es el producto inicial. La aplicación de escritorio reutilizará el editor y el motor. No convertir el proyecto en un servicio con cuentas y suscripciones para resolver necesidades de uso personal.

## 2. Base revisada y límites de la evidencia

Se han leído `engine/api.py`, `engine/core.py`, `engine/worker.py`, `src/components/Studio.tsx`, configuración y tests existentes. La arquitectura actual es Astro + React + TypeScript, Python/FastAPI, SQLite y FFmpeg. Node inicia herramientas de desarrollo; la API de vídeo es Python.

Ya existen importación binaria, ffprobe, proxy, miniatura, reproducción por rangos, tres composiciones fijas, edición con revisión y exportación MP4. La interfaz tiene biblioteca, búsqueda, ajustes y cola. Los datos viven en `.clippa-data`.

En esta revisión se ejecutaron TypeScript y pytest: TypeScript sin errores y **2 tests aprobados**, con dos avisos de deprecación de dependencias de test. El test integrado contiene varias comprobaciones, pero no equivale a una batería de validación completa. No se ha repetido en esta revisión la prueba visual anterior ni se ha medido calidad de IA. La compilación y revisión visual anteriores constan en STATUS.

No existen todavía transcripción real, detección de personas, seguimiento, diarización, selección semántica, subtítulos, varios clips independientes por proyecto ni instalador. Los colores sintéticos validan composición; no validan rostros, voces o interés editorial.

## 3. Prioridades y dependencias

| Hito | Objetivo | Depende de | Puerta para avanzar |
|---|---|---|---|
| M0 | Recuperación y consistencia | Base actual | Fallos inducidos sin pérdida ni resultados falsos |
| M1 | Varios clips y revisiones | M0 | Migrar y reabrir proyectos sin cambios de resultado |
| M2 | Editor manual completo y diseño | M1 | Crear, corregir y exportar sin IA |
| M3 | Dos personas y seguimiento | M1, geometría de M2 | Prueba real con movimiento y corrección manual |
| M4 | Transcripción y subtítulos | M1, tiempos de M2 | Texto corregido idéntico en preview y exportación |
| M5 | Quién habla y dirección automática | M3, M4 | Precisión y cobertura medidas |
| M6 | Propuestas y edición por texto | M4, secuencias de M2 | Propuestas reales y cortes reversibles |
| M7 | Plantillas, audio y lotes | M2, M4 | Misma revisión coherente en todos los destinos |
| M8 | Evaluación integral V1 | M0–M7 esenciales | Matriz de aceptación y benchmark |
| M9 | Aplicación Windows | Ensayo temprano; entrega tras M8 | Flujo real en Windows sin runtimes de desarrollo |
| M10 | Ampliaciones opcionales | Base estable correspondiente | Puerta propia por función |

Trabajar en este orden con entregas pequeñas. El ensayo de compatibilidad de modelos y del empaquetado puede adelantarse para descubrir bloqueos, sin desplazar la estabilización. Una funcionalidad experimental no bloquea el editor manual, pero tampoco cuenta como automática terminada.

## 4. M0 — problemas concretos que hay que investigar primero

Los siguientes son hallazgos de lectura del código; se distingue una condición demostrable por estructura de una hipótesis que requiere reproducción.

| ID | Hallazgo | Cambio previsto | Prueba de aceptación |
|---|---|---|---|
| FIX-01 | `cancel()` lee estado y lo escribe después sin transición condicional | Transición SQL atómica; impedir cancelar un trabajo ya finalizado | Forzar carrera entre reclamar, cancelar y terminar |
| FIX-02 | Heartbeat y cancelación dependen de leer stdout de FFmpeg | Supervisión independiente con timeout y propiedad del proceso | Proceso silencioso sigue cancelable y no se reclama dos veces |
| FIX-03 | Publicar fuente, guardar proyecto y encolar son operaciones separadas | Diario de importación y reconciliación idempotente entre disco y DB | Interrumpir en cada frontera y recuperar sin duplicar fuente |
| FIX-04 | Un fallo de proxy deja `project.status` en processing | Estado de preparación coherente con su trabajo vigente | Biblioteca muestra fallo o cancelación y permite recuperar |
| FIX-05 | `projects()` devuelve todo y `/jobs` limita a 100 | Paginación y contadores SQL independientes | Más de 100 trabajos no alteran cifras ni ocultan historial |
| FIX-06 | El frontend consulta tres endpoints cada 2,5 s | Evitar solapamiento; timeout, backoff y actualización selectiva | Respuesta antigua no revierte estado; desconexión recuperable |
| FIX-07 | Canvas y FFmpeg calculan geometría por separado | Contrato de geometría y comparación de fotogramas | Recortes consistentes, incluyendo rotación y dimensiones impares |
| FIX-08 | `capabilities()` comprueba archivos, no ejecución ni worker | Diagnóstico cacheado de binario, filtros y latido del worker | Binario dañado o worker detenido se muestra correctamente |
| FIX-09 | Se acepta cualquier duración positiva; UI usa mínimo 0,1 s | Política común de duración mínima y fin de medio | Vídeo más corto que 0,1 s: rechazo claro o edición válida |
| FIX-10 | Tolerancia de duración fija de 0,3 s | Tolerancia ligada a frames y muestras, con reglas por contenedor | Detectar cortes incorrectos sin rechazar desfase de muxing permitido |
| FIX-11 | Documento de edición incrustado sin migraciones | Esquema versionado y migrador comprobado | Restaurar copia anterior y repetir migración sin pérdida |
| FIX-12 | Existencia de salida no se valida en descarga | Error estructurado para archivo movido o eliminado | La UI ofrece regeneración; no descarga rota inexplicable |

Añadir una prueba de regresión por riesgo real. No transformar cada detalle visual en un test unitario. Añadir casos de disco lleno durante escritura, no solo comprobar espacio al principio. La reserva debe considerar originales, proxy, exportaciones y temporales simultáneos.

Revisar además fallos de carga que dejan proyectos vacíos, doble pulsación de exportar/reintentar, guardado mientras se escribe y cambio de proyecto con petición pendiente. Resolver idempotencia con claves y restricciones de DB, no solamente deshabilitando botones.

Los leases necesitan identificador de propietario e intento. Solo el propietario vigente puede publicar el resultado. Si otro worker recupera el trabajo, el anterior no puede escribir un éxito tardío. No considerar suficiente el tiempo transcurrido para concluir que el proceso murió.

## 5. M1 — datos que permiten crecer sin rehacerlo todo

Separar Project, MediaAsset, Clip, ClipRevision, Job, Export y AnalysisRun. Un proyecto tiene un original inicialmente y muchos clips. Compartir proxy y análisis entre clips. Duplicar un clip copia su edición, no el vídeo de varios GB.

La migración inicial crea un Clip a partir del `edit` actual, conserva UUID del proyecto, rutas y exportaciones, y registra versión de esquema. Antes de migrar, hacer copia consistente mediante API de backup de SQLite; no copiar a ciegas un archivo mientras WAL recibe escrituras. Ensayar éxito, interrupción y rollback en datos temporales.

Cada ClipRevision es una instantánea inmutable. Una exportación referencia exactamente una revisión, configuración de render y versiones relevantes. Si se cambia el título después, el archivo en cola conserva su nombre y contenido previstos. Guardar revisión base y hash de contenido para detectar conflictos.

Tiempos canónicos en microsegundos enteros y segmentos [inicio, fin). Registrar PTS/time_base cuando haga falta; no convertir VFR a tiempos suponiendo FPS constantes. El frontend puede mostrar segundos decimales, pero convierte en la frontera del contrato.

Secuencia mínima: lista ordenada de intervalos de origen. Su duración de salida es la suma de intervalos. Un mismo fragmento puede aparecer varias veces; la conversión salida→origen identifica también la instancia del segmento, no solo el timestamp.

LayoutSegment, CaptionCue y AudioEdit usan el mismo mapa temporal. Las correcciones manuales incluyen procedencia y bloqueo. Regenerar análisis no las borra; producir alternativas y permitir comparar.

Estructura incremental propuesta, conservando el proyecto actual:

```text
src/pages/                   Astro: entrada y rutas
src/components/studio/       biblioteca, shell, ajustes, exportaciones
src/components/editor/       reproductor, timeline, texto, inspector
src/lib/api/                 cliente y tipos de contrato
src/lib/editor/              estado, comandos, geometría y tiempos
src/lib/platform/            navegador y futuro escritorio
engine/domain/               revisiones, clips y validaciones
engine/storage/              repositorios y migraciones
engine/jobs/                 cola, leases y supervisión
engine/media/                probe, proxy, audio y render
engine/analysis/             escenas, caras, voces, texto, propuestas
tests/integration/           DB, FFmpeg y recuperación
tests/fixtures/              generadores y manifiesto del corpus
docs/validation/             informes con evidencia
```

Extraer módulos cuando se intervenga en ellos; evitar una mudanza masiva que cambie todas las rutas antes de añadir valor. Mantener scripts actuales durante la transición.

## 6. M2 — diseño de producto y sistema visual

Conservar identidad propia de Clippa: oscuro neutro, acento verde suave, tipografías locales y jerarquía clara. El vídeo es el elemento protagonista. Reservar verde intenso para la acción principal o selección activa; errores y avisos deben distinguirse también por texto e icono.

Crear tokens de colores, superficies, bordes, radios, espaciado, tipografía, sombras y movimiento. Separar fondo de aplicación, panel y control. Escala de espacio basada en 4/8 px; texto de controles legible; evitar información operativa diminuta. Revisar contraste del texto secundario, controles deshabilitados y foco sobre cada superficie.

Componentes comunes: Button, IconButton, Field, Tabs, Dialog, Toast, EmptyState, StatusBadge, JobProgress, ProjectCard y ClipCard. Documentar loading, empty, offline, error, disabled y selected. Los iconos sin texto llevan nombre accesible; las opciones de composición exponen su estado seleccionado.

Biblioteca: reducir el bloque introductorio una vez que hay proyectos para priorizar continuar trabajo. Vista cuadrícula/lista, orden por modificación, filtros, favoritos, etiquetas, duración y número de clips. Menú por proyecto: renombrar, abrir carpeta cuando exista puente nativo, archivar, duplicar metadatos y papelera recuperable. El estado de análisis no debe confundirse con un clip listo.

Proyecto: resumen de fuente, preparación/análisis por etapas, lista de clips, botón crear clip y acceso a transcripción. Un fallo parcial permite usar resultados válidos. Mostrar tareas largas en una bandeja persistente sin tapar el editor.

Editor escritorio: barra superior compacta con nombre, guardado y exportación; texto/candidatos a la izquierda; preview central; inspector a la derecha; timeline inferior. Paneles redimensionables y colapsables con límites útiles. Recordar preferencias de panel, no mezclar estas preferencias con revisiones del vídeo.

Editor móvil: una superficie principal y pestañas Vídeo, Texto, Encuadre y Audio. Exportar y volver siguen accesibles. No encoger tres columnas en una pantalla de 390 px. Para precisión, ampliar el control seleccionado en un panel temporal. Evitar que teclado virtual y navegación inferior oculten guardar o los últimos campos.

Diseñar pantallas de referencia a 390, 768, 1280 y 1440 px; probar también zoom 200 %, ventanas bajas y nombres de 150 caracteres. Los puntos de corte finales se ajustan al contenido. Los estados de carga conservan tamaño para no saltar de posición.

Accesibilidad: recorrido solo con teclado; foco que entra y vuelve correctamente en diálogos; Escape; formularios con error asociado; no atajos mientras se edita texto; alternativa numérica a arrastrar; reducción de animaciones; targets táctiles cómodos. No depender solo del color o del hover.

Aceptación visual: capturas revisadas de biblioteca vacía/poblada, editor en todos los modos, diálogo, error, progreso, lista larga y vista móvil. Además de mirar capturas, completar el flujo con teclado y con ratón.

## 7. M2 — herramientas del editor manual

### 7.1 Reproductor y encuadre

Espacio reproduce/pausa, flechas avanzan un frame cuando hay foco en el editor, J/K/L son opcionales y se documentan. Mostrar tiempo de origen y duración del clip diferenciados. Incluir volumen, mute, velocidad de preview y pantalla completa. Cambiar velocidad de preview no modifica exportación.

Mostrar original y salida con un comparador. Dibujar regiones editables sobre el original con arrastre, zoom limitado y reset. En dividido: identificar A/B, intercambiar arriba/abajo, recentrar y ajustar margen de cabeza. Un overlay técnico de detecciones es opcional; el usuario normal ve «Encuadre superior» y «Encuadre inferior».

La vista canvas sigue siendo rápida para arrastre. Una previsualización renderizada de pocos segundos valida el resultado canónico, especialmente subtítulos y movimiento. Mostrar su estado y revisión; no confundir preview desactualizado con resultado final.

### 7.2 Timeline y secuencias

Miniaturas de vídeo, onda de audio, regla temporal, zoom y desplazamiento. Arrastrar inicio/final, introducir tiempo, dividir, recortar, eliminar segmento y reordenar. Ajuste magnético a frames, palabras y cortes con opción de desactivar. Seleccionar un segmento muestra sus propiedades.

Pistas iniciales: fuente, composición y subtítulos. Audio adicional llega en M7. Mantener la UI sencilla: los detalles avanzados aparecen al seleccionar un elemento. Virtualizar listas largas, generar miniaturas por demanda y limitar caché.

Deshacer/rehacer mediante comandos de edición: una operación de arrastre produce una entrada final, no cientos. Historial acotado y snapshots de revisiones guardadas. Deshacer no puede borrar una exportación finalizada o un original.

Autoguardado serializado tras inactividad breve, cola de cambios locales y revisión optimista. Si hay conflicto entre pestañas, conservar borrador, explicar qué cambió y ofrecer recargar o guardar como copia. No resolver conflictos de vídeo fusionando campos arbitrariamente.

Aceptación: crear tres clips del mismo vídeo, unir dos intervalos en uno, cambiar encuadre solo en un tramo, deshacer, cerrar/reabrir y exportar la revisión elegida.

## 8. M3 — detección y seguimiento de personas

Implementar primero escenas y detección de caras en una muestra real; después asociación temporal y render. Los candidatos de biblioteca del plan original siguen siendo hipótesis hasta comprobar compatibilidad, licencia y consumo en este equipo. Registrar decisiones y versiones en MODELS.md.

Cada detección contiene tiempo, caja normalizada, confianza y escena. Cada trayectoria conserva muestras, huecos y procedencia. A/B son participantes internos, no identidades reales. Detectar una cara no identifica su voz.

Reglas: reiniciar asociación ante corte de cámara; mantener IDs estables dentro de escena; no reordenar A/B por posición en cada fotograma; limitar interpolación a huecos breves; marcar ambigüedad cuando cruzan o se ocultan. Si una persona sale, usar un encuadre conservador o pedir revisión, sin seguir un punto vacío indefinidamente.

Encuadre: incluir cabeza y torso, margen superior, límites de zoom, suavizado y velocidad de desplazamiento. Evitar temblores y saltos por fluctuaciones pequeñas. Cortes originales pueden permitir discontinuidad; en una toma continua exigir suavidad.

Controles: escoger cara con clic, bloquear sujeto, corregir posición en un instante, crear keyframe, aplicar a un tramo e intercambiar participantes. Correcciones manuales prevalecen. Permitir borrar solo una corrección y recalcular ese tramo.

Casos mínimos: una persona quieta, dos sentadas, movimiento lateral, giro de perfil, oclusión, salida de plano, cruce y cambio de cámara. Añadir personas pequeñas en plano general antes de prometer seguimiento de reuniones.

Aceptación: cajas anotadas y vídeo exportado revisado; medir rostro dentro de región útil, intercambios de IDs, huecos y movimientos bruscos. Usar objetivos del plan original, reportando denominadores. Si no se cumplen, mantener la función experimental y explicar el caso que falla.

## 9. M4 — transcripción y edición de subtítulos

Transcripción local mediante adaptador, elección de idioma automática o manual, modelo pequeño/preciso después de medir. Primera descarga con tamaño y progreso; cancelación y reanudación si el proveedor lo permite. Una vez instalado, verificar funcionamiento sin conexión.

Guardar resultado original, palabras con tiempo y confianza, versión de modelo y correcciones aparte. Detectar silencio, audio ausente, repeticiones anómalas y tiempos fuera del vídeo. No convertir ausencia de audio en error de importación.

Editor de texto: click para saltar, búsqueda, corregir palabra, unir/dividir bloques, modificar tiempo, marcar duda y volver al original. El resaltado sigue la reproducción. Editar texto no recorta automáticamente el vídeo. Eliminar vídeo por texto es una acción distinta con preview y deshacer.

Subtítulos: tres estilos propios iniciales, tamaño, peso, color, contorno, fondo, posición y palabras destacadas. Límite de líneas, saltos semánticos, márgenes y zonas seguras. Emojis y fuentes adicionales solo cuando exista render consistente; usar fallback visible ante glifo no disponible.

Generar SRT y ASS; opcional VTT para preview. Para incrustar, renderizar con fuentes administradas desde una misma especificación de estilo. Escapar texto y rutas según el formato de subtítulos; nunca interpolar texto arbitrario en comandos de shell.

Exportación sin subtítulos, con subtítulos incrustados o archivos separados. Cada exportación fija la revisión textual. Cambiar el modelo no destruye las correcciones anteriores.

Aceptación: español con acentos, signos, números, nombres propios, frase larga, silencio, dos voces y corrección manual. Revisar legibilidad en móvil, tiempos sobre muestra anotada y coincidencia literal entre editor, SRT y vídeo. No declarar precisión por el mero hecho de que exista un JSON.

## 10. M5 — quién habla y cuándo cambiar el plano

Separar tres problemas: detectar caras, separar turnos de voz y determinar qué cara habla. Probar primero un adaptador audiovisual con una muestra anotada, antes de diseñar toda la interfaz alrededor de una capacidad no confirmada.

Estado por intervalo: A habla, B habla, ambos, voz fuera de plano, silencio o desconocido. Conservar puntuaciones y origen, sin presentarlas como probabilidades calibradas. Una voz no se asigna por el lado donde aparece la cara.

Director de composición: mostrar a quien habla con permanencia mínima, umbral de cambio y margen de confianza. Ante solapamiento, preferir ambos; ante duda, plano general o dividido. Evitar saltos rápidos en respuestas cortas y risas. Los parámetros se miden con vídeos de prueba, no se fijan como verdades universales.

UI: «Ambos», «Solo A», «Solo B», «Seguir a quien habla», «Automático conservador». Vista de decisiones por tramos y marcador «Revisar». Permitir escuchar una muestra y vincular voz con cara durante un intervalo. Los vínculos manuales se pueden bloquear.

Aceptación: medir porcentaje de tiempo correcto y porcentaje cubierto automáticamente, además de errores en solapamiento y fuera de plano. No lograr aparente precisión enviando todo a desconocido. La función termina cuando exporta el seguimiento medido y corregible, no al mostrar botones.

## 11. M6 — encontrar momentos y editar por texto

Crear candidatos desde transcripción con contexto anterior/posterior. Controles: duración objetivo, número de clips, tema, tono y rango del vídeo. Cada propuesta muestra título, inicio/final, motivo y extracto real.

Validador: límites temporales, duración, IDs existentes, redundancia, comienzos comprensibles y conclusión no truncada. Ajustar a frase sin salir del medio. Si el modelo devuelve intervalos inválidos, rechazar o reparar de manera acotada y registrada.

Las puntuaciones se llaman relevancia o prioridad orientativa; no «probabilidad de viralidad». La calidad se revisa con criterio editorial humano: claridad, contexto suficiente y utilidad del fragmento.

Acciones: escuchar preview, aceptar, descartar, ampliar, combinar y crear clip. Distinguir propuestas nuevas de clips ya corregidos. Generar otra tanda no reemplaza trabajo guardado.

Búsqueda por texto y etiquetas primero; búsqueda semántica después, con índice versionado y reutilizable. Edición por instrucciones produce un borrador de cambios revisable, nunca ejecuta herramientas descritas dentro de una transcripción.

Pausas y muletillas: detección como sugerencias, preview con cortes, selección individual y deshacer. Remapear subtítulos, audio y encuadres mediante la secuencia canónica. No eliminar respiraciones o silencios expresivos automáticamente por defecto.

Un proveedor remoto es opcional y necesita configuración explícita, límites y descripción de datos enviados. Si falta, el editor sigue disponible; una heurística rotulada no cuenta como selección semántica terminada.

## 12. M7 — marca, formatos, audio y exportación

Plantillas: nombre, proporción, composición, subtítulos, colores, logo, márgenes y título. Guardar versión de plantilla. Aplicarla crea una revisión del clip; modificarla después no cambia exportaciones anteriores.

Perfiles: vertical 9:16, cuadrado 1:1, horizontal 16:9 y después 4:5. Recalcular encuadre para cada proporción y revisar texto; no estirar un resultado vertical. Zonas seguras editables y con fecha si representan interfaces de redes que pueden cambiar.

Audio: ganancia, mute de tramo, fundidos, normalización opcional y medición de saturación. Preservar pistas originales; elegir la pista deseada cuando haya varias. Reducción de ruido como opción medida, con comparador antes/después para evitar voz artificial.

Música local importada y bajada automática durante voz en una segunda entrega de audio. Mostrar mezcla y exportación coherentes. No asumir derechos sobre bibliotecas externas ni descargar música automáticamente.

Exportación: preset sencillo y panel avanzado; resolución, FPS compatible, calidad y nombre seguro. Mostrar revisión, duración, formato y subtítulos incluidos antes de encolar. Nombre útil derivado del título, colisiones resueltas y caracteres Windows saneados.

Lotes: varios clips y perfiles; cola con prioridad y cancelación individual. Cada elemento fija su revisión. Un fallo no cancela resultados independientes. Informar espacio estimado como estimación y controlar espacio real durante trabajo.

Validar salida: streams, duración, dimensiones, orientación, decodificación y audio según configuración. Un archivo parcial jamás aparece como descargable. Registrar checksum del archivo para integridad; no exigir bytes idénticos entre codificadores y versiones diferentes.

## 13. Almacenamiento y mantenimiento

Dashboard con tamaño de originales, proxies, análisis, modelos, exportaciones y temporales. Acciones independientes para regenerar proxy y limpiar caché. Papelera recuperable de proyectos con plazo visible; purgar es una operación distinta.

Nunca borrar originales externos por limpiar un proyecto. Antes de mover raíz de datos, validar destino, espacio y trabajos activos; copiar y verificar primero, cambiar puntero después. Permitir cancelar sin dejar proyecto incompleto.

Backup portable: manifiesto versionado, revisiones, metadatos y opción de incluir originales. Restauración detecta UUID repetidos y versiones incompatibles. Exportaciones se pueden excluir si son regenerables, explicándolo.

Caché por hash de fuente, algoritmo/modelo, parámetros y esquema. Cambiar color de subtítulo no retranscribe. Cambiar intervalo reutiliza análisis existente. Descargar modelo nuevo no invalida resultados de versiones anteriores sin una petición de recálculo.

Registro de modelos: fuente, revisión, checksum, licencia de código y pesos, tamaño, dispositivo probado y funcionamiento offline. Elegir dependencias tras ensayo de compatibilidad. No instalar todo el catálogo como preparación de una función futura.

## 14. Contratos, diagnóstico y arquitectura local

Generar tipos del contrato OpenAPI cuando el modelo Clip quede estable. Añadir errores con código, mensaje legible, detalle técnico saneado y reintento permitido. Distinguir API conectada de worker disponible.

Introducir endpoints de clips, revisiones, análisis y transcript sin romper de inmediato las rutas actuales. Añadir compatibilidad temporal y prueba de migración. Paginar biblioteca e historial; generar contadores completos en servidor.

SSE puede reemplazar polling cuando exista necesidad medida: eventos con secuencia, reconexión y snapshot. Mantener polling de respaldo. No introducir WebSocket solo para mostrar porcentajes.

Diagnóstico: versiones, dispositivo, memoria, disco libre, capacidades reales del render, modelo cargado, estado del worker y últimos errores. Logs con correlación por proyecto/trabajo y rotación; no incluir tokens ni transcripciones completas por defecto.

La API sigue en loopback. Revisar Host, Origin, sesión del proceso y rutas administradas durante el empaquetado. Validar parámetros de filtros y usar listas de argumentos. Una distribución de escritorio necesita un canal nativo controlado para autorizar archivos y no un endpoint que acepte cualquier ruta del disco.

## 15. M9 — aplicación de escritorio Windows

Ensayo temprano: abrir frontend compilado, arrancar sidecar, esperar readiness y cerrarlo sin procesos huérfanos. La entrega completa se hace tras estabilizar el flujo principal.

PlatformBridge: seleccionar archivo, importar, mostrar carpeta, guardar salida, estado del motor y almacenamiento. El editor recibe IDs; no conoce rutas nativas. El modo navegador mantiene carga HTTP.

Instalador incluye los componentes permitidos para redistribución y obtiene modelos aparte. Datos en carpeta de usuario, no dentro de Program Files. Verificar rutas Unicode, espacios, puertos ocupados, WebView y permisos normales.

Una sola instancia del motor por almacén, secreto de sesión local, proceso supervisado, reinicio con recuperación y logs accesibles. Cerrar ventana debe explicar si los trabajos continúan o se interrumpen; usar un comportamiento único y comprobado.

Actualizar conserva DB y revisiones mediante migración con backup. Firma, publicación y actualización automática son tareas explícitas posteriores; no afirmar que existen por generar un ejecutable.

Aceptación: instalación en Windows sin Python/Node de desarrollo, importar, transcribir, corregir, exportar, cerrar/reabrir y desinstalar sin eliminar datos inesperadamente. Si no hay máquina limpia, marcar esa prueba pendiente.

## 16. M10 — catálogo de ampliaciones con puertas propias

| Función | Valor | Condición previa y prueba |
|---|---|---|
| Tres/cuatro personas | Mesas redondas | IDs estables, regiones legibles y cambios de plano evaluados |
| Pantalla compartida | Tutoriales | Regiones manuales primero; comprobar texto legible exportado |
| Gameplay + cámara | Clips de juegos | Seleccionar región de cámara y acción; no confundir caras del juego |
| Multicámara | Podcasts con fuentes separadas | Sincronía, drift y reloj común antes de cambiar cámaras |
| Imágenes de apoyo | Explicar ideas visualmente | Importación local, derechos y segmentos reversibles |
| Traducción de subtítulos | Audiencia multilingüe | Revisar texto traducido, tiempos, tipografía y expansión de líneas |
| Títulos y portadas | Preparar publicación | Frame seleccionado y texto editable; assets exportados de verdad |
| Exportación a editores | Continuar trabajo fuera | Formato elegido y round-trip en el editor objetivo |
| Edición por instrucciones | Acelerar cambios frecuentes | Acciones acotadas, borrador y deshacer |
| Detección de acciones | Vídeos sin diálogo | Corpus específico; la transcripción no basta |
| Importación por URL | Ahorrar descarga manual | Alcance autorizado, protocolos, redirecciones y límites definidos |
| Publicación social | Entregar directamente | Integración solicitada, permisos, preview y estado de envío |

No activar publicación o servicios remotos como dependencia del editor. Priorizar seguimiento, texto y fiabilidad antes de ampliar a todos los casos audiovisuales.

## 17. Plan de pruebas funcionales y de recuperación

Separar tests rápidos de contratos/geometría, integración con DB y FFmpeg, flujos de navegador y evaluación de modelos. Los mocks sirven para estados de error y contratos, no para certificar IA.

| Grupo | Casos obligatorios | Evidencia |
|---|---|---|
| Importación | Vídeo válido, inválido, sin audio, Unicode, desconexión, disco lleno, carga duplicada | DB, temporales, estado final y mensaje |
| Metadatos | Rotación, SAR, HDR, VFR, pistas múltiples, duración mínima | Fixture y política esperada documentada |
| Edición | Dos pestañas, guardar mientras se escribe, cambio de proyecto, undo/redo | Revisiones y borrador preservado |
| Cola | Dos workers, cancelación en cola/en ejecución/al finalizar, retry doble, proceso silencioso | Una publicación por intento y proceso liberado |
| Recuperación | Corte tras fuente, DB, proxy, rename y antes de éxito | Reinicio idempotente y originales intactos |
| Geometría | Fit/single/split, bordes, impares, rotación, keyframes | Frames comparados y regiones anotadas |
| Secuencias | Dos cortes, repetición, pausas quitadas, tramos reordenados | Mapa temporal y sincronía |
| Subtítulos | Unicode, líneas largas, palabras corregidas, silencios, cambio de estilo | Texto y frames exportados |
| Exportación | Audio/mute, perfiles, lote, archivo ausente, fallo de encoder | ffprobe, decode y revisión visual |
| UI | Vacío, poblado, error, offline, progreso, teclado, zoom y móvil | Flujo reproducible y capturas |
| Datos | Migración, backup, restauración, papelera, caché | Inventario antes/después y checksums |
| Escritorio | Arranque, puerto ocupado, cierre, actualización, Windows limpio | Instalador e informe |

E2E principal: importar → esperar proxy → crear dos clips → editar intervalo → dividido A/B → guardar → reabrir → exportar → reproducir salida. Extender con transcripción real cuando exista. Test de fallo principal: interrumpir worker durante exportación, reabrir y reintentar sin perder edición.

Automatizar solo flujos con valor de regresión. Mantener evaluaciones visuales y de sincronía; que un botón responda o que FFmpeg termine no demuestra que el contenido sea correcto.

## 18. Corpus, métricas y rendimiento

Crear `tests/fixtures/manifest.json` con origen, permiso de uso, hash, metadatos, propósito y anotaciones. Las fixtures sintéticas verifican mecanismos. Para IA, usar material real autorizado y separar ejemplos de ajuste y evaluación.

Corpus mínimo: monólogo, entrevista fija, interrupciones, movimiento, oclusión, corte de cámara, voz fuera de plano y pantalla compartida. Medios técnicos: vertical rotado, VFR, audio ausente y nombres complejos. Incluir duración corta y un ensayo progresivo de 10, 30 y 60 minutos cuando exista material y espacio.

Objetivos iniciales de evaluación, no resultados logrados: sincronía A/V inferior a 100 ms en puntos anotados; tiempos de subtítulos con mediana inferior a 200 ms y P95 inferior a 500 ms; rostro correctamente encuadrado en al menos 95 % de frames elegibles; hablante correcto en 90 % del tiempo autoasignado con cobertura mínima de 80 %. Heredan el plan original y se revisan explícitamente tras el piloto.

Medir hardware y versión exacta, tiempo por etapa, factor respecto a duración del vídeo, RAM/VRAM máximas, disco temporal, carga de CPU en reposo, latencia de arrastre, búsqueda y apertura. Primer benchmark establece presupuesto; no inventar velocidad garantizada.

Optimización probable a verificar: evitar dibujar canvas continuamente si está pausado y no cambió nada; cancelar peticiones obsoletas; paginar; virtualizar palabras; cachear miniaturas; limitar modelos cargados; liberar memoria entre trabajos. Aplicar tras medir y repetir el caso afectado.

## 19. Entregas concretas para empezar

| Orden | Paquete de trabajo | Archivos probables | Resultado revisable |
|---|---|---|---|
| 1 | Carreras de cancelación y propiedad de jobs | engine/jobs, tests/integration | Tests deterministas de transición |
| 2 | Supervisor y diagnóstico de worker | worker, core, API | Cancelación aun sin stdout y estado vivo verificable |
| 3 | Importación recuperable y errores coherentes | API, storage, UI | Fallos inducidos reconciliados |
| 4 | Migraciones y entidad Clip | storage, domain, contratos | Proyecto antiguo con clip recuperado |
| 5 | Biblioteca de clips y revisiones | componentes studio/editor | Duplicar y editar sin copiar original |
| 6 | Descomponer Studio y tokens visuales | src/components, styles | Mismo flujo sin regresión visual |
| 7 | Timeline, crop y undo/redo | editor, geometría, tiempos | Edición precisa por tramos |
| 8 | Corpus y ensayo detector/tracker | analysis, fixtures, MODELS | Dos caras seguidas en vídeo real |
| 9 | Integrar seguimiento y preview canónico | renderer, editor | Corregir trayectoria y exportarla |
| 10 | ASR y editor textual | analysis, transcript UI | Palabras reales persistidas |
| 11 | Subtítulos y estilos | render, captions, editor | Texto corregido en SRT y MP4 |
| 12 | ASD y decisiones por tramos | voices, director | Métricas de precisión/cobertura |
| 13 | Propuestas y edición por texto | selectors, clips, timeline | Candidatos reales y cortes reversibles |
| 14 | Perfiles, plantillas, audio y lotes | render, presets, exports | Salidas coherentes con revisión |
| 15 | Recuperación integral y benchmark | tests, scripts, docs | Informe V1 con límites honestos |
| 16 | Entrega Windows | platform, desktop, packaging | Instalación y flujo sin runtimes de desarrollo |

Cada paquete debe poder revisarse y probarse antes del siguiente. Dividirlo si mezcla migración, motor e interfaz sin una prueba intermedia. Complejidad relativa: 1–5 media/alta, 6 media, 7–14 alta, 15 alta, 16 alta. No transformar estas categorías en fechas sin medir capacidad y compatibilidad.

## 20. Definición de terminado y documentación viva

Una tarea está terminada cuando tiene comportamiento real, estados de error, persistencia cuando corresponde, prueba pertinente y evidencia registrada. Si afecta al vídeo, inspeccionar el archivo resultante. Si afecta a IA, evaluar material real. Si afecta a recuperación, provocar el fallo.

Actualizar STATUS con: ID/hito, implementado, verificado, no validado, comandos, versiones, evidencia, limitaciones y siguiente tarea. Crear MODELS.md, BENCHMARKS.md y LIMITATIONS.md cuando haya resultados que registrar; no rellenarlos con promesas.

Un hito puede quedar implementado pero sin validar en una condición específica. Ese estado no se llama completo. Un test de contrato con respuesta simulada no certifica un proveedor. Una ventana de escritorio no certifica un instalador.

## 21. Instrucción lista para la siguiente ejecución

> Continúa Clippa desde su código actual siguiendo docs/PLAN_MAESTRO_V2.md y el plan original para detalles complementarios. Mantén Astro + React y Python/FastAPI. Empieza por M0 y reproduce las carreras de cancelación, supervisión e importación antes de corregirlas. Después migra a varios clips y desarrolla los hitos en orden. Conserva datos existentes y valida migraciones en copias. No construyas controles automáticos con resultados ficticios. Documenta evidencia y pendientes en STATUS; comprueba vídeos, interfaz y recuperación. Si un modelo requiere acceso no disponible, registra el requisito exacto y continúa las tareas independientes. No reinicies la aplicación desde cero ni instales todos los modelos por adelantado.

La siguiente acción concreta es FIX-01: reproducir la carrera de cancelación con transiciones controladas y hacer que solo el estado esperado pueda cambiar en la misma transacción.
