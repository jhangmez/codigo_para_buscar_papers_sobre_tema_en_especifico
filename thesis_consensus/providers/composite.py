"""
Proveedor compuesto que combina múltiples fuentes bibliográficas (OpenAlex y Crossref)
eliminando duplicados por DOI y por similitud de título.
"""

from typing import List, Set
from thesis_consensus.models import PaperMetadata
from thesis_consensus.providers.base import BaseAcademicProvider
from thesis_consensus.providers.openalex import OpenAlexProvider
from thesis_consensus.providers.crossref import CrossrefProvider


class CompositeAcademicProvider(BaseAcademicProvider):
    """
    Busca simultáneamente en OpenAlex y Crossref para obtener la mayor cobertura
    de literatura científica arbitrada y DOI oficiales sin riesgos de malware.
    """

    def __init__(self, providers: List[BaseAcademicProvider] = []) -> None:
        self._providers = providers or [OpenAlexProvider(), CrossrefProvider()]

    @property
    def name(self) -> str:
        return "Composite (OpenAlex + Crossref)"

    def search(
        self,
        query: str,
        limit: int = 15,
        min_year: int = 2012,
    ) -> List[PaperMetadata]:
        all_papers: List[PaperMetadata] = []
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()

        # Distribuir límite equitativamente
        per_provider_limit = max(limit // len(self._providers), 5)

        for provider in self._providers:
            try:
                results = provider.search(query=query, limit=per_provider_limit, min_year=min_year)
                for paper in results:
                    clean_title = paper.title.strip().lower()
                    clean_doi = paper.doi.strip().lower() if paper.doi else ""

                    if clean_doi and clean_doi in seen_dois:
                        continue
                    if clean_title and clean_title in seen_titles:
                        continue

                    if clean_doi:
                        seen_dois.add(clean_doi)
                    if clean_title:
                        seen_titles.add(clean_title)

                    all_papers.append(paper)
            except Exception as err:
                print(f"[{provider.name} Search Error]: {err}")

        # Ordenar por conteo de citas descendente
        all_papers.sort(key=lambda p: p.citation_count, reverse=True)
        return all_papers[:limit]
