"""
Generador de citas y referencias según las normas APA 7ma Edición (American Psychological Association, 7th ed.).
Incluye soporte para:
- Citas narrativas en texto (p. ej. "Según Adán et al. (2017)...")
- Citas parentéticas (p. ej. "(Adán et al., 2017)")
- Referencias bibliográficas completas para la lista final con mayúsculas/minúsculas correctas (Sentence case)
- Generación de BibTeX
"""

import re
from typing import List, Literal, Tuple
from thesis_consensus.models import Author, PaperMetadata, Apa7Citation
from thesis_consensus.constants import ACADEMIC_ACRONYMS, DEFAULT_LANGUAGE


def _to_sentence_case(title: str) -> str:
    """
    Convierte el título de un artículo al formato 'Sentence case' requerido por APA 7:
    Solo la primera letra del título y la primera letra después de dos puntos o guion
    van en mayúscula, preservando acrónimos reconocidos (ITIL, ITSM, IT, AI, etc.).
    """
    if not title:
        return ""

    known_acronyms = set(ACADEMIC_ACRONYMS)

    # Dividir por oraciones o subtítulos (después de ':' o '-')
    subparts = re.split(r"(: |- )", title)
    capitalized_subparts: List[str] = []

    for part in subparts:
        if part in (": ", "- "):
            capitalized_subparts.append(part)
            continue

        words = part.split()
        if not words:
            continue

        formatted_words: List[str] = []
        for i, word in enumerate(words):
            # Limpiar puntuación para comparar acrónimo
            clean_word = re.sub(r"[^\w]", "", word).lower()
            if clean_word in known_acronyms:
                # Mantener acrónimo en mayúsculas
                formatted_words.append(word.upper())
            elif i == 0:
                # Primera palabra del título o subtítulo en mayúscula inicial
                formatted_words.append(word.capitalize())
            else:
                # Si era una palabra con mayúsculas mezcladas (como ITIL-based), manejarlo
                if any(c.isupper() for c in word[1:]) and clean_word not in known_acronyms:
                    formatted_words.append(word.lower())
                else:
                    formatted_words.append(word.lower())

        capitalized_subparts.append(" ".join(formatted_words))

    return "".join(capitalized_subparts)


def _format_author_initials(given_name: str) -> str:
    """Extrae las iniciales del nombre de pila: 'John Doe' -> 'J. D.'"""
    if not given_name:
        return ""
    parts = given_name.replace("-", " ").split()
    initials: List[str] = [f"{p[0].upper()}." for p in parts if p]
    return " ".join(initials)


def format_in_text_citations(
    authors: List[Author],
    year: str,
    language: Literal["es", "en"] = "es"
) -> Tuple[str, str]:
    """
    Genera la cita narrativa y parentética según APA 7ma Edición.
    Regla APA 7:
    - 1 autor: Apellido (Año) / (Apellido, Año)
    - 2 autores: Apellido1 y Apellido2 (Año) / (Apellido1 & Apellido2, Año)
    - 3 o más autores: Apellido1 et al. (Año) / (Apellido1 et al., Año) desde la PRIMERA cita.
    """
    and_connector = "y" if language == "es" else "&"

    if not authors:
        narrative = f"Anónimo ({year})"
        parenthetical = f"(Anónimo, {year})"
        return narrative, parenthetical

    num_authors = len(authors)
    first_author_surname = authors[0].family_name or authors[0].full_name

    if num_authors == 1:
        narrative = f"{first_author_surname} ({year})"
        parenthetical = f"({first_author_surname}, {year})"
    elif num_authors == 2:
        second_author_surname = authors[1].family_name or authors[1].full_name
        narrative = f"{first_author_surname} {and_connector} {second_author_surname} ({year})"
        parenthetical = f"({first_author_surname} {and_connector} {second_author_surname}, {year})"
    else:
        # APA 7: Para 3 o más autores siempre se usa 'et al.' desde la primera mención
        narrative = f"{first_author_surname} et al. ({year})"
        parenthetical = f"({first_author_surname} et al., {year})"

    return narrative, parenthetical


