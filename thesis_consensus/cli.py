"""
Interfaz de línea de comandos (CLI) interactiva y scriptable con Rich.
Muestra tablas, veredictos de decisión con umbrales altos (80%-85%),
síntesis multi-paper y exportación consolidada para múltiples preguntas de tesis.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from thesis_consensus.agent import ThesisConsensusAgent
from thesis_consensus.decision import create_decision_judge
from thesis_consensus.exporter import ThesisExporter
from thesis_consensus.models import TopicResearchBatch
from thesis_consensus.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_DECISION_ENGINE,
    DEFAULT_RELEVANCE_THRESHOLD,
    STRICT_RELEVANCE_THRESHOLD,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_MIN_PUBLICATION_YEAR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_MD,
    DEFAULT_OUTPUT_BIB,
    EVIDENCE_TYPE_NAMES,
)

console = Console()


def display_welcome_banner(threshold: float, language: str) -> None:
    """Muestra el encabezado del asistente de investigación."""
    console.print(
        Panel.fit(
            "[bold cyan]🎓 THESIS CONSENSUS (Buscador y Evaluador de Literatura para Tesis)[/bold cyan]\n"
            f"[green]• Idioma configurado:[/green] [bold white]{language.upper()} (Español Académico)[/bold white]\n"
            f"[yellow]• Umbral de corte del Modelo de Decisión:[/yellow] [bold red]{threshold:.0%}[/bold red] (Alta exigencia para tesis)\n"
            "[magenta]• Síntesis multi-paper integrada con normas oficiales APA 7ma Edición[/magenta]",
            border_style="cyan",
        )
    )


def process_topics_batch(
    topics: List[str],
    limit: int = DEFAULT_SEARCH_LIMIT,
    min_year: int = DEFAULT_MIN_PUBLICATION_YEAR,
    engine: str = DEFAULT_DECISION_ENGINE,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    language: str = DEFAULT_LANGUAGE,
    out_md: str = DEFAULT_OUTPUT_MD,
    out_bib: str = DEFAULT_OUTPUT_BIB,
) -> TopicResearchBatch:
    """Procesa un conjunto de preguntas o afirmaciones de forma estructurada."""
    judge = create_decision_judge(preferred_engine=engine)
    agent = ThesisConsensusAgent(decision_judge=judge, language=language)

    console.print(f"[bold]⚙️ Motor de Decisión activo:[/bold] [yellow]{judge.engine_name}[/yellow]")
    if judge.engine_name == "unsloth_laya":
        if judge.is_available():
            console.print("[green]✔ Servidor Unsloth Desktop (Laya / Jev API) conectado en localhost:8888[/green]")
        else:
            console.print("[yellow]ℹ Servidor Unsloth Laya no detectado. Utilizando evaluador semántico con umbral estricto.[/yellow]")
    elif judge.engine_name == "heuristic_academic":
        console.print("[cyan]ℹ Evaluador semántico académico activo (umbral de corte calibrado al 80%-85%)[/cyan]")

    console.print(f"\n[bold green]📋 Total de temas a fundamentar:[/bold green] [bold white]{len(topics)}[/bold white]\n")

    def topic_progress_callback(curr: int, total: int, current_topic: str) -> None:
        console.print(f"[bold cyan]▶ [{curr}/{total}] Analizando literatura para:[/bold cyan] [italic]\"{current_topic}\"[/italic]")

    with console.status("[bold green]Consultando bases indexadas y evaluando pertinencia con el modelo de decisión..."):
        batch = agent.research_batch(
            topics=topics,
            limit_per_topic=limit,
            min_year=min_year,
            threshold=threshold,
            topic_callback=topic_progress_callback,
        )

    # Imprimir resumen ordenado por cada tema
    for idx, topic in enumerate(topics, start=1):
        conserved = batch.conserved_by_topic.get(topic, [])
        discarded = batch.discarded_by_topic.get(topic, [])
        synthesis = batch.syntheses_by_topic.get(topic)

        console.print("\n" + "=" * 80)
        console.print(f"[bold cyan]SECCIÓN {idx}: {topic}[/bold cyan]")
        console.print("=" * 80)

        # 1. Tabla de Veredicto del Modelo de Decisiones (Por qué se escogieron)
        table = Table(
            title=f"📊 Veredictos del Modelo de Decisión (Umbral Mínimo: {threshold:.0%})",
            border_style="cyan"
        )
        table.add_column("Estado", justify="center", width=12)
        table.add_column("Autor(es) / Año", width=22)
        table.add_column("P(Relevancia)", justify="center", width=14)
        table.add_column("Tipo Evidencia", style="magenta", width=16)
        table.add_column("Rigor", justify="center", width=10)
        table.add_column("Justificación del Modelo de Decisión", style="white")

        for it in conserved:
            author_str = it.paper.authors[0].family_name if it.paper.authors else "Anónimo"
            year_str = str(it.paper.year) if it.paper.year else "s.f."
            ev_label = EVIDENCE_TYPE_NAMES.get(it.decision.evidence_type, it.decision.evidence_type)
            table.add_row(
                "[green]CONSERVAR[/green]",
                f"{author_str} ({year_str})",
                f"[bold green]{it.decision.relevance_score:.1%}[/bold green]",
                ev_label,
                f"{it.decision.quality_score:.1f}/3.0",
                it.decision.verdict_reason,
            )

        for dp in discarded:
            author_str = dp.authors[0].family_name if dp.authors else "Anónimo"
            year_str = str(dp.year) if dp.year else "s.f."
            table.add_row(
                "[red]DESCARTAR[/red]",
                f"{author_str} ({year_str})",
                "[red]< umbral[/red]",
                "[dim]No relevante[/dim]",
                f"{dp.citation_count} citas",
                "[dim]No alcanzó el umbral del 80%-85% exigido.[/dim]",
            )

        console.print(table)
        console.print(f"[bold]Balance:[/bold] [green]{len(conserved)} conservados[/green] | [red]{len(discarded)} descartados[/red]")

        # 2. Síntesis Multi-Paper en Español
        if synthesis and conserved:
            console.print(Panel(
                f"[bold yellow]📝 Síntesis Teórica Integrada (Múltiples Papers)[/bold yellow]\n\n"
                f"[bold white]Opción A (Narrativa Dialéctica recomendada):[/bold white]\n{synthesis.integrated_narrative}\n\n"
                f"[bold white]Opción B (Citación Parentética Agrupada APA 7):[/bold white]\n{synthesis.parenthetical_synthesis}",
                border_style="yellow",
            ))

    # Exportar resultados estructurados agrupados por cada pregunta
    export_paths = ThesisExporter.export_batch_grouped_by_topic(
        batch=batch,
        base_output_dir=DEFAULT_OUTPUT_DIR,
        master_md_filename=Path(out_md).name,
        master_bib_filename=Path(out_bib).name,
    )

    console.print("\n" + "#" * 80)
    console.print("[bold green]✔ Resultados organizados y agrupados por pregunta:[/bold green]")
    for idx, topic in enumerate(batch.topics, start=1):
        topic_folder = export_paths.get(f"tema_{idx}")
        if topic_folder:
            console.print(f"  📂 [cyan]{topic_folder}[/cyan]")
            console.print("     ├── [white]fundamentos_teoricos.md[/white] (Marco teórico específico)")
            console.print("     ├── [white]referencias.bib[/white] (BibTeX específico del tema)")
            console.print("     └── [white]evidencia.json[/white] (JSON estructurado)")

    console.print(f"\n[bold green]✔ Reporte maestro consolidado de tesis:[/bold green]\n👉 [underline]{export_paths.get('master_md')}[/underline]")
    console.print(f"[bold green]✔ Bibliografía general consolidada y deduplicada (BibTeX):[/bold green]\n👉 [underline]{export_paths.get('master_bib')}[/underline]")
    console.print("#" * 80 + "\n")

    return batch


def interactive_menu() -> None:
    """Menú interactivo con soporte para múltiples preguntas."""
    display_welcome_banner(DEFAULT_RELEVANCE_THRESHOLD, DEFAULT_LANGUAGE)

    predefined_topics = [
        "How is IT Service Management (ITSM) or ITIL implemented in higher education institutions and university help desks?",
        "What are the challenges, ticket volume overloads, and bottlenecks in university IT support and help desk services?",
        "Impact of ITIL incident management and service level agreements (SLAs) on academic IT satisfaction",
    ]

    console.print("[bold yellow]Seleccione una modalidad de trabajo:[/bold yellow]")
    console.print("  [cyan][1][/cyan] Evaluar preguntas precargadas de tesis en lote (Batch)")
    console.print("  [cyan][2][/cyan] Ingresar múltiples preguntas personalizadas juntas")
    console.print("  [cyan][3][/cyan] Cargar preguntas desde un archivo de texto")

    choice = console.input("\n[bold green]Opción (1-3): [/bold green]").strip()

    topics_to_process: List[str] = []

    if choice == "1":
        topics_to_process = predefined_topics
    elif choice == "3":
        filepath = console.input("[bold green]Ruta del archivo con preguntas (un tema por línea): [/bold green]").strip()
        p = Path(filepath)
        if p.exists():
            topics_to_process = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            console.print(f"[red]Archivo {filepath} no encontrado. Usando preguntas de prueba.[/red]")
            topics_to_process = predefined_topics
    else:
        console.print("[bold yellow]Ingrese sus preguntas de tesis (presione ENTER con línea vacía para terminar):[/bold yellow]")
        while True:
            t = console.input(f"  Tema {len(topics_to_process) + 1}: ").strip()
            if not t:
                break
            topics_to_process.append(t)
        if not topics_to_process:
            topics_to_process = [predefined_topics[0]]

    # Preguntar umbral deseado
    console.print(f"\n[bold yellow]Seleccione el umbral del Modelo de Decisión:[/bold yellow]")
    console.print(f"  [cyan][1][/cyan] 80% (Recomendado estándar: {DEFAULT_RELEVANCE_THRESHOLD:.0%})")
    console.print(f"  [cyan][2][/cyan] 85% (Alta rigurosidad estricta: {STRICT_RELEVANCE_THRESHOLD:.0%})")
    u_choice = console.input("[bold green]Opción (1 o 2, por defecto 1): [/bold green]").strip()
    threshold = STRICT_RELEVANCE_THRESHOLD if u_choice == "2" else DEFAULT_RELEVANCE_THRESHOLD

    process_topics_batch(
        topics=topics_to_process,
        threshold=threshold,
        language=DEFAULT_LANGUAGE,
    )


def main() -> None:
    """Punto de entrada principal para CLI."""
    parser = argparse.ArgumentParser(
        description="Thesis Consensus: Buscador y evaluador de literatura para marco teórico con APA 7."
    )
    parser.add_argument("--topic", "-t", type=str, nargs="+", help="Uno o más temas / preguntas de tesis")
    parser.add_argument("--file", "-f", type=str, help="Archivo .txt con temas (uno por línea)")
    parser.add_argument("--limit", "-l", type=int, default=DEFAULT_SEARCH_LIMIT, help="Papers por tema (default: 15)")
    parser.add_argument("--min-year", "-y", type=int, default=DEFAULT_MIN_PUBLICATION_YEAR, help="Año mínimo de publicación")
    parser.add_argument(
        "--engine",
        "-e",
        choices=["unsloth_laya", "laya", "heuristic", "openai", "auto"],
        default=DEFAULT_DECISION_ENGINE,
        help=f"Motor de decisión (default: {DEFAULT_DECISION_ENGINE})",
    )
    parser.add_argument("--threshold", "-th", type=float, default=DEFAULT_RELEVANCE_THRESHOLD, help="Umbral de decisión (0.80 - 0.85)")
    parser.add_argument("--lang", type=str, default=DEFAULT_LANGUAGE, help="Idioma de redacción (default: es)")
    parser.add_argument("--out-md", "-o", type=str, default=DEFAULT_OUTPUT_MD, help="Ruta de exportación Markdown")
    parser.add_argument("--out-bib", "-b", type=str, default=DEFAULT_OUTPUT_BIB, help="Ruta de exportación BibTeX")
    parser.add_argument("--interactive", "-i", action="store_true", help="Lanzar en modo interactivo")

    args = parser.parse_args()

    if args.interactive or (len(sys.argv) == 1 and not args.topic and not args.file):
        interactive_menu()
    else:
        topics: List[str] = []
        if args.file:
            path = Path(args.file)
            if path.exists():
                topics = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if args.topic:
            topics.extend(args.topic)

        if not topics:
            parser.print_help()
            return

        display_welcome_banner(args.threshold, args.lang)
        process_topics_batch(
            topics=topics,
            limit=args.limit,
            min_year=args.min_year,
            engine=args.engine,
            threshold=args.threshold,
            language=args.lang,
            out_md=args.out_md,
            out_bib=args.out_bib,
        )


if __name__ == "__main__":
    main()
