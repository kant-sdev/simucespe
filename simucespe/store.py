from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Exam, ExamMetadata, QuestionItem, Simulado, ThematicBlock


@dataclass(frozen=True)
class ActiveSimulado:
    simulado: Simulado
    guide_by_block: dict[str, str]


class ExamStore:
    def __init__(self, parsed_dir: Path = Path("data/parsed")) -> None:
        self.parsed_dir = parsed_dir

    def list_exams(self) -> list[dict[str, Any]]:
        exams: list[dict[str, Any]] = []
        for path in sorted(self.parsed_dir.glob("*.json")):
            if path.name == "ingestion_report.json":
                continue
            data = _read_json(path)
            exams.append(
                {
                    "source_id": data["metadata"]["source_id"],
                    "metadata": data["metadata"],
                    "totals": data["totals"],
                }
            )
        return exams

    def get_exam(self, source_id: str) -> Exam:
        path = self.parsed_dir / f"{source_id}.json"
        if not path.exists():
            raise KeyError(source_id)
        return exam_from_dict(_read_json(path))


class ActiveSimuladoStore:
    def __init__(self) -> None:
        self._simulados: dict[str, ActiveSimulado] = {}

    def add(self, simulado: Simulado, guide_by_block: dict[str, str]) -> None:
        self._simulados[simulado.id] = ActiveSimulado(simulado=simulado, guide_by_block=guide_by_block)

    def get(self, simulado_id: str) -> ActiveSimulado:
        try:
            return self._simulados[simulado_id]
        except KeyError as exc:
            raise KeyError(simulado_id) from exc

    def remove(self, simulado_id: str) -> None:
        self._simulados.pop(simulado_id, None)


class HistoryStore:
    def __init__(self, history_path: Path = Path("data/runtime/history.json")) -> None:
        self.history_path = history_path

    def list(self) -> list[dict[str, Any]]:
        return self._read()

    def append(self, entry: dict[str, Any]) -> None:
        history = self._read()
        history.append(entry)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        return json.loads(self.history_path.read_text(encoding="utf-8"))


def exam_from_dict(data: dict[str, Any]) -> Exam:
    metadata = ExamMetadata(**data["metadata"])
    blocks: list[ThematicBlock] = []
    for block_data in data["blocks"]:
        items = tuple(QuestionItem(**_question_item_fields(item_data)) for item_data in block_data["items"])
        block = ThematicBlock(
            id=block_data["id"],
            guide_statement=block_data["guide_statement"],
            source_exam_id=block_data["source_exam_id"],
            theme=block_data.get("theme"),
            theme_pending=block_data.get("theme_pending", True),
            items=items,
        )
        blocks.append(block)
    return Exam(metadata=metadata, blocks=tuple(blocks))


def simulado_public_dict(
    simulado: Simulado,
    guide_by_block: dict[str, str],
    include_answers: bool = False,
) -> dict[str, Any]:
    blocks: dict[str, dict[str, Any]] = {}
    for item in simulado.items:
        blocks.setdefault(
            item.block_id,
            {
                "id": item.block_id,
                "source_exam_id": item.source_exam_id,
                "guide_statement": guide_by_block[item.block_id],
                "items": [],
            },
        )
        item_data = {
            "number": item.number,
            "statement": item.statement,
            "source_exam_id": item.source_exam_id,
            "block_id": item.block_id,
            "theme": item.theme,
            "theme_pending": item.theme_pending,
        }
        if include_answers:
            item_data["official_answer"] = item.official_answer
        blocks[item.block_id]["items"].append(item_data)

    return {
        "id": simulado.id,
        "mode": simulado.mode,
        "source_exam_id": simulado.source_exam_id,
        "themes": list(simulado.themes),
        "timer_seconds": simulado.timer_seconds,
        "total_items": len(simulado.items),
        "blocks": list(blocks.values()),
    }
def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _question_item_fields(item_data: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "number",
        "statement",
        "official_answer",
        "is_annulled",
        "source_exam_id",
        "block_id",
        "theme",
        "theme_pending",
    }
    return {key: value for key, value in item_data.items() if key in allowed}
