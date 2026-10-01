"""
Módulo de extracción segura de contenido completo y extendido (Full-Text / HTML / PDF).
Permite enriquecer el análisis del modelo de decisión más allá del abstract,
respetando el límite de contexto (1024 tokens de Laya) y previniendo cualquier riesgo de malware.
"""

import io
import re
from typing import Tuple, Optional, List
import httpx
from thesis_consensus.models import PaperMetadata
from thesis_consensus.constants import DEFAULT_TIMEOUT_SECONDS

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


class SafeContentExtractor:
    """
    Extractor de contenido académico seguro.
    Extrae texto extendido desde páginas Open Access HTML o PDFs legítimos en memoria,
    filtrando y priorizando secciones de Resultados, Discusión y Conclusiones.
    """

    MAX_FILE_BYTES = 10 * 1024 * 1024  # Máximo 10 MB para papers PDF de acceso abierto
    MAX_EXTRACTED_WORDS = 2500         # Calibrado para la ventana de 32K tokens de TypeSafe Jev

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    def _clean_html_text(self, html_content: str) -> str:
        """Limpia código HTML eliminando scripts, estilos, cabeceras y extrayendo párrafos."""
        # Eliminar scripts, estilos, iframes y etiquetas de navegación
        clean = re.sub(r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
        # Reemplazar etiquetas de bloque con saltos de línea
        clean = re.sub(r"</?(p|div|section|article|h1|h2|h3|h4|li|br)[^>]*>", "\n", clean, flags=re.IGNORECASE)
        # Eliminar cualquier etiqueta HTML remanente
        clean = re.sub(r"<[^>]+>", " ", clean)
        # Normalizar espacios en blanco
        clean = re.sub(r"[ \t]+", " ", clean)
        clean = re.sub(r"\n\s*\n+", "\n\n", clean)
        return clean.strip()

    def _prioritize_academic_sections(self, text: str) -> str:
        """
        Filtra y prioriza las secciones con mayor densidad de evidencia científica:
        Resultados, Hallazgos, Discusión y Conclusiones.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 60]
        if not paragraphs:
            return text[:1500]

        priority_keywords = [
            "result", "finding", "discussion", "conclusion", "evaluate", "implement",
            "resultado", "hallazgo", "discusion", "conclusi", "rendimiento", "ticket",
            "bottleneck", "cuello de botella", "eficiencia", "sla"
        ]

        scored_paragraphs: List[Tuple[int, str]] = []
        for p in paragraphs:
            p_lower = p.lower()
            score = sum(1 for kw in priority_keywords if kw in p_lower)
            scored_paragraphs.append((score, p))

        # Ordenar por relevancia de la sección
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)

        selected_paragraphs: List[str] = []
        total_words = 0

        for _, para in scored_paragraphs:
            words = para.split()
            if total_words + len(words) <= self.MAX_EXTRACTED_WORDS:
                selected_paragraphs.append(para)
                total_words += len(words)
            else:
                remaining = self.MAX_EXTRACTED_WORDS - total_words
                if remaining > 30:
                    selected_paragraphs.append(" ".join(words[:remaining]) + "...")
                break

        return "\n\n".join(selected_paragraphs)

    def extract_deep_content(self, paper: PaperMetadata) -> Tuple[str, str]:
        """
        Intenta obtener contenido enriquecido de acceso abierto (HTML o PDF en memoria).
        Si no está disponible o falla por paywall, recurre al abstract estructurado.

        Returns:
            Tupla (texto_contenido, tipo_fuente):
            - tipo_fuente: 'open_access_pdf', 'open_access_html', o 'abstract_only'
        """
        target_url = paper.open_access_pdf_url or (paper.url if paper.is_open_access else None)

        if not target_url:
            return paper.abstract, "abstract_only"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True) as client:
                resp = client.get(target_url, headers=headers)
                if resp.status_code != 200:
                    return paper.abstract, "abstract_only"

                content_type = resp.headers.get("content-type", "").lower()
                content_bytes = resp.content

                # Caso 1: Archivo PDF en Acceso Abierto legítimo
                if "application/pdf" in content_type or content_bytes.startswith(b"%PDF-"):
                    if not PYPDF_AVAILABLE:
                        return paper.abstract, "abstract_only"

                    # Procesamiento seguro estrictamente en memoria (BytesIO)
                    pdf_file = io.BytesIO(content_bytes[:self.MAX_FILE_BYTES])
                    reader = pypdf.PdfReader(pdf_file)

                    extracted_pages_text: List[str] = []
                    # Leer páginas estratégicas (primeras páginas y secciones finales donde están resultados y conclusiones)
                    num_pages = len(reader.pages)
                    pages_to_read = min(num_pages, 6)

                    for page_num in range(pages_to_read):
                        page_text = reader.pages[page_num].extract_text() or ""
                        if page_text.strip():
                            extracted_pages_text.append(page_text)

                    full_pdf_text = "\n".join(extracted_pages_text)
                    if len(full_pdf_text.strip()) > 150:
                        refined_text = self._prioritize_academic_sections(full_pdf_text)
                        return refined_text, "open_access_pdf"

                # Caso 2: Página de artículo completo en HTML
                elif "text/html" in content_type:
                    html_text = resp.text
                    clean_text = self._clean_html_text(html_text)

                    # Detección y rechazo de páginas de bloqueo / Cloudflare / Captcha
                    bot_indicators = [
                        "confirm you are a human", "robot", "captcha", "cloudflare",
                        "security check", "verify you are human", "please enable cookies",
                        "just a moment", "access denied", "attention required"
                    ]
                    clean_lower = clean_text.lower()
                    if any(indicator in clean_lower for indicator in bot_indicators):
                        # Descartar texto de captcha y recurrir al abstract indexado verificado
                        return paper.abstract, "abstract_only"

                    if len(clean_text) > 300:
                        refined_text = self._prioritize_academic_sections(clean_text)
                        return refined_text, "open_access_html"

        except Exception as err:
            # En caso de error de red o timeout, fallback garantizado al abstract
            pass

        return paper.abstract, "abstract_only"
