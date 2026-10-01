"""
Integración con el modelo de decisión Laya (Jev API) servido a través de Unsloth Desktop o CLI.
Documentación de referencia: https://unsloth.ai/docs/models/decision-laya
Endpoint: POST /v1/systemone
"""

import os
from typing import Dict, Optional
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
    UNSLOTH_DEFAULT_URL,
    DEFAULT_RELEVANCE_THRESHOLD,
    DEFAULT_DECISION_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    MINIMUM_RIGOR_SCORE,
)


class UnslothLayaJudge(BaseDecisionJudge):
    """
    Evaluador de artículos científicos basado en el modelo de decisión Laya de Unsloth.
    Utiliza preguntas 'noul' (probabilidad sí/no), 'choice' (clasificación) y 'score' (calidad).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_DECISION_MODEL,
        default_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        raw_url = base_url if base_url is not None else os.getenv("UNSLOTH_API_URL")
        self._base_url: str = raw_url if raw_url else UNSLOTH_DEFAULT_URL
        self._api_key: str = api_key if api_key is not None else (os.getenv("UNSLOTH_API_KEY") or "")
        self._model_name: str = model_name
        self._default_threshold: float = default_threshold
        self._timeout_seconds: float = timeout_seconds

    @property
    def engine_name(self) -> str:
        return "unsloth_laya"

    def is_available(self) -> bool:
        """
        Verifica si el endpoint de Decision API (/v1/systemone) está realmente activo
        y listo para servir inferencias de Laya.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                headers: Dict[str, str] = {"Content-Type": "application/json"}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"
                payload: Dict[str, object] = {
                    "model": self._model_name,
                    "state": "Health check",
                    "questions": {
                        "check": {"type": "noul", "instructions": "Is this text English?"}
                    },
                }
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
        Envía los metadatos y el resumen del paper a Unsloth Laya para tomar la decisión estructurada.
        Aplica el umbral alto exigido (80% - 85%).
        """
        content_body = paper.content_excerpt if paper.content_excerpt else paper.abstract
        content_snippet = content_body[:1500] if content_body else "(Sin resumen disponible, evaluar por título)"
        state_text = (
            f"Paper Title: {paper.title}\n"
            f"Venue/Journal: {paper.venue or 'Academic publication'}\n"
            f"Year: {paper.year or 'Recent'}\n"
            f"Content Source: {paper.content_source}\n"
            f"Content/Findings Excerpt:\n{content_snippet}"
        )

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        questions_payload: Dict[str, object] = {
            "is_relevant": {
                "type": "choice",
                "instructions": (
                    f"Does this academic paper provide direct empirical evidence, theoretical models, "
                    f"or actionable insights directly answering: '{topic_or_claim}'?"
                ),
                "criteria": {
                    "yes_relevant": "Yes, directly addresses the research question with empirical evidence, methodology, or theoretical foundations",
                    "no_irrelevant": "No, off-topic, unrelated domain, or lacks substantive relevance to the research question",
                },
            },
            "evidence_type": {
                "type": "choice",
                "instructions": "Which category best classifies the empirical or theoretical value of this research?",
                "criteria": {
                    "case_study": "Real-world university help desk or higher education implementation case study",
                    "survey_or_data": "Quantitative survey, ticket volume metrics, or bottleneck analysis",
                    "theoretical": "Conceptual framework, ITIL/ITSM best practices, or literature review",
                    "irrelevant": "Not relevant, unrelated field, or out of scope",
                },
            },
            "rigor_score": {
                "type": "score",
                "instructions": "How strong and valuable is this paper to be cited as a theoretical foundation in an undergraduate thesis?",
                "criteria": [
                    "insufficient substance or off topic",
                    "acceptable contextual background",
                    "solid empirical or theoretical contribution",
                    "high impact authoritative reference",
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
                    return self._fallback_error_evaluation(f"HTTP {resp.status_code}: {resp.text[:100]}", threshold)

                data = resp.json()
                answers_dict = data.get("answers")
                if not isinstance(answers_dict, dict):
                    return self._fallback_error_evaluation("Respuesta sin campo 'answers'", threshold)

                relevance_prob = 0.5
                raw_rel = answers_dict.get("is_relevant")
                if isinstance(raw_rel, dict):
                    if raw_rel.get("type") == "choice":
                        raw_probs = raw_rel.get("probabilities")
                        if isinstance(raw_probs, dict):
                            raw_val = raw_probs.get("yes_relevant", 0.0)
                            if isinstance(raw_val, (int, float)):
                                relevance_prob = float(raw_val)
                    elif raw_rel.get("type") == "noul":
                        parsed_noul = LayaNoulResponse.model_validate(raw_rel)
                        relevance_prob = parsed_noul.noul

                evidence_choice = "theoretical"
                raw_choice = answers_dict.get("evidence_type")
                if isinstance(raw_choice, dict):
                    parsed_choice = LayaChoiceResponse.model_validate(raw_choice)
                    evidence_choice = parsed_choice.choice

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
                    "umbral_exigido": f"{threshold:.0%}",
                    "tipologia_clasificada": evidence_choice,
                    "rigor_metodologico": f"{rigor_score:.2f}/3.0",
                    "decision": "Conservar para Marco Teórico" if is_conserved else "Descartar",
                }

                reason = (
                    f"Decisión Laya: P(relevancia)={relevance_prob:.1%} (Umbral: {threshold:.0%}). "
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
                    decision_engine="unsloth_laya",
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
            verdict_reason=f"Error en Unsloth Laya: {err_msg}",
            rationale_breakdown={"error": err_msg},
            decision_engine="unsloth_laya",
        )
