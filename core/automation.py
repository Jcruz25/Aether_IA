"""
Módulo de Automatización del Sistema y Coordinación con el Cerebro de AETHER.
Combina atajos directos para botones del HUD con la autonomía completa de Gemini Function Calling.
"""
import os
import subprocess
import webbrowser
import platform
from core.brain import AetherBrain

class AutomationEngine:
    def __init__(self):
        self.os_type = platform.system()
        self.brain = AetherBrain()

    def open_app(self, app_key: str) -> dict:
        """Abre aplicaciones estándar del sistema para los botones rápidos del HUD."""
        app_key = app_key.lower().strip()

        commands = {
            "notepad": ["notepad.exe"],
            "bloc de notas": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "calculadora": ["calc.exe"],
            "terminal": ["powershell.exe"],
            "cmd": ["cmd.exe"],
            "explorer": ["explorer.exe"],
            "archivos": ["explorer.exe"],
            "code": ["code"],
            "vscode": ["code"],
            "taskmgr": ["taskmgr.exe"],
            "administrador de tareas": ["taskmgr.exe"],
        }

        if app_key in commands:
            cmd = commands[app_key]
            try:
                subprocess.Popen(cmd, shell=True)
                return {"status": "success", "message": f"Iniciando {app_key} de inmediato, señor.", "mood": "estandar"}
            except Exception as e:
                return {"status": "error", "message": f"Dificultades al abrir {app_key}: {str(e)}", "mood": "alerta"}

        return {"status": "not_found", "message": f"La aplicación '{app_key}' no se encuentra en el registro rápido, señor.", "mood": "estandar"}

    def process_natural_command(self, text: str) -> dict:
        """
        Envía la directiva directamente al Cerebro de AETHER,
        el cual utiliza Function Calling para decidir y ejecutar herramientas en Windows,
        incorporando conciencia situacional y memoria semántica en tiempo real.
        """
        cmd = text.lower().strip()

        # Comando especial para limpiar memoria de conversación
        if cmd in ["reiniciar memoria", "olvida lo anterior", "nueva conversacion", "limpiar memoria"]:
            return {
                "status": "success",
                "message": self.brain.clear_memory(),
                "mood": "calmo"
            }

        # Toda orden o consulta pasa por el cerebro contextual
        res = self.brain.ask_contextual(text)
        return {
            "status": "ai_response",
            "message": res["message"],
            "mood": res.get("mood", "estandar")
        }

    def get_briefing(self) -> dict:
        """Genera el saludo inicial contextual con matiz acústico de Aether."""
        return self.brain.get_initial_briefing()
