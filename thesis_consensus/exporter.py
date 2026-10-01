"""
Módulo de exportación estructurada de resultados para la tesis.
Genera documentos en Markdown organizados por secciones, tablas de decisión,
archivos BibTeX deduplicados y JSON estructurado.
"""

import json
import re
import shutil
from pathlib import Path
from typing import List, Set, Dict, Optional
from thesis_consensus.models import (
    PaperMetadata,
    ThesisEvidenceItem,
    MultiPaperSynthesis,
    TopicResearchBatch,
)
from thesis_consensus.constants import EVIDENCE_TYPE_NAMES, DECISION_ENGINE_NAMES


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
            "# Fundamentos Teóricos de la Tesis: Evidencias de Literatura Arbitrada",
            "> Evidencia recuperada y evaluada con normas oficiales **APA 7ma Edición** y filtrado por modelos de decisión.",
            "",
            "## 📑 Índice de Fundamentación por Temas de Investigación",
            "",
        ]

        # 1. Tabla de contenidos interactiva
        for idx, topic in enumerate(batch.topics, start=1):
            anchor = f"tema-{idx}"
            conserved_count = len(batch.conserved_by_topic.get(topic, []))
            lines.append(f"- [{idx}. {topic}](#{anchor}) *({conserved_count} fuentes aprobadas por umbral)*")

        lines.extend([
            f"- [Referencias Bibliográficas (APA 7ma Edición)](#referencias-bibliograficas-unificadas)",
            "",
            "---",
            "",
        ])

        # 2. Secciones por cada tema / pregunta de tesis
        for idx, topic in enumerate(batch.topics, start=1):
            anchor = f"tema-{idx}"
            conserved = batch.conserved_by_topic.get(topic, [])
            discarded = batch.discarded_by_topic.get(topic, [])

            lines.extend([
                f"<a id=\"{anchor}\"></a>",
                f"## {idx}. Tema: {topic}",
                f"**Balance de revisión:** `{len(conserved)} fuentes conservadas` | `{len(discarded)} descartadas por umbral`",
                "",
                "### 📊 Evaluación y Criterios del Modelo de Decisión",
                "",
                "| Estado | Autor(es) y Año | P(Relevancia) | Umbral | Tipo Evidencia | Rigor Metodológico | Justificación de Elección |",
                "| :---: | :--- | :---: | :---: | :---: | :---: | :--- |",
            ])

            for item in conserved:
                first_author = item.paper.authors[0].family_name if item.paper.authors else "Anónimo"
                year_str = str(item.paper.year) if item.paper.year else "s.f."
                ev_label = EVIDENCE_TYPE_NAMES.get(item.decision.evidence_type, item.decision.evidence_type)
                lines.append(
                    f"| ✅ **CONSERVADO** | {first_author} ({year_str}) | `{item.decision.relevance_score:.1%}` | "
                    f"`>={item.decision.threshold_applied:.0%}` | {ev_label} | "
                    f"`{item.decision.quality_score:.1f}/3.0` | {item.decision.verdict_reason} |"
                )

            for p in discarded:
                first_author = p.authors[0].family_name if p.authors else "Anónimo"
                year_str = str(p.year) if p.year else "s.f."
                lines.append(
                    f"| ❌ *Descartado* | {first_author} ({year_str}) | `< umbral` | `exigido` | "
                    f"No relevante | `{p.citation_count} citas` | No superó el umbral de afinidad temática exigido para la tesis. |"
                )

            lines.append("")

            # 3. Detalle y evidencias individuales por paper con trazabilidad anti-alucinación
            lines.append("### 📚 Evidencias Específicas por Artículo y Auditoría Textual (Cero Alucinación)")
            for p_idx, item in enumerate(conserved, start=1):
                p = item.paper
                engine_label = DECISION_ENGINE_NAMES.get(item.decision.decision_engine, item.decision.decision_engine)
                ev_type_label = EVIDENCE_TYPE_NAMES.get(item.decision.evidence_type, item.decision.evidence_type)
                lines.extend([
                    f"#### {idx}.{p_idx}. {p.title}",
                    f"- **Motor de Decisión:** `{engine_label}` | **Tipología:** `{ev_type_label}`",
                    f"- **Cita narrativa (APA 7):** `{item.apa7.narrative_citation}`",
                    f"- **Cita parentética (APA 7):** `{item.apa7.parenthetical_citation}`",
                    "",
                    "> 🔍 **Auditoría de Veracidad y Respaldo Textual (Cero Alucinación):**",
                    f"> - **Cita Textual Literal del Artículo:** *\"{item.exact_source_quote}\"*",
                    f"> - **Procedencia de la Cita:** `{item.source_location}`",
                    f"> - **Tipo de Acceso:** `{p.content_source}` | **Citas Recibidas:** `{p.citation_count}`",
                    f"> - **Extracto Sustantivo / Abstract:**",
                    f">   {item.content_excerpt or p.abstract}",
                    "",
                    f"- **Referencia bibliográfica APA 7:** {item.apa7.full_reference}",
                    f"- **DOI Verificable:** [{p.doi or p.url or 'Enlace al Paper'}]({p.doi or p.url or '#'})",
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
        synthesis: Optional[MultiPaperSynthesis] = None,
    ) -> str:
        """Genera un archivo Markdown para una sola pregunta adaptándolo a la estructura de lote."""
        batch = TopicResearchBatch(
            topics=[topic_or_claim],
            conserved_by_topic={topic_or_claim: items},
            discarded_by_topic={topic_or_claim: []},
            syntheses_by_topic={topic_or_claim: synthesis} if synthesis else {},
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

    @staticmethod
    def to_batch_json(
        batch: TopicResearchBatch,
        output_filepath: str,
    ) -> str:
        """Exporta los datos estructurados de investigación a un archivo JSON."""
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = batch.model_dump(mode="json")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path.resolve())

    @classmethod
    def to_topic_json(
        cls,
        topic: str,
        conserved: List[ThesisEvidenceItem],
        discarded: List[PaperMetadata],
        output_filepath: str,
    ) -> str:
        """
        Exporta los datos estructurados en un formato JSON listo para ser consumido
        directamente por un agente redactor de marco teórico.
        """
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        min_threshold = conserved[0].decision.threshold_applied if conserved else 0.80

        data = {
            "tema_investigacion": topic,
            "resumen_evaluacion": {
                "total_candidatos_evaluados": len(conserved) + len(discarded),
                "papers_aprobados_conservados": len(conserved),
                "papers_descartados": len(discarded),
                "umbral_minimo_exigido": min_threshold,
            },
            "instrucciones_para_agente_redactor": (
                "Este archivo contiene la evidencia científica arbitrada y verificada para fundamentar "
                "este tema en la tesis. Utilice los datos de 'evidencias_conservadas' para redactar "
                "el marco teórico. Emplee las citas narrativas y parentéticas en formato APA 7 proporcionadas, "
                "cite textualmente o parafrasee basándose en 'cita_textual_literal' y 'contenido_sustantivo_extracto', "
                "y agregue las referencias en 'citacion_apa7.referencia_completa' a la bibliografía."
            ),
            "evidencias_conservadas": [
                {
                    "paper_id": item.paper.paper_id,
                    "titulo": item.paper.title,
                    "autores": [a.full_name for a in item.paper.authors],
                    "primer_autor": item.paper.authors[0].family_name if item.paper.authors else "Anónimo",
                    "año": item.paper.year,
                    "revista_o_fuente": item.paper.venue,
                    "doi": item.paper.doi,
                    "enlace_url": item.paper.doi or item.paper.url,
                    "citas_recibidas": item.paper.citation_count,
                    "tipo_acceso": item.paper.content_source,
                    "citacion_apa7": {
                        "cita_narrativa": item.apa7.narrative_citation,
                        "cita_parentetica": item.apa7.parenthetical_citation,
                        "referencia_completa": item.apa7.full_reference,
                        "bibtex": item.apa7.bibtex_entry,
                    },
                    "evaluacion_decision": {
                        "motor_decision": item.decision.decision_engine,
                        "probabilidad_relevancia": round(item.decision.relevance_score, 4),
                        "umbral_aplicado": item.decision.threshold_applied,
                        "tipo_evidencia": item.decision.evidence_type,
                        "rigor_metodologico": item.decision.quality_score,
                        "justificacion_decision": item.decision.verdict_reason,
                    },
                    "cita_textual_literal": item.exact_source_quote,
                    "ubicacion_fuente": item.source_location,
                    "contenido_sustantivo_extracto": item.content_excerpt or item.paper.abstract,
                    "abstract_completo": item.paper.abstract,
                }
                for item in conserved
            ],
            "papers_descartados": [
                {
                    "titulo": p.title,
                    "autores": [a.full_name for a in p.authors],
                    "año": p.year,
                    "citas": p.citation_count,
                    "motivo": "No superó el umbral mínimo exigido (80% - 85%)",
                }
                for p in discarded
            ],
        }

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path.resolve())

    @classmethod
    def export_batch_grouped_by_topic(
        cls,
        batch: TopicResearchBatch,
        base_output_dir: str = "outputs",
    ) -> Dict[str, str]:
        """
        Organiza y exporta todos los resultados ordenados exclusivamente en subcarpetas temáticas limpias.
        Sin prefijos numéricos (como tema_01), sin reporte general consolidado redundante,
        y asegurando que cada tema tenga su evidencia.json, referencias.bib y fundamentos_teoricos.md.
        """
        base_dir = Path(base_output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        created_paths: Dict[str, str] = {}

        # 1. Exportar subcarpeta individual por cada tema (sin prefijos numéricos)
        for idx, topic in enumerate(batch.topics, start=1):
            topic_slug = cls._slugify(topic)[:45]
            folder_name = f"tema_{topic_slug}".rstrip("-")
            topic_dir = base_dir / folder_name
            topic_dir.mkdir(parents=True, exist_ok=True)

            conserved = batch.conserved_by_topic.get(topic, [])
            discarded = batch.discarded_by_topic.get(topic, [])

            single_batch = TopicResearchBatch(
                topics=[topic],
                conserved_by_topic={topic: conserved},
                discarded_by_topic={topic: discarded},
                syntheses_by_topic={},
                all_conserved_items=conserved,
            )

            topic_md = str(topic_dir / "fundamentos_teoricos.md")
            topic_bib = str(topic_dir / "referencias.bib")
            topic_json = str(topic_dir / "evidencia.json")

            cls.to_batch_markdown(single_batch, topic_md)
            cls.to_batch_bibtex(single_batch, topic_bib)
            cls.to_topic_json(topic, conserved, discarded, topic_json)

            created_paths[f"tema_{idx}"] = str(topic_dir.resolve())

        # 2. Limpiar carpeta de reporte consolidado si existiera de ejecuciones previas
        consolidated_dir = base_dir / "reporte_general_consolidado"
        if consolidated_dir.is_dir():
            shutil.rmtree(consolidated_dir, ignore_errors=True)

        # 3. Limpiar cualquier archivo suelto que hubiera quedado en la raíz de outputs/
        for loose_file in ("fundamentos_teoricos_tesis.md", "referencias_tesis.bib", "evidencia_academica.json"):
            old_p = base_dir / loose_file
            if old_p.is_file():
                try:
                    old_p.unlink()
                except Exception:
                    pass

        return created_paths
