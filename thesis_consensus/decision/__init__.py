"""
Módulo de motores de decisión para evaluación de artículos científicos.
"""

from typing import Optional
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.decision.unsloth_laya import UnslothLayaJudge
from thesis_consensus.decision.openai_judge import OpenAILikeJudge
from thesis_consensus.decision.heuristic import HeuristicAcademicJudge

__all__ = [
    "BaseDecisionJudge",
    "UnslothLayaJudge",
    "OpenAILikeJudge",
    "HeuristicAcademicJudge",
    "create_decision_judge",
]


def create_decision_judge(
    preferred_engine: Optional[str] = None,
    unsloth_url: Optional[str] = None,
    unsloth_key: Optional[str] = None,
) -> BaseDecisionJudge:
    """
    Fábrica inteligente de evaluadores de decisión.
    Si se solicita 'laya' o si Unsloth Desktop está disponible en localhost:8888,
    utiliza UnslothLayaJudge.
    Si no, recurre de forma transparente al evaluador heurístico o al configurado.
    """
    if preferred_engine == "laya" or preferred_engine == "unsloth":
        laya_judge = UnslothLayaJudge(base_url=unsloth_url, api_key=unsloth_key)
        if laya_judge.is_available():
            return laya_judge
        # Si explícitamente se pidió pero no responde, retornamos la instancia para que reporte diagnóstico
        return laya_judge

    if preferred_engine == "openai" or preferred_engine == "ollama":
        return OpenAILikeJudge()

    # Detección automática: verificar si Unsloth está levantado
    auto_laya = UnslothLayaJudge(base_url=unsloth_url, api_key=unsloth_key)
    if auto_laya.is_available():
        return auto_laya

    # Respaldo automático sin dependencias externas
    return HeuristicAcademicJudge()
