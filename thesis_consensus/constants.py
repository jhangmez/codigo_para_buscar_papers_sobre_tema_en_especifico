"""
Constantes centrales para el sistema Thesis Consensus.
Centraliza configuraciones de red, umbrales de decisión, reglas lingüísticas y plantillas.
"""

from typing import Tuple, Dict

# ==============================================================================
# CONFIGURACIÓN DE IDIOMA Y LOCALIZACIÓN
# ==============================================================================
DEFAULT_LANGUAGE: str = "es"

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
# ARCHIVOS Y RUTAS POR DEFECTO
# ==============================================================================
DEFAULT_OUTPUT_MD: str = "fundamentos_teoricos_tesis.md"
DEFAULT_OUTPUT_BIB: str = "referencias_tesis.bib"
DEFAULT_OUTPUT_JSON: str = "tesis_consenso.json"

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
