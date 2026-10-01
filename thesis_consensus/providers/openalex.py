"""
Proveedor de búsqueda para OpenAlex (https://openalex.org).
OpenAlex contiene más de 250 millones de obras científicas con metadatos completos,
índices de citas y resúmenes estructurados, sin necesidad de descargar PDFs inseguros.
"""

from typing import List, Optional, Dict
import httpx
from thesis_consensus.models import Author, PaperMetadata
from thesis_consensus.providers.base import BaseAcademicProvider
from thesis_consensus.constants import (
    OPENALEX_BASE_URL,
    DEFAULT_USER_EMAIL,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_MIN_PUBLICATION_YEAR,
    STOPWORDS_EN,
    STOPWORDS_ES,
)


class OpenAlexProvider(BaseAcademicProvider):
    """
    Proveedor para la API REST pública de OpenAlex.
    Utiliza el 'polite pool' de OpenAlex especificando cabeceras de cortesía.
    """

    BASE_URL = OPENALEX_BASE_URL

    def __init__(
        self,
        email: str = DEFAULT_USER_EMAIL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._email = email
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "OpenAlex"

    def _reconstruct_abstract(self, inverted_index: Optional[Dict[str, List[int]]]) -> str:
        """
        Reconstruye el texto original del resumen (abstract) a partir del
        índice invertido devuelto por OpenAlex de forma segura y eficiente.
        """
        if not inverted_index:
            return ""

        # Encontrar la longitud máxima
        max_idx = -1
        for positions in inverted_index.values():
            for pos in positions:
                if pos > max_idx:
                    max_idx = pos

        if max_idx < 0:
            return ""

        # Crear arreglo de palabras y llenarlo
        words_array: List[str] = ["" for _ in range(max_idx + 1)]
        for word, positions in inverted_index.items():
            for pos in positions:
                if 0 <= pos <= max_idx:
                    words_array[pos] = word

        return " ".join(words_array).strip()

    @staticmethod
    def _clean_query_terms(query: str) -> str:
        """
        Limpia la consulta eliminando palabras interrogativas y conectores
        para maximizar la precisión de búsqueda en el motor de OpenAlex.
        """
        import re
        stopwords = set(STOPWORDS_EN).union(set(STOPWORDS_ES))
        cleaned = re.sub(r"[^\w\s-]", " ", query)
        words = [w for w in cleaned.split() if w.lower() not in stopwords]
        # Conservar los términos más significativos
        return " ".join(words[:10])

    def search(
        self,
        query: str,
        limit: int = 15,
        min_year: int = 2012,
    ) -> List[PaperMetadata]:
        """
        Ejecuta la búsqueda en OpenAlex filtrando por año y ordenando por relevancia/citas.
        """
        headers: Dict[str, str] = {
            "User-Agent": f"ThesisConsensus/1.0 (mailto:{self._email})",
            "Accept": "application/json",
        }

        # Filtros: desde min_year hasta el presente, excluyendo retracciones
        filter_param = f"from_publication_date:{min_year}-01-01,is_retracted:false"
        clean_search = self._clean_query_terms(query)

        params: Dict[str, str] = {
            "search": clean_search,
            "filter": filter_param,
            "per_page": str(min(limit, 50)),
            "sort": "relevance_score:desc",
        }

        papers: List[PaperMetadata] = []

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(self.BASE_URL, headers=headers, params=params)
                if response.status_code != 200:
                    return papers

                data = response.json()
                results: List[Dict[str, object]] = data.get("results", [])

                # Si no hubo resultados con la consulta completa, intentar una versión más compacta
                if not results:
                    compact_terms = " ".join([w for w in clean_search.split() if len(w) > 3][:5])
                    if compact_terms != clean_search:
                        params["search"] = compact_terms
                        fallback_resp = client.get(self.BASE_URL, headers=headers, params=params)
                        if fallback_resp.status_code == 200:
                            results = fallback_resp.json().get("results", [])

                for item in results:
                    # Extraer ID y título
                    raw_id = str(item.get("id", ""))
                    title = str(item.get("title") or "").strip()
                    if not title:
                        continue

                    # Extraer año
                    raw_year = item.get("publication_year")
                    year: Optional[int] = int(raw_year) if isinstance(raw_year, (int, str)) and str(raw_year).isdigit() else None

                    # Extraer autores
                    authors: List[Author] = []
                    raw_authorships = item.get("authorships")
                    if isinstance(raw_authorships, list):
                        for authorship in raw_authorships:
                            if isinstance(authorship, dict):
                                author_data = authorship.get("author")
                                if isinstance(author_data, dict):
                                    display_name = str(author_data.get("display_name", "")).strip()
                                    if display_name:
                                        authors.append(Author.from_raw_name(display_name))

                    # Reconstruir abstract
                    raw_inverted_index = item.get("abstract_inverted_index")
                    abstract = ""
                    if isinstance(raw_inverted_index, dict):
                        # Validación segura de tipos para el índice invertido
                        clean_inverted: Dict[str, List[int]] = {}
                        for word, positions in raw_inverted_index.items():
                            if isinstance(word, str) and isinstance(positions, list):
                                valid_positions = [p for p in positions if isinstance(p, int)]
                                clean_inverted[word] = valid_positions
                        abstract = self._reconstruct_abstract(clean_inverted)

                    # Si el paper no tiene abstract en OpenAlex, revisamos si tiene descripción
                    if not abstract:
                        raw_desc = item.get("description")
                        if isinstance(raw_desc, str):
                            abstract = raw_desc.strip()

                    # Extraer datos de la revista / congreso
                    venue: Optional[str] = None
                    raw_loc = item.get("primary_location")
                    if isinstance(raw_loc, dict):
                        source_dict = raw_loc.get("source")
                        if isinstance(source_dict, dict):
                            venue_name = source_dict.get("display_name")
                            if isinstance(venue_name, str):
                                venue = venue_name

                    # Extraer volumen, número y páginas
                    volume: Optional[str] = None
                    issue: Optional[str] = None
                    pages: Optional[str] = None
                    raw_biblio = item.get("biblio")
                    if isinstance(raw_biblio, dict):
                        raw_vol = raw_biblio.get("volume")
                        if isinstance(raw_vol, str):
                            volume = raw_vol
                        raw_iss = raw_biblio.get("issue")
                        if isinstance(raw_iss, str):
                            issue = raw_iss
                        first_page = raw_biblio.get("first_page")
                        last_page = raw_biblio.get("last_page")
                        if isinstance(first_page, str) and isinstance(last_page, str):
                            pages = f"{first_page}–{last_page}"
                        elif isinstance(first_page, str):
                            pages = first_page

                    # Extraer DOI y URL
                    doi: Optional[str] = None
                    raw_doi = item.get("doi")
                    if isinstance(raw_doi, str) and raw_doi.strip():
                        doi = raw_doi.strip()

                    url: Optional[str] = None
                    if doi:
                        url = doi
                    elif isinstance(raw_id, str):
                        url = raw_id

                    # Citas
                    raw_cites = item.get("cited_by_count")
                    citation_count: int = int(raw_cites) if isinstance(raw_cites, int) else 0

                    # Acceso abierto
                    is_oa = False
                    oa_url: Optional[str] = None
                    raw_oa = item.get("open_access")
                    if isinstance(raw_oa, dict):
                        is_oa = bool(raw_oa.get("is_oa", False))
                        raw_oa_url = raw_oa.get("oa_url")
                        if isinstance(raw_oa_url, str):
                            oa_url = raw_oa_url

                    papers.append(
                        PaperMetadata(
                            paper_id=raw_id,
                            title=title,
                            authors=authors,
                            year=year,
                            venue=venue,
                            volume=volume,
                            issue=issue,
                            pages=pages,
                            doi=doi,
                            url=url,
                            abstract=abstract,
                            citation_count=citation_count,
                            is_open_access=is_oa,
                            open_access_pdf_url=oa_url,
                            source_api="openalex",
                        )
                    )

        except Exception as err:
            # En caso de error de red o timeout, retornar los que se hayan procesado
            print(f"[OpenAlex Error]: {err}")
            return papers

        return papers
