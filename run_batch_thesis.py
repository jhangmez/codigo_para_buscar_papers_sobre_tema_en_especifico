#!/usr/bin/env python3
"""
Script de ejecución por lote para las 27 preguntas pendientes del marco teórico de tesis.
Utiliza TypeSafe AI Jev (System One / 32K Context) con umbral mínimo de 80%.
"""

import json
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table

from thesis_consensus.agent import ThesisConsensusAgent
from thesis_consensus.decision.typesafe_jev import TypeSafeJevJudge
from thesis_consensus.exporter import ThesisExporter
from thesis_consensus.models import TopicResearchBatch

console = Console()


def main() -> None:
    plan_path = Path("queries_tesis.json")
    if not plan_path.exists():
        console.print("[bold red]Error: No se encontró queries_tesis.json[/bold red]")
        sys.exit(1)

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    pending_items = [item for item in plan if item.get("estado") == "PENDIENTE"]
    already_done = [item for item in plan if item.get("estado") != "PENDIENTE"]

    console.print("\n" + "=" * 80)
    console.print("[bold green]🎓 THESIS CONSENSUS - EJECUCIÓN DEL MARCO TEÓRICO EN LOTE[/bold green]")
    console.print(f"• Total de temas planificados: [bold]{len(plan)}[/bold]")
    console.print(f"• Temas previamente completados: [bold green]{len(already_done)}[/bold green]")
    console.print(f"• Temas pendientes por procesar: [bold yellow]{len(pending_items)}[/bold yellow]")
    console.print("=" * 80 + "\n")

    if not pending_items:
        console.print("[bold green]✔ Todos los temas ya han sido procesados.[/bold green]")
        return

    # Inicializar Juez TypeSafe Jev
    judge = TypeSafeJevJudge()
    if not judge.is_available():
        console.print("[bold red]Error: No se pudo autenticar con TypeSafe AI Jev. Verifique TYPESAFE_API_KEY en .env[/bold red]")
        sys.exit(1)

    agent = ThesisConsensusAgent(decision_judge=judge, language="es")
    console.print("[green]✔ Servidor TypeSafe AI Jev (32K tokens de contexto) autenticado y listo.[/green]\n")

    start_time = time.time()

    for idx, item in enumerate(pending_items, start=1):
        sec = item["seccion"]
        query = item["query_en"]
        out_folder = Path(item["carpeta_output"])
        out_folder.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[bold cyan]▶ [{idx}/{len(pending_items)}] Procesando:[/bold cyan] [bold white]{sec}[/bold white]")
        console.print(f"   [dim]Query:[/dim] [italic]{query}[/italic]")

        # Realizar investigación y evaluación con TypeSafe Jev
        try:
            conserved_items, discarded_papers, _ = agent.research_single_topic(
                topic_or_claim=query,
                limit_search=6,
                min_year=2015,
                threshold=0.80,
            )

            # Exportar archivos específicos de este tema
            single_batch = TopicResearchBatch(
                topics=[query],
                conserved_by_topic={query: conserved_items},
                discarded_by_topic={query: discarded_papers},
                syntheses_by_topic={},
                all_conserved_items=conserved_items,
                topic_sections={query: sec},
            )

            topic_md = str(out_folder / "fundamentos_teoricos.md")
            topic_bib = str(out_folder / "referencias.bib")
            topic_json = str(out_folder / "evidencia.json")

            ThesisExporter.to_batch_markdown(single_batch, topic_md)
            ThesisExporter.to_batch_bibtex(single_batch, topic_bib)
            ThesisExporter.to_topic_json(
                topic=query,
                conserved=conserved_items,
                discarded=discarded_papers,
                output_filepath=topic_json,
                section_title=sec,
            )

            # Actualizar estado en plan
            item["estado"] = "YA_EJECUTADO"
            item["conservados"] = len(conserved_items)
            item["descartados"] = len(discarded_papers)
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)

            # Resumen visual en consola
            if conserved_items:
                console.print(f"   [bold green]✔ {len(conserved_items)} papers conservados[/bold green] (descartados: {len(discarded_papers)})")
                for p_it in conserved_items:
                    cit = p_it.apa7.narrative_citation
                    prob = p_it.decision.relevance_score
                    rig = p_it.decision.quality_score
                    console.print(f"     • [green]{cit}[/green] | P(rel)={prob:.0%} | Rigor={rig:.1f}/3.0 | Tipo={p_it.decision.evidence_type}")
            else:
                console.print(f"   [yellow]⚠ 0 papers superaron el umbral del 80%[/yellow] ({len(discarded_papers)} evaluados y descartados)")

        except Exception as e:
            console.print(f"   [bold red]❌ Error al procesar este tema: {e}[/bold red]")

    elapsed = time.time() - start_time
    console.print("\n" + "=" * 80)
    console.print(f"[bold green]🎉 PROCESO EN LOTE COMPLETADO EN {elapsed/60:.1f} MINUTOS[/bold green]")
    console.print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
