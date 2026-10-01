"""
Interfaz de línea de comandos (CLI) interactiva y scriptable con Rich.
Muestra tablas, veredictos de decisión, citas en APA 7 y exportación directa.
"""

import argparse
import sys
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from thesis_consensus.agent import ThesisConsensusAgent
from thesis_consensus.decision import create_decision_judge
from thesis_consensus.providers.openalex import OpenAlexProvider
from thesis_consensus.exporter import ThesisExporter
from thesis_consensus.synthesizer import ThesisSynthesizer
from thesis_consensus.models import ThesisEvidenceItem, PaperMetadata

console = Console()


def display_welcome_banner() -> None:
    """Muestra el encabezado del asistente de investigación."""
    console.print(
        Panel.fit(
            "[bold cyan]🎓 THESIS CONSENSUS (Buscador y Evaluador de Literatura para Tesis)[/bold cyan]\n"
            "[green]• Búsqueda científica segura sin descarga de PDFs riesgosos (vía OpenAlex & Crossref)[/green]\n"
            "[yellow]• Evaluación y filtrado con Modelos de Decisión (Unsloth Laya / Jev API / Heurístico)[/yellow]\n"
            "[magenta]• Redacción automática de párrafos y referencias en formato APA 7ma Edición[/magenta]",
            border_style="cyan",
        )
    )


def run_pipeline(
    topic: str,
    limit: int = 15,
    min_year: int = 2014,
    engine: str = "auto",
    out_md: str = "fundamentos_teoricos.md",
    out_bib: Optional[str] = "referencias.bib",
) -> List[ThesisEvidenceItem]:
    """Ejecuta el pipeline completo de búsqueda, evaluación y generación APA 7."""
    console.print(f"\n[bold blue]🔍 Consulta de Tesis / Afirmación a fundamentar:[/bold blue]\n[italic]\"{topic}\"[/italic]\n")

    # Inicializar motor de decisión
    judge = create_decision_judge(preferred_engine=engine)
    console.print(f"[bold]⚙️ Motor de Decisión activo:[/bold] [yellow]{judge.engine_name}[/yellow]")
    if judge.engine_name == "unsloth_laya":
        if judge.is_available():
            console.print("[green]✔ Servidor Unsloth Desktop (Laya / Jev API) conectado en localhost:8888[/green]")
        else:
            console.print("[yellow]ℹ Servidor Unsloth Desktop no detectado en localhost:8888. (Para activarlo: Abre Unsloth Desktop -> Settings -> Decision API -> Serve requests)[/yellow]")
    elif judge.engine_name == "heuristic_academic":
        console.print("[cyan]ℹ Evaluador semántico académico activo (clasificación y filtrado sin necesidad de GPU)[/cyan]")

    agent = ThesisConsensusAgent(decision_judge=judge)

    with console.status("[bold green]Buscando papers en bases indexadas y evaluando pertinencia..."):
        conserved, discarded = agent.research_and_fundament(
            topic_or_claim=topic,
            limit_search=limit,
            min_year=min_year,
        )

    # Mostrar tabla resumen de decisiones
    table = Table(title="📊 Evaluación y Filtrado de Literatura Científica", border_style="cyan")
    table.add_column("Estado", justify="center", style="bold", width=12)
    table.add_column("Año", justify="center", width=6)
    table.add_column("Citas", justify="center", width=7)
    table.add_column("Tipo Evidencia", style="magenta", width=18)
    table.add_column("Título del Paper", style="white")

    for item in conserved:
        table.add_row(
            "[green]CONSERVAR[/green]",
            str(item.paper.year or "-"),
            str(item.paper.citation_count),
            item.decision.evidence_type,
            item.paper.title[:75] + ("..." if len(item.paper.title) > 75 else "")
        )

    for p in discarded:
        table.add_row(
            "[red]DESCARTAR[/red]",
            str(p.year or "-"),
            str(p.citation_count),
            "[dim]No relevante[/dim]",
            f"[dim]{p.title[:75]}...[/dim]"
        )

    console.print(table)
    console.print(f"\n[bold]Resumen:[/bold] [green]{len(conserved)} conservados[/green] | [red]{len(discarded)} descartados[/red] de un total de {len(conserved) + len(discarded)} revisados.\n")

    # Mostrar las citas en formato APA 7 para cada paper conservado
    console.print(Panel("[bold yellow]📝 Párrafos para Fundamentos Teóricos y Referencias APA 7[/bold yellow]"))

    synthesizer = ThesisSynthesizer(language="es")

    for idx, item in enumerate(conserved, start=1):
        console.print(f"\n[bold cyan]── Paper {idx}: {item.paper.title} ──[/bold cyan]")
        console.print(f"[bold green]Cita Narrativa:[/bold green]   {item.apa7.narrative_citation}")
        console.print(f"[bold green]Cita Parentética:[/bold green] {item.apa7.parenthetical_citation}")
        console.print(f"[bold white]Texto sugerido para Marco Teórico:[/bold white]\n[italic]\"{item.narrative_paragraph}\"[/italic]")
        console.print(f"[bold magenta]Referencia Completa (APA 7):[/bold magenta]\n{item.apa7.full_reference}")
        if item.paper.doi:
            console.print(f"[blue]DOI:[/blue] {item.paper.doi}")

    # Exportar a archivos
    md_path = ThesisExporter.to_markdown(conserved, topic, out_md, synthesizer)
    console.print(f"\n[bold green]✔ Marco teórico exportado a:[/bold green] [underline]{md_path}[/underline]")

    if out_bib:
        bib_path = ThesisExporter.to_bibtex(conserved, out_bib)
        console.print(f"[bold green]✔ Entradas BibTeX exportadas a:[/bold green] [underline]{bib_path}[/underline]")

    return conserved


