from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from .document_reader import read_structured_document
from .models import Exam, ExamMetadata, QuestionItem, ThematicBlock

ITEM_START_RE = re.compile(r"(?m)^\s*(\d{1,3})\s+(?=\S)")
ZERO_LINE_RE = re.compile(r"^(?:0\s*)+$")
GUIDE_START_RE = re.compile(
    r"(?ms)(?:\n|(?<=\.)\s+)(?=(?:Julgue|Acerca|No que|Em relação|Considerando|João,|Malu,)(?:\b|\s))"
)


def pair_key(path: Path) -> str:
    stem = _drop_copy_suffix(path.stem)
    for suffix in ("-prova", "-gabarito", "prova", "gabarito"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)].rstrip("-_ ")
    return stem


def find_exam_pairs(directory: Path) -> dict[str, tuple[Path, Path]]:
    provas: dict[str, Path] = {}
    gabaritos: dict[str, Path] = {}
    for path in sorted(directory.glob("*.pdf")):
        normalized = _drop_copy_suffix(path.stem)
        if normalized.endswith("prova"):
            _set_preferred_path(provas, pair_key(path), path)
        elif normalized.endswith("gabarito"):
            _set_preferred_path(gabaritos, pair_key(path), path)
    return {key: (provas[key], gabaritos[key]) for key in sorted(provas.keys() & gabaritos.keys())}


def ingest_exam_pair(prova_path: Path, gabarito_path: Path) -> Exam:
    prova_doc = read_structured_document(prova_path)
    gabarito_doc = read_structured_document(gabarito_path)
    answers = parse_gabarito_answers(gabarito_doc.text)
    metadata = parse_metadata(gabarito_doc.text, prova_path, prova_doc.source_format)
    blocks = parse_prova_blocks(prova_doc.text, metadata.source_id, answers)
    return Exam(metadata=metadata, blocks=tuple(blocks))


def parse_gabarito_answers(text: str) -> dict[int, str]:
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line and not ZERO_LINE_RE.fullmatch(line)]
    answers: dict[int, str] = {}

    index = 0
    while index < len(lines) - 1:
        numbers = _parse_number_row(lines[index])
        answer_tokens = _parse_answer_row(lines[index + 1], len(numbers))
        if numbers and len(numbers) == len(answer_tokens):
            for number, answer in zip(numbers, answer_tokens, strict=True):
                answers[number] = answer.upper()
            index += 2
        else:
            index += 1

    if not answers:
        raise ValueError("No C/E/X answer blocks were found in the gabarito")
    return answers


def parse_prova_blocks(text: str, source_exam_id: str, answers: dict[int, str]) -> list[ThematicBlock]:
    body = _extract_objective_body(text)
    matches = _sequential_item_matches(body, answers)
    if not matches:
        raise ValueError("No numbered CEBRASPE items were found in the prova")

    blocks: list[ThematicBlock] = []
    current_guide = _normalize_text(body[: matches[0].start()])
    current_items: list[QuestionItem] = []

    for index, match in enumerate(matches):
        number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        segment = body[start:end]
        statement, trailing_guide = _split_trailing_guide(segment)

        if not current_guide:
            current_guide = "Enunciado-guia pendente de revisão"

        answer = answers.get(number)
        item = QuestionItem(
            number=number,
            statement=_normalize_text(statement),
            official_answer=answer if answer in {"C", "E"} else None,
            is_annulled=answer == "X",
            source_exam_id=source_exam_id,
            block_id=_block_id(source_exam_id, len(blocks) + 1),
        )
        current_items.append(item)

        if trailing_guide:
            blocks.append(_build_block(source_exam_id, len(blocks) + 1, current_guide, current_items))
            current_items = []
            current_guide = _normalize_text(trailing_guide)

    if current_items:
        blocks.append(_build_block(source_exam_id, len(blocks) + 1, current_guide, current_items))

    expected_numbers = set(answers)
    parsed_numbers = {item.number for block in blocks for item in block.items}
    missing = sorted(expected_numbers - parsed_numbers)
    if missing:
        raise ValueError(f"Gabarito has answers for items not found in prova: {missing[:10]}")

    return blocks


