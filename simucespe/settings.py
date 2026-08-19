from __future__ import annotations

import os

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://simucespe.netlify.app",
]


def cors_origins_from_env() -> list[str]:
    configured_origins = [
        origin.strip()
        for origin in os.getenv("BACKEND_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys([*DEFAULT_CORS_ORIGINS, *configured_origins]))


def api_host_from_env(default: str = "127.0.0.1") -> str:
    return os.getenv("HOST", default)


def api_port_from_env(default: int = 8000) -> int:
    raw = os.getenv("PORT")
    if raw is None:
        return default
    return int(raw)
