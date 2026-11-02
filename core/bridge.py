"""
Puente de Comunicación entre JavaScript (HUD) y Python (Aether Core).
Esta clase se expone directamente a la ventana de pywebview.
"""
import sys
from core.system_monitor import system_monitor as _global_monitor
from core.automation import AutomationEngine
from core.voice import AetherVoice
from core.vision import vision_engine
from core.memory import memory_manager
from core.context import context_engine
from core.memory_diagnostics import memory_diagnostics

class AetherBridge:
    def __init__(self, window_ref=None):
        self.window = window_ref
        self.monitor = _global_monitor  # Reutilizar instancia global (evita doble hilo GPU)
        self.automation = AutomationEngine()
        self.voice = AetherVoice()
        self.vision = vision_engine
        self.memory = memory_manager
        self.context = context_engine

    def set_window(self, window):
        """Asigna la referencia a la ventana de pywebview."""
        self.window = window

    def get_system_stats(self) -> dict:
        """Obtiene la telemetría en tiempo real de Windows, el estado de la memoria semántica y el contexto situacional."""
        stats = self.monitor.get_stats()
        stats["memory_semantic"] = self.memory.get_stats()
        stats["context_live"] = self.context.get_live_context_snapshot()
        return stats

    def search_memory(self, query: str) -> dict:
        """Permite consultar recuerdos semánticamente desde la interfaz."""
        results = self.memory.search_semantic(query, limit=5)
        return {"query": query, "results": results}

    def execute_command(self, command: str) -> dict:
        """
        Procesa una orden ingresada por el usuario (texto o voz),
        obtiene la respuesta contextual de Aether y genera el audio neuronal a través del
        pipeline concurrente optimizado para mínima latencia.
        """
        if not command or not command.strip():
            fallback_msg = "A la espera de sus órdenes, señor."
            v_res = self.voice.synthesize_pipelined(fallback_msg, mood="estandar")
            return {
                "status": "empty", 
                "message": fallback_msg, 
                "audio": v_res.get("audio", ""),
                "chunks": v_res.get("chunks", []),
                "mood": "estandar"
            }

        # 1. Obtener respuesta contextualizada del Cerebro LLM
        res = self.automation.process_natural_command(command)
        message = res.get("message", "")
        mood = res.get("mood", "estandar")

        # 2. Pipeline de síntesis concurrente por oraciones en paralelo
        v_res = self.voice.synthesize_pipelined(message, mood=mood)

        return {
            "status": res.get("status", "success"),
            "message": message,
            "audio": v_res.get("audio", ""),
            "chunks": v_res.get("chunks", []),
            "mood": mood,
            "latency_ms": v_res.get("elapsed_ms", 0)
        }

    def get_initial_briefing(self) -> dict:
        """
        Genera el saludo proactivo de bienvenida contextual de Aether al abrir la aplicación.
        """
        res = self.automation.get_briefing()
        message = res.get("message", "")
        mood = res.get("mood", "estandar")
        v_res = self.voice.synthesize_pipelined(message, mood=mood)
        return {
            "message": message,
            "audio": v_res.get("audio", ""),
            "chunks": v_res.get("chunks", []),
            "mood": mood
        }

    def trigger_quick_app(self, app_name: str) -> dict:
        """Acceso directo para abrir aplicaciones desde botones del HUD."""
        res = self.automation.open_app(app_name)
        message = res.get("message", "")
        mood = res.get("mood", "estandar")
        v_res = self.voice.synthesize_pipelined(message, mood=mood)
        return {
            "status": res.get("status", "success"),
            "message": message,
            "audio": v_res.get("audio", ""),
            "chunks": v_res.get("chunks", []),
            "mood": mood
        }

    def synthesize_speech(self, text: str, mood: str = "estandar") -> str:
        """Genera el audio en base64 para cualquier texto solicitado con modulación acústica."""
        return self.voice.synthesize(text, mood=mood)

    def run_hardware_diagnostics(self) -> dict:
        """Ejecuta el motor de diagnóstico holístico y retorna score, grado, anomalías y audio TTS."""
        from core.system_monitor import system_monitor
        diag = system_monitor.run_diagnostics()
        summary = diag.get("summary_text", "Diagnóstico completado.")
        score = diag.get("score", 100)
        # Elegir mood acústico según severidad
        if score < 50:
            mood = "alerta"
        elif score < 75:
            mood = "calmo"
        else:
            mood = "estandar"
        v_res = self.voice.synthesize_pipelined(summary, mood=mood)
        return {
            "score": score,
            "grade": diag.get("grade", ""),
            "anomalies": diag.get("anomalies", []),
            "recommendations": diag.get("recommendations", []),
            "summary_text": summary,
            "audio": v_res.get("audio", ""),
            "chunks": v_res.get("chunks", []),
            "mood": mood
        }

    def run_memory_diagnostics(self) -> dict:
        """Ejecuta el autodiagnóstico predictivo del índice semántico neuronal."""
        diag = memory_diagnostics.run_health_check()
        summary = diag.get("summary_text", "")
        v_res = self.voice.synthesize_pipelined(summary, mood="estandar")
        return {
            "health_score": diag.get("health_score"),
            "status": diag.get("status"),
            "confusion_risk": diag.get("confusion_risk"),
            "fragmentation_index": diag.get("fragmentation_index"),
            "recommendations": diag.get("recommendations"),
            "summary_text": summary,
            "audio": v_res.get("audio", ""),
            "chunks": v_res.get("chunks", [])
        }

    def get_top_processes(self, sort_by: str = "ram", count: int = 5) -> list:
        """Retorna los procesos con mayor consumo de RAM o CPU desde el monitor global."""
        from core.system_monitor import system_monitor
        return system_monitor.get_top_processes(sort_by=sort_by, count=count)

    def toggle_fullscreen(self) -> bool:
        """Alterna el modo de pantalla completa."""
        if self.window:
            self.window.toggle_fullscreen()
            return True
        return False

    def minimize_window(self) -> bool:
        """Minimiza la ventana de la aplicación."""
        if self.window:
            self.window.minimize()
            return True
        return False

    def toggle_vision(self) -> dict:
        """Inicia o detiene el subsistema de visión biométrica por cámara web."""
        if self.vision.is_running:
            self.vision.stop()
            return {"active": False, "message": "Visión biométrica desactivada."}
        else:
            started = self.vision.start()
            return {"active": started, "message": "Visión biométrica iniciada." if started else "Fallo al acceder a la cámara."}

    def get_vision_telemetry(self) -> dict:
        """Devuelve el estado en tiempo real de la detección de rostro y pose."""
        return self.vision.get_status()

    def close_app(self) -> None:
        """Cierra la aplicación de escritorio de forma segura."""
        self.vision.stop()
        if self.window:
            self.window.destroy()
        sys.exit(0)
