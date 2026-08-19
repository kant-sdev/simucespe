from __future__ import annotations

import unittest
from pathlib import Path

from simucespe.ingestion import parse_gabarito_answers, parse_metadata, parse_prova_blocks
from simucespe.models import Exam, ExamMetadata
from simucespe.simulado import build_full_exam_simulado


class IngestionTest(unittest.TestCase):
    def test_gabarito_ignores_zero_padding_and_marks_annulled(self) -> None:
        answers = parse_gabarito_answers(
            """
            1 2 3 4
            C E X C
            0 0 0 0
            Item
            Gabarito
            """
        )

        self.assertEqual(answers, {1: "C", 2: "E", 3: "X", 4: "C"})

    def test_gabarito_parses_compact_cebraspe_layout(self) -> None:
        answers = parse_gabarito_answers(
            """
            1 23456789 1 0 1 1 1 2 1 3 1 4 1 5 1 6 1 7 1 8 1 9 2 0
            C EECCEECECEECE C CE E EE
            41 42 43 44 45 46 47 48 49 50 0 0 0 000 000 0
            C ECECECEXC 0 0 0 000 000 0
            """
        )

        self.assertEqual(len(answers), 30)
        self.assertEqual(answers[1], "C")
        self.assertEqual(answers[20], "E")
        self.assertEqual(answers[49], "X")
        self.assertEqual(answers[50], "C")

    def test_prova_uses_gabarito_sequence_to_ignore_numbers_inside_statement(self) -> None:
        blocks = parse_prova_blocks(
            """
            -- PROVA OBJETIVA --
            Julgue os itens seguintes.
            1 O valor tem acréscimo para cada ano que exceder o tempo de
            20 anos de contribuição.
            2 O segundo item segue normalmente.
            """,
            "exam",
            {1: "C", 2: "E"},
        )

        self.assertEqual([item.number for item in blocks[0].items], [1, 2])
        self.assertIn("20 anos de contribuição", blocks[0].items[0].statement)

    def test_full_exam_simulado_excludes_annulled_items(self) -> None:
        blocks = parse_prova_blocks(
            """
            -- PROVA OBJETIVA --
            Julgue os itens seguintes.
            1 Primeiro item.
            2 Segundo item.
            """,
            "exam",
            {1: "X", 2: "E"},
        )
        exam = Exam(ExamMetadata(source_id="exam", bank="CEBRASPE"), tuple(blocks))

        simulado = build_full_exam_simulado(exam)

        self.assertEqual([item.number for item in simulado.items], [2])

    def test_metadata_accepts_single_digit_application_date(self) -> None:
        metadata = parse_metadata(
            "EDITAL Nº 16 – INSS, DE 24 DE FEVEREIRO DE 2023\nAplicação: 9/4/2023",
            Path("prova.pdf"),
            "pdf_text_fallback",
        )

        self.assertEqual(metadata.application_date, "9/4/2023")


if __name__ == "__main__":
    unittest.main()
