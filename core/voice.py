"""
Módulo de Voz Neuronal de Alta Fidelidad y Prosodia Adaptativa para AETHER.
Optimizado con pipeline de síntesis paralela concurrente por oraciones (asyncio.gather),
bucle asíncrono persistente en hilo dedicado, desinfección fonética avanzada y
caché multi-nivel (RAM LRU + disco persistente) para mínima latencia.
"""
import os
import re
import time
import base64
import hashlib
import asyncio
import threading
from pathlib import Path
from collections import OrderedDict
from typing import Optional, Dict, List, Tuple, Any
import edge_tts

# Directorio de caché persistente de audio
AUDIO_CACHE_DIR = Path(__file__).parent / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VOICE = "es-ES-AlvaroNeural"

# Perfiles de modulación acústica con velocidad optimizada para reducir tiempo de elocución
VOICE_MODULATION_PROFILES = {
    "estandar": {"rate": "+3%", "pitch": "-2Hz", "volume": "+0%"},
    "nocturno": {"rate": "-1%", "pitch": "-3Hz", "volume": "-8%"},
    "alerta": {"rate": "+5%", "pitch": "+0Hz", "volume": "+5%"},
    "calmo": {"rate": "+1%", "pitch": "-2Hz", "volume": "-3%"}
}


class SpeechSanitizer:
    """
    Desinfector y Optimizador Fonético para Síntesis Neuronal.
    Transforma texto generado por LLM en lenguaje natural fluido y acústicamente impecable,
    eliminando artefactos de markdown, emojis, código y pronunciando acrónimos técnicos con claridad.
    """
    PHONETIC_REPLACEMENTS = [
        (r'\bFastAPI\b', 'Fast A P I'),
        (r'\bThree\.js\b', 'Three J S'),
        (r'\bpywebview\b', 'py webview'),
        (r'\bYuNet\b', 'Yu Net'),
        (r'\bOpenCV\b', 'Open C V'),
        (r'\bCPU\b', 'C P U'),
        (r'\bRAM\b', 'R A M'),
        (r'\bLLM\b', 'L L M'),
        (r'\bTTS\b', 'T T S'),
        (r'\bHUD\b', 'H U D'),
        (r'\bVS Code\b', 'Visual Studio Code'),
        (r'\bGB\b', 'gigabytes'),
        (r'\bMB\b', 'megabytes'),
        (r'\bGHz\b', 'gigahercios'),
        (r'\bMHz\b', 'megahercios'),
        (r'(\d+)\s*%', r'\1 por ciento'),
        (r'%', ' por ciento'),
    ]

    @classmethod
    def clean_for_speech(cls, text: str) -> str:
        """Limpia y prepara el texto para una entonación natural al ser leído por edge-tts."""
        if not text:
            return ""

        s = text

        # 1. Eliminar bloques de código markdown ```...```
        s = re.sub(r'```[\s\S]*?```', '', s)

        # 2. Eliminar código inline `codigo`
        s = re.sub(r'`([^`]+)`', r'\1', s)

        # 3. Eliminar enlaces markdown [texto](url) -> texto
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)

        # 4. Eliminar etiquetas de arquitectura o tags entre corchetes [TAG]
        s = re.sub(r'\[[A-Za-z0-9_\s\-\.]+\]:?', '', s)

        # 5. Eliminar viñetas, guiones y numeraciones de listas al inicio de línea
        s = re.sub(r'^[#*•\-\+]\s+', '', s, flags=re.MULTILINE)
        s = re.sub(r'^\d+\.\s+', '', s, flags=re.MULTILINE)

        # 6. Reemplazar énfasis de markdown **negrita** o *cursiva*
        s = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', s)
        s = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', s)

        # 7. Eliminar URLs directas http:// o https://
        s = re.sub(r'https?://\S+', '', s)

        # 8. Eliminar emojis y símbolos decorativos Unicode
        emoji_pattern = re.compile(
            r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2b50\u200d]',
            flags=re.UNICODE
        )
        s = emoji_pattern.sub('', s)

        # 9. Aplicar reemplazos fonéticos de acrónimos técnicos
        for pattern, replacement in cls.PHONETIC_REPLACEMENTS:
            s = re.sub(pattern, replacement, s)

        # 10. Normalizar puntuación y espacios
        s = re.sub(r'[ \t]+', ' ', s)
        s = re.sub(r'\n{2,}', '. ', s)
        s = s.replace('\n', ' ')
        s = re.sub(r'\s+([,.:;?!])', r'\1', s)
        s = re.sub(r'([,.:;?!]){2,}', r'\1', s)

        return s.strip()

    @classmethod
    def split_into_speech_sentences(cls, text: str) -> List[str]:
        """
        Divide el texto limpio en unidades oracionales balanceadas para síntesis concurrente.
        Evita fragmentos diminutos (< 15 caracteres) fusionándolos con la oración adyacente.
        """
        clean = cls.clean_for_speech(text)
        if not clean:
            return []

        # Separar por signos de puntuación de cierre seguidos de espacio
        raw_parts = re.split(r'(?<=[.!?])\s+', clean)
        parts = [p.strip() for p in raw_parts if p.strip()]

        if len(parts) <= 1:
            return [clean]

        merged = []
        buffer = ""
        for p in parts:
            if buffer:
                buffer += " " + p
                if len(buffer) >= 20:
                    merged.append(buffer)
                    buffer = ""
            else:
                if len(p) < 15 and len(parts) > 1:
                    buffer = p
                else:
                    merged.append(p)

        if buffer:
            if merged:
                merged[-1] += " " + buffer
            else:
                merged.append(buffer)

        return merged if merged else [clean]


