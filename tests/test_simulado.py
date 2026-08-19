from __future__ import annotations

import unittest

from simucespe.ingestion import parse_prova_blocks
from simucespe.models import Exam, ExamMetadata
from simucespe.simulado import build_full_exam_simulado, calculate_result


class SimuladoTest(unittest.TestCase):
    def test_timer_seconds_must_be_positive_when_provided(self) -> None:
        exam = _exam_with_two_valid_items()

        with self.assertRaisesRegex(ValueError, "RV03"):
            build_full_exam_simulado(exam, timer_seconds=0)

    def test_result_percentage_uses_presented_valid_items(self) -> None:
        exam = _exam_with_two_valid_items()
        simulado = build_full_exam_simulado(exam)

        result = calculate_result(simulado, {1: "C", 2: "C"})

        self.assertEqual(result.total_items, 2)
        self.assertEqual(result.correct_items, 1)
        self.assertEqual(result.percent_correct, 50.0)


def _exam_with_two_valid_items() -> Exam:
    blocks = parse_prova_blocks(
        """
        -- PROVA OBJETIVA --
        Julgue os itens seguintes.
        1 Primeiro item.
        2 Segundo item.
        """,
        "exam",
        {1: "C", 2: "E"},
    )
    return Exam(ExamMetadata(source_id="exam", bank="CEBRASPE"), tuple(blocks))


if __name__ == "__main__":
    unittest.main()
