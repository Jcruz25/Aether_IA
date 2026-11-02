/**
 * Aether HUD - Lógica Principal y Puente con Aether Core
 * Conexión de Telemetría, Audio Neuronal (edge-tts) y Visualización Reactiva
 */

let isPywebviewReady = false;
let speechRecognizer = null;
let isListening = false;

// Audio Neuronal y Analizador de Ondas
let currentAudio = null;
let audioContext = null;
let audioAnalyser = null;
let audioSourceNode = null;
let audioAnimFrame = null;
let audioQueue = [];
let isPlayingQueue = false;

// Elementos de la UI
const cpuPercentEl = document.getElementById('cpu-percent');
const cpuBarEl = document.getElementById('cpu-bar');
const cpuCoresEl = document.getElementById('cpu-cores');

const ramTextEl = document.getElementById('ram-text');
const ramBarEl = document.getElementById('ram-bar');

const diskTextEl = document.getElementById('disk-text');
const diskBarEl = document.getElementById('disk-bar');

const batteryTextEl = document.getElementById('battery-text');
const hudStatusTextEl = document.getElementById('hud-status-text');
const commandInputEl = document.getElementById('command-input');
const micBtnEl = document.getElementById('mic-btn');

// Esperar al puente de pywebview
window.addEventListener('pywebviewready', () => {
    isPywebviewReady = true;
    startTelemetryLoop();

    // Saludo inicial proactivo contextual
    if (window.pywebview && window.pywebview.api && window.pywebview.api.get_initial_briefing) {
        logHud("SINCRONIZANDO CONTEXTO NEURONAL...");
        window.pywebview.api.get_initial_briefing().then(res => {
            if (res && res.message) {
                logHud(res.message, true);
                const audioToPlay = (res.chunks && res.chunks.length > 0) ? res.chunks : res.audio;
                if (audioToPlay) {
                    playNeuralAudio(audioToPlay, res.message);
                }
            }
        }).catch(err => {
            console.error("Error al obtener saludo proactivo:", err);
            logHud("AETHER CORE VINCULADO // TODOS LOS SISTEMAS EN LÍNEA");
        });
    } else {
        logHud("AETHER CORE VINCULADO // TODOS LOS SISTEMAS EN LÍNEA");
    }
});

// Actualización de mensajes en el HUD
function logHud(message, isAether = false) {
    if (hudStatusTextEl) {
        hudStatusTextEl.textContent = isAether ? message : message.toUpperCase();
        hudStatusTextEl.classList.add('glow-text');
    }
}

/**
 * Detiene inmediatamente cualquier reproducción de audio previa (corte instantáneo al nuevo comando).
 */
function stopAllAudio() {
    audioQueue = [];
    isPlayingQueue = false;

    if (currentAudio) {
        try {
            currentAudio.pause();
            currentAudio.currentTime = 0;
            currentAudio.src = "";
        } catch (e) {}
        currentAudio = null;
    }

    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }

    if (audioAnimFrame) {
        cancelAnimationFrame(audioAnimFrame);
        audioAnimFrame = null;
    }

    if (typeof triggerPulse === 'function') {
        triggerPulse(1.0);
    }
}

/**
 * Reproducción de Voz Neuronal de Alta Fidelidad y Mínima Latencia.
 * Soporta reproducción individual o encadenada (gapless queue) para oraciones concurrentes.
 */
function playNeuralAudio(audioPayload, fallbackText = "") {
    if (!audioPayload || (Array.isArray(audioPayload) && audioPayload.length === 0)) {
        if (fallbackText) speakBrowserFallback(fallbackText);
        return;
    }

    // Detener cualquier audio previo
    stopAllAudio();

    if (Array.isArray(audioPayload)) {
        audioQueue = [...audioPayload.filter(c => !!c)];
    } else {
        audioQueue = [audioPayload];
    }

    playNextAudioInQueue(fallbackText);
}

