"""
Agente orquestador para búsqueda, evaluación por modelo de decisión y redacción APA 7.
Soporta procesamiento individual y procesamiento en lote (batch) de múltiples preguntas de tesis.
"""

from typing import List, Optional, Literal, Tuple, Callable, Dict
from thesis_consensus.models import (
    PaperMetadata,
    ThesisEvidenceItem,
    MultiPaperSynthesis,
    TopicResearchBatch,
)
from thesis_consensus.providers.base import BaseAcademicProvider
from thesis_consensus.providers.composite import CompositeAcademicProvider
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.decision import create_decision_judge
from thesis_consensus.synthesizer import ThesisSynthesizer
from thesis_consensus.content_extractor import SafeContentExtractor
from thesis_consensus.constants import (
    DEFAULT_RELEVANCE_THRESHOLD,
    DEFAULT_MIN_PUBLICATION_YEAR,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_LANGUAGE,
)


class ThesisConsensusAgent:
    """
    Agente que orquesta el flujo completo de fundamentación teórica:
    Búsqueda segura -> Extracción de texto extendido -> Evaluación por Modelo de Decisión -> Síntesis Multi-Paper APA 7.
    """

    def __init__(
        self,
        provider: Optional[BaseAcademicProvider] = None,
        decision_judge: Optional[BaseDecisionJudge] = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self._provider: BaseAcademicProvider = provider or CompositeAcademicProvider()
        self._decision_judge: BaseDecisionJudge = decision_judge or create_decision_judge()
        self._synthesizer = ThesisSynthesizer(language=language)
        self._content_extractor = SafeContentExtractor()

    @property
    def current_decision_engine(self) -> str:
        return self._decision_judge.engine_name

    def research_single_topic(
        self,
        topic_or_claim: str,
        limit_search: int = DEFAULT_SEARCH_LIMIT,
        min_year: int = DEFAULT_MIN_PUBLICATION_YEAR,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        progress_callback: Optional[Callable[[int, int, PaperMetadata, bool], None]] = None,
    ) -> Tuple[List[ThesisEvidenceItem], List[PaperMetadata], MultiPaperSynthesis]:
        """
        Ejecuta la fundamentación completa de una afirmación individual aplicando el umbral exigido.

        Returns:
            Tupla de (items_conservados, papers_descartados, sintesis_multi_paper).
        """
        raw_papers = self._provider.search(
            query=topic_or_claim,
            limit=limit_search,
            min_year=min_year,
        )

        conserved_items: List[ThesisEvidenceItem] = []
        discarded_papers: List[PaperMetadata] = []

        for idx, paper in enumerate(raw_papers):
            # Extracción segura de contenido extendido si es Acceso Abierto
            if paper.is_open_access or paper.open_access_pdf_url:
                deep_text, source_type = self._content_extractor.extract_deep_content(paper)
                paper.content_excerpt = deep_text
                if source_type == "open_access_pdf":
                    paper.content_source = "open_access_pdf"
                elif source_type == "open_access_html":
                    paper.content_source = "open_access_html"
                else:
                    paper.content_source = "abstract_only"

            decision = self._decision_judge.evaluate(
                paper=paper,
                topic_or_claim=topic_or_claim,
                threshold=threshold,
            )

            if decision.is_relevant:
                item = self._synthesizer.synthesize_item(
                    paper=paper,
                    decision=decision,
                    topic_or_claim=topic_or_claim,
                    index=len(conserved_items),
                )
                conserved_items.append(item)
            else:
                discarded_papers.append(paper)

            if progress_callback:
                progress_callback(idx + 1, len(raw_papers), paper, decision.is_relevant)

        multi_synthesis = self._synthesizer.synthesize_multi_paper_consensus(
            topic_or_claim=topic_or_claim,
            items=conserved_items,
        )

        return conserved_items, discarded_papers, multi_synthesis

    def research_batch(
        self,
        topics: List[str],
        limit_per_topic: int = DEFAULT_SEARCH_LIMIT,
        min_year: int = DEFAULT_MIN_PUBLICATION_YEAR,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        topic_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> TopicResearchBatch:
        """
        Procesa una lista de múltiples afirmaciones o preguntas de tesis de forma organizada.
        """
        conserved_dict: Dict[str, List[ThesisEvidenceItem]] = {}
        discarded_dict: Dict[str, List[PaperMetadata]] = {}
        syntheses_dict: Dict[str, MultiPaperSynthesis] = {}
        all_conserved: List[ThesisEvidenceItem] = []

        total_topics = len(topics)
        for idx, topic in enumerate(topics, start=1):
            if topic_callback:
                topic_callback(idx, total_topics, topic)

            conserved, discarded, multi_syn = self.research_single_topic(
                topic_or_claim=topic,
                limit_search=limit_per_topic,
                min_year=min_year,
                threshold=threshold,
            )

            conserved_dict[topic] = conserved
            discarded_dict[topic] = discarded
            syntheses_dict[topic] = multi_syn
            all_conserved.extend(conserved)

        return TopicResearchBatch(
            topics=topics,
            conserved_by_topic=conserved_dict,
            discarded_by_topic=discarded_dict,
            syntheses_by_topic=syntheses_dict,
            all_conserved_items=all_conserved,
        )
