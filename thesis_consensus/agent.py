"""
Agente orquestador para búsqueda, evaluación por modelo de decisión y redacción APA 7.
"""

from typing import List, Optional, Literal, Tuple, Callable
from thesis_consensus.models import (
    PaperMetadata,
    ThesisEvidenceItem,
)
from thesis_consensus.providers.base import BaseAcademicProvider
from thesis_consensus.providers.composite import CompositeAcademicProvider
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.decision import create_decision_judge
from thesis_consensus.synthesizer import ThesisSynthesizer


class ThesisConsensusAgent:
    """
    Agente que orquesta el flujo completo de fundamentación teórica:
    Búsqueda segura -> Evaluación por LLM de Decisión -> Filtrado -> Redacción APA 7.
    """

    def __init__(
        self,
        provider: Optional[BaseAcademicProvider] = None,
        decision_judge: Optional[BaseDecisionJudge] = None,
        language: Literal["es", "en"] = "es",
    ) -> None:
        self._provider: BaseAcademicProvider = provider or CompositeAcademicProvider()
        self._decision_judge: BaseDecisionJudge = decision_judge or create_decision_judge()
        self._synthesizer = ThesisSynthesizer(language=language)

    @property
    def current_decision_engine(self) -> str:
        return self._decision_judge.engine_name

    def research_and_fundament(
        self,
        topic_or_claim: str,
        limit_search: int = 15,
        min_year: int = 2012,
        progress_callback: Optional[Callable[[int, int, PaperMetadata, bool], None]] = None,
    ) -> Tuple[List[ThesisEvidenceItem], List[PaperMetadata]]:
        """
        Ejecuta la fundamentación completa de una afirmación o pregunta de tesis.

        Args:
            topic_or_claim: La afirmación o pregunta a fundamentar.
            limit_search: Cantidad de papers iniciales a recuperar de la base científica.
            min_year: Año mínimo de publicación.
            progress_callback: Función opcional para reportar progreso en tiempo real.

        Returns:
            Tupla de (items_conservados, papers_descartados).
        """
        # 1. Búsqueda de literatura
        raw_papers = self._provider.search(
            query=topic_or_claim,
            limit=limit_search,
            min_year=min_year,
        )

        conserved_items: List[ThesisEvidenceItem] = []
        discarded_papers: List[PaperMetadata] = []

        # 2. Evaluación mediante el modelo de decisión (Laya / LLM / Heurístico)
        for idx, paper in enumerate(raw_papers):
            decision = self._decision_judge.evaluate(paper, topic_or_claim)

            if decision.is_relevant:
                # "y si sirve se conserva"
                item = self._synthesizer.synthesize_item(
                    paper=paper,
                    decision=decision,
                    topic_or_claim=topic_or_claim,
                    index=len(conserved_items),
                )
                conserved_items.append(item)
            else:
                # "y si no pues se va"
                discarded_papers.append(paper)

            if progress_callback:
                progress_callback(idx + 1, len(raw_papers), paper, decision.is_relevant)

        return conserved_items, discarded_papers
