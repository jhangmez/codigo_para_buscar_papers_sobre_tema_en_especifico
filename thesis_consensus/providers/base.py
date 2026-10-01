"""
Definición de interfaz base para proveedores de búsqueda académica.
"""

from abc import ABC, abstractmethod
from typing import List
from thesis_consensus.models import PaperMetadata


class BaseAcademicProvider(ABC):
    """Interfaz abstracta que deben implementar los proveedores de búsqueda de literatura."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del proveedor (p.ej: OpenAlex, Crossref)."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 15,
        min_year: int = 2012,
    ) -> List[PaperMetadata]:
        """
        Busca artículos científicos según la consulta dada.

        Args:
            query: Tema, pregunta de investigación o afirmación a buscar.
            limit: Número máximo de resultados a recuperar.
            min_year: Año mínimo de publicación para asegurar literatura actualizada.

        Returns:
            Lista de artículos estructurados como PaperMetadata.
        """
        pass
