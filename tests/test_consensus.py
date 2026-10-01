"""
Pruebas unitarias para el sistema Thesis Consensus.
Verifica:
- Formato estricto de citas y referencias APA 7ma Edición.
- Reconstrucción de abstracts invertidos sin malware.
- Lógica de decisión (conservar vs descartar).
- Cero dependencias de Any.
"""

import unittest
from thesis_consensus.models import Author, PaperMetadata, DecisionEvaluation
from thesis_consensus.apa7 import (
    format_in_text_citations,
    format_full_reference_apa7,
    build_apa7_citation,
    _to_sentence_case,
)
from thesis_consensus.providers.openalex import OpenAlexProvider
from thesis_consensus.decision.heuristic import HeuristicAcademicJudge
from thesis_consensus.synthesizer import ThesisSynthesizer


class TestThesisConsensus(unittest.TestCase):

    def test_apa7_author_citations(self) -> None:
        """Verifica las reglas APA 7 para 1, 2 y 3+ autores."""
        author1 = Author(full_name="Juan Adán", family_name="Adán", given_name="Juan")
        author2 = Author(full_name="María Pérez", family_name="Pérez", given_name="María")
        author3 = Author(full_name="Carlos Gómez", family_name="Gómez", given_name="Carlos")

        # 1 Autor
        narrative, parenthetical = format_in_text_citations([author1], "2017", language="es")
        self.assertEqual(narrative, "Adán (2017)")
        self.assertEqual(parenthetical, "(Adán, 2017)")

        # 2 Autores
        narrative2, parenthetical2 = format_in_text_citations([author1, author2], "2018", language="es")
        self.assertEqual(narrative2, "Adán y Pérez (2018)")
        self.assertEqual(parenthetical2, "(Adán y Pérez, 2018)")

        # 3 Autores (APA 7 exige 'et al.' desde la primera cita)
        narrative3, parenthetical3 = format_in_text_citations([author1, author2, author3], "2020", language="es")
        self.assertEqual(narrative3, "Adán et al. (2020)")
        self.assertEqual(parenthetical3, "(Adán et al., 2020)")

    def test_sentence_case_preserves_acronyms(self) -> None:
        """Verifica que el título en sentence case conserve acrónimos clave como ITIL e ITSM."""
        raw_title = "IMPLEMENTING ITIL IN HIGHER EDUCATION: A CASE STUDY OF ITSM ADOPTION"
        formatted = _to_sentence_case(raw_title)
        self.assertIn("ITIL", formatted)
        self.assertIn("ITSM", formatted)
        self.assertTrue(formatted.startswith("Implementing"))

    def test_full_reference_apa7(self) -> None:
        """Verifica la generación de la referencia bibliográfica completa."""
        paper = PaperMetadata(
            paper_id="W1234",
            title="Managing Service Level for Academic Help Desk Based on ITIL Framework",
            authors=[
                Author(full_name="John Adan", family_name="Adan", given_name="John"),
                Author(full_name="Robert Smith", family_name="Smith", given_name="Robert"),
            ],
            year=2020,
            venue="Journal of Higher Education Technology",
            volume="14",
            issue="2",
            pages="45–59",
            doi="https://doi.org/10.1016/j.jhet.2020.03.011",
            abstract="Study of ITIL help desk tickets.",
        )

        apa = build_apa7_citation(paper, language="es")
        self.assertIn("Adan, J., & Smith, R. (2020).", apa.full_reference)
        self.assertIn("*Journal of Higher Education Technology*, *14*(2), 45–59.", apa.full_reference)
        self.assertIn("https://doi.org/10.1016/j.jhet.2020.03.011", apa.full_reference)

    def test_openalex_abstract_reconstruction(self) -> None:
        """Verifica la reconstrucción segura del abstract a partir del índice invertido."""
        provider = OpenAlexProvider()
        inverted = {
            "This": [0],
            "paper": [1],
            "evaluates": [2],
            "ITIL": [3],
            "implementation": [4],
            "in": [5],
            "universities.": [6],
        }
        reconstructed = provider._reconstruct_abstract(inverted)
        self.assertEqual(reconstructed, "This paper evaluates ITIL implementation in universities.")

    def test_decision_judge_relevance(self) -> None:
        """Verifica que el evaluador distinga artículos relevantes de no relevantes."""
        judge = HeuristicAcademicJudge()

        relevant_paper = PaperMetadata(
            paper_id="P1",
            title="An empirical study of ITIL incident management and ticket overloads in university help desk",
            authors=[Author(full_name="A. Smith", family_name="Smith", given_name="A.")],
            year=2021,
            venue="IEEE Transactions on Education Services",
            abstract="We analyze 25,000 IT support tickets in university campus help desks and identify major bottlenecks during enrollment.",
            citation_count=18,
            doi="https://doi.org/10.1109/test.2021",
        )

        irrelevant_paper = PaperMetadata(
            paper_id="P2",
            title="Quantum entanglement in photosynthetic light-harvesting complexes",
            authors=[Author(full_name="B. Jones", family_name="Jones", given_name="B.")],
            year=2022,
            abstract="We investigate molecular quantum coherence in biological systems.",
            citation_count=5,
        )

        topic = "What are the challenges, ticket volume overloads, and bottlenecks in university IT support and help desk services?"

        eval_rel = judge.evaluate(relevant_paper, topic)
        self.assertTrue(eval_rel.is_relevant)
        self.assertIn(eval_rel.evidence_type, ("case_study", "survey_or_data"))

        eval_irrel = judge.evaluate(irrelevant_paper, topic)
        self.assertFalse(eval_irrel.is_relevant)
        self.assertEqual(eval_irrel.evidence_type, "irrelevant")

    def test_synthesizer_narrative_generation(self) -> None:
        """Verifica que el sintetizador genere el párrafo narrativo académico."""
        synthesizer = ThesisSynthesizer(language="es")
        paper = PaperMetadata(
            paper_id="P1",
            title="Analysis of ticket bottlenecks in higher education IT services",
            authors=[Author(full_name="Carlos Gomez", family_name="Gomez", given_name="Carlos")],
            year=2022,
            abstract="Results demonstrate that automating ticket triage reduces resolution time by 35%.",
        )
        decision = DecisionEvaluation(
            is_relevant=True,
            relevance_score=0.85,
            evidence_type="survey_or_data",
            quality_score=2.2,
            verdict_reason="Alta relevancia empírica",
            decision_engine="heuristic_academic",
        )

        item = synthesizer.synthesize_item(paper, decision, "cuellos de botella en mesas de ayuda")
        self.assertIn("Gomez (2022)", item.narrative_paragraph)
        self.assertIn("(Gomez, 2022)", item.narrative_paragraph)
        self.assertTrue(len(item.narrative_paragraph) > 50)


if __name__ == "__main__":
    unittest.main()
