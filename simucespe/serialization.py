from __future__ import annotations

from .models import Exam


def exam_to_dict(exam: Exam) -> dict:
    return {
        "metadata": exam.metadata.__dict__,
        "totals": {
            "blocks": len(exam.blocks),
            "items": len(exam.items),
            "valid_items": len(exam.valid_items),
            "annulled_items": len(exam.annulled_items),
            "annulled_numbers": [item.number for item in exam.annulled_items],
        },
        "blocks": [
            {
                "id": block.id,
                "source_exam_id": block.source_exam_id,
                "theme": block.theme,
                "theme_pending": block.theme_pending,
                "guide_statement": block.guide_statement,
                "items": [
                    {
                        "number": item.number,
                        "statement": item.statement,
                        "official_answer": item.official_answer,
                        "is_annulled": item.is_annulled,
                        "is_valid_for_simulado": item.is_valid_for_simulado,
                        "source_exam_id": item.source_exam_id,
                        "block_id": item.block_id,
                        "theme": item.theme,
                        "theme_pending": item.theme_pending,
                    }
                    for item in block.items
                ],
            }
            for block in exam.blocks
        ],
    }


def exam_summary_to_dict(pair_key: str, prova: str, gabarito: str, exam: Exam) -> dict:
    data = exam_to_dict(exam)
    return {
        "pair_key": pair_key,
        "prova": prova,
        "gabarito": gabarito,
        "metadata": data["metadata"],
        "totals": data["totals"],
    }

