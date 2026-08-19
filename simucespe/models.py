from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Answer = Literal["C", "E"]
MountMode = Literal["prova_completa", "por_tema"]


@dataclass(frozen=True)
class ExamMetadata:
    source_id: str
    bank: str
    title: str | None = None
    edital: str | None = None
    application_date: str | None = None
    source_format: str = "unknown"


@dataclass(frozen=True)
class QuestionItem:
    number: int
    statement: str
    official_answer: Answer | None
    is_annulled: bool
    source_exam_id: str
    block_id: str
    theme: str | None = None
    theme_pending: bool = True

    @property
    def is_valid_for_simulado(self) -> bool:
        return not self.is_annulled and self.official_answer in ("C", "E")


@dataclass(frozen=True)
class ThematicBlock:
    id: str
    guide_statement: str
    source_exam_id: str
    theme: str | None = None
    theme_pending: bool = True
    items: tuple[QuestionItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Exam:
    metadata: ExamMetadata
    blocks: tuple[ThematicBlock, ...]

    @property
    def items(self) -> tuple[QuestionItem, ...]:
        return tuple(item for block in self.blocks for item in block.items)

    @property
    def valid_items(self) -> tuple[QuestionItem, ...]:
        return tuple(item for item in self.items if item.is_valid_for_simulado)

    @property
    def annulled_items(self) -> tuple[QuestionItem, ...]:
        return tuple(item for item in self.items if item.is_annulled)


@dataclass(frozen=True)
class Simulado:
    id: str
    mode: MountMode
    items: tuple[QuestionItem, ...]
    source_exam_id: str | None = None
    themes: tuple[str, ...] = ()
    timer_seconds: int | None = None


@dataclass(frozen=True)
class AnswerReview:
    item_number: int
    user_answer: Answer
    official_answer: Answer
    is_correct: bool


@dataclass(frozen=True)
class SimuladoResult:
    simulado_id: str
    total_items: int
    correct_items: int
    percent_correct: float
    reviews: tuple[AnswerReview, ...]

