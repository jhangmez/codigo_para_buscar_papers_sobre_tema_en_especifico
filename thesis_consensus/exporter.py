"""
Módulo de exportación de resultados para la tesis.
Genera documentos en Markdown listos para copiar al marco teórico,
archivos BibTeX para Zotero/Mendeley y JSON estructurado.
"""

import json
from pathlib import Path
from typing import List
from thesis_consensus.models import ThesisEvidenceItem
from thesis_consensus.synthesizer import ThesisSynthesizer


class ThesisExporter:
    """Exportador de resultados académicos fundamentados."""

    @staticmethod
    def to_markdown(
        items: List[ThesisEvidenceItem],
        topic_or_claim: str,
        output_filepath: str,
        synthesizer: ThesisSynthesizer,
    ) -> str:
        """Genera un archivo Markdown completo con el marco teórico y la lista de referencias APA 7."""
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = [
            f"# Fundamentos Teóricos: Evidencia y Citas Académicas",
            f"**Tema de Investigación / Afirmación a Fundamentar:**",
            f"> *\"{topic_or_claim}\"*",
            "",
            "---",
            "",
            synthesizer.generate_consensus_summary(topic_or_claim, items),
            "",
            "---",
            "",
            "## 1. Redacción de Fundamentos Teóricos (Citas Narrativas y Parentéticas en APA 7)",
            "",
            "A continuación se presentan los párrafos estructurados y fundamentados, listos para incorporar en el capítulo de fundamentos teóricos de la tesis:",
            "",
        ]

        for i, item in enumerate(items, start=1):
            p = item.paper
            d = item.decision
            lines.extend([
                f"### 1.{i}. {p.title}",
                f"- **Motor de Decisión:** `{d.decision_engine}` | **Tipo:** `{d.evidence_type}` | **Rigor:** `{d.quality_score:.1f}/3.0` | **Citas recibidas:** `{p.citation_count}`",
                f"- **Veredicto del Modelo:** {d.verdict_reason}",
                "",
                "**Texto sugerido para el marco teórico:**",
                f"> {item.narrative_paragraph}",
                "",
                f"- **Cita narrativa:** `{item.apa7.narrative_citation}`",
                f"- **Cita parentética:** `{item.apa7.parenthetical_citation}`",
                f"- **DOI / Enlace seguro:** [{p.doi or p.url or 'Enlace'}]({p.doi or p.url or '#'})",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## 2. Referencias Bibliográficas (Estándar APA 7ma Edición)",
            "",
            "Pegue esta lista en la sección final de Referencias de su tesis:",
            "",
        ])

        # Ordenar alfabéticamente por primer autor como exige APA 7
        sorted_items = sorted(
            items,
            key=lambda it: it.paper.authors[0].family_name.lower() if it.paper.authors else "zzz",
        )

        for item in sorted_items:
            # En markdown se puede representar la sangría o lista limpia
            lines.append(f"- {item.apa7.full_reference}")

        content = "\n".join(lines)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())

    @staticmethod
    def to_bibtex(items: List[ThesisEvidenceItem], output_filepath: str) -> str:
        """Exporta todas las referencias a un archivo .bib compatible con LaTeX y Zotero."""
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        bibtex_entries = [item.apa7.bibtex_entry for item in items]
        content = "\n\n".join(bibtex_entries) + "\n"
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())

    @staticmethod
    def to_json(items: List[ThesisEvidenceItem], output_filepath: str) -> str:
        """Exporta la estructura completa a JSON para integraciones con aplicaciones web o APIs."""
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = [item.model_dump() for item in items]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path.resolve())