def interactive_menu() -> None:
    """Modo interactivo para seleccionar o escribir preguntas de tesis."""
    display_welcome_banner()

    predefined_topics = [
        "How is IT Service Management (ITSM) or ITIL implemented in higher education institutions and university help desks?",
        "What are the challenges, ticket volume overloads, and bottlenecks in university IT support and help desk services?",
        "Impact of ITIL incident management and service level agreements (SLAs) on academic IT satisfaction",
    ]

    console.print("[bold yellow]Seleccione una de las preguntas de tesis de prueba o escriba la suya:[/bold yellow]")
    for i, t in enumerate(predefined_topics, start=1):
        console.print(f"  [cyan][{i}][/cyan] {t}")
    console.print("  [cyan][0][/cyan] Escribir una nueva afirmación / pregunta personalizada")

    choice = console.input("\n[bold green]Opción (1-3 o 0): [/bold green]").strip()

    if choice in ("1", "2", "3"):
        selected_topic = predefined_topics[int(choice) - 1]
    else:
        selected_topic = console.input("\n[bold green]Ingrese el tema o afirmación a buscar: [/bold green]").strip()
        if not selected_topic:
            selected_topic = predefined_topics[0]

    run_pipeline(topic=selected_topic)


def main() -> None:
    """Punto de entrada principal para CLI."""
    parser = argparse.ArgumentParser(
        description="Thesis Consensus: Buscador y evaluador de literatura para marco teórico con APA 7."
    )
    parser.add_argument("--topic", "-t", type=str, help="Tema o afirmación de tesis a fundamentar")
    parser.add_argument("--limit", "-l", type=int, default=12, help="Cantidad de papers a buscar (default: 12)")
    parser.add_argument("--min-year", "-y", type=int, default=2014, help="Año mínimo de publicación (default: 2014)")
    parser.add_argument("--engine", "-e", choices=["auto", "laya", "openai", "heuristic"], default="auto", help="Motor de decisión a emplear")
    parser.add_argument("--out-md", "-o", type=str, default="fundamentos_teoricos.md", help="Ruta del archivo Markdown a exportar")
    parser.add_argument("--out-bib", "-b", type=str, default="referencias.bib", help="Ruta del archivo BibTeX a exportar")
    parser.add_argument("--interactive", "-i", action="store_true", help="Lanzar en modo interactivo")

    args = parser.parse_args()

    if args.interactive or (len(sys.argv) == 1 and not args.topic):
        interactive_menu()
    elif args.topic:
        display_welcome_banner()
        run_pipeline(
            topic=args.topic,
            limit=args.limit,
            min_year=args.min_year,
            engine=args.engine,
            out_md=args.out_md,
            out_bib=args.out_bib,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