function playNextAudioInQueue(fallbackText = "") {
    if (audioQueue.length === 0) {
        isPlayingQueue = false;
        if (typeof triggerPulse === 'function') triggerPulse(1.0);
        return;
    }

    isPlayingQueue = true;
    const uri = audioQueue.shift();

    try {
        currentAudio = new Audio(uri);

        // Inicializar contexto Web Audio si no está activo
        if (!audioContext) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
                audioContext = new AudioCtx();
                audioAnalyser = audioContext.createAnalyser();
                audioAnalyser.fftSize = 64;
            }
        }

        if (audioContext && audioAnalyser) {
            try {
                audioSourceNode = audioContext.createMediaElementSource(currentAudio);
                audioSourceNode.connect(audioAnalyser);
                audioAnalyser.connect(audioContext.destination);
            } catch (err) {
                // Si ya estaba conectado o hay restricción CORS local
            }
        }

        const dataArray = audioAnalyser ? new Uint8Array(audioAnalyser.frequencyBinCount) : null;

        function syncAudioVisualizer() {
            if (!currentAudio || currentAudio.paused || currentAudio.ended) {
                cancelAnimationFrame(audioAnimFrame);
                return;
            }

            if (audioAnalyser && dataArray) {
                audioAnalyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
                const avg = sum / dataArray.length;
                const dynamicIntensity = 1.0 + (avg / 255.0) * 2.8;

                if (typeof triggerPulse === 'function') {
                    triggerPulse(dynamicIntensity);
                }
            }

            audioAnimFrame = requestAnimationFrame(syncAudioVisualizer);
        }

        currentAudio.onplay = () => {
            if (audioContext && audioContext.state === 'suspended') {
                audioContext.resume();
            }
            syncAudioVisualizer();
        };

        currentAudio.onended = () => {
            // Pasar de inmediato al siguiente fragmento sin pausas
            playNextAudioInQueue(fallbackText);
        };

        currentAudio.onerror = (e) => {
            console.error("Error al reproducir audio de la cola:", e);
            playNextAudioInQueue(fallbackText);
        };

        currentAudio.play().catch(err => {
            console.error("Error al iniciar audio:", err);
            playNextAudioInQueue(fallbackText);
        });

    } catch (err) {
        console.error("Error inicializando audio:", err);
        if (fallbackText) speakBrowserFallback(fallbackText);
    }
}

// Fallback a síntesis del navegador si no hay audio neuronal
function speakBrowserFallback(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-ES';
        utterance.pitch = 0.95;
        utterance.rate = 1.05;

        const voices = window.speechSynthesis.getVoices();
        const esVoice = voices.find(v => v.lang.startsWith('es'));
        if (esVoice) utterance.voice = esVoice;

        utterance.onstart = () => {
            if (typeof triggerPulse === 'function') triggerPulse(2.2);
        };
        utterance.onend = () => {
            if (typeof triggerPulse === 'function') triggerPulse(1.0);
        };

        window.speechSynthesis.speak(utterance);
    }
}

// Bucle de telemetría en tiempo real
async function startTelemetryLoop() {
    async function update() {
        if (isPywebviewReady && window.pywebview && window.pywebview.api) {
            try {
                const stats = await window.pywebview.api.get_system_stats();
                updateUIWithStats(stats);
            } catch (err) {
                console.error("Error al obtener telemetría:", err);
            }
        }
        setTimeout(update, 1500);
    }
    update();
}

