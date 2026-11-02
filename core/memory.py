"""
Módulo de Memoria Persistente a Largo Plazo de AETHER con Indexación Semántica Avanzada.
Almacena datos del perfil del usuario, preferencias, proyectos y hechos aprendidos en disco,
integrando un motor vectorial de alta dimensión y búsqueda híbrida neuronal.
"""
import os
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.semantic_memory import semantic_memory_engine, SemanticMemoryItem
from core.crypto import aether_crypto

MEMORY_FILE = Path(__file__).parent / "memory.json"

DEFAULT_MEMORY = {
    "user_profile": {
        "title": "señor",
        "name": "Jose",
        "preferred_name": "Señor",
        "role": "Creador y Comandante de Aether IA"
    },
    "preferences": {
        "work_style": "desarrollo de software y tecnología avanzada",
        "music_genre": "música ambiental y synthwave",
        "concise_responses": True
    },
    "facts": [
        {"topic": "proyecto_principal", "detail": "Desarrollo del asistente de escritorio holográfico Aether IA", "updated": "2026-10-20"},
        {"topic": "stack_tecnologico", "detail": "Python, Three.js, pywebview, TailwindCSS y modelos de lenguaje de última generación", "updated": "2026-10-20"}
    ],
    "system_insights": {
        "sessions_count": 0,
        "last_session": "",
        "semantic_index_version": "2.0"
    }
}

class MemoryManager:
    def __init__(self, file_path=MEMORY_FILE):
        self.file_path = file_path
        self.semantic_engine = semantic_memory_engine
        self.data = self._load()

    def _save(self, data: dict = None):
        """Guarda los datos en el archivo JSON con cifrado de Éter Shield."""
        if data is None:
            data = self.data
        try:
            # Cifrar datos antes de guardar
            encrypted_token = aether_crypto.encrypt_json(data)
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(encrypted_token)
        except Exception as e:
            print(f"[AETHER MEMORY] Error guardando memoria cifrada: {e}")

    def _load(self) -> dict:
        """Carga la memoria descifrando el contenido desde el archivo."""
        if not self.file_path.exists():
            self._save(DEFAULT_MEMORY)
            return DEFAULT_MEMORY.copy()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            # Si el contenido parece JSON (no cifrado aún), lo ciframos
            if content.startswith("{"):
                data = json.loads(content)
                self._save(data)
                return data
            
            # Descifrar contenido
            return aether_crypto.decrypt_json(content)
        except Exception as e:
            print(f"[AETHER MEMORY] Error cargando/descifrando memoria: {e}. Usando valores predeterminados.")
            return DEFAULT_MEMORY.copy()

    def remember_fact(
        self,
        topic: str,
        detail: str,
        category: Optional[str] = None,
        importance: Optional[int] = None
    ) -> str:
        """
        Almacena o actualiza un hecho relevante sobre el usuario, proyecto o entorno
        con indexación semántica en tiempo real y persistencia dual.
        """
        res = self.semantic_engine.remember(
            topic=topic,
            detail=detail,
            category=category,
            importance=importance
        )
        self.data = self._load()
        return f"Entendido, señor. {res}"

    def forget_fact(self, topic_or_query: str) -> str:
        """Elimina un hecho específico de la memoria permanente buscando por tema o semántica."""
        res = self.semantic_engine.forget(topic_or_query)
        self.data = self._load()
        return res

    def search_semantic(
        self,
        query: str,
        limit: int = 4,
        category: Optional[str] = None,
        threshold: float = 0.42
    ) -> List[Dict[str, Any]]:
        """
        Realiza una búsqueda híbrida semántica en la memoria permanente.
        Devuelve una lista de diccionarios con el contenido, relevancia y metadatos.
        """
        results = self.semantic_engine.search(
            query=query,
            limit=limit,
            category=category,
            threshold=threshold
        )
        output = []
        for item, score in results:
            d = item.to_dict()
            d["relevance_score"] = round(score, 3)
            output.append(d)
        return output

    def get_relevant_context(
        self,
        query: str,
        max_items: int = 3,
        threshold: float = 0.44
    ) -> str:
        """
        Recupera de forma dinámica los recuerdos más relevantes para la directiva actual
        del usuario y formula un bloque inyectable en el turno de conversación.
        """
        if not query or not query.strip():
            return ""

        matches = self.semantic_engine.search(
            query=query,
            limit=max_items,
            threshold=threshold
        )
        if not matches:
            return ""

        lines = ["[ARCHIVOS NEURONALES A LARGO PLAZO RELEVANTES]:"]
        for item, score in matches:
            lines.append(f"• [{item.category.upper()}] {item.topic}: {item.detail} (relevancia: {score:.2f})")
        return "\n".join(lines)

    def get_context_summary(self) -> str:
        """
        Genera un resumen estructural de identidad y estado del índice semántico
        para ser inyectado como ancla permanente en el System Prompt de Gemini.
        """
        profile = self.data.get("user_profile", {})
        prefs = self.data.get("preferences", {})
        stats = self.semantic_engine.get_stats()

        summary_lines = [
            f"Usuario: {profile.get('name', 'Señor')} ({profile.get('role', 'Comandante')}).",
            f"Preferencia de trabajo: {prefs.get('work_style', 'tecnología')}.",
            f"Preferencia musical/ambiente: {prefs.get('music_genre', 'synthwave')}.",
            f"Índice Semántico Aether: {stats['indexed_vectors']} vectores activos ({stats['vector_dimension']}D) sincronizados."
        ]

        # Incluir recuerdos de máxima prioridad (importancia 5 / identidad clave)
        priority_items = [
            it for it in self.semantic_engine.items.values()
            if it.importance >= 5 and not it.id.startswith("profile_")
        ]
        if priority_items:
            summary_lines.append("Datos estructurales prioritarios:")
            for it in priority_items[:4]:
                summary_lines.append(f"- {it.topic}: {it.detail}")

        return "\n".join(summary_lines)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la memoria para telemetría del sistema."""
        return self.semantic_engine.get_stats()

    def register_session(self):
        """Registra el inicio de una sesión para estadísticas y análisis temporal."""
        insights = self.data.setdefault("system_insights", {})
        insights["sessions_count"] = insights.get("sessions_count", 0) + 1
        insights["last_session"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()

# Instancia global del gestor de memoria
memory_manager = MemoryManager()
