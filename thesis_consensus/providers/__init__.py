"""
Módulo de proveedores de búsqueda bibliográfica.
"""

from thesis_consensus.providers.base import BaseAcademicProvider
from thesis_consensus.providers.openalex import OpenAlexProvider
from thesis_consensus.providers.crossref import CrossrefProvider
from thesis_consensus.providers.composite import CompositeAcademicProvider

__all__ = [
    "BaseAcademicProvider",
    "OpenAlexProvider",
    "CrossrefProvider",
    "CompositeAcademicProvider",
]
