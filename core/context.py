"""
Módulo de Conciencia Contextual Dinámica y Proactividad de AETHER.
Calcula en tiempo real la situación temporal, telemetría de hardware, biometría visual,
estado de energía y estado anímico contextual para modular respuestas y voz neuronal.
"""
import time
import datetime
import psutil
from typing import Dict, Any
from core.memory import memory_manager
from core.vision import vision_engine

class ContextEngine:
    def __init__(self):
        self.memory = memory_manager
        self.vision = vision_engine
        self.session_start = time.time()
        self.interaction_count = 0
        self.last_interaction_time = time.time()

    def get_time_period(self, hour: int) -> str:
        """Determina el período del día en lenguaje natural refinado."""
        if 0 <= hour < 6:
            return "madrugada"
        elif 6 <= hour < 12:
            return "mañana"
        elif 12 <= hour < 15:
            return "mediodía"
        elif 15 <= hour < 20:
            return "tarde"
        else:
            return "noche"

    def get_system_load_status(self, cpu_pct: float, ram_pct: float) -> str:
        """Clasifica cualitativamente la carga de trabajo del ordenador."""
        if cpu_pct > 85 or ram_pct > 90:
            return "crítico"
        elif cpu_pct > 65 or ram_pct > 80:
            return "elevado"
        elif cpu_pct > 35:
            return "moderado"
        return "óptimo"

    def get_live_context_snapshot(self) -> Dict[str, Any]:
        """
        Genera un snapshot integral en tiempo real de la situación del usuario,
        del entorno temporal, hardware de Windows y visión biométrica.
        """
        now = datetime.datetime.now()
        period = self.get_time_period(now.hour)

        # 1. Telemetría de hardware en tiempo real
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_used_gb = round((mem.total - mem.available) / (1024 ** 3), 1)
        ram_total_gb = round(mem.total / (1024 ** 3), 1)
        load_status = self.get_system_load_status(cpu_pct, ram_pct)

        # 2. Telemetría de batería / energía
        battery_info = {"present": False, "percent": 100, "plugged": True, "critical": False}
        try:
            bat = psutil.sensors_battery()
            if bat:
                is_crit = (bat.percent < 18 and not bat.power_plugged)
                battery_info = {
                    "present": True,
                    "percent": round(bat.percent, 1),
                    "plugged": bat.power_plugged,
                    "critical": is_crit
                }
        except Exception:
            pass

        # 3. Telemetría de biometría visual
        vision_status = self.vision.get_status()
        user_present = vision_status.get("face_detected", False)
        vision_active = vision_status.get("active", False)

        if vision_active and user_present:
            presence_desc = "Rostro del señor verificado frente a la pantalla (Biometría activa)"
            presence_tag = "presente"
        elif vision_active and not user_present:
            presence_desc = "Cámara activa: el señor no está en el encuadre en este momento"
            presence_tag = "ausente"
        else:
            presence_desc = "Sensor biométrico suspendido por privacidad"
            presence_tag = "privacidad"

        # 4. Cálculo de tiempo y sesión
        session_mins = int((time.time() - self.session_start) / 60)
        is_late_night = (now.hour >= 23 or now.hour < 6)

        # 5. Determinación del matiz contextual (mood) para respuestas y voz
        if battery_info["critical"] or load_status == "crítico":
            mood = "alerta"
            mood_desc = "Tono vigilante, conciso y de alta prioridad"
        elif is_late_night:
            mood = "nocturno"
            mood_desc = "Tono sereno, pausado, distinguido y cómplice de madrugada"
        elif user_present:
            mood = "calmo"
            mood_desc = "Tono atento, elegante y directamente enfocado al señor"
        else:
            mood = "estandar"
            mood_desc = "Tono formal, distinguido y eficiente"

        dias_es = {
            "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
            "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
        }
        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        dia_nom = dias_es.get(now.strftime("%A"), now.strftime("%A"))
        fecha_humana = f"{dia_nom}, {now.day} de {meses_es.get(now.month, '')} de {now.year}"

        return {
            "timestamp": time.time(),
            "datetime_str": now.strftime("%Y-%m-%d %H:%M:%S"),
            "hour": now.hour,
            "minute": now.minute,
            "period": period,
            "is_late_night": is_late_night,
            "formatted_date": fecha_humana,
            "time_str": f"{now.hour:02d}:{now.minute:02d}",
            "session_minutes": session_mins,
            "cpu_percent": cpu_pct,
            "ram_percent": ram_pct,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "load_status": load_status,
            "battery": battery_info,
            "presence_tag": presence_tag,
            "presence_desc": presence_desc,
            "user_present": user_present,
            "vision_active": vision_active,
            "mood": mood,
            "mood_desc": mood_desc
        }

    def build_live_context_block(self) -> str:
        """
        Construye el bloque de contexto situacional en tiempo real que se inyecta
        de forma dinámica en cada turno de consulta de Gemini.
        """
        snap = self.get_live_context_snapshot()

        # Resumen de energía
        if snap["battery"]["present"]:
            estado_bat = "Cargando (AC)" if snap["battery"]["plugged"] else "En Batería"
            energia_str = f"Batería al {snap['battery']['percent']}% ({estado_bat})"
        else:
            energia_str = "Conectado a la red eléctrica (AC continuo)"

        lines = [
            "[CONTEXTO SITUACIONAL EN TIEMPO REAL]:",
            f"• Momento actual: {snap['formatted_date']} a las {snap['time_str']} ({snap['period'].capitalize()}).",
            f"• Sesión: {snap['session_minutes']} minutos en línea.",
            f"• Presencia: {snap['presence_desc']}.",
            f"• Hardware: CPU {snap['cpu_percent']}% ({snap['load_status'].capitalize()}) | RAM {snap['ram_percent']}% ({snap['ram_used_gb']}/{snap['ram_total_gb']} GB) | {energia_str}.",
            f"• Matiz de voz y respuesta: {snap['mood_desc']}."
        ]
        return "\n".join(lines)

    def build_system_context_prompt(self) -> str:
        """
        Construye el ancla estática inicial para el System Instruction con la memoria
        del usuario y la arquitectura de Aether.
        """
        snap = self.get_live_context_snapshot()
        return (
            f"\n--- IDENTIDAD CONTEXTUAL INICIAL ---\n"
            f"Momento de inicio: {snap['formatted_date']}, {snap['time_str']}.\n"
            f"--- ARCHIVOS DE MEMORIA A LARGO PLAZO ---\n"
            f"{self.memory.get_context_summary()}\n"
            f"----------------------------------------\n"
        )

    def register_interaction(self):
        """Registra una nueva interacción para métricas temporales de respuesta."""
        self.interaction_count += 1
        self.last_interaction_time = time.time()

# Instancia global del motor contextual
context_engine = ContextEngine()
