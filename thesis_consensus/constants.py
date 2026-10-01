"""
Constantes centrales para el sistema Thesis Consensus.
Centraliza configuraciones de red, umbrales de decisión, reglas lingüísticas y plantillas.
"""

import os
from pathlib import Path
from typing import Tuple, Dict


def _load_env_file(filepath: str = ".env") -> None:
    """Carga variables desde .env a os.environ si no existen en el entorno."""
    p = Path(filepath)
    if not p.is_file():
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, v = stripped.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


_load_env_file()

# ==============================================================================
# CONFIGURACIÓN DE IDIOMA Y MOTOR DE DECISIÓN POR DEFECTO
# ==============================================================================
DEFAULT_LANGUAGE: str = "es"
DEFAULT_DECISION_ENGINE: str = "unsloth_laya"

# ==============================================================================
# UMBRALES DEL MODELO DE DECISIÓN (Alta exigencia para tesis)
# ==============================================================================
# Umbral mínimo de afinidad/probabilidad para conservar un artículo (80% - 85%)
DEFAULT_RELEVANCE_THRESHOLD: float = 0.80
STRICT_RELEVANCE_THRESHOLD: float = 0.85
MINIMUM_RIGOR_SCORE: float = 1.6  # Escala de 0.0 a 3.0

# ==============================================================================
# ENDPOINTS Y SERVICIOS EXTERNOS
# ==============================================================================
OPENALEX_BASE_URL: str = "https://api.openalex.org/works"
CROSSREF_BASE_URL: str = "https://api.crossref.org/works"
UNSLOTH_DEFAULT_URL: str = "http://localhost:8888/v1/systemone"
OPENAI_DEFAULT_URL: str = "http://localhost:11434/v1"

DEFAULT_USER_EMAIL: str = "thesis_researcher@university.edu"
DEFAULT_DECISION_MODEL: str = "laya"
DEFAULT_TIMEOUT_SECONDS: float = 15.0

# ==============================================================================
# PARÁMETROS DE BÚSQUEDA BIBLIOGRÁFICA
# ==============================================================================
DEFAULT_SEARCH_LIMIT: int = 15
DEFAULT_MIN_PUBLICATION_YEAR: int = 2015

# ==============================================================================
# ARCHIVOS Y RUTAS POR DEFECTO (Organización en carpetas)
# ==============================================================================
DEFAULT_OUTPUT_DIR: str = "outputs"
DEFAULT_OUTPUT_MD: str = "outputs/fundamentos_teoricos_tesis.md"
DEFAULT_OUTPUT_BIB: str = "outputs/referencias_tesis.bib"
DEFAULT_OUTPUT_JSON: str = "outputs/evidencia_academica.json"

# ==============================================================================
# ETIQUETAS DESCRIPTIVAS EN ESPAÑOL PARA EL MARCO TEÓRICO
# ==============================================================================
EVIDENCE_TYPE_NAMES: Dict[str, str] = {
    "case_study": "Estudio de Caso Real (Universidad / Mesa de Ayuda)",
    "survey_or_data": "Estudio Cuantitativo (Datos de Tickets / Métricas)",
    "theoretical": "Marco Teórico / Conceptual (Normas y Mejores Prácticas)",
    "irrelevant": "No Relevante / Fuera de foco",
}

DECISION_ENGINE_NAMES: Dict[str, str] = {
    "unsloth_laya": "Modelo de Decisión Neuronal (Unsloth Laya / Jev API)",
    "openai_compatible": "Modelo LLM Generativo (OpenAI / Ollama)",
    "heuristic_academic": "Evaluador Semántico de Facetas Académicas",
}

# ==============================================================================
# LÉXICO ACADÉMICO, ACRÓNIMOS Y STOPWORDS
# ==============================================================================
ACADEMIC_ACRONYMS: Tuple[str, ...] = (
    "itil", "itsm", "it", "ai", "ict", "sla", "kpi", "api", "erp",
    "iso", "ieee", "acm", "cio", "cto", "nlp", "llm", "usa", "uk"
)

STOPWORDS_ES: Tuple[str, ...] = (
    "de", "la", "el", "en", "un", "una", "los", "las", "por", "para", "con",
    "sobre", "entre", "qué", "que", "cómo", "como", "cuáles", "cuales",
    "es", "son", "fue", "fueron", "ser", "estar", "tiene", "tienen"
)

STOPWORDS_EN: Tuple[str, ...] = (
    "the", "a", "an", "and", "or", "in", "on", "at", "for", "with", "by",
    "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "how", "what", "which", "who", "when", "where", "why",
    "can", "could", "should", "would"
)

# Diccionario de traducción académica de términos clave inglés -> español
ACADEMIC_TRANSLATIONS: Dict[str, str] = {
    "higher education": "educación superior",
    "higher education institutions": "instituciones de educación superior",
    "university": "universidad",
    "universities": "universidades",
    "help desk": "mesa de ayuda",
    "service desk": "centro de servicios",
    "it service management": "gestión de servicios de TI (ITSM)",
    "information technology": "tecnologías de la información",
    "incident management": "gestión de incidentes",
    "bottlenecks": "cuellos de botella",
    "bottleneck": "cuello de botella",
    "ticket volume": "volumen de tickets",
    "ticket overloads": "sobrecarga de tickets",
    "tickets": "tickets",
    "case study": "estudio de caso",
    "results show": "los resultados evidencian",
    "results demonstrate": "los resultados demuestran",
    "the study found": "el estudio identificó",
    "we found that": "se determinó que",
    "we conclude that": "se concluye que",
    "findings indicate": "los hallazgos indican",
    "maturity level": "nivel de madurez",
    "best practices": "mejores prácticas",
    "workflow automation": "automatización de flujos de trabajo",
    "satisfaction": "satisfacción",
}
