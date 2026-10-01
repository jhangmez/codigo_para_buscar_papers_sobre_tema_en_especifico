"""
Módulo de motores de decisión para evaluación de artículos científicos.
"""

from typing import Optional
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.decision.unsloth_laya import UnslothLayaJudge
from thesis_consensus.decision.openai_judge import OpenAILikeJudge
from thesis_consensus.decision.heuristic import HeuristicAcademicJudge

from thesis_consensus.constants import DEFAULT_DECISION_ENGINE

__all__ = [
    "BaseDecisionJudge",
    "UnslothLayaJudge",
    "OpenAILikeJudge",
    "HeuristicAcademicJudge",
    "create_decision_judge",
]


def create_decision_judge(
    preferred_engine: Optional[str] = DEFAULT_DECISION_ENGINE,
    unsloth_url: Optional[str] = None,
    unsloth_key: Optional[str] = None,
) -> BaseDecisionJudge:
    """
    Fábrica inteligente de evaluadores de decisión.
    Prioriza por defecto el modelo de decisión neuronal Unsloth Laya ejecutado localmente en GPU.
    Si el servidor local no estuviera en ejecución, recurre de forma segura al evaluador semántico.
    """
    engine_choice = (preferred_engine or DEFAULT_DECISION_ENGINE).lower().strip()

    if engine_choice in ("heuristic", "heuristic_academic"):
        return HeuristicAcademicJudge()

    if engine_choice in ("openai", "ollama"):
        return OpenAILikeJudge()

    # Por defecto ('unsloth_laya', 'laya', 'auto'): usar Unsloth Laya
    laya_judge = UnslothLayaJudge(base_url=unsloth_url, api_key=unsloth_key)
    if laya_judge.is_available():
        return laya_judge

    # Si se especificó explícitamente pero no responde, se retorna para reportar el diagnóstico en la CLI
    if engine_choice in ("unsloth_laya", "laya"):
        return laya_judge

    # Respaldo automático sin dependencias externas
    return HeuristicAcademicJudge()
