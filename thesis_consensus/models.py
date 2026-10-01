"""
Modelos de datos con tipado estricto para el sistema Thesis Consensus.
Nota: Se evita el uso de Any a favor de tipos explícitos y uniones exhaustivas.
"""

from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field


class Author(BaseModel):
    """Representa un autor académico con nombre y apellidos estructurados."""
    full_name: str
    family_name: str
    given_name: str

    @classmethod
    def from_raw_name(cls, raw_name: str) -> "Author":
        """Convierte una cadena de texto de autor a la estructura Author."""
        import re
        cleaned = raw_name.strip()
        clean_no_symbols = re.sub(r"^[^\w]+|[^\w]+$", "", cleaned)
        if not clean_no_symbols:
            return cls(full_name="Anónimo", family_name="Anónimo", given_name="")

        # Si viene en formato "Apellido, Nombre"
        if "," in cleaned:
            parts = [p.strip() for p in cleaned.split(",", 1)]
            fam = re.sub(r"^[^\w]+|[^\w]+$", "", parts[0]) or "Anónimo"
            giv = re.sub(r"^[^\w]+|[^\w]+$", "", parts[1]) if len(parts) > 1 else ""
            return cls(
                full_name=f"{giv} {fam}".strip() if giv else fam,
                family_name=fam,
                given_name=giv,
            )

        # Si viene en formato "Nombre Apellido"
        tokens = [t for t in cleaned.split() if re.search(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]", t)]
        if not tokens:
            return cls(full_name="Anónimo", family_name="Anónimo", given_name="")
        if len(tokens) == 1:
            return cls(full_name=tokens[0], family_name=tokens[0], given_name="")
        return cls(
            full_name=" ".join(tokens),
            family_name=tokens[-1],
            given_name=" ".join(tokens[:-1]),
        )


class PaperMetadata(BaseModel):
    """Metadatos completos de un artículo de investigación."""
    paper_id: str
    title: str
    authors: List[Author]
    year: Optional[int] = None
    venue: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: str = ""
    citation_count: int = 0
    is_open_access: bool = False
    open_access_pdf_url: Optional[str] = None
    source_api: str = "openalex"


class LayaNoulResponse(BaseModel):
    """Respuesta tipo noul (probabilidad sí/no) del modelo de decisión Laya."""
    type: Literal["noul"] = "noul"
    noul: float


class LayaChoiceResponse(BaseModel):
    """Respuesta tipo elección del modelo de decisión Laya."""
    type: Literal["choice"] = "choice"
    choice: str
    confidence: float
    probabilities: Dict[str, float] = Field(default_factory=dict)


class LayaScoreResponse(BaseModel):
    """Respuesta tipo puntuación/escala del modelo de decisión Laya."""
    type: Literal["score"] = "score"
    score: float
    confidence: float
    probabilities: Dict[str, float] = Field(default_factory=dict)


class DecisionEvaluation(BaseModel):
    """Resultado estructurado de la evaluación del modelo de decisión."""
    is_relevant: bool
    relevance_score: float  # De 0.0 a 1.0 (probabilidad calibrada)
    threshold_applied: float = 0.80  # Umbral exigido (80% u 85%)
    evidence_type: str      # p.ej: "case_study", "survey_or_data", "theoretical", "irrelevant"
    quality_score: float    # Escala de rigor metodológico (p.ej. 0 a 3)
    verdict_reason: str     # Explicación resumida
    rationale_breakdown: Dict[str, str] = Field(default_factory=dict)  # Detalles para la tarjeta de decisión
    decision_engine: Literal["unsloth_laya", "openai_compatible", "heuristic_academic"]


class Apa7Citation(BaseModel):
    """Estructuras de citación y referenciación en formato APA 7ma Edición."""
    narrative_citation: str       # p.ej: "Según Gómez et al. (2020)..."
    parenthetical_citation: str   # p.ej: "(Gómez et al., 2020)"
    full_reference: str           # Referencia completa para la lista final
    bibtex_entry: str


class ThesisEvidenceItem(BaseModel):
    """Elemento final procesado y fundamentado para la sección de Fundamentos Teóricos."""
    paper: PaperMetadata
    decision: DecisionEvaluation
    apa7: Apa7Citation
    key_findings_es: str          # Hallazgo o evidencia clave traducido y sintetizado al español
    narrative_paragraph: str      # Párrafo individual redactado en español


class MultiPaperSynthesis(BaseModel):
    """Síntesis teórica integrada que combina múltiples autores en párrafos coherentes."""
    topic_or_claim: str
    integrated_narrative: str     # Párrafo dialéctico conectando varios autores (Según X... mientras que Y...)
    complementary_narrative: str  # Párrafo acumulativo de evidencia
    parenthetical_synthesis: str  # Afirmación con citas parentéticas agrupadas: (A, 2020; B, 2022)
    papers_used_count: int
    consensus_verdict: str        # Conclusión teórica sobre si la literatura apoya o refuta la afirmación


class TopicResearchBatch(BaseModel):
    """Resultados consolidados de una o múltiples preguntas procesadas en lote."""
    topics: List[str]
    conserved_by_topic: Dict[str, List[ThesisEvidenceItem]]
    discarded_by_topic: Dict[str, List[PaperMetadata]]
    syntheses_by_topic: Dict[str, MultiPaperSynthesis]
    all_conserved_items: List[ThesisEvidenceItem]