def format_full_reference_apa7(
    paper: PaperMetadata,
    language: Literal["es", "en"] = "es"
) -> str:
    """
    Construye la referencia bibliográfica completa conforme al estándar APA 7ma edición.
    Ejemplo Revista / Conferencia:
    Apellido, N. I., & Apellido2, J. (2020). Título del artículo en sentence case.
    *Nombre de la Revista*, *volumen*(número), páginas. https://doi.org/xxxx
    """
    and_sym = "&" if language == "en" else "&"  # En referencias de APA 7 internacional suele usarse '&'
    year_str = str(paper.year) if paper.year else ("s.f." if language == "es" else "n.d.")

    # 1. Formatear lista de autores
    authors_formatted: List[str] = []
    for author in paper.authors:
        initials = _format_author_initials(author.given_name)
        surname = author.family_name or author.full_name
        if initials:
            authors_formatted.append(f"{surname}, {initials}")
        else:
            authors_formatted.append(surname)

    if not authors_formatted:
        author_string = "Anónimo"
    elif len(authors_formatted) == 1:
        author_string = authors_formatted[0]
    elif len(authors_formatted) == 2:
        author_string = f"{authors_formatted[0]}, {and_sym} {authors_formatted[1]}"
    elif len(authors_formatted) <= 20:
        author_string = ", ".join(authors_formatted[:-1]) + f", {and_sym} " + authors_formatted[-1]
    else:
        # APA 7: Si hay más de 20 autores, se colocan los primeros 19, puntos suspensivos y el último
        author_string = ", ".join(authors_formatted[:19]) + ", ... " + authors_formatted[-1]

    # 2. Formatear título en sentence case
    title_formatted = _to_sentence_case(paper.title)
    if title_formatted and not title_formatted.endswith("."):
        title_formatted += "."

    # 3. Formatear fuente / revista / actas de congreso
    source_parts: List[str] = []
    if paper.venue:
        venue_str = f"*{paper.venue.strip()}*"
        if paper.volume:
            vol_str = f"*{paper.volume}*"
            if paper.issue:
                vol_str += f"({paper.issue})"
            venue_str += f", {vol_str}"
        if paper.pages:
            venue_str += f", {paper.pages}"
        venue_str += "."
        source_parts.append(venue_str)

    # 4. Formatear DOI o URL
    doi_or_url = ""
    if paper.doi:
        clean_doi = paper.doi.strip()
        if not clean_doi.startswith("http"):
            clean_doi = f"https://doi.org/{clean_doi}"
        doi_or_url = clean_doi
    elif paper.url:
        doi_or_url = paper.url.strip()

    # Ensamblar la referencia final
    parts: List[str] = [f"{author_string} ({year_str}).", title_formatted]
    if source_parts:
        parts.extend(source_parts)
    if doi_or_url:
        parts.append(doi_or_url)

    return " ".join(parts)


def format_bibtex(paper: PaperMetadata) -> str:
    """Genera la entrada en formato BibTeX para gestores como Zotero, Mendeley o LaTeX."""
    first_author_key = "anon"
    if paper.authors:
        first_author_key = re.sub(r"[^\w]", "", paper.authors[0].family_name or "author").lower()
    year_key = str(paper.year) if paper.year else "nodate"
    first_word_key = "paper"
    words = [w for w in re.sub(r"[^\w\s]", "", paper.title).split() if len(w) > 3]
    if words:
        first_word_key = words[0].lower()

    citation_key = f"{first_author_key}_{year_key}_{first_word_key}"

    author_names = " and ".join(
        f"{a.family_name}, {a.given_name}" if a.given_name else a.full_name
        for a in paper.authors
    ) or "Anonymous"

    lines: List[str] = [
        f"@article{{{citation_key},",
        f"  title = {{{paper.title}}},",
        f"  author = {{{author_names}}},",
        f"  year = {{{paper.year or ''}}},",
    ]
    if paper.venue:
        lines.append(f"  journal = {{{paper.venue}}},")
    if paper.volume:
        lines.append(f"  volume = {{{paper.volume}}},")
    if paper.issue:
        lines.append(f"  number = {{{paper.issue}}},")
    if paper.pages:
        lines.append(f"  pages = {{{paper.pages}}},")
    if paper.doi:
        lines.append(f"  doi = {{{paper.doi}}},")
    if paper.url:
        lines.append(f"  url = {{{paper.url}}},")
    lines.append("}")
    return "\n".join(lines)


def build_apa7_citation(
    paper: PaperMetadata,
    language: Literal["es", "en"] = "es"
) -> Apa7Citation:
    """Genera el objeto completo Apa7Citation con todos sus formatos derivados."""
    year_str = str(paper.year) if paper.year else ("s.f." if language == "es" else "n.d.")
    narrative, parenthetical = format_in_text_citations(paper.authors, year_str, language)
    full_ref = format_full_reference_apa7(paper, language)
    bibtex = format_bibtex(paper)

    return Apa7Citation(
        narrative_citation=narrative,
        parenthetical_citation=parenthetical,
        full_reference=full_ref,
        bibtex_entry=bibtex,
    )
