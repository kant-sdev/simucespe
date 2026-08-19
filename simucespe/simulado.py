from __future__ import annotations

from uuid import uuid4

from .models import Answer, AnswerReview, Exam, QuestionItem, Simulado, SimuladoResult


def build_full_exam_simulado(exam: Exam, timer_seconds: int | None = None) -> Simulado:
    _validate_timer(timer_seconds)
    valid_items = exam.valid_items
    if not valid_items:
        raise ValueError("RV02: não é possível iniciar um simulado sem item válido")
    return Simulado(
        id=str(uuid4()),
        mode="prova_completa",
        source_exam_id=exam.metadata.source_id,
        items=valid_items,
        timer_seconds=timer_seconds,
    )


def build_theme_simulado(
    items: list[QuestionItem],
    themes: tuple[str, ...],
    quantity: int,
    timer_seconds: int | None = None,
) -> Simulado:
    _validate_timer(timer_seconds)
    valid_items = [item for item in items if item.is_valid_for_simulado and item.theme in themes]
    if quantity > len(valid_items):
        raise ValueError("RV01: quantidade solicitada excede os itens válidos disponíveis para o(s) tema(s)")
    selected = tuple(valid_items[:quantity])
    if not selected:
        raise ValueError("RV02: não é possível iniciar um simulado sem item válido")
    return Simulado(id=str(uuid4()), mode="por_tema", themes=themes, items=selected, timer_seconds=timer_seconds)


def calculate_result(simulado: Simulado, user_answers: dict[int, Answer]) -> SimuladoResult:
    reviews: list[AnswerReview] = []
    for item in simulado.items:
        if item.official_answer not in ("C", "E"):
            continue
        user_answer = user_answers[item.number]
        reviews.append(
            AnswerReview(
                item_number=item.number,
                user_answer=user_answer,
                official_answer=item.official_answer,
                is_correct=user_answer == item.official_answer,
            )
        )

    total = len(reviews)
    correct = sum(1 for review in reviews if review.is_correct)
    percent = (correct / total * 100) if total else 0.0
    return SimuladoResult(
        simulado_id=simulado.id,
        total_items=total,
        correct_items=correct,
        percent_correct=round(percent, 2),
        reviews=tuple(reviews),
    )


def _validate_timer(timer_seconds: int | None) -> None:
    if timer_seconds is not None and timer_seconds <= 0:
        raise ValueError("RV03: quando o cronômetro é ativado, o tempo total deve ser maior que zero")
