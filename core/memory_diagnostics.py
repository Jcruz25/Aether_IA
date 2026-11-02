"""
Módulo de Autodiagnóstico Predictivo de Memoria de AETHER.
Analiza la salud del índice semántico, predice necesidades de optimización 
y detecta fragmentación o duplicidad en los registros neuronales.
"""
import time
import numpy as np
from typing import Dict, Any, List
from core.semantic_memory import semantic_memory_engine

class MemoryDiagnostics:
    def __init__(self, engine=semantic_memory_engine):
        self.engine = engine

    def run_health_check(self) -> Dict[str, Any]:
        """Realiza un análisis profundo del estado de la memoria semántica."""
        stats = self.engine.get_stats()
        items = list(self.engine.items.values())
        
        # 1. Análisis de Coherencia Vectorial (Predicción de Confusión)
        confusion_risk = 0.0
        if self.engine._vector_matrix is not None and len(items) > 1:
            # Calcular matriz de similitud interna (Auto-cosina)
            matrix = self.engine._vector_matrix
            similarity = np.dot(matrix, matrix.T)
            # Quitar la diagonal (similitud consigo mismo = 1.0)
            np.fill_diagonal(similarity, 0)
            max_sim = np.max(similarity)
            # Si hay registros con similitud > 0.9, hay riesgo de duplicidad semántica
            confusion_risk = float(max_sim)

        # 2. Análisis de Fragmentación
        # Se define por la cantidad de items sin categoría clara o con baja importancia
        low_priority_count = sum(1 for it in items if it.importance <= 2)
        fragmentation = low_priority_count / max(len(items), 1)

        # 3. Predicción de Crecimiento
        # Basado en la tasa de creación de registros (simulado por ahora)
        growth_trend = "ESTABLE" if fragmentation < 0.3 else "EXPANDIENDO"

        # 4. Cálculo de Score de Salud
        # Penaliza confusión alta y fragmentación excesiva
        health_score = 100 - (confusion_risk * 40) - (fragmentation * 20)
        health_score = max(0, min(100, health_score))

        # Generar recomendaciones
        recommendations = []
        if confusion_risk > 0.85:
            recommendations.append("Detectada alta redundancia semántica. Se recomienda purga de duplicados.")
        if fragmentation > 0.4:
            recommendations.append("Fragmentación elevada. Consolidar recuerdos de baja importancia.")
        
        status = "OPTIMO"
        if health_score < 80: status = "NOMINAL"
        if health_score < 60: status = "DEGRADADO"
        if health_score < 40: status = "CRITICO"

        return {
            "health_score": round(health_score, 2),
            "status": status,
            "confusion_risk": round(confusion_risk, 3),
            "fragmentation_index": round(fragmentation, 2),
            "growth_trend": growth_trend,
            "total_vectors": stats["indexed_vectors"],
            "recommendations": recommendations,
            "summary_text": f"Diagnostico de memoria completado, señor. Indice de salud neuronal: {health_score:.0f} por ciento. Estado: {status}."
        }

# Instancia global
memory_diagnostics = MemoryDiagnostics()
