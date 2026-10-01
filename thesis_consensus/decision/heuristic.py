"""
Evaluador semántico heurístico para análisis bibliográfico académico.
Utiliza alineación por facetas conceptuales (dominio/marco, contexto institucional, problemas operativos)
y métricas de rigor para calibrar probabilidades con alta exigencia (umbrales del 80% - 85%).
"""

import re
from typing import Set, Dict, List
from thesis_consensus.models import PaperMetadata, DecisionEvaluation
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.constants import (
    DEFAULT_RELEVANCE_THRESHOLD,
    MINIMUM_RIGOR_SCORE,
    STOPWORDS_EN,
    STOPWORDS_ES,
)


class HeuristicAcademicJudge(BaseDecisionJudge):
    """
    Evaluador basado en análisis semántico de facetas conceptuales académicas,
    clasificación de tipología de investigación y métricas de impacto de citas.
    Aplica umbrales estrictos configurables (80% - 85%).
    """

    STOPWORDS: Set[str] = set(STOPWORDS_EN).union(set(STOPWORDS_ES))

    @property
    def engine_name(self) -> str:
        return "heuristic_academic"

    def is_available(self) -> bool:
        return True

    def _extract_keywords(self, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_-]{3,}\b", text.lower())
        return {w for w in words if w not in self.STOPWORDS}

    def evaluate(
        self,
        paper: PaperMetadata,
        topic_or_claim: str,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> DecisionEvaluation:
        """
        Evalúa el paper frente a las facetas conceptuales de la afirmación de tesis.
        """
        topic_lower = topic_or_claim.lower()
        title_lower = paper.title.lower()
        abstract_or_deep = paper.content_excerpt.lower() if paper.content_excerpt else paper.abstract.lower()
        combined_text = f"{title_lower} {abstract_or_deep}"

        # 1. Definición de facetas conceptuales clave para la tesis
        facet_definitions: Dict[str, Set[str]] = {
            "marco_o_dominio": {
                "itsm", "itil", "it service management", "service management", "it service",
                "information technology service", "governance", "iso 20000", "cobit"
            },
            "contexto_educativo": {
                "higher education", "university", "universities", "academic", "college",
                "campus", "universidad", "universidades", "educación superior"
            },
            "operacion_y_soporte": {
                "help desk", "service desk", "support", "ticket", "tickets", "incident",
                "incidents", "bottleneck", "bottlenecks", "overload", "soporte", "mesa de ayuda",
                "cuello de botella", "cuellos de botella", "atención", "sla", "slas"
            },
        }

        # Identificar qué facetas están activas en la pregunta/afirmación del usuario
        active_facets: Dict[str, bool] = {}
        for facet_name, terms in facet_definitions.items():
            active_facets[facet_name] = any(t in topic_lower for t in terms)

        # Si ninguna faceta estándar está activa, fallback a palabras clave directas
        if not any(active_facets.values()):
            query_terms = self._extract_keywords(topic_or_claim)
            matched = [w for w in query_terms if w in combined_text]
            ratio = len(matched) / max(len(query_terms), 1)
            relevance_score = min(ratio, 1.0)
            facet_report = f"Coincidencia de términos: {len(matched)}/{len(query_terms)}"
        else:
            total_active = sum(1 for v in active_facets.values() if v)
            matched_facets = 0
            matched_details: List[str] = []

            for facet_name, is_active in active_facets.items():
                if is_active:
                    terms = facet_definitions[facet_name]
                    found_in_paper = any(t in combined_text for t in terms)
                    found_in_title = any(t in title_lower for t in terms)
                    if found_in_paper:
                        matched_facets += 1
                        display_name = facet_name.replace("_", " ").title()
                        bonus_tag = " (en título)" if found_in_title else ""
                        matched_details.append(f"{display_name}{bonus_tag}")

            # Ratio base por cobertura de facetas (p.ej. 3/3 -> 1.0, 2/2 -> 1.0, 2/3 -> 0.67)
            base_ratio = matched_facets / max(total_active, 1)

            # Bonificación por presencia explícita en el título del artículo
            title_bonus = 0.08 if any(t in title_lower for terms in facet_definitions.values() for t in terms if any(t in topic_lower for t in terms)) else 0.0

            # Calibración final del porcentaje de relevancia
            if base_ratio == 1.0:
                relevance_score = min(0.85 + title_bonus, 0.98)
            elif base_ratio >= 0.66:
                relevance_score = min(0.72 + title_bonus, 0.79)
            elif base_ratio >= 0.50:
                relevance_score = 0.55
            else:
                relevance_score = 0.25

            facet_report = f"Facetas validadas: {', '.join(matched_details)} ({matched_facets}/{total_active})"

        # 2. Clasificación de tipo de evidencia
        case_study_markers = [
            "case study", "implementation", "university", "campus", "faculty",
            "institution", "caso de estudio", "universidad", "higher education"
        ]
        survey_markers = [
            "survey", "dataset", "tickets", "volume", "metrics", "log analysis",
            "quantitative", "bottlenecks", "slas", "encuesta", "evaluation"
        ]

        has_case_marker = any(m in combined_text for m in case_study_markers)
        has_survey_marker = any(m in combined_text for m in survey_markers)

        if has_case_marker and has_survey_marker:
            evidence_type = "case_study"
        elif has_survey_marker:
            evidence_type = "survey_or_data"
        elif has_case_marker:
            evidence_type = "case_study"
        elif relevance_score >= 0.60:
            evidence_type = "theoretical"
        else:
            evidence_type = "irrelevant"

        # 3. Puntuación de calidad / rigor académico (0.0 a 3.0)
        base_rigor = 1.0
        if paper.citation_count > 50:
            base_rigor += 1.0
        elif paper.citation_count > 15:
            base_rigor += 0.6
        elif paper.citation_count > 3:
            base_rigor += 0.3

        if paper.doi:
            base_rigor += 0.4
        if paper.venue:
            base_rigor += 0.4

        quality_score = min(base_rigor, 3.0)

        # 4. Decisión final: Aplica umbral alto (80% o 85%) y rigor mínimo
        is_relevant = (
            relevance_score >= threshold
            and evidence_type != "irrelevant"
            and quality_score >= MINIMUM_RIGOR_SCORE
        )

        rationale: Dict[str, str] = {
            "probabilidad_relevancia": f"{relevance_score:.1%}",
            "umbral_exigido": f"{threshold:.0%}",
            "facetas_alineadas": facet_report,
            "tipologia_identificada": evidence_type,
            "rigor_metodologico": f"{quality_score:.1f}/3.0 ({paper.citation_count} citas)",
            "veredicto_final": "CONSERVAR (Cumple umbral alto)" if is_relevant else "DESCARTAR (No alcanza umbral)",
        }

        reason = (
            f"Afinidad: {relevance_score:.1%} (Umbral: {threshold:.0%}). "
            f"{facet_report}. Tipo: {evidence_type}. Rigor: {quality_score:.1f}/3.0. "
            f"{'Se conserva para fundamentación' if is_relevant else 'Descartado por no cumplir todas las facetas requeridas'}"
        )

        return DecisionEvaluation(
            is_relevant=is_relevant,
            relevance_score=round(relevance_score, 3),
            threshold_applied=threshold,
            evidence_type=evidence_type,
            quality_score=round(quality_score, 2),
            verdict_reason=reason,
            rationale_breakdown=rationale,
            decision_engine="heuristic_academic",
        )
