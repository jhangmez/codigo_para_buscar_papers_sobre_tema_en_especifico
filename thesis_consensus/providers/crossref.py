"""
Proveedor de búsqueda para Crossref (https://api.crossref.org).
Ofrece metadatos de publicaciones científicas registradas oficialmente con DOI.
"""

from typing import List, Optional, Dict
import httpx
from thesis_consensus.models import Author, PaperMetadata
from thesis_consensus.providers.base import BaseAcademicProvider


class CrossrefProvider(BaseAcademicProvider):
    """Proveedor para la API REST de Crossref."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: str = "thesis_researcher@university.edu", timeout_seconds: float = 15.0) -> None:
        self._email = email
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "Crossref"

    def search(
        self,
        query: str,
        limit: int = 10,
        min_year: int = 2012,
    ) -> List[PaperMetadata]:
        """Busca artículos en Crossref mediante query bibliográfica."""
        headers: Dict[str, str] = {
            "User-Agent": f"ThesisConsensus/1.0 (mailto:{self._email})",
            "Accept": "application/json",
        }

        params: Dict[str, str] = {
            "query": query,
            "rows": str(limit),
            "filter": f"from-pub-date:{min_year}-01-01",
            "sort": "relevance",
            "order": "desc",
        }

        papers: List[PaperMetadata] = []

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(self.BASE_URL, headers=headers, params=params)
                if response.status_code != 200:
                    return papers

                data = response.json()
                message_dict = data.get("message")
                if not isinstance(message_dict, dict):
                    return papers

                items = message_dict.get("items")
                if not isinstance(items, list):
                    return papers

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    # Título
                    raw_title_list = item.get("title")
                    title = ""
                    if isinstance(raw_title_list, list) and raw_title_list:
                        title = str(raw_title_list[0]).strip()
                    if not title:
                        continue

                    # DOI
                    doi_raw = item.get("DOI")
                    doi: Optional[str] = f"https://doi.org/{doi_raw}" if isinstance(doi_raw, str) else None

                    # Año
                    year: Optional[int] = None
                    issued = item.get("issued")
                    if isinstance(issued, dict):
                        date_parts = issued.get("date-parts")
                        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
                            first_part = date_parts[0]
                            if first_part and isinstance(first_part[0], int):
                                year = first_part[0]

                    # Autores
                    authors: List[Author] = []
                    raw_author_list = item.get("author")
                    if isinstance(raw_author_list, list):
                        for a in raw_author_list:
                            if isinstance(a, dict):
                                family = str(a.get("family", "")).strip()
                                given = str(a.get("given", "")).strip()
                                import re
                                clean_fam = re.sub(r"^[^\w]+|[^\w]+$", "", family)
                                if clean_fam and re.search(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]", clean_fam):
                                    clean_giv = re.sub(r"^[^\w]+|[^\w]+$", "", given)
                                    full = f"{clean_giv} {clean_fam}".strip() if clean_giv else clean_fam
                                    authors.append(Author(full_name=full, family_name=clean_fam, given_name=clean_giv))

                    # Venue / Revista
                    venue: Optional[str] = None
                    container_title = item.get("container-title")
                    if isinstance(container_title, list) and container_title:
                        venue = str(container_title[0]).strip()

                    # Abstract (Crossref a veces incluye tag JATS <jats:p>...</jats:p>)
                    raw_abstract = item.get("abstract")
                    abstract = ""
                    if isinstance(raw_abstract, str):
                        # Limpiar tags XML simples
                        import re
                        abstract = re.sub(r"<[^>]+>", "", raw_abstract).strip()

                    # Citas
                    raw_cites = item.get("is-referenced-by-count")
                    citation_count: int = int(raw_cites) if isinstance(raw_cites, int) else 0

                    volume = str(item.get("volume")) if item.get("volume") is not None else None
                    issue = str(item.get("issue")) if item.get("issue") is not None else None
                    pages = str(item.get("page")) if item.get("page") is not None else None

                    papers.append(
                        PaperMetadata(
                            paper_id=doi or title,
                            title=title,
                            authors=authors,
                            year=year,
                            venue=venue,
                            volume=volume,
                            issue=issue,
                            pages=pages,
                            doi=doi,
                            url=doi,
                            abstract=abstract,
                            citation_count=citation_count,
                            is_open_access=False,
                            open_access_pdf_url=None,
                            source_api="crossref",
                        )
                    )

        except Exception as err:
            print(f"[Crossref Error]: {err}")
            return papers

        return papers
