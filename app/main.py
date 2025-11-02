from __future__ import annotations

import logging
from pathlib import Path

from .bot import PsymatchBot
from .config import get_settings


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(path, encoding="utf-8"),
        ],
    )


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_file)
    bot = PsymatchBot(settings)
    bot.run()


if __name__ == "__main__":
    main()

