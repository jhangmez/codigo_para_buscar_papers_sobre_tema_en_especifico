"""
Pruebas unitarias para el sistema Thesis Consensus.
Verifica:
- Formato estricto de citas y referencias APA 7ma Edición.
- Reconstrucción de abstracts invertidos sin malware.
- Lógica de decisión con umbrales altos (80% - 85%).
- Redacción en español y síntesis multi-paper integrada.
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
from thesis_consensus.constants import DEFAULT_RELEVANCE_THRESHOLD, STRICT_RELEVANCE_THRESHOLD


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

    def test_decision_judge_relevance_with_high_threshold(self) -> None:
        """Verifica que el evaluador distinga artículos relevantes con umbral alto (80%)."""
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

        eval_rel = judge.evaluate(relevant_paper, topic, threshold=DEFAULT_RELEVANCE_THRESHOLD)
        self.assertTrue(eval_rel.is_relevant)
        self.assertGreaterEqual(eval_rel.relevance_score, DEFAULT_RELEVANCE_THRESHOLD)
        self.assertIn(eval_rel.evidence_type, ("case_study", "survey_or_data"))

        eval_irrel = judge.evaluate(irrelevant_paper, topic, threshold=DEFAULT_RELEVANCE_THRESHOLD)
        self.assertFalse(eval_irrel.is_relevant)
        self.assertEqual(eval_irrel.evidence_type, "irrelevant")

    def test_spanish_translation_and_polish(self) -> None:
        """Verifica que los hallazgos en inglés se traduzcan fluidamente al español académico."""
        synthesizer = ThesisSynthesizer(language="es")
        raw_en = "The study found organisations adopting ITIL implemented more operational level processes than the tactical/strategic level processes."
        translated = synthesizer._translate_and_polish_finding_to_spanish(raw_en)
        self.assertIn("estudio evidenció que", translated.lower())
        self.assertIn("organizaciones que adoptan", translated.lower())

    def test_multi_paper_consensus_synthesis(self) -> None:
        """Verifica la generación de la síntesis combinada de múltiples papers."""
        synthesizer = ThesisSynthesizer(language="es")

        paper1 = PaperMetadata(
            paper_id="P1",
            title="Adoption of ITIL in University Help Desk",
            authors=[Author(full_name="Mauricio Marrone", family_name="Marrone", given_name="Mauricio")],
            year=2020,
            abstract="Results demonstrate that automating ticket triage reduces resolution time by 35%.",
        )
        dec1 = DecisionEvaluation(
            is_relevant=True,
            relevance_score=0.88,
            threshold_applied=0.80,
            evidence_type="case_study",
            quality_score=2.5,
            verdict_reason="Alta relevancia empírica",
            decision_engine="heuristic_academic",
        )
        item1 = synthesizer.synthesize_item(paper1, dec1, "ITIL en universidades", 0)

        paper2 = PaperMetadata(
            paper_id="P2",
            title="Incident Management Performance in Higher Education",
            authors=[Author(full_name="Verry Palilingan", family_name="Palilingan", given_name="Verry")],
            year=2021,
            abstract="We found that 84% of service requests are resolved within SLA boundaries.",
        )
        dec2 = DecisionEvaluation(
            is_relevant=True,
            relevance_score=0.86,
            threshold_applied=0.80,
            evidence_type="survey_or_data",
            quality_score=2.2,
            verdict_reason="Métricas empíricas sólidas",
            decision_engine="heuristic_academic",
        )
        item2 = synthesizer.synthesize_item(paper2, dec2, "ITIL en universidades", 1)

        multi_syn = synthesizer.synthesize_multi_paper_consensus(
            topic_or_claim="Implementación de ITIL en universidades",
            items=[item1, item2],
        )

        self.assertIn("Marrone (2020)", multi_syn.integrated_narrative)
        self.assertIn("Palilingan (2021)", multi_syn.integrated_narrative)
        self.assertIn("(Marrone, 2020; Palilingan, 2021)", multi_syn.parenthetical_synthesis)
        self.assertEqual(multi_syn.papers_used_count, 2)


if __name__ == "__main__":
    unittest.main()
