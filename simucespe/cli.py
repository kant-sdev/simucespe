from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn

from .ingestion import find_exam_pairs, ingest_exam_pair
from .serialization import exam_summary_to_dict, exam_to_dict
from .settings import api_host_from_env, api_port_from_env


def validate_pair_main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Parse and summarize one CEBRASPE prova/gabarito pair.")
    parser.add_argument("--dir", default="prova_gabarito", help="Directory containing prova/gabarito files.")
    parser.add_argument("--pair-key", help="Pair key to validate. Defaults to the first discovered pair.")
    parser.add_argument("--max-items-per-block", type=int, default=4)
    parser.add_argument("--summary-only", action="store_true", help="Print only metadata and totals.")
    args = parser.parse_args()

    pairs = find_exam_pairs(Path(args.dir))
    if not pairs:
        raise SystemExit("No prova/gabarito pairs were found.")

    pair_key = args.pair_key or sorted(pairs)[0]
    if pair_key not in pairs:
        raise SystemExit(f"Pair key not found: {pair_key}. Available: {', '.join(sorted(pairs))}")

    prova_path, gabarito_path = pairs[pair_key]
    exam = ingest_exam_pair(prova_path, gabarito_path)
    output = exam_summary_to_dict(pair_key, str(prova_path), str(gabarito_path), exam)
    if not args.summary_only:
        output["blocks"] = [
            {
                "id": block.id,
                "theme": block.theme,
                "theme_pending": block.theme_pending,
                "guide_statement": block.guide_statement,
                "item_numbers": [item.number for item in block.items],
                "items_sample": [
                    {
                        "number": item.number,
                        "statement": item.statement,
                        "official_answer": item.official_answer,
                        "is_annulled": item.is_annulled,
                        "theme": item.theme,
                        "theme_pending": item.theme_pending,
                    }
                    for item in block.items[: args.max_items_per_block]
                ],
            }
            for block in exam.blocks
        ]
    print(json.dumps(output, ensure_ascii=False, indent=2))


def ingest_all_main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Ingest all discovered CEBRASPE prova/gabarito pairs.")
    parser.add_argument("--dir", default="prova_gabarito", help="Directory containing prova/gabarito files.")
    parser.add_argument("--out-dir", default="data/parsed", help="Directory where parsed exam JSON files are written.")
    args = parser.parse_args()

    pairs = find_exam_pairs(Path(args.dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, list[dict]] = {"successes": [], "failures": []}
    for pair_key, (prova_path, gabarito_path) in pairs.items():
        try:
            exam = ingest_exam_pair(prova_path, gabarito_path)
            output_path = out_dir / f"{pair_key}.json"
            output_path.write_text(json.dumps(exam_to_dict(exam), ensure_ascii=False, indent=2), encoding="utf-8")
            report["successes"].append(
                {
                    **exam_summary_to_dict(pair_key, str(prova_path), str(gabarito_path), exam),
                    "output": str(output_path),
                }
            )
        except Exception as exc:
            report["failures"].append(
                {
                    "pair_key": pair_key,
                    "prova": str(prova_path),
                    "gabarito": str(gabarito_path),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    report_path = out_dir / "ingestion_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**report, "report": str(report_path)}, ensure_ascii=False, indent=2))


def api_main() -> None:
    parser = argparse.ArgumentParser(description="Run the SimuCESPE API.")
    parser.add_argument("--host", default=api_host_from_env())
    parser.add_argument("--port", type=int, default=api_port_from_env())
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("simucespe.api:app", host=args.host, port=args.port, reload=args.reload)
