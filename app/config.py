from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Set

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_path = BASE_DIR / ".env"
    load_dotenv(env_path, override=False)


def _parse_whitelist(value: str | None) -> Set[int]:
    if not value:
        return set()

    result: Set[int] = set()
    for part in value.split(","):
        candidate = part.strip()
        if not candidate:
            continue
        try:
            result.add(int(candidate))
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"ADMIN_WHITELIST содержит нечисловое значение: {candidate!r}") from exc
    return result


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    database_path: Path
    admin_whitelist: Set[int]
    log_file: Path


def get_settings() -> Settings:
    _load_env()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    db_path = os.getenv("DATABASE_PATH") or str(BASE_DIR / "psymatch.db")
    whitelist_raw = os.getenv("ADMIN_WHITELIST")
    log_file_raw = os.getenv("LOG_FILE") or str(BASE_DIR / "logs" / "bot.log")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")

    admin_whitelist = _parse_whitelist(whitelist_raw)

    return Settings(
        telegram_token=token,
        database_path=Path(db_path).expanduser().resolve(),
        admin_whitelist=admin_whitelist,
        log_file=Path(log_file_raw).expanduser().resolve(),
    )

