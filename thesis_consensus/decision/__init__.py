"""
Módulo de motores de decisión para evaluación de artículos científicos.
"""

from typing import Optional
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.decision.typesafe_jev import TypeSafeJevJudge
from thesis_consensus.decision.unsloth_laya import UnslothLayaJudge
from thesis_consensus.decision.openai_judge import OpenAILikeJudge
from thesis_consensus.decision.heuristic import HeuristicAcademicJudge

from thesis_consensus.constants import DEFAULT_DECISION_ENGINE

__all__ = [
    "BaseDecisionJudge",
    "TypeSafeJevJudge",
    "UnslothLayaJudge",
    "OpenAILikeJudge",
    "HeuristicAcademicJudge",
    "create_decision_judge",
]


def create_decision_judge(
    preferred_engine: Optional[str] = DEFAULT_DECISION_ENGINE,
    typesafe_url: Optional[str] = None,
    typesafe_key: Optional[str] = None,
    unsloth_url: Optional[str] = None,
    unsloth_key: Optional[str] = None,
) -> BaseDecisionJudge:
    """
    Fábrica inteligente de evaluadores de decisión.
    Prioriza por defecto el modelo de decisión TypeSafe AI / Jev (System One con 32K tokens de contexto).
    Permite alternar con Unsloth Laya (local en GPU) o el evaluador semántico determinístico.
    """
    engine_choice = (preferred_engine or DEFAULT_DECISION_ENGINE).lower().strip()

    if engine_choice in ("heuristic", "heuristic_academic"):
        return HeuristicAcademicJudge()

    if engine_choice in ("openai", "ollama"):
        return OpenAILikeJudge()

    if engine_choice in ("unsloth_laya", "laya"):
        return UnslothLayaJudge(base_url=unsloth_url, api_key=unsloth_key)

    # Por defecto ('typesafe_jev', 'jev', 'typesafe', 'auto'): usar TypeSafe Jev
    jev_judge = TypeSafeJevJudge(base_url=typesafe_url, api_key=typesafe_key)
    if jev_judge.is_available():
        return jev_judge

    # Si se solicitó explícitamente pero no autentica, retornarlo para diagnosticar en la CLI
    if engine_choice in ("typesafe_jev", "jev", "typesafe"):
        return jev_judge

    # Intentar Unsloth local como alternativa si está disponible
    laya_judge = UnslothLayaJudge(base_url=unsloth_url, api_key=unsloth_key)
    if laya_judge.is_available():
        return laya_judge

    # Respaldo automático sin dependencias externas
    return HeuristicAcademicJudge()
