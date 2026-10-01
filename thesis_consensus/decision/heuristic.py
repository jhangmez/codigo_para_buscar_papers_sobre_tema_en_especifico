"""
Evaluador semántico heurístico para análisis bibliográfico académico.
Sirve como motor por defecto (sin necesidad de GPU ni dependencias pesadas)
y como respaldo automático cuando Unsloth Laya u Ollama no están activos.
"""

import re
from typing import Set, List
from thesis_consensus.models import PaperMetadata, DecisionEvaluation
from thesis_consensus.decision.protocol import BaseDecisionJudge


class HeuristicAcademicJudge(BaseDecisionJudge):
    """
    Evaluador basado en análisis semántico de palabras clave académicas,
    clasificación de tipología de investigación y métricas de impacto de citas.
    """

    STOPWORDS: Set[str] = {
        "the", "a", "an", "and", "or", "in", "on", "at", "for", "with", "by", "about",
        "against", "between", "into", "through", "during", "before", "after", "above",
        "below", "to", "from", "up", "down", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "how", "what", "which",
        "who", "when", "where", "why", "can", "could", "should", "would", "institutions",
        "de", "la", "el", "en", "un", "una", "los", "las", "por", "para", "con", "sobre"
    }

    @property
    def engine_name(self) -> str:
        return "heuristic_academic"

    def is_available(self) -> bool:
        """El evaluador heurístico siempre está disponible (cero fallos de red)."""
        return True

    def _extract_keywords(self, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_-]{3,}\b", text.lower())
        return {w for w in words if w not in self.STOPWORDS}

    def evaluate(self, paper: PaperMetadata, topic_or_claim: str) -> DecisionEvaluation:
        """Evalúa relevancia, tipo de evidencia y rigor del artículo."""
        query_terms = self._extract_keywords(topic_or_claim)
        if not query_terms:
            return DecisionEvaluation(
                is_relevant=True,
                relevance_score=0.7,
                evidence_type="theoretical",
                quality_score=1.5,
                verdict_reason="Consulta amplia; artículo preseleccionado por búsqueda.",
                decision_engine="heuristic_academic",
            )

        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower()
        combined_text = f"{title_lower} {abstract_lower}"

        # 1. Conteo ponderado de coincidencias
        title_matches = sum(1 for term in query_terms if term in title_lower)
        abstract_matches = sum(1 for term in query_terms if term in abstract_lower)

        # Términos críticos compuestos o de alto impacto
        special_compounds = ["itsm", "itil", "help desk", "service desk", "ticket", "bottleneck", "university", "higher education"]
        compound_bonus = sum(0.15 for c in special_compounds if c in combined_text and c in topic_or_claim.lower())

        total_score_raw = (title_matches * 0.35) + (abstract_matches * 0.15) + compound_bonus
        # Normalizar entre 0.0 y 1.0
        relevance_score = min(max(total_score_raw / max(len(query_terms) * 0.4, 1.0), 0.0), 1.0)

        # 2. Clasificación de tipo de evidencia
        evidence_type = "theoretical"
        case_study_markers = ["case study", "implementation", "university", "campus", "faculty", "institution", "caso de estudio", "universidad"]
        survey_markers = ["survey", "dataset", "tickets", "volume", "metrics", "log analysis", "quantitative", "bottlenecks", "slas", "encuesta"]
        
        has_case_marker = any(m in combined_text for m in case_study_markers)
        has_survey_marker = any(m in combined_text for m in survey_markers)

        if has_case_marker and has_survey_marker:
            evidence_type = "case_study"
        elif has_survey_marker:
            evidence_type = "survey_or_data"
        elif has_case_marker:
            evidence_type = "case_study"
        elif relevance_score > 0.3:
            evidence_type = "theoretical"
        else:
            evidence_type = "irrelevant"

        # 3. Puntuación de calidad / rigor académico (0.0 a 3.0)
        base_rigor = 1.0
        if paper.citation_count > 50:
            base_rigor += 1.0
        elif paper.citation_count > 10:
            base_rigor += 0.5
        elif paper.citation_count > 2:
            base_rigor += 0.2

        if paper.doi:
            base_rigor += 0.4
        if paper.venue:
            base_rigor += 0.4

        quality_score = min(base_rigor, 3.0)

        is_relevant = relevance_score >= 0.35 and evidence_type != "irrelevant"

        reason = (
            f"Afinidad semántica: {relevance_score:.0%}. "
            f"Tipo identificado: {evidence_type}. "
            f"Rigor: {quality_score:.1f}/3.0 ({paper.citation_count} citas). "
            f"{'Se conserva para fundamentación' if is_relevant else 'Descartado por relevancia insuficiente'}"
        )

        return DecisionEvaluation(
            is_relevant=is_relevant,
            relevance_score=round(relevance_score, 3),
            evidence_type=evidence_type,
            quality_score=round(quality_score, 2),
            verdict_reason=reason,
            decision_engine="heuristic_academic",
        )
