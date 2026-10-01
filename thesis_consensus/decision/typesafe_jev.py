"""
Integración con el modelo de decisión TypeSafe AI / Jev (System One).
Documentación de referencia: https://docs.typesafe.ai/
Endpoint: POST https://api.typesafe.ai/v1/systemone
Ventana de contexto: 32K tokens.
"""

import os
from typing import Dict, Optional, Any
import httpx
from thesis_consensus.models import (
    PaperMetadata,
    DecisionEvaluation,
    LayaNoulResponse,
    LayaChoiceResponse,
    LayaScoreResponse,
)
from thesis_consensus.decision.protocol import BaseDecisionJudge
from thesis_consensus.constants import (
    TYPESAFE_DEFAULT_URL,
    DEFAULT_JEV_MODEL,
    DEFAULT_RELEVANCE_THRESHOLD,
    DEFAULT_TIMEOUT_SECONDS,
    MINIMUM_RIGOR_SCORE,
)


class TypeSafeJevJudge(BaseDecisionJudge):
    """
    Evaluador de artículos científicos basado en el modelo de decisión Jev de TypeSafe AI.
    Aprovecha la ventana de contexto de 32K tokens de Jev para evaluar papers completos o
    secciones extendidas de resultados sin truncamiento artificial.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_JEV_MODEL,
        default_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        raw_url = base_url if base_url is not None else os.getenv("TYPESAFE_API_URL")
        self._base_url: str = raw_url if raw_url else TYPESAFE_DEFAULT_URL
        self._api_key: str = api_key if api_key is not None else (os.getenv("TYPESAFE_API_KEY") or "")
        raw_model = os.getenv("TYPESAFE_MODEL")
        self._model_name: str = raw_model if raw_model else model_name
        self._default_threshold: float = default_threshold
        self._timeout_seconds: float = timeout_seconds

    @property
    def engine_name(self) -> str:
        return "typesafe_jev"

    def is_available(self) -> bool:
        """
        Verifica si la API de TypeSafe Jev está disponible y autentica correctamente con la clave.
        """
        if not self._api_key:
            return False
        try:
            headers: Dict[str, str] = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload: Dict[str, object] = {
                "model": self._model_name,
                "state": "System health check for academic evaluation.",
                "questions": {
                    "health": {
                        "type": "noul",
                        "instructions": "Is this an academic health check?",
                    }
                },
            }
            with httpx.Client(timeout=8.0) as client:
                res = client.post(self._base_url, headers=headers, json=payload)
                return res.status_code == 200
        except Exception:
            return False

    def evaluate(
        self,
        paper: PaperMetadata,
        topic_or_claim: str,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> DecisionEvaluation:
        """
        Envía los metadatos y el texto sustantivo (hasta 32K tokens) a TypeSafe Jev
        para tomar una decisión probabilística rigurosa sobre el artículo.
        """
        content_body = paper.content_excerpt if paper.content_excerpt else paper.abstract
        # Jev soporta 32K tokens; permitimos hasta 18,000 caracteres de contenido sustantivo
        content_snippet = content_body[:18000] if content_body else "(Sin resumen disponible, evaluar por título y metadatos)"

        state_text = (
            f"Paper Title: {paper.title}\n"
            f"Venue/Journal: {paper.venue or 'Academic publication'}\n"
            f"Year: {paper.year or 'Recent'}\n"
            f"Citations: {paper.citation_count}\n"
            f"Content Source: {paper.content_source}\n"
            f"Content & Findings (Full Text / Abstract):\n{content_snippet}"
        )

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Preguntas estructuradas paralelas System One
        questions_payload: Dict[str, object] = {
            "is_relevant": {
                "type": "noul",
                "instructions": (
                    f"Does this research paper provide theoretical, empirical, or methodological evidence relevant to: \"{topic_or_claim}\"?"
                ),
                "criteria": {
                    "true": "Directly or substantively addresses the core concepts, frameworks, challenges, or solutions in the research question",
                    "false": "Off-topic, unrelated discipline, or lacks meaningful connection to the research question",
                },
            },
            "evidence_type": {
                "type": "choice",
                "instructions": "Which category best classifies the empirical or theoretical contribution of this research?",
                "criteria": {
                    "case_study": "Real-world university help desk, higher education campus, or institutional implementation case study",
                    "survey_or_data": "Quantitative survey, ticket volume metrics, queue statistics, or bottleneck analysis",
                    "theoretical": "Conceptual framework, ITIL/ITSM best practices, architecture, or literature review",
                    "irrelevant": "Not relevant, unrelated field, or out of scope",
                },
            },
            "rigor_score": {
                "type": "score",
                "instructions": "Rate the scholarly quality and suitability of this paper for an undergraduate thesis theoretical framework:",
                "criteria": [
                    "insufficient quality or non-scholarly",
                    "acceptable background reference",
                    "solid empirical or theoretical methodology",
                    "authoritative benchmark paper",
                ],
            },
        }

        body: Dict[str, object] = {
            "model": self._model_name,
            "state": state_text,
            "questions": questions_payload,
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                resp = client.post(self._base_url, headers=headers, json=body)
                if resp.status_code != 200:
                    return self._fallback_error_evaluation(f"HTTP {resp.status_code}: {resp.text[:120]}", threshold)

                data: Dict[str, Any] = resp.json()
                answers_dict = data.get("answers")
                if not isinstance(answers_dict, dict):
                    return self._fallback_error_evaluation("Respuesta sin campo 'answers'", threshold)

                # 1. Probabilidad y Confianza de Relevancia
                relevance_prob = 0.5
                confidence_val = 1.0
                raw_rel = answers_dict.get("is_relevant")
                if isinstance(raw_rel, dict):
                    confidence_val = float(raw_rel.get("confidence", 1.0))
                    if raw_rel.get("type") == "choice":
                        raw_probs = raw_rel.get("probabilities")
                        if isinstance(raw_probs, dict):
                            raw_val = raw_probs.get("yes_relevant", 0.0)
                            if isinstance(raw_val, (int, float)):
                                relevance_prob = float(raw_val)
                    elif raw_rel.get("type") == "noul":
                        parsed_noul = LayaNoulResponse.model_validate(raw_rel)
                        relevance_prob = parsed_noul.noul

                # 2. Tipología de Evidencia
                evidence_choice = "theoretical"
                raw_choice = answers_dict.get("evidence_type")
                if isinstance(raw_choice, dict):
                    parsed_choice = LayaChoiceResponse.model_validate(raw_choice)
                    evidence_choice = parsed_choice.choice

                # 3. Puntuación de Rigor Metodológico
                rigor_score = 1.5
                raw_score = answers_dict.get("rigor_score")
                if isinstance(raw_score, dict):
                    parsed_score = LayaScoreResponse.model_validate(raw_score)
                    rigor_score = parsed_score.score

                # Veredicto con umbral alto (80% u 85%) y rigor mínimo
                is_conserved = (
                    relevance_prob >= threshold
                    and evidence_choice != "irrelevant"
                    and rigor_score >= MINIMUM_RIGOR_SCORE
                )

                rationale = {
                    "probabilidad_relevancia": f"{relevance_prob:.1%}",
                    "confianza_modelo": f"{confidence_val:.2f}",
                    "umbral_exigido": f"{threshold:.0%}",
                    "tipologia_clasificada": evidence_choice,
                    "rigor_metodologico": f"{rigor_score:.2f}/3.0",
                    "decision": "Conservar para Marco Teórico" if is_conserved else "Descartar",
                }

                reason = (
                    f"Decisión TypeSafe Jev: P(relevancia)={relevance_prob:.1%} (Umbral: {threshold:.0%}, Confianza: {confidence_val:.2f}). "
                    f"Tipo={evidence_choice}, Rigor={rigor_score:.1f}/3.0. "
                    f"{'Aceptado con alta afinidad' if is_conserved else 'Rechazado por no alcanzar el umbral exigido'}"
                )

                return DecisionEvaluation(
                    is_relevant=is_conserved,
                    relevance_score=round(relevance_prob, 3),
                    threshold_applied=threshold,
                    evidence_type=evidence_choice,
                    quality_score=round(rigor_score, 2),
                    verdict_reason=reason,
                    rationale_breakdown=rationale,
                    decision_engine="typesafe_jev",
                )

        except Exception as err:
            return self._fallback_error_evaluation(str(err), threshold)

    def _fallback_error_evaluation(self, err_msg: str, threshold: float) -> DecisionEvaluation:
        return DecisionEvaluation(
            is_relevant=False,
            relevance_score=0.0,
            threshold_applied=threshold,
            evidence_type="irrelevant",
            quality_score=0.0,
            verdict_reason=f"Error en TypeSafe Jev: {err_msg}",
            rationale_breakdown={"error": err_msg},
            decision_engine="typesafe_jev",
        )
