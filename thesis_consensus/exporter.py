"""
Módulo de exportación estructurada de resultados para la tesis.
Genera documentos en Markdown organizados por secciones, tablas de decisión,
archivos BibTeX deduplicados y JSON estructurado.
"""

import json
import re
from pathlib import Path
from typing import List, Set, Dict
from thesis_consensus.models import (
    ThesisEvidenceItem,
    MultiPaperSynthesis,
    TopicResearchBatch,
)


class ThesisExporter:
    """Exportador de resultados académicos fundamentados para marco teórico."""

    @staticmethod
    def _slugify(text: str) -> str:
        """Genera un slug compatible con anclas de Markdown."""
        clean = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[\s_-]+", "-", clean).strip("-")

    @classmethod
    def to_batch_markdown(
        cls,
        batch: TopicResearchBatch,
        output_filepath: str,
    ) -> str:
        """
        Genera un reporte Markdown maestro y ordenado para múltiples preguntas de investigación.
        Incluye índice, síntesis multi-paper integrada, tarjetas de decisión y bibliografía única.
        """
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = [
            "# Fundamentos Teóricos de la Tesis: Síntesis de Literatura Arbitrada",
            "> Documento generado automáticamente con normas oficiales **APA 7ma Edición** y evaluación de modelos de decisión.",
            "",
            "## 📑 Índice de Fundamentación por Temas de Investigación",
            "",
        ]

        # 1. Tabla de contenidos interactiva
        for idx, topic in enumerate(batch.topics, start=1):
            anchor = f"tema-{idx}"
            conserved_count = len(batch.conserved_by_topic.get(topic, []))
            lines.append(f"- [{idx}. {topic}](#{anchor}) *({conserved_count} fuentes de alta pertinencia)*")

        lines.extend([
            f"- [Referencias Bibliográficas Generales (APA 7ma Edición)](#referencias-bibliograficas-unificadas)",
            "",
            "---",
            "",
        ])

        # 2. Secciones por cada tema / pregunta de tesis
        for idx, topic in enumerate(batch.topics, start=1):
            anchor = f"tema-{idx}"
            conserved = batch.conserved_by_topic.get(topic, [])
            discarded = batch.discarded_by_topic.get(topic, [])
            synthesis = batch.syntheses_by_topic.get(topic)

            lines.extend([
                f"<a id=\"{anchor}\"></a>",
                f"## {idx}. Tema: {topic}",
                f"**Balance de revisión:** `{len(conserved)} fuentes conservadas` | `{len(discarded)} descartadas por umbral`",
                "",
                "### 📝 Síntesis Teórica Integrada (Múltiples Papers - Redacción en Español)",
                "",
            ])

            if synthesis:
                lines.extend([
                    "#### Opción A: Redacción Narrativa Dialéctica (Recomendada para abrir el marco teórico)",
                    f"> {synthesis.integrated_narrative}",
                    "",
                    "#### Opción B: Enfoque Complementario por Tipología de Evidencia",
                    f"> {synthesis.complementary_narrative}",
                    "",
                    "#### Opción C: Afirmación con Citas Parentéticas Agrupadas (APA 7)",
                    f"> {synthesis.parenthetical_synthesis}",
                    "",
                ])
            else:
                lines.append("*Sin síntesis multi-paper disponible.*")

            # 3. Tarjeta de Veredicto del Modelo de Decisiones (Por qué se escogieron)
            lines.extend([
                "### 📊 Evaluación y Criterios del Modelo de Decisión",
                "",
                "| Estado | Autor y Año | P(Relevancia) | Umbral | Tipo Evidencia | Rigor Metodológico | Justificación de Elección |",
                "| :---: | :--- | :---: | :---: | :---: | :---: | :--- |",
            ])

            for item in conserved:
                first_author = item.paper.authors[0].family_name if item.paper.authors else "Anónimo"
                year_str = str(item.paper.year) if item.paper.year else "s.f."
                lines.append(
                    f"| ✅ **CONSERVADO** | {first_author} ({year_str}) | `{item.decision.relevance_score:.1%}` | "
                    f"`>={item.decision.threshold_applied:.0%}` | `{item.decision.evidence_type}` | "
                    f"`{item.decision.quality_score:.1f}/3.0` | {item.decision.verdict_reason} |"
                )

            for p in discarded:
                first_author = p.authors[0].family_name if p.authors else "Anónimo"
                year_str = str(p.year) if p.year else "s.f."
                lines.append(
                    f"| ❌ *Descartado* | {first_author} ({year_str}) | `< umbral` | `exigido` | "
                    f"`no relevante` | `{p.citation_count} citas` | No superó el umbral de afinidad temática exigido para la tesis. |"
                )

            lines.append("")

            # 4. Detalle y citas individuales por paper
            lines.append("### 📚 Evidencias Específicas por Artículo")
            for p_idx, item in enumerate(conserved, start=1):
                p = item.paper
                lines.extend([
                    f"#### {idx}.{p_idx}. {p.title}",
                    f"- **Cita narrativa:** `{item.apa7.narrative_citation}`",
                    f"- **Cita parentética:** `{item.apa7.parenthetical_citation}`",
                    f"- **Aporte al marco teórico:** {item.narrative_paragraph}",
                    f"- **Referencia APA 7:** {item.apa7.full_reference}",
                    f"- **DOI:** [{p.doi or p.url or 'Enlace'}]({p.doi or p.url or '#'})",
                    "",
                ])

            lines.extend(["---", ""])

        # 3. Referencias Bibliográficas Generales Unificadas (Deduplicadas)
        lines.extend([
            "<a id=\"referencias-bibliograficas-unificadas\"></a>",
            "## 📖 Referencias Bibliográficas Unificadas (Estándar APA 7ma Edición)",
            "Lista general consolidada y deduplicada, ordenada alfabéticamente para colocar en la sección final de su tesis:",
            "",
        ])

        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        unique_items: List[ThesisEvidenceItem] = []

        for item in batch.all_conserved_items:
            clean_doi = item.paper.doi.strip().lower() if item.paper.doi else ""
            clean_title = item.paper.title.strip().lower()

            if clean_doi and clean_doi in seen_dois:
                continue
            if clean_title and clean_title in seen_titles:
                continue

            if clean_doi:
                seen_dois.add(clean_doi)
            seen_titles.add(clean_title)
            unique_items.append(item)

        # Ordenar alfabéticamente por apellido del primer autor
        unique_items.sort(
            key=lambda it: it.paper.authors[0].family_name.lower() if it.paper.authors else "zzz"
        )

        for item in unique_items:
            lines.append(f"- {item.apa7.full_reference}")

        content = "\n".join(lines)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())

    @classmethod
    def to_single_markdown(
        cls,
        items: List[ThesisEvidenceItem],
        topic_or_claim: str,
        output_filepath: str,
        synthesis: MultiPaperSynthesis,
    ) -> str:
        """Genera un archivo Markdown para una sola pregunta adaptándolo a la estructura de lote."""
        batch = TopicResearchBatch(
            topics=[topic_or_claim],
            conserved_by_topic={topic_or_claim: items},
            discarded_by_topic={topic_or_claim: []},
            syntheses_by_topic={topic_or_claim: synthesis},
            all_conserved_items=items,
        )
        return cls.to_batch_markdown(batch, output_filepath)

    @staticmethod
    def to_batch_bibtex(
        batch: TopicResearchBatch,
        output_filepath: str,
    ) -> str:
        """Exporta todas las referencias únicas a un archivo .bib deduplicado."""
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        bibtex_entries: List[str] = []

        for item in batch.all_conserved_items:
            clean_doi = item.paper.doi.strip().lower() if item.paper.doi else ""
            clean_title = item.paper.title.strip().lower()

            if clean_doi and clean_doi in seen_dois:
                continue
            if clean_title and clean_title in seen_titles:
                continue

            if clean_doi:
                seen_dois.add(clean_doi)
            seen_titles.add(clean_title)
            bibtex_entries.append(item.apa7.bibtex_entry)

        content = "\n\n".join(bibtex_entries) + "\n"
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())
