# 🌌 Aether IA - Asistente Holográfico de Escritorio

Asistente de inteligencia artificial y automatización con interfaz HUD futurista de escritorio. Construido con **Python 3** en el backend y **HTML5 + CSS3 + Three.js (WebGL)** en el frontend, empaquetado nativamente con **`pywebview`** (Microsoft Edge WebView2).

---

## 🏗️ Arquitectura del Proyecto

```
Project4 - Aether IA/
│
├── core/                        # Aether Core (Backend Python)
│   ├── brain.py                 # Cerebro LLM Gemini con memoria RAG y Function Calling
│   ├── semantic_memory.py       # Motor de indexación semántica avanzada (Embeddings 3072D + Búsqueda Híbrida)
│   ├── semantic_index.json      # Caché persistente de vectores y metadatos de memoria
│   ├── vision.py                # Éter Vision: Detección facial y seguimiento biométrico (OpenCV + YuNet)
│   ├── memory.py                # Gestor de memoria persistente a largo plazo
│   ├── memory.json              # Base de conocimientos estructurada del usuario y proyectos
│   ├── context.py               # Conciencia contextual en tiempo real (hora, hábitos, hardware)
│   ├── tools.py                 # Herramientas autónomas de Windows, memoria semántica y cámara
│   ├── voice.py                 # Síntesis de voz neuronal de alta fidelidad (edge-tts)
│   ├── system_monitor.py        # Telemetría real de Windows (CPU, RAM, Disco, Batería)
│   ├── automation.py            # Orquestador del sistema
│   └── bridge.py                # Puente bidireccional JavaScript <-> Python
│
├── web/                         # Aether HUD (Frontend Webview)
│   ├── index.html               # HUD holográfico con visor biométrico y consola
│   ├── css/
│   │   └── hud.css              # Estilos de neón, glassmorphism y scanlines
│   └── js/
│       ├── hud3d.js             # Núcleo 3D en Three.js con seguimiento de cabeza
│       └── app.js               # Enlace con Python, telemetría, biometría en vivo y voz
│
├── main.py                      # Punto de entrada de la aplicación de escritorio
├── run.bat                      # Lanzador rápido de un solo clic
├── requirements.txt             # Dependencias del proyecto
└── Notas.txt                    # Hoja de ruta y visión general
```

---

## ⚡ Capacidades Implementadas

1. **Pipeline de Voz Neuronal de Baja Latencia & Prosodia Adaptativa (Fase 1 & Optimización Avanzada):**
   * **Pipeline Concurrente por Oraciones (`asyncio.gather`):** Paralelización masiva de fragmentos oracionales en hilos WebSocket simultáneos, reduciendo la latencia de síntesis en un **75-80%**.
   * **Cola de Audio Fluida sin Pausas (Gapless Audio Queue):** El frontend encadena y reproduce oraciones de forma continua mientras sincroniza el analizador espectral Web Audio con el núcleo 3D.
   * **Corte Inmediato al Interrumpir (`stopAllAudio`):** Si el usuario ingresa una nueva orden mientras Aether habla, el audio se silencia al instante sin solapamientos.
   * **Motor de Alta Fidelidad:** `edge-tts` (`es-ES-AlvaroNeural`) operando sobre un bucle asíncrono persistente en hilo trabajador dedicado.
   * **Caché Multi-Nivel Instantánea:** Memoria LRU (recuperación en **< 1 ms**) y persistencia en disco en `core/audio_cache/`. Frases del sistema precargadas en segundo plano.
   * **Caché de Embeddings de Consulta:** Recuperación sub-milisegundo para búsquedas semánticas repetidas (ahorro de más de **500 ms**).
   * **Desinfección Fonética (`SpeechSanitizer`):** Filtra markdown, código, emojis y adapta acrónimos técnicos (*FastAPI*, *Three.js*, *CPU*, *RAM*, porcentajes) para una dicción acústica impecable.
   * **Modulación Acústica Contextual:** Ajuste dinámico de tono, velocidad y volumen según el momento (*estándar*, *nocturno*, *alerta*, *calmo*).

2. **Herramientas Autónomas con Function Calling (Fase 2):**
   * Creación de notas automáticas en el escritorio.
   * Diagnóstico completo de hardware en tiempo real.
   * Control de aplicaciones, búsquedas en Google y YouTube con lenguaje libre.

3. **Cerebro Contextual & Memoria Semántica a Largo Plazo (Fase 3 & Optimización):**
   * **Conciencia Situacional en Vivo:** Inyección per-turno de telemetría de Windows (CPU, RAM, energía/batería), hora exacta, fecha en español y presencia biométrica.
   * **Indexación Semántica Avanzada:** Embeddings vectoriales de 3072 dimensiones (`gemini-embedding-001`) con aceleración matricial NumPy.
   * **Búsqueda Híbrida Neuronal:** Fusión de similitud de coseno densa (Dense) + coincidencia léxica/términos clave (Sparse BM25/N-Gram) + ponderación de importancia.
   * **Inyección Dinámica RAG:** Recuperación contextual en tiempo real para cada directiva del usuario, eliminando el límite de recuerdos históricos.
   * **Herramientas de Memoria Autónomas:** `search_long_term_memory`, `list_memory_topics`, `remember_user_detail` y `forget_user_detail`.
   * **Deduplicación Semántica Inteligente:** Previene datos redundantes y actualiza recuerdos existentes por afinidad semántica.
   * **Persistencia Dual y Caché:** Almacenamiento en `core/memory.json` y `core/semantic_index.json` con tolerancia a fallos fuera de línea.
   * **Telemetría en el HUD:** Indicadores reactivos en tiempo real para memoria semántica y modo contextual (*NOCTURNO*, *ALERTA*, *CALMO*, *ESTÁNDAR*).

4. **Biometría y Visión por Computadora (Éter Vision):**
   * Escáner facial en tiempo real mediante cámara web con OpenCV y YuNet.
   * **Rastreo de cabeza (Head Tracking 3D):** El orbe 3D Three.js se inclina y sigue tu rostro en tiempo real cuando te mueves frente a la pantalla.
   * Retícula biométrica HUD y confirmación de identidad por voz (*"Biometría confirmada // Señor"*).
   * Control por voz: *"Aether, activa la visión biométrica"* / *"apaga la cámara"*.

---

## 🚀 Cómo Ejecutar

* **Opción rápida:** Doble clic en `run.bat`
* **Desde la terminal:**
  ```powershell
  python main.py
  ```
