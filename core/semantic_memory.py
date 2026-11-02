"""
Módulo de Indexación Semántica Avanzada y Memoria a Largo Plazo de AETHER.
Utiliza embeddings densos de alta fidelidad (Gemini) combinados con recuperación léxica híbrida
(Dense + Sparse BM25 / N-gram), deduplicación semántica y persistencia vectorial en disco.
"""
import os
import re
import json
import time
import datetime
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dotenv import load_dotenv

# Rutas de almacenamiento
CORE_DIR = Path(__file__).parent
MEMORY_JSON_PATH = CORE_DIR / "memory.json"
INDEX_CACHE_PATH = CORE_DIR / "semantic_index.json"

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

def normalize_text(text: str) -> str:
    """Normaliza texto eliminando acentos y convirtiendo a minúsculas para búsqueda léxica."""
    if not text:
        return ""
    text = text.lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text

def tokenize(text: str) -> List[str]:
    """Tokeniza texto normalizado extrayendo palabras clave."""
    norm = normalize_text(text)
    return re.findall(r"\b[a-z0-9_]{2,}\b", norm)


class SemanticMemoryItem:
    """Representa una unidad de memoria atómica con metadatos e indexación."""
    def __init__(
        self,
        item_id: str,
        topic: str,
        detail: str,
        category: str = "knowledge",
        importance: int = 3,
        updated: str = "",
        embedding: Optional[List[float]] = None,
        recall_count: int = 0,
        last_recalled: str = ""
    ):
        self.id = item_id
        self.topic = topic.strip()
        self.detail = detail.strip()
        self.category = category.lower().strip()
        self.importance = max(1, min(5, importance))
        self.updated = updated or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.embedding = embedding
        self.recall_count = recall_count
        self.last_recalled = last_recalled

    @property
    def semantic_text(self) -> str:
        """Texto compuesto utilizado para generar la huella vectorial semántica."""
        cat_map = {
            "profile": "Perfil e identidad del usuario",
            "preference": "Preferencia y estilo del usuario",
            "project": "Proyecto y arquitectura técnica",
            "knowledge": "Hecho aprendido y conocimiento permanente",
            "event": "Hito o acontecimiento temporal"
        }
        cat_desc = cat_map.get(self.category, "Conocimiento")
        return f"[{cat_desc}] Tema: {self.topic}. Detalle: {self.detail}"

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "topic": self.topic,
            "detail": self.detail,
            "category": self.category,
            "importance": self.importance,
            "updated": self.updated,
            "recall_count": self.recall_count,
            "last_recalled": self.last_recalled
        }
        if include_embedding and self.embedding is not None:
            data["embedding"] = self.embedding
        return data