def parse_metadata(text: str, prova_path: Path, source_format: str) -> ExamMetadata:
    edital = _first_match(r"EDITAL\s+N[ºo.]*\s*([^\n]+)", text)
    application_date = _first_match(r"Aplicação:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", text)
    title = _first_match(r"(CARGO DE [A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+)", text)
    return ExamMetadata(
        source_id=pair_key(prova_path),
        bank="CEBRASPE",
        title=title,
        edital=edital,
        application_date=application_date,
        source_format=source_format,
    )


def _build_block(source_exam_id: str, ordinal: int, guide: str, items: list[QuestionItem]) -> ThematicBlock:
    block_id = _block_id(source_exam_id, ordinal)
    fixed_items = tuple(replace(item, block_id=block_id) for item in items)
    return ThematicBlock(id=block_id, guide_statement=guide, source_exam_id=source_exam_id, items=fixed_items)


def _block_id(source_exam_id: str, ordinal: int) -> str:
    return f"{source_exam_id}:bloco:{ordinal:03d}"


def _extract_objective_body(text: str) -> str:
    marker = re.search(r"--\s*PROVA OBJETIVA\s*--", text, flags=re.IGNORECASE)
    if marker:
        text = text[marker.end() :]
    text = re.sub(r"(?m)^\s*CEBRASPE\s+[–-]\s+INSS\s+[–-]\s+Edital:.*$", "", text)
    text = re.sub(r"(?m)^\s*[•●].*$", "", text)
    text = re.sub(r"(?m)^\s*Espaço livre\s*$", "", text, flags=re.IGNORECASE)
    return text


def _split_trailing_guide(segment: str) -> tuple[str, str | None]:
    matches = list(GUIDE_START_RE.finditer(segment))
    if not matches:
        return segment, None
    split_at = matches[-1].start()
    statement = segment[:split_at]
    guide = segment[split_at:]
    if len(_normalize_text(statement)) < 12:
        return segment, None
    return statement, guide


def _sequential_item_matches(body: str, answers: dict[int, str]) -> list[re.Match[str]]:
    expected = sorted(answers)
    if not expected:
        return []

    accepted: list[re.Match[str]] = []
    expected_index = 0
    for match in ITEM_START_RE.finditer(body):
        number = int(match.group(1))
        if expected_index < len(expected) and number == expected[expected_index]:
            accepted.append(match)
            expected_index += 1
    return accepted


def _normalize_text(value: str) -> str:
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s*\n\s*", " ", value)
    return value.strip()


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _as_int_tokens(line: str) -> list[int]:
    tokens = line.split()
    if not tokens or not all(token.isdigit() for token in tokens):
        return []
    numbers = [int(token) for token in tokens]
    if all(number == 0 for number in numbers):
        return []
    return numbers


def _parse_number_row(line: str) -> list[int]:
    spaced_numbers = _as_int_tokens(line)
    if spaced_numbers:
        prefix = _nonzero_consecutive_prefix(spaced_numbers)
        if prefix:
            return prefix

    compact = re.sub(r"\s+", "", line)
    if not compact.isdigit():
        return []

    for start in range(1, 201, 20):
        expected = list(range(start, start + 20))
        expected_text = "".join(str(number) for number in expected)
        if compact.startswith(expected_text):
            return expected
    return []


def _parse_answer_row(line: str, expected_count: int) -> list[str]:
    compact = re.sub(r"\s+", "", line).upper()
    if not compact:
        return []

    answers: list[str] = []
    for char in compact:
        if char == "0":
            break
        if char not in {"C", "E", "X"}:
            return []
        answers.append(char)
        if len(answers) == expected_count:
            return answers
    return answers if len(answers) == expected_count else []


def _nonzero_consecutive_prefix(numbers: list[int]) -> list[int]:
    prefix: list[int] = []
    for number in numbers:
        if number == 0:
            break
        prefix.append(number)

    if not prefix:
        return []
    start = prefix[0]
    expected = list(range(start, start + len(prefix)))
    return prefix if prefix == expected else []


def _set_preferred_path(paths: dict[str, Path], key: str, path: Path) -> None:
    current = paths.get(key)
    if current is None or _is_copy_suffix(current.stem):
        paths[key] = path


def _drop_copy_suffix(stem: str) -> str:
    return re.sub(r"\s+\(\d+\)$", "", stem).strip()


def _is_copy_suffix(stem: str) -> bool:
    return bool(re.search(r"\s+\(\d+\)$", stem))


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return _normalize_text(match.group(1)) if match else None
