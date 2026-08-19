from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models import Answer
from .settings import cors_origins_from_env
from .simulado import build_full_exam_simulado, build_theme_simulado, calculate_result
from .store import ActiveSimuladoStore, ExamStore, HistoryStore, simulado_public_dict


class CreateSimuladoRequest(BaseModel):
    mode: Literal["prova_completa", "por_tema"]
    source_exam_id: str | None = None
    themes: list[str] = Field(default_factory=list)
    quantity: int | None = None
    timer_seconds: int | None = None


class SubmitAnswersRequest(BaseModel):
    answers: dict[int, Answer]


def create_app(
    parsed_dir: Path = Path("data/parsed"),
    history_path: Path = Path("data/runtime/history.json"),
    cors_origins: list[str] | None = None,
) -> FastAPI:
    app = FastAPI(title="SimuCESPE API", version="0.1.0")
    origins = cors_origins if cors_origins is not None else cors_origins_from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    exams = ExamStore(parsed_dir)
    active_simulados = ActiveSimuladoStore()
    history = HistoryStore(history_path)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/provas")
    def list_provas() -> list[dict]:
        return exams.list_exams()

    @app.get("/provas/{source_id}")
    def get_prova(source_id: str) -> dict:
        try:
            exam = exams.get_exam(source_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prova não encontrada") from exc
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
                    "guide_statement": block.guide_statement,
                    "theme": block.theme,
                    "theme_pending": block.theme_pending,
                    "items": [
                        {
                            "number": item.number,
                            "statement": item.statement,
                            "is_annulled": item.is_annulled,
                            "is_valid_for_simulado": item.is_valid_for_simulado,
                            "theme": item.theme,
                            "theme_pending": item.theme_pending,
                        }
                        for item in block.items
                    ],
                }
                for block in exam.blocks
            ],
        }

    @app.post("/simulados", status_code=status.HTTP_201_CREATED)
    def create_simulado(request: CreateSimuladoRequest) -> dict:
        try:
            if request.mode == "prova_completa":
                if not request.source_exam_id:
                    raise ValueError("source_exam_id é obrigatório para prova completa")
                exam = exams.get_exam(request.source_exam_id)
                simulado = build_full_exam_simulado(exam, timer_seconds=request.timer_seconds)
                guide_by_block = _guide_by_block(exam)
            else:
                if request.quantity is None:
                    raise ValueError("quantity é obrigatório para simulado por tema")
                all_items = []
                guide_by_block = {}
                for exam_summary in exams.list_exams():
                    exam = exams.get_exam(exam_summary["source_id"])
                    all_items.extend(exam.items)
                    guide_by_block.update(_guide_by_block(exam))
                simulado = build_theme_simulado(
                    all_items,
                    themes=tuple(request.themes),
                    quantity=request.quantity,
                    timer_seconds=request.timer_seconds,
                )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prova não encontrada") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        active_simulados.add(simulado, guide_by_block)
        return simulado_public_dict(simulado, guide_by_block)

    @app.get("/simulados/{simulado_id}")
    def get_simulado(simulado_id: str) -> dict:
        try:
            active = active_simulados.get(simulado_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado") from exc
        return simulado_public_dict(active.simulado, active.guide_by_block)

    @app.post("/simulados/{simulado_id}/respostas")
    def submit_answers(simulado_id: str, request: SubmitAnswersRequest) -> dict:
        try:
            active = active_simulados.get(simulado_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado") from exc
        simulado = active.simulado

        expected_numbers = {item.number for item in simulado.items}
        received_numbers = set(request.answers)
        missing = sorted(expected_numbers - received_numbers)
        extra = sorted(received_numbers - expected_numbers)
        if missing or extra:
            raise HTTPException(
                status_code=422,
                detail={"missing": missing, "extra": extra},
            )

        result = calculate_result(simulado, request.answers)
        response = {
            "simulado_id": result.simulado_id,
            "total_items": result.total_items,
            "correct_items": result.correct_items,
            "percent_correct": result.percent_correct,
            "reviews": [
                {
                    "item_number": review.item_number,
                    "user_answer": review.user_answer,
                    "official_answer": review.official_answer,
                    "is_correct": review.is_correct,
                }
                for review in result.reviews
            ],
        }
        history.append(
            {
                "completed_at": datetime.now(UTC).isoformat(),
                "simulado": simulado_public_dict(simulado, active.guide_by_block),
                "result": response,
            }
        )
        active_simulados.remove(simulado_id)
        return response

    @app.get("/historico")
    def list_historico() -> list[dict]:
        return history.list()

    return app


def _guide_by_block(exam) -> dict[str, str]:
    return {block.id: block.guide_statement for block in exam.blocks}


app = create_app()