function updateUIWithStats(stats) {
    if (!stats) return;

    // CPU
    if (cpuPercentEl && stats.cpu) {
        const cpuVal = stats.cpu.percent;
        cpuPercentEl.textContent = `${cpuVal.toFixed(1)}%`;
        if (cpuBarEl) cpuBarEl.style.width = `${Math.min(cpuVal, 100)}%`;
        if (cpuCoresEl) cpuCoresEl.textContent = `CPU (${stats.cpu.cores_logical} HILOS / ${stats.cpu.freq_current_mhz} MHz)`;
    }

    // RAM
    if (ramTextEl && stats.ram) {
        ramTextEl.textContent = `${stats.ram.used_gb} / ${stats.ram.total_gb} GB (${stats.ram.percent}%)`;
        if (ramBarEl) ramBarEl.style.width = `${stats.ram.percent}%`;
    }

    // DISCO
    if (diskTextEl && stats.disk) {
        diskTextEl.textContent = `${stats.disk.percent}% (${stats.disk.free_gb} GB libres)`;
        if (diskBarEl) diskBarEl.style.width = `${stats.disk.percent}%`;
    }

    // BATERÍA
    if (batteryTextEl && stats.battery) {
        if (stats.battery.present) {
            const state = stats.battery.plugged ? '⚡ Cargando' : '🔋 Batería';
            batteryTextEl.textContent = `${stats.battery.percent}% [${state}]`;
        } else {
            batteryTextEl.textContent = 'AC CONECTADO (ESTABLE)';
        }
    }

    // MEMORIA SEMÁNTICA VECTORIAL
    const memoryPillEl = document.getElementById('memory-pill');
    if (memoryPillEl && stats.memory_semantic) {
        const mem = stats.memory_semantic;
        memoryPillEl.textContent = `SEMÁNTICA (${mem.indexed_vectors || 0} VEC / 3072D)`;
        memoryPillEl.title = `Índice Semántico Activo: ${mem.total_items} recuerdos guardados, modelo ${mem.embedding_model}`;
    }

    // CONCIENCIA CONTEXTUAL EN VIVO
    const contextPillEl = document.getElementById('context-pill');
    if (contextPillEl && stats.context_live) {
        const ctx = stats.context_live;
        const moodUpper = (ctx.mood || 'estandar').toUpperCase();
        contextPillEl.textContent = `${moodUpper} // ${ctx.time_str}`;
        contextPillEl.title = `Situación: ${ctx.formatted_date} (${ctx.period}). Carga: ${ctx.load_status}. Presencia: ${ctx.presence_desc}`;
        
        // Estilos de color reactivos según el modo
        if (ctx.mood === 'alerta') {
            contextPillEl.className = 'text-red-400 font-mono font-bold animate-pulse';
        } else if (ctx.mood === 'nocturno') {
            contextPillEl.className = 'text-purple-300 font-mono';
        } else if (ctx.mood === 'calmo') {
            contextPillEl.className = 'text-emerald-300 font-mono';
        } else {
            contextPillEl.className = 'text-cyan-300 font-mono';
        }
    }
}

// Ejecutar comando de texto o pregunta a Aether
async function sendCommand() {
    if (!commandInputEl) return;
    const cmd = commandInputEl.value.trim();
    if (!cmd) return;

    commandInputEl.value = '';
    stopAllAudio(); // Corte inmediato de cualquier audio previo
    logHud(`ANALIZANDO DIRECTIVA: "${cmd}"...`);
    if (typeof triggerPulse === 'function') triggerPulse(2.0);

    if (isPywebviewReady && window.pywebview && window.pywebview.api) {
        try {
            const res = await window.pywebview.api.execute_command(cmd);
            logHud(res.message, true);
            if (typeof triggerPulse === 'function') {
                const pulseIntensity = res.mood === 'alerta' ? 3.0 : (res.mood === 'nocturno' ? 1.4 : 2.2);
                triggerPulse(pulseIntensity);
            }
            const audioToPlay = (res.chunks && res.chunks.length > 0) ? res.chunks : res.audio;
            if (audioToPlay) {
                playNeuralAudio(audioToPlay, res.message);
            } else {
                speakBrowserFallback(res.message);
            }
        } catch (err) {
            logHud(`ERROR EN EJECUCIÓN: ${err}`, false);
        }
    } else {
        const demo = `Modo demostración. Orden '${cmd}' recibida, señor.`;
        logHud(demo, true);
        speakBrowserFallback(demo);
    }
}

// Atajos rápidos de aplicaciones
async function triggerApp(appName) {
    stopAllAudio();
    if (isPywebviewReady && window.pywebview && window.pywebview.api) {
        try {
            const res = await window.pywebview.api.trigger_quick_app(appName);
            logHud(res.message, true);
            const audioToPlay = (res.chunks && res.chunks.length > 0) ? res.chunks : res.audio;
            if (audioToPlay) {
                playNeuralAudio(audioToPlay, res.message);
            }
        } catch (err) {
            logHud(`Error: ${err}`);
        }
    } else {
        logHud(`Lanzando ${appName}...`);
    }
}

