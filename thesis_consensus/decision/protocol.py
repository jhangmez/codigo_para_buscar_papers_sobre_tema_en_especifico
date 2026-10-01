"""
Protocolo e interfaz base para los motores de decisión de relevancia académica.
"""

from abc import ABC, abstractmethod
from thesis_consensus.models import PaperMetadata, DecisionEvaluation


class BaseDecisionJudge(ABC):
    """Interfaz abstracta para evaluar la idoneidad teórica de un artículo."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Nombre del motor de decisión."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Indica si el servidor del modelo de decisión está activo y respondiendo."""
        pass

    @abstractmethod
    def evaluate(self, paper: PaperMetadata, topic_or_claim: str) -> DecisionEvaluation:
        """
        Evalúa un artículo frente a la temática o afirmación de la tesis.

        Args:
            paper: Metadatos y resumen del artículo.
            topic_or_claim: Tema, pregunta o afirmación que se desea fundamentar.

        Returns:
            Evaluación estructurada con puntaje, tipo de evidencia y veredicto.
        """
        pass
