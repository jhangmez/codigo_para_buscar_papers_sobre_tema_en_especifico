"""
Integración con el modelo de decisión Laya (Jev API) servido a través de Unsloth Desktop o CLI.
Documentación de referencia: https://unsloth.ai/docs/models/decision-laya
Endpoint: POST /v1/systemone
"""

import os
from typing import Dict, List, Optional
import httpx
from thesis_consensus.models import (
    PaperMetadata,
    DecisionEvaluation,
    LayaNoulResponse,
    LayaChoiceResponse,
    LayaScoreResponse,
)
from thesis_consensus.decision.protocol import BaseDecisionJudge


class UnslothLayaJudge(BaseDecisionJudge):
    """
    Evaluador de artículos científicos basado en el modelo de decisión Laya de Unsloth.
    Utiliza preguntas 'noul' (probabilidad sí/no), 'choice' (clasificación) y 'score' (calidad).
    """

    DEFAULT_BASE_URL = "http://localhost:8888/v1/systemone"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = "laya",
        relevance_threshold: float = 0.55,
        timeout_seconds: float = 12.0,
    ) -> None:
        raw_url = base_url if base_url is not None else os.getenv("UNSLOTH_API_URL")
        self._base_url: str = raw_url if raw_url else self.DEFAULT_BASE_URL
        self._api_key: str = api_key if api_key is not None else (os.getenv("UNSLOTH_API_KEY") or "")
        self._model_name: str = model_name
        self._relevance_threshold: float = relevance_threshold
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
            with httpx.Client(timeout=2.0) as client:
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
                # Debe responder 200 OK para considerarse activo
                return res.status_code == 200
        except Exception:
            return False

    def evaluate(self, paper: PaperMetadata, topic_or_claim: str) -> DecisionEvaluation:
        """
        Envía los metadatos y el resumen del paper a Unsloth Laya para tomar la decisión estructurada.
        """
        # Preparar el estado (texto de entrada para el modelo)
        abstract_snippet = paper.abstract[:1500] if paper.abstract else "(Sin resumen disponible, evaluar por título)"
        state_text = (
            f"Paper Title: {paper.title}\n"
            f"Venue/Journal: {paper.venue or 'Academic publication'}\n"
            f"Year: {paper.year or 'Recent'}\n"
            f"Abstract: {abstract_snippet}"
        )

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        # Definir las 3 preguntas clave según las capacidades de Laya
        questions_payload: Dict[str, object] = {
            "is_relevant": {
                "type": "noul",
                "instructions": (
                    f"Does this academic paper provide direct evidence, theoretical foundations, "
                    f"case studies, or empirical findings related to: '{topic_or_claim}'?"
                ),
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
                    "0: Low relevance or insufficient substance",
                    "1: Acceptable contextual background",
                    "2: Solid empirical or theoretical contribution",
                    "3: High impact, authoritative reference",
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
                    return self._fallback_error_evaluation(f"HTTP {resp.status_code}: {resp.text[:100]}")

                data = resp.json()
                answers_dict = data.get("answers")
                if not isinstance(answers_dict, dict):
                    return self._fallback_error_evaluation("Respuesta sin campo 'answers'")

                # 1. Parsear respuesta 'noul'
                relevance_prob = 0.5
                raw_noul = answers_dict.get("is_relevant")
                if isinstance(raw_noul, dict):
                    parsed_noul = LayaNoulResponse.model_validate(raw_noul)
                    relevance_prob = parsed_noul.noul

                # 2. Parsear respuesta 'choice'
                evidence_choice = "theoretical"
                raw_choice = answers_dict.get("evidence_type")
                if isinstance(raw_choice, dict):
                    parsed_choice = LayaChoiceResponse.model_validate(raw_choice)
                    evidence_choice = parsed_choice.choice

                # 3. Parsear respuesta 'score'
                rigor_score = 1.5
                raw_score = answers_dict.get("rigor_score")
                if isinstance(raw_score, dict):
                    parsed_score = LayaScoreResponse.model_validate(raw_score)
                    rigor_score = parsed_score.score

                # Decisión: Conservar si probabilidad >= umbral y no es irrelevante
                is_conserved = (relevance_prob >= self._relevance_threshold) and (evidence_choice != "irrelevant")

                reason = (
                    f"Laya Decision: P(relevancia)={relevance_prob:.2f}, "
                    f"Tipo={evidence_choice}, Rigor={rigor_score:.1f}/3.0. "
                    f"{'Aceptado para fundamentos teóricos' if is_conserved else 'Descartado por baja afinidad'}"
                )

                return DecisionEvaluation(
                    is_relevant=is_conserved,
                    relevance_score=relevance_prob,
                    evidence_type=evidence_choice,
                    quality_score=rigor_score,
                    verdict_reason=reason,
                    decision_engine="unsloth_laya",
                )

        except Exception as err:
            return self._fallback_error_evaluation(str(err))

    def _fallback_error_evaluation(self, err_msg: str) -> DecisionEvaluation:
        return DecisionEvaluation(
            is_relevant=False,
            relevance_score=0.0,
            evidence_type="irrelevant",
            quality_score=0.0,
            verdict_reason=f"Error en Unsloth Laya: {err_msg}",
            decision_engine="unsloth_laya",
        )