class SemanticMemoryEngine:
    """
    Motor Central de Indexación Semántica Avanzada.
    Maneja el espacio vectorial, la búsqueda híbrida y la persistencia sinérgica.
    """
    def __init__(
        self,
        memory_json_path: Path = MEMORY_JSON_PATH,
        index_cache_path: Path = INDEX_CACHE_PATH,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL
    ):
        self.memory_json_path = memory_json_path
        self.index_cache_path = index_cache_path
        self.embedding_model = embedding_model
        self.client = None
        self.items: Dict[str, SemanticMemoryItem] = {}
        
        # Matrices en memoria para aceleración NumPy
        self._vector_matrix: Optional[np.ndarray] = None
        self._vector_item_ids: List[str] = []

        # Caché LRU de embeddings de consultas para respuesta sub-milisegundo en búsquedas repetidas
        from collections import OrderedDict
        self._query_cache: OrderedDict[str, List[float]] = OrderedDict()
        self._max_query_cache = 128
        
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._init_gemini_client()
        self.load_and_sync()

    def _init_gemini_client(self):
        """Inicializa el cliente de Gemini para generación de embeddings."""
        if not self.api_key:
            print("[AETHER SEMANTIC MEMORY] Aviso: GEMINI_API_KEY no presente. Operando en modo léxico de respaldo.")
            return
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            print("[AETHER SEMANTIC MEMORY] Cliente de embeddings Gemini vinculado.")
        except Exception as e:
            print(f"[AETHER SEMANTIC MEMORY] Error inicializando cliente Gemini: {e}")
            self.client = None

    def compute_embedding(self, text: str) -> Optional[List[float]]:
        """Calcula el vector de embedding de un texto a través de Gemini con caché LRU ultra-rápida."""
        if not self.client or not text or not text.strip():
            return None

        clean_key = normalize_text(text.strip())
        if clean_key in self._query_cache:
            self._query_cache.move_to_end(clean_key)
            return self._query_cache[clean_key]

        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text.strip()
            )
            if response.embeddings and len(response.embeddings) > 0:
                values = response.embeddings[0].values
                # Normalizar vector L2 para dot product ultra rápido
                arr = np.array(values, dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                vec_list = arr.tolist()

                # Guardar en caché LRU
                if len(self._query_cache) >= self._max_query_cache:
                    self._query_cache.popitem(last=False)
                self._query_cache[clean_key] = vec_list

                return vec_list
        except Exception as e:
            print(f"[AETHER SEMANTIC MEMORY] Fluctuación calculando embedding: {e}")
        return None

    def _infer_category_and_importance(self, topic: str, detail: str) -> Tuple[str, int]:
        """Infiere categoría e importancia a partir del tema y contenido."""
        t_norm = normalize_text(topic)
        d_norm = normalize_text(detail)

        # Perfil e identidad
        if any(k in t_norm for k in ["nombre", "perfil", "nacimiento", "titulo", "usuario", "graduado"]):
            return "profile", 5

        # Preferencias
        if any(k in t_norm for k in ["favorit", "preferencia", "estilo", "musica", "tratamiento"]):
            return "preference", 4

        # Proyectos y tecnología
        if any(k in t_norm for k in ["proyecto", "stack", "arquitectura", "aros", "meta", "tecnolog"]):
            return "project", 4

        # Hitos o eventos
        if any(k in t_norm for k in ["fecha", "año", "ano", "evento", "sesion"]):
            return "event", 3

        return "knowledge", 3

    def load_and_sync(self):
        """
        Carga la memoria persistente desde memory.json, sincroniza con el índice
        vectorial caché y calcula embeddings para elementos nuevos o modificados.
        """
        self.items.clear()

        # 1. Cargar caché de vectores existente si está disponible
        vector_cache: Dict[str, List[float]] = {}
        if self.index_cache_path.exists():
            try:
                with open(self.index_cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    for item_id, v in cache_data.get("vectors", {}).items():
                        if isinstance(v, list) and len(v) > 0:
                            vector_cache[item_id] = v
            except Exception as e:
                print(f"[AETHER SEMANTIC MEMORY] Error leyendo semantic_index.json: {e}")

        # 2. Cargar memoria JSON estructurada
        if not self.memory_json_path.exists():
            print("[AETHER SEMANTIC MEMORY] Archivo memory.json no encontrado.")
            return

        try:
            with open(self.memory_json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"[AETHER SEMANTIC MEMORY] Error leyendo memory.json: {e}")
            return

        # 3. Procesar hechos estándar
        facts = raw_data.get("facts", [])
        needs_cache_save = False

        for idx, fact in enumerate(facts):
            topic = fact.get("topic", "").strip()
            detail = fact.get("detail", "").strip()
            if not topic or not detail:
                continue

            item_id = fact.get("id") or f"fact_{normalize_text(topic).replace(' ', '_')}"
            category = fact.get("category")
            importance = fact.get("importance")
            if not category or not importance:
                cat, imp = self._infer_category_and_importance(topic, detail)
                category = category or cat
                importance = importance or imp

            cached_vec = vector_cache.get(item_id)
            item = SemanticMemoryItem(
                item_id=item_id,
                topic=topic,
                detail=detail,
                category=category,
                importance=importance,
                updated=fact.get("updated", ""),
                embedding=cached_vec,
                recall_count=fact.get("recall_count", 0),
                last_recalled=fact.get("last_recalled", "")
            )
            self.items[item_id] = item

        # 4. Asegurar que datos clave del perfil y preferencias también estén indexados
        user_profile = raw_data.get("user_profile", {})
        if user_profile:
            name = user_profile.get("name", "")
            role = user_profile.get("role", "")
            title = user_profile.get("title", "")
            if name:
                prof_id = "profile_identity"
                if prof_id not in self.items:
                    self.items[prof_id] = SemanticMemoryItem(
                        item_id=prof_id,
                        topic="identidad_usuario",
                        detail=f"El nombre del usuario es {name}, conocido como {title}. Su rol es {role}.",
                        category="profile",
                        importance=5,
                        embedding=vector_cache.get(prof_id)
                    )

        # 5. Generar embeddings faltantes
        unembedded_items = [it for it in self.items.values() if it.embedding is None]
        if unembedded_items:
            print(f"[AETHER SEMANTIC MEMORY] Indexando semánticamente {len(unembedded_items)} registros nuevos...")
            for it in unembedded_items:
                vec = self.compute_embedding(it.semantic_text)
                if vec:
                    it.embedding = vec
                    vector_cache[it.id] = vec
                    needs_cache_save = True

        # 6. Guardar caché de vectores si hubo cambios
        if needs_cache_save:
            self._save_vector_cache(vector_cache)

        # 7. Compilar matriz NumPy para búsquedas vectoriales instantáneas
        self._build_vector_matrix()
        print(f"[AETHER SEMANTIC MEMORY] Sincronización completada: {len(self.items)} recuerdos indexados.")

    def _save_vector_cache(self, vector_cache: Dict[str, List[float]]):
        """Guarda la caché de vectores en disco de manera segura."""
        try:
            payload = {
                "version": "2.0",
                "model": self.embedding_model,
                "dimension": len(next(iter(vector_cache.values()))) if vector_cache else 0,
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "vectors": vector_cache
            }
            with open(self.index_cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as e:
            print(f"[AETHER SEMANTIC MEMORY] Error guardando semantic_index.json: {e}")

    def _build_vector_matrix(self):
        """Construye la matriz NumPy (N, D) para cálculo de similitud acelerado por hardware."""
        valid_items = [it for it in self.items.values() if it.embedding is not None]
        if not valid_items:
            self._vector_matrix = None
            self._vector_item_ids = []
            return

        self._vector_item_ids = [it.id for it in valid_items]
        matrix = np.array([it.embedding for it in valid_items], dtype=np.float32)
        # Asegurar normalización L2 de cada fila
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._vector_matrix = matrix / norms

    def _calculate_sparse_score(self, query_tokens: List[str], query_raw: str, item: SemanticMemoryItem) -> float:
        """Calcula relevancia léxica basada en tokens, n-gramas y coincidencia de términos clave."""
        if not query_tokens:
            return 0.0

        item_text = f"{item.topic} {item.detail}"
        item_norm = normalize_text(item_text)
        item_tokens = set(tokenize(item_text))

        # 1. Coincidencia de tokens (Jaccard ponderado)
        overlap = sum(1 for t in query_tokens if t in item_tokens)
        token_score = overlap / max(len(query_tokens), 1)

        # 2. Bonificación por coincidencia exacta en el tema (topic)
        topic_norm = normalize_text(item.topic)
        topic_bonus = 0.0
        if any(t in topic_norm for t in query_tokens):
            topic_bonus = 0.25

        # 3. Substring directo (útil para números de año '2024', acrónimos 'FastAPI', etc.)
        norm_query_raw = normalize_text(query_raw)
        substring_bonus = 0.0
        if norm_query_raw in item_norm:
            substring_bonus = 0.35

        return min(1.0, (token_score * 0.6) + topic_bonus + substring_bonus)

    def search(
        self,
        query: str,
        limit: int = 4,
        category: Optional[str] = None,
        threshold: float = 0.45
    ) -> List[Tuple[SemanticMemoryItem, float]]:
        """
        Búsqueda Híbrida Avanzada (Dense Semantic + Sparse Lexical + Ponderación de Importancia).
        Devuelve una lista ordenada de tuplas (SemanticMemoryItem, score).
        """
        if not query or not query.strip() or not self.items:
            return []

        clean_query = query.strip()
        query_tokens = tokenize(clean_query)
        q_vec = self.compute_embedding(clean_query)

        # 1. Puntuación Densa (Vectorial)
        dense_scores: Dict[str, float] = {}
        if q_vec is not None and self._vector_matrix is not None and len(self._vector_item_ids) > 0:
            q_arr = np.array(q_vec, dtype=np.float32)
            # Como los vectores están normalizados L2, dot product == cosine similarity
            sims = np.dot(self._vector_matrix, q_arr)
            for item_id, sim_val in zip(self._vector_item_ids, sims):
                dense_scores[item_id] = float(sim_val)

        # 2. Puntuación Híbrida Combinada
        scored_results: List[Tuple[SemanticMemoryItem, float]] = []

        has_dense = len(dense_scores) > 0
        w_dense = 0.70 if has_dense else 0.0
        w_sparse = 0.25 if has_dense else 0.85
        w_importance = 0.05 if has_dense else 0.15

        for item_id, item in self.items.items():
            if category and item.category != category.lower().strip():
                continue

            s_dense = dense_scores.get(item_id, 0.0)
            s_sparse = self._calculate_sparse_score(query_tokens, clean_query, item)
            s_importance = item.importance / 5.0

            hybrid_score = (w_dense * s_dense) + (w_sparse * s_sparse) + (w_importance * s_importance)

            if hybrid_score >= threshold:
                scored_results.append((item, hybrid_score))

        # Ordenar descendentemente por puntuación
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Registrar acceso a los resultados principales
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        top_results = scored_results[:limit]
        for item, _ in top_results:
            item.recall_count += 1
            item.last_recalled = now_str

        return top_results

    def remember(
        self,
        topic: str,
        detail: str,
        category: Optional[str] = None,
        importance: Optional[int] = None
    ) -> str:
        """
        Almacena o actualiza inteligentemente un hecho en la memoria permanente
        con indexación semántica en tiempo real y deduplicación.
        """
        clean_topic = topic.strip()
        clean_detail = detail.strip()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        if not category or not importance:
            cat, imp = self._infer_category_and_importance(clean_topic, clean_detail)
            category = category or cat
            importance = importance or imp

        # Comprobar si existe coincidencia exacta o semántica muy alta (> 0.86)
        existing_item = None
        topic_norm = normalize_text(clean_topic)

        # 1. Búsqueda exacta de tema
        for item in self.items.values():
            if normalize_text(item.topic) == topic_norm:
                existing_item = item
                break

        # 2. Si no es exacto, comprobar deduplicación semántica
        if existing_item is None and self.client:
            potential_duplicates = self.search(f"{clean_topic}: {clean_detail}", limit=1, threshold=0.88)
            if potential_duplicates:
                existing_item = potential_duplicates[0][0]

        # Calcular nuevo vector
        new_vec = self.compute_embedding(f"[{category}] Tema: {clean_topic}. Detalle: {clean_detail}")

        if existing_item:
            existing_item.topic = clean_topic
            existing_item.detail = clean_detail
            existing_item.category = category
            existing_item.importance = max(existing_item.importance, importance)
            existing_item.updated = now_str
            if new_vec:
                existing_item.embedding = new_vec
            action_desc = f"Actualizado registro sináptico existente '{clean_topic}'"
        else:
            item_id = f"fact_{topic_norm.replace(' ', '_')}_{int(time.time())}"
            item = SemanticMemoryItem(
                item_id=item_id,
                topic=clean_topic,
                detail=clean_detail,
                category=category,
                importance=importance,
                updated=now_str,
                embedding=new_vec
            )
            self.items[item_id] = item
            action_desc = f"Consolidado nuevo registro sináptico '{clean_topic}'"

        # Sincronizar en disco tanto memory.json como el índice de vectores
        self._persist_all()
        self._build_vector_matrix()

        print(f"[AETHER SEMANTIC MEMORY] {action_desc}: {clean_detail}")
        return f"{action_desc}: {clean_detail}."

    def forget(self, topic_or_query: str) -> str:
        """
        Elimina un registro específico buscando por coincidencia exacta o semántica.
        """
        clean_target = topic_or_query.strip()
        target_norm = normalize_text(clean_target)

        # 1. Búsqueda por tema exacto
        target_id = None
        target_topic = clean_target

        for item_id, item in self.items.items():
            if normalize_text(item.topic) == target_norm:
                target_id = item_id
                target_topic = item.topic
                break

        # 2. Si no se halló por coincidencia exacta, buscar por similitud semántica alta
        if not target_id:
            matches = self.search(clean_target, limit=1, threshold=0.78)
            if matches:
                target_id = matches[0][0].id
                target_topic = matches[0][0].topic

        if target_id and target_id in self.items:
            del self.items[target_id]
            self._persist_all()
            self._build_vector_matrix()
            return f"El registro neuronal '{target_topic}' ha sido purgado permanentemente, señor."

        return f"No encontré ningún registro que coincida semánticamente con '{clean_target}' para purgar."

    def _persist_all(self):
        """Sincroniza el estado en memoria con memory.json y semantic_index.json."""
        # 1. Actualizar memory.json manteniendo el formato estructurado
        raw_data = {
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
            "facts": [],
            "system_insights": {
                "sessions_count": 0,
                "last_session": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "semantic_index_version": "2.0"
            }
        }

        # Cargar valores previos de perfil si existen
        if self.memory_json_path.exists():
            try:
                with open(self.memory_json_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if "user_profile" in old_data:
                        raw_data["user_profile"] = old_data["user_profile"]
                    if "preferences" in old_data:
                        raw_data["preferences"] = old_data["preferences"]
                    if "system_insights" in old_data:
                        raw_data["system_insights"] = old_data["system_insights"]
            except Exception:
                pass

        # Poblar facts
        vector_cache = {}
        for it in self.items.values():
            if it.id.startswith("profile_"):
                # No duplicar el perfil en facts
                if it.embedding:
                    vector_cache[it.id] = it.embedding
                continue

            raw_data["facts"].append(it.to_dict(include_embedding=False))
            if it.embedding:
                vector_cache[it.id] = it.embedding

        try:
            with open(self.memory_json_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[AETHER SEMANTIC MEMORY] Error guardando memory.json: {e}")

        # 2. Guardar caché vectorial
        self._save_vector_cache(vector_cache)

    def get_stats(self) -> Dict[str, Any]:
        """Devuelve telemetría y métricas del motor de memoria semántica."""
        cats: Dict[str, int] = {}
        for it in self.items.values():
            cats[it.category] = cats.get(it.category, 0) + 1

        indexed_vectors = sum(1 for it in self.items.values() if it.embedding is not None)
        return {
            "total_items": len(self.items),
            "indexed_vectors": indexed_vectors,
            "vector_dimension": 3072 if indexed_vectors > 0 else 0,
            "categories": cats,
            "embedding_model": self.embedding_model,
            "status": "online" if self.client else "fallback_lexical"
        }

# Instancia global del motor semántico
semantic_memory_engine = SemanticMemoryEngine()