// Diagnóstico profundo de hardware
async function triggerHardwareDiagnostics() {
    stopAllAudio();
    logHud("EJECUTANDO DIAGNÓSTICO PROFUNDO DE HARDWARE...");
    if (typeof triggerPulse === 'function') triggerPulse(2.5);

    if (isPywebviewReady && window.pywebview && window.pywebview.api) {
        try {
            const res = await window.pywebview.api.run_hardware_diagnostics();
            if (res && res.summary_text) {
                logHud(res.summary_text, true);
            }

            // Pulso visual según score de salud
            if (typeof triggerPulse === 'function') {
                const score = res && res.score !== undefined ? res.score : 100;
                triggerPulse(score < 75 ? 3.5 : 2.0);
            }

            const audioToPlay = (res && res.chunks && res.chunks.length > 0)
                ? res.chunks
                : (res && res.audio ? res.audio : null);
            if (audioToPlay) {
                playNeuralAudio(audioToPlay, res.summary_text || "Diagnóstico completado.");
            } else if (res && res.summary_text) {
                speakBrowserFallback(res.summary_text);
            }
        } catch (err) {
            logHud(`ERROR EN DIAGNÓSTICO: ${err}`, false);
            console.error("Error en diagnóstico de hardware:", err);
        }
    } else {
        logHud("SISTEMA NO DISPONIBLE — PYWEBVIEW AÚN NO CONECTADO");
    }
}

// Reconocimiento de voz (Speech Recognition)
function toggleVoiceListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        logHud("RECONOCIMIENTO DE VOZ NO SOPORTADO EN ESTE NAVEGADOR");
        return;
    }

    if (isListening) {
        speechRecognizer.stop();
        return;
    }

    speechRecognizer = new SpeechRecognition();
    speechRecognizer.lang = 'es-ES';
    speechRecognizer.interimResults = false;
    speechRecognizer.continuous = false;

    speechRecognizer.onstart = () => {
        isListening = true;
        if (micBtnEl) micBtnEl.classList.add('bg-cyan-400', 'text-black', 'shadow-[0_0_15px_#00f3ff]');
        logHud("ESCUCHANDO DIRECTIVA DE VOZ...");
        if (typeof triggerPulse === 'function') triggerPulse(2.0);
    };

    speechRecognizer.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (commandInputEl) commandInputEl.value = transcript;
        sendCommand();
    };

    speechRecognizer.onerror = (e) => {
        console.error("Error en reconocimiento de voz:", e);
        logHud("ERROR AL CAPTURAR VOZ");
    };

    speechRecognizer.onend = () => {
        isListening = false;
        if (micBtnEl) micBtnEl.classList.remove('bg-cyan-400', 'text-black', 'shadow-[0_0_15px_#00f3ff]');
    };

    speechRecognizer.start();
}

// Subsistema Éter Vision (Biometría y Rastreo Facial)
let isVisionActive = false;
let visionPollInterval = null;
let hasGreetedFace = false;

const visionLedEl = document.getElementById('vision-led');
const visionPillTextEl = document.getElementById('vision-pill-text');
const visionFeedEl = document.getElementById('vision-feed');
const visionPlaceholderEl = document.getElementById('vision-placeholder');
const visionFaceBadgeEl = document.getElementById('vision-face-badge');
const visionHudStatusEl = document.getElementById('vision-hud-status');

async function toggleVision() {
    if (!isPywebviewReady || !window.pywebview || !window.pywebview.api) {
        logHud("SISTEMA DE VISIÓN NO DISPONIBLE AÚN");
        return;
    }

    try {
        const res = await window.pywebview.api.toggle_vision();
        isVisionActive = res.active;
        updateVisionUIState(isVisionActive);

        if (isVisionActive) {
            logHud("ÉTER VISION ACTIVADA // ESCANEANDO ROSTRO...");
            if (typeof triggerPulse === 'function') triggerPulse(2.0);
            startVisionLoop();
        } else {
            logHud("ÉTER VISION SUSPENDIDA");
            stopVisionLoop();
        }
    } catch (err) {
        console.error("Error alternando visión:", err);
    }
}

