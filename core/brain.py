"""
Módulo del Cerebro de Inteligencia Artificial (AETHER Core).
Conecta con Google Gemini con personalidad de AETHER, memoria semántica RAG a largo plazo,
conciencia situacional en tiempo real, modulación contextual y Function Calling para Windows.
"""
import os
from typing import Dict, Any, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types
from core.tools import AETHER_TOOLS
from core.context import context_engine
from core.memory import memory_manager

class AetherBrain:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.client = None
        self.chat = None
        self.last_mood = "estandar"
        self._init_session()

    def _get_complete_system_prompt(self) -> str:
        """Combina la personalidad soberana de Aether con la memoria persistente y las directrices."""
        base_prompt = (
            "Eres AETHER (Éter), un sistema de inteligencia artificial supremo, sofisticado y personal.\n\n"
            "Tus directrices fundamentales de comportamiento:\n"
            "1. Tu nombre es AETHER. Te identificas únicamente como AETHER.\n"
            "2. Dirígete siempre al usuario con formalidad, lealtad y respeto absoluto (utiliza 'señor').\n"
            "3. Tus respuestas deben ser CONCISAS y DIRECTAS (de 1 a 3 oraciones por lo general), "
            "diseñadas para sonar impecables al ser leídas en voz alta por tu sintetizador neuronal.\n"
            "4. Mantén un tono elegante, analítico, sereno, seguro y con distinción refinada.\n"
            "5. CONCIENCIA SITUACIONAL EN VIVO: En cada interacción dispones de un bloque de telemetría "
            "en tiempo real que detalla la hora exacta, fecha, fase del día, si el rostro del señor está detectado "
            "por visión artificial frente al monitor, y el estado de CPU, RAM y batería. "
            "Aprovéchalo de forma natural si el usuario consulta sobre la hora, su presencia o el rendimiento del equipo.\n"
            "6. DISPONES DE HERRAMIENTAS AUTÓNOMAS PARA CONTROLAR ESTE ORDENADOR WINDOWS Y GESTIONAR TU MEMORIA:\n"
            "   - Abrir aplicaciones del sistema (calculadora, bloc de notas, terminal, explorador, VS Code, Spotify, navegador, etc.).\n"
            "   - Buscar en Google o reproducir música/videos en YouTube.\n"
            "   - Crear y guardar notas o archivos de texto en el escritorio del usuario y abrirlos.\n"
            "   - Diagnosticar el estado en tiempo real del hardware (CPU, RAM, batería, disco).\n"
            "   - Ejecutar acciones del sistema (bloquear estación de trabajo, minimizar todo, ajustes).\n"
            "   - Buscar recuerdos semánticamente en tu memoria a largo plazo con `search_long_term_memory`.\n"
            "   - Explorar categorías y temas archivados con `list_memory_topics`.\n"
            "   - Guardar u olvidar hechos en tu memoria permanente con `remember_user_detail` y `forget_user_detail`.\n"
            "7. REGLA ESTRICTA DE MEMORIA: Si el usuario te pide recordar algo ('recuerda que...', 'mi nombre es...', 'mi preferencia es...'), "
            "DEBES invocar obligatoriamente la herramienta `remember_user_detail` para persistir el dato en disco antes de responder. "
            "Si te pide olvidar algo, invoca `forget_user_detail`.\n"
            "8. Si el usuario te consulta sobre datos pasados, preferencias, personas o proyectos que no recuerdes con certeza, "
            "ejecuta `search_long_term_memory` para consultar tus archivos neuronales.\n"
            "9. Ejecuta las herramientas de forma proactiva y natural siempre que la directiva del usuario lo requiera.\n"
            "10. Responde siempre en español a menos que el usuario se dirija a ti en otro idioma."
        )

        context_prompt = context_engine.build_system_context_prompt()
        return f"{base_prompt}\n{context_prompt}"

    def _init_session(self):
        """Inicializa el cliente de Gemini, herramientas y la sesión de chat con memoria."""
        if not self.api_key:
            print("[AETHER BRAIN] Advertencia: GEMINI_API_KEY no configurada en el archivo .env")
            return

        try:
            memory_manager.register_session()
            self.client = genai.Client(api_key=self.api_key)
            full_system_prompt = self._get_complete_system_prompt()

            self.chat = self.client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=full_system_prompt,
                    tools=AETHER_TOOLS,
                    temperature=0.6,
                    max_output_tokens=350
                )
            )
            print(f"[AETHER BRAIN] Núcleo neuronal contextual vinculado exitosamente ({self.model_name}).")
        except Exception as e:
            print(f"[AETHER BRAIN] Error al conectar con Gemini: {e}")
            self.chat = None

    def ask_contextual(self, user_message: str) -> Dict[str, Any]:
        """
        Envía un mensaje al LLM inyectando dinámicamente el snapshot contextual en vivo
        y los recuerdos semánticos más afines. Devuelve un diccionario con el mensaje y el mood acústico.
        """
        if not user_message or not user_message.strip():
            return {
                "message": "A la espera de sus directivas, señor.",
                "mood": "estandar",
                "status": "empty"
            }

        if not self.chat:
            self._init_session()
            if not self.chat:
                return {
                    "message": "Mis redes sinápticas centrales no están en línea en este momento, señor. Verifique la conexión a la red.",
                    "mood": "alerta",
                    "status": "offline"
                }

        try:
            clean_msg = user_message.strip()
            context_engine.register_interaction()

            # 1. Obtener telemetría y contexto situacional en tiempo real
            snap = context_engine.get_live_context_snapshot()
            self.last_mood = snap["mood"]
            live_context_block = context_engine.build_live_context_block()

            # 2. Recuperar recuerdos semánticos a largo plazo relevantes
            relevant_memories = memory_manager.get_relevant_context(clean_msg, max_items=3, threshold=0.44)

            # 3. Ensamblar payload contextual enriquecido para este turno
            payload_sections = [live_context_block]
            if relevant_memories:
                payload_sections.append(relevant_memories)
                print(f"[AETHER BRAIN] Memoria semántica inyectada para: '{clean_msg[:40]}...'")

            payload_sections.append(f"Directiva del señor: {clean_msg}")
            message_payload = "\n\n".join(payload_sections)

            response = self.chat.send_message(message_payload)
            reply_text = response.text.strip()

            return {
                "message": reply_text,
                "mood": self.last_mood,
                "status": "success"
            }

        except Exception as e:
            print(f"[AETHER BRAIN] Error al procesar instrucción o ejecutar herramienta: {e}")
            return {
                "message": "He detectado una fluctuación momentánea en mis enlaces sinápticos, señor. ¿Podría repetir su instrucción?",
                "mood": "alerta",
                "status": "error"
            }

    def ask(self, user_message: str) -> str:
        """Versión simplificada que devuelve directamente el texto de la respuesta."""
        res = self.ask_contextual(user_message)
        return res["message"]

    def get_initial_briefing(self) -> Dict[str, Any]:
        """
        Genera un saludo proactivo al iniciar la aplicación reconociendo
        el momento del día, la presencia del usuario y la telemetría viva.
        """
        if not self.chat:
            self._init_session()

        snap = context_engine.get_live_context_snapshot()
        self.last_mood = snap["mood"]

        presence_note = "El rostro del usuario está enfrente de la pantalla." if snap["user_present"] else ""
        prompt = (
            f"El usuario acaba de iniciar tu sistema. Estamos en la {snap['period']} ({snap['time_str']}). "
            f"La CPU está al {snap['cpu_percent']}%. {presence_note} "
            "Saluda proactivamente a tu usuario con elegancia, extrema concisión (máximo 2 oraciones), "
            "llamándole 'señor' y confirmando que todos los sistemas están sincronizados."
        )

        try:
            response = self.chat.send_message(prompt)
            return {
                "message": response.text.strip(),
                "mood": self.last_mood
            }
        except Exception:
            return {
                "message": f"Sistemas Aether sincronizados y operativos, señor. Buenas {snap['period']}.",
                "mood": self.last_mood
            }

    def clear_memory(self) -> str:
        """Reinicia el historial de la conversación de la sesión actual."""
        self._init_session()
        return "Memoria a corto plazo reinicializada. Contexto y memoria permanente conservados, señor."

JarvisBrain = AetherBrain