class _AsyncVoiceWorker:
    """Hilo trabajador persistente con un bucle de eventos asyncio para evitar recrear loops."""
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, name="AetherVoiceWorker", daemon=True)
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, timeout: float = 4.5):
        """Ejecuta una corrutina en el bucle persistente con límite estricto de tiempo."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)


class AetherVoice:
    """
    Motor Central de Voz Neuronal de AETHER con Pipeline Concurrente de Baja Latencia.
    Genera audio MP3 ultra-realista con prosodia contextual, paralelización de oraciones
    y caché multi-nivel (RAM LRU + disco).
    """
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice
        self.worker = _AsyncVoiceWorker()
        
        # Caché LRU en memoria (hasta 150 respuestas frecuentes para recuperación en < 1ms)
        self._ram_cache: OrderedDict[str, str] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._max_ram_cache = 150

        # Precargar frases del sistema comunes en caché
        self._prewarm_common_phrases()

    def _compute_cache_key(self, text: str, rate: str, pitch: str) -> str:
        """Genera un hash determinista para indexar el audio en caché."""
        raw = f"{self.voice}_{rate}_{pitch}_{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Busca el audio en RAM primero y luego en disco."""
        with self._cache_lock:
            # 1. Comprobar RAM
            if key in self._ram_cache:
                self._ram_cache.move_to_end(key)
                return self._ram_cache[key]

        # 2. Comprobar Disco
        disk_path = AUDIO_CACHE_DIR / f"{key}.b64"
        if disk_path.exists():
            try:
                with open(disk_path, "r", encoding="utf-8") as f:
                    data_uri = f.read().strip()
                if data_uri:
                    with self._cache_lock:
                        self._put_in_ram_cache(key, data_uri)
                    return data_uri
            except Exception:
                pass

        return None

    def _put_in_ram_cache(self, key: str, data_uri: str):
        """Almacena en RAM aplicando política LRU."""
        if len(self._ram_cache) >= self._max_ram_cache:
            self._ram_cache.popitem(last=False)
        self._ram_cache[key] = data_uri

    def _save_to_cache(self, key: str, data_uri: str):
        """Guarda el audio en RAM y en el disco persistente."""
        with self._cache_lock:
            self._put_in_ram_cache(key, data_uri)

        disk_path = AUDIO_CACHE_DIR / f"{key}.b64"
        try:
            with open(disk_path, "w", encoding="utf-8") as f:
                f.write(data_uri)
        except Exception:
            pass

    async def _synth_single_sentence_async(self, sentence: str, rate: str, pitch: str, volume: str) -> bytes:
        """Sintetiza una sola oración consultando caché y comunicando con edge-tts si es necesario."""
        key = self._compute_cache_key(sentence, rate, pitch)
        cached_uri = self._get_from_cache(key)
        if cached_uri and cached_uri.startswith("data:audio/mp3;base64,"):
            try:
                return base64.b64decode(cached_uri.split(",", 1)[1])
            except Exception:
                pass

        communicate = edge_tts.Communicate(
            text=sentence,
            voice=self.voice,
            rate=rate,
            pitch=pitch,
            volume=volume
        )
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        raw_bytes = b"".join(chunks)
        if raw_bytes:
            b64_uri = f"data:audio/mp3;base64,{base64.b64encode(raw_bytes).decode('utf-8')}"
            self._save_to_cache(key, b64_uri)

        return raw_bytes

    async def _synthesize_parallel_async(
        self,
        sentences: List[str],
        rate: str,
        pitch: str,
        volume: str
    ) -> Tuple[str, List[str]]:
        """
        Ejecuta la síntesis de múltiples oraciones de manera concurrente (asyncio.gather).
        Devuelve (audio_unificado_b64, lista_chunks_b64).
        """
        if not sentences:
            return "", []

        tasks = [self._synth_single_sentence_async(s, rate, pitch, volume) for s in sentences]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_raw = []
        chunks_b64 = []

        for r in results:
            if isinstance(r, bytes) and len(r) > 0:
                valid_raw.append(r)
                chunks_b64.append(f"data:audio/mp3;base64,{base64.b64encode(r).decode('utf-8')}")
            elif isinstance(r, Exception):
                print(f"[AETHER VOICE] Error en síntesis de fragmento concurrente: {r}")

        if not valid_raw:
            return "", []

        # Los frames MP3 puros de edge-tts se concatenan directamente sin pérdidas
        combined_bytes = b"".join(valid_raw)
        combined_b64 = f"data:audio/mp3;base64,{base64.b64encode(combined_bytes).decode('utf-8')}"
        return combined_b64, chunks_b64

    def synthesize_pipelined(self, text: str, mood: str = "estandar") -> Dict[str, Any]:
        """
        Pipeline principal optimizado para mínima latencia.
        Divide el texto en oraciones, procesa concurrentemente con asyncio.gather,
        concatena audio en memoria y devuelve tanto el audio unificado como los chunks.
        """
        if not text or not text.strip():
            return {"audio": "", "chunks": [], "sentences": [], "elapsed_ms": 0}

        t0 = time.time()
        clean_text = SpeechSanitizer.clean_for_speech(text)
        if not clean_text:
            return {"audio": "", "chunks": [], "sentences": [], "elapsed_ms": 0}

        profile = VOICE_MODULATION_PROFILES.get(mood.lower(), VOICE_MODULATION_PROFILES["estandar"])
        rate = profile["rate"]
        pitch = profile["pitch"]
        volume = profile["volume"]

        # 1. Comprobar caché global completa
        overall_key = self._compute_cache_key(clean_text, rate, pitch)
        cached_overall = self._get_from_cache(overall_key)
        if cached_overall:
            elapsed = round((time.time() - t0) * 1000, 2)
            return {
                "audio": cached_overall,
                "chunks": [cached_overall],
                "sentences": [clean_text],
                "elapsed_ms": elapsed
            }

        # 2. Dividir en oraciones para paralelización
        sentences = SpeechSanitizer.split_into_speech_sentences(clean_text)

        # 3. Síntesis concurrente en el trabajador asíncrono
        try:
            combined_b64, chunks_b64 = self.worker.run(
                self._synthesize_parallel_async(sentences, rate, pitch, volume),
                timeout=4.5
            )
            elapsed = round((time.time() - t0) * 1000, 1)

            if combined_b64:
                self._save_to_cache(overall_key, combined_b64)
                print(f"[AETHER VOICE PIPELINE] Sintetizado en {elapsed} ms ({len(sentences)} oraciones concurrentes, modo: {mood})")
                return {
                    "audio": combined_b64,
                    "chunks": chunks_b64,
                    "sentences": sentences,
                    "elapsed_ms": elapsed
                }

        except Exception as e:
            print(f"[AETHER VOICE PIPELINE] Fluctuación en síntesis concurrente: {e}. Activando fallback.")

        return {"audio": "", "chunks": [], "sentences": sentences, "elapsed_ms": 0}

    def synthesize(self, text: str, mood: str = "estandar") -> str:
        """Método estándar compatible que devuelve directamente la data URI del audio completo."""
        res = self.synthesize_pipelined(text, mood=mood)
        return res["audio"]

    def _prewarm_common_phrases(self):
        """Precarga en segundo plano las frases operativas frecuentes para latencia 0 ms."""
        common = [
            "Afirmativo, señor.",
            "Entendido, señor.",
            "A su disposición, señor.",
            "A la espera de sus órdenes, señor.",
            "A la espera de sus directivas, señor.",
            "Sistemas Aether sincronizados y operativos, señor.",
            "Iniciando de inmediato, señor.",
            "Directiva procesada con éxito, señor.",
            "Estación de trabajo bloqueada con éxito.",
            "Todas las ventanas minimizadas. Escritorio despejado.",
            "Panel de configuración de Windows abierto.",
            "Visión biométrica iniciada. Escaneando entorno en busca del señor.",
            "Cámara y subsistema de visión biométrica suspendidos por privacidad.",
            "Identidad biométrica verificada. Bienvenido señor.",
            "Memoria a corto plazo reinicializada. Contexto y memoria permanente conservados, señor.",
            "Buenas noches, señor.",
            "Buenos días, señor.",
            "Buenas tardes, señor."
        ]

        def _worker_prewarm():
            time.sleep(1.0)
            for phrase in common:
                clean = SpeechSanitizer.clean_for_speech(phrase)
                profile = VOICE_MODULATION_PROFILES["estandar"]
                key = self._compute_cache_key(clean, profile["rate"], profile["pitch"])
                if not self._get_from_cache(key):
                    try:
                        self.synthesize(phrase, mood="estandar")
                    except Exception:
                        pass

        threading.Thread(target=_worker_prewarm, name="AetherPrewarmThread", daemon=True).start()

# Instancia global del sintetizador de voz neuronal optimizado
voice_engine = AetherVoice()