function updateVisionUIState(active) {
    if (visionLedEl) {
        visionLedEl.className = active 
            ? "w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00f3ff] animate-pulse" 
            : "w-2 h-2 rounded-full bg-gray-500";
    }
    if (visionPillTextEl) {
        visionPillTextEl.textContent = active ? "ÉTER VISION: ACTIVA" : "ÉTER VISION: OFF";
        visionPillTextEl.className = active 
            ? "text-[11px] orbitron font-bold text-cyan-300" 
            : "text-[11px] orbitron font-bold text-gray-300";
    }
    if (visionPlaceholderEl && visionFeedEl) {
        if (active) {
            visionPlaceholderEl.classList.add('hidden');
            visionFeedEl.classList.remove('hidden');
        } else {
            visionPlaceholderEl.classList.remove('hidden');
            visionFeedEl.classList.add('hidden');
            if (visionFaceBadgeEl) {
                visionFaceBadgeEl.textContent = "OFF";
                visionFaceBadgeEl.className = "text-[9px] px-2 py-0.5 rounded bg-gray-900 border border-gray-700 text-gray-400 font-mono";
            }
            if (visionHudStatusEl) visionHudStatusEl.textContent = "BIOMETRÍA SUSPENDIDA";
            if (typeof setHeadTrackingOffset === 'function') setHeadTrackingOffset(0, 0);
        }
    }
}

function startVisionLoop() {
    if (visionPollInterval) clearInterval(visionPollInterval);

    visionPollInterval = setInterval(async () => {
        if (!isVisionActive || !window.pywebview || !window.pywebview.api) return;

        try {
            const telemetry = await window.pywebview.api.get_vision_telemetry();
            if (!telemetry) return;

            // Actualizar miniatura de video con bounding box
            if (telemetry.snapshot && visionFeedEl) {
                visionFeedEl.src = telemetry.snapshot;
            }

            // Actualizar textos e indicadores biométricos
            if (telemetry.face_detected) {
                if (visionFaceBadgeEl) {
                    visionFaceBadgeEl.textContent = "AUTORIZADO";
                    visionFaceBadgeEl.className = "text-[9px] px-2 py-0.5 rounded bg-cyan-950 border border-cyan-400 text-cyan-300 font-bold shadow-[0_0_8px_rgba(0,243,255,0.4)]";
                }
                if (visionHudStatusEl) {
                    visionHudStatusEl.textContent = telemetry.status_text;
                    visionHudStatusEl.className = "text-[10px] text-cyan-300 font-mono truncate text-center glow-text";
                }

                // Inclinación 3D del reactor hacia el rostro del usuario
                if (telemetry.head_pose && typeof setHeadTrackingOffset === 'function') {
                    setHeadTrackingOffset(telemetry.head_pose.cx, telemetry.head_pose.cy);
                }

                // Saludo por voz en la primera detección de presencia
                if (!hasGreetedFace) {
                    hasGreetedFace = true;
                    logHud("IDENTIDAD BIOMÉTRICA VERIFICADA // BIENVENIDO SEÑOR", true);
                    if (typeof triggerPulse === 'function') triggerPulse(2.8);
                }
            } else {
                if (visionFaceBadgeEl) {
                    visionFaceBadgeEl.textContent = "ESCANEANDO...";
                    visionFaceBadgeEl.className = "text-[9px] px-2 py-0.5 rounded bg-purple-950 border border-purple-500 text-purple-300 font-mono";
                }
                if (visionHudStatusEl) {
                    visionHudStatusEl.textContent = "ESCANEANDO ENTORNO...";
                    visionHudStatusEl.className = "text-[10px] text-gray-400 font-mono truncate text-center";
                }
                if (typeof setHeadTrackingOffset === 'function') {
                    setHeadTrackingOffset(0, 0);
                }
            }
        } catch (err) {
            console.error("Error en telemetría de visión:", err);
        }
    }, 120);
}

function stopVisionLoop() {
    if (visionPollInterval) {
        clearInterval(visionPollInterval);
        visionPollInterval = null;
    }
}

// Controles de ventana
function minimizeWindow() {
    if (isPywebviewReady && window.pywebview && window.pywebview.api) {
        window.pywebview.api.minimize_window();
    }
}

function toggleFullscreen() {
    if (isPywebviewReady && window.pywebview && window.pywebview.api) {
        window.pywebview.api.toggle_fullscreen();
    }
}

function closeWindow() {
    if (isPywebviewReady && window.pywebview && window.pywebview.api) {
        window.pywebview.api.close_app();
    }
}

// Inicialización de eventos al cargar el DOM
document.addEventListener('DOMContentLoaded', () => {
    initAetherUniverse();

    if (commandInputEl) {
        commandInputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendCommand();
        });
    }

    if ('speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = () => {
            window.speechSynthesis.getVoices();
        };
    }
});
