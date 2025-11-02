from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


BASE_DIR = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def load_questions() -> Dict[str, Any]:
    path = BASE_DIR / "data" / "test_questions.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_texts() -> Dict[str, str]:
    path = BASE_DIR / "data" / "test_texts.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

