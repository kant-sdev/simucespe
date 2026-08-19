from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from simucespe.settings import api_port_from_env, cors_origins_from_env


class SettingsTest(unittest.TestCase):
    def test_api_port_uses_render_port_env(self) -> None:
        with patch.dict(os.environ, {"PORT": "10000"}):
            self.assertEqual(api_port_from_env(), 10000)

    def test_default_cors_origins_include_local_and_production_frontends(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                cors_origins_from_env(),
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "https://simucespe.netlify.app",
                ],
            )

    def test_cors_origins_are_comma_separated(self) -> None:
        with patch.dict(os.environ, {"BACKEND_CORS_ORIGINS": "https://front.netlify.app, http://localhost:5173"}):
            self.assertEqual(
                cors_origins_from_env(),
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "https://simucespe.netlify.app",
                    "https://front.netlify.app",
                ],
            )


if __name__ == "__main__":
    unittest.main()
