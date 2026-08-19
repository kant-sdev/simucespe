from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from simucespe.api import create_app


class ApiTest(unittest.TestCase):
    def test_full_exam_simulado_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            client = TestClient(create_app(history_path=history_path))

            provas = client.get("/provas")
            self.assertEqual(provas.status_code, 200)
            source_id = provas.json()[0]["source_id"]

            created = client.post(
                "/simulados",
                json={"mode": "prova_completa", "source_exam_id": source_id, "timer_seconds": 3600},
            )
            self.assertEqual(created.status_code, 201)
            simulado = created.json()
            self.assertGreater(simulado["total_items"], 0)
            self.assertIsNotNone(simulado["blocks"][0]["guide_statement"])
            self.assertNotIn("official_answer", simulado["blocks"][0]["items"][0])

            answers = {
                item["number"]: "C"
                for block in simulado["blocks"]
                for item in block["items"]
            }
            result = client.post(f"/simulados/{simulado['id']}/respostas", json={"answers": answers})

            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["total_items"], simulado["total_items"])
            self.assertTrue(history_path.exists())
            self.assertEqual(len(json.loads(history_path.read_text(encoding="utf-8"))), 1)

    def test_rejects_incomplete_answers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(history_path=Path(tmpdir) / "history.json"))
            source_id = client.get("/provas").json()[0]["source_id"]
            simulado = client.post(
                "/simulados",
                json={"mode": "prova_completa", "source_exam_id": source_id},
            ).json()

            result = client.post(f"/simulados/{simulado['id']}/respostas", json={"answers": {}})

            self.assertEqual(result.status_code, 422)
            self.assertTrue(result.json()["detail"]["missing"])

    def test_cors_allows_configured_frontend_origin(self) -> None:
        client = TestClient(create_app(cors_origins=["https://front.netlify.app"]))

        response = client.options(
            "/provas",
            headers={
                "Origin": "https://front.netlify.app",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://front.netlify.app")


if __name__ == "__main__":
    unittest.main()
