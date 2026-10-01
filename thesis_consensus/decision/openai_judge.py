"""
Evaluador de decisiones compatible con la API de OpenAI / Ollama / vLLM / LM Studio.
Permite utilizar modelos locales (vía Ollama o vLLM) o en la nube para calificar papers.
"""

import os
import json
from typing import Dict, Optional, Literal
import httpx
from thesis_consensus.models import PaperMetadata, DecisionEvaluation
from thesis_consensus.decision.protocol import BaseDecisionJudge


class OpenAILikeJudge(BaseDecisionJudge):
    """Evaluador que utiliza completions JSON de endpoints compatibles con OpenAI."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        raw_url = base_url if base_url is not None else os.getenv("OPENAI_BASE_URL")
        self._base_url: str = (raw_url or "http://localhost:11434/v1").rstrip("/")
        self._api_key: str = api_key if api_key is not None else (os.getenv("OPENAI_API_KEY") or "ollama")
        self._model_name: str = model_name if model_name is not None else (os.getenv("LLM_MODEL_NAME") or "llama3.2")
        self._timeout_seconds: float = timeout_seconds

    @property
    def engine_name(self) -> str:
        return "openai_compatible"

    def is_available(self) -> bool:
        """Comprueba conectividad con el endpoint de modelos."""
        try:
            url = f"{self._base_url}/models"
            headers: Dict[str, str] = {"Authorization": f"Bearer {self._api_key}"}
            with httpx.Client(timeout=2.0) as client:
                res = client.get(url, headers=headers)
                return res.status_code == 200
        except Exception:
            return False

    def evaluate(self, paper: PaperMetadata, topic_or_claim: str) -> DecisionEvaluation:
        """Pide al modelo evaluar la pertinencia del artículo y responder en formato JSON."""
        system_prompt = (
            "Eres un evaluador académico riguroso para tesis de pregrado y posgrado. "
            "Tu tarea es analizar el título y resumen de un artículo científico y determinar "
            "si aporta fundamentos teóricos o evidencia empírica directa al tema especificado. "
            "Debes responder EXCLUSIVAMENTE con un objeto JSON válido con los campos: "
            "'is_relevant' (booleano), 'relevance_score' (flotante de 0.0 a 1.0), "
            "'evidence_type' ('case_study', 'survey_or_data', 'theoretical' o 'irrelevant'), "
            "'quality_score' (flotante de 0.0 a 3.0), y 'reason' (cadena explicativa breve)."
        )

        user_content = (
            f"TEMA / AFIRMACIÓN DE LA TESIS: {topic_or_claim}\n\n"
            f"DATOS DEL PAPER:\n"
            f"- Título: {paper.title}\n"
            f"- Año: {paper.year or 'N/A'}\n"
            f"- Publicación: {paper.venue or 'N/A'}\n"
            f"- Resumen: {paper.abstract[:1200] if paper.abstract else 'Sin resumen'}\n"
        )

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        body: Dict[str, object] = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                resp = client.post(f"{self._base_url}/chat/completions", headers=headers, json=body)
                if resp.status_code != 200:
                    return self._fallback_error(f"HTTP {resp.status_code}: {resp.text[:100]}")

                data = resp.json()
                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    return self._fallback_error("Sin respuestas del LLM")

                first_choice = choices[0]
                if not isinstance(first_choice, dict):
                    return self._fallback_error("Formato inesperado de choice")

                message = first_choice.get("message")
                if not isinstance(message, dict):
                    return self._fallback_error("Formato inesperado de message")

                content = message.get("content")
                if not isinstance(content, str):
                    return self._fallback_error("Contenido no es texto")

                parsed = json.loads(content)
                is_rel = bool(parsed.get("is_relevant", False))
                rel_score = float(parsed.get("relevance_score", 0.0))
                ev_type = str(parsed.get("evidence_type", "theoretical"))
                q_score = float(parsed.get("quality_score", 1.0))
                reason = str(parsed.get("reason", "Evaluación completada por LLM"))

                return DecisionEvaluation(
                    is_relevant=is_rel and ev_type != "irrelevant",
                    relevance_score=rel_score,
                    evidence_type=ev_type,
                    quality_score=q_score,
                    verdict_reason=reason,
                    decision_engine="openai_compatible",
                )

        except Exception as err:
            return self._fallback_error(str(err))

    def _fallback_error(self, err_msg: str) -> DecisionEvaluation:
        return DecisionEvaluation(
            is_relevant=False,
            relevance_score=0.0,
            evidence_type="irrelevant",
            quality_score=0.0,
            verdict_reason=f"Fallo en evaluación LLM: {err_msg}",
            decision_engine="openai_compatible",
        )
